import { createContext, useContext } from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { NachetAuthContextValue } from "../NachetAuthContext";
import { OidcAuthProvider } from "./OidcAuthProvider";

const mockOidcAuth = vi.hoisted(() => ({
  value: {
    isAuthenticated: true,
    isLoading: false,
    user: {
      expired: false,
      access_token: "oidc-access-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    },
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
    </div>
  );
};

const TokenConsumer = () => {
  const auth = useContext(TestAuthContext);

  return (
    <button onClick={() => void auth?.getAccessToken().catch(() => undefined)}>
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
          .catch(() => undefined);
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

        void Promise.allSettled([auth.getAccessToken(), auth.getAccessToken()]);
      }}
    >
      get tokens concurrently
    </button>
  );
};

describe("OidcAuthProvider", () => {
  beforeEach(() => {
    capturedAuthProviderSettings.value = undefined;
    mockOidcAuth.value.isAuthenticated = true;
    mockOidcAuth.value.isLoading = false;
    mockOidcAuth.value.user = {
      expired: false,
      access_token: "oidc-access-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    };
    mockOidcAuth.value.signinRedirect.mockClear();
    mockOidcAuth.value.signinSilent.mockClear();
    mockOidcAuth.value.signoutRedirect.mockClear();
    delete document.body.dataset.oidcToken;
    delete import.meta.env.VITE_OIDC_AUTHORITY;
    delete import.meta.env.VITE_OIDC_CLIENT_ID;
    delete import.meta.env.VITE_OIDC_SCOPE;
    delete import.meta.env.VITE_OIDC_REDIRECT_URI;
    delete import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI;
  });

  it("fails closed when required OIDC configuration is missing", () => {
    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim="api://nachet/access_as_user"
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
    import.meta.env.VITE_OIDC_AUTHORITY = "   ";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173";

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim="api://nachet/access_as_user"
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("Missing required OIDC auth configuration: VITE_OIDC_AUTHORITY");
  });

  it("passes provider-neutral settings to the local OIDC provider", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
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
      scope: "openid profile email api://nachet/access_as_user",
      automaticSilentRenew: false,
    });
    expect(capturedAuthProviderSettings.value).not.toHaveProperty(
      "silent_redirect_uri",
    );
    expect(screen.getByTestId("provider").textContent).toBe("oidc");
    expect(screen.getByTestId("username").textContent).toBe(
      "oidc-user@example.com",
    );
  });

  it("adds the API scope to an explicit OIDC scope", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
        authContext={TestAuthContext}
      >
        <TestConsumer />
      </OidcAuthProvider>,
    );

    expect(capturedAuthProviderSettings.value).toMatchObject({
      scope: "openid profile api://nachet/access_as_user",
    });
  });

  it("starts sign-in when silent token renewal fails", async () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";
    mockOidcAuth.value.user = {
      expired: true,
      access_token: "expired-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    };
    mockOidcAuth.value.signinSilent.mockRejectedValueOnce(
      new Error("silent renewal failed"),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
        authContext={TestAuthContext}
      >
        <TokenConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("get token"));

    await waitFor(() => {
      expect(mockOidcAuth.value.signinRedirect).toHaveBeenCalledWith({
        scope: "openid profile email api://nachet/access_as_user",
      });
    });
  });

  it("returns the cached token when it is fresh and the default scope is requested", async () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
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
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce({
      expired: false,
      access_token: "fresh-oidc-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    });

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
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
      scope: "openid profile email api://nachet/access_as_user",
    });
  });

  it("uses silent renewal when additional scopes are requested", async () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce({
      expired: false,
      access_token: "extra-scope-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    });

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer scopes={["custom-scope"]} />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(document.body.dataset.oidcToken).toBe("extra-scope-token");
    });
    expect(mockOidcAuth.value.signinSilent).toHaveBeenCalledWith({
      scope: "openid profile email api://nachet/access_as_user custom-scope",
    });
  });

  it("starts sign-in when silent token renewal returns no fresh token", async () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";
    mockOidcAuth.value.user = {
      expired: true,
      access_token: "expired-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    };
    mockOidcAuth.value.signinSilent.mockResolvedValueOnce(null);

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
        authContext={TestAuthContext}
      >
        <TokenCaptureConsumer />
      </OidcAuthProvider>,
    );

    fireEvent.click(screen.getByText("capture token"));

    await waitFor(() => {
      expect(mockOidcAuth.value.signinRedirect).toHaveBeenCalledWith({
        scope: "openid profile email api://nachet/access_as_user",
      });
    });
  });

  it("shares expired-token recovery across concurrent requests", async () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile email";
    import.meta.env.VITE_OIDC_REDIRECT_URI = "http://localhost:5173/callback";
    import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI =
      "http://localhost:5173/";
    mockOidcAuth.value.user = {
      expired: true,
      access_token: "expired-token",
      profile: {
        preferred_username: "oidc-user@example.com",
        name: "OIDC User",
        sub: "oidc-subject",
      },
    };

    let rejectRenewal: (error: Error) => void = () => {};
    mockOidcAuth.value.signinSilent.mockReturnValueOnce(
      new Promise<null>((_, reject) => {
        rejectRenewal = reject;
      }),
    );

    render(
      <OidcAuthProvider
        apiScopeClaim="api://nachet/access_as_user"
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
      expect(mockOidcAuth.value.signinRedirect).toHaveBeenCalledTimes(1);
      expect(mockOidcAuth.value.signinRedirect).toHaveBeenCalledWith({
        scope: "openid profile email api://nachet/access_as_user",
      });
    });
  });
});
