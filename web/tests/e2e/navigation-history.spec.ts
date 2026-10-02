/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

// The router is the only navigation history: the breadcrumb Back/Forward buttons walk it, and they keep
// working after the sidebar has been used to move between pages.
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

test("breadcrumb Back and Forward walk the router history", async ({ page }, testInfo) => {
  test.skip(
    testInfo.project.name !== "chromium-desktop",
    "Navigation history is viewport-independent.",
  );
  await mockBackend(page, { role: "admin" });
  await page.goto(APP + "/");

  const back = page.getByRole("button", { name: "Back" });
  const forward = page.getByRole("button", { name: "Forward" });
  const sidebar = page.locator(".shell-sidebar");
  await expect(back).toBeDisabled();

  await sidebar.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page).toHaveURL(/\/search/);
  await sidebar.getByRole("button", { name: "Works", exact: true }).click();
  await expect(page).toHaveURL(/\/works/);
  await expect(back).toBeEnabled();
  await expect(forward).toBeDisabled();

  await back.click();
  await expect(page).toHaveURL(/\/search/);
  await expect(forward).toBeEnabled();

  await forward.click();
  await expect(page).toHaveURL(/\/works/);

  // Navigation is still live afterwards.
  await sidebar.getByRole("button", { name: "Home", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
});
