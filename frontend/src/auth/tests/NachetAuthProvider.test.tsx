import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InteractionStatus } from "@azure/msal-browser";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { acquireAccessToken } from "../../common/auth";
import { NachetAuthProvider, useNachetAuth } from "../";

vi.mock("@azure/msal-react");
vi.mock("../../common/auth");

const mockAccount = {
  homeAccountId: "home-account-id",
  environment: "login.microsoftonline.com",
  tenantId: "tenant-id",
  localAccountId: "local-account-id",
  username: "user@example.com",
  name: "Test User",
  idTokenClaims: {
    acct: 0,
  },
};

function TestConsumer() {
  const auth = useNachetAuth();

  return (
    <div>
      <span data-testid="provider">{auth.provider}</span>
      <span data-testid="authenticated">
        {auth.isAuthenticated ? "authenticated" : "anonymous"}
      </span>
      <span data-testid="loading">{auth.isLoading ? "loading" : "idle"}</span>
      <span data-testid="username">{auth.activeAccount?.username ?? ""}</span>
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
}

describe("NachetAuthProvider", () => {
  const mockMsalInstance = {
    getActiveAccount: vi.fn(),
    setActiveAccount: vi.fn(),
    loginRedirect: vi.fn(),
    logoutRedirect: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    delete document.body.dataset.token;
    import.meta.env.VITE_AUTH_PROVIDER = "msal";

    mockMsalInstance.getActiveAccount.mockReturnValue(null);
    mockMsalInstance.loginRedirect.mockResolvedValue(undefined);
    mockMsalInstance.logoutRedirect.mockResolvedValue(undefined);

    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.None,
      accounts: [mockAccount],
    });
    (useIsAuthenticated as any).mockReturnValue(true);
    (acquireAccessToken as any).mockResolvedValue("access-token");
    vi.spyOn(console, "warn").mockImplementation(() => {});
  });

  it("exposes MSAL account state through the shared auth interface", async () => {
    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/scope">
        <TestConsumer />
      </NachetAuthProvider>,
    );

    expect(screen.getByTestId("provider").textContent).toBe("msal");
    expect(screen.getByTestId("authenticated").textContent).toBe(
      "authenticated",
    );
    expect(screen.getByTestId("loading").textContent).toBe("idle");
    expect(screen.getByTestId("username").textContent).toBe("user@example.com");

    await waitFor(() => {
      expect(mockMsalInstance.setActiveAccount).toHaveBeenCalledWith(
        mockAccount,
      );
    });
  });

  it("delegates login, logout, and token acquisition to MSAL", async () => {
    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/scope">
        <TestConsumer />
      </NachetAuthProvider>,
    );

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
      expect(acquireAccessToken).toHaveBeenCalledWith(mockMsalInstance, [
        "api://nachet/scope",
      ]);
      expect(document.body.dataset.token).toBe("access-token");
    });
  });

  it("normalizes the configured provider name", () => {
    import.meta.env.VITE_AUTH_PROVIDER = " MSAL ";

    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/scope">
        <TestConsumer />
      </NachetAuthProvider>,
    );

    expect(screen.getByTestId("provider").textContent).toBe("msal");
  });

  it("does not start login while another MSAL interaction is in progress", async () => {
    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.Login,
      accounts: [mockAccount],
    });

    render(
      <NachetAuthProvider apiScopeClaim="api://nachet/scope">
        <TestConsumer />
      </NachetAuthProvider>,
    );

    expect(screen.getByTestId("loading").textContent).toBe("loading");

    fireEvent.click(screen.getByText("login"));
    await waitFor(() => {
      expect(mockMsalInstance.loginRedirect).not.toHaveBeenCalled();
      expect(console.warn).toHaveBeenCalledWith(
        "Interaction already in progress, please wait",
      );
    });
  });

  it("fails closed when an unsupported auth provider is configured", () => {
    import.meta.env.VITE_AUTH_PROVIDER = "oidc";

    expect(() =>
      render(
        <NachetAuthProvider apiScopeClaim="api://nachet/scope">
          <TestConsumer />
        </NachetAuthProvider>,
      ),
    ).toThrow("Unsupported auth provider 'oidc'");
  });
});
