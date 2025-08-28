"""Tests for analysis endpoints."""

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


def test_analyze_success(client: TestClient):
    """Test successful analysis."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.insights = []
        mock_analysis.summary = "Test analysis summary"
        mock_analysis.recommendations = ["Improve test coverage"]
        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        response = client.post(
            "/api/v1/analyze",
            data={"text": "fake test results", "custom_context": "fake context"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "insights" in data
        assert "summary" in data
        assert "recommendations" in data
        assert data["summary"] == "Test analysis summary"
        assert data["recommendations"] == ["Improve test coverage"]


def test_analyze_with_repo_clone(client: TestClient):
    """Test analysis with repository cloning."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.summary = "Summary"
        mock_analysis.recommendations = []
        mock_analysis.insights = []
        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        mock_git_client = Mock()
        mock_git_client.repo_path = "/tmp/fake_repo"
        mock_service_config.return_value.create_configured_git_client.return_value = mock_git_client

        response = client.post(
            "/api/v1/analyze",
            data={
                "text": "fake test results",
                "repository_url": "https://github.com/fake/repo.git",
                "include_repository_context": "true",
            },
        )

        assert response.status_code == 200
        mock_service_config.return_value.create_configured_git_client.assert_called_once()


def test_analyze_with_repo_clone_failure(client: TestClient):
    """Test analysis with repository cloning failure."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.summary = "Summary"
        mock_analysis.recommendations = []
        mock_analysis.insights = []
        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer
        mock_service_config.return_value.create_configured_git_client.side_effect = Exception("Clone failed")

        response = client.post(
            "/api/v1/analyze",
            data={
                "text": "fake test results",
                "repository_url": "https://github.com/fake/repo.git",
                "include_repository_context": "true",
            },
        )

        assert response.status_code == 200


def test_analyze_secret_leak_prevention(client: TestClient):
    """Test that clone failure warnings don't leak credentials in analysis text."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        with patch("backend.api.routers.analysis.logger") as mock_logger:
            mock_ai_analyzer = Mock()
            mock_analysis = Mock()
            mock_analysis.summary = "Summary"
            mock_analysis.recommendations = []
            mock_analysis.insights = []
            mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
            mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer
            mock_service_config.return_value.create_configured_git_client.side_effect = Exception("Clone failed")

            # Use a repo URL with credentials
            sensitive_repo_url = "https://token123:secret456@github.com/fake/repo.git"

            response = client.post(
                "/api/v1/analyze",
                data={
                    "text": "fake test results",
                    "repository_url": sensitive_repo_url,
                    "include_repository_context": "true",
                },
            )

            assert response.status_code == 200

            # Verify that warning was logged
            mock_logger.warning.assert_called_once()

            # Get the logged warning message
            warning_call_args = mock_logger.warning.call_args[0]
            logged_message = warning_call_args[0]

            # Assert that credentials are not leaked in the warning
            assert "token123" not in logged_message
            assert "secret456" not in logged_message
            assert "Repository cloning failed for url=" in logged_message
            # Should have redacted URL
            assert "***" in warning_call_args[1]  # The redacted URL parameter

            # Ensure secrets are not present in any logged args
            all_args_str = " ".join(map(str, mock_logger.warning.call_args[0]))
            assert "token123" not in all_args_str
            assert "secret456" not in all_args_str

            # Ensure secrets are not surfaced back to the client
            summary = response.json()["summary"]
            assert "token123" not in summary
            assert "secret456" not in summary


def test_analyze_repo_limits_validation(client: TestClient):
    """Test 422 responses for invalid repo limit bounds across endpoints."""

    # Test analyze endpoint
    # Invalid repo_max_files (too low)
    response = client.post(
        "/api/v1/analyze",
        data={"text": "fake test results", "repo_max_files": "0"},
    )
    assert response.status_code == 422
    assert "repo_max_files must be between 1 and 500" in response.json()["detail"]

    # Invalid repo_max_files (too high)
    response = client.post(
        "/api/v1/analyze",
        data={"text": "fake test results", "repo_max_files": "1000"},
    )
    assert response.status_code == 422
    assert "repo_max_files must be between 1 and 500" in response.json()["detail"]

    # Invalid repo_max_bytes (too low)
    response = client.post(
        "/api/v1/analyze",
        data={"text": "fake test results", "repo_max_bytes": "500"},
    )
    assert response.status_code == 422
    assert "repo_max_bytes must be between 1KB and 2MB" in response.json()["detail"]

    # Invalid repo_max_bytes (too high)
    response = client.post(
        "/api/v1/analyze",
        data={"text": "fake test results", "repo_max_bytes": "3000000"},
    )
    assert response.status_code == 422
    assert "repo_max_bytes must be between 1KB and 2MB" in response.json()["detail"]


def test_analyze_file_repo_limits_validation(client: TestClient):
    """Test 422 responses for invalid repo limit bounds in file endpoint."""
    files = {"files": ("test.xml", "<testsuite/>", "application/xml")}

    # Invalid repo_max_files
    response = client.post(
        "/api/v1/analyze/file",
        files=files,
        data={"repo_max_files": "0"},
    )
    assert response.status_code == 422
    assert "repo_max_files must be between 1 and 500" in response.json()["detail"]

    # Invalid repo_max_bytes
    response = client.post(
        "/api/v1/analyze/file",
        files=files,
        data={"repo_max_bytes": "500"},
    )
    assert response.status_code == 422
    assert "repo_max_bytes must be between 1KB and 2MB" in response.json()["detail"]


def test_analyze_jenkins_repo_limits_validation(client: TestClient):
    """Test 422 responses for invalid repo limit bounds in Jenkins endpoint."""

    # Invalid repo_max_files
    response = client.post(
        "/api/v1/analyze/jenkins",
        data={"job_name": "test-job", "repo_max_files": "600"},
    )
    assert response.status_code == 422
    assert "repo_max_files must be between 1 and 500" in response.json()["detail"]

    # Invalid repo_max_bytes
    response = client.post(
        "/api/v1/analyze/jenkins",
        data={"job_name": "test-job", "repo_max_bytes": "100"},
    )
    assert response.status_code == 422
    assert "repo_max_bytes must be between 1KB and 2MB" in response.json()["detail"]


def test_analyze_file_success(client: TestClient):
    """Test successful file analysis."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.insights = []
        mock_analysis.summary = "Test file analysis summary"
        mock_analysis.recommendations = ["Improve file test coverage"]
        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        files = {"files": ("test.xml", "<testsuite/>", "application/xml")}
        response = client.post("/api/v1/analyze/file", files=files)

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Test file analysis summary"


def test_analyze_file_invalid_type(client: TestClient):
    """Test file analysis with invalid file type."""
    files = {"files": ("test.pdf", "some content", "application/pdf")}
    response = client.post("/api/v1/analyze/file", files=files)
    assert response.status_code == 400


def test_analyze_file_no_filename(client: TestClient):
    """Test file analysis with no filename."""
    files = {"files": (None, "some content", "application/xml")}
    response = client.post("/api/v1/analyze/file", files=files)
    assert response.status_code == 422


def test_analyze_file_empty_content(client: TestClient):
    """Test file analysis with empty content."""
    files = {"files": ("test.xml", "", "application/xml")}
    response = client.post("/api/v1/analyze/file", files=files)
    assert response.status_code == 500


def test_analyze_file_unicode_error(client: TestClient):
    """Test file analysis with unicode error."""
    files = {"files": ("test.log", b"\x80abc", "text/plain")}
    response = client.post("/api/v1/analyze/file", files=files)
    assert response.status_code == 400


def test_analyze_jenkins_build_success(client: TestClient):
    """Test successful Jenkins build analysis."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_ai_analyzer = Mock()
        mock_analysis = Mock()
        mock_analysis.insights = []
        mock_analysis.summary = "Test Jenkins analysis summary"
        mock_analysis.recommendations = ["Improve Jenkins test coverage"]
        mock_ai_analyzer.analyze_test_results.return_value = mock_analysis
        mock_service_config.return_value.create_configured_ai_client.return_value = mock_ai_analyzer

        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_build_test_report.return_value = "{}"
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job", "build_number": "1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["summary"] == "Test Jenkins analysis summary"


def test_analyze_jenkins_build_not_connected(client: TestClient):
    """Test Jenkins analysis when client is not connected."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = False
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job", "build_number": "1"},
        )

        assert response.status_code == 503


def test_analyze_jenkins_build_invalid_build_number(client: TestClient):
    """Test Jenkins analysis with invalid build number."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client
        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job", "build_number": "abc"},
        )
        assert response.status_code == 400


def test_analyze_jenkins_build_no_builds_found(client: TestClient):
    """Test Jenkins analysis when no builds are found."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_job_builds.return_value = []
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job"},
        )
        assert response.status_code == 404


def test_analyze_jenkins_build_no_build_number_in_latest(client: TestClient):
    """Test Jenkins analysis when latest build has no number."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_job_builds.return_value = [{}]  # No 'number' key
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job"},
        )
        assert response.status_code == 404


def test_analyze_jenkins_build_no_test_report(client: TestClient):
    """Test Jenkins analysis when no test report is found."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_jenkins_client = Mock()
        mock_jenkins_client.is_connected.return_value = True
        mock_jenkins_client.get_build_test_report.return_value = None
        mock_service_config.return_value.create_configured_jenkins_client.return_value = mock_jenkins_client

        response = client.post(
            "/api/v1/analyze/jenkins",
            data={"job_name": "test-job", "build_number": "1"},
        )
        assert response.status_code == 404


def test_analyze_no_ai_client(client: TestClient):
    """Test analysis when AI client is not configured."""
    with patch("backend.api.routers.analysis.ServiceClientCreators") as mock_service_config:
        mock_service_config.return_value.create_configured_ai_client.return_value = None
        response = client.post("/api/v1/analyze", data={"text": "fake test results"})
        assert response.status_code == 503
        assert "AI analyzer not configured" in response.json()["detail"]


def test_analyze_file_no_files(client: TestClient):
    """Test file analysis with no files provided."""
    response = client.post("/api/v1/analyze/file", files={})
    assert response.status_code == 422


def test_analyze_jenkins_build_no_job(client: TestClient):
    """Test Jenkins analysis with no job name."""
    response = client.post("/api/v1/analyze/jenkins", data={"build_number": "1"})
    assert response.status_code == 422
