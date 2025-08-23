"""Git client service for repository operations."""

import tempfile
from urllib.parse import urlparse, urlunparse, quote
from pathlib import Path

from git import Repo


class GitRepositoryError(Exception):
    """Exception raised for git repository errors."""

    pass


class GitClient:
    """Simple Git client for cloning repositories and accessing file content."""

    def __init__(
        self, repo_url: str, branch: str | None = None, commit: str | None = None, github_token: str | None = None
    ):
        """Initialize Git client by cloning repository.

        Args:
            repo_url: Repository URL (required)
            branch: Branch name (required if commit not provided)
            commit: Commit hash (required if branch not provided)
            github_token: GitHub token for private repository access

        Raises:
            GitRepositoryError: If validation fails or cloning fails
            ValueError: If neither branch nor commit provided
        """
        if branch and commit:
            raise ValueError("Provide either branch or commit, not both")

        self.repo_url = repo_url
        self.github_token = github_token
        # Keep original URL public; compute authenticated URL for internal use
        self._authenticated_repo_url = self._authenticate_url() if self.github_token else self.repo_url
        self.branch = branch
        self.commit = commit

        # GitHub token should be provided by ServiceConfig.create_configured_git_client()
        # Don't fetch from settings here - this class should be dumb

        # Clone repository to temporary directory
        self.repo_path = Path(self._clone_repository())

        # Initialize repo object (cloning guarantees this will work)
        self._repo = Repo(self.repo_path)

    def _clone_repository(self) -> str:
        """Clone the repository to a temporary directory.

        Returns:
            Path to cloned repository
        """
        # Create temporary directory
        target_path = tempfile.mkdtemp(prefix="testinsight_ai_repo_")

        # Clone repository using GitPython (shallow by default)
        # Clone logic: full clone for specific commit; shallow clone for branch/default
        if self.commit:
            cloned_repo = Repo.clone_from(self._authenticated_repo_url, target_path)
            cloned_repo.git.fetch("origin", self.commit)
            cloned_repo.git.checkout(self.commit)
        else:
            cloned_repo = Repo.clone_from(self._authenticated_repo_url, target_path, depth=1)
            if self.branch:
                cloned_repo.git.checkout(self.branch)

        return target_path

    def _authenticate_url(self) -> str:
        """Add authentication to repository URL.

        Args:
            repo_url: Original repository URL

        Returns:
            Authenticated URL
        """
        parsed = urlparse(self.repo_url)
        # Only embed auth for http(s) schemes with a hostname
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return self.repo_url

        # For GitHub, prefer x-access-token user with token as password; URL-encode token
        if parsed.hostname.lower().endswith("github.com"):
            encoded = quote(self.github_token or "", safe="")
            netloc = f"x-access-token:{encoded}@{parsed.hostname}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))

        # For other providers, do not embed token (avoid unsafe patterns); return original URL
        return self.repo_url


# Debug code removed for security
