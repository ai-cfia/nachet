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

describe("AppBar", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  describe("rendering", () => {
    it("displays the app title", async () => {
      renderAppBar();
      await expect.element(page.getByText("Nachet Mini")).toBeVisible();
    });

    it("displays EN language label", async () => {
      renderAppBar();
      await expect.element(page.getByText("EN")).toBeVisible();
    });

    it("displays FR language label", async () => {
      renderAppBar();
      await expect.element(page.getByText("FR")).toBeVisible();
    });

    it("renders a language toggle switch", async () => {
      renderAppBar();
      await expect.element(page.getByRole("switch")).toBeVisible();
    });
  });

  describe("language toggle state", () => {
    it("switch is unchecked when language is English", async () => {
      renderAppBar();
      await expect.element(page.getByRole("switch")).not.toBeChecked();
    });

    it("switch is checked when language is French", async () => {
      await i18n.changeLanguage("fr");
      renderAppBar();
      await expect.element(page.getByRole("switch")).toBeChecked();
    });
  });

  describe("language toggle interaction", () => {
    it("clicking the switch toggles to French", async () => {
      renderAppBar();
      await page.getByRole("switch").click();
      await expect.element(page.getByRole("switch")).toBeChecked();
    });

    it("clicking the switch twice returns to English", async () => {
      renderAppBar();
      await page.getByRole("switch").click();
      await page.getByRole("switch").click();
      await expect.element(page.getByRole("switch")).not.toBeChecked();
    });

    it("i18n language is French after clicking the switch", async () => {
      renderAppBar();
      await page.getByRole("switch").click();
      expect(i18n.language).toBe("fr");
    });

    it("i18n language returns to English after clicking the switch twice", async () => {
      renderAppBar();
      await page.getByRole("switch").click();
      await page.getByRole("switch").click();
      expect(i18n.language).toBe("en");
    });
  });

  describe("active language label font weight", () => {
    it("EN label is bold in English mode", () => {
      renderAppBar();
      const el = page.getByText("EN").element();
      expect(getComputedStyle(el).fontWeight).toBe("700");
    });

    it("FR label is normal weight in English mode", () => {
      renderAppBar();
      const el = page.getByText("FR").element();
      expect(getComputedStyle(el).fontWeight).toBe("400");
    });

    it("FR label is bold in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderAppBar();
      const el = page.getByText("FR").element();
      expect(getComputedStyle(el).fontWeight).toBe("700");
    });

    it("EN label is normal weight in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderAppBar();
      const el = page.getByText("EN").element();
      expect(getComputedStyle(el).fontWeight).toBe("400");
    });
  });
});
