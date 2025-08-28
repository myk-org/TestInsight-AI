"""Tests for AI analyzer service coverage."""

from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch

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

        # Mock the file.open() context manager with simplified approach
        mock_file_path.open.return_value.__enter__ = Mock(return_value=BytesIO(b"content"))
        mock_file_path.open.return_value.__exit__ = Mock(return_value=None)

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
        # Create a mock file path
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.parts = ("tmp", "repo", "tests", "test_file.py")

        # Mock the relative_to method to return a mock path with parts attribute
        mock_relative_path = Mock()
        mock_relative_path.parts = ("tests", "test_file.py")  # 2 parts, less than max_depth of 8
        mock_file.relative_to.return_value = mock_relative_path

        mock_rglob.return_value = [mock_file]
        result = analyzer._find_file_in_repo(Path("/tmp/repo"), "test_file.py")
        assert result == mock_file
        # Verify relative_to was called to check depth (guards the depth check path)
        mock_file.relative_to.assert_called_once()


def test_find_file_in_repo_priority_directory_fast_path():
    """Test _find_file_in_repo priority directory fast-path behavior."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Mock the priority directory path to exist and be a directory
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch("pathlib.Path.is_dir") as mock_is_dir,
        patch("pathlib.Path.rglob") as mock_rglob,
    ):
        # Set up priority directory to exist and be a directory
        mock_exists.return_value = True
        mock_is_dir.return_value = True

        # Create a mock file found in priority directory
        mock_file = Mock()
        mock_file.is_file.return_value = True
        mock_file.parts = ("tmp", "repo", "tests", "test_file.py")

        # Mock rglob to return our file
        mock_rglob.return_value = [mock_file]

        result = analyzer._find_file_in_repo(Path("/tmp/repo"), "test_file.py")
        assert result == mock_file

        # Verify that the priority path was checked
        mock_exists.assert_called()
        mock_is_dir.assert_called()
        mock_rglob.assert_called_with("test_file.py")


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


@pytest.mark.parametrize(
    "content,expected",
    [
        # Test markdown fence removal - JSON with language tag
        (
            """```json
{"title": "Test", "description": "Test description"}
```""",
            '{"title": "Test", "description": "Test description"}',
        ),
        # Test markdown fence removal - uppercase JSON
        (
            """```JSON
{"title": "Test", "description": "Test description"}
```""",
            '{"title": "Test", "description": "Test description"}',
        ),
        # Test markdown fence removal - no language tag
        (
            """```
{"title": "Test", "description": "Test description"}
```""",
            '{"title": "Test", "description": "Test description"}',
        ),
        # Test markdown fence removal - with whitespace
        (
            """   ```json
   {"title": "Test", "description": "Test description"}
   ```   """,
            '{"title": "Test", "description": "Test description"}',
        ),
        # Test content without fences (should only trim whitespace)
        ("   Some regular content   ", "Some regular content"),
    ],
)
def test_clean_content_fence_removal(content, expected):
    """Test _clean_content method fence removal according to contract."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)
    result = analyzer._clean_content(content)
    assert result == expected


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


def test_fallback_recommendations_formatting():
    """Test _fallback_recommendations method formatting with category and severity."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Create mock insights with proper attributes for fallback formatting
    mock_severity = Mock()
    mock_severity.value = "high"

    mock_insight = Mock()
    mock_insight.title = "Database Connection Error"
    mock_insight.category = "Infrastructure"
    mock_insight.severity = mock_severity

    insights = [mock_insight]
    raw_content = "Some raw analysis content"

    result = analyzer._fallback_recommendations(insights, raw_content)

    # Should return a list with formatted recommendation
    assert isinstance(result, list)
    assert len(result) == 1

    # Verify proper formatting includes title, category, and severity
    recommendation = result[0]
    assert "Focus: Database Connection Error" in recommendation
    assert "infrastructure" in recommendation.lower()  # category is lowercased
    assert "high" in recommendation.lower()  # severity value is lowercased
    assert "—" in recommendation  # formatting separator

    # Test fallback with no insights returns raw content
    result_no_insights = analyzer._fallback_recommendations([], "Raw fallback content")
    assert result_no_insights == ["Raw fallback content"]

    # Test fallback with empty raw content and no insights
    result_empty = analyzer._fallback_recommendations([], "")
    assert result_empty == []


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


def test_format_insights_for_prompt_bullet_formatting():
    """Test _format_insights_for_prompt method bullet list formatting."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Create mock insights to test bullet formatting
    mock_severity = Mock()
    mock_severity.value = "critical"

    mock_insight = Mock()
    mock_insight.title = "Memory Leak Detected"
    mock_insight.severity = mock_severity

    insights = [mock_insight]
    result = analyzer._format_insights_for_prompt(insights)

    # Verify proper bullet list formatting
    assert result.startswith("- ")  # Should start with bullet point
    assert "Memory Leak Detected (critical)" in result


def test_format_insights_for_prompt_string_severity():
    """Test _format_insights_for_prompt method with string severity values."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Create mock insight with string severity (no .value attribute)
    mock_insight = Mock()
    mock_insight.title = "Configuration Error"
    mock_insight.severity = "medium"  # String severity instead of enum

    insights = [mock_insight]
    result = analyzer._format_insights_for_prompt(insights)

    # Verify severity appears correctly for string values
    assert "Configuration Error (medium)" in result


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

    # Test single-object JSON case (wrapped into list per implementation)
    single_object_json = '{"title": "Single Issue", "description": "Single description", "severity": "low"}'

    result_single = analyzer._parse_json_response(single_object_json)
    assert len(result_single) == 1  # Single dict wrapped into list
    assert result_single[0]["title"] == "Single Issue"
    assert result_single[0]["description"] == "Single description"
    assert result_single[0]["severity"] == "low"

    # Test invalid JSON - should raise ValueError
    invalid_json = "not valid json"
    with pytest.raises(ValueError, match="AI returned unparseable JSON content"):
        analyzer._parse_json_response(invalid_json)


def test_parse_json_response_embedded_array_extraction():
    """Test _parse_json_response with JSON array embedded in prose."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test JSON array embedded in prose text
    embedded_content = """Here are the analysis results:

    [
        {"title": "Memory Leak", "severity": "high", "category": "performance"},
        {"title": "SQL Injection", "severity": "critical", "category": "security"}
    ]

    That concludes the analysis."""

    result = analyzer._parse_json_response(embedded_content)
    assert len(result) == 2
    assert result[0]["title"] == "Memory Leak"
    assert result[0]["severity"] == "high"
    assert result[1]["title"] == "SQL Injection"
    assert result[1]["severity"] == "critical"


def test_parse_json_response_individual_objects_extraction():
    """Test _parse_json_response with individual JSON objects extraction."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test content with individual JSON objects (no array structure)
    objects_content = """Analysis found these issues:

    {"title": "Buffer Overflow", "severity": "critical", "line": 42}

    Additionally:

    {"title": "Deprecated API", "severity": "medium", "function": "old_method"}

    End of analysis."""

    result = analyzer._parse_json_response(objects_content)
    assert len(result) == 2
    assert result[0]["title"] == "Buffer Overflow"
    assert result[0]["severity"] == "critical"
    assert result[0]["line"] == 42
    assert result[1]["title"] == "Deprecated API"
    assert result[1]["severity"] == "medium"


def test_extract_json_array_edge_cases():
    """Test _extract_json_array method edge cases."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test no brackets
    result = analyzer._extract_json_array("no brackets here")
    assert result is None

    # Test malformed brackets
    result = analyzer._extract_json_array("[ invalid json content ]")
    assert result is None

    # Test nested arrays
    nested_content = """The results: [
        {"data": [1, 2, 3], "title": "Nested Array"},
        {"data": [4, 5, 6], "title": "Another Nested"}
    ] end"""

    result = analyzer._extract_json_array(nested_content)
    assert len(result) == 2
    assert result[0]["data"] == [1, 2, 3]
    assert result[1]["title"] == "Another Nested"

    # Test multiple array-like structures (should fail due to invalid combined extraction)
    multiple_arrays = """First: [{"id": 1}] Second: [{"id": 2}]"""
    result = analyzer._extract_json_array(multiple_arrays)
    assert result is None  # Invalid combined JSON from first [ to last ]


def test_extract_json_objects_edge_cases():
    """Test _extract_json_objects method edge cases."""
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    # Test no objects
    result = analyzer._extract_json_objects("no objects here")
    assert result == []

    # Test malformed objects
    result = analyzer._extract_json_objects("{ invalid json }")
    assert result == []

    # Test nested objects
    nested_content = """Found: {"outer": {"inner": "value"}, "title": "Nested"} and {"simple": "object"}"""
    result = analyzer._extract_json_objects(nested_content)
    assert len(result) == 2
    assert result[0]["outer"]["inner"] == "value"
    assert result[1]["simple"] == "object"

    # Test incomplete objects (unmatched braces)
    incomplete_content = """{ "incomplete": "object" and more text"""
    result = analyzer._extract_json_objects(incomplete_content)
    assert result == []  # Should not extract incomplete objects
