"""System status endpoints for TestInsight AI."""

import logging
import os
from typing import Any

from fastapi import APIRouter

from backend.services.service_config.status_checkers import ServiceStatusCheckers
from backend.services.service_config.client_creators import ServiceClientCreators
from backend.services.service_config.base import BaseServiceConfig

router = APIRouter(prefix="/status", tags=["system"])


@router.get("")
async def get_service_status() -> dict[str, Any]:
    """Get status of all services.

    Returns:
        Service status information
    """
    status_checkers = ServiceStatusCheckers()
    client_creators = ServiceClientCreators()
    base_config = BaseServiceConfig()
    config_status = status_checkers.get_service_status()

    # Test actual connections
    jenkins_available = False
    jenkins_url = "Not configured"
    try:
        jenkins = client_creators.create_configured_jenkins_client()
        if jenkins:
            jenkins_available = jenkins.is_connected()
            jenkins_url = jenkins.url or "Not configured"
    except Exception as e:
        logging.getLogger("testinsight").warning("Jenkins status check failed: %s", e)

    ai_available = False
    try:
        client_creators.create_configured_ai_client()
        ai_available = True
    except Exception as e:
        logging.getLogger("testinsight").warning("AI status check failed: %s", e)

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
            "last_updated": base_config.get_settings().last_updated,
        },
        # Keep app section minimal; read version from env with sensible default
        "app": {
            "version": os.getenv("APP_VERSION", "0.1.0"),
        },
    }
