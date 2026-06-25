import { createContext, useContext } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { NachetAuthContextValue } from "../NachetAuthContext";
import { OidcAuthProvider } from "./OidcAuthProvider";

const API_SCOPE_CLAIM = "api://nachet/access_as_user";
const DEFAULT_OIDC_ENV = {
  VITE_OIDC_AUTHORITY: "https://idp.example/realms/nachet",
  VITE_OIDC_CLIENT_ID: "frontend-client-id",
  VITE_OIDC_SCOPE: "openid profile email",
  VITE_OIDC_REDIRECT_URI: "http://localhost:5173/callback",
  VITE_OIDC_POST_LOGOUT_REDIRECT_URI: "http://localhost:5173/",
};

type OidcEnv = typeof DEFAULT_OIDC_ENV;

const setOidcEnv = (overrides: Partial<OidcEnv> = {}): void => {
  const env = { ...DEFAULT_OIDC_ENV, ...overrides };
  import.meta.env.VITE_OIDC_AUTHORITY = env.VITE_OIDC_AUTHORITY;
  import.meta.env.VITE_OIDC_CLIENT_ID = env.VITE_OIDC_CLIENT_ID;
  import.meta.env.VITE_OIDC_SCOPE = env.VITE_OIDC_SCOPE;
  import.meta.env.VITE_OIDC_REDIRECT_URI = env.VITE_OIDC_REDIRECT_URI;
  import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
    env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI;
};

const clearOidcEnv = (): void => {
  delete import.meta.env.VITE_OIDC_AUTHORITY;
  delete import.meta.env.VITE_OIDC_CLIENT_ID;
  delete import.meta.env.VITE_OIDC_SCOPE;
  delete import.meta.env.VITE_OIDC_REDIRECT_URI;
  delete import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI;
};

const createOidcUser = vi.hoisted(
  () =>
    ({
      expired = false,
      accessToken = "oidc-access-token",
      expiresAt = Math.floor(Date.now() / 1000) + (expired ? -60 : 300),
      profile = {},
    }: {
      expired?: boolean;
      accessToken?: string;
      expiresAt?: number;
      profile?: Record<string, unknown>;
    } = {}) => ({
      expired,
      access_token: accessToken,
      expires_at: expiresAt,
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
        ...profile,
      },
    }),
);

const mockOidcAuth = vi.hoisted(() => ({
  value: {
    isAuthenticated: true,
    isLoading: false,
    user: createOidcUser(),
    signinRedirect: vi.fn(),
    signinSilent: vi.fn(),
    signoutRedirect: vi.fn(),
  },
}));

const capturedAuthProviderSettings = vi.hoisted(() => ({
  value: undefined as Record<string, unknown> | undefined,
}));

vi.mock("./react-oidc-context/AuthProvider", () => ({
  AuthProvider: ({ children, ...settings }: any) => {
    capturedAuthProviderSettings.value = settings;
    return <>{children}</>;
  },
}));

vi.mock("./react-oidc-context/useAuth", () => ({
  useAuth: () => mockOidcAuth.value,
}));

const TestAuthContext = createContext<NachetAuthContextValue | undefined>(
  undefined,
);

const TestConsumer = () => {
  const auth = useContext(TestAuthContext);

  return (
    <div>
      <span data-testid="provider">{auth?.provider}</span>
      <span data-testid="username">{auth?.activeAccount?.username}</span>
      <span data-testid="user-id">{auth?.activeAccount?.userId}</span>
      <span data-testid="guest">
        {auth?.activeAccount?.isGuest ? "guest" : "member"}
      </span>
    </div>
  );
};

const TokenConsumer = () => {
  const auth = useContext(TestAuthContext);

  return (
    <button
      onClick={() => {
        void auth?.getAccessToken().catch((error: unknown) => {
          document.body.dataset.oidcTokenError =
            error instanceof Error ? error.message : "unknown error";
        });
      }}
    >
      get token
    </button>
  );
};

const TokenCaptureConsumer = ({
  forceRefresh = false,
  scopes,
}: {
  forceRefresh?: boolean;
  scopes?: string[];
}) => {
  const auth = useContext(TestAuthContext);

  return (
    <button
      onClick={() => {
        void auth
          ?.getAccessToken(scopes, forceRefresh ? { forceRefresh } : undefined)
          .then((token) => {
            document.body.dataset.oidcToken = token;
          })
          .catch((error: unknown) => {
            document.body.dataset.oidcTokenError =
              error instanceof Error ? error.message : "unknown error";
          });
      }}
    >
      capture token
    </button>
  );
};

const ConcurrentTokenConsumer = () => {
  const auth = useContext(TestAuthContext);

  return (
    <button
      onClick={() => {
        if (!auth) {
          return;
        }

        void Promise.allSettled([
          auth.getAccessToken(),
          auth.getAccessToken(),
        ]).then((results) => {
          document.body.dataset.concurrentTokenResults = results
            .map((result) => result.status)
            .join(",");
        });
      }}
    >
      get tokens concurrently
    </button>
  );
};

const OrderedScopesConsumer = () => {
  const auth = useContext(TestAuthContext);

  return (
    <div>
      <button
        onClick={() => {
          void auth?.getAccessToken(["read", "write"]).then((token) => {
            document.body.dataset.firstScopeToken = token;
          });
        }}
      >
        first order
      </button>
      <button
        onClick={() => {
          void auth?.getAccessToken(["write", "read"]).then((token) => {
            document.body.dataset.secondScopeToken = token;
          });
        }}
      >
        second order
      </button>
    </div>
  );
};

describe("OidcAuthProvider", () => {
  beforeEach(() => {
    capturedAuthProviderSettings.value = undefined;
    mockOidcAuth.value.isAuthenticated = true;
    mockOidcAuth.value.isLoading = false;
    mockOidcAuth.value.user = createOidcUser();
    mockOidcAuth.value.signinRedirect.mockReset();
    mockOidcAuth.value.signinSilent.mockReset();
    mockOidcAuth.value.signoutRedirect.mockReset();
    delete document.body.dataset.oidcToken;
    delete document.body.dataset.oidcTokenError;
    delete document.body.dataset.concurrentTokenResults;
    delete document.body.dataset.firstScopeToken;
    delete document.body.dataset.secondScopeToken;
    clearOidcEnv();
  });

  it("fails closed when required OIDC configuration is missing", () => {
    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim={API_SCOPE_CLAIM}
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow(
      "Missing required OIDC auth configuration: VITE_OIDC_AUTHORITY, VITE_OIDC_CLIENT_ID, VITE_OIDC_SCOPE, VITE_OIDC_REDIRECT_URI, VITE_OIDC_POST_LOGOUT_REDIRECT_URI",
    );
  });

  it("fails closed when a required OIDC value is blank", () => {
    setOidcEnv({ VITE_OIDC_AUTHORITY: "   " });

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim={API_SCOPE_CLAIM}
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("Missing required OIDC auth configuration: VITE_OIDC_AUTHORITY");
  });

  it("passes provider-neutral settings to the local OIDC provider", () => {
    setOidcEnv();

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TestConsumer />
      </OidcAuthProvider>,
    );

    expect(capturedAuthProviderSettings.value).toMatchObject({
      authority: "https://idp.example/realms/nachet",
      client_id: "frontend-client-id",
      redirect_uri: "http://localhost:5173/callback",
      post_logout_redirect_uri: "http://localhost:5173/",
      response_type: "code",
      scope: "api://nachet/access_as_user email openid profile",
      automaticSilentRenew: false,
    });
    expect(capturedAuthProviderSettings.value).not.toHaveProperty(
      "silent_redirect_uri",
    );
    expect(screen.getByTestId("provider").textContent).toBe("oidc");
    expect(screen.getByTestId("username").textContent).toBe(
      "oidc-user@example.com",
    );
    expect(screen.getByTestId("user-id").textContent).toBe("oidc-subject");
    expect(screen.getByTestId("guest").textContent).toBe("guest");
  });

  it("prefers an OIDC oid claim when one is available", () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      profile: {
        oid: "provider-object-id",
      },
    });

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TestConsumer />
      </OidcAuthProvider>,
    );

    expect(screen.getByTestId("user-id").textContent).toBe(
      "provider-object-id",
    );
  });

  it("fails closed when the OIDC profile has no stable subject identifier", () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      profile: {
        sub: undefined,
      },
    });

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim={API_SCOPE_CLAIM}
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("OIDC user profile is missing a stable user identifier.");
  });

  it("adds the API scope to an explicit OIDC scope", () => {
    setOidcEnv({ VITE_OIDC_SCOPE: "openid profile" });

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TestConsumer />
      </OidcAuthProvider>,
    );

    expect(capturedAuthProviderSettings.value).toMatchObject({
      scope: "api://nachet/access_as_user openid profile",
    });
  });

  it("does not redirect automatically when silent token renewal fails", async () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      expired: true,
      accessToken: "expired-token",
    });
    mockOidcAuth.value.signinSilent.mockRejectedValueOnce(
      new Error("silent renewal failed"),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("get token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcTokenError).toBe(
        "silent renewal failed",
      );
    });
    expect(mockOidcAuth.value.signinRedirect).not.toHaveBeenCalled();
  });

  it("returns the cached token when it is fresh and the default scope is requested", async () => {
    setOidcEnv();

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("oidc-access-token");
    });
    expect(mockOidcAuth.value.signinSilent).not.toHaveBeenCalled();
  });

  it("force-refreshes the token after a protected API 401", async () => {
    setOidcEnv();
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(
      createOidcUser({ accessToken: "fresh-oidc-token" }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer forceRefresh />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("fresh-oidc-token");
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledWith({
      scope: "api://nachet/access_as_user email openid profile",
    });
  });

  it("uses silent renewal when additional scopes are requested", async () => {
    setOidcEnv();
    mockOidcAuth.value.signinSilent.mockResolvedValue(
      createOidcUser({ accessToken: "extra-scope-token" }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("extra-scope-token");
    });

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledTimes(1);
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledWith({
      scope: "api://nachet/access_as_user custom-scope email openid profile",
    });
  });

  it("uses the same cache entry for reordered additional scopes", async () => {
    setOidcEnv();
    mockOidcAuth.value.signinSilent.mockResolvedValue(
      createOidcUser({ accessToken: "ordered-scope-token" }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <OrderedScopesConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("first order"));

    await waitFor(() => {
      expect(document.body.dataset.firstScopeToken).toBe("ordered-scope-token");
    });

    fireEvent.click(screen.getByText("second order"));

    await waitFor(() => {
      expect(document.body.dataset.secondScopeToken).toBe(
        "ordered-scope-token",
      );
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledTimes(1);
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledWith({
      scope: "api://nachet/access_as_user email openid profile read write",
    });
  });

  it("renews tokens before they enter the expiry buffer", async () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      accessToken: "almost-expired-token",
      expiresAt: Math.floor(Date.now() / 1000) + 30,
    });
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(
      createOidcUser({ accessToken: "buffer-renewed-token" }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("buffer-renewed-token");
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledWith({
      scope: "api://nachet/access_as_user email openid profile",
    });
  });

  it("keeps custom-scope cache when the same user object refreshes", async () => {
    setOidcEnv();
    mockOidcAuth.value.signinSilent.mockResolvedValue(
      createOidcUser({ accessToken: "cached-custom-scope-token" }),
    );

    const { rerender } = render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("cached-custom-scope-token");
    });

    mockOidcAuth.value.user = createOidcUser({
      accessToken: "refreshed-default-token",
      profile: {
        sub: "oidc-subject",
      },
    });
    rerender(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledTimes(1);
    });
  });

  it("clears custom-scope cache when the OIDC user identity changes", async () => {
    setOidcEnv();
    const { rerender } = render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(
      createOidcUser({ accessToken: "first-user-token" }),
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("first-user-token");
    });

    mockOidcAuth.value.user = createOidcUser({
      accessToken: "second-default-token",
      profile: {
        sub: "second-oidc-subject",
      },
    });
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(
      createOidcUser({
        accessToken: "second-user-custom-token",
        profile: {
          sub: "second-oidc-subject",
        },
      }),
    );
    rerender(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("second-user-custom-token");
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledTimes(2);
  });

  it("does not redirect automatically when silent renewal returns no fresh token", async () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      expired: true,
      accessToken: "expired-token",
    });
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(null);

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcTokenError).toBe(
        "OIDC silent token renewal did not return a usable access token.",
      );
    });
    expect(mockOidcAuth.value.signinRedirect).not.toHaveBeenCalled();
  });

  it("shares expired-token recovery across concurrent requests", async () => {
    setOidcEnv();
    mockOidcAuth.value.user = createOidcUser({
      expired: true,
      accessToken: "expired-token",
    });

    let rejectRenewal: (error: Error) => void = () => {};
    mockOidcAuth.value.signinSilent.mockReturnValueOnce(
      new Promise<null>((_, reject) => {
        rejectRenewal = reject;
      }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim={API_SCOPE_CLAIM}
        authContext={TestAuthContext}
      >
        <ConcurrentTokenConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("get tokens concurrently"));

    await waitFor(() => {
      expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledTimes(1);
    });

    rejectRenewal(new Error("silent renewal failed"));

    await waitFor(() => {
      expect(document.body.dataset.concurrentTokenResults).toBe(
        "rejected,rejected",
      );
    });
    expect(mockOidcAuth.value.signinRedirect).not.toHaveBeenCalled();
  });
});
