import { StrictMode } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "./AuthProvider";
import { useAuth } from "./useAuth";

const mockUserManager = vi.hoisted(() => {
  const removeEventListener = () => undefined;
  const addEventListener = () => removeEventListener;

  return {
    signinCallback: vi.fn(),
    getUser: vi.fn(),
    signinRedirect: vi.fn(),
    signinSilent: vi.fn(),
    signoutRedirect: vi.fn(),
    removeUser: vi.fn(),
    clearStaleState: vi.fn(),
    events: {
      addUserLoaded: addEventListener,
      addUserUnloaded: addEventListener,
      addUserSignedOut: addEventListener,
      addSilentRenewError: addEventListener,
    },
  };
});

vi.mock("oidc-client-ts", () => ({
  UserManager: vi.fn(function UserManager() {
    return mockUserManager;
  }),
}));

const AuthState = () => {
  const auth = useAuth();
  let label = "signed-out";
  if (auth.isLoading) {
    label = "loading";
  } else if (auth.isAuthenticated) {
    label = "authenticated";
  }

  return <div data-testid="auth-state">{label}</div>;
};

describe("AuthProvider", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/");
    vi.clearAllMocks();
    mockUserManager.signinCallback.mockResolvedValue({
      expired: false,
      profile: { sub: "local-user" },
    });
    mockUserManager.getUser.mockResolvedValue(null);
  });

  it("exchanges an authorization code once in React StrictMode", async () => {
    window.history.replaceState({}, "", "/?code=test-code&state=test-state");

    render(
      <StrictMode>
        <AuthProvider
          authority="https://idp.example/realms/nachet"
          client_id="nachet-frontend"
          redirect_uri="http://localhost:5173"
        >
          <AuthState />
        </AuthProvider>
      </StrictMode>,
    );

    await waitFor(() => {
      expect(mockUserManager.signinCallback).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId("auth-state").textContent).toBe(
        "authenticated",
      );
    });
  });
});
