"""Pydantic schemas for TestInsight AI."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AIInsight(BaseModel):
    """AI-generated insight."""

    title: str = Field(..., description="Insight title")
    description: str = Field(..., description="Detailed description")
    severity: Severity = Field(..., description="Issue severity")
    category: str = Field(..., description="Issue category")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")


class AnalysisRequest(BaseModel):
    """Request for test analysis."""

    text: str = Field(..., description="Text content to analyze (logs, junit xml, etc.)")
    custom_context: str | None = Field(None, description="Additional context")
    system_prompt: str | None = Field(None, description="Custom system prompt for the AI")
    repository_url: str | None = Field(None, description="GitHub repository URL for code context")
    repository_branch: str | None = Field(None, description="Repository branch to analyze")
    repository_commit: str | None = Field(None, description="Repository commit hash to analyze")
    include_repository_context: bool = Field(False, description="Include repository source code in analysis")
    cloned_repo_path: str | None = None
    repo_max_files: int | None = Field(None, ge=1, description="Max repo files to include in context")
    repo_max_bytes: int | None = Field(None, ge=1024, description="Max bytes per repo file to include")


class AnalysisResponse(BaseModel):
    """Response from test analysis."""

    insights: list[AIInsight] = Field(default_factory=list, description="AI-generated insights")
    summary: str = Field(..., description="Analysis summary")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")


class JenkinsSettings(BaseModel):
    """Jenkins connection settings."""

    url: str | None = Field(None, description="Jenkins server URL")
    username: str | None = Field(None, description="Jenkins username")
    api_token: str | None = Field(None, description="Jenkins API token")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")


class GitHubSettings(BaseModel):
    """GitHub settings."""

    token: str | None = Field(None, description="GitHub personal access token")


class AISettings(BaseModel):
    """AI service settings."""

    gemini_api_key: str | None = Field(None, description="Google Gemini API key")
    model: str = Field("", description="Gemini model to use")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="AI temperature setting")
    max_tokens: int = Field(4096, ge=1, le=32768, description="Maximum tokens for AI responses")


class AppSettings(BaseModel):
    """Complete application settings."""

    # Use BaseModel defaults directly to avoid Pydantic Field default_factory typing issues
    jenkins: JenkinsSettings = JenkinsSettings()
    github: GitHubSettings = GitHubSettings()
    ai: AISettings = AISettings()
    last_updated: datetime | None = Field(None, description="Last settings update timestamp")


class SettingsUpdate(BaseModel):
    """Settings update request."""

    jenkins: JenkinsSettings | None = Field(None, description="Jenkins settings to update")
    github: GitHubSettings | None = Field(None, description="GitHub settings to update")
    ai: AISettings | None = Field(None, description="AI settings to update")


class ConnectionTestResult(BaseModel):
    """Connection test result."""

    service: str = Field(..., description="Service name")
    success: bool = Field(..., description="Connection success status")
    message: str = Field(..., description="Test result message")
    error_details: str | None = Field(None, description="Error details if failed")


class GeminiModelInfo(BaseModel):
    """Gemini model information from Google AI API."""

    name: str = Field(..., description="Model name identifier")
    display_name: str = Field(..., description="Human-readable model name")
    description: str | None = Field(None, description="Model description")
    version: str | None = Field(None, description="Model version")
    input_token_limit: int | None = Field(None, description="Maximum input tokens")
    output_token_limit: int | None = Field(None, description="Maximum output tokens")
    supported_generation_methods: list[str] = Field(default_factory=list, description="Supported generation methods")


class GeminiModelsResponse(BaseModel):
    """Response containing available Gemini models."""

    success: bool = Field(..., description="Whether the request was successful")
    models: list[GeminiModelInfo] = Field(default_factory=list, description="Available Gemini models")
    total_count: int = Field(..., description="Total number of models")
    message: str | None = Field(None, description="Response message")
    error_details: str | None = Field(None, description="Error details if failed")


class TestConnectionWithParamsRequest(BaseModel):
    """Request to test connection with custom parameters."""

    service: str = Field(..., description="Service to test (jenkins, github, ai)")
    config: dict[str, Any] = Field(..., description="Configuration parameters for the service")
