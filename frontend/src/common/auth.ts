import {
  IPublicClientApplication,
  InteractionRequiredAuthError,
} from "@azure/msal-browser";

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
    if (error instanceof InteractionRequiredAuthError) {
      // Redirect to login - user will be redirected away and app will reload
      await msalInstance.acquireTokenRedirect(request);
      // This line will never be reached as user has been redirected
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
    if (error instanceof InteractionRequiredAuthError) {
      await msalInstance.acquireTokenRedirect(request);
      throw error;
    }
    throw error;
  }
}
