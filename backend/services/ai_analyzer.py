"""AI analyzer service using Google Gemini via ai_api.py."""

import json
import os
import re
from pathlib import Path
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
        insights = self._generate_insights(context, request.system_prompt)

        # Generate summary and recommendations
        summary = self._generate_summary(context, insights, request.system_prompt)
        recommendations = self._generate_recommendations(context, insights, request.system_prompt)

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
        context_parts.append(f"Text Content to Analyze:\n{request.text}")

        # Add custom context if provided
        if request.custom_context:
            context_parts.append(f"Additional Context:\n{request.custom_context}")

        # Add repository source code context if available
        if request.include_repository_context:
            if _repo_path := getattr(request, "cloned_repo_path", ""):
                repo_files = self._extract_relevant_repository_files(
                    repo_path=Path(_repo_path), failure_text=request.text
                )
                if repo_files:
                    context_parts.append("Repository Source Code Context:")
                    for file_path, content in repo_files:
                        context_parts.append(f"\n--- {file_path} ---\n{content}")

        return "\n\n".join(context_parts)

    def _generate_insights(self, context: str, system_prompt: str | None = None) -> list[AIInsight]:
        """Generate AI insights from context.

        Args:
            context: Analysis context
            request: Original request

        Returns:
            List of AI insights
        """
        prompt = f"""
        {system_prompt or "Analyze the following test results and build information to identify issues, patterns, and improvement opportunities."}
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
        2. Build failures and error patterns
        3. Infrastructure or environment issues
        4. Testing strategy improvements
        """

        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        content = result["content"].strip()
        if not content:
            raise ValueError("AI returned empty content for insights generation")

        # Strip markdown code blocks if present
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        try:
            insights_data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"AI returned invalid JSON for insights: {content} Error: {e}")

        if not isinstance(insights_data, list):
            raise ValueError(f"AI returned non-array JSON for insights: {type(insights_data)}")

        return [self._create_insight_from_dict(insight) for insight in insights_data]

    def _generate_summary(self, context: str, insights: list[AIInsight], system_prompt: str | None = None) -> str:
        """Generate analysis summary.

        Args:
            context: Analysis context
            insights: Generated insights
            system_prompt: Optional custom system prompt

        Returns:
            Summary text
        """

        prompt = f"""
        {system_prompt or "Based on the following test analysis context and insights, provide a concise summary of the overall situation."}

        Context:
        {context}

        Key Insights:
        {self._format_insights_for_prompt(insights)}
        """

        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        return result["content"].strip()

    def _generate_recommendations(
        self, context: str, insights: list[AIInsight], system_prompt: str | None = None
    ) -> list[str]:
        """Generate actionable recommendations.

        Args:
            context: Analysis context
            insights: Generated insights
            system_prompt: Optional custom system prompt

        Returns:
            List of recommendations
        """
        prompt = f"""
        {system_prompt or "Based on the analysis context and insights, provide specific, actionable recommendations."}

        Context Summary:
        {context}

        Top Insights:
        {self._format_insights_for_prompt(insights)}

        Return ONLY a List array of strings, no other text. Example format:
        ["Recommendation 1", "Recommendation 2", "Recommendation 3", "Additional recommendations as needed"]
        """
        result = self.client.generate_content(prompt)
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        try:
            return json.loads(result["content"].strip())
        except json.JSONDecodeError:
            # Fallback if AI doesn't follow format
            return []

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

    def _extract_relevant_repository_files(self, repo_path: Path, failure_text: str) -> list[tuple[str, str]]:
        """Extract 3-5 most relevant files for AI analysis.

        Args:
            repo_path: Path to cloned repository
            failure_text: Text containing failure information

        Returns:
            List of (file_path, content) tuples
        """
        files: list[tuple[str, str]] = []

        def _safe_int_env(key: str, default: int) -> int:
            try:
                return int(os.getenv(key, str(default)))
            except (TypeError, ValueError):
                # Avoid crashing on invalid env values; use default
                return default

        max_files = _safe_int_env("AI_REPO_MAX_FILES", 5)
        max_file_bytes = _safe_int_env("AI_REPO_MAX_FILE_BYTES", 51200)

        # 2. Test files mentioned in failure output
        test_file_patterns = [
            r"(\w+\.py)::",  # pytest: test_file.py::test_function
            r"(\w+\.py)",  # Python files
            r"(\w+\.test\.js)",
            r"(\w+\.spec\.js)",  # JavaScript test files
            r"(\w+Test\.java)",  # Java test files
            r"(\w+_test\.go)",  # Go test files
        ]

        for pattern in test_file_patterns:
            matches = re.findall(pattern, failure_text)
            for match in matches:
                test_file = match if isinstance(match, str) else match[0]
                test_file = test_file.split("::")[0] if "::" in test_file else test_file
                file_path = self._find_file_in_repo(repo_path, test_file)
                if file_path and file_path.exists():
                    try:
                        # Truncate large files to avoid excessive context
                        content_raw = file_path.read_text(encoding="utf-8")
                        content = content_raw if isinstance(content_raw, str) else str(content_raw)
                        encoded = content.encode("utf-8", errors="ignore")
                        if len(encoded) > max_file_bytes:
                            content = (
                                encoded[:max_file_bytes].decode("utf-8", errors="ignore") + "\n<!-- truncated -->\n"
                            )
                        relative_path = str(file_path.relative_to(repo_path))
                        files.append((relative_path, content))
                    except (UnicodeDecodeError, PermissionError):
                        continue

                if len(files) >= max_files:
                    return files

        return files

    def _find_file_in_repo(self, repo_path: Path, filename: str) -> Path | None:
        """Find file in repository by name.

        Args:
            repo_path: Path to repository root
            filename: Name of file to find

        Returns:
            Path to file if found, None otherwise
        """
        try:
            # Use glob to find the file, limiting search depth for performance
            for file_path in repo_path.rglob(filename):
                if file_path.is_file():
                    # Skip files in common ignore directories
                    path_parts = file_path.parts
                    if any(
                        ignore_dir in path_parts
                        for ignore_dir in [".git", "node_modules", "__pycache__", ".venv", "venv", "target"]
                    ):
                        continue
                    return file_path
        except (OSError, PermissionError):
            # Handle potential filesystem errors
            pass
        return None
