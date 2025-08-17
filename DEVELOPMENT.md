# TestInsight AI - Development Guide

This document contains all development-related information for TestInsight AI.

## 🏗️ Architecture

TestInsight AI is designed as a **lightweight, self-contained application** with only two services:

### Backend (FastAPI + Python)
- **FastAPI**: REST API with automatic OpenAPI documentation at /docs
- **8 Specialized Services**: ai_analyzer, gemini_api, gemini_models_service, git_client, jenkins_client, security_utils, service_config, settings_service
- **Pydantic Models**: Request/response validation and type safety
- **Storage**: Local JSON-based settings with AES-256 encryption for sensitive data
- **AI Integration**: Google Gemini API for test failure analysis
- **Comprehensive Security**: Input sanitization, validation, and encryption
- **Testing**: 254 tests with 85% code coverage using pytest
- **Modern Python Stack**: Python 3.12+, uv package manager, pre-commit hooks
- **No External Dependencies**: No databases, message queues, or caching layers required

### Frontend (React + TypeScript)
- **React 19**: Modern React with TypeScript for type safety
- **Tailwind CSS**: Utility-first CSS framework
- **Context API**: State management for themes and settings
- **Components**: Modular component architecture
- **API Communication**: Direct HTTP communication with backend service

### Directory Structure
```
testinsight-ai/
├── backend/                 # FastAPI backend
│   ├── api/                # API endpoints
│   ├── models/             # Pydantic schemas
│   ├── services/           # Business logic services (8 specialized services)
│   ├── tests/              # Comprehensive test suite
│   │   ├── api/           # API endpoint tests
│   │   ├── models/        # Schema validation tests
│   │   ├── services/      # Service layer tests
│   │   └── conftest.py    # Shared test fixtures and constants
│   └── main.py            # FastAPI application
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── contexts/      # React contexts
│   │   └── services/      # API clients
├── data/                   # Local data storage
│   └── settings.json      # Application settings with AES encryption
├── docker-compose.yml      # Development environment
├── docker-compose.prod.yml # Production environment
├── pyproject.toml         # Python dependencies (uv managed)
├── uv.lock                # Locked dependencies
├── pytest.ini             # Test configuration
├── tox.toml               # Testing environments
└── .pre-commit-config.yaml # Code quality hooks
```

## 🛠️ Development Setup

### Prerequisites
- Docker or Podman
- Git

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd testinsight-ai

# Setup environment
cp .env.example .env
# Edit .env with your development API keys

# Start development environment (backend + frontend only)
docker-compose up -d

# Access services
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

### Local Development (without Docker)

#### Backend Setup
```bash
# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies (uses uv.lock for reproducible builds)
uv sync

# Install development dependencies
uv sync --group dev --group tests

# Start backend (Python 3.12+ required)
uv run python -m backend.main
```

#### Frontend Setup
```bash
cd frontend
npm install
npm start
```

## 🧪 Testing

### Test Framework
- **Backend**: pytest with pytest-asyncio, pytest-cov, pytest-mock
- **Test Suite**: 254 tests with 85% code coverage
- **Test Organization**: Organized by component (api/, models/, services/)
- **Test Configuration**: pytest.ini with coverage reporting and IPython debugging
- **Shared Fixtures**: conftest.py for test constants and maintainability
- **Frontend**: Jest with React Testing Library
- **Quality Gates**: Pre-commit hooks with ruff, mypy, flake8, gitleaks, detect-secrets

### Running Tests
```bash
# Run all backend tests (254 tests)
uv run --group tests pytest backend/tests/ -v

# Run tests with coverage (current: 85%)
uv run --group tests pytest backend/tests/ --cov=backend --cov-report=html --cov-report=term

# Run specific test categories
uv run pytest backend/tests/api/ -v          # API endpoint tests
uv run pytest backend/tests/services/ -v     # Service layer tests
uv run pytest backend/tests/models/ -v       # Schema validation tests

# Run specific test files
uv run pytest backend/tests/services/test_ai_analyzer.py -v
uv run pytest backend/tests/api/test_endpoints.py -v

# Run with tox (configured environments)
tox -e backend-unittests  # Backend unit tests
tox -e unused-code        # Dead code detection

# Frontend tests
cd frontend
npm test
```

### Test Coverage Metrics
```bash
# Current test coverage: 85% (requirement: 80%)
# Total tests: 254 across 10 test files
# Coverage by module:
# - ai_analyzer.py: 100%
# - gemini_api.py: 100%
# - git_client.py: 100%
# - jenkins_client.py: 98%
# - security_utils.py: 95%
# - settings_service.py: 97%
# - service_config.py: 97%
# - schemas.py: 95%
# - endpoints.py: 81%
# - main.py: 80%

# View detailed coverage report
uv run pytest backend/tests/ --cov=backend --cov-report=html
# Open .tests_coverage/index.html for detailed report
```

## 🔧 Code Quality

### Linting and Formatting
```bash
# Format and lint with ruff (modern Python linter)
uv run ruff check backend/ --fix
uv run ruff format backend/

# Type checking with mypy (strict configuration)
uv run mypy backend/

# Run all quality checks
uv run pre-commit run --all-files

# Individual checks
uv run ruff check backend/                    # Linting
uv run flake8 backend/                        # Additional linting
uv run gitleaks detect --source .            # Security scan
uv run detect-secrets scan --all-files       # Secret detection
```

### Pre-commit Hooks
```bash
# Install pre-commit hooks (includes ruff, mypy, flake8, gitleaks, detect-secrets)
uv run pre-commit install

# Run all hooks manually
uv run pre-commit run --all-files

# Update hooks to latest versions
uv run pre-commit autoupdate

# Test specific hook
uv run pre-commit run ruff --all-files
uv run pre-commit run mypy --all-files
```

## 🐳 Docker Development

### Building Images
```bash
# Build backend image
docker build -f backend/Dockerfile -t testinsight-backend .

# Build frontend image
docker build -f frontend/Dockerfile -t testinsight-frontend ./frontend

# Build all services
docker-compose build
```

### Development Workflow
```bash
# Start development environment (backend + frontend)
docker-compose up -d

# View logs for individual services
docker-compose logs -f backend
docker-compose logs -f frontend

# Restart individual services
docker-compose restart backend
docker-compose restart frontend

# Stop all services
docker-compose down

# Clean up (only removes local data volume)
docker-compose down --volumes --remove-orphans
```

## 📋 Configuration Management

### Settings Service
TestInsight AI uses a sophisticated settings service with:
- **AES-256 Encryption**: Sensitive data encrypted at rest
- **Real-time Updates**: Configuration changes without restart
- **Connection Testing**: Automatic validation of external services
- **Backup & Restore**: Automatic settings backup functionality
- **Local Storage**: Settings stored in `data/settings.json`

### Development (.env)
```env
# Required (can also be configured via Settings UI)
GEMINI_API_KEY=your_development_key

# Optional - Jenkins (configured via Settings service)
JENKINS_URL=http://localhost:8080
JENKINS_USERNAME=admin
JENKINS_TOKEN=development_token

# Optional - GitHub (configured via Settings service)
GITHUB_TOKEN=ghp_development_token
DEFAULT_REPOSITORY_URL=https://github.com/your/test-repo

# Development settings
DEBUG=true
LOG_LEVEL=debug
```

### Production (.env.production)
```env
# Required
GEMINI_API_KEY=your_production_key

# Security
SSL_CERT_PATH=/etc/ssl/certs/cert.pem
SSL_KEY_PATH=/etc/ssl/private/key.pem

# Performance
WORKERS=4
MAX_CONNECTIONS=100

# Logging
LOG_LEVEL=info
LOG_FORMAT=json
```

## 🔌 API Development

### Adding New Endpoints
1. **Define Schema**: Add Pydantic models in `backend/models/schemas.py`
2. **Create Service**: Implement business logic in `backend/services/`
3. **Add Endpoint**: Add FastAPI route in `backend/api/endpoints.py`
4. **Write Tests**: Add tests in `backend/tests/api/` and `backend/tests/services/`
5. **Update Docs**: API docs auto-generate from FastAPI at `/docs`
6. **Security Review**: Ensure input validation and error handling

### Current Service Architecture
- **ai_analyzer.py**: AI-powered test failure analysis
- **gemini_api.py**: Google Gemini API integration
- **gemini_models_service.py**: Model management and configuration
- **git_client.py**: Git repository operations
- **jenkins_client.py**: Jenkins CI/CD integration
- **security_utils.py**: Encryption and security utilities
- **service_config.py**: Centralized service configuration
- **settings_service.py**: Real-time configuration management

### Service Integration
1. **Create Service Class**: Implement in `backend/services/`
2. **Add Configuration**: Update `service_config.py` for centralized config
3. **Add Settings**: Update settings schema and encryption if needed
4. **Write Tests**: Comprehensive unit tests (aim for >95% coverage)
5. **Integration Tests**: Add to `backend/tests/api/` for endpoint testing

## 🎨 Frontend Development

### Component Development
1. **Create Component**: Add to `frontend/src/components/`
2. **Add Types**: Define TypeScript interfaces
3. **Implement Logic**: Use React hooks and context
4. **Add Styles**: Use Tailwind CSS classes
5. **Write Tests**: Add Jest/RTL tests

### State Management
- **Theme**: ThemeContext for light/dark mode
- **Settings**: SettingsContext for application configuration
- **API**: Custom hooks for API interactions

## 📦 Deployment

### Production Deployment
```bash
# Setup production environment
cp .env.production.example .env.production
# Edit with production values

# Deploy production services (backend + frontend)
docker-compose -f docker-compose.prod.yml up -d

# Health checks
curl -f http://localhost:8000/health  # Backend health
curl -f http://localhost:3000         # Frontend availability
```

### Monitoring
- **Health Checks**: Built-in health endpoints for both services
- **Logging**: Structured JSON logging in production
- **Metrics**: Container metrics via Docker for both services
- **Data Storage**: Local JSON files with automatic backups

## 🐛 Debugging

### Backend Debugging
```bash
# Local debugging with ipdb (included in dev dependencies)
uv run python -m backend.main
# Add `import ipdb; ipdb.set_trace()` in code for breakpoints

# Run with verbose logging
LOG_LEVEL=debug uv run python -m backend.main

# Docker debugging
docker-compose logs -f backend

# Debug mode with development dependencies
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up

# Connect to container for inspection
docker-compose exec backend bash

# Test specific service with debugging
uv run --group tests pytest backend/tests/services/test_ai_analyzer.py -v -s --pdb
```

### Frontend Debugging
```bash
# Development mode with hot reload
docker-compose up frontend

# Browser DevTools: React Developer Tools recommended
# Network tab: Inspect API calls
```

### Common Issues

#### Backend-Specific Issues
1. **Python Version**: Requires Python 3.12+, check with `python --version`
2. **uv Installation**: Install uv with `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. **Dependencies**: Run `uv sync --group dev --group tests` for complete setup
4. **Settings Encryption**: If settings.json is corrupted, delete and reconfigure
5. **Test Failures**: Check coverage requirement (80% minimum)
6. **Import Errors**: Ensure `PYTHONPATH` includes project root

#### General Issues
1. **Port Conflicts**: Check if ports 3000/8000 are available
2. **API Keys**: Configure via Settings page or .env file
3. **Docker Issues**: Run `docker system prune` to clean up
4. **Data Persistence**: Settings stored in `./data` directory - ensure proper permissions
5. **Pre-commit Hooks**: Install with `uv run pre-commit install` for code quality

#### Performance Issues
1. **Test Speed**: Use `tox -e backend-unittests` for focused backend testing
2. **Coverage Reports**: HTML reports generated in `.tests_coverage/`
3. **Memory Usage**: Monitor with 254 tests, may need increased memory limits

## 🤝 Contributing

### Development Workflow
1. **Fork Repository**: Create your fork
2. **Create Branch**: `git checkout -b feature/your-feature`
3. **Develop**: Make changes with tests
4. **Test**: Run full test suite with `tox`
5. **Commit**: Use conventional commit messages
6. **Push**: Push to your fork
7. **Pull Request**: Create PR with description

### Code Standards
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Strict mode, explicit types
- **Testing**: Maintain >80% coverage
- **Documentation**: Update docs for new features

### Release Process
1. **Version Bump**: Update version in `pyproject.toml`
2. **Changelog**: Update CHANGELOG.md
3. **Tag**: Create git tag `git tag v1.0.0`
4. **Release**: Push tag to trigger release

## 📚 Additional Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **React Docs**: https://react.dev/
- **Tailwind CSS**: https://tailwindcss.com/
- **Docker Compose**: https://docs.docker.com/compose/
- **pytest**: https://docs.pytest.org/
- **tox**: https://tox.wiki/
