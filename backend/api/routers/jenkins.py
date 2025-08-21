"""Jenkins management endpoints for TestInsight AI."""

from typing import Any

from fastapi import APIRouter, HTTPException

from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/jenkins", tags=["jenkins"])


@router.get("/jobs")
async def get_jenkins_jobs(
    search: str | None = None,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Get list of Jenkins jobs with optional search.

    Args:
        search: Optional search query for fuzzy matching
        url: Jenkins URL (uses settings if not provided)
        username: Jenkins username (uses settings if not provided)
        password: Jenkins API token (uses settings if not provided)
        verify_ssl: Verify SSL (uses settings if not provided)

    Returns:
        List of Jenkins jobs
    """
    try:
        client_creators = ServiceClientCreators()

        try:
            jenkins_client = client_creators.create_configured_jenkins_client(
                url=url, username=username, password=password, verify_ssl=verify_ssl
            )
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))

        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Jenkins client connection failed. Please check your Jenkins settings."
            )

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


@router.get("/{job_name}/builds")
async def get_job_builds(
    job_name: str,
    limit: int = 10,
    url: str | None = None,
    username: str | None = None,
    password: str | None = None,
    verify_ssl: bool | None = None,
) -> dict[str, Any]:
    """Get recent builds for a Jenkins job.

    Args:
        job_name: Jenkins job name
        limit: Maximum number of builds to return

    Returns:
        List of recent builds
    """
    try:
        client_creators = ServiceClientCreators()

        try:
            jenkins_client = client_creators.create_configured_jenkins_client(
                url=url, username=username, password=password, verify_ssl=verify_ssl
            )
        except ValueError as e:
            raise HTTPException(status_code=503, detail=str(e))

        if not jenkins_client or not jenkins_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Jenkins client connection failed. Please check your Jenkins settings."
            )

        builds = jenkins_client.get_job_builds(job_name, limit)

        return {"job_name": job_name, "builds": builds, "total": len(builds), "limit": limit}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job builds: {str(e)}")
