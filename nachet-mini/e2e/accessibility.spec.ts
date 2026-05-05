import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const wcagTags = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

test("Nachet Mini has no automatically detectable WCAG A/AA issues on load", async ({
  page,
}, testInfo) => {
  await page.goto("/");

  const results = await new AxeBuilder({ page }).withTags(wcagTags).analyze();

  await testInfo.attach("accessibility-scan-results", {
    body: JSON.stringify(results, null, 2),
    contentType: "application/json",
  });

  expect(results.violations).toEqual([]);
});
