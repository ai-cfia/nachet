import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import {
  InteractionRequiredAuthError,
  BrowserAuthError,
} from "@azure/msal-browser";

// Track if we're currently in a redirect flow to prevent loops
let isRedirecting = false;
let requestInterceptorId: number | null = null;
let responseInterceptorId: number | null = null;

interface NachetAuthRequestConfig extends InternalAxiosRequestConfig {
  nachetAuthRequired?: boolean;
}

function assertAccessToken(accessToken: string): string {
  if (!accessToken) {
    throw new Error("Access token is null or empty");
  }

  return accessToken;
}

function requestRequiresNachetAuth(
  request?: InternalAxiosRequestConfig,
): request is NachetAuthRequestConfig {
  return Boolean(
    (request as NachetAuthRequestConfig | undefined)?.nachetAuthRequired,
  );
}

/**
 * Checks if an error requires user interaction (redirect to login)
 * @param error - The error to check
 * @returns true if the error requires redirect authentication
 */
export function shouldTriggerRedirect(error: unknown): boolean {
  return (
    error instanceof InteractionRequiredAuthError ||
    (error instanceof BrowserAuthError &&
      error.errorCode === "monitor_window_timeout")
  );
}

/**
 * Reset the redirect flag (called after successful redirect)
 */
export function resetRedirectFlag(): void {
  isRedirecting = false;
}

export function clearAxiosInterceptors(): void {
  if (requestInterceptorId !== null) {
    axios.interceptors.request.eject(requestInterceptorId);
    requestInterceptorId = null;
  }

  if (responseInterceptorId !== null) {
    axios.interceptors.response.eject(responseInterceptorId);
    responseInterceptorId = null;
  }

  resetRedirectFlag();
}

/**
 * Configure axios interceptor to handle 401 Unauthorized errors and retry once
 * with an access token from the active auth provider.
 *
 * @param getAccessToken - Provider-neutral token getter
 */
export function setupAxiosInterceptor(
  getAccessToken: () => Promise<string>,
): void {
  clearAxiosInterceptors();

  requestInterceptorId = axios.interceptors.request.use(
    async (config: NachetAuthRequestConfig) => {
      if (!config.nachetAuthRequired || config.headers?.Authorization) {
        return config;
      }

      config.headers.Authorization = `Bearer ${assertAccessToken(
        await getAccessToken(),
      )}`;
      return config;
    },
    (error) => Promise.reject(error),
  );

  // Response interceptor to handle 401 errors
  responseInterceptorId = axios.interceptors.response.use(
    (response) => response, // Pass through successful responses
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      // Check if this is a 401 error and we haven't already retried
      if (
        error.response?.status === 401 &&
        requestRequiresNachetAuth(originalRequest) &&
        !originalRequest?._retry
      ) {
        originalRequest._retry = true;

        // Prevent redirect loop
        if (isRedirecting) {
          return Promise.reject(error);
        }

        try {
          const accessToken = assertAccessToken(await getAccessToken());

          // Update the authorization header with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${accessToken}`;
          }

          // Retry the original request with new token
          return axios(originalRequest);
        } catch (tokenError) {
          // If silent token acquisition fails, check if redirect is needed
          if (shouldTriggerRedirect(tokenError)) {
            // Set redirect flag to prevent loops
            isRedirecting = true;

            return Promise.reject(tokenError);
          }

          // For other errors, just reject
          return Promise.reject(tokenError);
        }
      }

      // For non-401 errors or already retried requests, reject as normal
      return Promise.reject(error);
    },
  );
}
