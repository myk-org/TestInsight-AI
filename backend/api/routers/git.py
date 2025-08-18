"""Git operations endpoints for TestInsight AI."""

from pathlib import Path
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


@router.post("/file-content")
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
