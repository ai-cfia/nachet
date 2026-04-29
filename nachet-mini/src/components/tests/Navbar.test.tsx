import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enHeader from "../../locales/en/header";
import frHeader from "../../locales/fr/header";
import Navbar from "../Navbar";

const renderNavbar = () =>
  render(
    <I18nextProvider i18n={i18n}>
      <Navbar />
    </I18nextProvider>,
  );

describe("Navbar", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  it("renders a nav landmark", async () => {
    renderNavbar();
    await expect.element(page.getByRole("navigation")).toBeVisible();
  });

  it("renders the logo image with the correct alt text", async () => {
    renderNavbar();
    await expect
      .element(page.getByRole("img", { name: enHeader.navbar.logoAlt }))
      .toBeVisible();
  });

  it("wraps the logo in a link to inspection.canada.ca", async () => {
    renderNavbar();
    await expect
      .element(page.getByRole("link", { name: enHeader.navbar.logoAlt }))
      .toHaveAttribute("href", "https://inspection.canada.ca");
  });

  it("opens the link in a new tab", async () => {
    renderNavbar();
    await expect
      .element(page.getByRole("link", { name: enHeader.navbar.logoAlt }))
      .toHaveAttribute("target", "_blank");
  });

  it("sets safe rel attributes on the external link", async () => {
    renderNavbar();
    await expect
      .element(page.getByRole("link", { name: enHeader.navbar.logoAlt }))
      .toHaveAttribute("rel", "noopener noreferrer");
  });

  it("renders exactly one linked logo in the navigation landmark", async () => {
    renderNavbar();
    expect(await page.getByRole("link").all()).toHaveLength(1);
    expect(await page.getByRole("img").all()).toHaveLength(1);
    await expect
      .element(page.getByRole("link", { name: enHeader.navbar.logoAlt }))
      .toBeVisible();
  });

  it("uses the French logo alt text as the link name in French mode", async () => {
    await i18n.changeLanguage("fr");
    renderNavbar();
    await expect
      .element(page.getByRole("link", { name: frHeader.navbar.logoAlt }))
      .toBeVisible();
  });
});
