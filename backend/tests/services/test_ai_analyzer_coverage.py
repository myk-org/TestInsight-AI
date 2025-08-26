"""Tests for AI analyzer service coverage."""

from pathlib import Path
from unittest.mock import Mock, patch, mock_open

import pytest

from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient


def test_extract_relevant_repository_files():
    """Test _extract_relevant_repository_files method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    with patch("backend.services.ai_analyzer.AIAnalyzer._find_file_in_repo") as mock_find:
        # Create a mock file path that properly handles the chained method calls
        mock_file_path = Mock()
        mock_file_path.exists.return_value = True
        mock_file_path.is_file.return_value = True

        # Mock the file.open() context manager correctly
        mock_open_context = mock_open(read_data=b"content")
        mock_file_path.open = mock_open_context

        # Mock the chained resolve().relative_to() call
        mock_file_path.resolve.return_value.relative_to.return_value = Path("test_file.py")

        mock_find.return_value = mock_file_path

        files = analyzer._extract_relevant_repository_files(
            repo_path=Path("/tmp/repo"), failure_text="test_file.py::test_function", max_files=5, max_file_bytes=51200
        )
        assert len(files) >= 1
        assert files[0][0] == "test_file.py"
        assert files[0][1] == "content"


def test_find_file_in_repo():
    """Test _find_file_in_repo method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    with patch("pathlib.Path.rglob") as mock_rglob:
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.parts = ["tmp", "repo", "test_file.py"]
        mock_rglob.return_value = [mock_file]
        result = analyzer._find_file_in_repo(Path("/tmp/repo"), "test_file.py")
        assert result == mock_file


def test_clean_content():
    """Test _clean_content method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test cleaning content with various whitespace and newlines
    messy_content = "\n\n  Some content with extra whitespace  \n\n\n"
    result = analyzer._clean_content(messy_content)
    assert result == "Some content with extra whitespace"

    # Test empty content
    result = analyzer._clean_content("")
    assert result == ""

    # Test already clean content
    clean_content = "Clean content"
    result = analyzer._clean_content(clean_content)
    assert result == "Clean content"


def test_fallback_recommendations():
    """Test _fallback_recommendations method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Create mock insights
    mock_insight = Mock()
    mock_insight.title = "Test Issue"
    mock_insight.description = "A test issue description"
    mock_insight.severity = "medium"

    insights = [mock_insight]
    raw_content = "Some raw analysis content"

    result = analyzer._fallback_recommendations(insights, raw_content)

    # Should return a list of recommendations
    assert isinstance(result, list)
    assert len(result) >= 1
    # Should contain information from the insight
    assert any("Test Issue" in rec for rec in result)


def test_format_insights_for_prompt():
    """Test _format_insights_for_prompt method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Create mock insights with enum-like severity
    mock_severity1 = Mock()
    mock_severity1.value = "high"
    mock_severity2 = Mock()
    mock_severity2.value = "medium"

    mock_insight1 = Mock()
    mock_insight1.title = "Issue 1"
    mock_insight1.description = "Description 1"
    mock_insight1.severity = mock_severity1

    mock_insight2 = Mock()
    mock_insight2.title = "Issue 2"
    mock_insight2.description = "Description 2"
    mock_insight2.severity = mock_severity2

    insights = [mock_insight1, mock_insight2]

    result = analyzer._format_insights_for_prompt(insights)

    # Should contain both insights with severity values
    assert "Issue 1 (high)" in result
    assert "Issue 2 (medium)" in result

    # Test empty insights
    result = analyzer._format_insights_for_prompt([])
    assert result == "No insights available"


def test_parse_json_response():
    """Test _parse_json_response method."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test valid JSON array
    json_content = """[
        {"title": "Test Issue", "description": "Test description", "severity": "medium"},
        {"title": "Another Issue", "description": "Another description", "severity": "high"}
    ]"""

    result = analyzer._parse_json_response(json_content)
    assert len(result) == 2
    assert result[0]["title"] == "Test Issue"
    assert result[1]["severity"] == "high"

    # Test invalid JSON - should raise ValueError
    invalid_json = "not valid json"
    with pytest.raises(ValueError, match="AI returned unparseable JSON content"):
        analyzer._parse_json_response(invalid_json)
