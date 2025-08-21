"""Git operations endpoints for TestInsight AI."""

from typing import Any

from fastapi import APIRouter, Form, HTTPException

from backend.services.git_client import GitRepositoryError
from backend.services.service_config.client_creators import ServiceClientCreators

router = APIRouter(prefix="/git", tags=["git"])


@router.post("/clone", response_model=dict[str, Any])
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

        # Create GitClient using ServiceClientCreators factory method
        client_creators = ServiceClientCreators()
        git_client = client_creators.create_configured_git_client(
            repo_url=repo_url, branch=branch, commit=commit, github_token=github_token
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
