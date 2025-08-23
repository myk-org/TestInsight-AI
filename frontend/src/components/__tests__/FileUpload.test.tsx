import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import FileUpload from '../FileUpload';
import * as api from '../../services/api';

// Mock the API module
vi.mock('../../services/api');
const mockedApi = api as any;

let mockDroppedFiles: File[] = [];

// Mock react-dropzone
vi.mock('react-dropzone', () => ({
  useDropzone: vi.fn((options: any) => ({
    getRootProps: () => ({
      'data-testid': 'dropzone',
      onClick: () => options.onDrop?.(mockDroppedFiles),
    }),
    getInputProps: () => ({
      'data-testid': 'file-input',
      type: 'file',
    }),
    isDragActive: false,
  })),
}));

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
      title: 'Test Failure Analysis',
      description: 'Multiple tests are failing due to database connectivity issues',
      severity: 'high',
      category: 'Infrastructure',
      suggestions: ['Check database connection', 'Verify credentials'],
      confidence: 0.9,
    },
  ],
  summary: 'Analysis completed successfully with 1 critical issue found',
  recommendations: [
    'Fix database connectivity issues',
    'Implement retry logic for failed connections',
  ],
  test_failures: [
    {
      test_name: 'UserServiceTest.testCreateUser',
      failure_reason: 'Database connection timeout',
      file_path: 'src/test/java/UserServiceTest.java',
      line_number: 45,
    },
  ],
  performance_insights: [
    {
      metric: 'execution_time',
      value: 120.5,
      threshold: 60.0,
      status: 'warning',
      suggestion: 'Consider optimizing database queries',
    },
  ],
};

describe('FileUpload Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders file upload dropzone', () => {
    render(<FileUpload {...mockProps} />);

    expect(screen.getByTestId('dropzone')).toBeInTheDocument();
    expect(screen.getByText('Upload JUnit XML files')).toBeInTheDocument();
    expect(screen.getByText('Drag and drop your test result XML files, or click to browse')).toBeInTheDocument();
  });

  it('displays supported formats information', () => {
    render(<FileUpload {...mockProps} />);

    expect(screen.getByText(/Supported formats: JUnit XML, TestNG XML/)).toBeInTheDocument();
  });

  it('shows file list when files are uploaded', async () => {
    const user = userEvent.setup();
    render(<FileUpload {...mockProps} />);

    // Create mock files
    const xmlFile1 = new File(['<testsuites></testsuites>'], 'test1.xml', { type: 'application/xml' });
    const xmlFile2 = new File(['<testsuites></testsuites>'], 'test2.xml', { type: 'text/xml' });

    // Mock the dropzone callback
    mockDroppedFiles = [xmlFile1, xmlFile2];

    // Re-render with mocked dropzone
    render(<FileUpload {...mockProps} />);

    // Click to trigger file upload
    const [firstDropzone] = screen.getAllByTestId('dropzone');
    await user.click(firstDropzone);

    await waitFor(() => {
      expect(screen.getByText('Uploaded Files (2)')).toBeInTheDocument();
      expect(screen.getByText('test1.xml')).toBeInTheDocument();
      expect(screen.getByText('test2.xml')).toBeInTheDocument();
    });
  });

  it('filters non-XML files and shows error', async () => {
    const user = userEvent.setup();
    render(<FileUpload {...mockProps} />);

    // Create mock non-XML file
    const textFile = new File(['some text'], 'test.txt', { type: 'text/plain' });

    // Mock the dropzone callback to simulate dropping non-XML files
    mockDroppedFiles = [textFile];

    // Re-render with mocked dropzone
    render(<FileUpload {...mockProps} />);

    // Click to trigger file upload
    const [firstDropzone2] = screen.getAllByTestId('dropzone');
    await user.click(firstDropzone2);

    await waitFor(() => {
      expect(mockProps.onAnalysisError).toHaveBeenCalledWith(
        'Please upload XML files only. JUnit XML test reports are supported.'
      );
    });
  });

  it('allows removing uploaded files', async () => {
    const user = userEvent.setup();

    // Create mock file
    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    // Mock the dropzone callback
    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    // Upload file
    await user.click(screen.getByTestId('dropzone'));

    await waitFor(() => {
      expect(screen.getByText('test.xml')).toBeInTheDocument();
    });

    // Find and click remove button
    const removeButton = screen.getAllByRole('button').find((b) => (b as HTMLElement).textContent === '') as HTMLElement;
    await user.click(removeButton);

    await waitFor(() => {
      expect(screen.queryByText('test.xml')).not.toBeInTheDocument();
      expect(screen.queryByText('Uploaded Files')).not.toBeInTheDocument();
    });
  });

  it('shows analyze button when files are uploaded', async () => {
    const user = userEvent.setup();

    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    await user.click(screen.getByTestId('dropzone'));

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Analyze Test Results/i })).toBeInTheDocument();
    });
  });

  it('calls API and handles successful analysis', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeXMLFiles.mockResolvedValueOnce(mockAnalysisResult);

    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    // Upload file
    await user.click(screen.getByTestId('dropzone'));

    // Click analyze button
    const analyzeButton = await screen.findByRole('button', { name: /Analyze Test Results/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisStart).toHaveBeenCalled();
      expect(mockedApi.analyzeXMLFiles).toHaveBeenCalled();
      const args = (mockedApi.analyzeXMLFiles as any).mock.calls[0];
      expect(args[0][0].name).toBe('test.xml');
      expect(args[1]).toMatchObject({ url: mockProps.repoUrl });
      expect(mockProps.onAnalysisComplete).toHaveBeenCalledWith(mockAnalysisResult);
    });
  });

  it('handles API error during analysis', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Analysis failed due to server error';
    mockedApi.analyzeXMLFiles.mockRejectedValueOnce(new Error(errorMessage));

    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    // Upload file
    await user.click(screen.getByTestId('dropzone'));

    // Click analyze button
    const analyzeButton = await screen.findByRole('button', { name: /Analyze Test Results/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisStart).toHaveBeenCalled();
      expect(mockProps.onAnalysisError).toHaveBeenCalledWith(errorMessage);
    });
  });

  it('shows error when trying to analyze without files', async () => {
    const user = userEvent.setup();
    render(<FileUpload {...mockProps} />);

    // Try to click analyze without uploading files (button shouldn't be visible)
    expect(screen.queryByRole('button', { name: /Analyze Test Results/i })).not.toBeInTheDocument();
  });

  it('displays file size information', async () => {
    const user = userEvent.setup();

    // Create a file with specific size (1024 bytes = 1KB)
    const content = 'x'.repeat(1024);
    const xmlFile = new File([content], 'large-test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    await user.click(screen.getByTestId('dropzone'));

    await waitFor(() => {
      expect(screen.getByText('large-test.xml')).toBeInTheDocument();
      expect(screen.getByText('1.0 KB')).toBeInTheDocument();
    });
  });

  it('handles non-Error objects in catch block', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeXMLFiles.mockRejectedValueOnce('String error');

    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...mockProps} />);

    await user.click(screen.getByTestId('dropzone'));

    const analyzeButton = await screen.findByRole('button', { name: /Analyze Test Results/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockProps.onAnalysisError).toHaveBeenCalledWith('Failed to analyze files');
    });
  });

  it('passes repo URL to API call', async () => {
    const user = userEvent.setup();
    mockedApi.analyzeXMLFiles.mockResolvedValueOnce(mockAnalysisResult);

    const customProps = {
      ...mockProps,
      repoUrl: 'https://github.com/custom/repo',
    };

    const xmlFile = new File(['<testsuites></testsuites>'], 'test.xml', { type: 'application/xml' });

    mockDroppedFiles = [xmlFile];

    render(<FileUpload {...customProps} />);

    await user.click(screen.getByTestId('dropzone'));

    const analyzeButton = await screen.findByRole('button', { name: /Analyze Test Results/i });
    await user.click(analyzeButton);

    await waitFor(() => {
      expect(mockedApi.analyzeXMLFiles).toHaveBeenCalled();
      const args = (mockedApi.analyzeXMLFiles as any).mock.calls[0];
      expect(args[1]).toMatchObject({ url: 'https://github.com/custom/repo' });
    });
  });
});
