import { afterEach, describe, expect, it, vi } from "vitest";
import {
  acquireAccessToken,
  getDevAccessToken,
  getDevUserEmail,
  getDevUserId,
  isAppAuthenticated,
  isAzureAuthEnabled,
} from "../auth";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("local development auth mode", () => {
  it("treats auth as enabled by default", () => {
    expect(isAzureAuthEnabled()).toBe(true);
    expect(isAppAuthenticated(false)).toBe(false);
    expect(isAppAuthenticated(true)).toBe(true);
  });

  it("treats false-like VITE_AZURE_AUTH_ENABLED values as disabled", () => {
    vi.stubEnv("VITE_AZURE_AUTH_ENABLED", "false");

    expect(isAzureAuthEnabled()).toBe(false);
    expect(isAppAuthenticated(false)).toBe(true);
  });

  it("returns local dev identity defaults", () => {
    vi.stubEnv("VITE_AZURE_AUTH_ENABLED", "false");

    expect(getDevAccessToken()).toBe("local-dev-auth-disabled");
    expect(getDevUserId()).toBe("8ea46a6b-7d37-4fbb-a66f-775112376e16");
    expect(getDevUserEmail()).toBe("test.user@inspection.gc.ca");
  });

  it("allows local dev identity overrides", () => {
    vi.stubEnv("VITE_AZURE_AUTH_ENABLED", "false");
    vi.stubEnv("VITE_DEV_ACCESS_TOKEN", "custom-local-token");
    vi.stubEnv("VITE_DEV_USER_ID", "11111111-1111-1111-1111-111111111111");
    vi.stubEnv("VITE_DEV_USER_EMAIL", "developer@example.test");

    expect(getDevAccessToken()).toBe("custom-local-token");
    expect(getDevUserId()).toBe("11111111-1111-1111-1111-111111111111");
    expect(getDevUserEmail()).toBe("developer@example.test");
  });

  it("skips MSAL token acquisition when auth is disabled", async () => {
    vi.stubEnv("VITE_AZURE_AUTH_ENABLED", "false");
    const msalInstance = {
      getActiveAccount: vi.fn(),
      getAllAccounts: vi.fn(),
      acquireTokenSilent: vi.fn(),
      acquireTokenRedirect: vi.fn(),
    };

    await expect(acquireAccessToken(msalInstance as any, [])).resolves.toBe(
      "local-dev-auth-disabled",
    );
    expect(msalInstance.getActiveAccount).not.toHaveBeenCalled();
    expect(msalInstance.acquireTokenSilent).not.toHaveBeenCalled();
  });

  it("uses MSAL requirements when auth is enabled", async () => {
    vi.stubEnv("VITE_AZURE_AUTH_ENABLED", "true");
    const msalInstance = {
      getActiveAccount: vi.fn(() => null),
      getAllAccounts: vi.fn(() => []),
      acquireTokenSilent: vi.fn(),
      acquireTokenRedirect: vi.fn(),
    };

    await expect(acquireAccessToken(msalInstance as any, [])).rejects.toThrow(
      "User is not signed in",
    );
  });
});
