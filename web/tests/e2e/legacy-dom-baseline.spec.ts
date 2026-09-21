/* Copyright 2026 Aaron John Schlosser, PhD. */
import { createHash } from "node:crypto";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { mockBackend, type Fixtures, type Role } from "./support/mock-backend";

// Characterization baseline for the views that the legacy runtime still renders as HTML strings.
// Vue-native workspaces (Records, Search, Vector Stores, Works, and so on) are not listed here.
// The runtime decomposition must not change what these views put on the page, so each one is
// captured as normalized markup and compared with a committed snapshot. If a refactoring step
// changes a snapshot, that step has changed the UI and must be fixed, not the snapshot.
//
// Snapshots are desktop-only, matching playwright.legacy.config.ts.
// To regenerate after an intentional UI change: npx playwright test -c playwright.legacy.config.ts --update-snapshots
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

const RECORDS = [
  {
    record_id: "derrida-grammatology-00001",
    work: "Of Grammatology",
    document_author: "Jacques Derrida",
    year: 1967,
    page_start: 3,
    page_end: 3,
    text: "The sign and divinity have the same place and time of birth.",
    speaker: "Derrida",
    topics: ["sign", "presence"],
    concepts: ["logocentrism"],
    needs_review: false,
  },
  {
    record_id: "derrida-grammatology-00002",
    work: "Of Grammatology",
    document_author: "Jacques Derrida",
    year: 1967,
    page_start: 4,
    page_end: 6,
    text: "There is nothing outside the text.",
    speaker: "Derrida",
    topics: ["text"],
    needs_review: true,
    review_reason: "Quotation boundary uncertain",
  },
  {
    record_id: "derrida-cosmopoli-00001",
    work: "On Cosmopolitanism and Forgiveness",
    document_author: "Jacques Derrida",
    year: 2001,
    page_start: 5,
    page_end: 5,
    text: "What then would such a concept be?",
    topics: ["hospitality"],
    needs_review: false,
  },
];

/** Fixed clock and random source, and no animation, so the markup is the same on every run. */
async function stabilize(page: Page, scheme: "light" | "dark") {
  await page.addInitScript((value) => {
    // The dashboard picks a random record and re-renders a variable number of times as data arrives.
    Math.random = () => 0;
    localStorage.setItem("derridai.ui.scheme", value);
  }, scheme);
  await page.emulateMedia({ reducedMotion: "reduce", colorScheme: scheme });
  await page.clock.setFixedTime(new Date("2026-03-01T12:00:00Z"));
}

interface Scenario {
  name: string;
  /** In-app navigation, as a person would do it, after the app has started. */
  nav?: string;
  role?: Role;
  scheme?: "light" | "dark";
  /** Load the sample JSONL file before navigating (admin only). */
  load?: boolean;
  fixtures?: Fixtures;
  /** Interactions that reach the state, after navigation. */
  steps?: (page: Page) => Promise<void>;
  /** What to capture: the page's main region (default) or the open dialog. */
  target?: "main" | "dialog";
  /** Record computed styles instead of markup, to guard colors, fonts and spacing in each theme. */
  styles?: boolean;
}

async function open(page: Page, scenario: Scenario) {
  await stabilize(page, scenario.scheme ?? "light");
  await mockBackend(page, { role: scenario.role ?? "admin", fixtures: scenario.fixtures });
  await page.goto(APP + "/");
  await expect(page.locator("#main")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  // The runtime restores the saved workspace while it starts. Loading a file before that finishes
  // would let the restore overwrite it, so wait for the start-up requests to settle first.
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  if (scenario.load) {
    await page.setInputFiles("#fileInput", {
      name: "baseline.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(SAMPLE_TEXT),
    });
    await expect(page.getByText("Loaded 3 records")).toBeVisible({ timeout: 10_000 });
  }
  // The runtime picks its view from in-app navigation, so go there the way a person would.
  if (scenario.nav && scenario.nav !== "Home") {
    // The sidebar entry; the top bar has its own "Search" button.
    await page
      .locator("nav, aside")
      .getByRole("button", { name: scenario.nav, exact: true })
      .first()
      .click();
  }
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
  await scenario.steps?.(page);
}

/** Copy of an element's markup without the timing-dependent tooltip wrapper the runtime adds to disabled controls. */
async function rawMarkup(page: Page, target: "main" | "dialog"): Promise<string> {
  const locator =
    target === "dialog" ? page.locator("dialog[open]").last() : page.locator("main").first();
  const html = await locator.evaluate((el) => {
    const copy = el.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(".disabled-control-tooltip").forEach((wrap) => {
      const tip = wrap.getAttribute("data-tooltip");
      wrap.querySelectorAll("[title]").forEach((node) => {
        if (node.getAttribute("title") === tip) node.removeAttribute("title");
      });
      wrap.replaceWith(...wrap.childNodes);
    });
    return copy.outerHTML;
  });
  return (
    html
      .replace(/></g, ">\n<")
      .replace(/\s+(style="[^"]*")/g, " $1")
      // Scoped-style hashes change whenever a component's source does, and mean nothing to a person.
      .replace(/ data-v-[0-9a-f]{8}=""/g, "")
      .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g, "<uuid>")
      .replace(/\b\d{1,2}\/\d{1,2}\/\d{4},? \d{1,2}:\d{2}(:\d{2})?( [AP]M)?/g, "<date>")
  );
}

const STYLE_PROPERTIES = [
  "display",
  "color",
  "background-color",
  "border-top-color",
  "border-top-width",
  "border-radius",
  "font-size",
  "font-weight",
  "font-family",
  "line-height",
  "padding",
  "margin",
  "text-transform",
  "opacity",
];

/** One line per element under the target: its tag and classes, then the computed style values that do not depend on layout. */
async function computedStyles(page: Page, target: "main" | "dialog"): Promise<string> {
  const locator =
    target === "dialog" ? page.locator("dialog[open]").last() : page.locator("main").first();
  return locator.evaluate((root, properties) => {
    const lines: string[] = [];
    const walk = (el: Element, depth: number) => {
      // The runtime wraps disabled controls in a tooltip span at a timing-dependent moment; look through it.
      if (el.classList.contains("disabled-control-tooltip")) {
        for (const child of Array.from(el.children)) walk(child, depth);
        return;
      }
      const style = getComputedStyle(el);
      const label = `${el.tagName.toLowerCase()}${[...el.classList].map((c) => `.${c}`).join("")}`;
      lines.push(
        `${" ".repeat(depth)}${label} | ${properties.map((p) => `${p}:${style.getPropertyValue(p)}`).join("; ")}`,
      );
      for (const child of Array.from(el.children)) walk(child, depth + 1);
    };
    walk(root, 0);
    return lines.join("\n");
  }, STYLE_PROPERTIES);
}

/** Waits until the markup stops changing, because Vue views load their data after they mount. */
async function markup(page: Page, target: "main" | "dialog"): Promise<string> {
  let last = await rawMarkup(page, target);
  let stableFor = 0;
  for (let i = 0; i < 40 && stableFor < 4; i++) {
    await page.waitForTimeout(200);
    const next = await rawMarkup(page, target);
    stableFor = next === last ? stableFor + 1 : 0;
    last = next;
  }
  return last;
}

/** Clicks a control and waits for the runtime dialog it opens. */
const clickThenDialog = (find: (page: Page) => Locator) => async (page: Page) => {
  await find(page).click();
  await expect(page.locator("dialog[open]").last()).toBeVisible();
};

/** Opens the first work's Actions menu and runs one of the actions in it. */
const worksAction = (name: RegExp | string) => async (page: Page) => {
  await page.locator("main summary", { hasText: "Actions" }).first().click();
  await page.getByRole("button", { name }).first().click();
};

const inRecords = async (page: Page) => {
  await page.getByRole("button", { name: "Records", exact: true }).click();
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
};
const openDialogFromRecords =
  (button: RegExp | string, options: { secondFile?: boolean } = {}) =>
  async (page: Page) => {
    if (options.secondFile) {
      await page.setInputFiles("#fileInput", {
        name: "second.jsonl",
        mimeType: "application/x-ndjson",
        buffer: Buffer.from(
          JSON.stringify({ ...RECORDS[0], record_id: "second-00001", work: "Glas" }),
        ),
      });
      await expect(page.getByText("Loaded 1 records")).toBeVisible({ timeout: 10_000 });
    }
    await inRecords(page);
    const target = page.getByRole("button", { name: button }).first();
    // Some commands live in the "More" menu.
    if (!(await target.isVisible())) {
      const menus = page.locator("summary", { hasText: "More" });
      for (let i = 0; i < (await menus.count()) && !(await target.isVisible()); i++)
        await menus.nth(i).click();
    }
    await target.click();
    await expect(page.locator("dialog[open]").last()).toBeVisible();
  };

const JOBS = {
  jobs: [
    {
      id: "job-rag-1",
      type: "rag",
      status: "running",
      stage: "retrieval",
      stage_detail: "fetching passages",
      source_collection: "derrida_primary",
      model: "qwen3.5:4b",
      provider: "ollama",
      owner: "admin",
      created_at: "2026-03-01T11:50:00Z",
      started_at: "2026-03-01T11:50:05Z",
      total: 10,
      completed: 4,
      request: { locales: ["en"], k: 8, fetch_k: 50 },
    },
    {
      id: "job-llm-1",
      type: "llm",
      status: "completed",
      mode: "review",
      model: "qwen3.5:4b",
      fields: ["topics"],
      owner: "admin",
      created_at: "2026-03-01T11:00:00Z",
      started_at: "2026-03-01T11:00:05Z",
      finished_at: "2026-03-01T11:04:00Z",
      total: 6,
      completed: 6,
      pending_result_count: 2,
      pending_change_count: 3,
    },
    {
      id: "job-pdf-1",
      type: "pdf_corpus",
      status: "failed",
      source_filename: "grammatology.pdf",
      stage: "segmenting",
      fatal_error: "Source could not be read",
      owner: "admin",
      created_at: "2026-03-01T10:00:00Z",
      started_at: "2026-03-01T10:00:05Z",
      finished_at: "2026-03-01T10:01:00Z",
      total: 4,
      completed: 1,
    },
  ],
};

/** The runtime names a loaded file by a digest of its text, and review results point at records through that name. */
const SAMPLE_TEXT = RECORDS.map((r) => JSON.stringify(r)).join("\n");
const SAMPLE_FILE_ID = `jsonl-${createHash("sha256").update(SAMPLE_TEXT).digest("hex").slice(0, 24)}`;

const FINISHED_JOBS = {
  jobs: [
    {
      id: "job-rag-1",
      type: "rag",
      status: "completed",
      stage: "done",
      source_collection: "derrida_primary",
      model: "qwen3.5:4b",
      provider: "ollama",
      owner: "admin",
      created_at: "2026-03-01T11:50:00Z",
      started_at: "2026-03-01T11:50:05Z",
      finished_at: "2026-03-01T11:51:00Z",
      total: 10,
      completed: 10,
      result: {
        answer: "An answer.",
        prompt: "What is a trace?",
        model: "qwen3.5:4b",
        sources: [],
      },
      request: { locales: ["en"], k: 8 },
    },
    {
      id: "job-llm-1",
      type: "llm",
      status: "completed",
      mode: "review",
      model: "qwen3.5:4b",
      fields: ["topics"],
      owner: "admin",
      created_at: "2026-03-01T11:00:00Z",
      started_at: "2026-03-01T11:00:05Z",
      finished_at: "2026-03-01T11:04:00Z",
      total: 6,
      completed: 6,
      pending_result_count: 2,
      pending_change_count: 3,
      results: [
        {
          key: `${SAMPLE_FILE_ID}::0`,
          record_id: "derrida-grammatology-00001",
          proposal: {
            changes: { topics: ["sign", "trace"], speaker: "Derrida" },
            rationale: { topics: "The passage is about the trace." },
          },
        },
        {
          key: `${SAMPLE_FILE_ID}::1`,
          record_id: "derrida-grammatology-00002",
          proposal: { changes: {} },
        },
        {
          key: `${SAMPLE_FILE_ID}::2`,
          record_id: "derrida-cosmopoli-00001",
          error: "Model timed out",
        },
      ],
    },
    {
      id: "job-pdf-1",
      type: "pdf_corpus",
      status: "failed",
      source_filename: "grammatology.pdf",
      stage: "segmenting",
      fatal_error: "Source could not be read",
      owner: "admin",
      created_at: "2026-03-01T10:00:00Z",
      started_at: "2026-03-01T10:00:05Z",
      finished_at: "2026-03-01T10:01:00Z",
      total: 4,
      completed: 1,
    },
  ],
};

/** The job list, and the per-job endpoint the details and results dialogs read. */
const jobFixtures = (payload: { jobs: Array<{ id: string }> }): Fixtures => ({
  "/api/jobs": payload,
  ...Object.fromEntries(payload.jobs.map((job) => [`/api/jobs/${job.id}`, job])),
});

const scenarios: Scenario[] = [
  // The dashboard is the one view still drawn by the runtime through RuntimeSurface.
  { name: "home-empty" },
  { name: "home-loaded", load: true },
  { name: "styles-home-light", load: true, styles: true },
  { name: "styles-home-dark", load: true, scheme: "dark", styles: true },
  { name: "home-researcher", role: "researcher" },
  { name: "home-with-jobs", load: true, fixtures: jobFixtures(JOBS) },
  {
    name: "home-metric-next",
    load: true,
    steps: async (page) => {
      await page.locator("#dashMetricNext").click();
    },
  },
  {
    name: "home-metric-next-twice",
    load: true,
    steps: async (page) => {
      await page.locator("#dashMetricNext").click();
      await page.locator("#dashMetricNext").click();
    },
  },
  { name: "research-empty", nav: "Research" },
  // PDF Explorer is drawn by the runtime inside the Corpus Builder workspace.
  {
    name: "pdf-explorer-empty",
    nav: "Corpus Builder",
    steps: async (page) => {
      await page.getByRole("button", { name: /PDF Explorer/ }).click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(600);
    },
  },
  // Dialogs the runtime builds as HTML strings, reached from the Records commands.
  {
    name: "dialog-merge",
    load: true,
    target: "dialog",
    steps: openDialogFromRecords("Merge files", { secondFile: true }),
  },
  {
    name: "dialog-subset",
    load: true,
    target: "dialog",
    steps: openDialogFromRecords("Create subset"),
  },
  {
    name: "styles-dialog-subset-dark",
    load: true,
    scheme: "dark",
    target: "dialog",
    styles: true,
    steps: openDialogFromRecords("Create subset"),
  },
  // Job dialogs, opened from the Operations panel on the dashboard.
  ...[0, 1, 2].map(
    (index): Scenario => ({
      name: `dialog-job-details-${index}`,
      load: true,
      target: "dialog",
      fixtures: jobFixtures(FINISHED_JOBS),
      steps: clickThenDialog((page) => page.getByRole("button", { name: "Details" }).nth(index)),
    }),
  ),
  {
    name: "dialog-job-results-review",
    load: true,
    target: "dialog",
    fixtures: jobFixtures(FINISHED_JOBS),
    steps: clickThenDialog((page) => page.getByRole("button", { name: "Review results" }).first()),
  },
  // Export, and the collection wizard from Vector Stores.
  { name: "dialog-export", load: true, target: "dialog", steps: openDialogFromRecords("Export") },
  {
    name: "dialog-collection-wizard-source",
    nav: "Vector Stores",
    load: true,
    target: "dialog",
    steps: clickThenDialog((page) => page.getByRole("button", { name: "New" }).first()),
  },
  {
    name: "dialog-collection-wizard-retrieval",
    nav: "Vector Stores",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await clickThenDialog((p) => p.getByRole("button", { name: "New" }).first())(page);
      await page.locator("dialog[open] #wizardCollectionName").fill("baseline-collection");
      await page.locator("dialog[open] #wizardNext").click();
      await expect(page.locator("dialog[open] #wizardCollectionRole")).toBeVisible();
    },
  },
  // Works dialogs.
  {
    name: "dialog-works-populate-all",
    nav: "Works",
    load: true,
    target: "dialog",
    steps: clickThenDialog((page) => page.getByRole("button", { name: /Populate all metadata/ })),
  },
  {
    name: "dialog-works-separate",
    nav: "Works",
    load: true,
    target: "dialog",
    steps: clickThenDialog((page) => page.getByRole("button", { name: "Separate works" })),
  },
  {
    name: "dialog-ocr-cleanup",
    load: true,
    target: "dialog",
    steps: openDialogFromRecords("Clean OCR Artifacts"),
  },
  // Computed styles for more of the runtime-drawn surfaces.
  {
    name: "styles-dialog-job-results-dark",
    load: true,
    scheme: "dark",
    styles: true,
    target: "dialog",
    fixtures: jobFixtures(FINISHED_JOBS),
    steps: clickThenDialog((page) => page.getByRole("button", { name: "Review results" }).first()),
  },
  {
    name: "styles-dialog-wizard-dark",
    nav: "Vector Stores",
    load: true,
    scheme: "dark",
    styles: true,
    target: "dialog",
    steps: clickThenDialog((page) => page.getByRole("button", { name: "New" }).first()),
  },
  {
    name: "styles-pdf-explorer-light",
    nav: "Corpus Builder",
    styles: true,
    steps: async (page) => {
      await page.getByRole("button", { name: /PDF Explorer/ }).click();
      await page.waitForLoadState("networkidle");
      await page.waitForTimeout(600);
    },
  },
  { name: "styles-home-researcher-dark", role: "researcher", scheme: "dark", styles: true },
  // The Search view is Vue, but every command it sends and every result it shows goes through the runtime.
  { name: "search-loaded", nav: "Search", load: true },
  {
    name: "search-query",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.getByPlaceholder(/Search extracted text/).fill("text");
      await page.waitForTimeout(900);
    },
  },
  {
    name: "search-facet-topic",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.locator("summary", { hasText: "Topics" }).click();
      await page.locator("details", { hasText: "Topics" }).getByRole("checkbox").first().check();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "search-sort-page",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.locator("summary", { hasText: "Sort:" }).click();
      await page.getByRole("button", { name: "Page Start" }).first().click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "search-layout-cards",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.getByRole("button", { name: "Cards" }).click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "search-advanced-filter",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.locator("summary", { hasText: "Search options" }).click();
      await page.getByPlaceholder("Type or choose a value…").fill("Of Grammatology");
      await page.getByRole("button", { name: "Add filter" }).click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "search-select-record",
    nav: "Search",
    load: true,
    steps: async (page) => {
      await page.getByRole("checkbox", { name: /^Select derrida-grammatology-00001/ }).check();
      await page.waitForTimeout(700);
    },
  },
  // The Records view is Vue, but its rows, sorting, filtering and selection all come from the runtime.
  { name: "records-loaded", nav: "Records", load: true },
  {
    name: "records-query",
    nav: "Records",
    load: true,
    steps: async (page) => {
      await page.getByPlaceholder("Search text in this file").fill("text");
      await page.waitForTimeout(900);
    },
  },
  {
    name: "records-sort-work",
    nav: "Records",
    load: true,
    steps: async (page) => {
      await page.locator("button.records-sort", { hasText: "Work" }).click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "records-sort-work-descending",
    nav: "Records",
    load: true,
    steps: async (page) => {
      const sort = page.locator("button.records-sort", { hasText: "Work" });
      await sort.click();
      await page.waitForTimeout(400);
      await sort.click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "records-select-row",
    nav: "Records",
    load: true,
    steps: async (page) => {
      await page
        .getByRole("checkbox", { name: /^Select /i })
        .nth(1)
        .check();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "records-select-all",
    nav: "Records",
    load: true,
    steps: async (page) => {
      const target = page.getByRole("button", { name: "Select all" }).first();
      const menus = page.locator("summary", { hasText: "More" });
      for (let i = 0; i < (await menus.count()) && !(await target.isVisible()); i++)
        await menus.nth(i).click();
      await target.click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "records-columns-dialog",
    nav: "Records",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await page.getByRole("button", { name: "Columns" }).click();
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  // The Record view is Vue, but the record it shows, navigation, evidence and edits all come from the runtime.
  { name: "record-loaded", nav: "Record View", load: true },
  {
    name: "record-next",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByRole("button", { name: /Next record/ }).click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "record-find",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByPlaceholder(/Find in record/i).fill("outside");
      await page.waitForTimeout(700);
    },
  },
  {
    name: "record-add-evidence",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByRole("button", { name: "Add evidence" }).first().click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "record-add-to-selection",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.locator("summary", { hasText: "•••" }).click();
      await page.getByText("Add to selection", { exact: true }).click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "record-tab-provenance",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByRole("tab", { name: "Provenance" }).click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "record-tab-annotations",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByRole("tab", { name: "Annotations" }).click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "record-tab-history",
    nav: "Record View",
    load: true,
    steps: async (page) => {
      await page.getByRole("tab", { name: "History" }).click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "record-edit-sheet",
    nav: "Record View",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await page.getByRole("button", { name: "Edit record" }).click();
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  // The Works view is Vue, but the works, their overview and every action it offers come from the runtime.
  { name: "works-loaded", nav: "Works", load: true },
  {
    name: "works-search",
    nav: "Works",
    load: true,
    steps: async (page) => {
      await page.locator("#worksSearch").fill("Cosmopolitanism");
      await page.waitForTimeout(900);
    },
  },
  {
    name: "works-open-records",
    nav: "Works",
    load: true,
    steps: async (page) => {
      await page
        .getByRole("button", { name: /^Open \d+ records for / })
        .first()
        .click();
      await page.waitForTimeout(800);
    },
  },
  {
    name: "works-open-records-needing-review",
    nav: "Works",
    load: true,
    steps: async (page) => {
      await page
        .getByRole("button", { name: /records needing review for/ })
        .first()
        .click();
      await page.waitForTimeout(800);
    },
  },
  {
    name: "works-actions-menu",
    nav: "Works",
    load: true,
    steps: async (page) => {
      await page.locator("main summary", { hasText: "Actions" }).first().click();
      await page.waitForTimeout(500);
    },
  },
  {
    name: "dialog-works-edit-metadata",
    nav: "Works",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await worksAction("Edit metadata")(page);
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  {
    name: "dialog-works-remove-work",
    nav: "Works",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await worksAction("Remove entire work")(page);
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
];

// Times are rendered in the browser's zone (for example the title of a job's finish time), so pin the zone and locale:
// the snapshots must not depend on the machine that records or checks them.
test.use({ timezoneId: "UTC", locale: "en-US" });

test.describe("legacy runtime DOM baseline", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));
  for (const scenario of scenarios) {
    test(scenario.name, async ({ page }) => {
      await open(page, scenario);
      const target = scenario.target ?? "main";
      // Styles are read once the markup has stopped changing, so late-arriving data cannot make them vary.
      const stableMarkup = await markup(page, target);
      const captured = scenario.styles ? await computedStyles(page, target) : stableMarkup;
      expect(captured).toMatchSnapshot(`${scenario.name}.${scenario.styles ? "txt" : "html"}`);
    });
  }
});

test.describe("legacy runtime errors", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));
  // renderDashboard once called a function that no longer exists, so every render threw and the
  // final decorateDisabledControls call never ran.
  test("the dashboard renders without page errors", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (error) => errors.push(String(error)));
    await open(page, { name: "errors", load: true });
    await markup(page, "main");
    expect(errors).toEqual([]);
  });
  test("disabled dashboard controls are decorated when the dashboard renders", async ({ page }) => {
    await open(page, { name: "decorated" });
    await expect(page.locator("#main .disabled-control-tooltip").first()).toBeVisible();
  });
});

test.describe("views follow the loaded corpus", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));
  // A file imported while Records was open used to appear only after leaving and coming back.
  test("Records lists a file imported while it is open", async ({ page }) => {
    await open(page, { name: "import-while-open", nav: "Records", load: true });
    await expect(page.getByText(/Local JSONL\s*1 files?/i)).toBeVisible();
    await page.setInputFiles("#fileInput", {
      name: "second.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        JSON.stringify({ ...RECORDS[0], record_id: "second-00001", work: "Glas" }),
      ),
    });
    await expect(page.getByText("Loaded 1 records")).toBeVisible();
    await expect(page.getByText(/Local JSONL\s*2 files/i)).toBeVisible({ timeout: 5000 });
  });

  // The Compare picker searched the records that were loaded when the view opened.
  test("Compare finds a record imported while it is open", async ({ page }) => {
    await open(page, { name: "compare-import-while-open", nav: "Compare" });
    await expect(
      page.getByText(/Load JSONL files or browse the corpus database first/).first(),
    ).toBeVisible();
    await page.setInputFiles("#fileInput", {
      name: "late.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        JSON.stringify({ ...RECORDS[0], record_id: "late-00001", work: "Late Work" }),
      ),
    });
    await expect(page.getByText("Loaded 1 records")).toBeVisible();
    await page
      .getByPlaceholder(/Type record ID/)
      .first()
      .fill("Late");
    await expect(page.getByText("No matching records.")).toHaveCount(0);
    await expect(page.getByText(/late-00001/).first()).toBeVisible({ timeout: 5000 });
  });

  // The sync buttons stayed disabled after a file was imported while Vector Stores was open.
  test("Vector Stores enables syncing for a file imported while it is open", async ({ page }) => {
    await open(page, { name: "vector-import-while-open", nav: "Vector Stores" });
    const sync = page.locator("main button", { hasText: "Sync active JSONL" });
    await expect(sync).toBeDisabled();
    await page.setInputFiles("#fileInput", {
      name: "late.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        JSON.stringify({ ...RECORDS[0], record_id: "late-00001", work: "Late Work" }),
      ),
    });
    await expect(page.getByText("Loaded 1 records")).toBeVisible();
    await expect(sync).toBeEnabled({ timeout: 5000 });
  });
});
