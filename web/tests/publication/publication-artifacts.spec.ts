/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test } from "@playwright/test";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

const artifactDir = process.env.DERRIDAI_PUBLICATION_ARTIFACT_DIR;

test("real single-file export works from file:// without an application server", async ({
  page,
}) => {
  if (!artifactDir) throw new Error("DERRIDAI_PUBLICATION_ARTIFACT_DIR is required.");

  const requests: string[] = [];
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("request", (request) => {
    if (/^https?:/i.test(request.url())) requests.push(request.url());
  });

  await page.goto(pathToFileURL(resolve(artifactDir, "local.html")).href);

  await expect(page.getByRole("dialog", { name: "Welcome" })).toBeVisible();
  await page.getByRole("button", { name: "Skip tutorial" }).click();
  await expect(page.getByRole("heading", { name: "Search" })).toBeVisible();

  const search = page.locator("section[aria-labelledby='search-heading']");
  await search.getByLabel("Search").fill("hospitality");
  await search.getByRole("button", { name: "Search" }).click();

  await expect(
    page.getByText("Hospitality exceeds conditional exchange in this acceptance fixture."),
  ).toBeVisible();
  await page.getByRole("button", { name: "View record" }).first().click();
  await expect(page.getByRole("dialog", { name: "Glas" })).toBeVisible();
  await expect(page.getByText("Derrida, Jacques. Glas. p. 12.")).toBeVisible();

  await page.getByLabel("Note").fill("Acceptance annotation");
  await page.getByLabel("Tags").fill("acceptance,publication");
  await page.getByRole("button", { name: "Save annotation" }).click();
  await expect(page.getByText("Annotation saved.")).toBeVisible();
  await page.getByRole("button", { name: "Close" }).click();

  await page.getByRole("button", { name: "Annotations" }).click();
  await expect(page.getByText("Acceptance annotation")).toBeVisible();
  await expect(page.getByText("acceptance", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Evidence is available without a generated answer.")).toBeVisible();
  await expect(page.getByRole("button", { name: /\[E1\] Glas/ })).toBeVisible();
  await expect(
    page.getByRole("group", { name: "Technology used for this operation" }),
  ).toContainText("Text search");

  // Direct provider networking is allowed when a visitor selects a provider.
  // This fixture exports no provider profile, so all baseline research behavior
  // must remain local and server-independent.
  expect(requests).toEqual([]);
  expect(pageErrors).toEqual([]);
});
