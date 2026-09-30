/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

function strings() {
  const keys = {
    "site.runtime.search": "Search",
    "site.runtime.search_placeholder": "Search this collection",
    "site.runtime.search_mode": "Search mode",
    "site.runtime.keyword": "Keyword",
    "site.runtime.semantic": "Semantic",
    "site.runtime.hybrid": "Hybrid",
    "site.runtime.work_filter": "Work",
    "site.runtime.all_works": "All works",
    "site.runtime.field_filter": "Metadata field",
    "site.runtime.any_field": "Any metadata field",
    "site.runtime.filter_value": "Filter value",
    "site.runtime.works": "Works",
    "site.runtime.research": "Research",
    "site.runtime.annotations": "Annotations",
    "site.runtime.language": "Language",
    "site.runtime.theme": "Theme",
    "site.runtime.theme_light": "Light",
    "site.runtime.theme_dark": "Dark",
    "site.runtime.high_contrast": "High contrast",
    "site.runtime.tutorial": "Tutorial",
    "site.runtime.navigation": "Research site navigation",
    "site.runtime.display_controls": "Display and language controls",
    "site.runtime.skip_to_content": "Skip to main content",
    "site.runtime.site_title": "Research site",
    "site.runtime.powered_by_sdk": "Published with DerridAI",
    "site.runtime.publication_summary": "{works} works · {records} records · published {date}",
    "site.runtime.method_disclosure": "Technology used for this operation",
    "site.runtime.method_text": "Text search",
    "site.runtime.method_vector": "Vector search (embeddings)",
    "site.runtime.method_llm": "LLM answer generation",
    "site.runtime.method_on": "used",
    "site.runtime.method_off": "not used",
    "site.runtime.tutorial_welcome_title": "Welcome",
    "site.runtime.tutorial_welcome_body": "Learn how to use this research site.",
    "site.runtime.tutorial_search_title": "Search and inspect Records",
    "site.runtime.tutorial_search_body": "Use text, semantic, or hybrid search.",
    "site.runtime.tutorial_methods_title": "Know what the site is using",
    "site.runtime.tutorial_methods_body": "The site always identifies text, vector, and LLM use.",
    "site.runtime.tutorial_research_title": "Ask Research questions",
    "site.runtime.tutorial_research_body": "Research retrieves evidence before generation.",
    "site.runtime.tutorial_accessibility_title": "Language and accessibility",
    "site.runtime.tutorial_accessibility_body": "Use themes, high contrast, and keyboard controls.",
    "site.runtime.tutorial_progress": "Step {current} of {total}",
    "site.runtime.previous": "Previous",
    "site.runtime.next": "Next",
    "site.runtime.finish": "Finish",
    "site.runtime.skip_tutorial": "Skip tutorial",
    "site.runtime.records": "records",
  };
  return keys;
}

async function mountStaticSite(page: Page) {
  const sdkSource = await readFile(
    resolve(process.cwd(), "../api/app/site_assets/derridai-sdk.js"),
    "utf8",
  );
  const siteSource = await readFile(
    resolve(process.cwd(), "../api/app/site_assets/derridai-site.js"),
    "utf8",
  );
  const record = {
    record_id: "r1",
    source_document_id: "source-1",
    source_spans: [{ source_document_id: "source-1", source_unit_id: "unit-r1" }],
    work: "Glas",
    citation: "Derrida, Jacques. Glas.",
    text: "A publication-safe passage.",
  };
  const packageValue = {
    manifest: {
      format: "derridai-static-site-v3",
      publication_id: "sitepub-a11y",
      corpus_id: "test",
      created_at: "2026-09-30T12:00:00Z",
      title: "DerridAI accessibility fixture",
      description: "Static site accessibility fixture.",
      locale: "en-US",
      languages: [{ code: "en-US", name: "English", flag: "🇺🇸" }],
      works: [{ work: "Glas", record_count: 1, authors: ["Jacques Derrida"] }],
      vector_index: { dimension: null },
      source_collection: { filter_fields: ["work", "speaker"] },
      provider_profiles: [],
      features: {
        browse: true,
        lexical_search: true,
        semantic_search: false,
        local_annotations: true,
        research: true,
      },
      strings: { "en-US": strings() },
    },
    chunks: [
      {
        id: "work-1",
        work: "Glas",
        record_count: 1,
        records_b64: Buffer.from(JSON.stringify([record]), "utf8").toString("base64"),
        vector_ids: [],
        vectors_b64: "",
      },
    ],
  };

  await page.setContent('<main><div id="app" role="status" aria-live="polite">Loading…</div></main>');
  await page.evaluate((value) => {
    (window as typeof window & { __DERRIDAI_SITE_PACKAGE__?: unknown }).__DERRIDAI_SITE_PACKAGE__ = value;
  }, packageValue);
  await page.addScriptTag({ content: sdkSource });
  await page.addScriptTag({ content: siteSource });
  await expect(page.getByRole("dialog", { name: "Welcome" })).toBeVisible();
}

async function scan(page: Page) {
  const { violations } = await new AxeBuilder({ page }).withTags(TAGS).analyze();
  expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
}

for (const appearance of ["light", "dark", "high-contrast"] as const) {
  test(`published static site is WCAG 2.2 AA clean in ${appearance}`, async ({ page }) => {
    await mountStaticSite(page);
    await page.getByRole("button", { name: "Skip tutorial" }).click();
    await expect(page.getByRole("heading", { name: "Search" })).toBeVisible();

    if (appearance === "dark") {
      await page.getByLabel("Theme").selectOption("dark");
    } else if (appearance === "high-contrast") {
      await page.getByRole("checkbox", { name: "High contrast" }).check();
    }

    await scan(page);
  });
}

test("published tutorial is keyboard operable, skippable, and itself WCAG 2.2 AA clean", async ({
  page,
}) => {
  await mountStaticSite(page);
  const dialog = page.locator("dialog");
  await scan(page);
  await page.getByRole("button", { name: "Next" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Search and inspect Records" })).toBeVisible();

  for (let index = 0; index < 20; index += 1) await page.keyboard.press("Tab");
  expect(await dialog.evaluate((node) => node.contains(document.activeElement))).toBe(true);

  await page.getByRole("button", { name: "Skip tutorial" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    await page.evaluate(() => localStorage.getItem("derridai.site.tutorial.sitepub-a11y")),
  ).toBe("skipped");
});
