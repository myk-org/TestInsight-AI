# TestInsight AI

AI-powered test failure analysis tool that helps developers quickly diagnose and fix failing automated tests.

## 🚀 Features

### AI-Powered Analysis
- **Google Gemini Integration**: Advanced AI analysis using Gemini 1.5 Pro/Flash models
- **Intelligent Test Failure Analysis**: Root cause analysis with confidence scoring
- **Context-Aware Insights**: Incorporates code changes, logs, and build history
- **Actionable Recommendations**: Specific fix suggestions with code examples

### Multiple Input Methods
- **JUnit XML Upload**: Drag-and-drop JUnit test result files
- **Raw Log Analysis**: Paste console output from any test framework
- **Jenkins Integration**: Direct build analysis with job listing and fuzzy search
- **File Processing**: Batch analysis of multiple test files

### Repository Integration
- **GitHub Support**: Public and private repository access with token authentication
- **Commit-Specific Analysis**: Analyze tests against specific commits or branches
- **Code Context**: Fetches relevant source code for enhanced analysis
- **Git History**: Integrates commit messages and change logs

### Advanced Backend Features
- **Modular Service Architecture**: 8 specialized services (AI, Gemini API, Gemini Models, Jenkins, Git, Settings, Security, Config)
- **Comprehensive Test Suite**: 236 tests with 80% coverage and multiple test categories
- **Security-First Design**: AES-256 encryption, input validation, and secure storage
- **Modern Python Stack**: Python 3.12+, FastAPI, Pydantic, uv package manager
- **Production Ready**: Docker support, health checks, monitoring, and logging

### User Experience
- **Modern UI**: React with TypeScript and Tailwind CSS (Vite-based build)
- **Dark/Light Theme**: Persistent theme preferences
- **Real-time Configuration**: Live settings updates with connection testing
- **Responsive Design**: Works on desktop and mobile devices

## 📋 Requirements

- Python 3.12+ (for local development)
- Docker or Podman (for containerized deployment)
- uv package manager (for local Python development)
- Google Gemini API key
- (Optional) Jenkins instance for CI/CD integration
- (Optional) GitHub token for private repository access

## 🏗️ Architecture

TestInsight AI uses a modern two-service architecture:

- **Backend Service**: FastAPI-based REST API (Python 3.12+) with modular service architecture
  - AI-powered test failure analysis with Google Gemini integration
  - Jenkins CI/CD integration with job listing and fuzzy search
  - GitHub repository integration (public and private repos)
  - Local JSON-based settings with AES encryption for sensitive data
  - Comprehensive security with input sanitization and validation
  - Complete test suite with 236 tests achieving 80% coverage
- **Frontend Service**: React-based web interface with TypeScript and Tailwind CSS

No external databases or message queues are required - all data is stored locally in encrypted JSON format with automatic backup capabilities.

## 🐳 Installation

### Local Development Environment

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd testinsight-ai
   ```

2. **Install uv package manager** (if not already installed):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   # Or: pipx install uv
   ```

3. **Backend setup**:
   ```bash
   # Install Python dependencies
   uv sync

   # Configure environment
   cp .env.example .env
   # Edit .env with your API keys and settings

   # Start backend server
   uv run python -m backend.main
   ```

4. **Frontend setup** (in separate terminal):
   ```bash
   cd frontend
   npm install
   npm start
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Development Environment

1. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

2. **Start with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Environment

1. **Setup production environment**:
   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with secure production values
   ```

2. **Deploy with production compose**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - Health check (liveness): http://localhost:8000/health
   - Service status (includes app version): http://localhost:8000/status

## ⚙️ Configuration

### Settings Management

TestInsight AI features a comprehensive settings service with secure storage and real-time configuration:

**Configuration Methods:**
- **Web Interface**: Configure all settings through the modern web interface at `/settings`
- **Environment Variables**: Optional environment-based configuration for deployment
- **API Endpoints**: Programmatic configuration via REST API at `/api/v1/settings`

**Settings Categories:**
- **Jenkins Integration**: Connection URL, credentials, SSL verification, job filtering
- **GitHub Integration**: Personal access tokens for private repositories, default repository URLs
- **AI Configuration**: Gemini API key, model selection (gemini-1.5-pro, gemini-1.5-flash), temperature, max tokens
- **User Preferences**: Theme selection (light/dark), language, pagination settings, auto-refresh

**Security Features:**
- **AES-256 Encryption**: All sensitive settings (API keys, tokens) encrypted at rest
- **Local Storage**: Settings stored in encrypted JSON files - no external database required
- **Automatic Backup**: Settings automatically backed up before changes
- **Connection Testing**: Built-in connectivity testing for all external services
- **Input Validation**: Comprehensive validation of all configuration values

## 📖 How to Use

### 1. Upload JUnit XML Files
- Drag and drop JUnit XML test result files
- AI analyzes failures and provides fix suggestions

### 2. Analyze Raw Logs
- Paste console output from test runs
- Select log type (pytest, jest, junit, etc.)
- Get AI-powered failure analysis

### 3. Jenkins Integration
- Configure Jenkins connection in settings
- Select job from dropdown with fuzzy search
- Enter build number for analysis
- Automatically fetches test results and console output

### 4. Repository Context
- Add GitHub repository URL (HTTPS format: `https://github.com/user/repo.git`)
- Specify branch or commit for analysis
- Works with public and private GitHub repositories
- Format: `https://github.com/user/repository.git`

## 🛡️ Security

### Data Protection
- **AES-256 Encryption**: All sensitive settings (API keys, tokens, passwords) encrypted at rest
- **Local Storage**: No external databases - all data stored locally in encrypted JSON files
- **Secure Key Management**: Automatic encryption key generation and management
- **Input Validation**: Comprehensive validation using Pydantic models for all API inputs
- **Error Sanitization**: Error messages sanitized to prevent information leakage

### External Integrations
- **GitHub Access**: Support for private repositories with personal access tokens
- **Jenkins Authentication**: API token-based authentication (no password storage)
- **Google Gemini**: Secure API key handling with usage monitoring
- **Git Operations**: Read-only repository operations only

### Infrastructure Security
- **Docker Containers**: Run as non-root users with minimal privileges
- **SSL/HTTPS Support**: Production-ready SSL termination support
- **CORS Configuration**: Configurable CORS policies for production deployment
- **File Upload Security**: File type validation and size limits
- **Pre-commit Hooks**: Security scanning with gitleaks and detect-secrets

## 📊 Example Workflow

1. **Configure Settings**: Add your Gemini API key and Jenkins/GitHub credentials
2. **Select Input Method**: Choose from file upload, text input, or Jenkins
3. **Provide Repository Context**: Add your source code repository URL
4. **Analyze Results**: Review AI explanations and suggested fixes
5. **Apply Fixes**: Use provided code suggestions to fix failing tests

## 🛠️ Development

### Backend Development Commands

**Development Server:**
```bash
# Start backend with auto-reload
uv run python -m backend.main

# Or with explicit uvicorn
uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Code Quality:**
```bash
# Format code
uv run ruff format backend/

# Lint and auto-fix
uv run ruff check backend/ --fix

# Type checking
uv run mypy backend/

# Run all quality checks
uv run ruff format backend/ && uv run ruff check backend/ --fix && uv run mypy backend/
```

**Development Tools:**
```bash
# Install development dependencies
uv sync --dev

# Pre-commit hooks setup
uv run pre-commit install

# Run pre-commit on all files
uv run pre-commit run --all-files
```

### Frontend Development Commands (Vite)

```bash
cd frontend

# Install dependencies
npm install

# Start development server (Vite)
npm start

# Build for production
npm run build

# Run tests (Vitest)
npm run test -- --run

# Run linting
npm run lint
```

## 🧪 Testing

### Comprehensive Test Suite

The backend includes a robust test suite; the frontend has Vitest unit tests:

**Test Categories:**
- **Unit Tests**: Individual service and component testing
- **Integration Tests**: End-to-end workflow testing
- **Security Tests**: Encryption, validation, and security utilities
- **API Tests**: Complete API endpoint coverage

**Running Tests:**

**Recommended: Use tox for comprehensive testing**
```bash
# Run all tests with tox (recommended)
tox

# Specific test environments
tox -e py312        # Unit tests with Python 3.12
tox -e coverage     # Tests with coverage reporting
tox -e lint         # Linting checks
tox -e type-check   # Type checking with mypy
tox -e security     # Security tests
```

**Alternative: Direct test commands**
```bash
# Backend - run all tests
uv run pytest backend/tests/ -v

# Run with coverage
uv run pytest backend/tests/ --cov=backend --cov-report=html

# Run specific test categories
uv run pytest backend/tests/services/     # Service tests
uv run pytest backend/tests/api/         # API tests

# Frontend - run unit tests once (Vitest)
cd frontend && npm run test -- --run
```

**Test Results:**
- **236 total tests** across all modules
- **80% code coverage** with detailed reporting
- **Comprehensive service testing** for all backend components
- **Integration testing** for complete workflow validation

## 📚 Additional Documentation

### Backend Technical Details
For comprehensive backend architecture, API documentation, and deployment guides, see:
- **[Backend README](backend/README.md)** - Complete technical documentation
- **API Documentation** - Interactive docs at `/docs` when running locally
- **Service Architecture** - Detailed service descriptions and usage examples

### Key Backend Components
- **AI Analyzer Service** - Google Gemini integration and test analysis
- **Jenkins Client** - Enhanced CI/CD integration with job listing
- **Git Client** - Repository analysis with private repo support  
- **Settings Service** - Encrypted configuration management
- **Security Utils** - AES-256 encryption and validation
- **Service Config** - Service factory and dependency management

## 🆘 Support

For issues, feature requests, or questions, please check the troubleshooting section in our documentation or create an issue in the repository.

### Quick Troubleshooting
- **Backend Issues**: Check both `/health` (liveness) and `/status` (service status + version) endpoints and service logs
- **API Problems**: Review interactive docs at `/docs`
- **Configuration**: Use settings web interface at `/settings`
- **Testing**: Run `uv run pytest backend/tests/ -v` for diagnostics
