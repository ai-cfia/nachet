import axios from "axios";
import { describe, expect, it, vi } from "vitest";
import { setupAxiosInterceptor } from "../apiInterceptor";

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
});
