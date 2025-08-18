import React, { useState } from 'react';
import { TestFailure } from '../App';
import CodeDiff from './CodeDiff';

interface TestFailureCardProps {
  failure: TestFailure;
  isExpanded: boolean;
  onToggle: () => void;
}

const TestFailureCard: React.FC<TestFailureCardProps> = ({
  failure,
  isExpanded,
  onToggle,
}) => {
  const [activeTab, setActiveTab] = useState<'analysis' | 'fix' | 'error'>('analysis');

  const hasAnalysis = failure.ai_analysis && failure.ai_analysis.trim() !== '';
  const hasFix = failure.suggested_fix && failure.suggested_fix.trim() !== '';
  const hasLocation = failure.file_path || failure.line_number;

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    // You could add a toast notification here
  };

  const formatErrorMessage = (error: string) => {
    // Split error message into lines and format stack traces
    const lines = error.split('\n');
    return lines.map((line, index) => {
      const isStackTrace = line.trim().startsWith('at ') ||
                          line.trim().includes('.java:') ||
                          line.trim().includes('.py:') ||
                          line.trim().includes('.js:') ||
                          line.trim().includes('.ts:');

      return (
        <div key={index} className={isStackTrace ? 'text-gray-600 text-sm ml-4' : 'text-gray-800'}>
          {line || '\u00A0'} {/* Non-breaking space for empty lines */}
        </div>
      );
    });
  };

  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
      {/* Card Header */}
      <div className="px-4 py-3 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                <div className="w-3 h-3 bg-red-400 dark:bg-red-500 rounded-full"></div>
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-medium text-gray-900 dark:text-white truncate">
                  {failure.test_name}
                </h3>
                {hasLocation && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {failure.file_path && (
                      <span>{failure.file_path}</span>
                    )}
                    {failure.line_number && (
                      <span>
                        {failure.file_path ? ':' : 'Line '}
                        {failure.line_number}
                      </span>
                    )}
                  </p>
                )}
              </div>
            </div>
          </div>

          {/* Status Badges */}
          <div className="flex items-center space-x-2 ml-4">
            {hasAnalysis && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                Analysis
              </span>
            )}
            {hasFix && (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">
                <svg className="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Fix
              </span>
            )}

            {/* Expand/Collapse Button */}
            <button
              onClick={onToggle}
              className="p-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400 transition-colors"
            >
              <svg
                className={`w-5 h-5 transform transition-transform ${
                  isExpanded ? 'rotate-180' : ''
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Expandable Content */}
      {isExpanded && (
        <div className="bg-gray-50 dark:bg-gray-900">
          {/* Tab Navigation */}
          <div className="border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
            <nav className="flex space-x-8 px-4">
              {hasAnalysis && (
                <button
                  onClick={() => setActiveTab('analysis')}
                  className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === 'analysis'
                      ? 'border-primary-500 dark:border-primary-400 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  AI Analysis
                </button>
              )}
              {hasFix && (
                <button
                  onClick={() => setActiveTab('fix')}
                  className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                    activeTab === 'fix'
                      ? 'border-primary-500 dark:border-primary-400 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  Suggested Fix
                </button>
              )}
              <button
                onClick={() => setActiveTab('error')}
                className={`py-3 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === 'error'
                    ? 'border-primary-500 dark:border-primary-400 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                Error Details
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-4">
            {/* AI Analysis Tab */}
            {activeTab === 'analysis' && hasAnalysis && (
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">AI Analysis</h4>
                  <button
                    onClick={() => copyToClipboard(failure.ai_analysis)}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </button>
                </div>
                <div className="prose prose-sm max-w-none">
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                    {failure.ai_analysis}
                  </div>
                </div>
              </div>
            )}

            {/* Suggested Fix Tab */}
            {activeTab === 'fix' && hasFix && (
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Suggested Fix</h4>
                  <button
                    onClick={() => copyToClipboard(failure.suggested_fix)}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </button>
                </div>

                {/* Try to detect if this is a code diff */}
                {failure.suggested_fix.includes('```') ||
                 failure.suggested_fix.includes('+++') ||
                 failure.suggested_fix.includes('---') ? (
                  <CodeDiff content={failure.suggested_fix} />
                ) : (
                  <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-gray-200 dark:border-gray-700">
                    <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                      {failure.suggested_fix}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* Error Details Tab */}
            {activeTab === 'error' && (
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white">Error Message</h4>
                  <button
                    onClick={() => copyToClipboard(failure.error_message)}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 flex items-center"
                  >
                    <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                    Copy
                  </button>
                </div>
                <div className="bg-white dark:bg-gray-800 p-4 rounded-md border border-gray-200 dark:border-gray-700 font-mono text-sm">
                  {formatErrorMessage(failure.error_message)}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default TestFailureCard;
