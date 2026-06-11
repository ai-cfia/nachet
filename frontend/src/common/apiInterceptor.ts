import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";
import {
  IPublicClientApplication,
  InteractionRequiredAuthError,
  BrowserAuthError,
} from "@azure/msal-browser";
import { getDevAccessToken, isAzureAuthEnabled } from "./auth";

// Track if we're currently in a redirect flow to prevent loops
let isRedirecting = false;

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

/**
 * Configure axios interceptor to handle 401 Unauthorized errors
 * and trigger redirect authentication when tokens expire
 *
 * @param msalInstance - MSAL instance for authentication
 * @param scopes - Array of scopes to request for tokens
 */
export function setupAxiosInterceptor(
  msalInstance: IPublicClientApplication,
  scopes: string[],
): void {
  // Response interceptor to handle 401 errors
  axios.interceptors.response.use(
    (response) => response, // Pass through successful responses
    async (error: AxiosError) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & {
        _retry?: boolean;
      };

      // Check if this is a 401 error and we haven't already retried
      if (error.response?.status === 401 && !originalRequest?._retry) {
        originalRequest._retry = true;

        if (!isAzureAuthEnabled()) {
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${getDevAccessToken()}`;
          }
          return axios(originalRequest);
        }

        // Prevent redirect loop
        if (isRedirecting) {
          return Promise.reject(error);
        }

        // Get the active account
        const activeAccount = msalInstance.getActiveAccount();
        const accounts = msalInstance.getAllAccounts();

        if (!activeAccount && accounts.length === 0) {
          // Let the error propagate - user is not authenticated
          return Promise.reject(error);
        }

        const request = {
          scopes,
          account: activeAccount || accounts[0],
        };

        try {
          // Try to acquire token silently
          const authResult = await msalInstance.acquireTokenSilent(request);

          // Update the authorization header with new token
          if (originalRequest.headers) {
            originalRequest.headers.Authorization = `Bearer ${authResult.accessToken}`;
          }

          // Retry the original request with new token
          return axios(originalRequest);
        } catch (tokenError) {
          // If silent token acquisition fails, check if redirect is needed
          if (shouldTriggerRedirect(tokenError)) {
            // Set redirect flag to prevent loops
            isRedirecting = true;

            // Trigger redirect authentication
            await msalInstance.acquireTokenRedirect(request);
            // This line will never be reached as user is redirected away
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
