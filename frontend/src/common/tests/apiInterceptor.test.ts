import axios from "axios";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  clearAxiosInterceptors,
  setupAxiosInterceptor,
} from "../apiInterceptor";

const runRequest = async (config: Record<string, unknown>) => {
  return axios({
    method: "get",
    url: "https://api.example.test/protected",
    ...config,
    adapter: async (requestConfig: any) => ({
      data: null,
      status: 200,
      statusText: "OK",
      headers: {},
      config: requestConfig,
    }),
  } as any);
};

describe("apiInterceptor", () => {
  afterEach(() => {
    clearAxiosInterceptors();
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
        adapter: async (requestConfig: any) => {
          return Promise.reject({
            config: requestConfig,
            response: {
              data: null,
              status: 401,
              statusText: "Unauthorized",
              headers: {},
              config: requestConfig,
            },
          });
        },
      } as any),
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
    const authorizationHeaders: string[] = [];
    setupAxiosInterceptor(getAccessToken);

    const response = await axios({
      method: "get",
      url: "https://api.example.test/protected",
      nachetAuthRequired: true,
      adapter: async (requestConfig: any) => {
        authorizationHeaders.push(requestConfig.headers.Authorization);
        if (authorizationHeaders.length === 1) {
          return Promise.reject({
            config: requestConfig,
            response: {
              data: null,
              status: 401,
              statusText: "Unauthorized",
              headers: {},
              config: requestConfig,
            },
          });
        }

        return {
          data: { ok: true },
          status: 200,
          statusText: "OK",
          headers: {},
          config: requestConfig,
        };
      },
    } as any);

    expect(response.data).toEqual({ ok: true });
    expect(getAccessToken).toHaveBeenCalledTimes(2);
    expect(authorizationHeaders[0]).toBe("Bearer initial-token");
    expect(authorizationHeaders[1]).toBe("Bearer retry-token");
  });
});
