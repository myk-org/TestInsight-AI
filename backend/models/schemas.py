"""Pydantic schemas for TestInsight AI."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TestStatus(str, Enum):
    """Test execution status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TestCase(BaseModel):
    """Individual test case model."""

    name: str = Field(..., description="Test case name")
    class_name: str = Field(..., description="Test class name")
    time: float = Field(..., description="Execution time in seconds")
    status: TestStatus = Field(..., description="Test execution status")
    message: str | None = Field(None, description="Failure or error message")
    system_out: str | None = Field(None, description="System output")
    system_err: str | None = Field(None, description="System error output")


class TestSuite(BaseModel):
    """Test suite model."""

    name: str = Field(..., description="Test suite name")
    tests: int = Field(..., description="Total number of tests")
    failures: int = Field(..., description="Number of failed tests")
    errors: int = Field(..., description="Number of error tests")
    skipped: int = Field(..., description="Number of skipped tests")
    time: float = Field(..., description="Total execution time")
    timestamp: datetime | None = Field(None, description="Execution timestamp")
    test_cases: list[TestCase] = Field(default_factory=list, description="Test cases")


class JUnitReport(BaseModel):
    """JUnit XML report model."""

    test_suites: list[TestSuite] = Field(..., description="Test suites")
    total_tests: int = Field(..., description="Total number of tests")
    total_failures: int = Field(..., description="Total number of failures")
    total_errors: int = Field(..., description="Total number of errors")
    total_skipped: int = Field(..., description="Total number of skipped tests")
    total_time: float = Field(..., description="Total execution time")


class LogEntry(BaseModel):
    """Log entry model."""

    timestamp: datetime = Field(..., description="Log timestamp")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    source: str | None = Field(None, description="Log source")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class BuildInfo(BaseModel):
    """Jenkins build information."""

    job_name: str = Field(..., description="Jenkins job name")
    build_number: int = Field(..., description="Build number")
    status: str = Field(..., description="Build status")
    timestamp: datetime = Field(..., description="Build timestamp")
    duration: float = Field(..., description="Build duration in seconds")
    url: str = Field(..., description="Build URL")


class GitCommit(BaseModel):
    """Git commit information."""

    sha: str = Field(..., description="Commit SHA")
    author: str = Field(..., description="Commit author")
    message: str = Field(..., description="Commit message")
    timestamp: datetime = Field(..., description="Commit timestamp")
    url: str | None = Field(None, description="Commit URL")


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


class AnalysisResponse(BaseModel):
    """Response from test analysis."""

    insights: list[AIInsight] = Field(default_factory=list, description="AI-generated insights")
    summary: str = Field(..., description="Analysis summary")
    recommendations: list[str] = Field(default_factory=list, description="Recommendations")


class FileUpload(BaseModel):
    """File upload metadata."""

    filename: str = Field(..., description="Original filename")
    content_type: str = Field(..., description="File content type")
    size: int = Field(..., description="File size in bytes")


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    details: str | None = Field(None, description="Error details")
    code: str | None = Field(None, description="Error code")


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

    jenkins: JenkinsSettings = Field(default_factory=JenkinsSettings, description="Jenkins settings")
    github: GitHubSettings = Field(default_factory=GitHubSettings, description="GitHub settings")
    ai: AISettings = Field(default_factory=AISettings, description="AI settings")
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


class GeminiModelsRequest(BaseModel):
    """Request to fetch available Gemini models."""

    api_key: str | None = Field(None, description="Gemini API key (uses settings if not provided)")


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
