import { useEffect, useState, type Context, type ReactNode } from "react";
import axios, {
  type AxiosAdapter,
  type InternalAxiosRequestConfig,
} from "axios";
import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearApiAuthentication, fetchDevices } from "../../common/api";
import { NachetAuthProvider } from "../";
import type { NachetAuthContextValue } from "../NachetAuthContext";

const mockOidcAuth = vi.hoisted(() => ({
  getAccessToken: vi.fn(),
}));

vi.mock("../../logging", () => ({
  errorLogger: {
    getCorrelationId: vi.fn(() => "test-correlation-id"),
    getSessionId: vi.fn(() => "test-session-id"),
    logApiError: vi.fn(),
    logError: vi.fn(),
    setCorrelationId: vi.fn(),
    setTokenProvider: vi.fn(),
  },
}));

interface MockOidcAuthProviderProps {
  authContext: Context<NachetAuthContextValue | undefined>;
  children: ReactNode;
}

vi.mock("../oidc/OidcAuthProvider", () => ({
  OidcAuthProvider: ({ authContext, children }: MockOidcAuthProviderProps) => {
    const Provider = authContext.Provider;

    return (
      <Provider
        value={{
          provider: "oidc",
          isAuthenticated: true,
          isLoading: false,
          accounts: [
            {
              username: "oidc-user@example.com",
              name: "OIDC User",
              userId: "oidc-subject",
              isGuest: false,
              idTokenClaims: { sub: "oidc-subject" },
            },
          ],
          activeAccount: {
            username: "oidc-user@example.com",
            name: "OIDC User",
            userId: "oidc-subject",
            isGuest: false,
            idTokenClaims: { sub: "oidc-subject" },
          },
          login: vi.fn(),
          logout: vi.fn(),
          getAccessToken: mockOidcAuth.getAccessToken,
        }}
      >
        {children}
      </Provider>
    );
  },
}));

const ApiCallOnMount = ({ backendUrl }: { backendUrl: string }) => {
  const [status, setStatus] = useState("pending");

  useEffect(() => {
    void fetchDevices({ backendUrl })
      .then(() => {
        setStatus("loaded");
      })
      .catch((error: unknown) => {
        setStatus(error instanceof Error ? error.message : "failed");
      });
  }, [backendUrl]);

  return <span data-testid="api-status">{status}</span>;
};

describe("NachetAuthProvider API bridge", () => {
  const originalAdapter = axios.defaults.adapter;
  const authorizationHeaders: Array<string | undefined> = [];

  const okDevicesResponse = (requestConfig: InternalAxiosRequestConfig) => ({
    data: { devices: [] },
    status: 200,
    statusText: "OK",
    headers: {},
    config: requestConfig,
  });

  const getAuthorizationHeader = (
    requestConfig: InternalAxiosRequestConfig,
  ): string | undefined => {
    const authorizationHeader = requestConfig.headers.Authorization;
    return typeof authorizationHeader === "string"
      ? authorizationHeader
      : undefined;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    authorizationHeaders.length = 0;
    import.meta.env.VITE_AUTH_PROVIDER = "oidc";
    mockOidcAuth.getAccessToken.mockResolvedValue("oidc-api-token");
    const adapter: AxiosAdapter = async (requestConfig) => {
      authorizationHeaders.push(getAuthorizationHeader(requestConfig));

      return okDevicesResponse(requestConfig);
    };
    axios.defaults.adapter = adapter;
  });

  afterEach(() => {
    clearApiAuthentication();
    axios.defaults.adapter = originalAdapter;
    delete import.meta.env.VITE_AUTH_PROVIDER;
  });

  it("initializes Axios with the shared auth provider before child API helpers run", async () => {
    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/access_as_user">
        <ApiCallOnMount backendUrl="https://api.example.test" />
      </NachetAuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("api-status").textContent).toBe("loaded");
    });

    expect(mockOidcAuth.getAccessToken).toHaveBeenCalledOnce();
    expect(authorizationHeaders).toEqual(["Bearer oidc-api-token"]);
  });
});
