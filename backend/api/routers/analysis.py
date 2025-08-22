"""Analysis endpoints for TestInsight AI."""

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.schemas import AnalysisRequest, AnalysisResponse
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/analyze", tags=["analysis"])


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
) -> AnalysisResponse:
    """Analyze text content with AI (legacy endpoint)."""
    try:
        client_creators = ServiceClientCreators()
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        # Clone repository if requested
        cloned_repo_path = None
        if include_repository_context and repository_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repository_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception:
                # Fallback: continue without repository context if cloning fails
                pass

        # Create request with repository information
        request = AnalysisRequest(
            text=text,
            custom_context=custom_context,
            system_prompt=system_prompt,
            repository_url=repository_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
        )

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path

        analysis = ai_analyzer.analyze_test_results(request)

        return AnalysisResponse(
            insights=analysis.insights, summary=analysis.summary, recommendations=analysis.recommendations
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
        for file in files:
            content = await file.read()
            try:
                file_text = content.decode("utf-8")
                combined_text += f"\n\n=== {file.filename} ===\n{file_text}"
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} contains invalid UTF-8 encoding. Please ensure the file is text-based.",
                )

        if not combined_text.strip():
            raise HTTPException(status_code=400, detail="No valid content found in uploaded files")

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
        if include_repository_context and repo_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repo_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception:
                # Fallback: continue without repository context if cloning fails
                pass

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
        )

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        analysis = ai_analyzer.analyze_test_results(request)

        return AnalysisResponse(
            insights=analysis.insights, summary=analysis.summary, recommendations=analysis.recommendations
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
    system_prompt: str | None = Form(None, description="Custom system prompt for the AI"),
    jenkins_url: str | None = Form(None, description="Jenkins URL (uses settings if not provided)"),
    jenkins_username: str | None = Form(None, description="Jenkins username (uses settings if not provided)"),
    jenkins_password: str | None = Form(None, description="Jenkins API token (uses settings if not provided)"),
    verify_ssl: bool | None = Form(None, description="Verify SSL (uses settings if not provided)"),
    api_key: str | None = Form(None, description="Gemini API key (uses settings if not provided)"),
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
                raise HTTPException(status_code=400, detail="Build number must be a valid integer")

        # Get console output from Jenkins
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

        if test_report is None:
            raise HTTPException(status_code=404, detail=f"Test report not found for build {final_build_number}")

        # Build context
        context_parts = [f"Jenkins job: {job_name}", f"Build: {final_build_number}"]
        if repo_url:
            context_parts.append(f"Repository: {repo_url}")
        final_context = "; ".join(context_parts)

        # Clone repository if requested
        cloned_repo_path = None
        if include_repository_context and repo_url:
            try:
                git_client = client_creators.create_configured_git_client(
                    repo_url=repo_url, branch=repository_branch, commit=repository_commit
                )
                cloned_repo_path = str(git_client.repo_path)
            except Exception:
                # Fallback: continue without repository context if cloning fails
                pass

        # Analyze with AI
        ai_analyzer = client_creators.create_configured_ai_client(api_key=api_key)
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        # Create request with repository information
        request = AnalysisRequest(
            text=str(test_report) if test_report else "",
            custom_context=final_context,
            system_prompt=system_prompt,
            repository_url=repo_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
        )

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        analysis = ai_analyzer.analyze_test_results(request)

        return AnalysisResponse(
            insights=analysis.insights, summary=analysis.summary, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Jenkins analysis failed: {str(e)}")
