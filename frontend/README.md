# TestInsight AI - Frontend

**Modern React application providing an intuitive interface for AI-powered test analysis.**

The frontend delivers a seamless user experience for analyzing test failures through multiple input methods, real-time processing, and comprehensive visualization of AI-generated insights.

## Features

### Core User Interface
- **Multi-Modal Input System** - Upload files, paste text, or connect directly to Jenkins.
- **Real-Time Analysis** - Live progress indicators.
- **Interactive Results Display** - Expandable cards with detailed failure analysis.
- **Responsive Design** - Optimized for desktop, tablet, and mobile devices.

### Advanced Capabilities
- **AI-Powered Insights** - Intelligent root cause analysis and fix suggestions.
- **Contextual Analysis** - Repository integration for better code understanding.
- **Batch Processing** - Analyze multiple test files simultaneously.

### User Experience
- **Drag & Drop Interface** - Intuitive file handling.
- **Loading States** - Clear progress indication during processing.
- **Error Handling** - User-friendly error messages.

## Getting Started

### Prerequisites

- Node.js 18+
- npm 9+ or yarn 1.22+
- TestInsight AI Backend running on `http://localhost:8000`

### Installation

```bash
cd frontend
npm install
```

### Development Server

```bash
npm start
```
The application will be available at `http://localhost:3000`.

### Environment Configuration

Create a `.env` file in the `frontend` directory:

```env
REACT_APP_API_URL=http://localhost:8000
```

## Architecture

### Component Hierarchy

```
App.tsx
├── ThemeProvider
├── SettingsProvider
├── Router
│   ├── Navigation
│   └── Routes
│       ├── AnalyzePage
│       │   ├── InputTabs
│       │   │   ├── FileUpload
│       │   │   ├── TextInput
│       │   │   └── JenkinsForm
│       │   └── ResultsDisplay
│       └── Settings
└── ThemeToggle
```

### State Management

Global state is managed using React Context for settings and theme. Local component state is used for form inputs and UI interactions.

### API Integration

All communication with the backend is handled through the `services/api.ts` module, which uses `axios` to make requests to the FastAPI backend.

## Development

### Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   ├── contexts/        # React context providers
│   ├── services/        # API service
│   ├── App.tsx          # Root application component
│   ├── index.tsx        # Application entry point
│   └── ...
├── package.json         # Dependencies and scripts
└── tsconfig.json        # TypeScript configuration
```

### Development Workflow

- **Run development server:** `npm start`
- **Build for production:** `npm run build`
- **Run tests:** `npm test`

### Testing

The project is set up with Jest and React Testing Library. The existing tests primarily cover the initial setup and can be expanded.

---

**For complete project documentation, see the [main README](../README.md)**
**For backend API details, see the [backend documentation](../backend/README.md)**
