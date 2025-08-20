import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';

// Types for settings data
export interface JenkinsSettings {
  url?: string;
  username?: string;
  api_token?: string;
  verify_ssl: boolean;
}

export interface GitHubSettings {
  token?: string;
}

export interface AISettings {
  gemini_api_key?: string;
  model: string; // Changed to string to support dynamic models
  temperature: number;
  max_tokens: number;
}

export interface AppSettings {
  jenkins: JenkinsSettings;
  github: GitHubSettings;
  ai: AISettings;
  last_updated?: string;
}

export interface SettingsUpdate {
  jenkins?: Partial<JenkinsSettings>;
  github?: Partial<GitHubSettings>;
  ai?: Partial<AISettings>;
}

export interface ConnectionTestResult {
  service: string;
  success: boolean;
  message: string;
  error_details?: string;
}

interface SettingsContextType {
  settings: AppSettings | null;
  loading: boolean;
  error: string | null;
  fetchSettings: () => Promise<void>;
  updateSettings: (update: SettingsUpdate) => Promise<void>;
  resetSettings: () => Promise<void>;
  validateSettings: () => Promise<Record<string, string[]>>;
  testConnection: (service: string) => Promise<ConnectionTestResult>;
  backupSettings: () => Promise<void>;
  restoreSettings: (file: File) => Promise<void>;
}

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export const useSettings = () => {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
};

interface SettingsProviderProps {
  children: React.ReactNode;
}

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export const SettingsProvider: React.FC<SettingsProviderProps> = ({ children }) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Helper function to handle API errors
  const handleApiError = (error: any): string => {
    // Handle fetch API errors
    if (error.response?.data?.detail) {
      return Array.isArray(error.response.data.detail)
        ? error.response.data.detail.map((e: any) => e.msg || e).join(', ')
        : error.response.data.detail;
    }

    // Handle Error objects
    if (error instanceof Error) {
      return error.message;
    }

    // Handle string errors
    if (typeof error === 'string') {
      return error;
    }

    // Handle objects with message property
    if (error && typeof error === 'object' && error.message) {
      return error.message;
    }

    // Fallback for any other type
    return 'An unexpected error occurred';
  };

  // Fetch current settings
  const fetchSettings = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSettings(data);
    } catch (err: any) {
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Update settings
  const updateSettings = useCallback(async (update: SettingsUpdate): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(update),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSettings(data);
    } catch (err: any) {
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      console.error('Failed to update settings:', err);
      throw err; // Re-throw to allow form handling
    } finally {
      setLoading(false);
    }
  }, []);

  // Reset settings to defaults
  const resetSettings = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings/reset`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSettings(data);
    } catch (err: any) {
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      console.error('Failed to reset settings:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Validate current settings
  const validateSettings = useCallback(async (): Promise<Record<string, string[]>> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings/validate`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (err: any) {
      console.error('Failed to validate settings:', err);
      throw err;
    }
  }, []);

  // Test connection to a service
  const testConnection = useCallback(async (service: string): Promise<ConnectionTestResult> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings/test-connection?service=${encodeURIComponent(service)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (err: any) {
      console.error(`Failed to test ${service} connection:`, err);
      return {
        service,
        success: false,
        message: `Connection test failed: ${handleApiError(err)}`,
        error_details: err.message
      };
    }
  }, []);

  // Backup settings - trigger file download
  const backupSettings = useCallback(async (): Promise<void> => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/settings/backup`, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      // Get the filename from the Content-Disposition header
      const contentDisposition = response.headers.get('content-disposition');
      let filename = 'testinsight_settings_backup.json';

      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }

      // Create blob and trigger download
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      console.error('Failed to backup settings:', err);
      throw err;
    }
  }, []);

  // Restore settings from uploaded file
  const restoreSettings = useCallback(async (file: File): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      // Create form data for file upload
      const formData = new FormData();
      formData.append('backup_file', file);

      const response = await fetch(`${API_BASE_URL}/api/v1/settings/restore`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setSettings(data);
    } catch (err: any) {
      const errorMessage = handleApiError(err);
      setError(errorMessage);
      console.error('Failed to restore settings:', err);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Load settings on component mount
  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const value: SettingsContextType = {
    settings,
    loading,
    error,
    fetchSettings,
    updateSettings,
    resetSettings,
    validateSettings,
    testConnection,
    backupSettings,
    restoreSettings,
  };

  return (
    <SettingsContext.Provider value={value}>
      {children}
    </SettingsContext.Provider>
  );
};

// Default settings for form initialization
export const defaultSettings: AppSettings = {
  jenkins: {
    url: '',
    username: '',
    api_token: '',
    verify_ssl: true,
  },
  github: {
    token: '',
  },
  ai: {
    gemini_api_key: '',
    model: '',
    temperature: 0.7,
    max_tokens: 4096,
  },
};
