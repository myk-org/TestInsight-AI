# TestInsight AI - Frontend

**Modern React application providing intuitive interface for AI-powered test analysis and intelligent failure insights.**

The frontend delivers a seamless user experience for analyzing test failures through multiple input methods, real-time processing, and comprehensive visualization of AI-generated insights and fix suggestions. Designed to work with the lightweight TestInsight AI backend service with no additional infrastructure required.

## Features

### Core User Interface
- **Multi-Modal Input System** - Upload files, paste text, or connect directly to Jenkins
- **Real-Time Analysis** - Live progress indicators and streaming results
- **Interactive Results Display** - Expandable cards with detailed failure analysis
- **Code Diff Visualization** - Syntax-highlighted before/after code comparisons
- **Responsive Design** - Optimized for desktop, tablet, and mobile devices

### Advanced Capabilities
- **AI-Powered Insights** - Intelligent root cause analysis and fix suggestions
- **Contextual Analysis** - Repository integration for better code understanding
- **Batch Processing** - Analyze multiple test files simultaneously
- **Export Functionality** - Download analysis results and recommendations
- **Error Pattern Recognition** - Visual representation of recurring failure types

### User Experience
- **Drag & Drop Interface** - Intuitive file handling with visual feedback
- **Progressive Disclosure** - Information hierarchy from summary to detailed analysis
- **Loading States** - Clear progress indication during processing
- **Error Handling** - User-friendly error messages with actionable guidance
- **Accessibility** - WCAG 2.1 AA compliant interface design

## Getting Started

### Prerequisites

**Required:**
- Node.js 18+ (LTS recommended)
- npm 9+ or yarn 1.22+
- TestInsight AI Backend running on `http://localhost:8000`

**Optional:**
- Git (for development)
- Docker (for containerized deployment)

**Note:** No additional databases, message queues, or external services are required beyond the backend API.

### Installation

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd testinsight-ai/frontend

# Install dependencies
npm install

# Verify installation
npm list --depth=0
```

### Development Server

```bash
# Start development server
npm start

# The application will open at http://localhost:3000
# Hot reload is enabled for development
```

### Environment Configuration

Create `.env` file in the frontend directory:

```env
# Backend API Configuration
REACT_APP_API_URL=http://localhost:8000

# Feature Flags
REACT_APP_ENABLE_JENKINS=true
REACT_APP_ENABLE_GIT_INTEGRATION=true
REACT_APP_ENABLE_EXPORT=true

# Development Settings
REACT_APP_DEBUG_MODE=true
REACT_APP_LOG_LEVEL=info

# UI Configuration
REACT_APP_MAX_FILE_SIZE=10485760  # 10MB
REACT_APP_SUPPORTED_FORMATS=xml,junit,log,txt
```

## User Interface Guide

### 1. File Upload Interface

**Features:**
- Drag-and-drop file handling
- Multiple file selection
- Format validation (JUnit XML, logs)
- File size limits and progress tracking
- Preview of selected files

**Supported Formats:**
- JUnit XML (`.xml`, `.junit`)
- Log files (`.log`, `.txt`)
- TestNG reports
- Console outputs

**Usage:**
```typescript
// Drag files onto the upload area or click to browse
// Multiple files can be processed together
// Automatic format detection and validation
```

### 2. Text Input Interface

**Features:**
- Large text area for log content
- Format detection hints
- Sample data loading
- Real-time character count
- Format validation

**Supported Input Types:**
- Console output from CI/CD systems
- Raw JUnit XML content
- Application logs
- Stack traces
- Custom test output

### 3. Jenkins Integration

**Features:**
- Direct Jenkins API connection
- Secure authentication with API tokens
- Job and build number selection
- Connection testing
- Automatic data retrieval

**Configuration:**
```typescript
interface JenkinsConfig {
  url: string;        // Jenkins server URL
  username: string;   // Jenkins username
  apiToken: string;   // API token (not password)
  jobName: string;    // Job to analyze
  buildNumber: string; // Specific build number
}
```

### 4. Results Visualization

**Analysis Summary:**
- Overall test statistics
- Failure breakdown by category
- Success/failure ratios
- Execution time analysis

**Individual Failures:**
- Test name and location
- Error messages and stack traces
- AI-generated root cause analysis
- Suggested fixes with code examples
- Severity and impact assessment

**Interactive Features:**
- Expandable/collapsible cards
- Copy-to-clipboard functionality
- Direct navigation to code locations
- Export individual or batch results

## Architecture

### Component Hierarchy

```
App.tsx (Root)
├── Header
│   ├── Navigation
│   └── Status Indicators
├── Main Content
│   ├── InputTabs
│   │   ├── FileUpload
│   │   ├── TextInput
│   │   └── JenkinsForm
│   └── ResultsDisplay
│       ├── AnalysisSummary
│       ├── TestFailureCard[]
│       └── CodeDiff
└── Footer
    ├── Status Bar
    └── Export Controls
```

### Component Details

#### Core Components

**App.tsx**
- **Purpose**: Root component managing global state and routing
- **State Management**: Analysis results, loading states, error handling
- **Props**: None (root component)
- **Key Features**: Context providers, global error boundary

```typescript
interface AppState {
  results: AnalysisResult | null;
  loading: boolean;
  error: string | null;
  currentTab: 'upload' | 'text' | 'jenkins';
}
```

**InputTabs.tsx**
- **Purpose**: Tabbed interface for different input methods
- **Props**: `onAnalysisStart`, `onAnalysisComplete`, `onAnalysisError`
- **Features**: Tab switching, state persistence, validation

**FileUpload.tsx**
- **Purpose**: Drag-and-drop file upload with validation
- **Key Features**: Multiple file support, progress tracking, format validation
- **Dependencies**: `react-dropzone`, file type validation

```typescript
interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  acceptedTypes: string[];
  maxFileSize: number;
  maxFiles: number;
}
```

**TextInput.tsx**
- **Purpose**: Text area for manual input with format detection
- **Features**: Auto-sizing, format hints, sample data
- **Validation**: Content type detection, size limits

**JenkinsForm.tsx**
- **Purpose**: Jenkins integration configuration and connection
- **Features**: Connection testing, credential validation, job browsing
- **Security**: API token handling, secure credential storage

**ResultsDisplay.tsx**
- **Purpose**: Comprehensive analysis results visualization
- **Features**: Summary statistics, failure categorization, export options
- **Props**: `results: AnalysisResult`, `onExport: () => void`

**TestFailureCard.tsx**
- **Purpose**: Individual test failure display with AI insights
- **Features**: Expandable details, code highlighting, copy functionality
- **Props**: `failure: TestFailure`, `expanded: boolean`

**CodeDiff.tsx**
- **Purpose**: Side-by-side code comparison with syntax highlighting
- **Dependencies**: `react-diff-view`, `highlight.js`
- **Features**: Language detection, line numbering, highlight themes

### State Management

**Global State (React Context):**
```typescript
interface AppContext {
  // Analysis state
  currentAnalysis: AnalysisResult | null;
  analysisHistory: AnalysisResult[];

  // UI state
  theme: 'light' | 'dark';
  preferences: UserPreferences;

  // Configuration
  apiConfig: ApiConfiguration;
  featureFlags: FeatureFlags;
}
```

**Local Component State:**
- Form inputs and validation
- UI interaction states
- Temporary data during processing

### API Integration

**Service Architecture (Direct Backend Communication):**

```typescript
// services/api.ts - Simple HTTP client for backend communication
class ApiService {
  private client: AxiosInstance;

  // Analysis endpoints (directly to backend service)
  async analyzeFiles(files: File[], options?: AnalysisOptions): Promise<AnalysisResult>
  async analyzeText(content: string, format: string): Promise<AnalysisResult>
  async analyzeJenkinsBuild(config: JenkinsConfig): Promise<AnalysisResult>

  // Utility endpoints
  async validateConnection(): Promise<boolean>
  async getServiceStatus(): Promise<ServiceStatus>
}
```

**Note:** All communication is direct HTTP to the FastAPI backend - no message queues, websockets, or complex protocols required.

**Error Handling:**
```typescript
interface ApiError {
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
}

// Automatic retry logic for transient errors
// User-friendly error messages
// Fallback mechanisms for service unavailability
```

## Development

### Project Structure

```
frontend/
├── public/                     # Static assets
│   ├── index.html             # Main HTML template
│   ├── manifest.json          # PWA manifest
│   └── favicon.ico           # Application icon
├── src/
│   ├── components/            # React components
│   │   ├── __tests__/        # Component tests
│   │   ├── CodeDiff.tsx      # Code comparison display
│   │   ├── FileUpload.tsx    # File upload interface
│   │   ├── InputTabs.tsx     # Input method tabs
│   │   ├── JenkinsForm.tsx   # Jenkins integration form
│   │   ├── ResultsDisplay.tsx # Results visualization
│   │   ├── TestFailureCard.tsx # Individual failure display
│   │   └── TextInput.tsx     # Text input interface
│   ├── services/             # API and utility services
│   │   ├── __tests__/        # Service tests
│   │   └── api.ts           # API client and methods
│   ├── types/               # TypeScript type definitions
│   │   └── index.ts         # Shared type definitions
│   ├── utils/               # Utility functions
│   │   ├── formatters.ts    # Data formatting utilities
│   │   └── validators.ts    # Input validation functions
│   ├── App.tsx              # Root application component
│   ├── App.css              # Application-specific styles
│   ├── index.tsx            # Application entry point
│   ├── index.css            # Global styles and Tailwind imports
│   └── setupTests.ts        # Jest test configuration
├── package.json             # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── tailwind.config.js      # Tailwind CSS configuration
└── postcss.config.js       # PostCSS configuration
```

### Development Workflow

**Setup Development Environment:**
```bash
# Install dependencies
npm install

# Start development server with hot reload
npm start

# Run in different modes
NODE_ENV=development npm start    # Development mode
NODE_ENV=test npm start          # Test mode with mock data
```

**Code Quality Tools:**
```bash
# Linting
npm run lint              # ESLint check
npm run lint:fix          # Auto-fix ESLint issues

# Type checking
npm run type-check        # TypeScript compilation check

# Testing
npm test                  # Run tests in watch mode
npm run test:coverage     # Generate coverage report
npm run test:ci          # Run tests once (CI mode)

# Formatting
npm run format           # Prettier formatting
npm run format:check     # Check formatting without fixing
```

### Testing

**Test Structure:**
```
src/
├── components/__tests__/
│   ├── FileUpload.test.tsx      # File upload component tests
│   ├── JenkinsForm.test.tsx     # Jenkins form tests
│   ├── ResultsDisplay.test.tsx  # Results display tests
│   └── TestFailureCard.test.tsx # Test failure card tests
└── services/__tests__/
    └── api.test.ts              # API service tests
```

**Testing Framework:**
- **Jest** - Test runner and assertion library
- **React Testing Library** - Component testing utilities
- **MSW (Mock Service Worker)** - API mocking for tests
- **Jest DOM** - Additional DOM matchers

**Test Categories:**

1. **Unit Tests** - Individual component logic
```typescript
test('FileUpload validates file types correctly', () => {
  const validFile = new File(['content'], 'test.xml', { type: 'text/xml' });
  const invalidFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

  expect(validateFileType(validFile)).toBe(true);
  expect(validateFileType(invalidFile)).toBe(false);
});
```

2. **Integration Tests** - Component interaction
```typescript
test('Analysis workflow from upload to results', async () => {
  render(<App />);

  // Upload file
  const file = new File(['<junit>...</junit>'], 'test.xml', { type: 'text/xml' });
  const uploadInput = screen.getByTestId('file-upload');
  fireEvent.change(uploadInput, { target: { files: [file] } });

  // Trigger analysis
  fireEvent.click(screen.getByText('Analyze'));

  // Verify results display
  await waitFor(() => {
    expect(screen.getByText('Analysis Results')).toBeInTheDocument();
  });
});
```

3. **Accessibility Tests** - WCAG compliance
```typescript
test('FileUpload is accessible', async () => {
  const { container } = render(<FileUpload />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

**Running Tests:**
```bash
# Interactive test runner
npm test

# Single run with coverage
npm run test:coverage

# Specific test file
npm test FileUpload.test.tsx

# Tests matching pattern
npm test --testNamePattern="validation"
```

### Styling and Design System

**Tailwind CSS Configuration:**
```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
        success: {
          50: '#f0fdf4',
          500: '#22c55e',
          900: '#14532d',
        },
        danger: {
          50: '#fef2f2',
          500: '#ef4444',
          900: '#7f1d1d',
        }
      },
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ]
}
```

**Component Styling Patterns:**
```typescript
// Consistent button styling
const buttonClasses = {
  base: 'px-4 py-2 font-medium rounded-lg transition-colors focus:outline-none focus:ring-2',
  primary: 'bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500',
  secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300 focus:ring-gray-500',
  danger: 'bg-danger-500 text-white hover:bg-danger-600 focus:ring-danger-500'
};
```

**Responsive Design:**
```css
/* Mobile-first responsive utilities */
.container {
  @apply w-full mx-auto px-4;
  @apply sm:px-6 lg:px-8;
  @apply max-w-sm sm:max-w-md lg:max-w-4xl xl:max-w-6xl;
}

/* Breakpoint-specific layouts */
.grid-responsive {
  @apply grid grid-cols-1;
  @apply md:grid-cols-2 lg:grid-cols-3;
  @apply gap-4 md:gap-6;
}
```

### Performance Optimization

**Code Splitting:**
```typescript
// Lazy load components for better initial load time
const CodeDiff = lazy(() => import('./components/CodeDiff'));
const ResultsDisplay = lazy(() => import('./components/ResultsDisplay'));

// Wrap with Suspense
<Suspense fallback={<LoadingSpinner />}>
  <CodeDiff original={original} modified={modified} />
</Suspense>
```

**Memoization:**
```typescript
// Memo for expensive re-renders
const TestFailureCard = memo(({ failure, onExpand }) => {
  return (
    <div className="card">
      {/* Card content */}
    </div>
  );
});

// Callback memoization
const handleFileSelect = useCallback((files: File[]) => {
  setSelectedFiles(files);
}, []);
```

**Bundle Optimization:**
```bash
# Analyze bundle size
npm run build
npx webpack-bundle-analyzer build/static/js/*.js

# Bundle size monitoring
npm install --save-dev webpack-bundle-analyzer
```

## Deployment

### Build Process

**Production Build:**
```bash
# Create optimized production build
npm run build

# Output directory: build/
# - Minified and optimized JavaScript
# - CSS extraction and optimization
# - Asset optimization and hashing
# - Service worker generation (if enabled)
```

**Build Optimization:**
```javascript
// package.json build configuration
{
  "scripts": {
    "build": "react-scripts build",
    "build:analyze": "npm run build && npx webpack-bundle-analyzer build/static/js/*.js"
  }
}
```

### Environment Configuration

**Production Environment Variables:**
```env
# Production API endpoint
REACT_APP_API_URL=https://api.testinsight.example.com

# Feature flags for production
REACT_APP_ENABLE_JENKINS=true
REACT_APP_ENABLE_GIT_INTEGRATION=true
REACT_APP_DEBUG_MODE=false

# Performance settings
REACT_APP_API_TIMEOUT=30000
REACT_APP_MAX_FILE_SIZE=52428800  # 50MB

# Analytics (optional)
REACT_APP_GA_TRACKING_ID=GA-XXXXXXXXX
```

### Static Hosting

**Netlify Deployment:**
```toml
# netlify.toml
[build]
  command = "npm run build"
  publish = "build"

[build.environment]
  NODE_VERSION = "18"

[[redirects]]
  from = "/*"
  to = "/index.html"
  status = 200
```

**Vercel Deployment:**
```json
// vercel.json
{
  "version": 2,
  "builds": [
    {
      "src": "package.json",
      "use": "@vercel/static-build",
      "config": { "distDir": "build" }
    }
  ],
  "routes": [
    { "handle": "filesystem" },
    { "src": "/(.*)", "dest": "/index.html" }
  ]
}
```

**Docker Deployment:**
```dockerfile
# Multi-stage build for optimized image
FROM node:18-alpine AS builder

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
RUN npm run build

# Production image
FROM node:18-alpine
WORKDIR /app

# Install serve to host the static files
RUN npm install -g serve

# Copy built application
COPY --from=builder /app/build ./build

EXPOSE 3000
CMD ["serve", "-s", "build", "-l", "3000"]
```

### CDN and Caching

**Asset Optimization:**
```javascript
// Service worker for caching (if using PWA)
const CACHE_NAME = 'testinsight-v1';
const urlsToCache = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
];
```

## Troubleshooting

### Common Development Issues

**1. Build Failures**
```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear React scripts cache
npm start -- --reset-cache

# TypeScript compilation errors
npm run type-check
```

**2. API Connection Issues**
```typescript
// Check environment variables
console.log('API URL:', process.env.REACT_APP_API_URL);

// Test backend connectivity
curl http://localhost:8000/health

// CORS issues (backend configuration needed)
// Ensure backend CORS settings allow frontend origin
```

**3. File Upload Problems**
```javascript
// Check file size limits
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

// Verify file types
const ACCEPTED_TYPES = ['.xml', '.junit', '.log', '.txt'];

// Debug file upload
console.log('File details:', {
  name: file.name,
  size: file.size,
  type: file.type
});
```

**4. Performance Issues**
```bash
# Bundle analysis
npm run build:analyze

# Component profiling
# Use React DevTools Profiler

# Memory leaks
# Check for unmounted component state updates
```

### Production Troubleshooting

**Error Monitoring:**
```typescript
// Error boundary for production error tracking
class ErrorBoundary extends Component {
  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log to error tracking service
    console.error('Application error:', error, errorInfo);
  }
}
```

**Performance Monitoring:**
```typescript
// Web Vitals reporting
import { reportWebVitals } from './reportWebVitals';

reportWebVitals((metric) => {
  // Send to analytics service
  console.log(metric);
});
```

**Debug Mode:**
```typescript
// Enable debug logging in development
if (process.env.NODE_ENV === 'development') {
  window.DEBUG = true;
  console.log('Debug mode enabled');
}
```

## API Integration

### Backend Communication

**API Client Configuration:**
```typescript
// services/api.ts
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  timeout: 300000, // 5 minutes for analysis
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use((config) => {
  config.headers.Authorization = `Bearer ${getAuthToken()}`;
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle authentication errors
      redirectToLogin();
    }
    return Promise.reject(error);
  }
);
```

**Error Handling:**
```typescript
interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  errors?: string[];
}

const handleApiError = (error: AxiosError): string => {
  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }
  if (error.message) {
    return error.message;
  }
  return 'An unexpected error occurred';
};
```

## Contributing

### Development Guidelines

**Code Style:**
- Use TypeScript for type safety
- Follow React functional component patterns
- Implement proper error boundaries
- Use semantic HTML and ARIA attributes
- Follow naming conventions (PascalCase for components, camelCase for functions)

**Component Design Principles:**
- Single responsibility principle
- Prop interface documentation
- Default props and prop validation
- Proper state management (local vs global)
- Lifecycle method optimization

**Testing Requirements:**
- Unit tests for all components
- Integration tests for user workflows
- Accessibility testing
- Performance testing for large datasets
- Cross-browser compatibility testing

**Documentation Standards:**
- TSDoc comments for public interfaces
- README updates for new features
- Component prop documentation
- API integration documentation

### Pull Request Process

1. **Development Setup**
   ```bash
   git checkout -b feature/new-feature
   npm install
   npm test
   ```

2. **Code Quality Checks**
   ```bash
   npm run lint:fix
   npm run type-check
   npm test
   npm run build
   ```

3. **Testing**
   - Add tests for new components
   - Ensure existing tests pass
   - Test in multiple browsers
   - Verify accessibility compliance

4. **Documentation**
   - Update component documentation
   - Add usage examples
   - Update API documentation if needed

---

**For complete project documentation, see the [main README](../README.md)**
**For backend API details, see the [backend documentation](../backend/README.md)**
