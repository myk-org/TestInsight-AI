from pathlib import Path
from unittest.mock import Mock


from backend.services.ai_analyzer import AIAnalyzer
from backend.services.gemini_api import GeminiClient


def _make_repo(tmp_path: Path) -> Path:
    # Create a minimal repo structure
    (tmp_path / "tests" / "unit").mkdir(parents=True, exist_ok=True)
    f = tmp_path / "tests" / "unit" / "test_sample.py"
    f.write_text("print('ok')\n", encoding="utf-8")
    return tmp_path


def test_find_file_in_repo_handles_absolute_posix(tmp_path: Path):
    repo = _make_repo(tmp_path)
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    abs_like = "/var/lib/jenkins/workspace/job/tests/unit/test_sample.py"
    found = analyzer._find_file_in_repo(repo, abs_like)
    assert found is not None
    assert found.name == "test_sample.py"
    assert str(found.resolve()).startswith(str(repo.resolve()))


def test_find_file_in_repo_handles_windows_path(tmp_path: Path):
    repo = _make_repo(tmp_path)
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    windows_like = "C:\\agent\\_work\\1\\s\\tests\\unit\\test_sample.py"
    found = analyzer._find_file_in_repo(repo, windows_like)
    assert found is not None
    assert found.name == "test_sample.py"


def test_find_file_in_repo_relative_subpath(tmp_path: Path):
    repo = _make_repo(tmp_path)
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    rel = "tests/unit/test_sample.py"
    found = analyzer._find_file_in_repo(repo, rel)
    assert found is not None
    assert found.name == "test_sample.py"


def test_find_file_in_repo_nonexistent_returns_none(tmp_path: Path):
    repo = _make_repo(tmp_path)
    mock_client = Mock(spec=GeminiClient)
    analyzer = AIAnalyzer(client=mock_client)

    not_there = "/abs/path/does/not/exist.py"
    found = analyzer._find_file_in_repo(repo, not_there)
    assert found is None
