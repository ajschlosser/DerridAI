/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { createHash } from "node:crypto";
import { expect, test, type Locator, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { FAQ_RECORDS, mockBackend, type Fixtures, type Role } from "./support/mock-backend";

// Characterization baseline for runtime-owned UI and runtime-coupled workflows that do not yet
// have an equivalent modern browser contract. Vue-native Records, Works, and Annotations behavior
// lives in their dedicated E2E/component suites instead of being frozen here. Remaining snapshots
// protect legacy presentation until the owning runtime surface is migrated deliberately.
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
  /**
   * For a surface that is now a Vue component: assert this text appears in the captured markup
   * instead of comparing a committed baseline of the retired imperative DOM.
   */
  contains?: string[];
  /** Interactions that reach the state, after navigation. */
  steps?: (page: Page) => Promise<void>;
  /** What to capture: the page's main region (default) or the open dialog. */
  target?: "main" | "runtime" | "dialog" | "app" | "dock";
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
    if (scenario.nav === "Record View") {
      // These fixtures load records directly into the runtime rather than the
      // server-backed Records table, so preserve that state while routing to
      // the now-contextual Record View.
      await page.evaluate(() => {
        window.dispatchEvent(
          new CustomEvent("derridai:navigate-native", {
            detail: { path: "/record", runtimeView: "record" },
          }),
        );
      });
      await expect(page.locator("main.record-workspace-page")).toBeVisible();
    } else {
      // Target destination buttons, not same-named collapsible section headings. Some groups
      // use progressive disclosure, so reveal the owning group before activating a hidden target.
      const destination = page
        .locator(
          `.shell-sidebar .nav-tooltip-wrap button[aria-label=${JSON.stringify(scenario.nav)}]`,
        )
        .first();
      if (!(await destination.isVisible())) {
        const section = destination.locator("xpath=ancestor::section[1]");
        const groupToggle = section.locator(".shell-nav-group-toggle");
        if (await groupToggle.count()) await groupToggle.click();
      }
      await expect(destination).toBeVisible();
      await destination.click();
    }
  }
  await page.waitForLoadState("networkidle");
  await scenario.steps?.(page);
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
    // These legacy snapshots characterize backup/restore states. Data retention is a separate
    // Vue workspace with dedicated component coverage, so keep it from invalidating all six
    // backup snapshots whenever its independent UI changes.
    copy
      .querySelectorAll('[aria-labelledby="settings-heading-data-retention"]')
      .forEach((section) => section.remove());
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
      .replace(/Build [0-9a-f]{7,8}\b/g, "Build <hash>")
      .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g, "<uuid>")
      .replace(/\bui-tooltip-\d+\b/g, "ui-tooltip-<id>")
      .replace(/\b\d{1,2}\/\d{1,2}\/\d{4},? \d{1,2}:\d{2}(:\d{2})?( [AP]M)?/g, "<date>")
  );
}

/** Waits until the markup stops changing, because Vue views load their data after they mount. */
async function markup(
  page: Page,
  target: "main" | "runtime" | "dialog" | "app" | "dock",
): Promise<string> {
  let last = await rawMarkup(page, target);
  let stableFor = 0;
  for (let i = 0; i < 40 && stableFor < 3; i++) {
    await page.waitForTimeout(100);
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
  await page
    .locator("main")
    .getByRole("button", { name: /^Actions for / })
    .first()
    .click();
  await page.getByRole("menuitem", { name }).first().click();
};

/** Opens the Works page header's More actions menu and runs one of its commands. */
const worksHeaderAction = (name: RegExp | string) => async (page: Page) => {
  await page.locator("main").getByRole("button", { name: "More actions" }).first().click();
  await page.getByRole("menuitem", { name }).first().click();
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
  const explorerPath = "/source-explorer";
  await expect
    .poll(
      async () => {
        await page.evaluate((path) => {
          window.dispatchEvent(
            new CustomEvent("derridai:navigate-native", {
              detail: { path, runtimeView: "pdf" },
            }),
          );
        }, explorerPath);
        const url = new URL(page.url());
        return `${url.pathname}${url.search}`;
      },
      { timeout: 10_000, intervals: [50, 100, 200, 500] },
    )
    .toBe(explorerPath);
  await page.waitForLoadState("networkidle");
  const input = page.locator("#pdfInput");
  await expect(input).toBeAttached({ timeout: 10_000 });
  if (!open) return;
  await input.setInputFiles({
    name: "trace.pdf",
    mimeType: "application/pdf",
    buffer: samplePdf(),
  });
  await expect(page.locator(".pdf-document-title")).toContainText("trace.pdf · 2 pages", {
    timeout: 10_000,
  });
  await expect(page.locator("#pdfCanvas")).toBeAttached();
};

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

/** Settings > Data & storage, where the backup and restore controls are. */
const inBackupSection = async (page: Page) => {
  await page.locator('a[href="/settings/data"]').first().click();
  await expect(page.getByRole("heading", { name: "Backup and restore" })).toBeVisible();
};
const RESTORE_RESPONSE = {
  workspace: { files: [], prefs: {} },
  chroma: { count: 2 },
  pdf_available: false,
};

/** Selects the first record as evidence in the Record view, then opens Research. */
const researchWithEvidence = async (page: Page) => {
  await page.evaluate(() => {
    window.dispatchEvent(
      new CustomEvent("derridai:navigate-native", {
        detail: { path: "/record", runtimeView: "record" },
      }),
    );
  });
  await expect(page.locator("main.record-workspace-page")).toBeVisible();
  const addEvidence = page.getByRole("button", { name: "Add evidence" }).first();
  await expect(addEvidence).toBeVisible();
  await addEvidence.click();
  await page
    .locator(".shell-sidebar .nav-tooltip-wrap")
    .getByRole("button", { name: "Research", exact: true })
    .first()
    .click();
  await expect(page.locator("#researchQuestion")).toBeVisible();
  await expect(page.getByRole("button", { name: /Remove from evidence/ }).first()).toBeVisible();
};

const inRecords = async (page: Page) => {
  await page.getByRole("button", { name: "Records", exact: true }).click();
  await page.waitForLoadState("networkidle");
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

/** The job list, and the per-job endpoint the details and results dialogs read. */
const jobFixtures = (payload: { jobs: Array<{ id: string }> }): Fixtures => ({
  "/api/jobs": payload,
  ...Object.fromEntries(payload.jobs.map((job) => [`/api/jobs/${job.id}`, job])),
});

const DOCK_WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

async function exerciseDockedOperations(page: Page) {
  await expect(page.locator("html")).toHaveAttribute("data-operations-dock-mode", "docked");
  const summary = page.locator(".operations-docked-summary");
  const stack = page.locator("#operationProgressStack");
  await expect(summary).toBeVisible({ timeout: 8_000 });
  await expect(summary).toHaveAttribute("aria-expanded", "false");

  await summary.click();
  await expect(summary).toHaveAttribute("aria-expanded", "true", { timeout: 2_000 });
  await expect(stack).toBeVisible();

  for (const selector of [".operations-docked-summary", "#operationProgressStack"]) {
    const scan = await new AxeBuilder({ page })
      .include(selector)
      .withTags(DOCK_WCAG_TAGS)
      .analyze();
    expect(
      scan.violations.map(
        (violation) =>
          `${violation.id}: ${violation.nodes.map((node) => node.target.join(" ")).join(", ")}`,
      ),
    ).toEqual([]);
  }

  await summary.dblclick();
  await expect(page.locator("html")).toHaveAttribute("data-operations-dock-mode", "floating");
  await expect(stack).toBeVisible();
}

const scenarios: Scenario[] = [
  // The dashboard is the one view still drawn by the runtime through RuntimeSurface.
  { name: "home-empty" },
  { name: "home-loaded", load: true },
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
      await expect(page.locator("#pdfPageInput")).toHaveValue("2");
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
    contains: ["Merge JSONL tabs"],
    load: true,
    target: "dialog",
    steps: openDialogFromRecords("Merge files", { secondFile: true }),
  },
  // Job dialogs, opened from the Operations panel on the dashboard.
  ...[0, 1, 2].map(
    (index): Scenario => ({
      name: `dialog-job-details-${index}`,
      contains: [" details"],
      load: true,
      target: "dialog",
      fixtures: jobFixtures(FINISHED_JOBS),
      steps: clickThenDialog((page) => page.getByRole("button", { name: "Details" }).nth(index)),
    }),
  ),
  {
    name: "dialog-job-results-review",
    contains: ["LLM review changes"],
    load: true,
    target: "dialog",
    fixtures: jobFixtures(FINISHED_JOBS),
    steps: clickThenDialog((page) => page.getByRole("button", { name: "Review results" }).first()),
  },
  // Export, and the collection wizard from Corpus Data.
  { name: "dialog-export", load: true, target: "dialog", steps: openDialogFromRecords("Export") },
  {
    name: "dialog-collection-wizard-source",
    nav: "Corpus Data",
    load: true,
    target: "dialog",
    steps: clickThenDialog((page) => page.getByRole("button", { name: "New" }).first()),
  },
  {
    name: "dialog-collection-wizard-retrieval",
    nav: "Corpus Data",
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
    contains: ["Populate metadata with LLM"],
    nav: "Works",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await worksHeaderAction(/Populate all metadata/)(page);
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  {
    name: "dialog-works-separate",
    contains: ["Separate works from a JSONL file"],
    nav: "Works",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await worksHeaderAction("Separate works")(page);
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  {
    name: "dialog-ocr-cleanup",
    contains: ["Clean OCR Artifacts"],
    load: true,
    target: "dialog",
    steps: openDialogFromRecords("Clean OCR Artifacts"),
  },
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
      await page.getByRole("tab", { name: "Attribution" }).click();
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
    contains: ["Edit record"],
    nav: "Record View",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await page.getByRole("button", { name: "Edit record" }).click();
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
  },
  {
    name: "dialog-works-edit-metadata",
    contains: ["Edit work metadata"],
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
    contains: ["Remove entire work"],
    nav: "Works",
    load: true,
    target: "dialog",
    steps: async (page) => {
      await worksAction("Remove entire work")(page);
      await expect(page.locator("dialog[open]").last()).toBeVisible();
    },
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
  // System Data is Vue-native and covered by component/E2E tests rather than the legacy runtime DOM baseline.
  // The Response Library is Vue too; it reads cached research answers through the runtime.
  {
    name: "faq-records",
    path: "/faq",
    fixtures: { "/api/response-cache/records": FAQ_PAGE },
    contains: [
      "Response Library",
      "How does Derrida distinguish responsibility from programmable rule-following?",
      "The responsible decision is not a calculable one.",
    ],
  },
  {
    name: "faq-archive-dialog",
    path: "/faq",
    target: "dialog",
    fixtures: { "/api/response-cache/records": FAQ_PAGE },
    contains: [
      "Saved questions",
      "Select a question to open its saved answer.",
      "How does Derrida distinguish responsibility from programmable rule-following?",
    ],
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
      const completed = page.locator('[data-op-id="job-rag-2"]');
      await expect(completed.locator(".ops-status")).toContainText("Completed", { timeout: 8_000 });
      // The UI briefly marks newly completed work as fresh; the committed baseline is the settled state.
      await expect(completed).not.toHaveClass(/is-fresh/, { timeout: 8_000 });
    },
  },
  {
    name: "jobs-refresh",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page.locator("#refreshJobs").click();
      await expect(
        page.locator('[role="status"]').filter({ hasText: "Operations updated." }),
      ).toHaveCount(1);
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
      await expect(page.locator('[data-op-id="job-rag-2"] .ops-status')).toContainText("Cancelled");
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
      await expect(page.locator('[data-op-id="job-rag-1"]')).toHaveCount(0, { timeout: 8_000 });
      await expect(page.locator(".ops-undo")).toHaveCount(0, { timeout: 8_000 });
    },
  },
  {
    name: "jobs-clear-finished",
    load: true,
    fixtures: liveJobs(),
    steps: async (page) => {
      await page.locator("#clearFinishedJobs").click();
      await expect(page.locator('[data-op-id="job-rag-1"]')).toHaveCount(0, { timeout: 8_000 });
      await expect(page.locator(".ops-undo")).toHaveCount(0, { timeout: 8_000 });
    },
  },
  {
    name: "jobs-dock-running",
    load: true,
    target: "dock",
    fixtures: liveJobs(),
    steps: exerciseDockedOperations,
  },
  {
    name: "jobs-dock-running-dark",
    load: true,
    scheme: "dark",
    target: "dock",
    fixtures: liveJobs(),
    steps: exerciseDockedOperations,
  },
  // Backup and restore are started from Settings; the runtime does the work and reports it in a toast.
  {
    name: "backup-section",
    contains: ["Backup and restore"],
    nav: "Settings",
    load: true,
    steps: inBackupSection,
  },
  {
    name: "backup-confirm",
    nav: "Settings",
    load: true,
    target: "dialog",
    contains: ["Create full backup?"],
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("button", { hasText: "Download full backup" }).first().click();
      await expect(page.getByRole("dialog")).toBeVisible();
    },
  },
  {
    name: "backup-created",
    nav: "Settings",
    load: true,
    target: "app",
    contains: ["Full backup created"],
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
    contains: ["Backup failed: disk full"],
    steps: async (page) => {
      await inBackupSection(page);
      await page.route("**/api/admin/backup", async (route) => {
        await route.fulfill({
          status: 500,
          contentType: "application/json",
          body: JSON.stringify({ detail: "disk full" }),
        });
      });
      await page.locator("button", { hasText: "Download full backup" }).first().click();
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await expect(page.getByText("Backup failed: disk full")).toBeVisible();
    },
  },
  {
    name: "restore-confirm",
    nav: "Settings",
    target: "dialog",
    contains: ["Restore full DerridAI backup?"],
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("input[type=file][accept*=zip]").setInputFiles({
        name: "backup.zip",
        mimeType: "application/zip",
        buffer: Buffer.from("PK"),
      });
      await expect(page.getByRole("dialog")).toBeVisible();
    },
  },
  {
    name: "restore-done",
    nav: "Settings",
    target: "app",
    contains: ["Settings"],
    fixtures: { "POST /api/admin/restore": () => RESTORE_RESPONSE },
    steps: async (page) => {
      await inBackupSection(page);
      await page.locator("input[type=file][accept*=zip]").setInputFiles({
        name: "backup.zip",
        mimeType: "application/zip",
        buffer: Buffer.from("PK"),
      });
      const reloaded = page.waitForEvent("load", { timeout: 10_000 });
      await page.getByRole("button", { name: "Yes", exact: true }).click();
      await expect(page.getByText(/Restore complete/)).toBeVisible({ timeout: 10_000 });
      await reloaded;
      await page.waitForLoadState("networkidle");
      await expect(page.locator("#app")).toBeVisible();
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
      const stableMarkup = await markup(page, target);
      if (target === "dock") {
        expect(stableMarkup).toContain('id="operationProgressStack"');
        expect(stableMarkup).toContain('id="operationStackItems"');
      } else if (scenario.contains) {
        for (const text of scenario.contains) expect(stableMarkup).toContain(text);
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

  // The sync buttons stayed disabled after a file was imported while Corpus Data was open.
  test("Corpus Data enables syncing for a file imported while it is open", async ({ page }) => {
    await open(page, { name: "vector-import-while-open", nav: "Corpus Data" });
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

  // Unlike Records/Compare/Corpus Data before their fix, Search's Loaded records scope
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
