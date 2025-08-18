import React, { useState } from 'react';
import { AnalysisResult } from '../App';
import { analyzeTextLog } from '../services/api';

interface TextInputProps {
  repoUrl: string;
  branch: string;
  commit: string;
  onAnalysisStart: () => void;
  onAnalysisComplete: (results: AnalysisResult) => void;
  onAnalysisError: (error: string) => void;
}

const TextInput: React.FC<TextInputProps> = ({
  repoUrl,
  branch,
  commit,
  onAnalysisStart,
  onAnalysisComplete,
  onAnalysisError,
}) => {
  const [logText, setLogText] = useState('');
  const [logType, setLogType] = useState<'console' | 'junit' | 'testng' | 'pytest' | 'other'>('console');

  const handleAnalyze = async () => {
    if (!logText.trim()) {
      onAnalysisError('Please enter some log text to analyze');
      return;
    }

    try {
      onAnalysisStart();
      const results = await analyzeTextLog(logText.trim(), logType, repoUrl);
      onAnalysisComplete(results);
    } catch (error) {
      onAnalysisError(error instanceof Error ? error.message : 'Failed to analyze log text');
    }
  };

  const handleClear = () => {
    setLogText('');
  };

  const handleSampleData = () => {
    const sampleLog = `FAILURE: Build failed with an exception.

* What went wrong:
Execution failed for task ':app:testDebugUnitTest'.
> There were failing tests. See the report at: file:///path/to/project/app/build/reports/tests/testDebugUnitTest/index.html

* Test Results:
com.example.app.UserServiceTest > testCreateUser() FAILED
    java.lang.AssertionError: Expected user to be created but was null
        at org.junit.Assert.fail(Assert.java:88)
        at org.junit.Assert.assertTrue(Assert.java:41)
        at com.example.app.UserServiceTest.testCreateUser(UserServiceTest.java:45)

com.example.app.ValidationTest > testEmailValidation() FAILED
    java.lang.AssertionError: Expected validation to fail for invalid email
        at org.junit.Assert.assertTrue(Assert.java:41)
        at com.example.app.ValidationTest.testEmailValidation(ValidationTest.java:23)

2 tests completed, 2 failed`;

    setLogText(sampleLog);
    setLogType('console');
  };

  const logTypeOptions = [
    { value: 'console', label: 'Console Output', description: 'Raw console output from build tools' },
    { value: 'junit', label: 'JUnit Text', description: 'JUnit test output in text format' },
    { value: 'testng', label: 'TestNG', description: 'TestNG test results' },
    { value: 'pytest', label: 'Pytest', description: 'Python pytest output' },
    { value: 'other', label: 'Other', description: 'Other test framework output' },
  ];

  return (
    <div className="space-y-6">
      {/* Log Type Selection */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
          Log Type
        </label>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {logTypeOptions.map((option) => (
            <label
              key={option.value}
              className={`relative flex cursor-pointer rounded-lg border p-4 focus:outline-none transition-colors ${
                logType === option.value
                  ? 'border-primary-500 dark:border-primary-400 bg-primary-50 dark:bg-primary-900/20'
                  : 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-400 dark:hover:border-gray-500'
              }`}
            >
              <input
                type="radio"
                name="log-type"
                value={option.value}
                checked={logType === option.value}
                onChange={(e) => setLogType(e.target.value as any)}
                className="sr-only"
              />
              <div className="flex flex-col">
                <span
                  className={`block text-sm font-medium ${
                    logType === option.value ? 'text-primary-900 dark:text-primary-200' : 'text-gray-900 dark:text-white'
                  }`}
                >
                  {option.label}
                </span>
                <span
                  className={`block text-xs ${
                    logType === option.value ? 'text-primary-700 dark:text-primary-300' : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {option.description}
                </span>
              </div>
              {logType === option.value && (
                <div className="absolute -inset-px rounded-lg border-2 border-primary-500 dark:border-primary-400 pointer-events-none" />
              )}
            </label>
          ))}
        </div>
      </div>

      {/* Text Area */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label htmlFor="log-text" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            Log Output
          </label>
          <div className="flex space-x-2">
            <button
              onClick={handleSampleData}
              className="text-xs text-primary-600 dark:text-primary-400 hover:text-primary-500 dark:hover:text-primary-300 underline"
            >
              Load sample data
            </button>
            <button
              onClick={handleClear}
              className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 underline"
            >
              Clear
            </button>
          </div>
        </div>
        <textarea
          id="log-text"
          value={logText}
          onChange={(e) => setLogText(e.target.value)}
          rows={15}
          placeholder="Paste your test logs, console output, or error messages here...

Example formats supported:
- Build tool output (Maven, Gradle, npm, etc.)
- JUnit/TestNG test results
- Pytest output
- Console error logs
- Stack traces and error messages"
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 font-mono text-sm"
        />
        <div className="flex justify-between items-center mt-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {logText.length} characters
          </p>
          {logText.length > 10000 && (
            <p className="text-xs text-amber-600 dark:text-amber-400">
              Large logs may take longer to analyze
            </p>
          )}
        </div>
      </div>

      {/* Analyze Button */}
      {logText.trim() && (
        <div className="flex justify-end">
          <button
            onClick={handleAnalyze}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 dark:bg-primary-500 hover:bg-primary-700 dark:hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-offset-2 dark:focus:ring-offset-gray-800 focus:ring-primary-500 dark:focus:ring-primary-400 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Analyze Log Output
          </button>
        </div>
      )}
    </div>
  );
};

export default TextInput;
