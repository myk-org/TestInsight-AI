# TestInsight AI Backend

**Lightweight FastAPI-based backend service providing AI-powered test analysis capabilities.**

This self-contained backend service orchestrates test result analysis through multiple specialized services including AI analysis, Jenkins integration, and Git repository analysis. No external databases or message queues required - all data is stored locally with encryption.

## Architecture

### Service Architecture

```
┌─────────────────┐
│   FastAPI App   │
│   (main.py)     │
└─────────┬───────┘
          │
    ┌─────┴─────┐
    │  API Routes │
    │ (api/main.py)│
    └─────┬─────┘
          │
┌─────────┴─────────┐
│    Core Services  │
├───────────────────┤
│ • AI Analyzer     │
│ • Jenkins Client  │
│ • Git Client      │
│ • Settings Service│
│ • Security Utils  │
└───────────────────┘
          │
┌─────────┴─────────┐
│   Local Storage   │
├───────────────────┤
│ • JSON Files      │
│ • AES Encryption  │
│ • No External DB  │
└───────────────────┘
```

### Directory Structure

```
backend/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── api/
│   ├── __init__.py
│   └── routers/            # API route definitions
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic data models
└── services/
    ├── __init__.py
    ├── ai_analyzer.py      # Google Gemini AI integration
    ├── git_client.py       # Git operations
    ├── jenkins_client.py   # Jenkins integration
    ├── settings_service.py # Settings management with encryption
    ├── security_utils.py   # Encryption and security utilities
    └── service_config/     # Service configuration management
```

## Core Services

### AI Analyzer (`ai_analyzer.py`)

**Purpose**: Provides intelligent analysis of test results using Google Gemini AI. Takes raw data input and returns AI-generated insights, summaries, and recommendations.

**Key Features**:
- Root cause analysis of test failures
- Intelligent fix suggestions
- Pattern recognition across multiple failures
- Context-aware analysis using code changes and logs
- Severity assessment and prioritization

**Usage**:
```python
from backend.services.ai_analyzer import AIAnalyzer
from backend.models.schemas import AnalysisRequest

analyzer = AIAnalyzer()
request = AnalysisRequest(
    text="...",
    custom_context="Additional context"
)
analysis = analyzer.analyze_test_results(request)
# Returns: insights, summary, recommendations
```


### Jenkins Client (`jenkins_client.py`)

**Purpose**: Jenkins integration for automated build and test analysis.

**Capabilities**:
- Build information retrieval
- Test report fetching
- Job status monitoring
- Jobs listing with search
- Connection testing
- Fuzzy search support

**Usage**:
```python
from backend.services.jenkins_client import JenkinsClient

client = JenkinsClient(url="...", username="...", password="...")
build_info = client.get_build_info("job-name", 123)
jobs_list = client.list_jobs()
```

### Git Client (`git_client.py`)

**Purpose**: Git repository analysis with private repository support.

**Features**:
- Private repository support
- Commit-specific cloning
- GitPython integration
- On-demand repository cloning

**Usage**:
```python
from backend.services.git_client import GitClient

client = GitClient(repo_url="...", github_token="...")
# The client clones the repo on initialization
```

### Settings Service (`settings_service.py`)

**Purpose**: Manages application settings with secure storage and encryption.

**Features**:
- Encrypted storage for sensitive settings
- Local JSON file storage
- Validation of configuration values
- Connection testing for external services
- Backup and restore functionality

**Configuration Categories**:
- Jenkins settings
- GitHub settings
- AI settings

### Security Utils (`security_utils.py`)

**Purpose**: Provides encryption and security utilities for sensitive data.

**Features**:
- AES-256 encryption
- Key management
- Input validation and sanitization

## API Endpoints

### Analysis Endpoints

- `POST /api/v1/analyze`: Analyze text content with AI.
- `POST /api/v1/analyze-file`: Analyze uploaded files with AI.
- `POST /api/v1/analyze-jenkins`: Analyze Jenkins build output with AI.

### Jenkins Integration Endpoints

- `GET /api/v1/jenkins/jobs`: List all available Jenkins jobs.
- `GET /api/v1/jenkins/{job_name}/builds`: Get recent builds for a Jenkins job.

### Git Integration Endpoints

- `POST /api/v1/git/clone`: Clone a repository.

### Settings Management Endpoints

- `GET /api/v1/settings`: Get current application settings.
- `PUT /api/v1/settings`: Update application settings.
- `POST /api/v1/settings/reset`: Reset all settings to defaults.
- `GET /api/v1/settings/validate`: Validate current settings.
- `GET /api/v1/settings/secrets-status`: Get status of whether secrets are configured.
- `POST /api/v1/settings/test-connection`: Test connection to a configured service.
- `POST /api/v1/settings/test-connection-with-config`: Test connection with custom parameters.
- `GET /api/v1/settings/backup`: Create a backup of current settings.
- `POST /api/v1/settings/restore`: Restore settings from an uploaded backup file.

### AI Endpoints

- `POST /api/v1/ai/models`: Fetch available Gemini models.
- `POST /api/v1/ai/models/validate-key`: Validate the configured Gemini API key.

### System Endpoints

- `GET /api/v1/status`: Get status of all services.

## Data Models

### Core Models (defined in `models/schemas.py`)

- `AnalysisRequest`: Defines the structure for a test analysis request.
- `AnalysisResponse`: Defines the structure for a test analysis response.
- `AIInsight`: Represents an AI-generated insight.
- `Severity`: Enum for issue severity levels.
- `AppSettings`: The main model for all application settings.

## Development Setup

### Local Development

```bash
# Install dependencies
uv sync

# Run development server with auto-reload
uv run python -m backend.main
```

### Testing

**Recommended: Use tox for testing**

```bash
# Run all default environments (unit tests, linting, type checking)
tox
```

**Alternative: Direct pytest commands**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov-report=html
```

---

**For complete project documentation, see the [main README](../README.md)**
