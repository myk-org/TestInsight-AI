"""Settings management endpoints for TestInsight AI."""

import json
from datetime import datetime
from io import BytesIO
from typing import Generator

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from backend.models.schemas import (
    AppSettings,
    ConnectionTestResult,
    SettingsUpdate,
    TestConnectionWithParamsRequest,
)
from backend.services.service_config.connection_testers import ServiceConnectionTesters
from backend.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
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


@router.put("", response_model=AppSettings)
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


@router.post("/reset", response_model=AppSettings)
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


@router.get("/validate")
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


@router.get("/secrets-status")
async def get_secrets_status() -> dict[str, dict[str, bool]]:
    """Get status of whether secrets are configured.

    Returns:
        Dictionary indicating which secrets are set
    """
    try:
        settings_service = SettingsService()
        return settings_service.get_secret_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get secrets status: {str(e)}")


@router.post("/test-connection", response_model=ConnectionTestResult)
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
        service_config = ServiceConnectionTesters()

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
                service_config.test_ai_connection()
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


@router.post("/test-connection-with-config", response_model=ConnectionTestResult)
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
        service_config = ServiceConnectionTesters()

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
                service_config.test_ai_connection()
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


@router.get("/backup")
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

        def generate() -> Generator[bytes, None, None]:
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


@router.post("/restore")
async def restore_settings(backup_file: UploadFile = File(...)) -> AppSettings:
    """Restore settings from uploaded backup file.

    Args:
        backup_file: Uploaded JSON backup file

    Returns:
        Restored settings with sensitive data masked
    """
    try:
        # Validate extension is .json for safety and predictable UX
        filename = getattr(backup_file, "filename")
        if not filename.endswith(".json"):
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
