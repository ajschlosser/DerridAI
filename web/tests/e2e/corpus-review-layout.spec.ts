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

import { expect, test, type Page } from "@playwright/test";
import {
  CORPUS_BUILD_ID,
  CORPUS_RECORDS,
  mockBackend,
  type Fixtures,
} from "./support/mock-backend";
import AxeBuilder from "@axe-core/playwright";

// The Corpus Builder review workspace in the real app: it should fit beneath the top bar,
// keep its decisions in reach, scroll each pane on its own, and be usable from the keyboard. Rendered
// against the mock API from the production build (see app-views.spec.ts).
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

async function open(page: Page, fixtures: Fixtures = {}) {
  await mockBackend(page, { fixtures });
  await page.goto(`${APP}/pdf`);
  await page.locator(".review-grid").waitFor();
  // Entering the workspace scrolls it to the top of the screen; wait for that to settle.
  await expect
    .poll(async () =>
      page.evaluate(() =>
        Math.round(document.querySelector(".review-frame")!.getBoundingClientRect().top),
      ),
    )
    .toBeLessThanOrEqual(64);
}
const rect = (page: Page, selector: string) =>
  page
    .locator(selector)
    .first()
    .evaluate((el) => {
      const r = el.getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height, right: r.right, bottom: r.bottom };
    });

test.describe("at a wide desktop", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the workspace respects its preferred height within the viewport without phantom scroll", async ({
    page,
  }) => {
    await open(page);
    const m = await page.evaluate(() => {
      const frame = document.querySelector(".review-frame")!.getBoundingClientRect();
      const bar = document.querySelector(".shell-topbar")!.getBoundingClientRect();
      const doc = document.documentElement;
      return {
        top: frame.top,
        bottom: frame.bottom,
        topbar: bar.bottom,
        view: innerHeight,
        below: doc.scrollHeight - (frame.bottom + scrollY),
      };
    });
    expect(
      Math.abs(m.top - m.topbar),
      "the frame sits right under the top bar",
    ).toBeLessThanOrEqual(2);
    expect(m.bottom - m.top, "retains a usable reading area").toBeGreaterThan(600);
    expect(m.bottom).toBeLessThanOrEqual(m.view);
    // The queue's visually-hidden labels used to stretch the page by thousands of pixels.
    expect(m.below, "nothing but the footer is below the workspace").toBeLessThan(160);
  });

  test("the decisions are one row, in reach, with the primary action last", async ({ page }) => {
    await open(page);
    const bar = await rect(page, ".decision-bar");
    expect(bar.h).toBeLessThanOrEqual(72);
    const [skip, reject, accept] = await Promise.all(
      ["Skip", "Reject & next", "Accept & next"].map(
        async (name) => (await page.getByRole("button", { name, exact: true }).boundingBox())!,
      ),
    );
    expect(Math.abs(skip.y - accept.y)).toBeLessThanOrEqual(4);
    expect(Math.abs(reject.y - accept.y)).toBeLessThanOrEqual(4);
    expect(accept.x).toBeGreaterThan(reject.x);
    expect(reject.x).toBeGreaterThan(skip.x);
    expect(accept.y + accept.height, "inside the window without scrolling").toBeLessThanOrEqual(
      900,
    );
  });

  test("the record's text is shown, and its metadata can be decided from the keyboard", async ({
    page,
  }) => {
    await open(page);
    await expect(page.locator(".record-primary-text .ctx-focus")).toContainText(/hospitality/);
    // The dock says what blocks the record; M jumps to the first field to decide.
    const blocker = page.locator("#record-metadata-blocker");
    await expect(blocker).toContainText(/3 decision/);
    await page.locator("body").press("m");
    const first = page.locator('.decision-list [data-unresolved-field="true"]').first();
    await expect(first.locator("[data-primary-action]").first()).toBeFocused();
    // The dock sits under the inspector, on one row, with the primary action last.
    const [inspector, dock] = await Promise.all([
      rect(page, ".review-inspector"),
      rect(page, ".record-decision-dock"),
    ]);
    expect(dock.y).toBeGreaterThanOrEqual(inspector.bottom - 1);
    expect(dock.right).toBeGreaterThanOrEqual(inspector.right - 1);
  });

  test("each pane scrolls on its own, and the page does not move", async ({ page }) => {
    await open(page);
    const before = await page.evaluate(() => scrollY);
    const queue = page.locator(".records-pane");
    expect(await queue.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    // Drive the pane directly instead of relying on a synthetic wheel gesture landing on
    // the intended scroll container. The neighboring edge-propagation test below exercises
    // wheel chaining; this assertion is specifically about independent pane scrolling.
    await queue.evaluate((el) => el.scrollBy({ top: 400, behavior: "instant" }));
    await expect.poll(() => queue.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
    expect(await page.evaluate(() => scrollY)).toBe(before);
  });

  test("scrolling passes to the page at the edge of a pane, so nothing above the workspace is out of reach", async ({
    page,
  }) => {
    await open(page);
    const before = await page.evaluate(() => scrollY);
    expect(before, "the workspace is scrolled into place").toBeGreaterThan(0);
    for (const selector of [".records-pane", ".record-review-pane", ".review-inspector"]) {
      await page.evaluate((y) => scrollTo(0, y), before);
      const box = (await page.locator(selector).first().boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + 80);
      await page.mouse.wheel(0, -1200); // each pane is already at its top
      await expect
        .poll(() => page.evaluate(() => scrollY), { message: `wheel over ${selector}` })
        .toBeLessThanOrEqual(before);
    }
  });

  test("a record's state is shown by a shape and its name, not by colour alone", async ({
    page,
  }) => {
    await open(page);
    const rows = page.locator(".record-row");
    expect(await rows.count()).toBeGreaterThan(5);
    for (const row of await rows.all()) {
      await expect(row.locator(".record-state-icon")).toHaveCount(1);
      expect((await row.locator(".record-row-status").innerText()).trim().length).toBeGreaterThan(
        0,
      );
    }
    // The status is stated once: a row never repeats it in a second line.
    const texts = await page
      .locator(".record-row")
      .first()
      .evaluate((el) => (el.textContent || "").toLowerCase());
    expect(texts.split("metadata").length - 1).toBeLessThanOrEqual(1);
  });

  test("More actions is a menu: it says why an action is unavailable and returns focus on Escape", async ({
    page,
  }) => {
    await open(page);
    const trigger = page.getByRole("button", { name: /More (record )?actions/ });
    await trigger.focus();
    await page.keyboard.press("Enter");
    const menu = page.getByRole("menu");
    await expect(menu).toBeVisible();
    // The first record has no previous record to combine with.
    const combine = menu.getByRole("menuitem", { name: /Combine with previous record/ });
    await expect(combine).toHaveAttribute("aria-disabled", "true");
    await expect(combine).toContainText("no previous record");
    await page.keyboard.press("ArrowDown");
    await expect(menu.getByRole("menuitem").nth(1)).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
    await expect(trigger).toBeFocused();
  });

  test("the panes can be resized from the keyboard, and the size is remembered", async ({
    page,
  }) => {
    await open(page);
    const width = () =>
      page
        .locator(".review-grid")
        .evaluate((el) => parseInt((el as HTMLElement).style.getPropertyValue("--rw-queue")));
    const separator = page.getByRole("separator", { name: /Resize review queue/ });
    await expect(separator).toHaveAttribute("aria-valuenow", "256");
    await separator.focus();
    await page.keyboard.press("ArrowRight");
    expect(await width()).toBe(272);
    await page.keyboard.press("Shift+ArrowRight");
    expect(await width()).toBe(336);
    await page.keyboard.press("Home");
    expect(await width()).toBe(224);
    await page.keyboard.press("ArrowRight");
    await page.reload();
    await page.locator(".review-grid").waitFor();
    expect(await width()).toBe(240);
  });

  test("record navigation is immediate and restores the local text draft", async ({ page }) => {
    await open(page);
    let writes = 0;
    page.on("request", (request) => {
      if (request.method() === "PATCH" && request.url().endsWith("/text")) writes++;
    });
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page
      .locator(".record-review-pane textarea")
      .fill("An unsaved correction with its negation intact.");
    await page.locator(".record-row").nth(1).click();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
    await expect(page.getByRole("dialog", { name: "Leave this unsaved review?" })).toHaveCount(0);
    await page.locator(".record-row").nth(0).click();
    await expect(page.locator(".record-review-pane textarea")).toHaveValue(
      "An unsaved correction with its negation intact.",
    );
    expect(writes).toBe(0);
  });

  test("an unsaved field does not block Reject and next", async ({ page }) => {
    const records = CORPUS_RECORDS.map((record) => ({ ...record, state_version: 1 }));
    const fixtures: Fixtures = {
      [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: (url: URL) => {
        const offset = Number(url.searchParams.get("offset") || 0);
        const limit = Number(url.searchParams.get("limit") || 50);
        return {
          items: records.slice(offset, offset + limit),
          total: records.length,
          offset,
          limit,
        };
      },
    };
    await open(page, fixtures);
    const build = await page.evaluate(
      async (buildId) => (await fetch(`/api/pdf/corpus-builds/${buildId}`)).json(),
      CORPUS_BUILD_ID,
    );
    await page.route(
      `**/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/${CORPUS_RECORDS[0].record_id}/review-decision`,
      (route) => {
        records[0] = {
          ...records[0],
          review_disposition: "rejected",
          review_state: "rejected",
          rejected: true,
          accepted: false,
          needs_review: false,
          record_revision: 2,
          state_version: 2,
        };
        fixtures[`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`] = {
          ...build,
          review_queue_data_generation: 2,
          rejected_count: build.rejected_count + 1,
          review_queue_counts: {
            ...build.review_queue_counts,
            rejected: build.review_queue_counts.rejected + 1,
            pending: build.review_queue_counts.pending - 1,
            metadata: build.review_queue_counts.metadata - 1,
            issues: build.review_queue_counts.issues - 1,
          },
        };
        return route.fulfill({
          json: {
            applied: true,
            blocked: false,
            build: fixtures[`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`],
            record: records[0],
            next_record: CORPUS_RECORDS[1],
          },
        });
      },
    );
    await page.locator(".decision-list textarea").first().fill("An uncommitted field value.");
    await page.getByRole("button", { name: "Reject & next", exact: true }).click();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
    await expect(page.locator(".record-row").first()).toContainText("rejected");
    await expect(page.getByRole("dialog", { name: "Leave this unsaved review?" })).toHaveCount(0);
  });

  test("sequential pages use live cursors and retain the current page's actual offset", async ({
    page,
  }) => {
    const reads: Array<{ offset?: number; cursor?: string; direction?: string }> = [];
    page.on("request", (request) => {
      if (!request.url().endsWith("/api/graphql")) return;
      const body = request.postDataJSON();
      if (body.operationName === "CorpusReviewQueue") reads.push(body.variables);
    });
    await open(page);
    await page
      .getByRole("group", { name: "Queue pages" })
      .getByRole("button", { name: "Next", exact: true })
      .click();
    await expect(page.locator(".record-row").first()).toContainText(CORPUS_RECORDS[50].record_id);
    expect(reads.at(-1)?.cursor).toBeTruthy();
    expect(reads.at(-1)?.direction).toBe("forward");
    await page
      .getByRole("group", { name: "Queue pages" })
      .getByRole("button", { name: "Previous", exact: true })
      .click();
    await expect(page.locator(".record-row").first()).toContainText(CORPUS_RECORDS[0].record_id);
    expect(reads.at(-1)?.cursor).toBeTruthy();
    expect(reads.at(-1)?.direction).toBe("backward");
    await expect(
      page
        .getByRole("group", { name: "Queue pages" })
        .getByRole("button", { name: "Previous", exact: true }),
    ).toBeDisabled();
  });

  test("starting another build preserves the local text draft without a dialog", async ({
    page,
  }) => {
    await open(page);
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page
      .locator(".record-review-pane textarea")
      .fill("A draft before starting another build.");
    await page.getByRole("button", { name: "Start new build", exact: true }).click();
    await expect(page).toHaveURL(/workspace=setup/);
    await expect(page.getByRole("dialog", { name: "Leave this unsaved review?" })).toHaveCount(0);
    expect(
      await page.evaluate(
        ({ build, record }) =>
          localStorage.getItem(`derridai.pdf-corpus.text-draft.${build}.${record}`),
        { build: CORPUS_BUILD_ID, record: CORPUS_RECORDS[0].record_id },
      ),
    ).toBe("A draft before starting another build.");
  });

  test("a restored advanced metadata draft does not trap navigation", async ({ page }) => {
    await page.addInitScript(
      ({ buildId, recordId }) =>
        localStorage.setItem(
          `derridai.pdf-corpus.metadata-draft.${buildId}.${recordId}`,
          JSON.stringify({ speaker: "A saved but uncommitted metadata draft" }),
        ),
      { buildId: CORPUS_BUILD_ID, recordId: CORPUS_RECORDS[0].record_id },
    );
    await open(page);
    await page.locator(".record-row").nth(1).click();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
    await expect(page.getByRole("dialog", { name: "Leave this unsaved review?" })).toHaveCount(0);
    expect(
      await page.evaluate(
        ({ build, record }) =>
          localStorage.getItem(`derridai.pdf-corpus.metadata-draft.${build}.${record}`),
        { build: CORPUS_BUILD_ID, record: CORPUS_RECORDS[0].record_id },
      ),
    ).toContain("A saved but uncommitted metadata draft");
  });
});

test.describe("on a laptop", () => {
  test.use({ viewport: { width: 1024, height: 768 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the queue and the record sit side by side, with the inspector below, all in the window", async ({
    page,
  }) => {
    await open(page);
    const [queue, record, inspector, bar] = await Promise.all(
      [".records-pane", ".record-review-pane", ".review-inspector", ".decision-bar"].map((s) =>
        rect(page, s),
      ),
    );
    expect(queue.x).toBeLessThan(record.x);
    expect(Math.abs(queue.y - record.y)).toBeLessThanOrEqual(2);
    expect(inspector.y).toBeGreaterThanOrEqual(record.bottom - 2);
    expect(inspector.bottom).toBeLessThanOrEqual(768);
    expect(bar.bottom, "the decisions are still in the window").toBeLessThanOrEqual(768);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      "and nothing overflows sideways",
    ).toBe(true);
  });
});

test.describe("at a small laptop width", () => {
  test.use({ viewport: { width: 1280, height: 720 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the inspector tabs stay on one row and the decision bar does not overlap itself", async ({
    page,
  }) => {
    await open(page);
    const tabs = await page
      .locator(".review-inspector-tabs button")
      .evaluateAll((els) => els.map((el) => Math.round(el.getBoundingClientRect().top)));
    expect(tabs.length).toBeGreaterThanOrEqual(4);
    expect(new Set(tabs).size, "every tab shares one row").toBe(1);
    const blocker = await rect(page, ".dock-blocker");
    const history = await rect(page, ".decision-history");
    expect(blocker.right, "the blocker stops before the undo/redo buttons").toBeLessThanOrEqual(
      history.x + 1,
    );
  });
});

test.describe("on a short window", () => {
  test.use({ viewport: { width: 1366, height: 650 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the decisions stay on one row and the record text is readable", async ({ page }) => {
    await open(page);
    const bar = await rect(page, ".decision-bar");
    expect(bar.h).toBeLessThanOrEqual(72);
    const text = await rect(page, ".record-primary-text");
    const dock = await rect(page, ".record-decision-dock");
    // At least a couple of lines of the record show above the dock.
    expect(Math.min(text.bottom, dock.y) - text.y).toBeGreaterThan(60);
    // The compact menu is still named for assistive technology.
    await expect(page.getByRole("button", { name: /More (record )?actions/ })).toBeVisible();
  });
});

for (const viewport of [
  { width: 390, height: 844, name: "mobile" },
  { width: 720, height: 450, name: "200 percent zoom-equivalent" },
]) {
  test.describe(`at the ${viewport.name} viewport`, () => {
    test.use({ viewport: { width: viewport.width, height: viewport.height } });
    test.beforeEach(({}, info) =>
      test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
    );
    test("reflows without horizontal overflow and keeps text and decisions reachable", async ({
      page,
    }) => {
      await open(page);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(
        true,
      );
      await page.locator(".record-primary-text .ctx-focus").scrollIntoViewIfNeeded();
      await expect(page.locator(".record-primary-text .ctx-focus")).toContainText("hospitality");
      const accept = page.getByRole("button", { name: "Accept & next", exact: true });
      await accept.scrollIntoViewIfNeeded();
      await expect(accept).toBeInViewport();
      await page
        .getByRole("button", { name: "Reject & next", exact: true })
        .scrollIntoViewIfNeeded();
      expect(
        (
          await new AxeBuilder({ page })
            .include(".review-grid")
            .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
            .analyze()
        ).violations,
      ).toEqual([]);
    });
  });
}

test.describe("French review controls in dark mode", () => {
  test.use({ viewport: { width: 1280, height: 720 }, colorScheme: "dark" });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewport."),
  );
  test("keeps French keyboard navigation immediate with a recoverable draft", async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem("derridai-locale", "fr-CA"));
    await mockBackend(page);
    await page.route("**/api/i18n/languages/fr-CA", (route) =>
      route.fulfill({
        json: {
          code: "fr-CA",
          name: "Français",
          flag: "🇨🇦",
          dictionary: {
            "pdf_corpus.reject_next": "Rejeter et suivante",
          },
        },
      }),
    );
    await page.goto(`${APP}/pdf`);
    await page.locator(".review-grid").waitFor();
    await expect(page.locator("html")).toHaveAttribute("lang", "fr-CA");
    await expect(page.locator("html")).toHaveAttribute("data-color-scheme", "dark");
    await expect(
      page.getByRole("button", { name: "Rejeter et suivante", exact: true }),
    ).toBeVisible();
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page.locator(".record-review-pane textarea").fill("Une correction non enregistrée.");
    await page.locator(".record-row").nth(1).click();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await page.locator(".record-row").nth(0).focus();
    await page.keyboard.press("Enter");
    await expect(page.locator(".record-review-pane textarea")).toHaveValue(
      "Une correction non enregistrée.",
    );
  });
});
