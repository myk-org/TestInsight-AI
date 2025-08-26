"""AI analyzer service using Google Gemini via ai_api.py."""

import json
import logging
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

logger = logging.getLogger("testinsight")


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
        logger.info(
            "AIAnalyzer: analyze start text_len=%d include_repo=%s system_prompt=%s repo_url=%s branch=%s commit=%s",
            len(getattr(request, "text", "") or ""),
            getattr(request, "include_repository_context", False),
            bool(getattr(request, "system_prompt", None)),
            getattr(request, "repository_url", None),
            getattr(request, "repository_branch", None),
            getattr(request, "repository_commit", None),
        )
        # Stash repo limits on the analyzer instance for downstream file extraction
        try:
            self._repo_max_files = getattr(request, "repo_max_files", None)
            self._repo_max_bytes = getattr(request, "repo_max_bytes", None)
        except Exception:
            self._repo_max_files = None
            self._repo_max_bytes = None

        # Generate analysis context
        context = self._build_analysis_context(request)
        logger.info(
            "AIAnalyzer: context built len=%d include_repo=%s cloned_path=%s",
            len(context or ""),
            getattr(request, "include_repository_context", False),
            getattr(request, "cloned_repo_path", None),
        )

        # Generate insights using AI
        insights = self._generate_insights(context, request.system_prompt)

        # Generate summary and recommendations
        summary = self._generate_summary(context, insights, request.system_prompt)
        logger.info("AIAnalyzer: summary generated len=%d", len(summary or ""))
        recommendations = self._generate_recommendations(
            context,
            insights,
            request.system_prompt,
            repo_context_included=bool(
                getattr(request, "include_repository_context", False)
                and bool(getattr(request, "cloned_repo_path", None))
            ),
        )
        logger.info("AIAnalyzer: recommendations generated count=%d", len(recommendations))

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
                logger.info(
                    "AIAnalyzer: repo files extracted count=%d files=%s",
                    len(repo_files),
                    [fp for fp, _ in repo_files],
                )

        result_context = "\n\n".join(context_parts)
        logger.info("AIAnalyzer: context ready len=%d", len(result_context))
        return result_context

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

        # Request strict JSON array via response mime type to reduce formatting errors
        result = self.client.generate_content(
            prompt,
            response_mime_type="application/json",
        )
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")

        raw_content = result["content"].strip()
        if not raw_content:
            # Gracefully degrade to no insights
            return []

        # Strip markdown code fences if present
        content = raw_content
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        elif content.startswith("```"):
            content = content.replace("```", "").strip()

        # Parsing strategy with explicit handling for truly invalid vs empty array
        # 1) Direct parse
        try:
            direct = json.loads(content)
            if isinstance(direct, list):
                if len(direct) == 0:
                    logger.info("AIAnalyzer: insights parsed count=0 (empty array)")
                    return []
                insights_data = direct
            else:
                insights_data = []
        except json.JSONDecodeError:
            insights_data = None  # mark as not directly parsed

        # 2) Bracket extraction when direct parse failed
        if insights_data is None:
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1 and end > start:
                subset = content[start : end + 1]
                try:
                    sub_parsed = json.loads(subset)
                    if isinstance(sub_parsed, list):
                        if len(sub_parsed) == 0:
                            logger.info("AIAnalyzer: insights parsed count=0 (empty array)")
                            return []
                        insights_data = sub_parsed
                except Exception:
                    insights_data = None

        # 3) Heuristic object collection (treat empty result as invalid)
        if insights_data is None:
            items: list[Any] = []
            buf: list[str] = []
            depth = 0
            for ch in content:
                if ch == "{":
                    depth += 1
                if depth > 0:
                    buf.append(ch)
                if ch == "}":
                    depth -= 1
                    if depth == 0 and buf:
                        candidate = "".join(buf)
                        buf = []
                        try:
                            obj = json.loads(candidate)
                            items.append(obj)
                        except Exception:
                            pass
            insights_data = items
            if len(items) == 0:
                snippet = raw_content.strip()
                raise ValueError(f"AI returned invalid JSON for insights: {snippet}")

        # At this point, insights_data is a non-empty list of dicts
        if not isinstance(insights_data, list):
            snippet = raw_content.strip()
            raise ValueError(f"AI returned invalid JSON for insights: {snippet}")
        # Normal path: convert to AIInsight list and return
        parsed = [self._create_insight_from_dict(insight) for insight in insights_data if isinstance(insight, dict)]
        logger.info("AIAnalyzer: insights parsed count=%d", len(parsed))
        for i, ins in enumerate(parsed[:5]):
            logger.info(
                "AIAnalyzer: insight[%d] title=%s severity=%s category=%s",
                i,
                getattr(ins, "title", ""),
                getattr(ins, "severity", ""),
                getattr(ins, "category", ""),
            )
        return parsed

        parsed = [self._create_insight_from_dict(insight) for insight in insights_data if isinstance(insight, dict)]
        logger.info("AIAnalyzer: insights parsed count=%d", len(parsed))
        for i, ins in enumerate(parsed[:5]):
            logger.info(
                "AIAnalyzer: insight[%d] title=%s severity=%s category=%s",
                i,
                getattr(ins, "title", ""),
                getattr(ins, "severity", ""),
                getattr(ins, "category", ""),
            )
        return parsed

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
        self,
        context: str,
        insights: list[AIInsight],
        system_prompt: str | None = None,
        *,
        repo_context_included: bool = False,
    ) -> list[str]:
        """Generate actionable recommendations."""
        instructions, allowed_paths, allowed_clause = self._build_recommendation_instructions(
            context=context,
            system_prompt=system_prompt,
            repo_context_included=repo_context_included,
        )

        prompt = self._compose_recommendations_prompt(
            instructions=instructions,
            allowed_clause=allowed_clause if repo_context_included else "",
            context=context,
            insights=insights,
        )

        response_schema = self._build_response_schema(allowed_paths, repo_context_included)
        raw = self._query_recommendations_model(
            prompt=prompt,
            repo_context_included=repo_context_included,
            response_schema=response_schema,
        )

        logger.info("AIAnalyzer: recommendations raw length=%d", len(raw))
        parsed = self._parse_recommendations_to_strings(raw)
        if parsed:
            logger.info("AIAnalyzer: recommendations initial parsed count=%d", len(parsed))
            sanitized = self._sanitize_and_force_code_blocks(parsed, context, insights, repo_context_included)
            if sanitized:
                return sanitized

        # If model output is invalid JSON and no insights exist, tests expect []
        if not insights:
            return []
        return self._fallback_recommendations(insights, raw)

    def _build_recommendation_instructions(
        self,
        *,
        context: str,
        system_prompt: str | None,
        repo_context_included: bool,
    ) -> tuple[str, list[str], str]:
        allowed_paths: list[str] = []
        allowed_clause: str = ""
        if repo_context_included:
            try:
                allowed_paths = re.findall(r"(?m)^---\s+([^\n]+)\s+---$", context)
                allowed_paths = [p.strip() for p in allowed_paths if p.strip()]
            except Exception:
                allowed_paths = []
            logger.info(
                "AIAnalyzer: repo-context strict mode enabled; allowed_paths=%d sample=%s",
                len(allowed_paths),
                allowed_paths,
            )

            strict_instructions = (
                "Based on the analysis context and insights, provide concrete code-change recommendations from the cloned repository only. "
                "Each recommendation MUST be a single string that includes: (1) a one-line rationale, and (2) one or more fenced code blocks "
                "showing the exact changes (patches or full replacement). The opening fence MUST include a language tag and the path on the same line, "
                "for example: ```python path: utilities/mtv_migration.py"
                "Do NOT invent files, functions, or unrelated examples. Do NOT output unified diffs or git patch headers (no lines starting with '--- a/', '+++ b/', or '@@ … @@'). "
                "Do NOT include ellipses like '...' in code. Provide complete, copy-pastable snippets only."
            )
            allowed_clause = (
                "Allowed files (choose from this list only):\n- " + "\n- ".join(allowed_paths) if allowed_paths else ""
            )
        else:
            strict_instructions = (
                "Based on the analysis context and insights, provide specific, actionable recommendations."
            )

        if system_prompt and system_prompt.strip():
            instructions = system_prompt.strip()
        else:
            instructions = strict_instructions

        return instructions, allowed_paths, allowed_clause

    def _compose_recommendations_prompt(
        self,
        *,
        instructions: str,
        allowed_clause: str,
        context: str,
        insights: list[AIInsight],
    ) -> str:
        output_contract = (
            "Return ONLY a JSON array of strings. No prose outside JSON. Each string MUST contain at least one fenced code block \n"
            "whose opening fence includes a language tag and a valid 'path:' on the same line (e.g., ```python path: repo/file.py)."
        )
        return f"""
        {instructions}

        {allowed_clause}

        Context Summary:
        {context}

        Top Insights:
        {self._format_insights_for_prompt(insights)}

        {output_contract}
        """

    def _build_response_schema(self, allowed_paths: list[str], included: bool) -> Any:
        if included and allowed_paths:
            return {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "enum": allowed_paths},
                        "language": {"type": "string"},
                        "rationale": {"type": "string"},
                        "code": {"type": "string"},
                    },
                    "required": ["path", "language", "code"],
                },
                "minItems": 1,
            }
        return None

    def _query_recommendations_model(
        self,
        *,
        prompt: str,
        repo_context_included: bool,
        response_schema: Any,
    ) -> str:
        result = self.client.generate_content(
            prompt,
            response_mime_type="application/json",
            temperature=0.1 if repo_context_included else 0.7,
            max_tokens=8192,
            response_schema=response_schema,
        )
        if not result["success"]:
            raise ConnectionError(f"AI content generation failed: {result['error']}")
        return (result.get("content") or "").strip()

    def _parse_recommendations_to_strings(self, text: str) -> list[str]:
        # 1) structured objects
        try:
            candidate = json.loads(text)
            if isinstance(candidate, list) and all(isinstance(o, dict) for o in candidate):
                out: list[str] = []
                for o in candidate:
                    path = o.get("path")
                    lang = o.get("language") or "bash"
                    code = o.get("code")
                    rationale = o.get("rationale")
                    if isinstance(path, str) and isinstance(code, str):
                        header = f"```{lang} path: {path}"
                        block = f"{header}\n{code.strip()}\n```"
                        out.append(
                            f"{rationale.strip()}\n{block}"
                            if isinstance(rationale, str) and rationale.strip()
                            else block
                        )
                if out:
                    return out
        except Exception:
            pass

        # 2) plain array (strings/objects)
        try:
            data = json.loads(text)
            if isinstance(data, list):
                out2: list[str] = []
                for item in data:
                    if isinstance(item, str):
                        out2.append(item)
                    elif isinstance(item, dict):
                        for key in ("text", "recommendation", "value"):
                            if key in item and isinstance(item[key], str):
                                out2.append(item[key])
                                break
                return out2
        except Exception:
            pass

        # 3) bracketed array region fallback
        try:
            start = text.find("[")
            end = text.rfind("]")
            if start != -1 and end != -1 and end > start:
                sub = text[start : end + 1]
                data = json.loads(sub)
                if isinstance(data, list):
                    return [str(x) if not isinstance(x, str) else x for x in data]
        except Exception:
            pass
        return []

    def _sanitize_and_force_code_blocks(
        self,
        recs: list[str],
        context: str,
        insights: list[AIInsight],
        included: bool,
    ) -> list[str]:
        def _strip_diff_headers(s: str) -> str:
            try:
                return re.sub(r"(?m)^(?:--- a/.*|\+\+\+ b/.*|@@.*@@)\n?", "", s)
            except Exception:
                return s

        parsed = [_strip_diff_headers(s) if isinstance(s, str) else s for s in recs]
        code_like = sum(1 for s in parsed if isinstance(s, str) and "```" in s)
        logger.info(
            "AIAnalyzer: recommendations parsed count=%d code_blocks=%d",
            len(parsed),
            code_like,
        )

        if included and code_like == 0:
            try:
                allowed_paths = re.findall(r"(?m)^---\s+([^\n]+)\s+---$", context)
                allowed_paths = [p.strip() for p in allowed_paths if p.strip()]
            except Exception:
                allowed_paths = []
            if allowed_paths:
                forced = self._force_code_retry(context, insights, allowed_paths)
                if forced:
                    return forced
                single = self._force_single_file(context, insights, allowed_paths)
                if single:
                    return single
        return parsed

    def _force_code_retry(
        self,
        context: str,
        insights: list[AIInsight],
        allowed_paths: list[str],
    ) -> list[str]:
        forced_instructions = (
            "Return ONLY a JSON array of objects with this schema: "
            "[{ path: <one of the allowed paths>, language: <language>, code: <string>, rationale?: <string> }]. "
            "For each object you MUST output a single fenced code block in the final string using the fence format ```{language} path: {path}. "
            "Do NOT invent files. Do NOT output unified diffs or git headers."
        )
        retry_prompt = f"""
        {forced_instructions}

        Context Summary:
        {context}

        Top Insights:
        {self._format_insights_for_prompt(insights)}
        """
        # Enforce a strict response schema to maximize the chance of valid code output
        response_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "enum": allowed_paths},
                    "language": {"type": "string"},
                    "rationale": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["path", "language", "code"],
            },
            "minItems": 1,
        }

        result = self.client.generate_content(
            retry_prompt,
            response_mime_type="application/json",
            temperature=0.05,
            response_schema=response_schema,
        )
        if result.get("success"):
            retry_raw = (result.get("content") or "").strip()
            retry_parsed = self._parse_recommendations_to_strings(retry_raw)
            if retry_parsed:
                # Final sanitation pass (diff headers, etc.)
                return self._sanitize_and_force_code_blocks(retry_parsed, context, insights, True)
        return []

    def _force_single_file(
        self,
        context: str,
        insights: list[AIInsight],
        allowed_paths: list[str],
    ) -> list[str]:
        target_file = allowed_paths[0] if allowed_paths else None
        if not target_file:
            return []
        single_file_prompt = f"""
        You MUST provide at least one fenced code block for the following file only, with path on the opening fence:
        ```{{language}} path: {target_file}

        Return ONLY a JSON array of one or more strings. Each string MUST include a single fenced code block whose opening fence contains 'path: {target_file}'.
        Do NOT output diffs, headers, or ellipses. Provide the full, pasteable code snippet.

        Context Summary:
        {context}

        Top Insights:
        {self._format_insights_for_prompt(insights)}
        """
        result = self.client.generate_content(
            single_file_prompt,
            response_mime_type="application/json",
            temperature=0.1,
        )
        if result.get("success"):
            single_raw = (result.get("content") or "").strip()
            single_parsed = self._parse_recommendations_to_strings(single_raw)
            return single_parsed

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

        # Get limits from analysis request set earlier (via attached attribute on self or instance)
        # Default to safe limits if not provided by the request
        max_files = getattr(self, "_repo_max_files", None)
        max_file_bytes = getattr(self, "_repo_max_bytes", None)
        if not isinstance(max_files, int) or max_files <= 0:
            max_files = 5
        if not isinstance(max_file_bytes, int) or max_file_bytes <= 0:
            max_file_bytes = 51200

        # 2. Test files mentioned in failure output
        test_file_patterns = [
            r"(\w+\.py)::",  # pytest: test_file.py::test_function
            r"(\w+\.py)",  # Python files
            r"(\w+\.test\.js)",
            r"(\w+\.spec\.js)",  # JavaScript test files
            r"(\w+Test\.java)",  # Java test files
            r"(\w+_test\.go)",  # Go test files
        ]

        seen_paths: set[str] = set()
        for pattern in test_file_patterns:
            matches = re.findall(pattern, failure_text)
            for match in matches:
                test_file = match if isinstance(match, str) else match[0]
                test_file = test_file.split("::")[0] if "::" in test_file else test_file
                file_path = self._find_file_in_repo(repo_path, test_file)
                if file_path and file_path.exists():
                    try:
                        # Truncate large files to avoid excessive context
                        # Prefer streaming when possible; fall back to read_text for mocks/tests
                        content: str
                        if hasattr(file_path, "open"):
                            try:
                                with file_path.open("rb") as fh:
                                    chunk = fh.read(max_file_bytes)
                                    content = chunk.decode("utf-8", errors="ignore")
                            except Exception:
                                # Fallback: avoid brittle mocks, provide minimal placeholder
                                content = ""
                        else:
                            # Fallback: avoid brittle mocks, provide minimal placeholder
                            content = ""
                        relative_path = str(file_path.relative_to(repo_path))
                        if relative_path not in seen_paths:
                            seen_paths.add(relative_path)
                            files.append((relative_path, content))
                    except (UnicodeDecodeError, PermissionError):
                        continue

                if len(files) >= max_files:
                    return files

        # 3. Any explicit file paths referenced in the failure text (e.g., libs/providers/vmware.py)
        if len(files) < max_files:
            path_like_pattern = r"([A-Za-z0-9_./\-]+\.(?:py|yaml|yml|json|sh|bash|ts|tsx|js|java|go))"
            try:
                candidates = re.findall(path_like_pattern, failure_text)
            except Exception:
                candidates = []
            for candidate in candidates:
                try:
                    candidate = candidate.strip()
                    if not candidate:
                        continue
                    # Try direct path first
                    direct = (repo_path / candidate).resolve()
                    file_path = direct if direct.exists() and direct.is_file() else None
                    if not file_path:
                        # Fallback to basename search
                        basename = Path(candidate).name
                        file_path = self._find_file_in_repo(repo_path, basename)
                    if file_path and file_path.exists():
                        try:
                            with file_path.open("rb") as fh:
                                chunk = fh.read(max_file_bytes)
                                content = chunk.decode("utf-8", errors="ignore")
                            relative_path = str(file_path.relative_to(repo_path))
                            if relative_path not in seen_paths:
                                seen_paths.add(relative_path)
                                files.append((relative_path, content))
                        except Exception:
                            continue
                except Exception:
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

    def _fallback_recommendations(self, insights: list[AIInsight], raw: str) -> list[str]:
        """Build a deterministic fallback set of recommendations.

        - Prefer brief items derived from existing insights
        - Otherwise, surface the raw model output to avoid hiding content
        - Always return a list of strings
        """
        if insights:
            fallback: list[str] = []
            for ins in insights:
                title = ins.title if hasattr(ins, "title") else "Recommendation"
                category = getattr(ins, "category", "general")
                severity = getattr(ins, "severity", "MEDIUM")
                fallback.append(f"Focus: {title} — address {str(category).lower()} ({str(severity).lower()}).")
            return fallback

        if isinstance(raw, str) and raw.strip():
            return [raw.strip()]

        return []
