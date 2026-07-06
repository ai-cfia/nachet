import {
  IPublicClientApplication,
  InteractionRequiredAuthError,
  BrowserAuthError,
} from "@azure/msal-browser";
import type { NachetAuthTokenOptions } from "@auth";

// Track if we're currently in a redirect flow to prevent loops
let isRedirecting = false;

/**
 * Checks if an error requires user interaction (redirect to login)
 * @param error - The error to check
 * @returns true if the error requires redirect authentication
 */
export const shouldTriggerRedirect = (error: unknown): boolean => {
  return (
    error instanceof InteractionRequiredAuthError ||
    (error instanceof BrowserAuthError &&
      error.errorCode === "monitor_window_timeout") ||
    (error instanceof BrowserAuthError &&
      error.errorCode === "interaction_in_progress")
  );
};

/**
 * Reset the redirect flag (called after successful redirect)
 */
export const resetAuthRedirectFlag = (): void => {
  isRedirecting = false;
};

/**
 * Acquires an access token outside of React component context
 * This function can be safely used in useEffect dependencies without causing infinite loops
 *
 * @param msalInstance - The PublicClientApplication instance
 * @param scopes - Array of scopes to request
 * @returns Access token string
 * @throws Error if user is not signed in or token acquisition fails
 */
export const acquireAccessToken = async (
  msalInstance: IPublicClientApplication,
  scopes: string[],
  options: NachetAuthTokenOptions = {},
): Promise<string> => {
  const activeAccount = msalInstance.getActiveAccount();
  const accounts = msalInstance.getAllAccounts();

  if (!activeAccount && accounts.length === 0) {
    throw new Error(
      "User is not signed in. Cannot acquire token outside of MsalProvider context.",
    );
  }

  const request = {
    scopes,
    account: activeAccount || accounts[0],
    forceRefresh: options.forceRefresh,
  };

  try {
    const authResult = await msalInstance.acquireTokenSilent(request);
    return authResult.accessToken;
  } catch (error) {
    // Prevent redirect loop - if already redirecting, just throw the error
    if (isRedirecting) {
      throw error;
    }

    // Check if error requires redirect (InteractionRequiredAuthError or timeout)
    if (shouldTriggerRedirect(error)) {
      // Set flag to prevent concurrent redirects
      isRedirecting = true;

      // Redirect to login - user will be redirected away and app will reload
      try {
        await msalInstance.acquireTokenRedirect(request);
        // This line will never be reached as user has been redirected
      } catch (redirectError) {
        // If redirect fails, reset flag
        isRedirecting = false;
        throw redirectError;
      }
      throw error;
    }
    throw error;
  }
};

/**
 * Acquires an ID token
 * @param msalInstance - The PublicClientApplication instance
 * @param scopes - Array of scopes to request
 * @returns ID token string
 */
export const acquireIdToken = async (
  msalInstance: IPublicClientApplication,
  scopes: string[],
): Promise<string> => {
  const activeAccount = msalInstance.getActiveAccount();
  const accounts = msalInstance.getAllAccounts();

  if (!activeAccount && accounts.length === 0) {
    throw new Error(
      "User is not signed in. Cannot acquire token outside of MsalProvider context.",
    );
  }

  const request = {
    scopes,
    account: activeAccount || accounts[0],
  };

  try {
    const authResult = await msalInstance.acquireTokenSilent(request);
    return authResult.idToken;
  } catch (error) {
    // Prevent redirect loop
    if (isRedirecting) {
      console.error(
        "Already redirecting to login, skipping duplicate redirect",
      );
      throw error;
    }

    // Check if error requires redirect (InteractionRequiredAuthError or timeout)
    if (shouldTriggerRedirect(error)) {
      isRedirecting = true;
      try {
        await msalInstance.acquireTokenRedirect(request);
      } catch (redirectError) {
        isRedirecting = false;
        throw redirectError;
      }
      throw error;
    }
    throw error;
  }
};
