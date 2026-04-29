import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import AppBar from "../AppBar";

const renderAppBar = () =>
  render(
    <I18nextProvider i18n={i18n}>
      <AppBar />
    </I18nextProvider>,
  );

const getLanguageSwitch = () =>
  page.getByLabelText(
    /toggle language between english and french|basculer la langue entre l'anglais et le francais/i,
  );

describe("AppBar", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  describe("rendering", () => {
    it("renders the app title as a heading", async () => {
      renderAppBar();
      await expect
        .element(page.getByRole("heading", { name: "Nachet Mini", level: 2 }))
        .toBeVisible();
    });

    it("renders a labeled language switch with both language labels", async () => {
      renderAppBar();
      await expect.element(page.getByText("EN")).toBeVisible();
      await expect.element(page.getByText("FR")).toBeVisible();
      await expect.element(getLanguageSwitch()).toBeVisible();
    });
  });

  describe("language toggle state", () => {
    it("renders the switch unchecked when the active language is English", async () => {
      renderAppBar();
      await expect.element(getLanguageSwitch()).not.toBeChecked();
    });

    it("renders the switch checked when the active language is French", async () => {
      await i18n.changeLanguage("fr");
      renderAppBar();
      await expect.element(getLanguageSwitch()).toBeChecked();
    });
  });

  describe("language toggle interaction", () => {
    it("clicking the switch toggles to French and persists the language", async () => {
      renderAppBar();
      await getLanguageSwitch().click();
      await expect.element(getLanguageSwitch()).toBeChecked();
      expect(i18n.language).toBe("fr");
      expect(localStorage.getItem("i18nextLng")).toBe("fr");
    });

    it("clicking the switch twice returns to English and persists the language", async () => {
      renderAppBar();
      await getLanguageSwitch().click();
      await getLanguageSwitch().click();
      await expect.element(getLanguageSwitch()).not.toBeChecked();
      expect(i18n.language).toBe("en");
      expect(localStorage.getItem("i18nextLng")).toBe("en");
    });
  });
});
