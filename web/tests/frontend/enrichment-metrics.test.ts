import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import CorpusEnrichmentMetrics from "../../src/components/CorpusEnrichmentMetrics.vue";
import { pdfCorpusApi } from "../../src/api/pdfCorpus";

const model = (over = {}) => ({
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
  ...over,
  acceptance_ci: { rate: 0.85, low: 0.64, high: 0.95, n: 20 },
  substantive_error_rate: { rate: 0.05, low: 0.01, high: 0.24, n: 20 },
  autofill_precision_ci: { rate: null, low: null, high: null, n: 0 },
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
});

describe("Enrichment metrics", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("loads only when opened, shows a row per model, and says when data is missing", async () => {
    const spy = vi.spyOn(pdfCorpusApi, "enrichmentMetrics").mockResolvedValue({
      models: { qwen3: model() },
      inter_model_agreement: { compared: 0, agreement: null },
      unresolved_remaining: 7,
      runs: ["r1"],
      concurrency: { limit: 1, working: 0 },
    });
    const wrapper = mount(CorpusEnrichmentMetrics, {
      props: { buildId: "b1" },
      attachTo: document.body,
    });
    expect(spy).not.toHaveBeenCalled();
    const details = wrapper.find("details").element as HTMLDetailsElement;
    details.open = true;
    details.dispatchEvent(new Event("toggle"));
    await flushPromises();
    expect(spy).toHaveBeenCalledWith("b1");
    const row = wrapper.find("tbody tr").text();
    expect(row).toContain("qwen3");
    expect(row).toContain("85%");
    expect(row).toContain("0.071");
    expect(row).toContain("4.2 s");
    expect(row).toContain("not enough data"); // stability had no repeat runs
    expect(wrapper.text()).toContain("7");
    expect(wrapper.text()).toContain("85% (64–95%, n=20)");
    expect(wrapper.find("a[download]").attributes("href")).toContain("enrichment-ledger.csv");
    wrapper.unmount();
  });
});
