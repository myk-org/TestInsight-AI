"""API endpoints for TestInsight AI."""

import json
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AppSettings,
    ConnectionTestResult,
    GeminiModelsRequest,
    GeminiModelsResponse,
    SettingsUpdate,
    TestConnectionWithParamsRequest,
)
from backend.services.gemini_api import GeminiClient
from backend.services.git_client import GitRepositoryError
from backend.services.service_config import ServiceConfig
from backend.services.settings_service import SettingsService

router = APIRouter()

# Services will be created on-demand using current settings


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze(
    text: str = Form(..., description="Text content to analyze (logs, junit xml, etc.)"),
    custom_context: str | None = Form(None, description="Additional context"),
) -> AnalysisResponse:
    """Analyze text content with AI.

    Args:
        text: Text content to analyze (can be logs, JUnit XML, console output, etc.)
        custom_context: Optional additional context

    Returns:
        AI analysis results with insights, summary, and recommendations
    """
    try:
        service_config = ServiceConfig()
        ai_analyzer = service_config.create_configured_ai_client()
        if not ai_analyzer:
            raise HTTPException(status_code=503, detail="AI analyzer not configured")

        request = AnalysisRequest(text=text, custom_context=custom_context)

        analysis = ai_analyzer.analyze_test_results(request)

        return AnalysisResponse(
            insights=analysis.insights, summary=analysis.summary, recommendations=analysis.recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/jenkins/jobs")
async def get_jenkins_jobs(search: str | None = None) -> dict[str, Any]:
    """Get list of Jenkins jobs with optional search.

    Args:
        search: Optional search query for fuzzy matching

    Returns:
        List of Jenkins jobs
    """
    try:
        service_config = ServiceConfig()
        jenkins_client = service_config.create_configured_jenkins_client()
        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(status_code=503, detail="Jenkins client not configured or unavailable")

        if search:
            jobs = jenkins_client.search_jobs(search)
        else:
            jobs = jenkins_client.list_jobs()

        # Extract just the names for dropdown
        job_names = [job.get("name", "") for job in jobs if job.get("name")]

        return {"jobs": job_names, "total": len(job_names), "search_query": search}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Jenkins jobs: {str(e)}")


@router.get("/jenkins/{job_name}/builds")
async def get_job_builds(job_name: str, limit: int = 10) -> dict[str, Any]:
    """Get recent builds for a Jenkins job.

    Args:
        job_name: Jenkins job name
        limit: Maximum number of builds to return

    Returns:
        List of recent builds
    """
    try:
        service_config = ServiceConfig()
        jenkins_client = service_config.create_configured_jenkins_client()
        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(status_code=503, detail="Jenkins client not configured or unavailable")

        builds = jenkins_client.get_job_builds(job_name, limit)

        return {"job_name": job_name, "builds": builds, "total": len(builds), "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job builds: {str(e)}")


@router.get("/jenkins/{job_name}/{build_number}/console")
async def get_build_console(job_name: str, build_number: int) -> dict[str, str]:
    """Get console output from Jenkins build.

    Args:
        job_name: Jenkins job name
        build_number: Build number

    Returns:
        Console output
    """
    try:
        service_config = ServiceConfig()
        jenkins_client = service_config.create_configured_jenkins_client()
        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(status_code=503, detail="Jenkins client not configured or unavailable")

        console_output = jenkins_client.get_console_output(job_name, build_number)
        if console_output is None:
            raise HTTPException(status_code=404, detail=f"Console output not found for build {build_number}")

        return {"console_output": console_output}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get console output: {str(e)}")


@router.post("/git/clone", response_model=dict[str, Any])
async def clone_repository(
    repo_url: str = Form(..., description="Repository URL"),
    branch: str | None = Form(None, description="Branch name"),
    commit: str | None = Form(None, description="Commit hash"),
    github_token: str | None = Form(None, description="GitHub token for authentication"),
) -> dict[str, Any]:
    """Clone a repository with specific branch or commit.

    Args:
        repo_url: Repository URL
        branch: Branch name (optional)
        commit: Commit hash (optional)

    Returns:
        Clone operation result with repository path
    """
    try:
        # Validate: either branch OR commit, not both
        if branch and commit:
            raise HTTPException(status_code=400, detail="Provide either branch or commit, not both")

        # Create GitClient using ServiceConfig factory method
        service_config = ServiceConfig()
        git_client = service_config.create_configured_git_client(
            repo_url, branch=branch, commit=commit, github_token=github_token
        )

        return {
            "success": True,
            "repository_url": repo_url,
            "commit_hash": commit,
            "branch": branch,
            "cloned_path": str(git_client.repo_path),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GitRepositoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clone failed: {str(e)}")


@router.post("/git/file-content")
async def get_file_content(
    file_path: str = Form(..., description="Path to file in repository"),
    cloned_path: str = Form(..., description="Path to already cloned repository"),
) -> dict[str, str]:
    """Get file content from a git repository using existing cloned repository path.

    Args:
        file_path: Path to file in repository
        cloned_path: Path to already cloned repository (from /git/clone response)

    Returns:
        File content
    """
    try:
        cloned_repo_path = Path(cloned_path)
        if not cloned_repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Cloned repository path not found: {cloned_path}")

        file_full_path = cloned_repo_path / file_path
        if not file_full_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

        content = file_full_path.read_text(encoding="utf-8")

        return {
            "file_path": file_path,
            "content": content,
            "cloned_path": cloned_path,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GitRepositoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file content: {str(e)}")


@router.get("/status")
async def get_service_status() -> dict[str, Any]:
    """Get status of all services.

    Returns:
        Service status information
    """
    service_config = ServiceConfig()
    config_status = service_config.get_service_status()

    # Test actual connections
    jenkins_available = False
    jenkins_url = "Not configured"
    try:
        jenkins = service_config.create_configured_jenkins_client()
        if jenkins:
            jenkins_available = jenkins.is_connected()
            jenkins_url = jenkins.url or "Not configured"
    except Exception:
        pass

    ai_available = False
    try:
        service_config.create_configured_ai_client()
        ai_available = True
    except Exception:
        pass

    return {
        "services": {
            "jenkins": {
                "configured": config_status["jenkins"]["configured"],
                "available": jenkins_available,
                "url": jenkins_url,
            },
            "git": {
                "configured": config_status["github"]["configured"],
            },
            "ai_analyzer": {
                "configured": config_status["ai"]["configured"],
                "available": ai_available,
                "provider": "Google Gemini",
            },
        },
        "settings": {
            "encryption_enabled": True,
            "last_updated": service_config.get_settings().last_updated,
        },
    }


# AI Models endpoints


@router.post("/ai/models", response_model=GeminiModelsResponse)
async def get_gemini_models(request: GeminiModelsRequest) -> GeminiModelsResponse:
    """Fetch available Gemini models using the provided API key.

    This endpoint allows users to dynamically fetch the list of available
    Gemini models from Google's AI API using their API key. This replaces
    the need for hardcoded model names in the frontend.

    Args:
        request: Request containing the Gemini API key

    Returns:
        GeminiModelsResponse with available models or error information

    Raises:
        HTTPException: For various error conditions with appropriate status codes
    """
    try:
        gemini_client = GeminiClient(api_key=request.api_key)

        # Fetch models using the client
        response = gemini_client.get_available_models()

        # Return appropriate HTTP status based on success
        if not response.success:
            if response.error_details and response.message:
                # Determine appropriate HTTP status code based on error type
                if "Invalid API key" in response.error_details or "Authentication failed" in response.message:
                    raise HTTPException(status_code=401, detail=response.error_details or response.message)
                elif "Permission denied" in response.message:
                    raise HTTPException(status_code=403, detail=response.error_details or response.message)
                elif "quota exceeded" in response.message.lower():
                    raise HTTPException(status_code=429, detail=response.error_details or response.message)
                elif "Invalid input" in response.message:
                    raise HTTPException(status_code=400, detail=response.error_details or response.message)
            else:
                # Generic server error for other cases
                raise HTTPException(status_code=500, detail=response.error_details or response.message)

        return response

    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to fetch Gemini models: {str(e)}")


@router.post("/ai/models/validate-key")
async def validate_gemini_api_key(request: GeminiModelsRequest) -> dict[str, Any]:
    """Validate a Gemini API key without fetching models.

    This endpoint provides a lightweight way to validate an API key
    without the overhead of fetching the full models list.

    Args:
        request: Request containing the Gemini API key to validate

    Returns:
        Dictionary with validation result and connection test information
    """
    try:
        gemini_client = GeminiClient(api_key=request.api_key)

        # Test the API key connection
        is_valid = gemini_client.validate_api_key()

        if is_valid:
            return {
                "valid": True,
                "message": "API key is valid and connection successful",
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid API key or connection failed")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API key validation failed: {str(e)}")


# Settings endpoints


@router.get("/settings", response_model=AppSettings)
async def get_settings() -> AppSettings:
    """Get current application settings with sensitive data masked.

    Returns:
        Current application settings
    """
    try:
        settings_service = SettingsService()
        return settings_service.get_masked_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve settings: {str(e)}")


@router.put("/settings", response_model=AppSettings)
async def update_settings(settings_update: SettingsUpdate) -> AppSettings:
    """Update application settings.

    Args:
        settings_update: Settings to update

    Returns:
        Updated settings with sensitive data masked
    """
    try:
        settings_service = SettingsService()

        # Update settings (validation is handled within the service)
        settings_service.update_settings(settings_update)
        return settings_service.get_masked_settings()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.post("/settings/reset", response_model=AppSettings)
async def reset_settings() -> AppSettings:
    """Reset settings to defaults.

    Returns:
        Default settings
    """
    try:
        settings_service = SettingsService()
        settings_service.reset_settings()
        return settings_service.get_masked_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset settings: {str(e)}")


@router.get("/settings/validate")
async def validate_settings() -> dict[str, list[str]]:
    """Validate current settings.

    Returns:
        Dictionary with validation errors by section
    """
    try:
        settings_service = SettingsService()
        return settings_service.validate_settings()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate settings: {str(e)}")


@router.post("/settings/test-connection", response_model=ConnectionTestResult)
async def test_service_connection(service: str) -> ConnectionTestResult:
    """Test connection to a configured service.

    Args:
        service: Service to test (jenkins, github, or ai)

    Returns:
        Connection test result
    """
    try:
        settings_service = SettingsService()
        settings = settings_service.get_settings()
        service_config = ServiceConfig()

        if service == "jenkins":
            try:
                service_config.test_jenkins_connection(
                    url=settings.jenkins.url or "",
                    username=settings.jenkins.username or "",
                    password=settings.jenkins.api_token or "",
                    verify_ssl=settings.jenkins.verify_ssl,
                )
                return ConnectionTestResult(
                    service="jenkins",
                    success=True,
                    message="Jenkins connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="jenkins",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        elif service == "github":
            try:
                service_config.test_github_connection(token=settings.github.token or "")
                return ConnectionTestResult(
                    service="github",
                    success=True,
                    message="GitHub connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="github",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        elif service == "ai":
            try:
                service_config.test_ai_connection(
                    api_key=settings.ai.gemini_api_key or "",
                )
                return ConnectionTestResult(
                    service="ai",
                    success=True,
                    message="AI service connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="ai",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown service: {service}. Supported services: jenkins, github, ai"
            )

    except HTTPException:
        raise
    except Exception as e:
        return ConnectionTestResult(
            service=service, success=False, message="Connection test failed", error_details=str(e)
        )


@router.post("/settings/test-connection-with-config", response_model=ConnectionTestResult)
async def test_service_connection_with_config(request: TestConnectionWithParamsRequest) -> ConnectionTestResult:
    """Test connection to a service using custom parameters instead of saved settings.

    Args:
        request: Request containing service name and configuration parameters

    Returns:
        Connection test result
    """
    try:
        service = request.service.lower()
        config = request.config
        service_config = ServiceConfig()

        if service == "jenkins":
            try:
                service_config.test_jenkins_connection(
                    url=config.get("url", ""),
                    username=config.get("username", ""),
                    password=config.get("api_token", ""),
                    verify_ssl=config.get("verify_ssl", True),
                )
                return ConnectionTestResult(
                    service="jenkins",
                    success=True,
                    message="Jenkins connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="jenkins",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        elif service == "github":
            try:
                service_config.test_github_connection(token=config.get("token", ""))
                return ConnectionTestResult(
                    service="github",
                    success=True,
                    message="GitHub connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="github",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        elif service == "ai":
            try:
                service_config.test_ai_connection(
                    api_key=config.get("gemini_api_key", ""),
                )
                return ConnectionTestResult(
                    service="ai",
                    success=True,
                    message="AI service connection successful",
                    error_details="",
                )
            except (ConnectionError, ValueError) as e:
                return ConnectionTestResult(
                    service="ai",
                    success=False,
                    message=str(e),
                    error_details=str(e),
                )

        else:
            raise HTTPException(
                status_code=400, detail=f"Unknown service: {service}. Supported services: jenkins, github, ai"
            )

    except HTTPException:
        raise
    except Exception as e:
        return ConnectionTestResult(
            service=request.service, success=False, message="Connection test failed", error_details=str(e)
        )


@router.get("/settings/backup")
async def backup_settings() -> StreamingResponse:
    """Create a backup of current settings and download as JSON file.

    Returns:
        StreamingResponse with JSON file download
    """
    try:
        settings_service = SettingsService()
        settings = settings_service.get_settings()

        # Create JSON content for download
        settings_json = json.dumps(settings.model_dump(mode="json"), indent=2, ensure_ascii=False, default=str)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"testinsight_settings_backup_{timestamp}.json"

        # Convert to bytes for proper streaming
        json_bytes = settings_json.encode("utf-8")
        json_stream = BytesIO(json_bytes)

        def generate() -> Any:
            json_stream.seek(0)
            while True:
                chunk = json_stream.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                yield chunk

        return StreamingResponse(
            generate(),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename}", "Content-Type": "application/json"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create backup: {str(e)}")


@router.post("/settings/restore")
async def restore_settings(backup_file: UploadFile = File(...)) -> AppSettings:
    """Restore settings from uploaded backup file.

    Args:
        backup_file: Uploaded JSON backup file

    Returns:
        Restored settings with sensitive data masked
    """
    try:
        # Validate file type
        filename = getattr(backup_file, "filename")

        if filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Backup file must be a JSON file")

        # Read and parse the uploaded file
        content = await backup_file.read()

        try:
            # Decode content and parse JSON
            json_content = content.decode("utf-8")
            backup_data = json.loads(json_content)
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File encoding error. Please ensure the file is UTF-8 encoded.")
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON format: {str(e)}")

        # Validate backup data structure by trying to create AppSettings object
        try:
            validated_settings = AppSettings(**backup_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid settings format: {str(e)}")

        # Restore settings using the service
        settings_service = SettingsService()
        settings_service._save_settings(validated_settings)
        settings_service._current_settings = validated_settings

        return settings_service.get_masked_settings()

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restore settings: {str(e)}")
