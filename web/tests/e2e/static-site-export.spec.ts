/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test } from "@playwright/test";
import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";

function fixturePath(name = "local.html"): string {
  return resolve(
    process.env.DERRIDAI_PUBLICATION_FIXTURE_DIR || "../.tmp/publication-acceptance",
    name,
  );
}

test("single-file export works directly from file://", async ({ page }) => {
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
  await expect(page.getByRole("dialog")).not.toBeVisible();

  const searchRegion = page.getByRole("region", { name: "Search" });
  await searchRegion.getByRole("searchbox", { name: "Search" }).fill("hospitality");
  await searchRegion.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("1 results")).toBeVisible();
  await expect(
    page.getByText("Hospitality exceeds the economy of conditional exchange."),
  ).toBeVisible();

  await page.getByRole("button", { name: "View record" }).click();
  const recordDialog = page.getByRole("dialog", { name: "Glas" });
  await expect(recordDialog).toBeVisible();
  await expect(recordDialog).toContainText("Derrida, Jacques. Glas.");
  await recordDialog.getByLabel("Note").fill("Acceptance annotation");
  await recordDialog.getByLabel("Tags").fill("publication, acceptance");
  await recordDialog.getByRole("button", { name: "Save annotation" }).click();
  await recordDialog.getByRole("button", { name: "Close" }).click();

  await page.getByRole("button", { name: "Annotations" }).click();
  await expect(page.getByText("Acceptance annotation")).toBeVisible();

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(
    page.getByText(
      "The evidence packet is available below. No answer-generation capability is currently available.",
    ),
  ).toBeVisible();
  const evidenceRegion = page.getByRole("region", { name: "Evidence" });
  await expect(evidenceRegion.getByRole("button", { name: /\[E1\] Glas/ })).toBeVisible();

  expect(networkRequests).toEqual([]);
});

test("same-origin provider paths resolve against the served publication origin", async ({
  page,
}) => {
  const html = await readFile(fixturePath("local-provider.html"), "utf-8");
  const providerRequests: string[] = [];

  await page.route("https://site.example.test/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/") {
      await route.fulfill({ status: 200, contentType: "text/html", body: html });
      return;
    }
    if (url.pathname === "/provider/models") {
      providerRequests.push(url.pathname);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ data: [{ id: "gpt-oss:20b" }] }),
      });
      return;
    }
    if (url.pathname === "/provider/chat/completions") {
      providerRequests.push(url.pathname);
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          choices: [
            { message: { content: "Answer generated through the same-origin proxy." } },
          ],
        }),
      });
      return;
    }
    await route.abort();
  });

  await page.goto("https://site.example.test/");
  await page.getByRole("button", { name: "Skip tutorial" }).click();

  await page.getByRole("button", { name: "Models", exact: true }).click();
  const form = page.getByRole("form", { name: "Add an endpoint" });
  await form.getByLabel("Name", { exact: true }).fill("Same-origin proxy");
  await form.getByLabel("Endpoint URL").fill("/provider");
  await form.getByLabel("Model", { exact: true }).fill("gpt-oss:20b");
  await form.getByLabel("Use for embeddings").uncheck();
  await form.getByLabel("Use for Research answers").check();
  await form.getByRole("button", { name: "Save endpoint" }).click();

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Answer generated through the same-origin proxy.")).toBeVisible();
  expect(providerRequests).toContain("/provider/chat/completions");
});

test("single-file export preserves evidence when reader-configured providers are unreachable", async ({
  page,
}) => {
  const html = fixturePath("local-provider.html");
  await access(html);

  const providerRequests: string[] = [];
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("https://models.example.test/v1/**", async (route) => {
    providerRequests.push(route.request().url());
    await route.abort("connectionrefused");
  });

  await page.goto(pathToFileURL(html).href);
  await expect(page.getByRole("dialog", { name: "Welcome" })).toBeVisible();
  await page.getByRole("button", { name: "Skip tutorial" }).click();

  const addEndpoint = async (
    name: string,
    model: string,
    roles: Array<"embeddings" | "answers">,
  ) => {
    await page.getByRole("button", { name: "Models", exact: true }).click();
    const form = page.getByRole("form", { name: "Add an endpoint" });
    await form.getByLabel("Name", { exact: true }).fill(name);
    await form.getByLabel("Endpoint URL").fill("https://models.example.test/v1");
    await form.getByLabel("Model", { exact: true }).fill(model);
    if (roles.includes("embeddings")) await form.getByLabel("Use for embeddings").check();
    else await form.getByLabel("Use for embeddings").uncheck();
    if (roles.includes("answers")) await form.getByLabel("Use for Research answers").check();
    else await form.getByLabel("Use for Research answers").uncheck();
    await form.getByRole("button", { name: "Save endpoint" }).click();
  };

  await addEndpoint("Acceptance embedder", "bge-m3:latest", ["embeddings"]);
  await addEndpoint("Acceptance writer", "gpt-oss:20b", ["answers"]);

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(
    page.getByText(
      "The evidence packet is available below. No answer-generation capability is currently available.",
    ),
  ).toBeVisible();
  const evidenceRegion = page.getByRole("region", { name: "Evidence" });
  await expect(evidenceRegion.getByRole("button", { name: /\[E1\] Glas/ })).toBeVisible();

  expect(providerRequests.some((url) => url.endsWith("/embeddings"))).toBe(true);
  expect(providerRequests.some((url) => url.endsWith("/chat/completions"))).toBe(true);
  expect(pageErrors).toEqual([]);
});
