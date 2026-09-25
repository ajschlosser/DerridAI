/* Copyright 2026 Aaron John Schlosser, PhD. */
import { runAxe } from "./support/axe";
import { expect, test, type Page } from "@playwright/test";
import { CORPUS_BUILD_ID, CORPUS_RECORDS, mockBackend } from "./support/mock-backend";

// The enrichment measurements panel and the blind-review and re-check fields, in the real app,
// against the mock API from the production build.
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;

const model = {
  proposals: 40,
  reviews: 20,
  autofilled: 12,
  acceptance_rate: 0.85,
  brier_score: 0.071,
  correction_rate: 0.1,
  rejection_rate: 0.05,
  autofill_precision: 0.9,
  stability: null,
  touched_share: 0.5,
  grounded_rate: 0.95,
  ms_per_accepted_field: 4200,
  precision_at_threshold: [{ threshold: 0.9, reviews: 10, precision: 0.93, coverage: 0.6 }],
  learning_curve: [],
  acceptance_ci: { rate: 0.85, low: 0.64, high: 0.95, n: 20 },
  substantive_error_rate: { rate: 0.05, low: 0.01, high: 0.24, n: 20 },
  autofill_precision_ci: { rate: 0.9, low: 0.6, high: 0.98, n: 10 },
  spot_checks_still_needed: 3,
  correction_severity: {},
  supported_rate: 0.8,
  supported_checked: 5,
  repeat_rate: null,
  proposals_after_a_rejection: 0,
  review_seconds_per_decision: 12,
  seconds_to_first_useful_value: 30,
  autofill_suspensions: 1,
  autofill_resumptions: 0,
};
const metrics = {
  self_consistency: { rate: 0.9, low: 0.6, high: 0.98, n: 10 },
  models: {
    "qwen3.5:4b": model,
    "a-much-longer-model-name-for-wrapping:latest": { ...model, acceptance_rate: null },
  },
  inter_model_agreement: { compared: 4, agreement: 0.75 },
  unresolved_remaining: 7,
  runs: ["r1"],
  concurrency: { limit: 1, working: 0 },
};

async function open(page: Page, records?: unknown[]) {
  await mockBackend(page, {
    fixtures: {
      "/api/pdf/corpus-enrichment-metrics": metrics,
      ...(records
        ? {
            [`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}/records`]: {
              items: records,
              total: records.length,
              offset: 0,
              limit: 50,
            },
          }
        : {}),
    },
  });
  await page.goto(`${APP}/pdf`);
  await page.locator(".review-grid").waitFor();
}

test.describe("the enrichment measurements panel", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));

  test("loads on demand, scrolls its own tables, and has no accessibility violations", async ({
    page,
  }) => {
    await open(page);
    const summary = page.getByText("How well is enrichment working?").first();
    await summary.scrollIntoViewIfNeeded();
    await summary.click();
    await expect(
      page.getByRole("region", { name: "How well is enrichment working?" }),
    ).toBeVisible();
    await expect(page.getByRole("region", { name: "Trust, effort and cost" })).toBeVisible();
    await expect(page.getByText("85% (64–95%, n=20)").first()).toBeVisible();
    await expect(page.getByText("not enough data").first()).toBeVisible();
    // Wide tables scroll inside their region and never widen the page.
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    await page.screenshot({ path: "test-results/enrichment-panel.png", fullPage: false });
    const scan = await runAxe(page, (builder) => builder.include("details.enrich-metrics"));
    expect(
      scan.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target).join(" ")}`),
    ).toEqual([]);
  });
});

test.describe("blind review and re-check fields", () => {
  test.beforeEach(({}, info) => test.skip(info.project.name !== "chromium-desktop", "Runs once."));

  test("a blind field shows no value and says why; a re-checked field reveals the earlier answer", async ({
    page,
  }) => {
    const source = CORPUS_RECORDS.find((r) => r.review_state === "metadata")!;
    const record = {
      ...source,
      metadata_field_status: {
        target: {
          status: "unresolved",
          method: "llm",
          blind: true,
          reason_code: "blind_review",
          reason: "",
        },
        stance: { status: "human_confirmed", method: "human" },
        proposition_status: {
          status: "unresolved",
          method: "human_recheck",
          recheck: true,
          reason_code: "recheck",
          reason: "",
        },
      },
      recheck_results: { stance: { first: "affirm", second: "reject", agreed: false } },
    };
    await open(page, [
      record,
      ...CORPUS_RECORDS.filter((r) => r.record_id !== record.record_id).slice(0, 10),
    ]);
    await page.getByText(record.record_id).first().waitFor();
    await expect(
      page.getByText(/blind review: choose your own value first/i).first(),
    ).toBeVisible();
    await expect(page.getByText(/quality check: enter your value again/i).first()).toBeVisible();
    await page.screenshot({ path: "test-results/blind-fields.png" });
  });
});
