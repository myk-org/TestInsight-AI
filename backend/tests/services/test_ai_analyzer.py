"""Tests for AI analyzer service."""

import json
from unittest.mock import Mock, patch
import pytest

from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient
from backend.models.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AIInsight,
    Severity,
)


class TestAIAnalyzer:
    """Test cases for AIAnalyzer class."""

    def test_init(self):
        """Test AIAnalyzer initialization."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        assert analyzer.client == mock_client

    def test_analyze_test_results_success(self):
        """Test analyze_test_results with successful analysis."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        # Mock the private methods
        fake_context = "Mocked analysis context"
        fake_insights = [
            AIInsight(
                title="Test Failure",
                description="Multiple test failures detected",
                severity=Severity.HIGH,
                category="Reliability",
                suggestions=["Fix authentication", "Add retry logic"],
                confidence=0.85,
            )
        ]
        fake_summary = "Analysis shows critical test failures"
        fake_recommendations = ["Fix auth issues", "Improve error handling"]

        with (
            patch.object(analyzer, "_build_analysis_context", return_value=fake_context),
            patch.object(analyzer, "_generate_insights", return_value=fake_insights),
            patch.object(analyzer, "_generate_summary", return_value=fake_summary),
            patch.object(analyzer, "_generate_recommendations", return_value=fake_recommendations),
        ):
            request = AnalysisRequest(
                text="Test failure logs here",
                custom_context="Jenkins build #42 failed",
                repository_url=None,
                repository_branch=None,
                repository_commit=None,
                include_repository_context=False,
            )

            result = analyzer.analyze_test_results(request)

            assert isinstance(result, AnalysisResponse)
            assert result.insights == fake_insights
            assert result.summary == fake_summary
            assert result.recommendations == fake_recommendations

    def test_build_analysis_context_with_custom_context(self):
        """Test _build_analysis_context includes custom context."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        request = AnalysisRequest(
            text="Test failure logs with detailed stack traces here",
            custom_context="This is from Jenkins build #123",
            repository_url=None,
            repository_branch=None,
            repository_commit=None,
            include_repository_context=False,
        )

        result = analyzer._build_analysis_context(request)

        assert "Text Content to Analyze:" in result
        assert "Test failure logs with detailed stack traces here" in result
        assert "Additional Context:" in result
        assert "This is from Jenkins build #123" in result

    def test_build_analysis_context_without_custom_context(self):
        """Test _build_analysis_context without custom context."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        request = AnalysisRequest(
            text="Simple test failure",
            custom_context=None,
            repository_url=None,
            repository_branch=None,
            repository_commit=None,
            include_repository_context=False,
        )

        result = analyzer._build_analysis_context(request)

        assert "Text Content to Analyze:" in result
        assert "Simple test failure" in result
        assert "Additional Context:" not in result

    def test_build_analysis_context_includes_full_text(self):
        """Test _build_analysis_context includes full text."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        long_text = "B" * 10000  # 10k characters - using B to avoid conflict with "A" in other text
        request = AnalysisRequest(
            text=long_text,
            custom_context=None,
            repository_url=None,
            repository_branch=None,
            repository_commit=None,
            include_repository_context=False,
        )

        result = analyzer._build_analysis_context(request)

        # Should include full text
        assert "B" * 10000 in result  # Full text should be present
        assert result.count("B") == 10000  # All 10000 B's should be there
        assert "Text Content to Analyze:" in result  # Should have the header

    def test_generate_insights_success(self):
        """Test _generate_insights with successful AI response."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {
            "success": True,
            "content": json.dumps([
                {
                    "title": "Authentication Failure",
                    "description": "Multiple authentication failures detected in test suite",
                    "severity": "HIGH",
                    "category": "Reliability",
                    "suggestions": ["Check credentials", "Review auth flow"],
                    "confidence": 0.9,
                },
                {
                    "title": "Performance Issue",
                    "description": "Tests running slower than expected",
                    "severity": "MEDIUM",
                    "category": "Performance",
                    "suggestions": ["Optimize queries", "Add caching"],
                    "confidence": 0.7,
                },
            ]),
        }

        analyzer = AIAnalyzer(client=mock_client)

        context = "Test failure context"
        result = analyzer._generate_insights(context)

        assert len(result) == 2
        assert result[0].title == "Authentication Failure"
        assert result[0].severity == Severity.HIGH
        assert result[0].category == "Reliability"
        assert result[0].confidence == 0.9
        assert len(result[0].suggestions) == 2

        assert result[1].title == "Performance Issue"
        assert result[1].severity == Severity.MEDIUM
        assert result[1].category == "Performance"

    def test_generate_insights_ai_failure(self):
        """Test _generate_insights with AI API failure."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": False, "error": "API rate limit exceeded"}

        analyzer = AIAnalyzer(client=mock_client)

        with pytest.raises(ConnectionError, match="AI content generation failed: API rate limit exceeded"):
            analyzer._generate_insights("context")

    def test_generate_insights_invalid_json(self):
        """Test _generate_insights with invalid JSON response."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "This is not valid JSON"}

        analyzer = AIAnalyzer(client=mock_client)

        # Should raise ValueError for invalid JSON
        with pytest.raises(ValueError, match="AI returned invalid JSON"):
            analyzer._generate_insights("context")

    def test_generate_insights_empty_response(self):
        """Test _generate_insights with empty JSON array."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "[]"}

        analyzer = AIAnalyzer(client=mock_client)

        result = analyzer._generate_insights("context")

        assert result == []

    def test_generate_summary_success(self):
        """Test _generate_summary with successful AI response."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {
            "success": True,
            "content": "The analysis reveals critical authentication failures affecting test reliability.",
        }

        analyzer = AIAnalyzer(client=mock_client)

        fake_insights = [
            AIInsight(
                title="Auth Failure",
                description="Test description",
                severity=Severity.HIGH,
                category="Reliability",
                suggestions=[],
                confidence=0.8,
            )
        ]

        result = analyzer._generate_summary("context", fake_insights)

        assert result == "The analysis reveals critical authentication failures affecting test reliability."

    def test_generate_summary_ai_failure(self):
        """Test _generate_summary with AI API failure."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": False, "error": "Connection timeout"}

        analyzer = AIAnalyzer(client=mock_client)

        with pytest.raises(ConnectionError, match="AI content generation failed: Connection timeout"):
            analyzer._generate_summary("context", [])

    def test_generate_recommendations_success(self):
        """Test _generate_recommendations with successful AI response."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {
            "success": True,
            "content": json.dumps([
                "Review authentication configuration",
                "Implement retry mechanisms for flaky tests",
                "Add better error logging",
            ]),
        }

        analyzer = AIAnalyzer(client=mock_client)

        fake_insights = [
            AIInsight(
                title="Auth Issue",
                description="Test description",
                severity=Severity.HIGH,
                category="Reliability",
                suggestions=[],
                confidence=0.8,
            )
        ]

        result = analyzer._generate_recommendations("context", fake_insights)

        assert len(result) == 3
        assert "Review authentication configuration" in result
        assert "Implement retry mechanisms for flaky tests" in result
        assert "Add better error logging" in result

    def test_generate_recommendations_ai_failure(self):
        """Test _generate_recommendations with AI API failure."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": False, "error": "Service unavailable"}

        analyzer = AIAnalyzer(client=mock_client)

        with pytest.raises(ConnectionError, match="AI content generation failed: Service unavailable"):
            analyzer._generate_recommendations("context", [])

    def test_generate_recommendations_invalid_json(self):
        """Test _generate_recommendations with invalid JSON response."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "Not a JSON array"}

        analyzer = AIAnalyzer(client=mock_client)

        result = analyzer._generate_recommendations("context", [])

        # Should return empty list as fallback
        assert result == []

    def test_create_insight_from_dict_complete_data(self):
        """Test _create_insight_from_dict with complete data."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        data = {
            "title": "Database Connection Error",
            "description": "Tests failing due to database connection issues",
            "severity": "CRITICAL",
            "category": "Infrastructure",
            "suggestions": ["Check DB config", "Verify network connectivity"],
            "confidence": 0.95,
        }

        result = analyzer._create_insight_from_dict(data)

        assert result.title == "Database Connection Error"
        assert result.description == "Tests failing due to database connection issues"
        assert result.severity == Severity.CRITICAL
        assert result.category == "Infrastructure"
        assert result.suggestions == ["Check DB config", "Verify network connectivity"]
        assert result.confidence == 0.95

    def test_create_insight_from_dict_minimal_data(self):
        """Test _create_insight_from_dict with minimal data."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        data = {}  # Empty dict

        result = analyzer._create_insight_from_dict(data)

        assert result.title == "Unknown Issue"
        assert result.description == "No description available"
        assert result.severity == Severity.MEDIUM  # Default
        assert result.category == "General"
        assert result.suggestions == []
        assert result.confidence == 0.7

    def test_create_insight_from_dict_invalid_severity(self):
        """Test _create_insight_from_dict with invalid severity."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        data = {"severity": "INVALID_SEVERITY"}

        result = analyzer._create_insight_from_dict(data)

        assert result.severity == Severity.MEDIUM  # Falls back to default

    def test_format_insights_for_prompt_with_insights(self):
        """Test _format_insights_for_prompt with insights."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        insights = [
            AIInsight(
                title="Auth Failure",
                description="Description",
                severity=Severity.HIGH,
                category="Reliability",
                suggestions=[],
                confidence=0.8,
            ),
            AIInsight(
                title="Performance Issue",
                description="Description",
                severity=Severity.MEDIUM,
                category="Performance",
                suggestions=[],
                confidence=0.6,
            ),
        ]

        result = analyzer._format_insights_for_prompt(insights)

        # The actual format uses insight.severity.value
        expected = f"- Auth Failure ({Severity.HIGH.value})\n- Performance Issue ({Severity.MEDIUM.value})"
        assert result == expected

    def test_format_insights_for_prompt_empty_list(self):
        """Test _format_insights_for_prompt with empty list."""
        mock_client = Mock(spec=GeminiClient)
        analyzer = AIAnalyzer(client=mock_client)

        result = analyzer._format_insights_for_prompt([])

        assert result == "No insights available"

    def test_generate_insights_context_in_prompt(self):
        """Test _generate_insights includes context in prompt."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "[]"}

        analyzer = AIAnalyzer(client=mock_client)

        context = "Test failure context with errors"
        analyzer._generate_insights(context)

        # Verify the prompt includes the context
        call_args = mock_client.generate_content.call_args[0][0]
        assert "Test failure context with errors" in call_args
        assert "Focus on:" in call_args
        assert "Failed tests and their root causes" in call_args

    def test_generate_summary_includes_full_context(self):
        """Test _generate_summary includes full context and insights in prompt."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "Summary"}

        analyzer = AIAnalyzer(client=mock_client)

        long_context = "A" * 2000  # 2k characters
        insights = [
            AIInsight(
                title="Test Issue",
                description="Description",
                severity=Severity.LOW,
                category="Testing",
                suggestions=[],
                confidence=0.5,
            )
        ]

        result = analyzer._generate_summary(long_context, insights)

        # Check that full context is included and we get the expected result
        call_args = mock_client.generate_content.call_args[0][0]
        assert "A" * 2000 in call_args  # Full context should be present
        assert "Test Issue" in call_args  # Insights should be included
        assert result == "Summary"

    def test_generate_summary_includes_all_insights(self):
        """Test _generate_summary includes all provided insights."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": "Summary"}

        analyzer = AIAnalyzer(client=mock_client)

        # Create 10 insights
        insights = []
        for i in range(10):
            insights.append(
                AIInsight(
                    title=f"Issue {i}",
                    description="Description",
                    severity=Severity.LOW,
                    category="Testing",
                    suggestions=[],
                    confidence=0.5,
                )
            )

        analyzer._generate_summary("context", insights)

        # Check that all insights are included in the prompt
        call_args = mock_client.generate_content.call_args[0][0]
        assert "Issue 0" in call_args
        assert "Issue 4" in call_args
        assert "Issue 9" in call_args  # All 10 insights should be present

    def test_generate_recommendations_includes_context_and_insights(self):
        """Test _generate_recommendations includes full context and insights."""
        mock_client = Mock(spec=GeminiClient)
        mock_client.generate_content.return_value = {"success": True, "content": '["Recommendation"]'}

        analyzer = AIAnalyzer(client=mock_client)

        long_context = "B" * 1000  # 1k characters
        insights = []
        for i in range(5):
            insights.append(
                AIInsight(
                    title=f"Issue {i}",
                    description="Description",
                    severity=Severity.MEDIUM,
                    category="Testing",
                    suggestions=[],
                    confidence=0.7,
                )
            )

        result = analyzer._generate_recommendations(long_context, insights)

        # Check that full context and all insights are included
        call_args = mock_client.generate_content.call_args[0][0]
        assert "B" * 1000 in call_args  # Full context should be present
        assert "Issue 0" in call_args
        assert "Issue 4" in call_args  # All 5 insights should be present
        assert result == ["Recommendation"]

    def test_integration_full_analysis_flow(self):
        """Test full analysis flow integration."""
        mock_client = Mock(spec=GeminiClient)

        # Setup AI responses for each step
        insights_response = {
            "success": True,
            "content": json.dumps([
                {
                    "title": "Test Timeout",
                    "description": "Tests timing out due to slow DB queries",
                    "severity": "HIGH",
                    "category": "Performance",
                    "suggestions": ["Optimize queries", "Increase timeout"],
                    "confidence": 0.85,
                }
            ]),
        }

        summary_response = {
            "success": True,
            "content": "Tests are failing due to performance issues with database queries.",
        }

        recommendations_response = {
            "success": True,
            "content": json.dumps([
                "Optimize slow database queries",
                "Review test timeout configurations",
                "Consider database indexing improvements",
            ]),
        }

        mock_client.generate_content.side_effect = [insights_response, summary_response, recommendations_response]

        analyzer = AIAnalyzer(client=mock_client)

        request = AnalysisRequest(
            text="Test failure logs with timeout errors",
            custom_context="Jenkins build failed after 30 minutes",
            repository_url=None,
            repository_branch=None,
            repository_commit=None,
            include_repository_context=False,
        )

        result = analyzer.analyze_test_results(request)

        # Verify complete analysis result
        assert isinstance(result, AnalysisResponse)
        assert len(result.insights) == 1
        assert result.insights[0].title == "Test Timeout"
        assert result.insights[0].severity == Severity.HIGH
        assert result.summary == "Tests are failing due to performance issues with database queries."
        assert len(result.recommendations) == 3
        assert "Optimize slow database queries" in result.recommendations

        # Verify AI was called 3 times (insights, summary, recommendations)
        assert mock_client.generate_content.call_count == 3
