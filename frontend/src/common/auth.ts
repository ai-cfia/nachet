import { IPublicClientApplication } from "@azure/msal-browser";
import { InteractionRequiredAuthError } from "@azure/msal-browser";

export interface TokenRequest {
  scopes: string[];
}

export async function getAccessToken(
  msalInstance: IPublicClientApplication,
  request: TokenRequest,
): Promise<string> {
  try {
    const tokenResponse = await msalInstance.acquireTokenSilent(request);
    return tokenResponse.accessToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      const tokenResponse = await msalInstance.acquireTokenPopup(request);
      return tokenResponse.accessToken;
    }
    throw error;
  }
}

export async function getIdToken(
  msalInstance: IPublicClientApplication,
  request: TokenRequest,
): Promise<string> {
  try {
    const tokenResponse = await msalInstance.acquireTokenSilent(request);
    return tokenResponse.idToken;
  } catch (error) {
    if (error instanceof InteractionRequiredAuthError) {
      const tokenResponse = await msalInstance.acquireTokenPopup(request);
      return tokenResponse.idToken;
    }
    throw error;
  }
}
