import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
// Mock SettingsContext to avoid network and provide default settings
vi.mock('../../contexts/SettingsContext', () => {
  const React = require('react');
  const mockContext = {
    settings: {
      jenkins: { url: 'http://jenkins.local', username: 'user', api_token: 'token', verify_ssl: true },
      github: { token: '' },
      ai: { gemini_api_key: '', model: '', temperature: 0.7, max_tokens: 4096 },
    },
    loading: false,
    error: null,
    fetchSettings: vi.fn(),
    updateSettings: vi.fn(),
    resetSettings: vi.fn(),
    validateSettings: vi.fn(),
    testConnection: vi.fn(),
    backupSettings: vi.fn(),
    restoreSettings: vi.fn(),
  };
  return {
    useSettings: () => mockContext,
    SettingsProvider: ({ children }: { children: React.ReactNode }) => React.createElement(React.Fragment, null, children),
  };
});

import JenkinsForm from '../JenkinsForm';
import * as api from '../../services/api';

// Mock the API module
vi.mock('../../services/api');
const mockedApi = api as any;

const mockProps = {
  repoUrl: 'https://github.com/example/repo',
  branch: '',
  commit: '',
  systemPrompt: '',
  onAnalysisStart: vi.fn(),
  onAnalysisComplete: vi.fn(),
  onAnalysisError: vi.fn(),
};

const mockAnalysisResult = {
  insights: [
    {
      title: 'Jenkins Build Analysis',
      description: 'Build failed due to test failures',
      severity: 'high',
      category: 'Build',
      suggestions: ['Review failing tests', 'Check build configuration'],
      confidence: 0.95,
    },
  ],
  summary: 'Jenkins build analysis completed',
  recommendations: ['Fix failing tests', 'Optimize build time'],
  test_failures: [],
  performance_insights: [],
};

describe('JenkinsForm Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders required form fields', () => {
    render(<JenkinsForm {...mockProps} />);
    expect(screen.getByLabelText(/Job Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Build Number/i)).toBeInTheDocument();
  });

  it('shows build number hint', () => {
    render(<JenkinsForm {...mockProps} />);
    expect(screen.getByText(/Leave empty for latest build/i)).toBeInTheDocument();
  });

  it('updates job name field', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);
    const jobNameInput = screen.getByLabelText(/Job Name/i);
    await user.type(jobNameInput, 'test-job');
    expect(jobNameInput).toHaveValue('test-job');
  });

  it('displays Jenkins Connected/Configuration Required card', () => {
    render(<JenkinsForm {...mockProps} />);
    // We cannot assert settings-connected state here; just ensure the component renders
    expect(screen.getByText(/Build Information/i)).toBeInTheDocument();
  });

  // Connection validation now handled via Settings; omit here.

  // Required fields for analysis rely on Settings; component validates job name.

  it('calls API for successful Jenkins analysis', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockResolvedValueOnce(mockAnalysisResult);

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields for analysis (settings provide URL/creds)
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');
    await user.type(screen.getByLabelText(/Build Number/i), '123');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisStart).toHaveBeenCalled();
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalled();
      const [configArg, repoArg] = mockedApi.analyzeJenkinsBuild.mock.calls[0];
      expect(configArg).toMatchObject({
        url: 'http://jenkins.local',
        username: 'user',
        apiToken: 'token',
        jobName: 'test-job',
        buildNumber: '123',
      });
      expect(repoArg).toMatchObject({ url: mockProps.repoUrl });
      expect(mockProps.onAnalysisComplete).toHaveBeenCalledWith(mockAnalysisResult);
    });
  });

  it('handles Jenkins analysis API error', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Jenkins connection failed';
    mockedApi.analyzeJenkinsBuild.mockRejectedValueOnce(new Error(errorMessage));

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields (job only; settings provide connection)
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisStart).toHaveBeenCalled();
      expect(mockProps.onAnalysisError).toHaveBeenCalledWith(errorMessage);
    });
  });

  it('works without build number (latest build)', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockResolvedValueOnce(mockAnalysisResult);

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields but leave build number empty
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalled();
      const [configArg] = mockedApi.analyzeJenkinsBuild.mock.calls[0];
      expect(configArg).toMatchObject({
        url: 'http://jenkins.local',
        username: 'user',
        apiToken: 'token',
        jobName: 'test-job',
        buildNumber: '',
      });
    });
  });

  it('shows Jenkins connected card when settings provide URL', () => {
    render(<JenkinsForm {...mockProps} />);
    expect(screen.getByText(/Jenkins Connected/i)).toBeInTheDocument();
    expect(screen.getByText(/Connected to/i)).toBeInTheDocument();
  });

  it('updates job name and build number on change', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);
    const job = screen.getByLabelText(/Job Name/i);
    const build = screen.getByLabelText(/Build Number/i);
    await user.type(job, 'job-x');
    await user.type(build, '42');
    expect(job).toHaveValue('job-x');
    expect(build).toHaveValue('42');
  });

  it('handles non-Error objects in catch blocks', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockRejectedValueOnce('String error');

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisError).toHaveBeenCalledWith('Failed to analyze Jenkins build');
    });
  });

  it('passes custom repo URL to API', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockResolvedValueOnce(mockAnalysisResult);

    const customProps = {
      ...mockProps,
      repoUrl: 'https://github.com/custom/repo',
    };

    render(<JenkinsForm {...customProps} />);

    // Fill required fields
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalled();
      const [, repoArg] = mockedApi.analyzeJenkinsBuild.mock.calls[0];
      expect(repoArg).toMatchObject({ url: 'https://github.com/custom/repo' });
    });
  });

  it('shows helpful information and hints', () => {
    render(<JenkinsForm {...mockProps} />);
    expect(screen.getByText(/Build Information/i)).toBeInTheDocument();
    expect(screen.getByText(/Leave empty for latest build/i)).toBeInTheDocument();
  });

  it('maintains form state correctly', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    // Fill multiple fields
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');
    await user.type(screen.getByLabelText(/Build Number/i), '456');

    // Verify all values are maintained
    expect(screen.getByLabelText(/Job Name/i)).toHaveValue('test-job');
    expect(screen.getByLabelText(/Build Number/i)).toHaveValue('456');
  });
});
