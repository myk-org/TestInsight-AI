"""AI analyzer service using Google Gemini via ai_api.py."""

import json
from typing import Any

from backend.models.schemas import (
    AIInsight,
    AnalysisRequest,
    AnalysisResponse,
    Severity,
)
from backend.services.gemini_api import GeminiClient


class AIAnalyzer:
    """AI-powered analyzer using Google Gemini."""

    def __init__(self, client: GeminiClient):
        """Initialize AI analyzer.

        Args:
            gemini_client: Gemini client instance from gemini_api.py
        """
        self.client = client

    def analyze_test_results(self, request: AnalysisRequest) -> AnalysisResponse:
        """Analyze test results and generate insights.

        Args:
            request: Analysis request with test data

        Returns:
            Analysis response with insights
        """
        # Generate analysis context
        context = self._build_analysis_context(request)

        # Generate insights using AI
        insights = self._generate_insights(context)

        # Generate summary and recommendations
        summary = self._generate_summary(context, insights)
        recommendations = self._generate_recommendations(context, insights)

        return AnalysisResponse(
            insights=insights,
            summary=summary,
            recommendations=recommendations,
        )

    def _build_analysis_context(self, request: AnalysisRequest) -> str:
        """Build context string for AI analysis.

        Args:
            request: Analysis request

        Returns:
            Context string
        """
        context_parts = []

        # Add the main text content
        context_parts.append(f"Text Content to Analyze:\n{request.text}...")

        # Add custom context if provided
        if request.custom_context:
            context_parts.append(f"Additional Context:\n{request.custom_context}")

        return "\n\n".join(context_parts)

    def _generate_insights(self, context: str) -> list[AIInsight]:
        """Generate AI insights from context.

        Args:
            context: Analysis context
            request: Original request

        Returns:
            List of AI insights
        """
        prompt = f"""
        Analyze the following test results and build information to identify issues, patterns, and improvement opportunities.

        Context:
        {context}

        Return ONLY a JSON array of objects. Each object must have these exact fields:
        {{
            "title": "Issue/Pattern Title",
          "description": "Detailed description",
          "severity": "LOW|MEDIUM|HIGH|CRITICAL",
          "category": "Performance|Reliability|Code Quality|Infrastructure|Testing",
          "suggestions": ["suggestion 1", "suggestion 2"],
          "confidence": 0.8
        }}

        Focus on:
        1. Failed tests and their root causes
        2. Performance issues and slow tests
        3. Build failures and error patterns
        4. Code quality concerns
        5. Infrastructure or environment issues
        6. Testing strategy improvements
        """

        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        try:
            insights_data = json.loads(result["content"].strip())
            return [self._create_insight_from_dict(insight) for insight in insights_data]
        except json.JSONDecodeError:
            # Fallback
            return []

    def _generate_summary(self, context: str, insights: list[AIInsight]) -> str:
        """Generate analysis summary.

        Args:
            context: Analysis context
            insights: Generated insights

        Returns:
            Summary text
        """
        # Limit context to 1000 characters
        truncated_context = context[:1000]
        if len(context) > 1000:
            truncated_context += "..."

        # Limit insights to first 5
        limited_insights = insights[:5]

        prompt = f"""
        Based on the following test analysis context and insights, provide a concise summary of the overall situation.

        Context:
        {truncated_context}

        Key Insights:
        {self._format_insights_for_prompt(limited_insights)}

        Provide a brief 2-3 sentence summary highlighting the most important findings.
        """

        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        return result["content"].strip()

    def _generate_recommendations(self, context: str, insights: list[AIInsight]) -> list[str]:
        """Generate actionable recommendations.

        Args:
            context: Analysis context
            insights: Generated insights

        Returns:
            List of recommendations
        """
        # Limit context to 500 characters
        truncated_context = context[:500]
        if len(context) > 500:
            truncated_context += "..."

        # Limit insights to first 3
        limited_insights = insights[:3]

        prompt = f"""
        Based on the analysis context and insights, provide specific, actionable recommendations.

        Context Summary:
        {truncated_context}

        Top Insights:
        {self._format_insights_for_prompt(limited_insights)}

        Return ONLY a JSON array of strings, no other text. Example format:
        ["Recommendation 1", "Recommendation 2", "Recommendation 3", "Additional recommendations as needed"]
        """
        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        try:
            return json.loads(result["content"].strip())
        except json.JSONDecodeError:
            # Fallback if AI doesn't follow format
            return ["Review test failures manually", "Check configuration", "Analyze error patterns"]

    def _create_insight_from_dict(self, data: dict[str, Any]) -> AIInsight:
        """Create AIInsight from parsed data.

        Args:
            data: Parsed insight data

        Returns:
            AIInsight object
        """
        severity_map = {
            "LOW": Severity.LOW,
            "MEDIUM": Severity.MEDIUM,
            "HIGH": Severity.HIGH,
            "CRITICAL": Severity.CRITICAL,
        }

        return AIInsight(
            title=data.get("title", "Unknown Issue"),
            description=data.get("description", "No description available"),
            severity=severity_map.get(data.get("severity", "MEDIUM"), Severity.MEDIUM),
            category=data.get("category", "General"),
            suggestions=data.get("suggestions", []),
            confidence=data.get("confidence", 0.7),
        )

    def _format_insights_for_prompt(self, insights: list[AIInsight]) -> str:
        """Format insights for use in prompts.

        Args:
            insights: List of insights

        Returns:
            Formatted insight text
        """
        if not insights:
            return "No insights available"

        formatted = []
        for insight in insights:
            formatted.append(f"- {insight.title} ({insight.severity.value})")

        return "\n".join(formatted)
