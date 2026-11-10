import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import AuthPopup from "../AuthPopup";

const { auth } = vi.hoisted(() => ({
  auth: {
    isAuthenticated: false,
    isLoading: false,
    login: vi.fn(),
  },
}));

vi.mock("@auth", () => ({
  useNachetAuth: () => auth,
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

describe("AuthPopup", () => {
  beforeEach(() => {
    auth.isAuthenticated = false;
    auth.isLoading = false;
    auth.login.mockReset();
  });

  it("allows sign-in and closing with Escape when idle", () => {
    const onClose = vi.fn();
    render(<AuthPopup open onClose={onClose} />);

    fireEvent.click(screen.getByRole("button", { name: "auth.signInButton" }));
    expect(auth.login).toHaveBeenCalledOnce();

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("prevents closing with Escape while sign-in is in progress", () => {
    auth.isLoading = true;
    const onClose = vi.fn();
    render(<AuthPopup open onClose={onClose} />);

    expect(screen.getByText("auth.signingIn")).toBeTruthy();
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).not.toHaveBeenCalled();
  });
});
