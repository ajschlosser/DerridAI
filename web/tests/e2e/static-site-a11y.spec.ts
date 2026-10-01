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
    "site.runtime.tutorial_welcome_body": "About welcome.",
    "site.runtime.tutorial_nav_title": "Four workspaces",
    "site.runtime.tutorial_nav_body": "About four workspaces.",
    "site.runtime.tutorial_works_title": "Works: the published texts",
    "site.runtime.tutorial_works_body": "About works: the published texts.",
    "site.runtime.tutorial_search_title": "Search and inspect Records",
    "site.runtime.tutorial_search_body": "About search and inspect records.",
    "site.runtime.tutorial_filters_title": "Search mode and filters",
    "site.runtime.tutorial_filters_body": "About search mode and filters.",
    "site.runtime.tutorial_methods_title": "Know what the site is using",
    "site.runtime.tutorial_methods_body": "About know what the site is using.",
    "site.runtime.tutorial_research_title": "Ask Research questions",
    "site.runtime.tutorial_research_body": "About ask research questions.",
    "site.runtime.tutorial_provider_title": "Optional language-model provider",
    "site.runtime.tutorial_provider_body": "About optional language-model provider.",
    "site.runtime.tutorial_evidence_title": "Evidence and citations",
    "site.runtime.tutorial_evidence_body": "About evidence and citations.",
    "site.runtime.tutorial_notes_title": "Your annotations",
    "site.runtime.tutorial_notes_body": "About your annotations.",
    "site.runtime.tutorial_controls_title": "Language and accessibility",
    "site.runtime.tutorial_controls_body": "About language and accessibility.",
    "site.runtime.tutorial_restart_title": "Replay this tour any time",
    "site.runtime.tutorial_restart_body": "About replay this tour any time.",
    "site.runtime.tutorial_hint": "Use Next and Previous, or the arrow keys.",
    "site.runtime.tutorial_progress": "Step {current} of {total}",
    "site.runtime.previous": "Previous",
    "site.runtime.next": "Next",
    "site.runtime.finish": "Finish",
    "site.runtime.skip_tutorial": "Skip tutorial",
    "site.runtime.records": "records",
    "site.runtime.provider_settings": "Provider settings",
    "site.runtime.provider_profile": "Provider profile",
    "site.runtime.provider_none": "No direct provider",
    "site.runtime.provider_none_help": "No direct provider selected.",
    "site.runtime.provider_openai": "OpenAI-compatible",
    "site.runtime.provider_ollama": "Ollama",
    "site.runtime.provider_summary": "{type} · model {model} · {endpoint}",
    "site.runtime.not_configured": "Not configured",
    "site.runtime.api_key": "API key",
    "site.runtime.api_key_session": "Optional API key",
    "site.runtime.api_key_help": "Kept only in this tab.",
    "site.runtime.apply_provider": "Use this provider",
    "site.runtime.test_provider": "Test connection",
    "site.runtime.provider_applying": "Applying provider…",
    "site.runtime.provider_applied": "Provider applied.",
    "site.runtime.provider_apply_failed": "Could not apply provider: {error}",
    "site.runtime.provider_select_required": "Select a provider first.",
    "site.runtime.provider_endpoint_missing": "Provider endpoint missing.",
    "site.runtime.provider_endpoint_invalid": "Provider endpoint invalid.",
    "site.runtime.provider_model_missing": "Model {model} was not reported.",
    "site.runtime.provider_ready": "Provider connection ready.",
    "site.runtime.provider_test_failed": "Provider test failed: {error}",
    "site.runtime.no_exported_providers": "No provider profiles were exported.",
    "site.runtime.question": "Question",
    "site.runtime.question_placeholder": "Ask a research question",
    "site.runtime.ask": "Ask",
    "site.runtime.evidence": "Evidence",
    "site.runtime.research_tools": "Research tools and evidence",
    "site.runtime.activity_research_hybrid":
      "Research: text + vector retrieval before LLM synthesis.",
    "site.runtime.activity_research_text": "Research: text retrieval before LLM synthesis.",
    "site.runtime.activity_vector_embedding": "Vector search: creating a query embedding.",
    "site.runtime.activity_llm_generation": "LLM: generating an answer.",
    "site.runtime.complete": "Research complete.",
    "site.runtime.complete_with_warning": "Research complete with warning: {warning}",
    "site.runtime.no_evidence": "No evidence found.",
    "site.runtime.generation_unavailable_evidence":
      "Evidence is available without a generated answer.",
    "site.runtime.sdk_generation_unavailable":
      "LLM generation is unavailable; evidence remains available.",
    "site.runtime.sdk_embedding_unavailable": "Embedding provider unavailable.",
    "site.runtime.sdk_embedding_contract_mismatch": "Embedding contract mismatch.",
    "site.runtime.sdk_embedding_dimension_mismatch": "Embedding dimension mismatch.",
    "site.runtime.results_count": "{count} results",
    "site.runtime.results_with_warning": "{count} results · {warning}",
    "site.runtime.no_results": "No results",
    "site.runtime.search_failed": "Search failed: {error}",
    "site.runtime.research_failed": "Research failed: {error}",
    "site.runtime.activity_text_search": "Text search.",
    "site.runtime.activity_vector_search": "Vector search.",
    "site.runtime.activity_hybrid_search": "Text + vector search.",
    "site.runtime.loading_progress": "{stage} {current}/{total} · {work}",
    "site.runtime.loading_vectors": "Loading vectors",
    "site.runtime.loading_records": "Loading records",
    "site.runtime.view_record": "View record",
    "site.runtime.close": "Close",
    "site.runtime.add_annotation": "Add annotation",
    "site.runtime.quotation": "Quotation",
    "site.runtime.quote_placeholder": "Quotation",
    "site.runtime.note": "Note",
    "site.runtime.note_placeholder": "Note",
    "site.runtime.tags": "Tags",
    "site.runtime.tags_placeholder": "Tags",
    "site.runtime.save_annotation": "Save annotation",
    "site.runtime.annotation_saved": "Annotation saved.",
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
      format: "derridai-static-site-v4",
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

  await page.setContent(
    '<main><div id="app" role="status" aria-live="polite">Loading…</div></main>',
  );
  await page.evaluate((value) => {
    (window as typeof window & { __DERRIDAI_SITE_PACKAGE__?: unknown }).__DERRIDAI_SITE_PACKAGE__ =
      value;
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

test("published site reflows at 320 CSS pixels and exposes a working skip link", async ({
  page,
}) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await mountStaticSite(page);
  await page.getByRole("button", { name: "Skip tutorial" }).click();

  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to main content" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#site-main")).toBeFocused();

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
  await scan(page);
});

test("published site remains accessible with forced colors active", async ({ page }) => {
  await page.emulateMedia({ forcedColors: "active", reducedMotion: "reduce" });
  await mountStaticSite(page);
  await page.getByRole("button", { name: "Skip tutorial" }).click();
  await scan(page);
});

test("published tutorial is keyboard operable, skippable, and itself WCAG 2.2 AA clean", async ({
  page,
}) => {
  await mountStaticSite(page);
  const dialog = page.locator("dialog");
  await scan(page);
  await page.getByRole("button", { name: "Next" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Four workspaces" })).toBeVisible();

  for (let index = 0; index < 20; index += 1) await page.keyboard.press("Tab");
  expect(await dialog.evaluate((node) => node.contains(document.activeElement))).toBe(true);

  await page.getByRole("button", { name: "Skip tutorial" }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Tutorial" })).toBeVisible();
  await page.getByRole("button", { name: "Tutorial" }).click();
  await expect(page.getByRole("dialog", { name: "Welcome" })).toBeVisible();
  await page.getByRole("button", { name: "Skip tutorial" }).click();
});

test("guided tour spotlights each real element, switches views, and restores the page", async ({
  page,
}) => {
  // Reduced motion removes the spotlight glide so its geometry can be measured immediately.
  await page.emulateMedia({ reducedMotion: "reduce" });
  await mountStaticSite(page);
  const dialog = page.getByRole("dialog");
  const spot = page.locator(".tour-spot");
  const card = page.locator(".tour-card");
  const next = page.getByRole("button", { name: "Next" });

  // Welcome has no target: a centered card over a fully dimmed page.
  await expect(dialog).toHaveAccessibleName("Welcome");
  await expect(spot).toBeHidden();
  await next.click();

  const overlaps = async (selector: string) => {
    const target = await page.locator(selector).first().boundingBox();
    const ring = await spot.boundingBox();
    const box = await card.boundingBox();
    expect(target && ring && box).toBeTruthy();
    // The spotlight encloses the target, and the card never covers the highlighted element.
    expect(ring!.x).toBeLessThanOrEqual(target!.x);
    expect(ring!.y).toBeLessThanOrEqual(target!.y);
    expect(ring!.x + ring!.width).toBeGreaterThanOrEqual(target!.x + target!.width - 1);
    const disjoint =
      box!.x + box!.width <= ring!.x ||
      ring!.x + ring!.width <= box!.x ||
      box!.y + box!.height <= ring!.y ||
      ring!.y + ring!.height <= box!.y;
    expect(disjoint).toBe(true);
  };

  await expect(dialog).toHaveAccessibleName("Four workspaces");
  await expect(spot).toBeVisible();
  await overlaps("nav[data-tour=nav]");

  await next.click();
  await expect(dialog).toHaveAccessibleName("Works: the published texts");
  await overlaps("[data-tour=works]");

  await next.click();
  await expect(dialog).toHaveAccessibleName("Search and inspect Records");
  await overlaps("[data-tour=search]");

  await next.click();
  await expect(dialog).toHaveAccessibleName("Search mode and filters");
  await next.click();
  await expect(dialog).toHaveAccessibleName("Know what the site is using");
  await overlaps("[data-tour=methods]");

  // Arrow keys move through the tour as well.
  await page.keyboard.press("ArrowRight");
  await expect(dialog).toHaveAccessibleName("Ask Research questions");
  await page.keyboard.press("ArrowLeft");
  await expect(dialog).toHaveAccessibleName("Know what the site is using");
  await page.keyboard.press("ArrowRight");

  for (const name of [
    "Optional language-model provider",
    "Evidence and citations",
    "Your annotations",
    "Language and accessibility",
    "Replay this tour any time",
  ]) {
    await next.click();
    await expect(dialog).toHaveAccessibleName(name);
    await expect(spot).toBeVisible();
  }
  await scan(page);

  await page.getByRole("button", { name: "Finish" }).click();
  await expect(page.locator("dialog.tour")).toHaveCount(0);
  // The tour wandered through Works, Research, and Annotations; the reader is back on Search.
  await expect(page.getByRole("button", { name: "Search", exact: true }).first()).toHaveAttribute(
    "aria-current",
    "page",
  );
  await expect(page.getByRole("heading", { name: "Search" })).toBeVisible();
});

test("guided tour is dismissed with Escape, remembered, and fits a phone screen", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.setViewportSize({ width: 360, height: 640 });
  await mountStaticSite(page);
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();
  await page.getByRole("button", { name: "Next" }).click();

  const box = await page.locator(".tour-card").boundingBox();
  expect(box!.x).toBeGreaterThanOrEqual(0);
  expect(box!.x + box!.width).toBeLessThanOrEqual(360);
  expect(box!.y + box!.height).toBeLessThanOrEqual(640);
  const ring = await page.locator(".tour-spot").boundingBox();
  // The docked card never covers the highlighted element, whichever side it docks on.
  expect(ring!.y + ring!.height <= box!.y + 1 || box!.y + box!.height <= ring!.y + 1).toBe(true);

  await page.keyboard.press("Escape");
  await expect(page.locator("dialog.tour")).toHaveCount(0);

  // Reopened from the button, the tour returns focus to that button when it closes.
  await page.getByRole("button", { name: "Tutorial" }).click();
  await expect(page.getByRole("dialog")).toHaveAccessibleName("Welcome");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: "Tutorial" })).toBeFocused();
});

test("exported OpenAI profile powers vector + LLM Research with method disclosure", async ({
  page,
}) => {
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
    text: "Hospitality exceeds the economy of conditional exchange.",
    speaker: "Derrida",
    position_holder: "Derrida",
    stance: "argues",
  };
  const vector = Buffer.alloc(8);
  vector.writeFloatLE(1, 0);
  vector.writeFloatLE(0, 4);
  const packageValue = {
    manifest: {
      format: "derridai-static-site-v4",
      publication_id: "sitepub-provider",
      corpus_id: "test",
      created_at: "2026-09-30T12:00:00Z",
      title: "Provider fixture",
      locale: "en-US",
      languages: [{ code: "en-US", name: "English", flag: "🇺🇸" }],
      works: [{ work: "Glas", record_count: 1, authors: ["Jacques Derrida"] }],
      vector_index: {
        dimension: 2,
        model: "bge-m3:latest",
        distance_metric: "cosine",
        text_field: "text",
      },
      source_collection: { filter_fields: ["work", "speaker"] },
      provider_profiles: [
        {
          id: "openai-main",
          name: "Research endpoint",
          type: "openai",
          base_url: "https://models.example.test/v1",
          model: "gpt-oss:20b",
          has_api_key: true,
        },
      ],
      features: {
        browse: true,
        lexical_search: true,
        semantic_search: true,
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
        vector_ids: ["r1"],
        vectors_b64: vector.toString("base64"),
      },
    ],
  };

  await page.route("https://models.example.test/v1/**", async (route) => {
    const request = route.request();
    const headers = {
      "access-control-allow-origin": "*",
      "access-control-allow-headers": "authorization,content-type",
      "access-control-allow-methods": "GET,POST,OPTIONS",
      "content-type": "application/json",
    };
    if (request.method() === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
      return;
    }
    if (request.url().endsWith("/embeddings")) {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({ data: [{ embedding: [1, 0] }] }),
      });
      return;
    }
    if (request.url().endsWith("/chat/completions")) {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          choices: [{ message: { content: "Hospitality exceeds conditional exchange [E1]." } }],
        }),
      });
      return;
    }
    if (request.url().endsWith("/models")) {
      await route.fulfill({
        status: 200,
        headers,
        body: JSON.stringify({
          data: [{ id: "gpt-oss:20b" }, { id: "bge-m3:latest" }],
        }),
      });
      return;
    }
    await route.fulfill({ status: 404, headers, body: "{}" });
  });

  await page.setContent('<div id="app" role="status" aria-live="polite">Loading…</div>');
  await page.evaluate((value) => {
    (window as typeof window & { __DERRIDAI_SITE_PACKAGE__?: unknown }).__DERRIDAI_SITE_PACKAGE__ =
      value;
  }, packageValue);
  await page.addScriptTag({ content: sdkSource });
  await page.addScriptTag({ content: siteSource });
  await page.getByRole("button", { name: "Skip tutorial" }).click();

  await page.getByRole("button", { name: "Research" }).click();
  await page.getByLabel("Provider profile").selectOption("openai-main");
  await page.getByRole("button", { name: "Use this provider" }).click();
  await expect(page.getByLabel("Question")).toBeVisible();

  await page.getByLabel("Question").fill("What does the passage say about hospitality?");
  await page.getByRole("button", { name: "Ask" }).click();

  await expect(page.getByText("Hospitality exceeds conditional exchange [E1].")).toBeVisible();
  const methods = page.getByRole("group", { name: "Technology used for this operation" });
  await expect(methods).toContainText("Text search");
  await expect(methods).toContainText("Vector search (embeddings)");
  await expect(methods).toContainText("LLM answer generation");
  await expect(methods).not.toContainText("not used");
  await scan(page);
});
