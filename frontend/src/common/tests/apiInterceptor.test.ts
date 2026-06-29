import axios, {
  type AxiosAdapter,
  type AxiosRequestConfig,
  type InternalAxiosRequestConfig,
} from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import { setupAxiosInterceptor } from "../apiInterceptor";
import { clearApiAuthentication, fetchDevices, initializeApi } from "../api";

interface NachetAuthAxiosRequestConfig extends AxiosRequestConfig {
  nachetAuthRequired?: boolean;
}

const okResponse = (
  requestConfig: InternalAxiosRequestConfig,
  data: unknown = null,
) => ({
  data,
  status: 200,
  statusText: "OK",
  headers: {},
  config: requestConfig,
});

const unauthorizedResponse = (requestConfig: InternalAxiosRequestConfig) => ({
  config: requestConfig,
  response: {
    data: null,
    status: 401,
    statusText: "Unauthorized",
    headers: {},
    config: requestConfig,
  },
});

const getAuthorizationHeader = (
  requestConfig: InternalAxiosRequestConfig,
): string | undefined => {
  const authorizationHeader = requestConfig.headers.Authorization;
  return typeof authorizationHeader === "string"
    ? authorizationHeader
    : undefined;
};

const runRequest = async (config: NachetAuthAxiosRequestConfig) => {
  return axios({
    method: "get",
    url: "https://api.example.test/protected",
    ...config,
    adapter: async (requestConfig) => okResponse(requestConfig),
  });
};

describe("apiInterceptor", () => {
  const originalAdapter = axios.defaults.adapter;

  afterEach(() => {
    clearApiAuthentication();
    axios.defaults.adapter = originalAdapter;
  });

  it("attaches a bearer token to protected Nachet API requests", async () => {
    setupAxiosInterceptor(vi.fn().mockResolvedValue("access-token"));

    const response = await runRequest({ nachetAuthRequired: true });

    expect(response.config.headers.Authorization).toBe("Bearer access-token");
  });

  it("does not attach a bearer token to requests without the Nachet API marker", async () => {
    const getAccessToken = vi.fn().mockResolvedValue("access-token");
    setupAxiosInterceptor(getAccessToken);

    const response = await runRequest({});

    expect(getAccessToken).not.toHaveBeenCalled();
    expect(response.config.headers.Authorization).toBeUndefined();
  });

  it("fails closed when a protected request cannot get a token", async () => {
    setupAxiosInterceptor(vi.fn().mockResolvedValue(""));

    await expect(runRequest({ nachetAuthRequired: true })).rejects.toThrow(
      "Access token is null or empty",
    );
  });

  it("does not retry unrelated 401 responses with a bearer token", async () => {
    const getAccessToken = vi.fn().mockResolvedValue("access-token");
    setupAxiosInterceptor(getAccessToken);

    await expect(
      axios({
        method: "get",
        url: "https://example.test/not-nachet",
        adapter: async (requestConfig) => {
          return Promise.reject(unauthorizedResponse(requestConfig));
        },
      }),
    ).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(getAccessToken).not.toHaveBeenCalled();
  });

  it("retries marked protected requests once with a replacement token", async () => {
    const getAccessToken = vi
      .fn()
      .mockResolvedValueOnce("initial-token")
      .mockResolvedValueOnce("retry-token");
    const authorizationHeaders: Array<string | undefined> = [];
    setupAxiosInterceptor(getAccessToken);

    const retryAdapter: AxiosAdapter = async (requestConfig) => {
      authorizationHeaders.push(getAuthorizationHeader(requestConfig));
      if (authorizationHeaders.length === 1) {
        return Promise.reject(unauthorizedResponse(requestConfig));
      }

      return okResponse(requestConfig, { ok: true });
    };

    const requestConfig: NachetAuthAxiosRequestConfig = {
      method: "get",
      url: "https://api.example.test/protected",
      nachetAuthRequired: true,
      adapter: retryAdapter,
    };

    const response = await axios(requestConfig);

    expect(response.data).toEqual({ ok: true });
    expect(getAccessToken).toHaveBeenCalledTimes(2);
    expect(getAccessToken).toHaveBeenNthCalledWith(1);
    expect(getAccessToken).toHaveBeenNthCalledWith(2, { forceRefresh: true });
    expect(authorizationHeaders[0]).toBe("Bearer initial-token");
    expect(authorizationHeaders[1]).toBe("Bearer retry-token");
  });

  it("attaches tokens to API helper requests through initializeApi", async () => {
    const getAccessToken = vi.fn().mockResolvedValue("api-helper-token");
    const authorizationHeaders: Array<string | undefined> = [];
    axios.defaults.adapter = async (requestConfig) => {
      authorizationHeaders.push(getAuthorizationHeader(requestConfig));
      return okResponse(requestConfig, { devices: [] });
    };

    initializeApi(getAccessToken);

    await expect(
      fetchDevices({ backendUrl: "https://api.example.test" }),
    ).resolves.toEqual({ devices: [] });
    expect(getAccessToken).toHaveBeenCalledOnce();
    expect(authorizationHeaders).toEqual(["Bearer api-helper-token"]);
  });

  it("retries stale explicit-token requests with a replacement token", async () => {
    const getAccessToken = vi.fn().mockResolvedValue("retry-token");
    const authorizationHeaders: Array<string | undefined> = [];
    setupAxiosInterceptor(getAccessToken);

    const retryAdapter: AxiosAdapter = async (requestConfig) => {
      authorizationHeaders.push(getAuthorizationHeader(requestConfig));
      if (authorizationHeaders.length === 1) {
        return Promise.reject(unauthorizedResponse(requestConfig));
      }

      return okResponse(requestConfig, { ok: true });
    };

    const requestConfig: NachetAuthAxiosRequestConfig = {
      method: "get",
      url: "https://api.example.test/protected",
      nachetAuthRequired: true,
      headers: { Authorization: "Bearer stale-token" },
      adapter: retryAdapter,
    };

    const response = await axios(requestConfig);

    expect(response.data).toEqual({ ok: true });
    expect(getAccessToken).toHaveBeenCalledOnce();
    expect(getAccessToken).toHaveBeenCalledWith({ forceRefresh: true });
    expect(authorizationHeaders[0]).toBe("Bearer stale-token");
    expect(authorizationHeaders[1]).toBe("Bearer retry-token");
  });
});
