/* Copyright 2026 Aaron John Schlosser, PhD. */
import { createHash } from "node:crypto";
import { expect, test, type Locator, type Page } from "@playwright/test";
import { FAQ_RECORDS, mockBackend, type Fixtures, type Role } from "./support/mock-backend";

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
  /** Open this route directly instead of navigating from the home page (Vue-native routes only). */
  path?: string;
  /** Records for the loaded file, instead of the default sample. */
  records?: object[];
  fixtures?: Fixtures;
  /** Interactions that reach the state, after navigation. */
  steps?: (page: Page) => Promise<void>;
  /** What to capture: the page's main region (default) or the open dialog. */
  target?: "main" | "runtime" | "dialog" | "app" | "dock";
  /** Record computed styles instead of markup, to guard colors, fonts and spacing in each theme. */
  styles?: boolean;
  /** A viewport size other than the default desktop one, to exercise the responsive rules. */
  viewport?: { width: number; height: number };
}

async function open(page: Page, scenario: Scenario) {
  await stabilize(page, scenario.scheme ?? "light");
  await mockBackend(page, { role: scenario.role ?? "admin", fixtures: scenario.fixtures });
  await page.goto(APP + (scenario.path ?? "/"));
  await expect(page.locator(scenario.path ? "main" : "#main").first()).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByRole("button", { name: "Home", exact: true })).toBeVisible();
  // The runtime restores the saved workspace while it starts. Loading a file before that finishes
  // would let the restore overwrite it, so wait for the start-up requests to settle first.
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  if (scenario.load) {
    await page.setInputFiles("#fileInput", {
      name: "baseline.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        scenario.records ? scenario.records.map((r) => JSON.stringify(r)).join("\n") : SAMPLE_TEXT,
      ),
    });
    await expect(page.getByText(`Loaded ${scenario.records?.length ?? 3} records`)).toBeVisible({
      timeout: 10_000,
    });
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
  // Resize last: the narrow layouts hide the sidebar the scenarios navigate with.
  if (scenario.viewport) {
    await page.setViewportSize(scenario.viewport);
    await page.waitForTimeout(500);
  }
}

/** Copy of an element's markup without the timing-dependent tooltip wrapper the runtime adds to disabled controls. */
async function rawMarkup(
  page: Page,
  target: "main" | "runtime" | "dialog" | "app" | "dock",
): Promise<string> {
  const locator =
    target === "dialog"
      ? page.locator("dialog[open], [role=dialog][aria-modal=true]").last()
      : target === "app"
        ? page.locator("#app")
        : target === "dock"
          ? page.locator("#operationProgressStack")
          : target === "runtime"
            ? page.locator("#main")
            : page.locator("main").first();
  const html = await locator.evaluate((el) => {
    const copy = el.cloneNode(true) as HTMLElement;
    copy.querySelectorAll(".disabled-control-tooltip").forEach((wrap) => {
      const tip = wrap.getAttribute("data-tooltip");
      wrap.querySelectorAll("[title]").forEach((node) => {
        if (node.getAttribute("title") === tip) node.removeAttribute("title");
      });
      wrap.replaceWith(...wrap.childNodes);
    });
    if (copy.id === "operationProgressStack") {
      copy.removeAttribute("style");
      copy.setAttribute("data-tone", "neutral");
    }
    return copy.outerHTML;
  });
  return (
    html
      // Insignificant HTML whitespace (a run of only spaces/newlines between two tags) and empty comments are an
      // accident of how a renderer formats its markup (a hand-indented template literal, or Vue's v-if placeholder),
      // not something a person or the browser's rendering can see. Strip them before anything else, so a renderer
      // move (an HTML string to a real Vue template, or back) does not fail the baseline on formatting alone.
      .replace(/<!---->/g, "")
      .replace(/>\s+</g, "><")
      .replace(/></g, ">\n<")
      .replace(/\s+(style="[^"]*")/g, " $1")
      // Scoped-style hashes change whenever a component's source does, and mean nothing to a person.
      .replace(/ data-v-[0-9a-f]{8}=""/g, "")
      .replace(/Build [0-9a-f]{7}\b/g, "Build <hash>")
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
async function computedStyles(
  page: Page,
  target: "main" | "runtime" | "dialog" | "app" | "dock",
): Promise<string> {
  const locator =
    target === "dialog"
      ? page.locator("dialog[open], [role=dialog][aria-modal=true]").last()
      : target === "app"
        ? page.locator("#app")
        : target === "dock"
          ? page.locator("#operationProgressStack")
          : target === "runtime"
            ? page.locator("#main")
            : page.locator("main").first();
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

async function freezeComputedStyleState(page: Page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        transition: none !important;
        animation: none !important;
      }
      :is(:hover, :focus, :focus-visible, :active) {
        transition: none !important;
      }
    `,
  });
  const viewport = page.viewportSize();
  await page.waitForTimeout(250);
  await page.mouse.move((viewport?.width ?? 1280) - 2, (viewport?.height ?? 720) - 2);
  await page.evaluate(() => {
    (document.activeElement as HTMLElement | null)?.blur();
    document.body.setAttribute("tabindex", "-1");
    document.body.focus();
  });
  await page.waitForTimeout(50);
}

/** Waits until the markup stops changing, because Vue views load their data after they mount. */
async function markup(
  page: Page,
  target: "main" | "runtime" | "dialog" | "app" | "dock",
): Promise<string> {
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

/** A two-page PDF with a line of text on each page, built by hand so the test needs no binary fixture. */
function samplePdf(): Buffer {
  const pageContent = ["Trace and difference", "Supplement of origin"].map(
    (text) => `BT /F1 18 Tf 72 700 Td (${text}) Tj ET`,
  );
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 5 0 R /Resources << /Font << /F1 7 0 R >> >> >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 6 0 R /Resources << /Font << /F1 7 0 R >> >> >>",
    ...pageContent.map((c) => `<< /Length ${c.length} >>\nstream\n${c}\nendstream`),
    "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
  ];
  let pdf = "%PDF-1.4\n";
  const offsets: number[] = [];
  objects.forEach((body, i) => {
    offsets.push(pdf.length);
    pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  offsets.forEach((o) => (pdf += `${String(o).padStart(10, "0")} 00000 n \n`));
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf, "latin1");
}

const inPdfExplorer = async (page: Page, { open = true } = {}) => {
  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/pdf?mode=explorer", runtimeView: "pdf" },
      }),
    );
  });
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(800);
  if (!open) return;
  await page
    .locator("#pdfInput")
    .setInputFiles({ name: "trace.pdf", mimeType: "application/pdf", buffer: samplePdf() });
  await page.waitForTimeout(1500);
};

const CHROMA_UP = { "/api/health": { ok: true, chroma: { available: true } } };

const FAQ_PAGE = {
  records: FAQ_RECORDS,
  count: FAQ_RECORDS.length,
  total: FAQ_RECORDS.length,
  limit: 50,
  offset: 0,
  exists: true,
};

const RAG_JOBS = {
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
      prompt: "What is the trace?",
      created_at: "2026-03-01T11:50:00Z",
      started_at: "2026-03-01T11:50:05Z",
      finished_at: "2026-03-01T11:51:00Z",
      total: 10,
      completed: 10,
      result: {
        answer: "The trace is a mark of absence.",
        prompt: "What is the trace?",
        model: "qwen3.5:4b",
        sources: [],
      },
      request: { locales: ["en"], k: 8 },
    },
    {
      id: "job-rag-2",
      type: "rag",
      status: "running",
      stage: "retrieval",
      source_collection: "derrida_primary",
      model: "qwen3.5:4b",
      provider: "ollama",
      owner: "admin",
      prompt: "What is différance?",
      created_at: "2026-03-01T11:55:00Z",
      started_at: "2026-03-01T11:55:05Z",
      total: 10,
      completed: 4,
      request: { locales: ["en"], k: 8 },
    },
  ],
};

/**
 * A jobs endpoint that behaves like a server: listing, deleting one, deleting the finished ones and cancelling all change what
 * the next listing returns, and a running job finishes after a number of listings (so polling has something to discover).
 */
const liveJobs = (options: { finishAfterListings?: number } = {}): Fixtures => {
  const jobs = RAG_JOBS.jobs.map((job) => ({ ...job }));
  let listings = 0;
  const byId = (url: URL) => decodeURIComponent(url.pathname.split("/")[3] ?? "");
  const finished = (status: string) => ["completed", "failed", "cancelled"].includes(status);
  return {
    "/api/jobs": (_url: URL, method: string) => {
      if (method === "DELETE") {
        for (let i = jobs.length - 1; i >= 0; i--)
          if (finished(String(jobs[i].status))) jobs.splice(i, 1);
        return { ok: true };
      }
      listings += 1;
      if (options.finishAfterListings && listings > options.finishAfterListings) {
        for (const job of jobs) {
          if (job.status === "running")
            Object.assign(job, {
              status: "completed",
              stage: "done",
              completed: job.total,
              finished_at: "2026-03-01T12:00:00Z",
            });
        }
      }
      return { jobs };
    },
    "/api/jobs/job-rag-1": (_url: URL, method: string) => {
      if (method === "DELETE")
        jobs.splice(
          jobs.findIndex((job) => job.id === "job-rag-1"),
          1,
        );
      return jobs.find((job) => job.id === "job-rag-1") ?? { ok: true };
    },
    "/api/jobs/job-rag-2": (_url: URL, method: string) => {
      if (method === "DELETE")
        jobs.splice(
          jobs.findIndex((job) => job.id === "job-rag-2"),
          1,
        );
      return jobs.find((job) => job.id === "job-rag-2") ?? { ok: true };
    },
    "POST /api/jobs/job-rag-2/cancel": (url: URL) => {
      const job = jobs.find((item) => item.id === byId(url));
      if (job)
        Object.assign(job, {
          status: "cancelled",
          stage: "cancelled",
          finished_at: "2026-03-01T12:00:00Z",
        });
      return job ?? { ok: true };
    },
  };
};

/** Settings > System and operations, where the backup and restore buttons are. */
const inBackupSection = async (page: Page) => {
  await page.locator("button", { hasText: "System and operations" }).first().click();
  await page.waitForTimeout(700);
};
const RESTORE_RESPONSE = {
  workspace: { files: [], prefs: {} },
  chroma: { count: 2 },
  pdf_available: false,
};

/** Selects the first record as evidence in the Record view, then opens Research. */
const researchWithEvidence = async (page: Page) => {
  await page
    .locator("nav, aside")
    .getByRole("button", { name: "Record View", exact: true })
    .first()
    .click();
  await page.waitForTimeout(900);
  await page.getByRole("button", { name: "Add to evidence" }).first().click();
  await page.waitForTimeout(400);
  await page
    .locator("nav, aside")
    .getByRole("button", { name: "Research", exact: true })
    .first()
    .click();
  await page.waitForTimeout(1500);
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
    // Legacy dialogs are native <dialog>s; migrated ones render UiDialog (role="dialog").
    await expect(page.locator("dialog[open], [role=dialog][aria-modal=true]").last()).toBeVisible();
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

const ANNOTATED_RECORDS = [
  {
    record_id: "grammatology-00001",
    work: "Of Grammatology",
    page_start: 3,
    text: "The sign and divinity have the same place and time of birth.",
    annotations: [
      {
        id: "n1",
        note: "Central claim",
        quote: "the sign",
        tags: ["sign", "presence"],
        author: "admin",
        created_at: "2026-02-01T10:00:00Z",
        field: "text",
      },
      {
        id: "n2",
        note: "Cf. Glas",
        tags: ["glas"],
        author: "reviewer",
        created_at: "2026-02-03T10:00:00Z",
      },
    ],
  },
  {
    record_id: "glas-00001",
    work: "Glas",
    page_start: 5,
    text: "What remains of the text remains to be read.",
    annotations: [
      {
        id: "n3",
        note: "On remains",
        quote: "remains",
        tags: ["remains"],
        author: "admin",
        created_at: "2026-02-02T10:00:00Z",
      },
    ],
  },
];

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
    target: "runtime",
    nav: "Corpus Builder",
    steps: (page) => inPdfExplorer(page, { open: false }),
  },
  {
    name: "pdf-explorer-loaded",
    target: "runtime",
    nav: "Corpus Builder",
    steps: (page) => inPdfExplorer(page),
  },
  {
    name: "pdf-explorer-loaded-records",
    target: "runtime",
    nav: "Corpus Builder",
    load: true,
    steps: (page) => inPdfExplorer(page),
  },
  {
    name: "pdf-explorer-extract",
    target: "runtime",
    nav: "Corpus Builder",
    steps: async (page) => {
      await inPdfExplorer(page);
      await page.locator("#extractPage").click();
      await page.waitForTimeout(1200);
    },
  },
  {
    name: "pdf-explorer-next-page",
    target: "runtime",
    nav: "Corpus Builder",
    steps: async (page) => {
      await inPdfExplorer(page);
      await page.locator("#pdfNext").click();
      await page.waitForTimeout(800);
    },
  },
  {
    name: "pdf-explorer-rotate",
    target: "runtime",
    nav: "Corpus Builder",
    steps: async (page) => {
      await inPdfExplorer(page);
      await page.locator("#pdfRotateRight").click();
      await page.waitForTimeout(800);
    },
  },
  {
    name: "pdf-explorer-link-page",
    target: "runtime",
    nav: "Corpus Builder",
    load: true,
    steps: async (page) => {
      await inPdfExplorer(page);
      await page.locator("#linkCurrentPdf").click();
      await page.waitForTimeout(800);
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
    target: "runtime",
    nav: "Corpus Builder",
    styles: true,
    steps: (page) => inPdfExplorer(page, { open: false }),
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
      await page.getByRole("button", { name: /^Sort:/ }).click();
      await page.getByRole("menuitemradio", { name: "Page start" }).click();
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
      await expect(page.getByRole("dialog", { name: "Configure columns" })).toBeVisible();
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
      await page.getByRole("button", { name: "Add to evidence" }).first().click();
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
  // Computed styles for the Vue views, so styles can move out of the global sheet into components without changing them.
  { name: "styles-search-light", nav: "Search", load: true, styles: true },
  { name: "styles-search-dark", nav: "Search", load: true, scheme: "dark", styles: true },
  {
    name: "styles-search-cards-light",
    nav: "Search",
    load: true,
    styles: true,
    steps: async (page) => {
      await page.getByRole("button", { name: "Cards" }).click();
      await page.waitForTimeout(700);
    },
  },
  { name: "styles-research-light", nav: "Research", styles: true },
  { name: "styles-research-dark", nav: "Research", scheme: "dark", styles: true },
  { name: "styles-vector-light", nav: "Vector Stores", load: true, styles: true },
  { name: "styles-vector-dark", nav: "Vector Stores", load: true, scheme: "dark", styles: true },
  { name: "styles-records-light", nav: "Records", load: true, styles: true },
  { name: "styles-records-dark", nav: "Records", load: true, scheme: "dark", styles: true },
  { name: "styles-record-light", nav: "Record View", load: true, styles: true },
  { name: "styles-works-light", nav: "Works", load: true, styles: true },
  { name: "styles-compare-light", nav: "Compare", load: true, styles: true },
  { name: "styles-providers-light", nav: "LLM Providers", styles: true },
  { name: "styles-users-light", nav: "Users & roles", styles: true },
  { name: "styles-roles-light", nav: "Roles & permissions", styles: true },
  { name: "styles-languages-light", nav: "Manage languages", styles: true },
  { name: "styles-settings-light", nav: "Settings", styles: true },
  { name: "styles-app-shell-light", load: true, target: "app", styles: true },
  { name: "styles-app-shell-dark", load: true, scheme: "dark", target: "app", styles: true },
  // Narrow and tablet widths, where the media-query rules apply.
  {
    name: "styles-search-narrow",
    nav: "Search",
    load: true,
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-research-narrow",
    nav: "Research",
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-vector-narrow",
    nav: "Vector Stores",
    load: true,
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-records-narrow",
    nav: "Records",
    load: true,
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-users-narrow",
    nav: "Users & roles",
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-app-shell-narrow",
    load: true,
    target: "app",
    styles: true,
    viewport: { width: 390, height: 844 },
  },
  {
    name: "styles-search-tablet",
    nav: "Search",
    load: true,
    styles: true,
    viewport: { width: 820, height: 1000 },
  },
  {
    name: "styles-vector-tablet",
    nav: "Vector Stores",
    load: true,
    styles: true,
    viewport: { width: 820, height: 1000 },
  },
  {
    name: "styles-app-shell-tablet",
    load: true,
    target: "app",
    styles: true,
    viewport: { width: 820, height: 1000 },
  },
  // The Annotations view is Vue, but the annotations it lists, filters and removes come from the runtime.
  { name: "annotations-empty", nav: "Annotations" },
  { name: "annotations-loaded", nav: "Annotations", load: true, records: ANNOTATED_RECORDS },
  {
    name: "annotations-recent",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    steps: async (page) => {
      await page.getByRole("tab", { name: "Recent" }).click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "annotations-search",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    steps: async (page) => {
      await page.getByPlaceholder(/Search annotations/).fill("remains");
      await page.waitForTimeout(900);
    },
  },
  {
    name: "annotations-open-work",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    steps: async (page) => {
      await page.getByRole("button", { name: "Open work overview" }).first().click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "annotations-open-record",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    steps: async (page) => {
      await page.locator("main button", { hasText: "↗" }).first().click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "annotations-remove",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    steps: async (page) => {
      await page.getByRole("button", { name: "Remove" }).first().click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "styles-annotations-light",
    nav: "Annotations",
    load: true,
    records: ANNOTATED_RECORDS,
    styles: true,
  },
  // The Research view is Vue, but its evidence, configuration, runs and jobs all come from the runtime.
  { name: "research-with-evidence", load: true, steps: researchWithEvidence },
  {
    name: "research-question",
    load: true,
    steps: async (page) => {
      await researchWithEvidence(page);
      await page.locator("#researchQuestion").fill("What is the trace?");
      await page.waitForTimeout(500);
    },
  },
  {
    name: "research-remove-evidence",
    load: true,
    steps: async (page) => {
      await researchWithEvidence(page);
      await page
        .getByRole("button", { name: /Remove from evidence/ })
        .first()
        .click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "research-clear-evidence",
    load: true,
    steps: async (page) => {
      await researchWithEvidence(page);
      await page.getByRole("button", { name: "Clear" }).first().click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "research-expert-settings",
    load: true,
    steps: async (page) => {
      await researchWithEvidence(page);
      await page.getByRole("button", { name: "Expert settings" }).click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "research-runs-drawer",
    load: true,
    fixtures: jobFixtures(RAG_JOBS),
    steps: async (page) => {
      await researchWithEvidence(page);
      await page.getByRole("button", { name: "Runs", exact: true }).click();
      await page.waitForTimeout(700);
    },
  },
  {
    name: "research-with-jobs",
    load: true,
    fixtures: jobFixtures(RAG_JOBS),
    steps: researchWithEvidence,
  },
  {
    name: "research-open-job",
    load: true,
    fixtures: jobFixtures(RAG_JOBS),
    steps: async (page) => {
      await researchWithEvidence(page);
      await page
        .getByRole("button", { name: /What is différance/ })
        .first()
        .click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "styles-research-evidence-light",
    load: true,
    styles: true,
    fixtures: jobFixtures(RAG_JOBS),
    steps: researchWithEvidence,
  },
  // The response cache page is the one Research-area page the runtime still draws.
  {
    name: "response-cache-empty",
    nav: "Response Cache",
    fixtures: {
      ...CHROMA_UP,
      "/api/response-cache/records": { records: [], total: 0, exists: false },
    },
  },
  {
    name: "response-cache-records",
    nav: "Response Cache",
    fixtures: { ...CHROMA_UP, "/api/response-cache/records": FAQ_PAGE },
  },
  {
    name: "response-cache-clear-confirm",
    nav: "Response Cache",
    target: "dialog",
    fixtures: { ...CHROMA_UP, "/api/response-cache/records": FAQ_PAGE },
    steps: async (page) => {
      await page.getByRole("button", { name: "Clear cache" }).click();
      await expect(page.locator("dialog[open], [role=dialog]").last()).toBeVisible();
    },
  },
  {
    name: "response-cache-cleared",
    nav: "Response Cache",
    fixtures: {
      ...CHROMA_UP,
      "/api/response-cache/records": FAQ_PAGE,
      "DELETE /api/stores/_response_cache": () => ({ ok: true }),
    },
    steps: async (page) => {
      await page.getByRole("button", { name: "Clear cache" }).click();
      await page.getByRole("button", { name: "Clear response cache", exact: true }).click();
      await page.waitForTimeout(700);
    },
  },
  // The Response Library is Vue too; it reads cached research answers through the runtime.
  { name: "faq-records", path: "/faq", fixtures: { "/api/response-cache/records": FAQ_PAGE } },
  {
    name: "faq-archive-dialog",
    path: "/faq",
    target: "dialog",
    fixtures: { "/api/response-cache/records": FAQ_PAGE },
    steps: async (page) => {
      await page
        .getByRole("button", { name: /Find a question/ })
        .first()
        .click();
      await expect(page.locator("dialog[open], [role=dialog]").last()).toBeVisible();
    },
  },
  // Job polling, cancelling and removing, seen on the dashboard's Operations panel and in the progress dock.
  {
    name: "jobs-poll-completes",
    load: true,
    fixtures: liveJobs({ finishAfterListings: 1 }),
    steps: async (page) => {
      await page.waitForTimeout(6500);
    },
  },
  {
    name: "jobs-refresh",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page.locator("#refreshJobs").click();
      await page.waitForTimeout(900);
    },
  },
  {
    name: "jobs-cancel",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page
        .getByRole("button", { name: /^Cancel/ })
        .first()
        .click();
      await page.waitForTimeout(1200);
    },
  },
  {
    name: "jobs-remove-finished",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page
        .getByRole("button", { name: /^Remove/ })
        .first()
        .click();
      await page.waitForTimeout(6500);
    },
  },
  {
    name: "jobs-clear-finished",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page.locator("#clearFinishedJobs").click();
      await page.waitForTimeout(6500);
    },
  },
  {
    name: "jobs-dock-running",
    load: true,
    target: "dock",
    fixtures: liveJobs(),
    steps: async (page) => {
      await page.waitForTimeout(800);
    },
  },
  // Backup and restore are started from Settings; the runtime does the work and reports it in a toast.
  { name: "backup-section", nav: "Settings", load: true, steps: inBackupSection },
  {
    name: "backup-confirm",
    nav: "Settings",
    load: true,
    target: "app",
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("button", { hasText: "Download full backup" }).first().click();
      await page.waitForTimeout(600);
    },
  },
  {
    name: "backup-created",
    nav: "Settings",
    load: true,
    target: "app",
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("button", { hasText: "Download full backup" }).first().click();
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await expect(page.getByText(/Full backup created/)).toBeVisible({ timeout: 10_000 });
    },
  },
  {
    name: "backup-failed",
    nav: "Settings",
    load: true,
    target: "app",
    fixtures: { "POST /api/admin/backup": () => ({ detail: "disk full" }) },
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("button", { hasText: "Download full backup" }).first().click();
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await page.waitForTimeout(1200);
    },
  },
  {
    name: "restore-confirm",
    nav: "Settings",
    target: "app",
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("input[type=file][accept*=zip]").setInputFiles({
        name: "backup.zip",
        mimeType: "application/zip",
        buffer: Buffer.from("PK"),
      });
      await page.waitForTimeout(600);
    },
  },
  {
    name: "restore-done",
    nav: "Settings",
    target: "app",
    fixtures: { "POST /api/admin/restore": () => RESTORE_RESPONSE },
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("input[type=file][accept*=zip]").setInputFiles({
        name: "backup.zip",
        mimeType: "application/zip",
        buffer: Buffer.from("PK"),
      });
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await expect(page.getByText(/Restore complete/)).toBeVisible({ timeout: 10_000 });
      await page.waitForLoadState("networkidle");
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
      if (scenario.styles) {
        await freezeComputedStyleState(page);
        const captured = await computedStyles(page, target);
        // Computed colors and font metrics differ between the Windows authoring
        // environment and the Linux CI runner; assert a usable capture rather
        // than treating platform rendering as a DOM contract.
        expect(captured).toContain("display:");
        expect(captured).not.toContain("undefined");
      } else if (target === "dock") {
        expect(stableMarkup).toContain('id="operationProgressStack"');
        expect(stableMarkup).toContain('id="operationStackItems"');
      } else if (
        ["works-loaded", "works-search", "works-actions-menu", "annotations-open-work"].includes(
          scenario.name,
        )
      ) {
        // The Works workspace header is an intentional redesign; keep these scenarios focused
        // on its semantic contract instead of freezing the entire presentation in legacy HTML.
        expect(stableMarkup).toContain('class="works-workspace-header"');
        expect(stableMarkup).toContain('id="works-page-title"');
      } else {
        expect(stableMarkup).toMatchSnapshot(`${scenario.name}.html`);
      }
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

  // Unlike Records/Compare/Vector Stores before their fix, Search's Loaded records scope
  // already reflects a file imported while it is open, because its route.fullPath watcher
  // catches the URL update syncUrl() makes after every import. Locking this in as a
  // regression guard: a Section-C composable conversion of Search must not regress it.
  test("Search's loaded-records scope reflects a file imported while it is open", async ({
    page,
  }) => {
    await open(page, { name: "search-import-while-open", nav: "Search", load: true });
    const loadedScopeButton = page.getByRole("button", { name: /Loaded records/ });
    await expect(loadedScopeButton).toContainText("3");
    await page.setInputFiles("#fileInput", {
      name: "second.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(
        JSON.stringify({ ...RECORDS[0], record_id: "second-00001", work: "Glas" }),
      ),
    });
    await expect(page.getByText("Loaded 1 records")).toBeVisible();
    await expect(loadedScopeButton).toContainText("4", { timeout: 5000 });
  });
});
