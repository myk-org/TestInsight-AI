"""Tests for Pydantic models and schemas."""

from backend.models.schemas import (
    AIInsight,
    AnalysisRequest,
    AnalysisResponse,
    ConnectionTestResult,
    GeminiModelInfo,
    GeminiModelsRequest,
    GeminiModelsResponse,
    Severity,
    TestCase,
    TestSuite,
    TestStatus,
    TestConnectionWithParamsRequest,
)


class TestSeverityEnum:
    """Test Severity enum."""

    def test_severity_values(self):
        """Test all severity enum values."""
        assert Severity.LOW.value == "low"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.HIGH.value == "high"
        assert Severity.CRITICAL.value == "critical"


class TestTestStatusEnum:
    """Test TestStatus enum."""

    def test_test_status_values(self):
        """Test all test status enum values."""
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.SKIPPED.value == "skipped"
        assert TestStatus.ERROR.value == "error"


class TestAIInsight:
    """Test AIInsight model."""

    def test_valid_ai_insight(self):
        """Test valid AIInsight creation."""
        insight = AIInsight(
            title="Test Issue",
            description="Fake test failure description",
            severity=Severity.HIGH,
            category="Testing",
            suggestions=["Fix test setup", "Review assertions"],
            confidence=0.85,
        )
        assert insight.title == "Test Issue"
        assert insight.severity == Severity.HIGH
        assert len(insight.suggestions) == 2
        assert insight.confidence == 0.85

    def test_ai_insight_defaults(self):
        """Test AIInsight with default values."""
        insight = AIInsight(
            title="Test Issue",
            description="Fake description",
            severity=Severity.LOW,
            category="Testing",
            confidence=0.0,
        )
        assert insight.suggestions == []
        assert insight.confidence == 0.0


class TestAnalysisRequest:
    """Test AnalysisRequest model."""

    def test_valid_analysis_request(self):
        """Test valid AnalysisRequest creation."""
        request = AnalysisRequest(text="Fake test results content", custom_context="Fake analysis context")
        assert request.text == "Fake test results content"
        assert request.custom_context == "Fake analysis context"

    def test_analysis_request_optional_fields(self):
        """Test AnalysisRequest with optional fields."""
        request = AnalysisRequest(text="Fake test results")
        assert request.text == "Fake test results"
        assert request.custom_context is None


class TestAnalysisResponse:
    """Test AnalysisResponse model."""

    def test_valid_analysis_response(self):
        """Test valid AnalysisResponse creation."""
        insights = [
            AIInsight(
                title="Test Issue",
                description="Fake description",
                severity=Severity.HIGH,
                category="Testing",
                confidence=0.85,
            )
        ]
        response = AnalysisResponse(
            insights=insights, summary="Fake analysis summary", recommendations=["Fix tests", "Update config"]
        )
        assert len(response.insights) == 1
        assert response.summary == "Fake analysis summary"
        assert len(response.recommendations) == 2


class TestConnectionTestResult:
    """Test ConnectionTestResult model."""

    def test_successful_connection_result(self):
        """Test successful connection test result."""
        result = ConnectionTestResult(
            service="jenkins", success=True, message="Connection successful", error_details=""
        )
        assert result.service == "jenkins"
        assert result.success is True
        assert result.message == "Connection successful"
        assert result.error_details == ""

    def test_failed_connection_result(self):
        """Test failed connection test result."""
        result = ConnectionTestResult(
            service="github", success=False, message="Connection failed", error_details="Invalid token"
        )
        assert result.service == "github"
        assert result.success is False
        assert result.error_details == "Invalid token"


class TestGeminiModelInfo:
    """Test GeminiModelInfo model."""

    def test_valid_gemini_model_info(self):
        """Test valid GeminiModelInfo creation."""
        model = GeminiModelInfo(
            name="gemini-1.5-pro",
            display_name="Gemini 1.5 Pro",
            description="Fake model for testing",
            version="1.5",
            input_token_limit=8192,
            output_token_limit=8192,
            supported_generation_methods=["generateContent"],
        )
        assert model.name == "gemini-1.5-pro"
        assert model.input_token_limit == 8192
        assert len(model.supported_generation_methods) == 1

    def test_gemini_model_info_defaults(self):
        """Test GeminiModelInfo with default values."""
        model = GeminiModelInfo(name="gemini-test", display_name="Test Model")
        assert model.description is None or model.description == ""
        assert model.version is None or model.version == ""
        assert model.input_token_limit is None or model.input_token_limit == 0
        assert model.supported_generation_methods == []


class TestGeminiModelsRequest:
    """Test GeminiModelsRequest model."""

    def test_valid_gemini_models_request(self):
        """Test valid GeminiModelsRequest creation."""
        request = GeminiModelsRequest(api_key="AIzaSyFakeKeyExample123456789")  # pragma: allowlist secret
        assert request.api_key == "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret


class TestGeminiModelsResponse:
    """Test GeminiModelsResponse model."""

    def test_successful_gemini_models_response(self):
        """Test successful Gemini models response."""
        models = [GeminiModelInfo(name="gemini-1.5-pro", display_name="Gemini 1.5 Pro")]
        response = GeminiModelsResponse(
            success=True, models=models, total_count=1, message="Successfully fetched models", error_details=""
        )
        assert response.success is True
        assert len(response.models) == 1
        assert response.total_count == 1

    def test_failed_gemini_models_response(self):
        """Test failed Gemini models response."""
        response = GeminiModelsResponse(
            success=False, models=[], total_count=0, message="Failed to fetch models", error_details="Invalid API key"
        )
        assert response.success is False
        assert len(response.models) == 0
        assert response.error_details == "Invalid API key"


class TestTestCase:
    """Test TestCase model."""

    def test_valid_test_case(self):
        """Test valid TestCase creation."""
        test_case = TestCase(name="test_fake_function", class_name="TestFakeClass", time=1.23, status=TestStatus.PASSED)
        assert test_case.name == "test_fake_function"
        assert test_case.status == TestStatus.PASSED
        assert test_case.time == 1.23

    def test_test_case_with_failure(self):
        """Test TestCase with failure message."""
        test_case = TestCase(
            name="test_fake_failure",
            class_name="TestFakeClass",
            time=0.5,
            status=TestStatus.FAILED,
            message="Assertion failed: expected True but got False",
        )
        assert test_case.status == TestStatus.FAILED
        assert test_case.message == "Assertion failed: expected True but got False"


class TestTestSuite:
    """Test TestSuite model."""

    def test_valid_test_suite(self):
        """Test valid TestSuite creation."""
        test_cases = [
            TestCase(name="test_1", class_name="TestClass", time=1.0, status=TestStatus.PASSED),
            TestCase(name="test_2", class_name="TestClass", time=0.5, status=TestStatus.FAILED),
        ]

        suite = TestSuite(
            name="FakeTestSuite", tests=2, failures=1, errors=0, skipped=0, time=1.5, test_cases=test_cases
        )

        assert suite.name == "FakeTestSuite"
        assert suite.tests == 2
        assert suite.failures == 1
        assert len(suite.test_cases) == 2


class TestTestConnectionWithParamsRequest:
    """Test TestConnectionWithParamsRequest model."""

    def test_jenkins_connection_request(self):
        """Test Jenkins connection test request."""
        request = TestConnectionWithParamsRequest(
            service="jenkins",
            config={
                "url": "https://fake-jenkins.example.com",
                "username": "testuser",
                "api_token": "fake_token_123",  # pragma: allowlist secret
                "verify_ssl": False,
            },
        )
        assert request.service == "jenkins"
        assert request.config["url"] == "https://fake-jenkins.example.com"

    def test_github_connection_request(self):
        """Test GitHub connection test request."""
        request = TestConnectionWithParamsRequest(
            service="github", config={"token": "fake_github_token_xyz"}
        )  # pragma: allowlist secret
        assert request.service == "github"
        assert request.config["token"] == "fake_github_token_xyz"  # pragma: allowlist secret

    def test_ai_connection_request(self):
        """Test AI connection test request."""
        request = TestConnectionWithParamsRequest(
            service="ai",
            config={
                "gemini_api_key": "AIzaSyFakeKeyExample123456789",  # pragma: allowlist secret
                "gemini_model": "gemini-1.5-pro",
            },
        )
        assert request.service == "ai"
        assert request.config["gemini_api_key"] == "AIzaSyFakeKeyExample123456789"  # pragma: allowlist secret
