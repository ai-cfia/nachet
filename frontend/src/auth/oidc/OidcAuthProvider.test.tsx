import { createContext, useContext } from "react";
import { render, screen } from "@testing-library/react";
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

describe("OidcAuthProvider", () => {
  beforeEach(() => {
    capturedAuthProviderSettings.value = undefined;
    mockOidcAuth.value.signinRedirect.mockClear();
    mockOidcAuth.value.signinSilent.mockClear();
    mockOidcAuth.value.signoutRedirect.mockClear();
    delete import.meta.env.VITE_OIDC_AUTHORITY;
    delete import.meta.env.VITE_OIDC_CLIENT_ID;
    delete import.meta.env.VITE_OIDC_SCOPE;
    delete import.meta.env.VITE_OIDC_REDIRECT_URI;
    delete import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI;
    delete import.meta.env.VITE_OIDC_SILENT_REDIRECT_URI;
  });

  it("fails closed when the OIDC authority is missing", () => {
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim="api://nachet/access_as_user"
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("VITE_OIDC_AUTHORITY is required by the OIDC auth adapter");
  });

  it("fails closed when a required OIDC value is blank", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "   ";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim="api://nachet/access_as_user"
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("VITE_OIDC_AUTHORITY is required by the OIDC auth adapter");
  });

  it("fails closed when the OIDC client id is missing", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";

    expect(() =>
      render(
        <OidcAuthProvider
          apiScopeClaim="api://nachet/access_as_user"
          authContext={TestAuthContext}
        >
          <TestConsumer />
        </OidcAuthProvider>,
      ),
    ).toThrow("VITE_OIDC_CLIENT_ID is required by the OIDC auth adapter");
  });

  it("passes provider-neutral settings to the local OIDC provider", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
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
    expect(screen.getByTestId("provider").textContent).toBe("oidc");
    expect(screen.getByTestId("username").textContent).toBe(
      "oidc-user@example.com",
    );
  });

  it("adds the API scope to an explicit OIDC scope", () => {
    import.meta.env.VITE_OIDC_AUTHORITY = "https://idp.example/realms/nachet";
    import.meta.env.VITE_OIDC_CLIENT_ID = "frontend-client-id";
    import.meta.env.VITE_OIDC_SCOPE = "openid profile";

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
});
