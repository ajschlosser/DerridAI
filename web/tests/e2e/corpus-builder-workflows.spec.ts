import { expect, test } from "@playwright/test";
import { runAxe } from "./support/axe";

async function expectWcag2AA(page: any, include: string) {
  await page.waitForTimeout(100);
  for (let attempt = 0; attempt < 3; attempt += 1) {
    try {
      const results = await runAxe(page, (builder) =>
        builder.include(include).withTags(["wcag2a", "wcag2aa"]),
      );
      expect(results.violations, JSON.stringify(results.violations, null, 2)).toEqual([]);
      return;
    } catch (error) {
      if (!String(error).includes("Axe is already running") || attempt === 2) throw error;
      await page.waitForTimeout(250);
    }
  }
}
async function expectNoHorizontalOverflow(locator: any) {
  const metrics = await locator.evaluate((el: HTMLElement) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth + 1);
}
const story = (id: string) => "/iframe.html?id=" + id + "&viewMode=story";

test.describe("Corpus Builder composed workflow", () => {
  test("French length stories declare their language to assistive technology", async ({ page }) => {
    await page.goto(story("corpus-builder-workflow-workspace-header--french-length-stress"));
    await expect(page.locator("html")).toHaveAttribute("lang", "fr-CA");
    await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  });

  test("setup sections expose one disclosure each with their state and summary", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-setup-section--expanded"));
    const toggle = page.locator(".corpus-setup-section-toggle");
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator(".corpus-setup-indicator")).toHaveText("1");
    await expect(toggle).toContainText("Of Grammatology.pdf");
    await expect(page.locator(".corpus-setup-state")).toContainText(/Complete/i);
    await expect(page.locator(".corpus-setup-section-body")).toBeVisible();
    await toggle.focus();
    await expect(toggle).toBeFocused();
    await expectWcag2AA(page, ".corpus-setup-section");

    await page.goto(story("corpus-builder-setup-section--complete-collapsed"));
    await expect(page.locator(".corpus-setup-section-toggle")).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    await expect(page.locator(".corpus-setup-section-body")).toBeHidden();

    await page.goto(story("corpus-builder-setup-section--warning"));
    await expect(page.locator(".corpus-setup-section-toggle")).toBeVisible();
    await expect(page.locator(".corpus-setup-indicator")).toHaveText("3");
    await expectWcag2AA(page, ".corpus-setup-section");

    await page.goto(story("corpus-builder-setup-section--french-length-stress"));
    const longSection = page.locator(".corpus-setup-section");
    await expectNoHorizontalOverflow(longSection);
    await expectWcag2AA(page, ".corpus-setup-section");
  });

  test("workspace header shifts from introduction to active build context", async ({ page }) => {
    await page.goto(story("corpus-builder-workflow-workspace-header--empty-workspace"));
    const header = page.locator(".corpus-workspace-header");
    await expect(header).not.toHaveClass(/contextual/);
    await expect(header).toContainText(/Corpus Builder/i);

    await page.goto(story("corpus-builder-workflow-workspace-header--active-build"));
    const active = page.locator(".corpus-workspace-header");
    await expect(active).toHaveClass(/contextual/);
    await expect(active).toContainText("Of Grammatology.pdf");
    await expect(active).toContainText(/31 of 84 Records accepted/i);
    await expectWcag2AA(page, ".corpus-workspace-header");
  });

  test("the header navigation shows the three researcher-facing phases and current phase", async ({
    page,
  }) => {
    const states = [
      ["corpus-builder-workflow-workspace-header--empty-workspace", "Setup"],
      ["corpus-builder-workflow-workspace-header--active-build", "Build & review"],
      ["corpus-builder-workflow-workspace-header--published", "Publish"],
    ];
    for (const [id, label] of states) {
      await page.goto(story(id));
      const nav = page.locator(".workspace-mode-nav");
      await expect(nav.locator(".workspace-phase-list").getByRole("button")).toHaveCount(3);
      const current = nav.locator('[aria-current="step"]');
      await expect(current).toBeVisible();
      await expect(current).toContainText(label);
      await expectWcag2AA(page, ".corpus-workspace-header");
    }

    await page.goto(story("corpus-builder-workflow-workspace-header--active-build"));
    const subnav = page.locator(".workspace-subnav");
    await expect(subnav.getByRole("button")).toHaveCount(2);
    await expect(subnav.getByRole("button", { name: "Review" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );

    await page.goto(story("corpus-builder-workflow-workspace-header--empty-workspace"));
    await expect(page.getByRole("button", { name: /^Build & review/ })).toBeDisabled();
  });

  test("document structure remains usable in the narrow laptop composition", async ({ page }) => {
    await page.goto(story("corpus-builder-source-document-structure-pagination--narrow-laptop"));
    const surface = page.locator(".structure-config");
    await expect(surface).toBeVisible();
    await expectNoHorizontalOverflow(surface);
    await expect(page.getByRole("button", { name: /Save document structure/i })).toBeDisabled();
    await page.getByRole("button", { name: /Next/i }).click();
    await page.getByRole("button", { name: /Set current as main-text start/i }).click();
    await expect(page.getByText(/Unsaved changes/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /Save document structure/i })).toBeEnabled();
    await expectWcag2AA(page, ".structure-config");
  });

  test("advanced execution exposes unsafe context as an alert", async ({ page }) => {
    await page.goto(story("corpus-builder-settings-execution--unsafe-context"));
    const shell = page.locator(".execution-settings-shell");
    await expect(shell).toHaveAttribute("open", "");
    await expect(page.locator(".context-check")).toHaveAttribute("role", "alert");
    await expect(page.locator(".context-check")).toContainText(/Context budget is too small/i);
    await expectNoHorizontalOverflow(shell);
    await expectWcag2AA(page, ".execution-settings-shell");
  });

  test("build telemetry makes unresolved provenance and validation state visible", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-build-telemetry--provenance-hazard"));
    const surface = page.locator(".corpus-build-telemetry");
    await expect(page.locator(".unresolved-line")).toContainText("1");
    await expect(surface).toContainText(/boundary decision/i);
    await expectNoHorizontalOverflow(surface);
    await expectWcag2AA(page, ".corpus-build-telemetry");
  });

  test("build primary status is the one progress surface, with stages and next actions", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-build-primary-status--enriching"));
    const status = page.locator(".corpus-build-primary-status");
    await expect(status.getByRole("heading", { name: "Enriching metadata" })).toBeVisible();
    await expect(status.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "58");
    await expect(status.locator('[aria-current="step"]')).toContainText("Enrich");
    await expect(status.locator('[data-flow-state="ready"]')).toContainText("36");
    await expect(status.locator('[data-flow-state="enriching"]')).toContainText("274");
    await expect(status.locator('[data-flow-state="attention"]')).toContainText("17");
    await expect(status.getByRole("button", { name: "Review 36 ready Records" })).toBeVisible();
    await expect(status.getByRole("button", { name: "Pause" })).toBeVisible();
    await expectNoHorizontalOverflow(status);
    await expectWcag2AA(page, ".corpus-build-primary-status");

    await page.goto(story("corpus-builder-build-primary-status--ready-for-review"));
    await expect(page.getByRole("button", { name: "Review Records" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Publication readiness" })).toBeVisible();
  });

  test("publish workspace leads with readiness and hands off to review", async ({ page }) => {
    await page.goto(story("corpus-builder-publish-workspace--unreviewed-records"));
    await expect(page.locator("#corpus-publish-title")).toContainText(
      "31 Records remain unreviewed",
    );
    await expect(
      page.getByRole("button", { name: "Use suggestions as-is & publish" }),
    ).toBeVisible();
    await expectWcag2AA(page, ".corpus-publish-workspace");
    await page.goto(story("corpus-builder-publish-workspace--published"));
    await expect(page.locator("#corpus-publish-title")).toHaveText("Published");
    await expect(page.locator(".publication-blockers")).toHaveCount(0);
  });

  test("initialization is an inline panel, not a modal, while topology is being prepared", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-build-initialization-dialog--segmenting"));
    const panel = page.locator(".init-panel");
    await expect(panel).toBeVisible();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(page.locator("[aria-modal]")).toHaveCount(0);
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "18");
    await expect(page.getByRole("button", { name: /Cancel build/i })).toBeEnabled();
    await expectWcag2AA(page, ".init-panel");
  });

  test("actively enriching records use a spinner and explicit Enriching status", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-review-record-queue--mixed-states"));
    const preparing = page
      .locator(".record-row")
      .filter({ has: page.locator('[data-state="preparing"]') })
      .first();
    await expect(preparing).toContainText("Enriching");
    await expect(preparing.locator(".record-processing-spinner")).toBeVisible();
    await expect(preparing.locator(".record-state-icon svg")).toHaveCount(0);
    await expectWcag2AA(page, ".records-pane");
  });

  test("review queue is one keyboard-operable filter list that includes the issue kinds", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-review-queue-tabs--metadata-queue"));
    const filter = page.locator("[data-review-queue-select]");
    await expect(filter).toHaveValue("metadata");
    await expect(filter.locator("option")).toContainText([/All/, /Ready/, /Needs attention/]);
    await filter.focus();
    await filter.selectOption("accepted");
    await expect(filter).toHaveValue("accepted");
    await expectWcag2AA(page, ".queue-controls");
  });

  test("focus review supports keyboard tabs and reviewed-text editing", async ({ page }) => {
    await page.goto(story("corpus-builder-review-focus-view--pending"));
    const dialog = page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const metadata = page.locator("#focus-tab-metadata");
    await metadata.focus();
    await metadata.press("ArrowRight");
    await expect(page.locator("#focus-tab-evidence")).toBeFocused();
    await expect(page.locator("#focus-tab-evidence")).toHaveAttribute("aria-selected", "true");
    await page.getByRole("button", { name: /Edit text/i }).click();
    const editor = page.locator("textarea.focus-text-editor");
    await expect(editor).toBeVisible();
    await editor.fill("A corrected reviewed passage.");
    await editor.press("Control+s");
    await expect(editor).toHaveCount(0);
    await expectWcag2AA(page, ".focus-review");
  });

  test("metadata review distinguishes ambiguous and inherited states", async ({ page }) => {
    await page.goto(story("corpus-builder-review-metadata-resolution--ambiguous-fields"));
    await expect(page.locator(".review-status")).toContainText(/decision/i);
    // The tab lists what needs review first; "Add more details" below it has a list of its own.
    await expect(page.locator('.metadata-grid[role="list"]').first()).toBeVisible();
    await expectWcag2AA(page, ".metadata-review");
    await page.goto(
      story("corpus-builder-review-metadata-resolution--inherited-and-overridden-bibliography"),
    );
    await expect(page.locator(".inherited-metadata")).toBeVisible();
    await expect(page.locator(".inherited-metadata")).toContainText(/Inherited document metadata/i);
    await expectWcag2AA(page, ".metadata-review");
  });

  test("finish workspace covers publishable, mixed, and all-rejected outcomes", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-workflow-finish-workspace--ready-to-publish"));
    await expect(page.getByRole("button", { name: /Publish corpus/i })).toBeEnabled();
    await expectWcag2AA(page, ".finish-workspace");
    await page.goto(story("corpus-builder-workflow-finish-workspace--mixed-accepted-and-rejected"));
    await expect(page.locator(".finish-workspace")).toContainText("40");
    await expect(page.locator(".finish-workspace")).toContainText("23");
    await page.goto(story("corpus-builder-workflow-finish-workspace--no-publishable-records"));
    await expect(page.locator(".no-publishable")).toContainText(
      /All records are currently rejected/i,
    );
    await expect(page.getByRole("button", { name: /Restore all rejected/i })).toBeEnabled();
    await expectWcag2AA(page, ".finish-workspace");
  });

  test("review dialogs remain modal, width-safe, and accessible", async ({ page }) => {
    const dialogs = [
      "corpus-builder-review-llm-text-touch-up--proposal",
      "corpus-builder-review-metadata-enrichment-dialog--default",
      "corpus-builder-review-text-cleanup--default",
      "corpus-builder-review-bulk-metadata-editor--default",
      "corpus-builder-review-jsonl-preview--blocked",
    ];
    for (const id of dialogs) {
      await page.goto(story(id));
      const dialog = page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await expectNoHorizontalOverflow(dialog);
      await expectWcag2AA(page, '[role="dialog"]');
    }
  });

  test("compact source and provider-switch surfaces stay usable without overflow", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-source-compact-source-summary--narrow-inspector"));
    const source = page.locator(".source-summary");
    await expect(source).toBeVisible();
    await expectNoHorizontalOverflow(source);
    await expectWcag2AA(page, ".source-summary");
    await page.goto(story("corpus-builder-enrichment-provider-switcher--default"));
    const provider = page.locator(".provider-switcher");
    await expect(provider).toBeVisible();
    await expectNoHorizontalOverflow(provider);
    await expectWcag2AA(page, ".provider-switcher");
  });

  test("finish and review surfaces survive 200 percent zoom-equivalent scaling", async ({
    page,
  }) => {
    await page.goto(story("corpus-builder-workflow-finish-workspace--french-length-stress"));
    await page.evaluate(() => {
      document.documentElement.style.zoom = "2";
    });
    const finish = page.locator(".finish-workspace");
    await expect(finish).toBeVisible();
    await expectNoHorizontalOverflow(finish);
    await expectWcag2AA(page, ".finish-workspace");
  });
});
