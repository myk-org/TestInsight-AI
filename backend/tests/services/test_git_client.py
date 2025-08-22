"""Tests for Git client service."""

from pathlib import Path
from unittest.mock import Mock, patch
import pytest

from backend.services.git_client import GitClient
from backend.tests.conftest import FAKE_COMMIT_HASH


class TestGitClient:
    """Test cases for GitClient class."""

    def test_init_with_branch(self):
        """Test GitClient initialization with branch parameter."""
        fake_repo_path = "/tmp/fake_repo_123"

        with (
            patch("backend.services.git_client.tempfile.mkdtemp", return_value=fake_repo_path),
            patch("backend.services.git_client.Repo") as mock_repo_class,
        ):
            # Set up mock instances
            mock_cloned_repo = Mock()
            mock_repo_instance = Mock()
            mock_repo_class.return_value = mock_repo_instance

            # Set up clone_from as a classmethod that returns the cloned repo
            mock_clone = Mock(return_value=mock_cloned_repo)
            mock_repo_class.clone_from = mock_clone

            client = GitClient(repo_url="https://github.com/testorg/testrepo", branch="main")

            assert client.repo_url == "https://github.com/testorg/testrepo"
            assert client.branch == "main"
            assert client.commit is None
            assert client.github_token is None
            assert client.repo_path == Path(fake_repo_path)

            mock_clone.assert_called_once_with("https://github.com/testorg/testrepo", fake_repo_path, depth=1)
            mock_cloned_repo.git.checkout.assert_called_once_with("main")
            mock_repo_class.assert_called_once_with(Path(fake_repo_path))

    def test_init_with_commit(self):
        """Test GitClient initialization with commit parameter."""
        fake_repo_path = "/tmp/fake_repo_123"

        with (
            patch("backend.services.git_client.tempfile.mkdtemp", return_value=fake_repo_path),
            patch("backend.services.git_client.Repo") as mock_repo_class,
        ):
            # Set up mock instances
            mock_cloned_repo = Mock()
            mock_repo_instance = Mock()
            mock_repo_class.return_value = mock_repo_instance

            # Set up clone_from as a classmethod that returns the cloned repo
            mock_clone = Mock(return_value=mock_cloned_repo)
            mock_repo_class.clone_from = mock_clone

            client = GitClient(
                repo_url="https://github.com/testorg/testrepo",
                commit=FAKE_COMMIT_HASH,
            )

            assert client.repo_url == "https://github.com/testorg/testrepo"
            assert client.branch is None
            assert client.commit == FAKE_COMMIT_HASH
            assert client.github_token is None

            mock_cloned_repo.git.checkout.assert_called_once_with(FAKE_COMMIT_HASH)
            mock_repo_class.assert_called_once_with(Path(fake_repo_path))

    def test_init_with_github_token(self):
        """Test GitClient initialization with GitHub token parameter."""
        fake_repo_path = "/tmp/fake_repo_123"

        with (
            patch("backend.services.git_client.tempfile.mkdtemp", return_value=fake_repo_path),
            patch("backend.services.git_client.Repo") as mock_repo_class,
        ):
            # Set up mock instances
            mock_cloned_repo = Mock()
            mock_repo_instance = Mock()
            mock_repo_class.return_value = mock_repo_instance

            # Set up clone_from as a classmethod that returns the cloned repo
            mock_clone = Mock(return_value=mock_cloned_repo)
            mock_repo_class.clone_from = mock_clone

            client = GitClient(
                repo_url="https://github.com/testorg/testrepo",
                branch="main",
                github_token="fake_github_token_xyz",  # pragma: allowlist secret
            )

            assert (
                client.github_token == "fake_github_token_xyz"
            )  # pragma: allowlist secret  # pragma: allowlist secret
            # URL should be authenticated
            expected_url = (
                "https://x-access-token:fake_github_token_xyz@github.com/testorg/testrepo"  # pragma: allowlist secret
            )
            mock_clone.assert_called_once_with(expected_url, fake_repo_path, depth=1)
            mock_repo_class.assert_called_once_with(Path(fake_repo_path))

    def test_init_validation_error(self):
        """Test GitClient raises ValueError when both branch and commit provided."""
        with pytest.raises(ValueError, match="Provide either branch or commit, not both"):
            GitClient(
                repo_url="https://github.com/testorg/testrepo",
                branch="main",
                commit=FAKE_COMMIT_HASH,
            )

    def test_authenticate_url(self):
        """Test URL authentication with GitHub token."""
        fake_repo_path = "/tmp/fake_repo_123"

        with (
            patch("backend.services.git_client.tempfile.mkdtemp", return_value=fake_repo_path),
            patch("backend.services.git_client.Repo") as mock_repo_class,
        ):
            # Set up mock instances
            mock_cloned_repo = Mock()
            mock_repo_instance = Mock()
            mock_repo_class.return_value = mock_repo_instance

            # Set up clone_from as a classmethod that returns the cloned repo
            mock_clone = Mock(return_value=mock_cloned_repo)
            mock_repo_class.clone_from = mock_clone

            client = GitClient(
                repo_url="https://github.com/testorg/testrepo",
                branch="main",
                github_token="fake_github_token_xyz",  # pragma: allowlist secret
            )

            expected_url = (
                "https://x-access-token:fake_github_token_xyz@github.com/testorg/testrepo"  # pragma: allowlist secret
            )
            mock_clone.assert_called_once_with(expected_url, fake_repo_path, depth=1)

            # repo_url gets modified to authenticated URL when github_token is provided
            assert (
                client.repo_url == "https://x-access-token:fake_github_token_xyz@github.com/testorg/testrepo"
            )  # pragma: allowlist secret
            assert client.branch == "main"
            assert client.github_token == "fake_github_token_xyz"  # pragma: allowlist secret
