import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useSettings, AppSettings, SettingsUpdate, ConnectionTestResult } from '../contexts/SettingsContext';
import { validateGeminiApiKey, fetchGeminiModels, getSecretsStatus } from '../services/api';

interface FormErrors {
  [key: string]: string;
}

interface ConnectionStatus {
  [key: string]: {
    testing: boolean;
    result?: ConnectionTestResult;
    tested: boolean;
  };
}

interface TestableFormData {
  jenkins: {
    url?: string;
    username?: string;
    api_token?: string;
    verify_ssl: boolean;
  };
  github: {
    token?: string;
  };
  ai: {
    gemini_api_key?: string;
    gemini_model: string;
    temperature: number;
    max_tokens: number;
  };
}

const Settings: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const {
    settings,
    loading,
    error,
    updateSettings,
    resetSettings,
    testConnection,
    backupSettings,
    restoreSettings,
  } = useSettings();

  const [formData, setFormData] = useState<AppSettings | null>(null);
  const [originalSettings, setOriginalSettings] = useState<AppSettings | null>(null);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({});
  const [canSave, setCanSave] = useState(false);

  // Get active tab from URL, default to 'jenkins'
  const getActiveTabFromUrl = (): 'jenkins' | 'github' | 'ai' | 'preferences' => {
    const tab = searchParams.get('tab');
    if (tab && ['jenkins', 'github', 'ai', 'preferences'].includes(tab)) {
      return tab as 'jenkins' | 'github' | 'ai' | 'preferences';
    }
    return 'jenkins';
  };

  const [activeTab, setActiveTab] = useState<'jenkins' | 'github' | 'ai' | 'preferences'>(getActiveTabFromUrl());

  // AI models state
  const [availableModels, setAvailableModels] = useState<any[]>([]);
  const [secretsStatus, setSecretsStatus] = useState<Record<string, Record<string, boolean>>>({});
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [apiKeyValidating, setApiKeyValidating] = useState(false);

  // File upload state for restore
  const [restoreFile, setRestoreFile] = useState<File | null>(null);
  const [isRestoring, setIsRestoring] = useState(false);

  // Sync active tab with URL changes
  useEffect(() => {
    setActiveTab(getActiveTabFromUrl());
  }, [searchParams]);

  // Fetch secrets status on component mount
  useEffect(() => {
    const fetchSecretsStatus = async () => {
      try {
        const status = await getSecretsStatus();
        setSecretsStatus(status);
      } catch (error) {
        console.error('Failed to fetch secrets status:', error);
      }
    };

    fetchSecretsStatus();
  }, []);

  // Initialize form data when settings are loaded
  useEffect(() => {
    if (settings) {
      // Ensure AI settings have valid default values
      const validatedSettings = {
        ...settings,
        ai: {
          ...settings.ai,
          // Ensure gemini_model is never empty/null
          gemini_model: settings.ai.gemini_model || 'gemini-pro',
        }
      };
      setFormData(validatedSettings);
      setOriginalSettings(validatedSettings);
      // Reset connection status and save capability when settings change
      setConnectionStatus({});
      setCanSave(false);
    }
  }, [settings]);

  // Clear messages after 5 seconds
  useEffect(() => {
    if (successMessage) {
      const timer = setTimeout(() => setSuccessMessage(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [successMessage]);

  // Check if we can save settings - only allow saving if there are changes and requirements are met
  useEffect(() => {
    if (!formData || !originalSettings) {
      setCanSave(false);
      return;
    }

    // First check if there are any changes made to the form
    const hasChanges = hasFormChanges();
    if (!hasChanges) {
      setCanSave(false);
      return;
    }

    const configuredServices = [];
    const newlyConfiguredServices = [];

    // Check Jenkins configuration
    if (formData.jenkins.url) {
      configuredServices.push('jenkins');
      // Only requires testing if new credentials are provided or if not previously configured
      if (formData.jenkins.api_token || !secretsStatus?.jenkins?.api_token) {
        newlyConfiguredServices.push('jenkins');
      }
    }

    // Check GitHub configuration
    if (formData.github.token || secretsStatus?.github?.token) {
      configuredServices.push('github');
      // Only requires testing if new token is provided
      if (formData.github.token) {
        newlyConfiguredServices.push('github');
      }
    }

    // Check AI configuration
    if (formData.ai.gemini_api_key || secretsStatus?.ai?.gemini_api_key) {
      configuredServices.push('ai');
      // Only requires testing if new API key is provided
      if (formData.ai.gemini_api_key) {
        newlyConfiguredServices.push('ai');
      }
    }

    // If no services are configured, allow saving (preferences only changes)
    if (configuredServices.length === 0) {
      setCanSave(true);
      return;
    }

    // If no new services are being configured, allow saving (using existing secrets)
    if (newlyConfiguredServices.length === 0) {
      setCanSave(true);
      return;
    }

    // Check if at least one newly configured service has been tested successfully
    const hasSuccessfulTest = newlyConfiguredServices.some(service => {
      const status = connectionStatus[service];
      return status && status.tested && status.result?.success;
    });

    setCanSave(hasSuccessfulTest);
  }, [formData, connectionStatus, secretsStatus, originalSettings]);

  // Utility function to check if any changes have been made to the form
  const hasFormChanges = (): boolean => {
    if (!formData || !originalSettings) return false;

    // Compare all fields except sensitive ones (they're empty in form but may exist in original)
    // For sensitive fields, only consider it changed if user entered a new value

    // Jenkins changes
    if (formData.jenkins.url !== originalSettings.jenkins.url ||
        formData.jenkins.username !== originalSettings.jenkins.username ||
        formData.jenkins.verify_ssl !== originalSettings.jenkins.verify_ssl ||
        (formData.jenkins.api_token && formData.jenkins.api_token.trim() !== '')) {
      return true;
    }

    // GitHub changes
    if (formData.github.token && formData.github.token.trim() !== '') {
      return true;
    }

    // AI changes
    if (formData.ai.gemini_model !== originalSettings.ai.gemini_model ||
        formData.ai.temperature !== originalSettings.ai.temperature ||
        formData.ai.max_tokens !== originalSettings.ai.max_tokens ||
        (formData.ai.gemini_api_key && formData.ai.gemini_api_key.trim() !== '')) {
      return true;
    }

    // Preferences changes
    if (formData.preferences.theme !== originalSettings.preferences.theme) {
      return true;
    }

    return false;
  };

  // Utility function to check if API key is valid format
  const isValidApiKeyFormat = (apiKey: string): boolean => {
    return apiKey.startsWith('AIzaSy') && apiKey.length === 39;
  };

  // Handle tab change with URL update
  const handleTabChange = (tab: 'jenkins' | 'github' | 'ai' | 'preferences') => {
    setActiveTab(tab);
    setSearchParams({ tab });
  };

  // Handle refresh models button click
  const handleRefreshModels = async () => {
    if (!secretsStatus?.ai?.gemini_api_key) {
      setModelsError('No API key configured. Please configure and test your AI connection first.');
      return;
    }

    setModelsLoading(true);
    setModelsError(null);

    try {
      // We cannot fetch models without an API key, so show appropriate message
      throw new Error('Cannot refresh models without re-entering API key. Please test connection with your API key first.');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to refresh models';
      setModelsError(errorMessage);
      setAvailableModels([]);
    } finally {
      setModelsLoading(false);
    }
  };

  // Helper function to safely convert any value to string for error display
  const getErrorMessage = (error: any): string => {
    if (typeof error === 'string') return error;
    if (error instanceof Error) return error.message;
    if (error && typeof error === 'object' && error.message) return error.message;
    if (error && typeof error === 'object') return 'An error occurred while processing your request';
    return 'An unexpected error occurred';
  };

  // Fetch models from API using form values (for test connection)
  const fetchModelsWithApiKey = useCallback(async (apiKey: string): Promise<{ success: boolean; models?: any[]; error?: string }> => {
    if (!isValidApiKeyFormat(apiKey)) {
      return {
        success: false,
        error: 'API key must start with "AIzaSy" and be 39 characters long'
      };
    }

    try {
      // First validate the API key
      const validation = await validateGeminiApiKey(apiKey);

      if (!validation.valid) {
        return {
          success: false,
          error: validation.message || 'Invalid API key'
        };
      }

      // If validation passes, fetch models
      const models = await fetchGeminiModels(apiKey);
      return {
        success: true,
        models
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch models'
      };
    }
  }, []);

  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    if (!formData) return false;

    // Jenkins validation
    if (formData.jenkins.url) {
      if (!formData.jenkins.url.startsWith('http://') && !formData.jenkins.url.startsWith('https://')) {
        errors['jenkins.url'] = 'URL must start with http:// or https://';
      }
      if (!formData.jenkins.username) {
        errors['jenkins.username'] = 'Username is required when URL is provided';
      }
      // Only require API token if none is configured and none is provided in form
      if (!formData.jenkins.api_token && !secretsStatus?.jenkins?.api_token) {
        errors['jenkins.api_token'] = 'API token is required when URL is provided';
      }
    }

    // GitHub validation - no additional validation needed for token only

    // AI validation
    if (formData.ai.temperature < 0 || formData.ai.temperature > 2) {
      errors['ai.temperature'] = 'Temperature must be between 0 and 2';
    }
    if (formData.ai.max_tokens < 1 || formData.ai.max_tokens > 32768) {
      errors['ai.max_tokens'] = 'Max tokens must be between 1 and 32768';
    }

    // Preferences validation - no additional validation needed currently

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (section: keyof AppSettings, field: string, value: any) => {
    if (!formData) return;

    setFormData(prev => {
      if (!prev) return null;

      const currentSection = prev[section] as Record<string, any>;

      return {
        ...prev,
        [section]: {
          ...currentSection,
          [field]: value,
        },
      };
    });

    // Clear specific field error
    const errorKey = `${section}.${field}`;
    if (formErrors[errorKey]) {
      setFormErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[errorKey];
        return newErrors;
      });
    }

    // Clear connection status when form values change
    setConnectionStatus(prev => {
      const newStatus = { ...prev };
      // Clear relevant connection status based on section
      if (section === 'jenkins' && newStatus.jenkins) {
        newStatus.jenkins = { ...newStatus.jenkins, tested: false, result: undefined };
      } else if (section === 'github' && newStatus.github) {
        newStatus.github = { ...newStatus.github, tested: false, result: undefined };
      } else if (section === 'ai' && newStatus.ai) {
        // Only clear connection status when API key changes, not when model selection changes
        if (field === 'gemini_api_key') {
          newStatus.ai = { ...newStatus.ai, tested: false, result: undefined };
          setAvailableModels([]);
          setModelsError(null);
        }
      }
      return newStatus;
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData || !validateForm()) {
      return;
    }

    setIsSubmitting(true);
    setSuccessMessage(null);

    try {
      const update: SettingsUpdate = {
        jenkins: formData.jenkins,
        github: formData.github,
        ai: formData.ai,
        preferences: formData.preferences,
      };

      await updateSettings(update);
      setSuccessMessage('Settings saved successfully!');

      // Update original settings to reflect the saved state
      setOriginalSettings(formData);

      // Refresh secrets status after successful save
      try {
        const status = await getSecretsStatus();
        setSecretsStatus(status);
      } catch (error) {
        console.error('Failed to refresh secrets status:', error);
      }
    } catch (err) {
      // Error is handled by the context - additional safety check
      if (err && typeof err === 'object' && 'message' in err && typeof (err as any).message === 'string') {
        setErrorMessage((err as any).message);
      } else if (typeof err === 'string') {
        setErrorMessage(err);
      } else {
        setErrorMessage('An error occurred while saving settings');
      }
      console.error('Save settings error:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = async () => {
    if (window.confirm('Are you sure you want to reset all settings to defaults? This action cannot be undone.')) {
      try {
        await resetSettings();
        setSuccessMessage('Settings reset to defaults successfully!');
      } catch (err) {
        // Error is handled by the context
      }
    }
  };

  const handleTestConnection = async (service: string) => {
    if (!formData) return;

    setConnectionStatus(prev => ({
      ...prev,
      [service]: { testing: true, tested: false },
    }));

    try {
      let result: ConnectionTestResult;

      if (service === 'jenkins') {
        result = await testJenkinsConnection({
          url: formData.jenkins.url || '',
          username: formData.jenkins.username || '',
          api_token: formData.jenkins.api_token || '',
          verify_ssl: formData.jenkins.verify_ssl
        });
      } else if (service === 'github') {
        result = await testGitHubConnection({
          token: formData.github.token || ''
        });
      } else if (service === 'ai') {
        result = await testAIConnection({
          gemini_api_key: formData.ai.gemini_api_key || '',
          gemini_model: formData.ai.gemini_model,
          temperature: formData.ai.temperature,
          max_tokens: formData.ai.max_tokens
        });
      } else {
        throw new Error(`Unknown service: ${service}`);
      }

      setConnectionStatus(prev => ({
        ...prev,
        [service]: { testing: false, tested: true, result },
      }));
    } catch (err) {
      setConnectionStatus(prev => ({
        ...prev,
        [service]: {
          testing: false,
          tested: true,
          result: {
            service,
            success: false,
            message: 'Connection test failed',
            error_details: err instanceof Error ? err.message : 'Unknown error'
          }
        },
      }));
    }
  };

  // Test functions for individual services with form values
  const testJenkinsConnection = async (jenkinsConfig: TestableFormData['jenkins']): Promise<ConnectionTestResult> => {
    if (!jenkinsConfig.url) {
      return {
        service: 'jenkins',
        success: false,
        message: 'Jenkins URL is required',
        error_details: 'Please enter a Jenkins URL'
      };
    }

    try {
      const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/settings/test-connection-with-config`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          service: 'jenkins',
          config: jenkinsConfig
        }),
      });

      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || `HTTP ${response.status}`);
      }

      return result;
    } catch (error) {
      return {
        service: 'jenkins',
        success: false,
        message: 'Connection test failed',
        error_details: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  };

  const testGitHubConnection = async (githubConfig: TestableFormData['github']): Promise<ConnectionTestResult> => {
    // If no token in form, use existing settings
    if (!githubConfig.token && !secretsStatus?.github?.token) {
      return {
        service: 'github',
        success: false,
        message: 'GitHub token is required',
        error_details: 'Please enter a GitHub personal access token or configure it first'
      };
    }

    try {
      if (githubConfig.token) {
        // Test with new token from form
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/settings/test-connection-with-config`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            service: 'github',
            config: githubConfig
          }),
        });

        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || `HTTP ${response.status}`);
        }

        return result;
      } else {
        // Test with existing configured settings
        const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/settings/test-connection?service=github`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const result = await response.json();
        if (!response.ok) {
          throw new Error(result.detail || `HTTP ${response.status}`);
        }

        return result;
      }
    } catch (error) {
      return {
        service: 'github',
        success: false,
        message: 'Connection test failed',
        error_details: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  };

  const testAIConnection = async (aiConfig: TestableFormData['ai']): Promise<ConnectionTestResult> => {
    // If no API key in form, use existing settings
    if (!aiConfig.gemini_api_key && !secretsStatus?.ai?.gemini_api_key) {
      return {
        service: 'ai',
        success: false,
        message: 'Gemini API key is required',
        error_details: 'Please enter a Google Gemini API key or configure it first'
      };
    }

    try {
      let modelsResult: { success: boolean; models?: any[]; error?: string } = {
        success: false,
        error: 'Not tested'
      };

      if (aiConfig.gemini_api_key) {
        // Test with new API key from form
        modelsResult = await fetchModelsWithApiKey(aiConfig.gemini_api_key);
      } else {
        // Test with existing configured settings (use backend endpoint)
        try {
          const response = await fetch(`${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/v1/settings/test-connection?service=ai`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const result = await response.json();
          if (!response.ok) {
            throw new Error(result.detail || `HTTP ${response.status}`);
          }

          if (result.success) {
            // Connection test passed, but no models without API key
            modelsResult = {
              success: true,
              models: []
            };
          } else {
            return result;
          }
        } catch (error) {
          return {
            service: 'ai',
            success: false,
            message: 'Connection test failed',
            error_details: error instanceof Error ? error.message : 'Unknown error'
          };
        }
      }

      if (modelsResult.success && modelsResult.models) {
        // Update available models on successful test
        setAvailableModels(modelsResult.models);
        setModelsError(null);

        // Update model if current selection is not available
        const modelNames = modelsResult.models.map((model: any) => model.name);
        if (!modelNames.includes(aiConfig.gemini_model) && modelsResult.models.length > 0) {
          setFormData(prev => {
            if (!prev) return null;
            return {
              ...prev,
              ai: {
                ...prev.ai,
                gemini_model: modelsResult.models![0].name,
              },
            };
          });
        }

        return {
          service: 'ai',
          success: true,
          message: 'AI connection successful'
        };
      } else {
        setModelsError(modelsResult.error || 'Failed to fetch models');
        setAvailableModels([]);
        return {
          service: 'ai',
          success: false,
          message: 'AI connection failed',
          error_details: modelsResult.error || 'Failed to validate API key and fetch models'
        };
      }
    } catch (error) {
      setModelsError(error instanceof Error ? error.message : 'Connection test failed');
      setAvailableModels([]);
      return {
        service: 'ai',
        success: false,
        message: 'AI connection test failed',
        error_details: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  };

  const handleBackup = async () => {
    try {
      await backupSettings();
      setSuccessMessage('Settings backup downloaded successfully!');
    } catch (err) {
      console.error('Backup failed:', err);
      setErrorMessage(err instanceof Error ? err.message : 'Failed to backup settings');
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.name.endsWith('.json')) {
        setErrorMessage('Please select a JSON backup file');
        return;
      }

      setRestoreFile(file);
      setErrorMessage(null);
    }
  };

  const handleRestore = async () => {
    if (!restoreFile) {
      setErrorMessage('Please select a backup file to restore');
      return;
    }

    if (!window.confirm('Are you sure you want to restore settings from this backup? This will overwrite your current settings.')) {
      return;
    }

    setIsRestoring(true);
    setErrorMessage(null);

    try {
      await restoreSettings(restoreFile);
      setSuccessMessage('Settings restored successfully!');
      setRestoreFile(null);
      // Reset the file input
      const fileInput = document.getElementById('restore-file-input') as HTMLInputElement;
      if (fileInput) {
        fileInput.value = '';
      }
    } catch (err) {
      console.error('Restore failed:', err);
      setErrorMessage(err instanceof Error ? err.message : 'Failed to restore settings');
    } finally {
      setIsRestoring(false);
    }
  };

  const renderConnectionStatus = (service: string) => {
    const status = connectionStatus[service];
    if (!status) return null;

    if (status.testing) {
      return (
        <div className="flex items-center mt-2 text-sm text-blue-600 dark:text-blue-400">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400 mr-2"></div>
          Testing connection...
        </div>
      );
    }

    if (status.result) {
      return (
        <div className={`mt-2 p-2 rounded text-sm ${
          status.result.success
            ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
            : 'bg-red-100 dark:bg-red-900 text-red-800 dark:text-red-200'
        }`}>
          <div className="flex items-center">
            <div className="font-medium flex-1">{status.result.message}</div>
            {status.result.success && (
              <div className="ml-2">
                <svg className="w-4 h-4 text-green-600 dark:text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
          {status.result.error_details && (
            <div className="text-xs opacity-75 mt-1">
              {status.result.error_details}
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  if (loading && !formData) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 dark:border-primary-400"></div>
        <span className="ml-3 text-gray-600 dark:text-gray-400">Loading settings...</span>
      </div>
    );
  }

  if (!formData) {
    return (
      <div className="p-8 text-center">
        <div className="text-red-600 dark:text-red-400">Failed to load settings</div>
        {error && <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">{error}</div>}
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                Configure your TestInsight AI application settings
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3">
              {/* Backup/Restore Section */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={handleBackup}
                  className="px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-200 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                >
                  📥 Backup Settings
                </button>

                <div className="flex items-center gap-2">
                  <input
                    id="restore-file-input"
                    type="file"
                    accept=".json"
                    onChange={handleFileUpload}
                    className="hidden"
                  />
                  <label
                    htmlFor="restore-file-input"
                    className="px-3 py-2 text-sm font-medium text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900 border border-blue-300 dark:border-blue-700 rounded-md hover:bg-blue-200 dark:hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer"
                  >
                    📤 Restore Settings
                  </label>

                  {restoreFile && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-gray-600 dark:text-gray-400 max-w-32 truncate">
                        {restoreFile.name}
                      </span>
                      <button
                        type="button"
                        onClick={handleRestore}
                        disabled={isRestoring}
                        className="px-3 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {isRestoring ? (
                          <div className="flex items-center">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                            Restoring...
                          </div>
                        ) : (
                          'Restore'
                        )}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Reset Button */}
              <button
                type="button"
                onClick={handleReset}
                className="px-3 py-2 text-sm font-medium text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 rounded-md hover:bg-red-200 dark:hover:bg-red-800 focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent"
              >
                🔄 Reset to Defaults
              </button>
            </div>
          </div>
        </div>

        {/* Messages */}

        {successMessage && (
          <div className="mx-6 mt-4 p-4 bg-green-100 dark:bg-green-900 border border-green-300 dark:border-green-700 rounded-md">
            <div className="text-green-800 dark:text-green-200">{successMessage}</div>
          </div>
        )}

        {(error || errorMessage) && (
          <div className="mx-6 mt-4 p-4 bg-red-100 dark:bg-red-900 border border-red-300 dark:border-red-700 rounded-md">
            <div className="text-red-800 dark:text-red-200">
              {getErrorMessage(error || errorMessage)}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {/* Tabs */}
          <div className="border-b border-gray-200 dark:border-gray-700">
            <nav className="flex space-x-8 px-6">
              {[
                { id: 'jenkins', label: 'Jenkins', icon: '🔧' },
                { id: 'github', label: 'GitHub', icon: '🐙' },
                { id: 'ai', label: 'AI', icon: '🤖' },
                { id: 'preferences', label: 'Preferences', icon: '⚙️' },
              ].map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => handleTabChange(tab.id as any)}
                  className={`py-3 px-1 border-b-2 font-medium text-sm ${
                    activeTab === tab.id
                      ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                      : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  <span className="mr-2">{tab.icon}</span>
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {/* Jenkins Tab */}
            {activeTab === 'jenkins' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    Jenkins Configuration
                  </h3>
                  <div className="grid grid-cols-1 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Jenkins URL
                      </label>
                      <input
                        type="url"
                        value={formData.jenkins.url || ''}
                        onChange={(e) => handleInputChange('jenkins', 'url', e.target.value)}
                        placeholder="https://jenkins.example.com"
                        className={`mt-1 block w-full rounded-md border ${
                          formErrors['jenkins.url']
                            ? 'border-red-300 dark:border-red-600'
                            : 'border-gray-300 dark:border-gray-600'
                        } px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500`}
                      />
                      {formErrors['jenkins.url'] && (
                        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                          {formErrors['jenkins.url']}
                        </p>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Username
                        </label>
                        <input
                          type="text"
                          value={formData.jenkins.username || ''}
                          onChange={(e) => handleInputChange('jenkins', 'username', e.target.value)}
                          className={`mt-1 block w-full rounded-md border ${
                            formErrors['jenkins.username']
                              ? 'border-red-300 dark:border-red-600'
                              : 'border-gray-300 dark:border-gray-600'
                          } px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500`}
                        />
                        {formErrors['jenkins.username'] && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {formErrors['jenkins.username']}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          API Token
                        </label>
                        <input
                          type="password"
                          value={formData.jenkins.api_token || ''}
                          onChange={(e) => handleInputChange('jenkins', 'api_token', e.target.value)}
                          placeholder={
                            secretsStatus?.jenkins?.api_token
                              ? "Click here to change API token"
                              : "Enter your Jenkins API token"
                          }
                          className={`mt-1 block w-full rounded-md border ${
                            formErrors['jenkins.api_token']
                              ? 'border-red-300 dark:border-red-600'
                              : 'border-gray-300 dark:border-gray-600'
                          } px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500`}
                        />
                        {formErrors['jenkins.api_token'] && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {formErrors['jenkins.api_token']}
                          </p>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center">
                      <input
                        type="checkbox"
                        id="verify_ssl"
                        checked={formData.jenkins.verify_ssl}
                        onChange={(e) => handleInputChange('jenkins', 'verify_ssl', e.target.checked)}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 dark:border-gray-600 rounded"
                      />
                      <label htmlFor="verify_ssl" className="ml-2 block text-sm text-gray-700 dark:text-gray-300">
                        Verify SSL certificates
                      </label>
                    </div>

                    <div>
                      <button
                        type="button"
                        onClick={() => handleTestConnection('jenkins')}
                        disabled={!formData.jenkins.url || !formData.jenkins.username || (!formData.jenkins.api_token && !secretsStatus?.jenkins?.api_token) || connectionStatus.jenkins?.testing}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {connectionStatus.jenkins?.testing ? 'Testing...' : 'Test Jenkins Connection'}
                      </button>
                      {renderConnectionStatus('jenkins')}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* GitHub Tab */}
            {activeTab === 'github' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    GitHub Configuration
                  </h3>
                  <div className="grid grid-cols-1 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Personal Access Token
                      </label>
                      <input
                        type="password"
                        value={formData.github.token || ''}
                        onChange={(e) => handleInputChange('github', 'token', e.target.value)}
                        placeholder={
                          secretsStatus?.github?.token
                            ? "Click here to change GitHub token"
                            : "ghp_xxxxxxxxxxxxxxxxxxxx"
                        }
                        className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500"
                      />
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Required for private repositories and enhanced API limits
                      </p>
                    </div>


                    <div>
                      <button
                        type="button"
                        onClick={() => handleTestConnection('github')}
                        disabled={(!formData.github.token && !secretsStatus?.github?.token) || connectionStatus.github?.testing}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {connectionStatus.github?.testing ? 'Testing...' : 'Test GitHub API Token'}
                      </button>
                      {renderConnectionStatus('github')}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* AI Tab */}
            {activeTab === 'ai' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    AI Configuration
                  </h3>
                  <div className="grid grid-cols-1 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Google Gemini API Key
                      </label>
                      <div className="relative">
                        <input
                          type="password"
                          value={formData.ai.gemini_api_key || ''}
                          onChange={(e) => handleInputChange('ai', 'gemini_api_key', e.target.value)}
                          placeholder={
                            secretsStatus?.ai?.gemini_api_key
                              ? "Click here to change API key"
                              : "AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                          }
                          className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500"
                        />
                        {apiKeyValidating && (
                          <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 dark:border-primary-400"></div>
                          </div>
                        )}
                      </div>
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        Get your API key from Google AI Studio
                      </p>
                      {modelsError && (
                        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                          {modelsError}
                        </p>
                      )}
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Gemini Model
                      </label>
                      <div className="flex gap-2">
                        <div className="relative flex-1">
                          <select
                            value={formData.ai.gemini_model}
                            onChange={(e) => handleInputChange('ai', 'gemini_model', e.target.value)}
                            disabled={!availableModels.length || modelsLoading}
                            className={`mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500 ${
                              (!availableModels.length || modelsLoading) ? 'opacity-50 cursor-not-allowed' : ''
                            }`}
                          >
                            {availableModels.length === 0 && !modelsLoading && (
                              <option value="">No models available</option>
                            )}
                            {modelsLoading && (
                              <option value="gemini-pro">Loading models...</option>
                            )}
                            {availableModels.map((model) => (
                              <option key={model.name} value={model.name}>
                                {model.display_name || model.name}
                              </option>
                            ))}
                          </select>
                          {modelsLoading && (
                            <div className="absolute right-8 top-1/2 transform -translate-y-1/2">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary-600 dark:border-primary-400"></div>
                            </div>
                          )}
                        </div>
                        <button
                          type="button"
                          onClick={handleRefreshModels}
                          disabled={!secretsStatus?.ai?.gemini_api_key || modelsLoading}
                          className="mt-1 px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                          title={!secretsStatus?.ai?.gemini_api_key ? 'Configure and save AI settings first' : 'Refresh available models'}
                        >
                          {modelsLoading ? 'Loading...' : 'Refresh Models'}
                        </button>
                      </div>
                      <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                        {availableModels.length > 0
                          ? `${availableModels.length} models available`
                          : 'Models will be loaded when you test the AI connection'
                        }
                      </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Temperature ({formData.ai.temperature})
                        </label>
                        <input
                          type="range"
                          min="0"
                          max="2"
                          step="0.1"
                          value={formData.ai.temperature}
                          onChange={(e) => handleInputChange('ai', 'temperature', parseFloat(e.target.value))}
                          className="mt-1 block w-full"
                        />
                        <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                          <span>Conservative</span>
                          <span>Creative</span>
                        </div>
                        {formErrors['ai.temperature'] && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {formErrors['ai.temperature']}
                          </p>
                        )}
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                          Max Tokens
                        </label>
                        <input
                          type="number"
                          min="1"
                          max="32768"
                          value={formData.ai.max_tokens}
                          onChange={(e) => handleInputChange('ai', 'max_tokens', parseInt(e.target.value))}
                          className={`mt-1 block w-full rounded-md border ${
                            formErrors['ai.max_tokens']
                              ? 'border-red-300 dark:border-red-600'
                              : 'border-gray-300 dark:border-gray-600'
                          } px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500`}
                        />
                        {formErrors['ai.max_tokens'] && (
                          <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {formErrors['ai.max_tokens']}
                          </p>
                        )}
                      </div>
                    </div>

                    <div>
                      <button
                        type="button"
                        onClick={() => handleTestConnection('ai')}
                        disabled={(!formData.ai.gemini_api_key && !secretsStatus?.ai?.gemini_api_key) || connectionStatus.ai?.testing}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        {connectionStatus.ai?.testing ? 'Testing...' : 'Test Connection'}
                      </button>
                      {renderConnectionStatus('ai')}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Preferences Tab */}
            {activeTab === 'preferences' && (
              <div className="space-y-6">
                <div>
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                    User Preferences
                  </h3>
                  <div className="grid grid-cols-1 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                        Theme
                      </label>
                      <select
                        value={formData.preferences.theme}
                        onChange={(e) => handleInputChange('preferences', 'theme', e.target.value)}
                        className="mt-1 block w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:border-primary-500 focus:ring-primary-500"
                      >
                        <option value="light">Light</option>
                        <option value="dark">Dark</option>
                        <option value="system">System</option>
                      </select>
                    </div>


                  </div>
                </div>
              </div>
            )}

            {/* Submit Button */}
            <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-end">
                <button
                  type="submit"
                  disabled={isSubmitting || !canSave}
                  className="px-6 py-3 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <div className="flex items-center">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Saving...
                    </div>
                  ) : (
                    'Save Settings'
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Settings;
