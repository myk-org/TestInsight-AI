/**
 * TestInsight AI Frontend API Service
 *
 * This module provides a comprehensive API client for the TestInsight AI backend.
 * All endpoints are properly aligned with the backend FastAPI application.
 *
 * RECENT UPDATES:
 * - ✅ Fixed health check endpoint: /health → /status for comprehensive service status
 * - ✅ Added complete Settings API: getSettings, updateSettings, resetSettings, validateSettings,
 *      testConnection, testConnectionWithConfig, backupSettings, restoreSettings
 * - ✅ Added Git Repository API: cloneRepository, getFileContent for repository operations
 * - ✅ Enhanced error handling with specific HTTP status code messaging
 * - ✅ TypeScript interfaces properly match backend Pydantic schemas
 * - ✅ Proper FormData usage for file uploads and multipart endpoints
 * - ✅ Comprehensive error messages with user guidance for common issues
 *
 * ENDPOINTS MAPPING:
 * Frontend → Backend
 * - /analyze → POST /api/v1/analyze (FormData: text, custom_context)
 * - /jenkins/jobs → GET /api/v1/jenkins/jobs
 * - /jenkins/{job}/{build}/console → GET /api/v1/jenkins/{job}/{build}/console
 * - /jenkins/{job}/builds → GET /api/v1/jenkins/{job}/builds
 * - /ai/models → POST /api/v1/ai/models (JSON: api_key)
 * - /ai/models/validate-key → POST /api/v1/ai/models/validate-key (JSON: api_key)
 * - /settings → GET/PUT /api/v1/settings
 * - /settings/reset → POST /api/v1/settings/reset
 * - /settings/validate → GET /api/v1/settings/validate
 * - /settings/test-connection → POST /api/v1/settings/test-connection (Query: service)
 * - /settings/test-connection-with-config → POST /api/v1/settings/test-connection-with-config (JSON)
 * - /settings/backup → GET /api/v1/settings/backup (Download)
 * - /settings/restore → POST /api/v1/settings/restore (FormData: backup_file)
 * - /git/clone → POST /api/v1/git/clone (FormData: repo_url, branch?, commit?, github_token?)
 * - /git/file-content → POST /api/v1/git/file-content (FormData: file_path, cloned_path)
 * - /status → GET /api/v1/status (Comprehensive service status)
 */

import axios from "axios";
import { AnalysisResult, AIInsight } from "../App";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000";

const api = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 300000, // 5 minutes timeout for analysis
});

export interface JenkinsConfig {
  url: string;
  username: string;
  apiToken: string;
  jobName: string;
  buildNumber: string;
}

/**
 * Analyze XML files (JUnit, TestNG, etc.)
 */
export const analyzeXMLFiles = async (
  files: File[],
  repositoryConfig?: {
    url: string;
    branch?: string;
    commit?: string;
    includeContext?: boolean;
  }
): Promise<AnalysisResult> => {
  try {
    // Read all files and combine their content
    const fileContents = await Promise.all(
      files.map(async (file) => {
        const text = await file.text();
        return `--- File: ${file.name} ---\n${text}\n`;
      }),
    );

    const combinedText = fileContents.join("\n");
    const customContext = repositoryConfig?.url
      ? `Repository: ${repositoryConfig.url}\nAnalyzing XML test results files: ${files.map((f) => f.name).join(", ")}`
      : `Analyzing XML test results files: ${files.map((f) => f.name).join(", ")}`;

    return await analyzeText(combinedText, customContext, repositoryConfig);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("An unexpected error occurred while analyzing XML files");
  }
};

/**
 * Analyze text logs (console output, etc.)
 */
export const analyzeTextLog = async (
  logText: string,
  logType: "console" | "junit" | "testng" | "pytest" | "other",
  repositoryConfig?: {
    url: string;
    branch?: string;
    commit?: string;
    includeContext?: boolean;
  }
): Promise<AnalysisResult> => {
  try {
    const customContext = repositoryConfig?.url
      ? `Repository: ${repositoryConfig.url}\nLog type: ${logType}`
      : `Log type: ${logType}`;
    return await analyzeText(logText, customContext, repositoryConfig);
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("An unexpected error occurred while analyzing log text");
  }
};



/**
 * Analyze text content (replaces analyzeJenkinsBuild)
 */
export const analyzeText = async (
  text: string,
  customContext?: string,
  repositoryConfig?: {
    url: string;
    branch?: string;
    commit?: string;
    includeContext?: boolean;
  }
): Promise<AnalysisResult> => {
  const formData = new FormData();
  formData.append("text", text);

  if (customContext && customContext.trim()) {
    formData.append("custom_context", customContext.trim());
  }

  // Add repository context integration
  if (repositoryConfig?.url) {
    formData.append("repository_url", repositoryConfig.url);
    if (repositoryConfig.branch) {
      formData.append("repository_branch", repositoryConfig.branch);
    }
    if (repositoryConfig.commit) {
      formData.append("repository_commit", repositoryConfig.commit);
    }
    if (repositoryConfig.includeContext) {
      formData.append("include_repository_context", "true");
    }
  }

  try {
    const response = await api.post("/analyze", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      let errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to analyze text";

      // Provide specific guidance for AI configuration issues
      if (
        errorMessage.includes("AI analyzer not configured") ||
        errorMessage.includes("503")
      ) {
        errorMessage =
          "AI service temporarily unavailable. Please check your AI configuration in Settings (Gemini API key and model) and try again.";
      }

      throw new Error(errorMessage);
    }
    throw new Error("An unexpected error occurred while analyzing text");
  }
};

/**
 * Get Jenkins job builds
 */
export const getJenkinsJobBuilds = async (
  jobName: string,
  limit: number = 1,
): Promise<any[]> => {
  try {
    const response = await api.get(`/jenkins/${jobName}/builds?limit=${limit}`);
    return response.data.builds || [];
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to get Jenkins job builds";
      throw new Error(errorMessage);
    }
    throw new Error(
      "An unexpected error occurred while fetching Jenkins job builds",
    );
  }
};

/**
 * Analyze Jenkins build (now uses the correct flow)
 */
export const analyzeJenkinsBuild = async (
  config: JenkinsConfig,
  repositoryConfig?: {
    url: string;
    branch?: string;
    commit?: string;
    includeContext?: boolean;
  }
): Promise<AnalysisResult> => {
  try {
    // Use the dedicated Jenkins analysis endpoint
    const formData = new FormData();
    formData.append("job_name", config.jobName);
    formData.append("build_number", config.buildNumber || "");

    if (repositoryConfig?.url) {
      formData.append("repo_url", repositoryConfig.url);
      if (repositoryConfig.branch) {
        formData.append("repository_branch", repositoryConfig.branch);
      }
      if (repositoryConfig.commit) {
        formData.append("repository_commit", repositoryConfig.commit);
      }
      if (repositoryConfig.includeContext) {
        formData.append("include_repository_context", "true");
      }
    }

    const response = await api.post("/analyze-jenkins", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(
      "An unexpected error occurred while analyzing Jenkins build",
    );
  }
};

/**
 * Health check endpoint (now uses /status for comprehensive service status)
 */
export const checkHealth = async (): Promise<{
  status: string;
  version?: string;
}> => {
  try {
    const response = await api.get("/status");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail || error.message || "Health check failed",
      );
    }
    throw new Error("Health check failed");
  }
};

/**
 * Get comprehensive service status
 */
export const getServiceStatus = async (): Promise<any> => {
  try {
    const response = await api.get("/status");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to get service status",
      );
    }
    throw new Error("Failed to get service status");
  }
};

/**
 * Get API documentation/info
 */
export const getApiInfo = async (): Promise<any> => {
  try {
    const response = await api.get("/");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to get API info",
      );
    }
    throw new Error("Failed to get API info");
  }
};

/**
 * Validate Gemini API key
 */
export const validateGeminiApiKey = async (
  apiKey: string,
): Promise<{ valid: boolean; message?: string }> => {
  try {
    const response = await api.post(
      `/ai/models/validate-key?api_key=${encodeURIComponent(apiKey)}`,
      {},
      {
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to validate API key";
      return { valid: false, message: errorMessage };
    }
    return {
      valid: false,
      message: "An unexpected error occurred while validating API key",
    };
  }
};

/**
 * Fetch available Gemini models using provided API key
 */
export const fetchGeminiModels = async (apiKey: string): Promise<any[]> => {
  try {
    const response = await api.post(
      `/ai/models?api_key=${encodeURIComponent(apiKey)}`,
      {},
      {
        headers: {
          "Content-Type": "application/json",
        },
      },
    );

    return response.data.models || [];
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to fetch models";
      throw new Error(errorMessage);
    }
    throw new Error("An unexpected error occurred while fetching models");
  }
};

/**
 * Fetch Jenkins jobs list
 */
export const fetchJenkinsJobs = async (): Promise<string[]> => {
  try {
    const response = await api.get("/jenkins/jobs");
    return response.data.jobs || [];
  } catch (error) {
    if (axios.isAxiosError(error)) {
      let errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to fetch Jenkins jobs";

      // Provide specific guidance for common Jenkins authentication issues
      if (
        errorMessage.includes("401") ||
        errorMessage.includes("Unauthorized")
      ) {
        errorMessage =
          "Jenkins authentication failed. Please verify your username and API token/password in Settings.";
      } else if (errorMessage.includes("crumbIssuer")) {
        errorMessage =
          "Jenkins CSRF protection is enabled. Please check your Jenkins API token permissions or contact your Jenkins administrator.";
      }

      throw new Error(errorMessage);
    }
    throw new Error("An unexpected error occurred while fetching Jenkins jobs");
  }
};

// ================== SETTINGS API FUNCTIONS ==================

/**
 * TypeScript interfaces for settings
 */
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
  model: string;
  temperature: number;
  max_tokens: number;
}

export interface UserPreferences {
  theme: string;
  language: string;
  auto_refresh: boolean;
  results_per_page: number;
}

export interface AppSettings {
  jenkins: JenkinsSettings;
  github: GitHubSettings;
  ai: AISettings;
  preferences: UserPreferences;
  last_updated?: string;
}

export interface SettingsUpdate {
  jenkins?: JenkinsSettings;
  github?: GitHubSettings;
  ai?: AISettings;
  preferences?: UserPreferences;
}

export interface ConnectionTestResult {
  service: string;
  success: boolean;
  message: string;
  error_details?: string;
}

export interface TestConnectionWithConfigRequest {
  service: string;
  config: Record<string, any>;
}

/**
 * Get current application settings
 */
export const getSettings = async (): Promise<AppSettings> => {
  try {
    const response = await api.get("/settings");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to get settings",
      );
    }
    throw new Error("Failed to get settings");
  }
};

/**
 * Update application settings
 */
export const updateSettings = async (
  settingsUpdate: SettingsUpdate,
): Promise<AppSettings> => {
  try {
    const response = await api.put("/settings", settingsUpdate, {
      headers: {
        "Content-Type": "application/json",
      },
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to update settings",
      );
    }
    throw new Error("Failed to update settings");
  }
};

/**
 * Reset settings to defaults
 */
export const resetSettings = async (): Promise<AppSettings> => {
  try {
    const response = await api.post("/settings/reset");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to reset settings",
      );
    }
    throw new Error("Failed to reset settings");
  }
};

/**
 * Validate current settings
 */
export const validateSettings = async (): Promise<Record<string, string[]>> => {
  try {
    const response = await api.get("/settings/validate");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to validate settings",
      );
    }
    throw new Error("Failed to validate settings");
  }
};

/**
 * Get status of configured secrets
 */
export const getSecretsStatus = async (): Promise<Record<string, Record<string, boolean>>> => {
  try {
    const response = await api.get("/settings/secrets-status");
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to get secrets status",
      );
    }
    throw new Error("Failed to get secrets status");
  }
};

/**
 * Test connection to a configured service
 */
export const testConnection = async (
  service: string,
): Promise<ConnectionTestResult> => {
  try {
    // Send as query parameter since FastAPI expects it as a simple parameter
    const response = await api.post(
      `/settings/test-connection?service=${encodeURIComponent(service)}`,
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data;
      if (
        errorData &&
        typeof errorData === "object" &&
        "service" in errorData
      ) {
        return errorData as ConnectionTestResult;
      }
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to test connection",
      );
    }
    throw new Error("Failed to test connection");
  }
};

/**
 * Test connection with custom configuration parameters
 */
export const testConnectionWithConfig = async (
  request: TestConnectionWithConfigRequest,
): Promise<ConnectionTestResult> => {
  try {
    const response = await api.post(
      "/settings/test-connection-with-config",
      request,
      {
        headers: {
          "Content-Type": "application/json",
        },
      },
    );
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const errorData = error.response?.data;
      if (
        errorData &&
        typeof errorData === "object" &&
        "service" in errorData
      ) {
        return errorData as ConnectionTestResult;
      }
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to test connection with config",
      );
    }
    throw new Error("Failed to test connection with config");
  }
};

/**
 * Backup current settings as downloadable JSON file
 */
export const backupSettings = async (): Promise<void> => {
  try {
    const response = await api.get("/settings/backup", {
      responseType: "blob", // Important for file downloads
    });

    // Create a blob from the response
    const blob = new Blob([response.data], { type: "application/json" });

    // Create download link
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;

    // Extract filename from response headers or use default
    const contentDisposition = response.headers["content-disposition"];
    let filename = "testinsight_settings_backup.json";
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename=(.+)/);
      if (filenameMatch) {
        filename = filenameMatch[1].replace(/"/g, "");
      }
    }

    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to backup settings",
      );
    }
    throw new Error("Failed to backup settings");
  }
};

/**
 * Restore settings from uploaded backup file
 */
export const restoreSettings = async (
  backupFile: File,
): Promise<AppSettings> => {
  try {
    const formData = new FormData();
    formData.append("backup_file", backupFile);

    const response = await api.post("/settings/restore", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(
        error.response?.data?.detail ||
          error.message ||
          "Failed to restore settings",
      );
    }
    throw new Error("Failed to restore settings");
  }
};

// ================== GIT REPOSITORY API FUNCTIONS ==================

/**
 * TypeScript interfaces for git operations
 */
export interface CloneRepositoryRequest {
  repo_url: string;
  branch?: string;
  commit?: string;
  github_token?: string;
}

export interface CloneRepositoryResponse {
  success: boolean;
  repository_url: string;
  commit_hash?: string;
  branch?: string;
  cloned_path: string;
}

export interface GetFileContentRequest {
  file_path: string;
  cloned_path: string;
}

export interface GetFileContentResponse {
  file_path: string;
  content: string;
  cloned_path: string;
}

/**
 * Clone a git repository with specific branch or commit
 */
export const cloneRepository = async (
  repoUrl: string,
  branch?: string,
  commit?: string,
  githubToken?: string,
): Promise<CloneRepositoryResponse> => {
  try {
    const formData = new FormData();
    formData.append("repo_url", repoUrl);

    if (branch) {
      formData.append("branch", branch);
    }

    if (commit) {
      formData.append("commit", commit);
    }

    if (githubToken) {
      formData.append("github_token", githubToken);
    }

    const response = await api.post("/git/clone", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      let errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to clone repository";

      // Provide specific guidance for common git errors
      if (
        errorMessage.includes("authentication") ||
        errorMessage.includes("401")
      ) {
        errorMessage =
          "Repository authentication failed. Please check your GitHub token in Settings or ensure the repository is public.";
      } else if (
        errorMessage.includes("not found") ||
        errorMessage.includes("404")
      ) {
        errorMessage =
          "Repository not found. Please verify the repository URL is correct and accessible.";
      } else if (
        errorMessage.includes("branch") &&
        errorMessage.includes("not found")
      ) {
        errorMessage =
          "Specified branch not found. Please verify the branch name is correct.";
      } else if (
        errorMessage.includes("commit") &&
        errorMessage.includes("not found")
      ) {
        errorMessage =
          "Specified commit not found. Please verify the commit hash is correct.";
      }

      throw new Error(errorMessage);
    }
    throw new Error("An unexpected error occurred while cloning repository");
  }
};

/**
 * Get file content from a cloned repository
 */
export const getFileContent = async (
  filePath: string,
  clonedPath: string,
): Promise<GetFileContentResponse> => {
  try {
    const formData = new FormData();
    formData.append("file_path", filePath);
    formData.append("cloned_path", clonedPath);

    const response = await api.post("/git/file-content", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error)) {
      let errorMessage =
        error.response?.data?.detail ||
        error.response?.data?.message ||
        error.message ||
        "Failed to get file content";

      // Provide specific guidance for common file access errors
      if (errorMessage.includes("not found") || errorMessage.includes("404")) {
        if (errorMessage.includes("repository")) {
          errorMessage =
            "Cloned repository path not found. Please clone the repository first.";
        } else {
          errorMessage =
            "File not found in repository. Please verify the file path is correct.";
        }
      } else if (
        errorMessage.includes("permission") ||
        errorMessage.includes("access")
      ) {
        errorMessage =
          "Permission denied accessing file. Please check file permissions.";
      }

      throw new Error(errorMessage);
    }
    throw new Error("An unexpected error occurred while getting file content");
  }
};

// ================== ERROR HANDLING ==================

/**
 * Enhanced error handling to match backend error response formats
 */
export interface ApiError {
  detail?: string;
  message?: string;
  error?: string;
  status?: number;
  code?: string;
}

/**
 * Parse error response and provide user-friendly messages
 */
const parseApiError = (error: any): string => {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const data = error.response?.data as ApiError;

    // Extract error message from various possible fields
    const errorMessage =
      data?.detail || data?.message || data?.error || error.message;

    // Handle specific HTTP status codes with better messaging
    switch (status) {
      case 400:
        return `Bad Request: ${errorMessage || "Invalid request parameters"}`;
      case 401:
        return `Authentication Failed: ${errorMessage || "Please check your credentials in Settings"}`;
      case 403:
        return `Access Denied: ${errorMessage || "You do not have permission to perform this action"}`;
      case 404:
        return `Not Found: ${errorMessage || "The requested resource was not found"}`;
      case 429:
        return `Rate Limited: ${errorMessage || "Too many requests. Please wait and try again"}`;
      case 500:
        return `Server Error: ${errorMessage || "An internal server error occurred"}`;
      case 503:
        return `Service Unavailable: ${errorMessage || "The service is temporarily unavailable"}`;
      default:
        return errorMessage || "An unexpected error occurred";
    }
  }

  // Handle network and timeout errors
  if (error.code === "ECONNABORTED") {
    return "Request timeout - the operation is taking longer than expected. Please try again.";
  }

  if (error.code === "ERR_NETWORK") {
    return `Unable to connect to the TestInsight AI backend. Please check if the backend server is running on ${API_BASE_URL}`;
  }

  return error?.message || "An unexpected error occurred";
};

// Response interceptor for better error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Create a more descriptive error message
    const errorMessage = parseApiError(error);

    // Enhance the error object with parsed information
    const enhancedError = new Error(errorMessage);

    // Preserve original error information for debugging
    if (axios.isAxiosError(error)) {
      (enhancedError as any).status = error.response?.status;
      (enhancedError as any).code = error.code;
      (enhancedError as any).config = error.config;
      (enhancedError as any).response = error.response;
    }

    return Promise.reject(enhancedError);
  },
);

export default api;
