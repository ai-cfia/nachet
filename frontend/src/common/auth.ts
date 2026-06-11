import {
  IPublicClientApplication,
  InteractionRequiredAuthError,
  BrowserAuthError,
} from "@azure/msal-browser";

const DEV_ACCESS_TOKEN = "local-dev-auth-disabled";
const DEV_USER_ID = "8ea46a6b-7d37-4fbb-a66f-775112376e16";
const DEV_USER_EMAIL = "test.user@inspection.gc.ca";

// Track if we're currently in a redirect flow to prevent loops
let isRedirecting = false;

function isFalseLike(value: unknown): boolean {
  return ["false", "0", "no", "off"].includes(
    String(value ?? "")
      .trim()
      .toLowerCase(),
  );
}

export function isAzureAuthEnabled(): boolean {
  return !isFalseLike(import.meta.env.VITE_AZURE_AUTH_ENABLED);
}

export function isAppAuthenticated(isMsalAuthenticated: boolean): boolean {
  return !isAzureAuthEnabled() || isMsalAuthenticated;
}

export function getDevAccessToken(): string {
  return import.meta.env.VITE_DEV_ACCESS_TOKEN || DEV_ACCESS_TOKEN;
}

export function getDevUserId(): string {
  return import.meta.env.VITE_DEV_USER_ID || DEV_USER_ID;
}

export function getDevUserEmail(): string {
  return import.meta.env.VITE_DEV_USER_EMAIL || DEV_USER_EMAIL;
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
      error.errorCode === "monitor_window_timeout") ||
    (error instanceof BrowserAuthError &&
      error.errorCode === "interaction_in_progress")
  );
}

/**
 * Reset the redirect flag (called after successful redirect)
 */
export function resetAuthRedirectFlag(): void {
  isRedirecting = false;
}

/**
 * Acquires an access token outside of React component context
 * This function can be safely used in useEffect dependencies without causing infinite loops
 *
 * @param msalInstance - The PublicClientApplication instance
 * @param scopes - Array of scopes to request
 * @returns Access token string
 * @throws Error if user is not signed in or token acquisition fails
 */
export async function acquireAccessToken(
  msalInstance: IPublicClientApplication,
  scopes: string[],
): Promise<string> {
  if (!isAzureAuthEnabled()) {
    return getDevAccessToken();
  }

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
}

/**
 * Acquires an ID token
 * @param msalInstance - The PublicClientApplication instance
 * @param scopes - Array of scopes to request
 * @returns ID token string
 */
export async function acquireIdToken(
  msalInstance: IPublicClientApplication,
  scopes: string[],
): Promise<string> {
  if (!isAzureAuthEnabled()) {
    return getDevAccessToken();
  }

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
}
