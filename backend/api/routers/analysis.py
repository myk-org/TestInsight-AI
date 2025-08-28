"""Analysis endpoints for TestInsight AI."""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.models.schemas import AnalysisRequest, AnalysisResponse
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/analyze", tags=["analysis"])
logger = logging.getLogger("testinsight")

# Maximum payload size to protect model and server (5MB)
MAX_COMBINED_TEXT_SIZE = 5 * 1024 * 1024  # 5MB in bytes


def _validate_repo_limits(repo_max_files: int | None, repo_max_bytes: int | None) -> None:
    """Validate repository limits for analysis endpoints.

    Args:
        repo_max_files: Maximum number of files to include from repository
        repo_max_bytes: Maximum bytes per repository file

    Raises:
        HTTPException: If limits are outside acceptable ranges
    """
    if repo_max_files is not None and (repo_max_files < 1 or repo_max_files > 500):
        raise HTTPException(status_code=422, detail="repo_max_files must be between 1 and 500")
    if repo_max_bytes is not None and (repo_max_bytes < 1024 or repo_max_bytes > 2_000_000):
        raise HTTPException(status_code=422, detail="repo_max_bytes must be between 1KB and 2MB")


def _redact_text(text: str | None) -> str | None:
    """Redact sensitive information from text for safe logging.

    Handles multiple patterns including URLs and common sensitive data:
    - https://token@github.com/user/repo.git -> https://***@github.com/user/repo.git
    - https://user:token@github.com/user/repo -> https://***:***@github.com/user/repo # pragma: allowlist secret
    - ssh://user@host/repo -> ssh://***@host/repo
    - git@github.com:user/repo.git -> ***@github.com:user/repo.git
    - API keys, passwords, tokens in quoted strings
    - Database connection strings
    - URL query parameters: ?token=abc123 -> ?token=***
    - Authorization headers: Authorization: Bearer abc123 -> Authorization: Bearer ***

    Args:
        text: Text to redact (can be None or non-string)

    Returns:
        Redacted text or original value if non-string/None/exception
    """
    if not text or not isinstance(text, str):
        return text
    try:
        # Replace http(s) auth patterns (case-insensitive)
        redacted = re.sub(r"(?i)(https?)://[^/@:]+:[^/@]*@", r"\1://***:***@", text)
        redacted = re.sub(r"(?i)(https?)://[^/@:]+@", r"\1://***@", redacted)
        # Replace ssh://user@ patterns
        redacted = re.sub(r"(?i)ssh://[^/@:]+@", "ssh://***@", redacted)
        # Replace scp-like patterns at token boundaries: user@host:
        redacted = re.sub(r"(?m)(?<!\S)[^/@:\s]+@([^/@:\s]+):", r"***@\1:", redacted)

        # Redact common sensitive patterns in exception messages
        # API keys in quotes (common format: 'AIzaSy...' or "sk-...")
        redacted = re.sub(r"['\"]([A-Za-z0-9_-]{20,})['\"]", r"'***'", redacted)
        # Password/token patterns in quotes
        redacted = re.sub(
            r"(password|token|key|secret)\s*['\"]([^'\"]+)['\"]", r"\1 '***'", redacted, flags=re.IGNORECASE
        )
        # Unquoted tokens after 'with token', 'token:', etc.
        redacted = re.sub(r"(with\s+token|token[:=])\s+([A-Za-z0-9_-]{6,})", r"\1 ***", redacted, flags=re.IGNORECASE)
        # Database connection strings with passwords
        redacted = re.sub(r"://([^:/]+):([^@/]+)@", r"://\1:***@", redacted)

        # Redact common query parameters with sensitive values
        redacted = re.sub(
            r"(?i)([?&])(token|access_token|api_key|api-key|key|secret|password)=[^&\s]+", r"\1\2=***", redacted
        )

        # Redact Authorization headers and Bearer tokens
        redacted = re.sub(r"(?i)authorization:\s*bearer\s+[A-Za-z0-9\-_\.]+", "Authorization: Bearer ***", redacted)
        redacted = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9\-_\.]+", "Bearer ***", redacted)

        return redacted
    except Exception:
        return text


def _redact_repo_url(url: str | None) -> str | None:
    """Redact embedded credentials/tokens from a repository URL for safe logging.

    This is a convenience wrapper around _redact_text for backwards compatibility.
    """
    return _redact_text(url)


def _sanitize_filename_for_header(name: str) -> str:
    """Sanitize filename for safe inclusion in text headers.

    Removes control characters and newlines that could cause header injection
    or formatting issues, and caps length to prevent excessive output.

    Args:
        name: Original filename

    Returns:
        Sanitized filename safe for headers
    """
    # Remove control chars/newlines and cap length
    return re.sub(r"[\r\n\t]+", " ", name)[:256]


def _truncate_text_safely(text: str, max_size: int = MAX_COMBINED_TEXT_SIZE) -> tuple[str, bool]:
    """Truncate text to maximum size with note if truncated.

    Guarantees the returned text bytes never exceed max_size by reserving
    space for the truncation note before cutting the original text.

    Args:
        text: Text to potentially truncate
        max_size: Maximum size in bytes

    Returns:
        Tuple of (potentially truncated text, was_truncated)
    """
    text_bytes = text.encode("utf-8")
    if len(text_bytes) <= max_size:
        return text, False

    # Calculate truncation note and its byte length
    truncation_note = f"\n\n[NOTE: Text was truncated to {max_size // (1024 * 1024)}MB due to size limits]"
    note_bytes_len = len(truncation_note.encode("utf-8"))

    # If the note itself is larger than max_size, use a shorter note
    if note_bytes_len >= max_size:
        truncation_note = "\n\n[NOTE: Text truncated]"
        note_bytes_len = len(truncation_note.encode("utf-8"))

        # If even the short note is too large, return just the truncated content
        if note_bytes_len >= max_size:
            truncated_bytes = text_bytes[:max_size]
            try:
                return truncated_bytes.decode("utf-8"), True
            except UnicodeDecodeError:
                # Find the last complete UTF-8 sequence
                while len(truncated_bytes) > 0:
                    try:
                        return truncated_bytes.decode("utf-8"), True
                    except UnicodeDecodeError:
                        truncated_bytes = truncated_bytes[:-1]
                return "", True

    # Calculate allowed content byte length (ensure it's >= 0)
    allowed_content_bytes = max(0, max_size - note_bytes_len)

    # Truncate to allowed content length, ensuring we don't break UTF-8 encoding
    truncated_bytes = text_bytes[:allowed_content_bytes]
    try:
        truncated_text = truncated_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Find the last complete UTF-8 sequence
        while len(truncated_bytes) > 0:
            try:
                truncated_text = truncated_bytes.decode("utf-8")
                break
            except UnicodeDecodeError:
                truncated_bytes = truncated_bytes[:-1]
        else:
            truncated_text = ""

    return truncated_text + truncation_note, True


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

        # Truncate text if too large to protect model and server
        text, was_truncated = _truncate_text_safely(text)
        if was_truncated:
            logger.warning("Input text was truncated due to size limits for analysis")
        # Basic input validation and sensible upper bounds for repository limits
        _validate_repo_limits(repo_max_files, repo_max_bytes)
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
                warning_note = "Repository cloning failed; proceeding without repository context."
                logger.warning(
                    "Repository cloning failed for url=%s: %s (%s)",
                    _redact_repo_url(repository_url),
                    type(e).__name__,
                    _redact_text(str(e)),
                )
            else:
                logger.info(
                    "Analyze(text): repo cloned ok url=%s branch=%s commit=%s path=%s",
                    _redact_repo_url(repository_url),
                    repository_branch,
                    repository_commit,
                    cloned_repo_path,
                )

        # Create request with repository information
        # Redact repo URL in user-supplied context to prevent credential leakage to LLM
        safe_custom_context = _redact_text(custom_context) if custom_context else custom_context

        request = AnalysisRequest(
            text=text,
            custom_context=safe_custom_context,
            system_prompt=system_prompt,
            repository_url=repository_url,
            repository_branch=repository_branch,
            repository_commit=repository_commit,
            include_repository_context=include_repository_context,
            repo_max_files=repo_max_files,
            repo_max_bytes=repo_max_bytes,
        )

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path

        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(text): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary or ""
        if warning_note:
            summary_text = f"Note: {warning_note}\n\n{summary_text}"

        return AnalysisResponse(
            insights=analysis.insights, summary=summary_text, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analyze(text) failed: %s", _redact_text(str(e)))
        raise HTTPException(status_code=500, detail="Text analysis failed.")


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
        _validate_repo_limits(repo_max_files, repo_max_bytes)
        if not files:
            raise HTTPException(status_code=422, detail="No files provided")

        # Validate file types
        for file in files:
            if not file.filename:
                raise HTTPException(status_code=422, detail="File must have a filename")

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
                safe_name = _sanitize_filename_for_header(file.filename)
                combined_text += f"\n\n=== {safe_name} ===\n{file_text}"
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} contains invalid UTF-8 encoding. Please ensure the file is text-based.",
                )

        # If all files were empty (or whitespace-only), surface a clear error (test expects 500)
        if not has_non_empty_content:
            raise HTTPException(status_code=500, detail="Uploaded files contain no analyzable content")

        # Truncate combined text if too large to protect model and server
        combined_text, was_truncated = _truncate_text_safely(combined_text)
        if was_truncated:
            logger.warning("Combined file content was truncated due to size limits for analysis")

        # Build context from repository and custom context
        context_parts = []
        if repo_url:
            context_parts.append(f"Repository: {_redact_repo_url(repo_url)}")
        if custom_context:
            redacted_context = _redact_text(custom_context)
            if redacted_context:  # Only append if not None
                context_parts.append(redacted_context)

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
                warning_note = "Repository cloning failed; proceeding without repository context."
                logger.warning(
                    "Repository cloning failed for url=%s: %s (%s)",
                    _redact_repo_url(repo_url),
                    type(e).__name__,
                    _redact_text(str(e)),
                )
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

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(file): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary or ""
        if warning_note:
            summary_text = f"Note: {warning_note}\n\n{summary_text}"

        return AnalysisResponse(
            insights=analysis.insights, summary=summary_text, recommendations=analysis.recommendations
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Analyze(file) failed: %s", _redact_text(str(e)))
        raise HTTPException(status_code=500, detail="File analysis failed.")


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
        _validate_repo_limits(repo_max_files, repo_max_bytes)
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

        # Truncate combined text if too large to protect model and server
        if combined_text:
            combined_text, was_truncated = _truncate_text_safely(combined_text)
            if was_truncated:
                logger.warning("Jenkins analysis content was truncated due to size limits")

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
            context_parts.append(f"Repository: {_redact_repo_url(repo_url)}")
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
                warning_note = "Repository cloning failed; proceeding without repository context."
                logger.warning(
                    "Repository cloning failed for url=%s: %s (%s)",
                    _redact_repo_url(repo_url),
                    type(e).__name__,
                    _redact_text(str(e)),
                )
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

        # Add cloned path to request object for AI analyzer
        if cloned_repo_path:
            request.cloned_repo_path = cloned_repo_path
        analysis = ai_analyzer.analyze_test_results(request)
        logger.info(
            "Analyze(jenkins): results insights=%d recommendations=%d summary_len=%d",
            len(analysis.insights),
            len(analysis.recommendations),
            len(analysis.summary or ""),
        )

        summary_text = analysis.summary or ""
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
        logger.exception(
            "Analyze(jenkins) failed job=%s build=%s: %s",
            job_name,
            build_label,
            _redact_text(str(e)),
        )
        raise HTTPException(
            status_code=500,
            detail=f"Jenkins analysis failed for job {job_name}, build {build_label}.",
        )
