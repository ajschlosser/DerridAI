/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

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
async function stabilize(page: Page) {
  await page.addInitScript(() => {
    // The dashboard picks a random record and re-renders a variable number of times as data arrives.
    Math.random = () => 0;
    localStorage.setItem("derridai.ui.scheme", "light");
  });
  await page.clock.setFixedTime(new Date("2026-03-01T12:00:00Z"));
}

async function open(page: Page, nav: string, load: boolean) {
  await stabilize(page);
  await mockBackend(page, { role: "admin" });
  await page.goto(APP + "/");
  await expect(page.locator("#main")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByRole("button", { name: "Annotations", exact: true })).toBeVisible();
  // The runtime restores the saved workspace while it starts. Loading a file before that finishes
  // would let the restore overwrite it, so wait for the start-up requests to settle first.
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(1000);
  if (load) {
    await page.setInputFiles("#fileInput", {
      name: "baseline.jsonl",
      mimeType: "application/x-ndjson",
      buffer: Buffer.from(RECORDS.map((r) => JSON.stringify(r)).join("\n")),
    });
    await expect(page.getByText("Loaded 3 records")).toBeVisible({ timeout: 10_000 });
  }
  // The runtime picks its view from in-app navigation, so go there the way a person would.
  if (nav !== "Home") await page.getByRole("button", { name: nav, exact: true }).click();
  // Let asynchronous rendering (progressive render, health checks, fonts) settle.
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600);
}

async function rawMarkup(page: Page): Promise<string> {
  // The runtime wraps disabled controls in a tooltip span some time after render. When that happens
  // depends on timing, so undo it and compare the markup underneath.
  const html = await page
    .locator("main")
    .first()
    .evaluate((el) => {
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
  return html
    .replace(/></g, ">\n<")
    .replace(/\s+(style="[^"]*")/g, " $1")
    .replace(/\b\d{1,2}\/\d{1,2}\/\d{4},? \d{1,2}:\d{2}(:\d{2})?( [AP]M)?/g, "<date>");
}

const views: Array<{ name: string; nav: string; load: boolean }> = [
  { name: "home-empty", nav: "Home", load: false },
  { name: "home-loaded", nav: "Home", load: true },
  { name: "research-empty", nav: "Research", load: false },
];

test.describe("legacy runtime DOM baseline", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));
  for (const view of views) {
    test(view.name, async ({ page }) => {
      await open(page, view.nav, view.load);
      expect(await markup(page)).toMatchSnapshot(`${view.name}.html`);
    });
  }
});

/** Waits until the markup stops changing, because Vue views load their data after they mount. */
async function markup(page: Page): Promise<string> {
  let last = await rawMarkup(page);
  let stableFor = 0;
  for (let i = 0; i < 40 && stableFor < 4; i++) {
    await page.waitForTimeout(200);
    const next = await rawMarkup(page);
    stableFor = next === last ? stableFor + 1 : 0;
    last = next;
  }
  return last;
}
