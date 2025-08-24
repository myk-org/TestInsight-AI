import React, { useState, useEffect } from 'react';
import FileUpload from './FileUpload';
import TextInput from './TextInput';
import JenkinsForm from './JenkinsForm';
import { AnalysisResult } from '../App';

interface InputTabsProps {
  onAnalysisStart: () => void;
  onAnalysisComplete: (results: AnalysisResult) => void;
  onAnalysisError: (error: string) => void;
}

type TabType = 'file' | 'text' | 'jenkins';

const InputTabs: React.FC<InputTabsProps> = ({
  onAnalysisStart,
  onAnalysisComplete,
  onAnalysisError,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('file');
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [commit, setCommit] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [isValidUrl, setIsValidUrl] = useState(true);

  useEffect(() => {
    const storedRepoUrl = localStorage.getItem('repoUrl');
    if (storedRepoUrl) {
      setRepoUrl(storedRepoUrl);
      validateGitHubUrl(storedRepoUrl);
    }
    const storedSystemPrompt = localStorage.getItem('systemPrompt');
    if (storedSystemPrompt) {
      setSystemPrompt(storedSystemPrompt);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('repoUrl', repoUrl);
  }, [repoUrl]);

  useEffect(() => {
    localStorage.setItem('systemPrompt', systemPrompt);
  }, [systemPrompt]);

  const tabs = [
    {
      id: 'file' as TabType,
      name: 'File Upload',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
      ),
      description: 'Upload JUnit XML files',
    },
    {
      id: 'text' as TabType,
      name: 'Text Input',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      description: 'Paste console output',
    },
    {
      id: 'jenkins' as TabType,
      name: 'Jenkins',
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
      description: 'Connect to Jenkins',
    },
  ];

  const validateGitHubUrl = (url: string) => {
    if (!url.trim()) {
      setIsValidUrl(true);
      return;
    }

    // Only support GitHub HTTPS URLs
    const urlPattern = /^https:\/\/github\.com\/[^\s\/]+\/[^\s\/]+(?:\.git)?$/;
    setIsValidUrl(urlPattern.test(url.trim()));
  };

  const handleRepoUrlChange = (url: string) => {
    setRepoUrl(url);
    validateGitHubUrl(url);
  };

  const handleBranchChange = (newBranch: string) => {
    setBranch(newBranch);
    if (newBranch.trim()) {
      setCommit(''); // Clear commit when branch is set
    }
  };

  const handleCommitChange = (newCommit: string) => {
    setCommit(newCommit);
    if (newCommit.trim()) {
      setBranch(''); // Clear branch when commit is set
    }
  };

  const renderTabContent = () => {
    const commonProps = {
      repoUrl,
      branch,
      commit,
      systemPrompt,
      onAnalysisStart,
      onAnalysisComplete,
      onAnalysisError,
    };

    switch (activeTab) {
      case 'file':
        return <FileUpload {...commonProps} />;
      case 'text':
        return <TextInput {...commonProps} />;
      case 'jenkins':
        return <JenkinsForm {...commonProps} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Collapsible System Prompt */}
      <details className="group">
        <summary className="flex items-center justify-between w-full cursor-pointer text-left text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
          <span className="flex items-center gap-2">
            <span>System Prompt (Optional)</span>
            {/* Show indicator only when details is closed and prompt is non-empty */}
            {systemPrompt.trim() && (
              <span
                aria-label="System prompt configured"
                className="group-open:hidden inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 border border-green-200 dark:border-green-800"
              >
                Configured
              </span>
            )}
          </span>
          <svg className="w-5 h-5 transform transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="mt-4">
          <textarea
            id="system-prompt"
            rows={3}
            value={systemPrompt}
            onChange={(e) => setSystemPrompt(e.target.value)}
            placeholder="e.g., You are a senior software engineer specializing in test failures."
            className="w-full px-3 py-2 border rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 border-gray-300 dark:border-gray-600"
          />
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            Provide a custom system prompt to guide the AI analysis.
          </p>
        </div>
      </details>

      {/* Collapsible Repository Configuration */}
      <details className="group">
        <summary className="flex items-center justify-between w-full cursor-pointer text-left text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white">
          <span className="flex items-center gap-2">
            <span>GitHub Repository URL (Optional)</span>
            {/* Show indicator only when details is closed and repo is valid/non-empty */}
            {repoUrl.trim() && isValidUrl && (
              <span
                aria-label="Repository configured"
                className="group-open:hidden inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 border border-green-200 dark:border-green-800"
              >
                Configured
              </span>
            )}
          </span>
          <svg className="w-5 h-5 transform transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </summary>
        <div className="mt-4 space-y-4">
          <div>
            <input
              type="text"
              id="repo-url"
              value={repoUrl}
              onChange={(e) => handleRepoUrlChange(e.target.value)}
              placeholder="https://github.com/user/repository.git"
              className={`w-full px-3 py-2 border rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 ${
                repoUrl && !isValidUrl
                  ? 'border-red-300 dark:border-red-600'
                  : 'border-gray-300 dark:border-gray-600'
              }`}
            />
            {repoUrl && !isValidUrl && (
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                Please enter a valid GitHub HTTPS URL (e.g., https://github.com/user/repo.git)
              </p>
            )}
          </div>

          {/* Branch and Commit inputs - only show when repo URL is provided */}
          {repoUrl && isValidUrl && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label htmlFor="branch" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Branch
                </label>
                <input
                  type="text"
                  id="branch"
                  value={branch}
                  onChange={(e) => handleBranchChange(e.target.value)}
                  placeholder="main"
                  disabled={!!commit}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 border-gray-300 dark:border-gray-600 ${
                    commit ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>

              <div>
                <label htmlFor="commit" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Commit Hash
                </label>
                <input
                  type="text"
                  id="commit"
                  value={commit}
                  onChange={(e) => handleCommitChange(e.target.value)}
                  placeholder="abc123..."
                  disabled={!!branch}
                  className={`w-full px-3 py-2 border rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 border-gray-300 dark:border-gray-600 ${
                    branch ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                />
              </div>
            </div>
          )}

          <div className="text-xs text-gray-500 dark:text-gray-400 space-y-1">
            <p>Provide GitHub repository details to get more accurate code suggestions.</p>
            <p><strong>Note:</strong> Only GitHub HTTPS URLs are supported. Branch and commit are optional.</p>

            <details className="mt-2">
              <summary className="cursor-pointer hover:text-gray-700 dark:hover:text-gray-300">Examples</summary>
              <div className="mt-1 pl-4 space-y-1 font-mono text-xs">
                <div>https://github.com/user/repo.git</div>
                <div>https://github.com/user/repository</div>
              </div>
            </details>
          </div>
        </div>
      </details>

      {/* Tabs */}
      <div>
        <div className="border-b border-gray-200 dark:border-gray-700">
          <nav className="-mb-px flex space-x-8">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`group inline-flex items-center py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-primary-500 dark:border-primary-400 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                <span
                  className={`mr-2 ${
                    activeTab === tab.id
                      ? 'text-primary-500 dark:text-primary-400'
                      : 'text-gray-400 dark:text-gray-500 group-hover:text-gray-500 dark:group-hover:text-gray-400'
                  }`}
                >
                  {tab.icon}
                </span>
                <span>{tab.name}</span>
              </button>
            ))}
          </nav>
        </div>

        {/* Tab Descriptions */}
        <div className="mt-4 h-10">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              className={`${activeTab === tab.id ? 'block' : 'hidden'}`}
            >
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">{tab.description}</p>
            </div>
          ))}
        </div>

        {/* Tab Content */}
        <div className="mt-6">
          {renderTabContent()}
        </div>
      </div>
    </div>
  );
};

export default InputTabs;
