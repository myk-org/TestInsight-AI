"""Analysis endpoints for TestInsight AI."""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.schemas import AnalysisRequest, AnalysisResponse
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/analyze", tags=["analysis"])
logger = logging.getLogger("testinsight")


def _redact_repo_url(url: str | None) -> str | None:
    """Redact embedded credentials/tokens from a repository URL for safe logging.

    Examples:
    - https://token@github.com/user/repo.git -> https://***@github.com/user/repo.git
    - https://user:token@github.com/user/repo -> https://***:***@github.com/user/repo # pragma: allowlist secret
    - http(s) basic auth patterns are replaced, leaving host/path intact.
    """
    if not url or not isinstance(url, str):
        return url
    try:
        # Replace user or user:pass before '@'
        return re.sub(r"https?://[^/@:]+(?::[^/@]*)?@", "https://***@", url)
    except Exception:
        return url


@router.post("", response_model=AnalysisResponse)
async def analyze(
    text: str = Form(..., description="Text content to analyze (logs, junit xml, etc.)"),
    custom_context: str | None = Form(None, description="Additional context"),
    system_prompt: str | None = Form(None, description="Custom system prompt for the AI"),
    repository_url: str | None = Form(None, description="GitHub repository URL for code context"),
    repository_branch: str | None = Form(None, description="Repository branch to analyze"),
    repository_commit: str | None = Form(None, description="Repository commit hash to analyze"),
    include_repository_context: bool = Form(False, description="Include repository source code in analysis"),
    api_key: str | None = Form(None, description="Gemini API key (uses settings if not provided)"),
    repo_max_files: int | None = Form(None, description="Max repo files to include"),
    repo_max_bytes: int | None = Form(None, description="Max bytes per repo file"),
) -> AnalysisResponse:
    """Analyze text content with AI (legacy endpoint)."""
    try:
        # Early validation to avoid long-running work on empty input
        if not text or not text.strip():
            raise HTTPException(status_code=422, detail="Text content is empty; no analyzable content")
        # Basic input validation and sensible upper bounds for repository limits
        if repo_max_files is not None and (repo_max_files < 1 or repo_max_files > 500):
            raise HTTPException(status_code=422, detail="repo_max_files must be between 1 and 500")
        if repo_max_bytes is not None and (repo_max_bytes < 1024 or repo_max_bytes > 2_000_000):
            raise HTTPException(status_code=422, detail="repo_max_bytes must be between 1KB and 2MB")
        logger.info(
            "Analyze(text): include_repo=%s repo_url=%s branch=%s commit=%s",
            include_repository_context,
            _redact_repo_url(repository_url),
            repository_branch,
            repository_commit,
        )
        client_creators = ServiceClientCreators()
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        # Clone repository if requested
        cloned_repo_path = None
        warning_note: str | None = None
        if include_repository_context and repository_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repository_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception as e:
                # Fallback: continue without repository context if cloning fails
                warning_note = f"Repository cloning failed: {str(e)}. Proceeding without repository context."
            else:
                logger.info(
                    "Analyze(text): repo cloned ok url=%s branch=%s commit=%s path=%s",
                    _redact_repo_url(repository_url),
                    repository_branch,
                    repository_commit,
                    cloned_repo_path,
                )

        # Create request with repository information
        request = AnalysisRequest(
            text=text,
            custom_context=custom_context,
            system_prompt=system_prompt,
            repository_url=repository_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
            repo_max_files=repo_max_files,
            repo_max_bytes=repo_max_bytes,
        )

        # Add cloned path and repo limits to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        request.repo_max_files = repo_max_files
        request.repo_max_bytes = repo_max_bytes

        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(text): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary
        if warning_note:
            summary_text = f"Note: {warning_note}\n\n{summary_text}"

        return AnalysisResponse(
            insights=analysis.insights, summary=summary_text, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text analysis failed: {str(e)}")


@router.post("/file", response_model=AnalysisResponse)
async def analyze_file(
    files: list[UploadFile] = File(..., description="Files to analyze (json, xml, text, log)"),
    repo_url: str | None = Form(None, description="Repository URL for context"),
    repository_branch: str | None = Form(None, description="Repository branch to analyze"),
    repository_commit: str | None = Form(None, description="Repository commit hash to analyze"),
    include_repository_context: bool = Form(False, description="Include repository source code in analysis"),
    custom_context: str | None = Form(None, description="Additional context"),
    system_prompt: str | None = Form(None, description="Custom system prompt for the AI"),
    api_key: str | None = Form(None, description="Gemini API key (uses settings if not provided)"),
    repo_max_files: int | None = Form(None, description="Max repo files to include"),
    repo_max_bytes: int | None = Form(None, description="Max bytes per repo file"),
) -> AnalysisResponse:
    """Analyze uploaded files with AI.

    Args:
        files: List of files to analyze (supports json, xml, text, log file types)
        repo_url: Optional repository URL for additional context
        custom_context: Optional additional context
        api_key: Optional Gemini API key

    Returns:
        AI analysis results with insights, summary, and recommendations
    """
    # Define allowed file extensions and MIME types
    ALLOWED_EXTENSIONS = {".json", ".xml", ".txt", ".log", ".text"}
    ALLOWED_MIME_TYPES = {
        "application/json",
        "application/xml",
        "text/xml",
        "text/plain",
        "text/x-log",
        "application/octet-stream",  # Some log files may have this MIME type
    }

    try:
        logger.info(
            "Analyze(file): include_repo=%s repo_url=%s branch=%s commit=%s file_count=%d",
            include_repository_context,
            _redact_repo_url(repo_url),
            repository_branch,
            repository_commit,
            len(files or []),
        )
        # Basic input validation and sensible upper bounds for repository limits
        if repo_max_files is not None and (repo_max_files < 1 or repo_max_files > 500):
            raise HTTPException(status_code=422, detail="repo_max_files must be between 1 and 500")
        if repo_max_bytes is not None and (repo_max_bytes < 1024 or repo_max_bytes > 2_000_000):
            raise HTTPException(status_code=422, detail="repo_max_bytes must be between 1KB and 2MB")
        if not files:
            raise HTTPException(status_code=400, detail="No files provided")

        # Validate file types
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=400, detail="File must have a filename")

            # Get file extension
            file_ext = Path(file.filename).suffix.lower()

            # Check file extension
            if file_ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type '{file_ext}' not supported. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
                )

            # Check MIME type if available
            if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
                # Allow through if extension is valid but MIME type is unexpected
                # This handles cases where browsers send different MIME types
                pass

        # Combine all file contents
        combined_text = ""
        has_non_empty_content = False
        for file in files:
            content = await file.read()
            try:
                file_text = content.decode("utf-8")
                if file_text.strip():
                    has_non_empty_content = True
                combined_text += f"\n\n=== {file.filename} ===\n{file_text}"
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} contains invalid UTF-8 encoding. Please ensure the file is text-based.",
                )

        # If all files were empty (or whitespace-only), surface a clear error (test expects 500)
        if not has_non_empty_content:
            raise HTTPException(status_code=500, detail="Uploaded files contain no analyzable content")

        # Build context from repository and custom context
        context_parts = []
        if repo_url:
            context_parts.append(f"Repository: {repo_url}")
        if custom_context:
            context_parts.append(custom_context)

        final_context = "; ".join(context_parts) if context_parts else None

        # Clone repository if requested
        client_creators = ServiceClientCreators()
        cloned_repo_path = None
        warning_note: str | None = None
        if include_repository_context and repo_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repo_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception as e:
                # Fallback: continue without repository context if cloning fails
                warning_note = f"Repository cloning failed: {str(e)}. Proceeding without repository context."
            else:
                logger.info(
                    "Analyze(file): repo cloned ok url=%s branch=%s commit=%s path=%s",
                    _redact_repo_url(repo_url),
                    repository_branch,
                    repository_commit,
                    cloned_repo_path,
                )

        # Analyze with AI
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        # Create request with repository information
        request = AnalysisRequest(
            text=combined_text.strip(),
            custom_context=final_context,
            system_prompt=system_prompt,
            repository_url=repo_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
            repo_max_files=repo_max_files,
            repo_max_bytes=repo_max_bytes,
        )

        # Add cloned path and repo limits to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        request.repo_max_files = repo_max_files
        request.repo_max_bytes = repo_max_bytes
        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(file): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary
        if warning_note:
            summary_text = f"Note: {warning_note}\n\n{summary_text}"

        return AnalysisResponse(
            insights=analysis.insights, summary=summary_text, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")


@router.post("/jenkins", response_model=AnalysisResponse)
async def analyze_jenkins_build(
    job_name: str = Form(..., description="Jenkins job name"),
    build_number: str = Form("", description="Build number (empty for latest)"),
    repo_url: str | None = Form(None, description="Repository URL for context"),
    repository_branch: str | None = Form(None, description="Repository branch to analyze"),
    repository_commit: str | None = Form(None, description="Repository commit hash to analyze"),
    include_repository_context: bool = Form(False, description="Include repository source code in analysis"),
    include_console: bool = Form(False, description="Include Jenkins console output in analysis"),
    system_prompt: str | None = Form(None, description="Custom system prompt for the AI"),
    jenkins_url: str | None = Form(None, description="Jenkins URL (uses settings if not provided)"),
    jenkins_username: str | None = Form(None, description="Jenkins username (uses settings if not provided)"),
    jenkins_password: str | None = Form(None, description="Jenkins API token (uses settings if not provided)"),
    verify_ssl: bool | None = Form(None, description="Verify SSL (uses settings if not provided)"),
    api_key: str | None = Form(None, description="Gemini API key (uses settings if not provided)"),
    repo_max_files: int | None = Form(None, description="Max repo files to include"),
    repo_max_bytes: int | None = Form(None, description="Max bytes per repo file"),
) -> AnalysisResponse:
    """Analyze Jenkins build output with AI.

    Args:
        job_name: Jenkins job name
        build_number: Build number (empty for latest)
        repo_url: Optional repository URL for additional context
        jenkins_url: Optional Jenkins URL
        jenkins_username: Optional Jenkins username
        jenkins_password: Optional Jenkins API token
        verify_ssl: Optional SSL verification setting
        api_key: Optional Gemini API key

    Returns:
        AI analysis results with insights, summary, and recommendations
    """
    try:
        logger.info(
            "Analyze(jenkins): job=%s build=%s include_repo=%s repo_url=%s branch=%s commit=%s include_console=%s",
            job_name,
            build_number,
            include_repository_context,
            _redact_repo_url(repo_url),
            repository_branch,
            repository_commit,
            include_console,
        )
        # Basic input validation and sensible upper bounds for repository limits
        if repo_max_files is not None and (repo_max_files < 1 or repo_max_files > 500):
            raise HTTPException(status_code=422, detail="repo_max_files must be between 1 and 500")
        if repo_max_bytes is not None and (repo_max_bytes < 1024 or repo_max_bytes > 2_000_000):
            raise HTTPException(status_code=422, detail="repo_max_bytes must be between 1KB and 2MB")
        # Default label used in error messages before we can resolve a concrete build number
        build_label: str = "unknown"
        client_creators = ServiceClientCreators()

        # Get Jenkins client with provided or configured parameters
        try:
            jenkins_client = client_creators.create_configured_jenkins_client(
                url=jenkins_url, username=jenkins_username, password=jenkins_password, verify_ssl=verify_ssl
            )
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))

        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Jenkins client connection failed. Please check your Jenkins settings."
            )

        # Determine build number (latest if not provided)
        final_build_number = None
        if build_number and build_number.strip():
            try:
                final_build_number = int(build_number.strip())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Build number must be a valid integer for job {job_name}",
                )

        # Get test report (and optionally console output) from Jenkins
        if final_build_number:
            test_report = jenkins_client.get_build_test_report(job_name, final_build_number)
        else:
            # Get latest build
            builds = jenkins_client.get_job_builds(job_name, 1)
            if not builds:
                raise HTTPException(status_code=404, detail=f"No builds found for job {job_name}")
            latest_build = builds[0]
            final_build_number = latest_build.get("number")
            if final_build_number is None:
                raise HTTPException(status_code=404, detail=f"Latest build for job {job_name} has no build number")
            test_report = jenkins_client.get_build_test_report(job_name, final_build_number)
        logger.info("Analyze(jenkins): resolved build_number=%s", final_build_number)

        # Update build label for subsequent error messages
        build_label = str(final_build_number) if final_build_number is not None else "latest"

        console_output: str | None = None
        if include_console:
            try:
                # JenkinsClient from python-jenkins exposes get_build_console_output
                console_output = jenkins_client.get_build_console_output(job_name, final_build_number)
            except Exception:
                # If console retrieval fails, continue with test report only
                console_output = None

        # Combine contents for AI analysis
        combined_text = str(test_report) if test_report is not None else ""
        if include_console and console_output:
            combined_text = f"{combined_text}\n\n=== Jenkins Console Output (Job: {job_name}, Build: {final_build_number}) ===\n{console_output}"

        # If both test report and console output are unavailable, return 404
        if not combined_text.strip():
            # Provide actionable hint when console analysis is not enabled
            hint = (
                " Hint: enable 'Include Jenkins console output' to analyze console logs when the test report is missing."
                if not include_console
                else ""
            )
            raise HTTPException(
                status_code=404,
                detail=f"No analyzable content found for job {job_name}, build {build_label}.{hint}",
            )

        # Build context
        context_parts = [f"Jenkins job: {job_name}", f"Build: {final_build_number}"]
        if repo_url:
            context_parts.append(f"Repository: {repo_url}")
        final_context = "; ".join(context_parts)

        # Clone repository if requested
        cloned_repo_path = None
        warning_note: str | None = None
        if include_repository_context and repo_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repo_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception as e:
                # Fallback: continue without repository context if cloning fails
                warning_note = f"Repository cloning failed: {str(e)}. Proceeding without repository context."
            else:
                logger.info(
                    "Analyze(jenkins): repo cloned ok url=%s branch=%s commit=%s path=%s",
                    _redact_repo_url(repo_url),
                    repository_branch,
                    repository_commit,
                    cloned_repo_path,
                )

        # Analyze with AI
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        # Create request with repository information
        request = AnalysisRequest(
            text=combined_text if combined_text else "",
            custom_context=final_context,
            system_prompt=system_prompt,
            repository_url=repo_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
            repo_max_files=repo_max_files,
            repo_max_bytes=repo_max_bytes,
        )

        # Add cloned path and repo limits to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        request.repo_max_files = repo_max_files
        request.repo_max_bytes = repo_max_bytes
        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(jenkins): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary
        if warning_note:
            summary_text = f"Note: {warning_note}\n\n{summary_text}"

        return AnalysisResponse(
            insights=analysis.insights, summary=summary_text, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        # Use best-effort context for clearer error reporting
        try:
            build_label  # noqa: B018 - just ensure variable exists
        except Exception:
            build_label = "unknown"
        raise HTTPException(
            status_code=500,
            detail=f"Jenkins analysis failed for job {job_name}, build {build_label}: {str(e)}",
        )
