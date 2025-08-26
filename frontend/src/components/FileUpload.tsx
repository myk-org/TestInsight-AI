import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';
import { AnalysisResult } from '../App';
import { analyzeXMLFiles } from '../services/api';

interface FileUploadProps {
  repoUrl: string;
  branch: string;
  commit: string;
  systemPrompt: string;
  onAnalysisStart: () => void;
  onAnalysisComplete: (results: AnalysisResult) => void;
  onAnalysisError: (error: string) => void;
}

const FileUpload: React.FC<FileUploadProps> = ({
  repoUrl,
  branch,
  commit,
  systemPrompt,
  onAnalysisStart,
  onAnalysisComplete,
  onAnalysisError,
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [includeRepoContext, setIncludeRepoContext] = useState(false);

  // Disable and reset includeRepoContext when repo URL is not provided
  useEffect(() => {
    if (!repoUrl || !repoUrl.trim()) {
      if (includeRepoContext) {
        setIncludeRepoContext(false);
      }
    }
  }, [repoUrl, includeRepoContext]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    // Filter for XML files
    const xmlFiles = acceptedFiles.filter(file =>
      file.name.toLowerCase().endsWith('.xml') ||
      file.type === 'text/xml' ||
      file.type === 'application/xml'
    );

    if (xmlFiles.length === 0) {
      onAnalysisError('Please upload XML files only. JUnit XML test reports are supported.');
      return;
    }

    setUploadedFiles(xmlFiles);
  }, [onAnalysisError]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/xml': ['.xml'],
      'application/xml': ['.xml'],
    },
    multiple: true,
  });

  const removeFile = (index: number) => {
    setUploadedFiles(files => files.filter((_, i) => i !== index));
  };

  const handleAnalyze = async () => {
    if (uploadedFiles.length === 0) {
      onAnalysisError('Please upload at least one XML file');
      return;
    }

    try {
      onAnalysisStart();

      const repositoryConfig = repoUrl?.trim() ? {
        url: repoUrl.trim(),
        branch: branch?.trim() || undefined,
        commit: commit?.trim() || undefined,
        includeContext: includeRepoContext
      } : undefined;

      const results = await analyzeXMLFiles(uploadedFiles, repositoryConfig, systemPrompt);
      onAnalysisComplete(results);
    } catch (error) {
      onAnalysisError(error instanceof Error ? error.message : 'Failed to analyze files');
    }
  };

  return (
    <div className="space-y-6">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          isDragActive
            ? 'border-primary-400 dark:border-primary-500 bg-primary-50 dark:bg-primary-900/20'
            : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
        }`}
      >
        <input {...getInputProps()} />
        <div className="space-y-4">
          <div className="flex justify-center">
            <svg
              className={`w-12 h-12 ${
                isDragActive ? 'text-primary-400 dark:text-primary-500' : 'text-gray-400 dark:text-gray-500'
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <div>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              {isDragActive ? 'Drop XML files here' : 'Upload JUnit XML files'}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Drag and drop your test result XML files, or click to browse
            </p>
          </div>
          <div className="text-xs text-gray-400 dark:text-gray-500">
            Supported formats: JUnit XML, TestNG XML, and other standard test result formats
          </div>
        </div>
      </div>

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-gray-900 dark:text-white">
            Uploaded Files ({uploadedFiles.length})
          </h4>
          <div className="space-y-2">
            {uploadedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-md border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center space-x-3">
                  <svg className="w-5 h-5 text-blue-500 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <div>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{file.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {(file.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => removeFile(index)}
                  className="text-red-500 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Repository Context Option - always visible */}
      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="includeRepoContext"
          checked={includeRepoContext}
          onChange={(e) => setIncludeRepoContext(e.target.checked)}
          disabled={!repoUrl || !repoUrl.trim()}
          className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500 dark:focus:ring-primary-400 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <label htmlFor="includeRepoContext" className="text-sm text-gray-700 dark:text-gray-300">
          Include repository source code in analysis (slower but more accurate)
        </label>
      </div>

      {/* Analyze Button */}
      {uploadedFiles.length > 0 && (
        <div className="flex justify-end">
          <button
            onClick={handleAnalyze}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 dark:bg-primary-500 hover:bg-primary-700 dark:hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-800 focus:ring-primary-500 dark:focus:ring-primary-400 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Analyze Test Results
          </button>
        </div>
      )}
    </div>
  );
};

export default FileUpload;
