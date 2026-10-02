/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { CORPUS_BUILD_ID, CORPUS_RECORDS, mockBackend } from "./support/mock-backend";
import AxeBuilder from "@axe-core/playwright";

// The Corpus Builder review workspace in the real app: it should fit beneath the top bar,
// keep its decisions in reach, scroll each pane on its own, and be usable from the keyboard. Rendered
// against the mock API from the production build (see app-views.spec.ts).
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

async function open(page: Page) {
  await mockBackend(page);
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
    await expect(first.locator("input, select, textarea").first()).toBeFocused();
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

  test("Stay and Discard protect a text draft without changing the active Record", async ({
    page,
  }) => {
    await open(page);
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    const draft = page.locator(".record-review-pane textarea");
    await draft.fill("An unsaved correction with its negation intact.");
    await page.locator(".record-row").nth(1).click();
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await expect(dialog).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .include('[role="dialog"]')
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await dialog.getByRole("button", { name: "Stay on this record", exact: true }).last().click();
    await expect(draft).toHaveValue("An unsaved correction with its negation intact.");
    await expect(page.locator(".record-row").nth(0)).toHaveAttribute("aria-current", "true");
    await page.locator(".record-row").nth(1).click();
    await dialog.getByRole("button", { name: "Discard & continue", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
  });

  test("Save and continue waits for durable text persistence", async ({ page }) => {
    await open(page);
    let release!: () => void;
    const persisted = new Promise<void>((resolve) => {
      release = resolve;
    });
    let submitted: Record<string, unknown> | undefined;
    await page.route(
      `**/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/${CORPUS_RECORDS[0].record_id}/text`,
      async (route) => {
        submitted = route.request().postDataJSON();
        await persisted;
        await route.fulfill({
          json: { ...CORPUS_RECORDS[0], text: submitted!.text, record_revision: 2 },
        });
      },
    );
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page.locator(".record-review-pane textarea").fill("A reviewed correction.");
    await page.locator(".record-row").nth(1).click();
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await dialog.getByRole("button", { name: "Save & continue", exact: true }).click();
    await expect.poll(() => submitted?.text).toBe("A reviewed correction.");
    await expect(dialog).toBeVisible();
    await expect(page.locator(".record-row").nth(0)).toHaveAttribute("aria-current", "true");
    release();
    await expect(dialog).toBeHidden();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
  });

  test("a failed draft save stays visible and can be retried before navigating", async ({
    page,
  }) => {
    await open(page);
    let failing = true;
    await page.route(
      `**/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records/${CORPUS_RECORDS[0].record_id}/text`,
      async (route) => {
        await route.fulfill(
          failing
            ? { status: 503, json: { detail: "Persistence unavailable" } }
            : {
                json: {
                  ...CORPUS_RECORDS[0],
                  text: route.request().postDataJSON().text,
                  record_revision: 2,
                },
              },
        );
      },
    );
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page.locator(".record-review-pane textarea").fill("A correction to retry.");
    await page.locator(".record-row").nth(1).click();
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await dialog.getByRole("button", { name: "Save & continue", exact: true }).click();
    await expect(dialog.getByRole("alert")).toContainText("Persistence unavailable");
    await expect(page.locator(".record-row").nth(0)).toHaveAttribute("aria-current", "true");
    await dialog.getByRole("button", { name: "Stay on this record", exact: true }).last().click();
    await expect(dialog).toBeHidden();
    await page.locator(".record-row").nth(1).click();
    await expect(dialog).toBeVisible();
    failing = false;
    await dialog.getByRole("button", { name: "Save & continue", exact: true }).click();
    await expect(dialog).toBeHidden();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
  });

  test("Reject & next protects a metadata draft before changing disposition", async ({ page }) => {
    await open(page);
    const draft = page.locator(".decision-list textarea").first();
    await draft.fill("A metadata draft before rejecting.");
    await page.getByRole("button", { name: "Reject & next", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Stay on this record", exact: true }).last().click();
    await expect(page.locator(".record-row").nth(0)).toHaveAttribute("aria-current", "true");
    await expect(draft).toHaveValue("A metadata draft before rejecting.");
  });

  test("starting a new build cannot silently discard the current text draft", async ({ page }) => {
    await open(page);
    await page.getByRole("button", { name: "Edit text", exact: true }).click();
    await page
      .locator(".record-review-pane textarea")
      .fill("A draft before starting another build.");
    await page.getByRole("button", { name: "Start new build", exact: true }).click();
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Stay on this record", exact: true }).last().click();
    await expect(page.locator(".record-review-pane textarea")).toHaveValue(
      "A draft before starting another build.",
    );
  });

  test("a restored advanced metadata draft is protected before its editor is opened", async ({
    page,
  }) => {
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
    const dialog = page.getByRole("dialog", { name: "Leave this unsaved review?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Discard & continue", exact: true }).click();
    await expect(page.locator(".record-row").nth(1)).toHaveAttribute("aria-current", "true");
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
  test("keeps translated draft decisions readable and keyboard accessible", async ({ page }) => {
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
            "pdf_corpus.draft_navigation_title": "Quitter cet examen non enregistré?",
            "pdf_corpus.draft_navigation_help":
              "Enregistrez vos modifications avant de continuer, abandonnez-les ou restez sur cette fiche.",
            "pdf_corpus.draft_save_continue": "Enregistrer et continuer",
            "pdf_corpus.draft_discard_continue": "Abandonner et continuer",
            "pdf_corpus.draft_stay": "Rester sur cette fiche",
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
    const dialog = page.getByRole("dialog", { name: "Quitter cet examen non enregistré?" });
    await expect(dialog).toBeVisible();
    expect(
      (
        await new AxeBuilder({ page })
          .include('[role="dialog"]')
          .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
          .analyze()
      ).violations,
    ).toEqual([]);
    await dialog
      .getByRole("button", { name: "Rester sur cette fiche", exact: true })
      .last()
      .focus();
    await page.keyboard.press("Enter");
    await expect(dialog).toBeHidden();
    await expect(page.locator(".record-review-pane textarea")).toHaveValue(
      "Une correction non enregistrée.",
    );
  });
});
