# TestInsight AI Backend

**Lightweight FastAPI-based backend service providing AI-powered test analysis capabilities.**

This self-contained backend service orchestrates test result analysis through multiple specialized services including AI analysis, Jenkins integration, Git repository analysis, and intelligent parsing of test outputs. No external databases or message queues required - all data is stored locally with encryption.

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
    │ (endpoints.py)│
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
│   └── endpoints.py        # API route definitions
├── models/
│   ├── __init__.py
│   └── schemas.py          # Pydantic data models
└── services/
    ├── __init__.py
    ├── ai_analyzer.py      # Google Gemini AI integration
    ├── git_client.py       # Enhanced Git operations with private repos
    ├── jenkins_client.py   # Enhanced Jenkins integration with jobs listing
    ├── settings_service.py # Settings management with encryption
    ├── security_utils.py   # Encryption and security utilities
    └── service_config.py   # Service configuration management
```

## Core Services

### AI Analyzer (`ai_analyzer.py`)

**Purpose**: Provides intelligent analysis of test results using Google Gemini AI. Takes raw data input (JUnit XML strings, log strings) and returns AI-generated insights, summaries, and recommendations.

**Key Features**:
- Direct processing of raw JUnit XML and log content
- Root cause analysis of test failures
- Intelligent fix suggestions
- Pattern recognition across multiple failures
- Context-aware analysis using code changes and logs
- Severity assessment and prioritization
- No preprocessing or parsing required - AI handles everything

**Configuration**:
```python
# Environment variables required (or configured via Settings API)
GOOGLE_API_KEY=your_gemini_api_key

# Configurable AI models and parameters
AI_MODEL=gemini-1.5-pro  # Default model
AI_TEMPERATURE=0.7       # Default temperature
AI_MAX_TOKENS=8192       # Default max tokens
```

**Usage**:
```python
from backend.services.ai_analyzer import AIAnalyzer
from backend.models.schemas import AnalysisRequest

analyzer = AIAnalyzer()
request = AnalysisRequest(
    junit_xml=junit_xml_string,  # Raw JUnit XML content
    logs=log_content_string,     # Raw log content
    custom_context="Additional context"
)
analysis = analyzer.analyze_test_results(request)
# Returns: insights, summary, recommendations
```


### Jenkins Client (`jenkins_client.py`)

**Purpose**: Enhanced Jenkins integration for automated build and test analysis.

**Capabilities**:
- Build information retrieval
- Console output access
- Test report fetching
- Artifact download
- Job status monitoring
- **Jobs listing with search** - List all available Jenkins jobs
- **Connection testing** - Verify Jenkins connectivity and credentials
- **Fuzzy search support** - Enhanced job discovery

**Configuration**:
```python
# Environment variables (or configured via Settings API)
JENKINS_URL=http://your-jenkins:8080
JENKINS_USERNAME=your_username
JENKINS_TOKEN=your_api_token
JENKINS_VERIFY_SSL=true  # SSL verification setting
```

**Usage**:
```python
from backend.services.jenkins_client import JenkinsClient

client = JenkinsClient()
build_info = client.get_build_info("job-name", 123)
console = client.get_build_console_output("job-name", 123)

# New features
jobs_list = client.list_jobs()  # List all available jobs
connection_test = client.test_connection()  # Test connectivity
```

### Git Client (`git_client.py`)

**Purpose**: Enhanced Git repository analysis with private repository support.

**Features**:
- Latest commit information
- Specific commit details
- Branch information
- File change analysis
- Commit message parsing
- **Private repository support** - Access private GitHub repositories with tokens
- **Commit-specific URLs** - Support for commit-specific repository URLs
- **GitPython integration** - Enhanced Git operations with full GitPython support
- **Repository cloning** - Clone and analyze repositories on-demand

**Usage**:
```python
from backend.services.git_client import GitClient

client = GitClient()
latest_commit = client.get_latest_commit()
commit_details = client.get_commit("sha123")

# New features with private repository support
client_with_token = GitClient(github_token="ghp_xxxx")
repo_info = client_with_token.clone_and_analyze(
    "https://github.com/user/private-repo",
    commit_sha="abc123"
)
```

### Settings Service (`settings_service.py`)

**Purpose**: Manages application settings with secure storage and encryption.

**Features**:
- **Encrypted storage** - All sensitive settings encrypted using AES-256
- **Local file storage** - No external database required, uses JSON files
- **Validation** - Comprehensive validation of all configuration values
- **Connection testing** - Test connectivity to external services
- **Backup and restore** - Settings backup functionality
- **Environment integration** - Seamless integration with environment variables
- **Real-time updates** - Settings changes applied immediately

**Configuration Categories**:
- **Jenkins settings** - URL, credentials, SSL verification
- **GitHub settings** - Personal access tokens, default repositories
- **AI settings** - Gemini API key, model selection, parameters
- **User preferences** - Theme, language, pagination settings

**Usage**:
```python
from backend.services.settings_service import get_settings_service

settings_service = get_settings_service()

# Get all settings
current_settings = await settings_service.get_settings()

# Update settings
new_settings = {"jenkins": {"url": "https://new-jenkins.com"}}
await settings_service.update_settings(new_settings)

# Test connection
result = await settings_service.test_connection("jenkins")

# Backup settings
backup_path = await settings_service.backup_settings()
```

### Security Utils (`security_utils.py`)

**Purpose**: Provides encryption and security utilities for sensitive data.

**Features**:
- **AES-256 encryption** - Strong encryption for sensitive settings
- **Key management** - Automatic key generation and management
- **Data validation** - Input validation and sanitization
- **Secure storage** - File-based encrypted storage
- **Password hashing** - Secure password and token handling

**Usage**:
```python
from backend.services.security_utils import SecurityUtils

# Encrypt sensitive data
encrypted = SecurityUtils.encrypt_data("sensitive_value")

# Decrypt when needed
decrypted = SecurityUtils.decrypt_data(encrypted)
```

## API Endpoints

### Analysis Endpoints

#### `POST /api/v1/analyze`
**Purpose**: Analyze test results with AI insights

**Request Body**:
```json
{
  "junit_xml": "<junit-xml-content>",
  "logs": "<log-content>",
  "custom_context": "Additional context",
  "build_info": {
    "number": 123,
    "url": "http://jenkins/job/123",
    "status": "FAILURE"
  },
  "git_commit": {
    "sha": "abc123",
    "message": "Fix authentication bug",
    "author": "developer@example.com"
  }
}
```

**Response**:
```json
{
  "summary": {
    "total_tests": 150,
    "failures": 5,
    "errors": 1,
    "skipped": 2,
    "success_rate": 94.67,
    "execution_time": 45.2
  },
  "ai_insights": {
    "overall_analysis": "The test failures indicate authentication issues...",
    "key_issues": [
      "Token expiration in authentication service",
      "Database connection timeout"
    ],
    "recommended_actions": [
      "Update token refresh mechanism",
      "Increase database connection timeout"
    ],
    "confidence_score": 0.92
  },
  "test_failures": [
    {
      "test_name": "test_user_login",
      "class_name": "TestAuthentication",
      "error_message": "AssertionError: Expected 200, got 401",
      "ai_analysis": "Authentication token has expired...",
      "suggested_fix": "Implement token refresh before test execution",
      "severity": "high",
      "file_path": "tests/test_auth.py",
      "line_number": 45
    }
  ],
  "junit_report": {
    "test_suites": [...],
    "summary": {...}
  },
  "log_entries": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "level": "ERROR",
      "message": "Token validation failed",
      "source": "auth-service"
    }
  ]
}
```

#### `POST /api/v1/analyze/upload`
**Purpose**: Upload and analyze test files

**Form Data**:
- `junit_file`: JUnit XML file (optional)
- `log_file`: Log file (optional)
- `custom_context`: Additional context string (optional)

**Response**: Same as `/analyze` endpoint

### Jenkins Integration Endpoints

#### `GET /api/v1/jenkins/jobs`
**Purpose**: List all available Jenkins jobs

**Response**:
```json
{
  "jobs": [
    {
      "name": "my-app-backend",
      "url": "http://jenkins/job/my-app-backend/",
      "description": "Backend service CI/CD pipeline",
      "buildable": true,
      "color": "red"
    },
    {
      "name": "my-app-frontend",
      "url": "http://jenkins/job/my-app-frontend/",
      "description": "Frontend application pipeline",
      "buildable": true,
      "color": "blue"
    }
  ],
  "total_jobs": 2
}
```

#### `GET /api/v1/jenkins/{job_name}/latest`
**Purpose**: Get latest build information

**Response**:
```json
{
  "number": 123,
  "url": "http://jenkins/job/my-job/123/",
  "status": "FAILURE",
  "timestamp": "2024-01-15T10:30:00Z",
  "duration": 300000,
  "result": "FAILURE"
}
```

#### `GET /api/v1/jenkins/{job_name}/{build_number}`
**Purpose**: Get specific build information

#### `GET /api/v1/jenkins/{job_name}/{build_number}/console`
**Purpose**: Get build console output

**Response**:
```json
{
  "console_output": "Started by user admin\n[Pipeline] Start of Pipeline..."
}
```

#### `GET /api/v1/jenkins/{job_name}/{build_number}/analyze`
**Purpose**: Analyze Jenkins build with AI

**Response**: Same as `/analyze` endpoint with Jenkins build context

### Git Integration Endpoints

#### `GET /api/v1/git/latest-commit`
**Purpose**: Get latest Git commit information

**Response**:
```json
{
  "sha": "abc123def456",  # pragma: allowlist secret
  "message": "Fix authentication bug in user service",
  "author": "developer@example.com",
  "timestamp": "2024-01-15T10:30:00Z",
  "files_changed": ["src/auth.py", "tests/test_auth.py"]
}
```

#### `GET /api/v1/git/commit/{sha}`
**Purpose**: Get specific commit information

### Settings Management Endpoints

#### `GET /api/v1/settings`
**Purpose**: Get current application settings

**Response**:
```json
{
  "jenkins": {
    "url": "https://jenkins.example.com",
    "username": "admin",
    "api_token": "***encrypted***",
    "verify_ssl": true
  },
  "github": {
    "token": "***encrypted***",
    "default_repo_url": "https://github.com/user/repo"
  },
  "ai": {
    "gemini_api_key": "***encrypted***",
    "gemini_model": "gemini-1.5-pro",
    "temperature": 0.7,
    "max_tokens": 8192
  },
  "preferences": {
    "theme": "dark",
    "language": "en",
    "results_per_page": 25,
    "auto_refresh": true
  }
}
```

#### `POST /api/v1/settings`
**Purpose**: Update application settings

**Request Body**:
```json
{
  "jenkins": {
    "url": "https://new-jenkins.example.com",
    "username": "new_admin",
    "api_token": "new_token_123"
  },
  "ai": {
    "temperature": 0.8,
    "max_tokens": 4096
  }
}
```

**Response**: Updated settings object (same format as GET)

#### `GET /api/v1/settings/test-connection/{service}`
**Purpose**: Test connection to external service

**Parameters**:
- `service`: Service name (`jenkins`, `github`, `ai`)

**Response**:
```json
{
  "service": "jenkins",
  "success": true,
  "message": "Connection successful",
  "response_time_ms": 234,
  "details": {
    "jenkins_version": "2.414.1",
    "available_jobs": 15
  }
}
```

#### `POST /api/v1/settings/backup`
**Purpose**: Create a backup of current settings

**Response**:
```json
{
  "backup_path": "/data/settings_backup_20240115_143022.json",
  "timestamp": "2024-01-15T14:30:22Z",
  "settings_count": 4
}
```

#### `POST /api/v1/settings/reset`
**Purpose**: Reset all settings to defaults

**Response**:
```json
{
  "message": "Settings reset to defaults successfully",
  "backup_created": "/data/settings_backup_before_reset_20240115_143055.json"
}
```

### Utility Endpoints

#### `POST /api/v1/junit/parse`
**Purpose**: Parse JUnit XML file only

#### `POST /api/v1/logs/parse`
**Purpose**: Parse log file only

#### `GET /api/v1/status`
**Purpose**: Get service health status

**Response**:
```json
{
  "services": {
    "jenkins": {
      "available": true,
      "url": "http://jenkins:8080"
    },
    "git": {
      "available": true,
      "repo_path": "/path/to/repo",
      "current_branch": "main"
    },
    "ai_analyzer": {
      "available": true,
      "provider": "Google Gemini"
    }
  },
  "parsers": {
    "junit": true,
    "logs": true
  }
}
```

## Data Models

### Core Models (defined in `models/schemas.py`)

#### `AnalysisRequest`
```python
class AnalysisRequest(BaseModel):
    junit_xml: Optional[str] = None
    logs: Optional[str] = None
    custom_context: Optional[str] = None
    build_info: Optional[BuildInfo] = None
    git_commit: Optional[GitCommit] = None
```

#### `AnalysisResponse`
```python
class AnalysisResponse(BaseModel):
    summary: TestSummary
    ai_insights: AIInsights
    test_failures: list[TestFailure]
    junit_report: Optional[JUnitReport] = None
    log_entries: list[LogEntry] = []
```

#### `TestFailure`
```python
class TestFailure(BaseModel):
    test_name: str
    class_name: str
    error_message: str
    ai_analysis: str
    suggested_fix: str
    severity: Severity
    file_path: Optional[str] = None
    line_number: Optional[int] = None
```

#### `AIInsights`
```python
class AIInsights(BaseModel):
    overall_analysis: str
    key_issues: list[str]
    recommended_actions: list[str]
    confidence_score: float
    analysis_timestamp: datetime
```

## Environment Configuration

### Environment Variables (Optional)

All configuration is managed through the Settings API. Environment variables are optional:

```bash
# Application Configuration (Optional)
DEBUG=false
HOST=0.0.0.0
PORT=8000

# Settings Encryption (auto-generated if not provided)
SETTINGS_ENCRYPTION_KEY=your_secret_encryption_key_here
```

### Configuration Loading

Environment variables are loaded in `main.py` using:
```python
from dotenv import load_dotenv
load_dotenv()
```

## Development Setup

### Local Development

```bash
# Install dependencies
uv sync

# Run development server with auto-reload
uv run python -m backend.main

# Or with explicit uvicorn
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### Development Tools

```bash
# Code formatting
uv run ruff format backend/

# Linting
uv run ruff check backend/ --fix

# Type checking
uv run mypy backend/

# Run all quality checks
uv run ruff format backend/ && \
uv run ruff check backend/ --fix && \
uv run mypy backend/
```

### Testing

**Recommended: Use tox for testing**

```bash
# Run all default environments (unit tests, linting, type checking)
tox

# Run specific environments
tox -e py312                     # Unit tests with Python 3.12
tox -e fast                      # Fast unit tests only
tox -e integration               # Integration tests
tox -e security                  # Security tests
tox -e coverage                  # Tests with coverage reporting
tox -e lint                      # Linting checks
tox -e type-check                # Type checking with mypy
tox -e format                    # Auto-format code

# Run all tests with coverage
tox -e coverage

# Clean up artifacts
tox -e clean
```

**Alternative: Direct pytest commands**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend --cov-report=html

# Run specific test categories
uv run pytest tests/unit/services/        # Service tests
uv run pytest tests/unit/api/            # API tests
uv run pytest tests/integration/         # Integration tests

# Run tests with specific markers
uv run pytest -m unit                    # Unit tests only
uv run pytest -m integration             # Integration tests only
uv run pytest -m security                # Security tests only

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/services/test_settings_service.py
```

### Test Structure

```
tests/
├── conftest.py                    # Pytest configuration and fixtures
├── fixtures/
│   └── sample_data.py            # Test data fixtures
├── unit/
│   ├── api/
│   │   └── test_endpoints.py     # API endpoint tests (including settings endpoints)
│   └── services/
│       ├── test_ai_analyzer.py   # AI analyzer tests
│       ├── test_git_client.py    # Enhanced Git client tests (private repos)
│       ├── test_jenkins_client.py # Enhanced Jenkins client tests (jobs listing)
│       ├── test_junit_parser.py  # JUnit parser tests
│       ├── test_log_parser.py    # Log parser tests
│       ├── test_settings_service.py # Settings service tests (encryption, validation)
│       ├── test_security_utils.py # Security utilities tests
│       └── test_service_config.py # Service configuration tests
└── integration/
    ├── test_full_analysis_workflow.py # End-to-end tests
    ├── test_settings_integration.py   # Settings integration tests
    └── test_security_integration.py   # Security integration tests
```

## Deployment

### Production Configuration

```python
# production.env
DEBUG=false
HOST=0.0.0.0
PORT=8000
GOOGLE_API_KEY=prod_api_key
JENKINS_URL=https://jenkins.company.com
```

### Docker Deployment

**Simplified deployment with only FastAPI backend - no external services required:**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Deployment

```bash
# Build and tag
docker build -t testinsight-ai-backend .

# Run with environment file
docker run -d \
  --name testinsight-backend \
  --env-file production.env \
  -p 8000:8000 \
  testinsight-ai-backend

# Or with docker-compose (simple single-service deployment)
version: '3.8'
services:
  backend:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data  # Persist local data
    env_file:
      - production.env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: testinsight-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: testinsight-backend
  template:
    metadata:
      labels:
        app: testinsight-backend
    spec:
      containers:
      - name: backend
        image: testinsight-ai-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: GOOGLE_API_KEY
          valueFrom:
            secretKeyRef:
              name: testinsight-secrets
              key: google-api-key
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## Security Considerations

### API Security

- **Encrypted Storage**: Sensitive fields (API keys, tokens) encrypted using AES-256 in local JSON files
- **Input Validation**: All inputs validated using Pydantic models
- **Error Handling**: Sanitized error messages to prevent information leakage

### External Integrations

- **Jenkins Authentication**: Use API tokens, not passwords
- **Google Gemini**: API key rotation and monitoring
- **Git Operations**: Read-only operations only
- **File Uploads**: Size limits and type validation

### Production Hardening

For production deployment on a public network, configure a reverse proxy (nginx, traefik, etc.) to handle SSL termination and access control. The application is designed for local network use with permissive CORS settings.

## Monitoring and Logging

### Health Monitoring

The `/health` endpoint provides service status:
- Application health
- External service connectivity
- Resource availability

### Logging Configuration

```python
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add request/response logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url} - {response.status_code} - {process_time:.2f}s")
    return response
```

### Metrics and Monitoring

Recommended monitoring setup:
- **Application Metrics**: Request counts, response times, error rates
- **Business Metrics**: Analysis requests, success rates, AI confidence scores
- **Infrastructure Metrics**: CPU, memory, disk usage
- **External Services**: Jenkins connectivity, Google API quotas

## Troubleshooting

### Common Issues

#### Google Gemini API Issues
```bash
# Check API key configuration
curl -H "x-goog-api-key: $GOOGLE_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"

# Verify quota and billing
# Visit: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
```

#### Jenkins Connectivity Issues
```bash
# Test Jenkins connection
curl -u username:token http://jenkins:8080/api/json

# Check credentials and permissions
# Ensure user has read access to jobs and builds
```

#### Git Repository Issues
```bash
# Verify git repository
git status
git log --oneline -5

# Check git client permissions
ls -la .git/
```

### Debug Mode

Enable debug mode for detailed logging:
```bash
DEBUG=true uv run python -m backend.main
```

### API Testing

Use the interactive API docs at http://localhost:8000/docs for testing endpoints.

## Performance Optimization

### Response Caching

Consider implementing caching for:
- Git commit information
- Jenkins build metadata
- AI analysis results (with appropriate TTL)

### Async Operations

All endpoints are async for better performance:
```python
@router.post("/analyze")
async def analyze_test_results(request: AnalysisRequest) -> AnalysisResponse:
    # Async processing for better concurrency
```

### Resource Management

- **Memory**: Limit file upload sizes
- **CPU**: Consider async processing for large analyses
- **Network**: Connection pooling for external services

---

**For complete project documentation, see the [main README](../README.md)**
