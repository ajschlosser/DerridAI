/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test } from "@playwright/test";
import { access } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

function fixturePath(): string {
  return resolve(
    process.env.DERRIDAI_PUBLICATION_FIXTURE_DIR || "../.tmp/publication-acceptance",
    "local.html",
  );
}

test("generated single-file publication works directly from file:// without an application server", async ({
  page,
}) => {
  const html = fixturePath();
  await access(html);

  const networkRequests: string[] = [];
  page.on("request", (request) => {
    if (/^https?:/i.test(request.url())) networkRequests.push(request.url());
  });

  await page.goto(pathToFileURL(html).href);
  await expect(page).toHaveTitle("DerridAI publication acceptance");
  await expect(page.getByRole("dialog", { name: "Welcome" })).toBeVisible();
  await page.getByRole("button", { name: "Skip tutorial" }).click();

  await page.getByLabel("Search").fill("hospitality");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("1 results")).toBeVisible();
  await expect(page.getByText("Hospitality exceeds the economy of conditional exchange.")).toBeVisible();

  await page.getByRole("button", { name: "View record" }).click();
  const recordDialog = page.getByRole("dialog", { name: "Glas" });
  await expect(recordDialog).toBeVisible();
  await expect(recordDialog).toContainText("Derrida, Jacques. Glas.");
  await recordDialog.getByLabel("Note").fill("Acceptance annotation");
  await recordDialog.getByLabel("Tags").fill("publication, acceptance");
  await recordDialog.getByRole("button", { name: "Save annotation" }).click();
  await expect(recordDialog.getByText("Annotation saved.")).toBeVisible();
  await recordDialog.getByRole("button", { name: "Close" }).click();

  await page.getByRole("button", { name: "Annotations" }).click();
  await expect(page.getByText("Acceptance annotation")).toBeVisible();

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByText("Evidence is available without a generated answer.")).toBeVisible();
  await expect(page.getByText("Hospitality exceeds the economy of conditional exchange.")).toBeVisible();

  expect(networkRequests).toEqual([]);
});
