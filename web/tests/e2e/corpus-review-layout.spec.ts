/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend } from "./support/mock-backend";

// The Corpus Builder review workspace in the real app: it should fill the screen under the top bar,
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

  test("the workspace fills the screen under the top bar and adds no phantom scroll", async ({
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
    expect(m.bottom, "and reaches the bottom of the window").toBeGreaterThan(m.view - 24);
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

  test("each pane scrolls on its own, and the page does not move", async ({ page }) => {
    await open(page);
    const before = await page.evaluate(() => scrollY);
    const queue = page.locator(".records-pane");
    expect(await queue.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    await queue.hover();
    await page.mouse.wheel(0, 400);
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
