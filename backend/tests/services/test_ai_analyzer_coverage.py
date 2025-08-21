"""Tests for AI analyzer service coverage."""

from pathlib import Path
from unittest.mock import Mock, patch

from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient


def test_extract_relevant_repository_files():
    """Test _extract_relevant_repository_files method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    with patch("pathlib.Path.rglob") as mock_rglob:
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.parts = ["tmp", "repo", "test_file.py"]
        mock_file.relative_to.return_value = "test_file.py"
        mock_rglob.return_value = [mock_file]
        with patch("pathlib.Path.read_text", return_value="content"):
            files = analyzer._extract_relevant_repository_files(
                repo_path=Path("/tmp/repo"),
                failure_text="test_file.py::test_function",
            )
            assert len(files) >= 1
            assert files[0][0] == "test_file.py"


def test_find_file_in_repo():
    """Test _find_file_in_repo method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    with patch("pathlib.Path.rglob") as mock_rglob:
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.parts = ["tmp", "repo", "test_file.py"]
        mock_file.name = "test_file.py"
        mock_rglob.return_value = [mock_file]
        file_path = analyzer._find_file_in_repo(
            repo_path=Path("/tmp/repo"),
            filename="test_file.py",
        )
        assert file_path is not None
        assert file_path.name == "test_file.py"
