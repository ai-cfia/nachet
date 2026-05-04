import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import enCommon from "../../locales/en/common";
import frCommon from "../../locales/fr/common";
import { useVersionCheckStore } from "@stores/useVersionCheckStore";
import { versions } from "../../_versions";
import VersionCheckDialog from "../VersionCheckDialog";

vi.mock("@stores/useVersionCheckStore", () => ({
  useVersionCheckStore: vi.fn(),
}));

type VersionCheckState = ReturnType<(typeof useVersionCheckStore)["getState"]>;

const mockCloseDialog = vi.fn();

const setStore = (overrides: Partial<VersionCheckState> = {}) => {
  const state: VersionCheckState = {
    remoteVersion: null,
    dialogOpen: true,
    setRemoteVersion: vi.fn(),
    openDialog: vi.fn(),
    closeDialog: mockCloseDialog,
    ...overrides,
  };
  vi.mocked(useVersionCheckStore).mockImplementation(
    (selector: (s: VersionCheckState) => unknown) => selector(state),
  );
};

const mockReload = vi.fn();

const renderDialog = () =>
  render(
    <I18nextProvider i18n={i18n}>
      <VersionCheckDialog onReload={mockReload} />
    </I18nextProvider>,
  );

const versionMessage = (remote: string) =>
  i18n.t("versionDialog.message", {
    ns: "main",
    current: versions.version,
    remote,
  });

describe("VersionCheckDialog", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
    mockCloseDialog.mockClear();
    mockReload.mockClear();
    setStore();
  });

  afterEach(cleanup);

  describe("when closed", () => {
    it("does not render dialog content when dialogOpen is false", async () => {
      setStore({ dialogOpen: false });
      renderDialog();
      expect(await page.getByRole("dialog").all()).toHaveLength(0);
    });
  });

  describe("when open", () => {
    it("renders the dialog", async () => {
      setStore({ dialogOpen: true, remoteVersion: "1.0.0" });
      renderDialog();
      await expect.element(page.getByRole("dialog")).toBeVisible();
    });

    it("renders the title", async () => {
      setStore({ dialogOpen: true, remoteVersion: "1.0.0" });
      renderDialog();
      await expect
        .element(page.getByText(enMain.versionDialog.title))
        .toBeVisible();
    });

    it("renders the warning text", async () => {
      setStore({ dialogOpen: true, remoteVersion: "1.0.0" });
      renderDialog();
      await expect
        .element(page.getByText(enMain.versionDialog.warning))
        .toBeVisible();
    });

    it("renders the message with current and remote versions", async () => {
      setStore({ dialogOpen: true, remoteVersion: "9.9.9" });
      renderDialog();
      await expect
        .element(page.getByText(versionMessage("9.9.9")))
        .toBeVisible();
    });

    it("renders the message with empty remote when remoteVersion is null", async () => {
      setStore({ dialogOpen: true, remoteVersion: null });
      renderDialog();
      await expect.element(page.getByText(versionMessage(""))).toBeVisible();
    });

    it("renders the Reload button", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("button", { name: enMain.versionDialog.reload }),
        )
        .toBeVisible();
    });

    it("renders both a close icon button and a close text button", async () => {
      renderDialog();
      const closeButtons = await page
        .getByRole("button", { name: enCommon.actions.close })
        .all();
      expect(closeButtons).toHaveLength(2);
    });
  });

  describe("close interactions", () => {
    it("calls closeDialog when the close icon button is clicked", async () => {
      renderDialog();
      const closeIcon = document.querySelector(
        '[data-testid="version-dialog-close-icon"]',
      ) as HTMLButtonElement;
      closeIcon.click();
      expect(mockCloseDialog).toHaveBeenCalledOnce();
    });

    it("calls closeDialog when the Close text button is clicked", async () => {
      renderDialog();
      const closeButton = document.querySelector(
        '[data-testid="version-dialog-close-button"]',
      ) as HTMLButtonElement;
      closeButton.click();
      expect(mockCloseDialog).toHaveBeenCalledOnce();
    });

    it("calls closeDialog when Escape is pressed", async () => {
      renderDialog();
      await userEvent.keyboard("{Escape}");
      expect(mockCloseDialog).toHaveBeenCalledOnce();
    });
  });

  describe("reload interaction", () => {
    it("calls onReload when the Reload button is clicked", async () => {
      renderDialog();
      await page
        .getByRole("button", { name: enMain.versionDialog.reload })
        .click();
      expect(mockReload).toHaveBeenCalledOnce();
      expect(mockCloseDialog).not.toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("the dialog is labelled by the title element", async () => {
      renderDialog();
      const dialog = page.getByRole("dialog").element();
      const labelledBy = dialog.getAttribute("aria-labelledby");
      expect(labelledBy).toBe("version-check-dialog-title");
      expect(document.getElementById(labelledBy as string)?.textContent).toBe(
        enMain.versionDialog.title,
      );
    });

    it("the dialog is described by the message element", async () => {
      setStore({ dialogOpen: true, remoteVersion: "2.0.0" });
      renderDialog();
      const dialog = page.getByRole("dialog").element();
      const describedBy = dialog.getAttribute("aria-describedby");
      expect(describedBy).toBe("version-check-dialog-description");
      expect(document.getElementById(describedBy as string)?.textContent).toBe(
        versionMessage("2.0.0"),
      );
    });

    it("the close icon button has an accessible label", async () => {
      renderDialog();
      const closeButtons = await page
        .getByRole("button", { name: enCommon.actions.close })
        .all();
      const iconBtn = closeButtons[0].element() as HTMLButtonElement;
      expect(iconBtn.getAttribute("aria-label")).toBe(enCommon.actions.close);
    });
  });

  describe("i18n", () => {
    it("renders the French title in French mode", async () => {
      await i18n.changeLanguage("fr");
      setStore({ dialogOpen: true, remoteVersion: "1.0.0" });
      renderDialog();
      await expect
        .element(page.getByText(frMain.versionDialog.title))
        .toBeVisible();
    });

    it("renders the French warning in French mode", async () => {
      await i18n.changeLanguage("fr");
      setStore({ dialogOpen: true, remoteVersion: "1.0.0" });
      renderDialog();
      await expect
        .element(page.getByText(frMain.versionDialog.warning))
        .toBeVisible();
    });

    it("renders the French Reload button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(
          page.getByRole("button", { name: frMain.versionDialog.reload }),
        )
        .toBeVisible();
    });

    it("renders the French Close button label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      const closeButtons = await page
        .getByRole("button", { name: frCommon.actions.close })
        .all();
      expect(closeButtons).toHaveLength(2);
    });

    it("interpolates the version values into the French message", async () => {
      await i18n.changeLanguage("fr");
      setStore({ dialogOpen: true, remoteVersion: "3.2.1" });
      renderDialog();
      await expect
        .element(page.getByText(versionMessage("3.2.1")))
        .toBeVisible();
    });
  });
});
