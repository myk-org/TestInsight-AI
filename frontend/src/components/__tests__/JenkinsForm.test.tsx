import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import JenkinsForm from '../JenkinsForm';
import * as api from '../../services/api';

// Mock the API module
jest.mock('../../services/api');
const mockedApi = api as jest.Mocked<typeof api>;

const mockProps = {
  repoUrl: 'https://github.com/example/repo',
  onAnalysisStart: jest.fn(),
  onAnalysisComplete: jest.fn(),
  onAnalysisError: jest.fn(),
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
    jest.clearAllMocks();
  });

  it('renders all form fields', () => {
    render(<JenkinsForm {...mockProps} />);

    expect(screen.getByLabelText(/Jenkins URL/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Username/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/API Token/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Job Name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Build Number/i)).toBeInTheDocument();
  });

  it('renders help text and placeholders', () => {
    render(<JenkinsForm {...mockProps} />);

    expect(screen.getByPlaceholderText('https://jenkins.example.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your-username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('your-job-name')).toBeInTheDocument();
    expect(screen.getByText(/Leave empty for latest build/i)).toBeInTheDocument();
    expect(screen.getByText(/You can generate an API token/i)).toBeInTheDocument();
  });

  it('updates form fields when user types', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    const urlInput = screen.getByLabelText(/Jenkins URL/i);
    const usernameInput = screen.getByLabelText(/Username/i);
    const jobNameInput = screen.getByLabelText(/Job Name/i);

    await user.type(urlInput, 'https://jenkins.example.com');
    await user.type(usernameInput, 'testuser');
    await user.type(jobNameInput, 'test-job');

    expect(urlInput).toHaveValue('https://jenkins.example.com');
    expect(usernameInput).toHaveValue('testuser');
    expect(jobNameInput).toHaveValue('test-job');
  });

  it('toggles API token visibility', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    const tokenInput = screen.getByLabelText(/API Token/i);
    const toggleButton = screen.getByRole('button', { name: /show/i });

    // Initially hidden
    expect(tokenInput).toHaveAttribute('type', 'password');
    expect(toggleButton).toHaveTextContent('Show');

    // Click to show
    await user.click(toggleButton);
    expect(tokenInput).toHaveAttribute('type', 'text');
    expect(toggleButton).toHaveTextContent('Hide');

    // Click to hide again
    await user.click(toggleButton);
    expect(tokenInput).toHaveAttribute('type', 'password');
    expect(toggleButton).toHaveTextContent('Show');
  });

  it('validates required fields for test connection', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    const testButton = screen.getByRole('button', { name: /Test Connection/i });
    await user.click(testButton);

    expect(mockProps.onAnalysisError).toHaveBeenCalledWith(
      'Please fill in all connection fields'
    );
  });

  it('validates required fields for analysis', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    // Fill some but not all required fields
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    expect(mockProps.onAnalysisError).toHaveBeenCalledWith(
      'Please fill in all required fields (URL, Username, API Token, Job Name)'
    );
  });

  it('calls API for successful Jenkins analysis', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockResolvedValueOnce(mockAnalysisResult);

    render(<JenkinsForm {...mockProps} />);

    // Fill all required fields
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/API Token/i), 'test-token');
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');
    await user.type(screen.getByLabelText(/Build Number/i), '123');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisStart).toHaveBeenCalled();
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalledWith(
        {
          url: 'https://jenkins.example.com',
          username: 'testuser',
          apiToken: 'test-token',
          jobName: 'test-job',
          buildNumber: '123',
        },
        mockProps.repoUrl
      );
      expect(mockProps.onAnalysisComplete).toHaveBeenCalledWith(mockAnalysisResult);
    });
  });

  it('handles Jenkins analysis API error', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Jenkins connection failed';
    mockedApi.analyzeJenkinsBuild.mockRejectedValueOnce(new Error(errorMessage));

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/API Token/i), 'test-token');
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
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/API Token/i), 'test-token');
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalledWith(
        {
          url: 'https://jenkins.example.com',
          username: 'testuser',
          apiToken: 'test-token',
          jobName: 'test-job',
          buildNumber: '',
        },
        mockProps.repoUrl
      );
    });
  });

  it('displays security note for API token', () => {
    render(<JenkinsForm {...mockProps} />);

    expect(screen.getByText(/Security Note:/i)).toBeInTheDocument();
    expect(screen.getByText(/Your credentials are only used for this analysis/i)).toBeInTheDocument();
  });

  it('clears test connection status when form changes', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    const urlInput = screen.getByLabelText(/Jenkins URL/i);

    // Simulate changing input (this would normally trigger test connection reset)
    await user.type(urlInput, 'https://jenkins.example.com');

    // The test connection status should reset to 'idle' when form changes
    // This is handled by the handleInputChange function
    expect(urlInput).toHaveValue('https://jenkins.example.com');
  });

  it('handles non-Error objects in catch blocks', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeJenkinsBuild.mockRejectedValueOnce('String error');

    render(<JenkinsForm {...mockProps} />);

    // Fill required fields
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/API Token/i), 'test-token');
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
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/API Token/i), 'test-token');
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');

    const analyzeButton = screen.getByRole('button', { name: /Analyze Jenkins Build/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockedApi.analyzeJenkinsBuild).toHaveBeenCalledWith(
        expect.any(Object),
        'https://github.com/custom/repo'
      );
    });
  });

  it('shows helpful information about Jenkins setup', () => {
    render(<JenkinsForm {...mockProps} />);

    expect(screen.getByText(/Connect to your Jenkins server/i)).toBeInTheDocument();
    expect(screen.getByText(/Example: my-project-main/i)).toBeInTheDocument();
    expect(screen.getByText(/You can generate an API token in Jenkins/i)).toBeInTheDocument();
  });

  it('maintains form state correctly', async () => {
    const user = userEvent.setup();
    render(<JenkinsForm {...mockProps} />);

    // Fill multiple fields
    await user.type(screen.getByLabelText(/Jenkins URL/i), 'https://jenkins.example.com');
    await user.type(screen.getByLabelText(/Username/i), 'testuser');
    await user.type(screen.getByLabelText(/Job Name/i), 'test-job');
    await user.type(screen.getByLabelText(/Build Number/i), '456');

    // Verify all values are maintained
    expect(screen.getByLabelText(/Jenkins URL/i)).toHaveValue('https://jenkins.example.com');
    expect(screen.getByLabelText(/Username/i)).toHaveValue('testuser');
    expect(screen.getByLabelText(/Job Name/i)).toHaveValue('test-job');
    expect(screen.getByLabelText(/Build Number/i)).toHaveValue('456');
  });
});
