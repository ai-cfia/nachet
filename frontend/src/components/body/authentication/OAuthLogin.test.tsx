import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import "@testing-library/jest-dom";
import { MsalProvider } from "@azure/msal-react";
import { PublicClientApplication } from "@azure/msal-browser";
import OAuthLogin from "./OAuthLogin";
import { AuthProvider } from "../../../common/auth/AuthContext";

// Mock MSAL configuration
const mockMsalConfig = {
  auth: {
    clientId: "test-client-id",
    authority: "https://login.microsoftonline.com/test-tenant",
    redirectUri: "http://localhost:3000",
  },
  cache: {
    cacheLocation: "memory",
    storeAuthStateInCookie: false,
  },
};

// Create mock MSAL instance
const mockMsalInstance = new PublicClientApplication(mockMsalConfig);

// Mock the loginPopup method
const mockLoginPopup = vi.fn();
mockMsalInstance.loginPopup = mockLoginPopup;

describe("OAuthLogin Component", () => {
  const mockSetSignUpOpen = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders OAuth login dialog", () => {
    render(
      <MsalProvider instance={mockMsalInstance}>
        <AuthProvider>
          <OAuthLogin setSignUpOpen={mockSetSignUpOpen} />
        </AuthProvider>
      </MsalProvider>,
    );

    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sign in with your organizational account to access Nachet",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Sign in with Microsoft" }),
    ).toBeInTheDocument();
  });

  it("closes dialog when close button is clicked", () => {
    render(
      <MsalProvider instance={mockMsalInstance}>
        <AuthProvider>
          <OAuthLogin setSignUpOpen={mockSetSignUpOpen} />
        </AuthProvider>
      </MsalProvider>,
    );

    const closeButton = screen.getByRole("button", { name: "" }); // Close icon button
    fireEvent.click(closeButton);

    expect(mockSetSignUpOpen).toHaveBeenCalledWith(false);
  });

  it("triggers login when Sign in with Microsoft button is clicked", async () => {
    mockLoginPopup.mockResolvedValue({});

    render(
      <MsalProvider instance={mockMsalInstance}>
        <AuthProvider>
          <OAuthLogin setSignUpOpen={mockSetSignUpOpen} />
        </AuthProvider>
      </MsalProvider>,
    );

    const loginButton = screen.getByRole("button", {
      name: "Sign in with Microsoft",
    });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(mockLoginPopup).toHaveBeenCalledWith({
        scopes: ["openid", "profile", "email"],
      });
    });
  });

  it("handles login errors gracefully", async () => {
    const consoleErrorSpy = vi
      .spyOn(console, "error")
      .mockImplementation(() => {});
    mockLoginPopup.mockRejectedValue(new Error("Login failed"));

    render(
      <MsalProvider instance={mockMsalInstance}>
        <AuthProvider>
          <OAuthLogin setSignUpOpen={mockSetSignUpOpen} />
        </AuthProvider>
      </MsalProvider>,
    );

    const loginButton = screen.getByRole("button", {
      name: "Sign in with Microsoft",
    });
    fireEvent.click(loginButton);

    await waitFor(() => {
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Login failed:",
        expect.any(Error),
      );
    });

    consoleErrorSpy.mockRestore();
  });
});
