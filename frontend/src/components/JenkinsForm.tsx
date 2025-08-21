import React, { useState, useEffect } from 'react';
import { AnalysisResult } from '../App';
import { analyzeJenkinsBuild, fetchJenkinsJobs as apiFetchJenkinsJobs } from '../services/api';
import { useSettings } from '../contexts/SettingsContext';

interface JenkinsFormProps {
  repoUrl: string;
  branch: string;
  commit: string;
  systemPrompt: string;
  onAnalysisStart: () => void;
  onAnalysisComplete: (results: AnalysisResult) => void;
  onAnalysisError: (error: string) => void;
}

interface JenkinsConfig {
  url: string;
  username: string;
  apiToken: string;
  jobName: string;
  buildNumber: string;
}

const JenkinsForm: React.FC<JenkinsFormProps> = ({
  repoUrl,
  branch,
  commit,
  systemPrompt,
  onAnalysisStart,
  onAnalysisComplete,
  onAnalysisError,
}) => {
  const { settings } = useSettings();

  const [config, setConfig] = useState<JenkinsConfig>({
    url: '',
    username: '',
    apiToken: '',
    jobName: '',
    buildNumber: '',
  });
  const [includeRepoContext, setIncludeRepoContext] = useState(false);

  // Populate form with saved settings
  useEffect(() => {
    if (settings) {
      setConfig(prev => ({
        ...prev,
        url: settings.jenkins.url || '',
        username: settings.jenkins.username || '',
        apiToken: settings.jenkins.api_token || '',
      }));
    }
  }, [settings]);

  const [jobsList, setJobsList] = useState<string[]>([]);
  const [jobsLoading, setJobsLoading] = useState(false);
  const [jobSearchQuery, setJobSearchQuery] = useState('');
  const [showJobDropdown, setShowJobDropdown] = useState(false);
  const [filteredJobs, setFilteredJobs] = useState<string[]>([]);

  const handleInputChange = (field: keyof JenkinsConfig, value: string) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const fetchJenkinsJobs = async () => {
    // Check if Jenkins is configured in settings
    if (!settings?.jenkins?.url || !settings?.jenkins?.username || !settings?.jenkins?.api_token) {
      onAnalysisError('Please configure Jenkins connection in Settings first');
      return;
    }

    setJobsLoading(true);
    try {
      const jobs = await apiFetchJenkinsJobs();
      setJobsList(jobs);
      setFilteredJobs(jobs);
    } catch (error) {
      console.error('Error fetching Jenkins jobs:', error);
      onAnalysisError(error instanceof Error ? error.message : 'Error connecting to Jenkins. Please check your configuration in Settings.');
    } finally {
      setJobsLoading(false);
    }
  };

  const handleJobSearch = (query: string) => {
    setJobSearchQuery(query);
    setConfig(prev => ({ ...prev, jobName: query }));

    if (query.trim() === '') {
      setFilteredJobs(jobsList);
    } else {
      const filtered = jobsList.filter(job =>
        job.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredJobs(filtered);
    }
    setShowJobDropdown(true);
  };

  const selectJob = (jobName: string) => {
    setConfig(prev => ({ ...prev, jobName }));
    setJobSearchQuery(jobName);
    setShowJobDropdown(false);
  };

  // Auto-fetch jobs when component loads if Jenkins is configured
  useEffect(() => {
    // We will no longer auto-fetch to prevent errors on load.
    // The user can fetch jobs manually.
  }, [settings]);

  const handleAnalyze = async () => {
    // Check if Jenkins is configured in settings
    if (!settings?.jenkins?.url || !settings?.jenkins?.username || !settings?.jenkins?.api_token) {
      onAnalysisError('Please configure Jenkins connection in Settings first');
      return;
    }

    if (!config.jobName) {
      onAnalysisError('Please select a job name');
      return;
    }

    try {
      onAnalysisStart();
      // Use settings for Jenkins config instead of form data
      const jenkinsConfig = {
        url: settings.jenkins.url,
        username: settings.jenkins.username,
        apiToken: settings.jenkins.api_token,
        jobName: config.jobName,
        buildNumber: config.buildNumber,
      };

      const repositoryConfig = repoUrl?.trim() ? {
        url: repoUrl.trim(),
        branch: branch?.trim() || undefined,
        commit: commit?.trim() || undefined,
        includeContext: includeRepoContext
      } : undefined;

      const results = await analyzeJenkinsBuild(jenkinsConfig, repositoryConfig, systemPrompt);
      onAnalysisComplete(results);
    } catch (error) {
      onAnalysisError(error instanceof Error ? error.message : 'Failed to analyze Jenkins build');
    }
  };

  const isFormValid = settings?.jenkins?.url && settings?.jenkins?.username && settings?.jenkins?.api_token && config.jobName;

  return (
    <div className="space-y-6">
      {/* Jenkins Status */}
      {settings?.jenkins?.url ? (
        <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-md p-4">
          <div className="flex items-center justify-between">
            <div className="flex">
              <svg className="w-5 h-5 text-green-400 dark:text-green-300 mr-3 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div>
                <h4 className="text-sm font-medium text-green-800 dark:text-green-200">
                  Jenkins Connected
                </h4>
                <p className="mt-1 text-sm text-green-700 dark:text-green-300">
                  Connected to {settings.jenkins.url}
                </p>
              </div>
            </div>
            <button
              onClick={fetchJenkinsJobs}
              disabled={jobsLoading}
              className="inline-flex items-center px-3 py-2 border border-green-300 text-sm font-medium rounded-md text-green-700 bg-green-50 hover:bg-green-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors disabled:opacity-50"
            >
              {jobsLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-600 mr-2"></div>
                  Loading...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  Load Jobs
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-md p-4">
          <div className="flex">
            <svg className="w-5 h-5 text-blue-400 dark:text-blue-300 mr-3 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="text-sm font-medium text-blue-800 dark:text-blue-200">
                Jenkins Configuration Required
              </h4>
              <p className="mt-1 text-sm text-blue-700 dark:text-blue-300">
                Please configure your Jenkins connection in the Settings page before analyzing builds.
                Go to Settings → Jenkins to set up your server URL, username, and API token.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Job Settings */}
      <div className="border-t border-gray-200 pt-6">
        <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-4">Build Information</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Job Name with Dropdown */}
          <div>
            <label htmlFor="job-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Job Name *
            </label>
            <div className="relative">
              <input
                type="text"
                id="job-name"
                value={config.jobName}
                onChange={(e) => handleJobSearch(e.target.value)}
                onFocus={() => setShowJobDropdown(filteredJobs.length > 0)}
                onBlur={() => setTimeout(() => setShowJobDropdown(false), 200)}
                placeholder={jobsLoading ? "Loading jobs..." : "Type to search jobs or enter manually"}
                disabled={jobsLoading}
                className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400"
              />
              {jobsLoading && (
                <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600"></div>
                </div>
              )}
              {!jobsLoading && jobsList.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowJobDropdown(!showJobDropdown)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-400"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}

              {/* Dropdown */}
              {showJobDropdown && filteredJobs.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-lg max-h-60 overflow-auto">
                  {filteredJobs.slice(0, 10).map((job, index) => (
                    <button
                      key={index}
                      type="button"
                      onClick={() => selectJob(job)}
                      className="w-full px-3 py-2 text-left hover:bg-gray-100 dark:hover:bg-gray-600 text-gray-900 dark:text-white border-b border-gray-200 dark:border-gray-600 last:border-b-0"
                    >
                      {job}
                    </button>
                  ))}
                  {filteredJobs.length > 10 && (
                    <div className="px-3 py-2 text-xs text-gray-500 dark:text-gray-400 border-t border-gray-200 dark:border-gray-600">
                      Showing 10 of {filteredJobs.length} jobs. Keep typing to narrow results.
                    </div>
                  )}
                </div>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              {jobsList.length > 0
                ? `${jobsList.length} jobs available. Type to search or select from dropdown.`
                : "Configure Jenkins in Settings to load available jobs, or enter job name manually"}
            </p>
          </div>

          {/* Build Number */}
          <div>
            <label htmlFor="build-number" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              Build Number
            </label>
            <input
              type="text"
              id="build-number"
              value={config.buildNumber}
              onChange={(e) => handleInputChange('buildNumber', e.target.value)}
              placeholder="latest or 123"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400"
            />
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
              Leave empty for latest build, or specify a build number
            </p>
          </div>
        </div>
      </div>

      {/* Repository Context Option */}
      {isFormValid && repoUrl && (
        <div className="flex items-center space-x-2 pt-4 border-t border-gray-200 dark:border-gray-700">
          <input
            type="checkbox"
            id="includeRepoContextJenkins"
            checked={includeRepoContext}
            onChange={(e) => setIncludeRepoContext(e.target.checked)}
            className="rounded border-gray-300 dark:border-gray-600 text-primary-600 focus:ring-primary-500 dark:focus:ring-primary-400"
          />
          <label htmlFor="includeRepoContextJenkins" className="text-sm text-gray-700 dark:text-gray-300">
            Include repository source code in analysis (slower but more accurate)
          </label>
        </div>
      )}

      {/* Analyze Button */}
      {isFormValid && (
        <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={handleAnalyze}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-colors"
          >
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
            Analyze Jenkins Build
          </button>
        </div>
      )}
    </div>
  );
};

export default JenkinsForm;
