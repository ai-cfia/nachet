import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import Footer from "../Footer";
import type { ModelLoadProgress } from "@stores/useInferenceStore";

const renderFooter = (props: {
  statusText?: string;
  isError?: boolean;
  isLoading?: boolean;
  loadProgress?: ModelLoadProgress | null;
} = {}) =>
  render(
    <I18nextProvider i18n={i18n}>
      <Footer {...props} />
    </I18nextProvider>,
  );

describe("Footer", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  describe("static content", () => {
    it('shows "Developed by AI Lab" text', async () => {
      renderFooter();
      await expect.element(page.getByText("Developed by AI Lab")).toBeVisible();
    });

    it("shows the Hugging Face logo image", async () => {
      renderFooter();
      await expect
        .element(page.getByRole("img", { name: "Hugging Face" }))
        .toBeVisible();
    });

    it("Hugging Face link points to the correct URL", async () => {
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Hugging Face" }))
        .toHaveAttribute("href", "https://huggingface.co/cfia-ai-lab");
    });

    it("GitHub link points to the ai-cfia org", () => {
      renderFooter();
      const link = page
        .getByTestId("GitHubIcon")
        .element()
        .closest("a") as HTMLAnchorElement;
      expect(link?.href).toContain("github.com/ai-cfia");
    });

    it('shows "Report an Issue" link', async () => {
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Report an Issue" }))
        .toBeVisible();
    });

    it('"Report an Issue" link points to the correct URL', async () => {
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Report an Issue" }))
        .toHaveAttribute("href", "https://github.com/ai-cfia/nachet/issues");
    });

    it('shows "Privacy Policy" link', async () => {
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Privacy Policy" }))
        .toBeVisible();
    });

    it('"Privacy Policy" link points to the correct URL', async () => {
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Privacy Policy" }))
        .toHaveAttribute(
          "href",
          "https://github.com/ai-cfia/nachet/blob/main/nachet-mini/src/common/privacy.md",
        );
    });

    it("shows the app version", async () => {
      renderFooter();
      await expect.element(page.getByText("Version: 0.9.6")).toBeVisible();
    });

    it("all external links open in a new tab", async () => {
      renderFooter();
      const links = page.getByRole("link");
      for (const link of await links.all()) {
        await expect.element(link).toHaveAttribute("target", "_blank");
      }
    });
  });

  describe("statusText prop", () => {
    it("shows no status text by default", async () => {
      renderFooter();
      expect(await page.getByText("Model loading...").all()).toHaveLength(0);
    });

    it("shows the provided statusText", async () => {
      renderFooter({ statusText: "Model loading..." });
      await expect.element(page.getByText("Model loading...")).toBeVisible();
    });
  });

  describe("isError prop", () => {
    it("statusText color differs between error and normal states", () => {
      renderFooter({ statusText: "Status", isError: true });
      const errorColor = getComputedStyle(
        page.getByText("Status").element(),
      ).color;
      cleanup();
      renderFooter({ statusText: "Status", isError: false });
      const normalColor = getComputedStyle(
        page.getByText("Status").element(),
      ).color;
      expect(errorColor).not.toBe(normalColor);
    });
  });

  describe("load progress", () => {
    it("does not show progress bar when isLoading is false", async () => {
      renderFooter({
        statusText: "Loading",
        isLoading: false,
        loadProgress: { name: "detector", progress: 50 },
      });
      expect(await page.getByRole("progressbar").all()).toHaveLength(0);
    });

    it("does not show progress bar when loadProgress is null", async () => {
      renderFooter({ statusText: "Loading", isLoading: true, loadProgress: null });
      expect(await page.getByRole("progressbar").all()).toHaveLength(0);
    });

    it("shows progress bar when isLoading and loadProgress are provided", async () => {
      renderFooter({
        statusText: "Loading model",
        isLoading: true,
        loadProgress: { name: "detector", progress: 75 },
      });
      await expect.element(page.getByRole("progressbar")).toBeVisible();
    });

    it("shows the model name in the progress display", async () => {
      renderFooter({
        statusText: "Loading model",
        isLoading: true,
        loadProgress: { name: "detector", progress: 75 },
      });
      await expect.element(page.getByText(/detector/)).toBeVisible();
    });

    it("shows the rounded progress percentage", async () => {
      renderFooter({
        statusText: "Loading model",
        isLoading: true,
        loadProgress: { name: "detector", progress: 75.7 },
      });
      await expect.element(page.getByText(/76%/)).toBeVisible();
    });
  });

  describe("i18n", () => {
    it('shows French "developedBy" text', async () => {
      await i18n.changeLanguage("fr");
      renderFooter();
      await expect
        .element(page.getByText("Développé par le laboratoire d’IA"))
        .toBeVisible();
    });

    it('shows French "Report an Issue" text', async () => {
      await i18n.changeLanguage("fr");
      renderFooter();
      await expect
        .element(page.getByRole("link", { name: "Signaler un problème" }))
        .toBeVisible();
    });

    it('shows French "Privacy Policy" text', async () => {
      await i18n.changeLanguage("fr");
      renderFooter();
      await expect
        .element(
          page.getByRole("link", { name: "Politique de confidentialité" }),
        )
        .toBeVisible();
    });
  });
});
