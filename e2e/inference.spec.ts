import { test, expect } from '@playwright/test';

test('inference succeeeds', async ({ page }) => {
  await page.goto('http://localhost:12436/');
  await page.getByRole('button', { name: 'I Agree' }).click();
  await page.getByRole('button', { name: 'Capture', exact: true }).click();
  await page.getByRole('button', { name: 'LOAD' }).click();
  await page.getByRole('button', { name: 'Choose File' }).click();
  await page.getByRole('button', { name: 'Choose File' }).setInputFiles('e2e/files/ambrosia_psilostachya.tiff');
  await page.getByRole('button', { name: 'MODEL SELECTION' }).click();
  await page.getByRole('button', { name: 'Done' }).click();
  await page.getByRole('button', { name: 'CLASSIFY' }).click();
  await page.waitForTimeout(5000); // Wait 5 seconds for processing to start
  await expect(page.getByRole('cell', { name: 'Ambrosia psilostachya' })).toBeVisible({ timeout: 90000 });
//   await page.screenshot({ path: 'debug.png' });
});
