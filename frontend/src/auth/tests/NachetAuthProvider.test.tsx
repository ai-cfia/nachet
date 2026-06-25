import type { Context, ReactNode } from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InteractionStatus, Logger } from "@azure/msal-browser";
import type { AccountInfo, PublicClientApplication } from "@azure/msal-browser";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import type { IMsalContext } from "@azure/msal-react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { acquireAccessToken } from "../../common/auth";
import {
  NachetAuthProvider,
  useNachetAuth,
  type NachetAuthContextValue,
} from "../";

vi.mock("@azure/msal-react", () => ({
  MsalProvider: ({ children }: { children: ReactNode }) => <>{children}</>,
  useIsAuthenticated: vi.fn(),
  useMsal: vi.fn(),
}));
vi.mock("../../common/auth");
vi.mock("../oidc/OidcAuthProvider", () => ({
  OidcAuthProvider: ({
    authContext,
    children,
  }: {
    authContext: Context<NachetAuthContextValue | undefined>;
    children: ReactNode;
  }) => {
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
              isGuest: true,
              idTokenClaims: { sub: "oidc-subject" },
            },
          ],
          activeAccount: {
            username: "oidc-user@example.com",
            name: "OIDC User",
            userId: "oidc-subject",
            isGuest: true,
            idTokenClaims: { sub: "oidc-subject" },
          },
          login: vi.fn(),
          logout: vi.fn(),
          getAccessToken: vi.fn().mockResolvedValue("oidc-access-token"),
        }}
      >
        {children}
      </Provider>
    );
  },
}));

const mockAccount: AccountInfo = {
  homeAccountId: "home-account-id",
  environment: "login.microsoftonline.com",
  tenantId: "tenant-id",
  localAccountId: "local-account-id",
  username: "user@example.com",
  name: "Test User",
  idTokenClaims: {
    oid: "member-oid",
    acct: 0,
  },
};

const TestConsumer = () => {
  const auth = useNachetAuth();

  return (
    <div>
      <span data-testid="provider">{auth.provider}</span>
      <span data-testid="authenticated">
        {auth.isAuthenticated ? "authenticated" : "anonymous"}
      </span>
      <span data-testid="loading">{auth.isLoading ? "loading" : "idle"}</span>
      <span data-testid="username">{auth.activeAccount?.username ?? ""}</span>
      <span data-testid="user-id">{auth.activeAccount?.userId ?? ""}</span>
      <span data-testid="guest">
        {auth.activeAccount?.isGuest ? "guest" : "member"}
      </span>
      <button onClick={() => void auth.login()}>login</button>
      <button onClick={() => void auth.logout()}>logout</button>
      <button
        onClick={() => {
          void auth.getAccessToken().then((token) => {
            document.body.dataset.token = token;
          });
        }}
      >
        token
      </button>
    </div>
  );
};

describe("NachetAuthProvider", () => {
  const mockMsalInstance = {
    getActiveAccount: vi.fn(),
    setActiveAccount: vi.fn(),
    loginRedirect: vi.fn(),
    logoutRedirect: vi.fn(),
  };
  const mockPublicClientApplication =
    mockMsalInstance as unknown as PublicClientApplication;
  const createMsalContext = (
    inProgress: InteractionStatus = InteractionStatus.None,
  ): IMsalContext => ({
    instance: mockPublicClientApplication,
    inProgress,
    accounts: [mockAccount],
    logger: new Logger({}),
  });

  const renderWithProvider = ({
    msalInstance = mockPublicClientApplication,
  }: { msalInstance?: PublicClientApplication } = {}) =>
    render(
      <NachetAuthProvider
        apiScopeClaim="api://nachet/scope"
        msalInstance={msalInstance}
      >
        <TestConsumer />
      </NachetAuthProvider>,
    );

  beforeEach(() => {
    vi.clearAllMocks();
    delete document.body.dataset.token;
    import.meta.env.VITE_AUTH_PROVIDER = "msal";

    mockMsalInstance.getActiveAccount.mockReturnValue(null);
    mockMsalInstance.loginRedirect.mockResolvedValue(undefined);
    mockMsalInstance.logoutRedirect.mockResolvedValue(undefined);

    vi.mocked(useMsal).mockReturnValue(createMsalContext());
    vi.mocked(useIsAuthenticated).mockReturnValue(true);
    vi.mocked(acquireAccessToken).mockResolvedValue("access-token");
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("exposes MSAL account state through the shared auth interface", async () => {
    renderWithProvider();

    expect(screen.getByTestId("provider").textContent).toBe("msal");
    expect(screen.getByTestId("authenticated").textContent).toBe(
      "authenticated",
    );
    expect(screen.getByTestId("loading").textContent).toBe("idle");
    expect(screen.getByTestId("username").textContent).toBe("user@example.com");
    expect(screen.getByTestId("user-id").textContent).toBe("member-oid");
    expect(screen.getByTestId("guest").textContent).toBe("member");

    await waitFor(() => {
      expect(mockMsalInstance.setActiveAccount).toHaveBeenCalledWith(
        mockAccount,
      );
    });
  });

  it("treats a string MSAL acct member claim as member", () => {
    vi.mocked(useMsal).mockReturnValue({
      ...createMsalContext(),
      accounts: [
        {
          ...mockAccount,
          idTokenClaims: {
            oid: "member-oid",
            acct: "0",
          },
        },
      ],
    });

    renderWithProvider();

    expect(screen.getByTestId("guest").textContent).toBe("member");
  });

  it("delegates login, logout, and token acquisition to MSAL", async () => {
    renderWithProvider();

    fireEvent.click(screen.getByText("login"));
    await waitFor(() => {
      expect(mockMsalInstance.loginRedirect).toHaveBeenCalledWith({
        scopes: ["api://nachet/scope"],
      });
    });

    fireEvent.click(screen.getByText("logout"));
    await waitFor(() => {
      expect(mockMsalInstance.logoutRedirect).toHaveBeenCalled();
    });

    fireEvent.click(screen.getByText("token"));
    await waitFor(() => {
      expect(acquireAccessToken).toHaveBeenCalledWith(
        mockMsalInstance,
        ["api://nachet/scope"],
        undefined,
      );
      expect(document.body.dataset.token).toBe("access-token");
    });
  });

  it("normalizes the configured provider name", () => {
    import.meta.env.VITE_AUTH_PROVIDER = " MSAL ";

    renderWithProvider();

    expect(screen.getByTestId("provider").textContent).toBe("msal");
  });

  it("fails closed when no auth provider is configured", () => {
    delete import.meta.env.VITE_AUTH_PROVIDER;

    expect(() => renderWithProvider()).toThrow(
      'VITE_AUTH_PROVIDER must be set to "msal" or "oidc".',
    );
  });

  it("does not start login while another MSAL interaction is in progress", async () => {
    vi.mocked(useMsal).mockReturnValue(
      createMsalContext(InteractionStatus.Login),
    );

    renderWithProvider();

    expect(screen.getByTestId("loading").textContent).toBe("loading");

    fireEvent.click(screen.getByText("login"));
    await waitFor(() => {
      expect(mockMsalInstance.loginRedirect).not.toHaveBeenCalled();
      expect(console.warn).toHaveBeenCalledWith(
        "Interaction already in progress, please wait",
      );
    });
  });

  it("selects the OIDC adapter when oidc is configured", () => {
    import.meta.env.VITE_AUTH_PROVIDER = "oidc";

    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/scope">
        <TestConsumer />
      </NachetAuthProvider>,
    );

    expect(screen.getByTestId("provider").textContent).toBe("oidc");
    expect(screen.getByTestId("username").textContent).toBe(
      "oidc-user@example.com",
    );
  });

  it("fails closed when an unsupported auth provider is configured", () => {
    import.meta.env.VITE_AUTH_PROVIDER = "unknown";

    expect(() =>
      render(
        <NachetAuthProvider
          apiScopeClaim="api://nachet/scope"
          msalInstance={mockPublicClientApplication}
        >
          <TestConsumer />
        </NachetAuthProvider>,
      ),
    ).toThrow('VITE_AUTH_PROVIDER must be set to "msal" or "oidc".');
  });
});
