import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

let requestInterceptorId: number | null = null;
let responseInterceptorId: number | null = null;
let apiAccessTokenProvider: GetAccessToken | null = null;

interface NachetAuthRequestConfig extends InternalAxiosRequestConfig {
  useNachetAuthProvider?: boolean;
}

interface RetriableNachetAuthRequestConfig extends NachetAuthRequestConfig {
  _retry?: boolean;
}

interface AccessTokenOptions {
  forceRefresh?: boolean;
}

type GetAccessToken = (options?: AccessTokenOptions) => Promise<string>;

const assertAccessToken = (accessToken: string): string => {
  if (!accessToken) {
    throw new Error("Access token is empty");
  }

  return accessToken;
};

const requestUsesNachetAuthProvider = (
  request?: NachetAuthRequestConfig,
): boolean => {
  return request?.useNachetAuthProvider === true;
};

export const clearAxiosInterceptors = (): void => {
  if (requestInterceptorId !== null) {
    axios.interceptors.request.eject(requestInterceptorId);
    requestInterceptorId = null;
  }

  if (responseInterceptorId !== null) {
    axios.interceptors.response.eject(responseInterceptorId);
    responseInterceptorId = null;
  }

  apiAccessTokenProvider = null;
};

export const hasApiAccessTokenProvider = (): boolean => {
  return apiAccessTokenProvider !== null;
};

/**
 * Configure axios interceptor to handle 401 Unauthorized errors and retry once
 * with an access token from the active auth provider.
 *
 * @param getAccessToken - Provider-neutral token getter
 */
export const setupAxiosInterceptor = (getAccessToken: GetAccessToken): void => {
  clearAxiosInterceptors();
  apiAccessTokenProvider = getAccessToken;

  requestInterceptorId = axios.interceptors.request.use(
    async (config: NachetAuthRequestConfig) => {
      if (
        !requestUsesNachetAuthProvider(config) ||
        config.headers.has("Authorization")
      ) {
        return config;
      }

      config.headers.set(
        "Authorization",
        `Bearer ${assertAccessToken(await getAccessToken())}`,
      );
      return config;
    },
    (error) => Promise.reject(error),
  );

  // Response interceptor to handle 401 errors
  responseInterceptorId = axios.interceptors.response.use(
    (response) => response, // Pass through successful responses
    async (error: AxiosError) => {
      const originalRequest = error.config as
        | RetriableNachetAuthRequestConfig
        | undefined;

      // Check if this is a 401 error and we haven't already retried
      if (
        error.response?.status === 401 &&
        originalRequest &&
        requestUsesNachetAuthProvider(originalRequest) &&
        !originalRequest._retry
      ) {
        originalRequest._retry = true;

        try {
          const accessToken = assertAccessToken(
            await getAccessToken({ forceRefresh: true }),
          );

          // Update the authorization header with new token
          originalRequest.headers.set("Authorization", `Bearer ${accessToken}`);

          // Retry the original request with new token
          return axios(originalRequest);
        } catch (tokenError) {
          return Promise.reject(tokenError);
        }
      }

      // For non-401 errors or already retried requests, reject as normal
      return Promise.reject(error);
    },
  );
};
