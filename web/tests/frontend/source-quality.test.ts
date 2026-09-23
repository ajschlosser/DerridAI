import { describe, expect, it, beforeEach } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick, ref } from "vue";
import {
  assetHasExtractionWarning,
  firstRecordWithSourceWarning,
  recordHasSourceWarning,
} from "../../src/domain/sourceQuality";
import { useCorpusIngestWarning } from "../../src/composables/useCorpusIngestWarning";
import CorpusRecordFocusReview from "../../src/components/CorpusRecordFocusReview.vue";
import ProviderProfileSelect from "../../src/components/ProviderProfileSelect.vue";

describe("ProviderProfileSelect availability", () => {
  it("does not offer unavailable profiles while retaining the active one for diagnosis", () => {
    const wrapper = mount(ProviderProfileSelect, {
      props: {
        modelValue: "missing",
        profiles: [
          {
            id: "missing",
            name: "Missing",
            type: "ollama",
            model: "gone",
            available: false,
            availability_error: 'Configured model "gone" was not found.',
          },
          { id: "ready", name: "Ready", type: "ollama", model: "present", available: true },
        ],
      },
    });
    const options = wrapper.findAll("option");
    expect(options).toHaveLength(2);
    expect(options[0].attributes("disabled")).toBeDefined();
    expect(options[1].attributes("disabled")).toBeUndefined();
    expect(wrapper.get(".provider-unavailable").text()).toContain("Unavailable");
    expect(wrapper.get(".provider-unavailable").text()).toContain("gone");
    wrapper.unmount();
  });
});

describe("useCorpusIngestWarning", () => {
  beforeEach(() => sessionStorage.clear());

  it("opens once per asset and acknowledges through session storage", () => {
    let warning!: ReturnType<typeof useCorpusIngestWarning>;
    const asset = ref({ asset_id: "asset-1", extraction_noise: { exceeds_threshold: true } });
    const Host = defineComponent({
      setup() {
        warning = useCorpusIngestWarning(asset);
        return () => h("div");
      },
    });
    const wrapper = mount(Host);

    warning.maybeOpen();
    expect(warning.open.value).toBe(true);
    warning.acknowledge();
    expect(warning.open.value).toBe(false);
    expect(sessionStorage.getItem("derridai.source-quality.seen.asset-1")).toBe("1");
    warning.maybeOpen();
    expect(warning.open.value).toBe(false);
    wrapper.unmount();
  });

  it("does not open for a clean asset", () => {
    let warning!: ReturnType<typeof useCorpusIngestWarning>;
    const asset = ref({ asset_id: "asset-2", extraction_noise: { exceeds_threshold: false } });
    const Host = defineComponent({
      setup() {
        warning = useCorpusIngestWarning(asset);
        return () => h("div");
      },
    });
    const wrapper = mount(Host);
    warning.maybeOpen();
    expect(warning.open.value).toBe(false);
    wrapper.unmount();
  });
});

describe("source extraction warning placement", () => {
  it("flags ingest noise that exceeds the unusable threshold", () => {
    expect(assetHasExtractionWarning({ extraction_noise: { exceeds_threshold: true } })).toBe(true);
    expect(assetHasExtractionWarning({ extraction_noise: { exceeds_threshold: false } })).toBe(false);
    expect(assetHasExtractionWarning({ source_quality: { blocking_page_count: 1 } })).toBe(true);
  });

  it("flags records that still carry source issues", () => {
    expect(recordHasSourceWarning({ source_quality_issues: [{ code: "illegible_text" }] })).toBe(true);
    expect(recordHasSourceWarning({ source_quality_issues: [] })).toBe(false);
  });

  it("finds the first source-problem record after run hydration", () => {
    const clean = { record_id: "clean", source_quality_issues: [] };
    const problem = { record_id: "problem", source_quality_issues: [{ code: "illegible_text" }] };
    expect(firstRecordWithSourceWarning([clean, problem])).toBe(problem);
    expect(firstRecordWithSourceWarning([clean])).toBeUndefined();
  });

  it("puts the source warning on an icon control instead of an inline banner", async () => {
    const record: any = {
      record_id: "record-00014",
      text: "garbled",
      text_length: 7,
      page_start: 1,
      page_end: 1,
      pdf_pages: [1],
      source_block_ids: [],
      source_spans: [],
      needs_review: true,
      review_disposition: "pending",
      source_quality_issues: [{ code: "illegible_text", severity: "blocking", pages: [1] }],
    };
    const wrapper = mount(CorpusRecordFocusReview, {
      attachTo: document.body,
      props: { record },
      global: {
        stubs: {
          CorpusSourceIssuePanel: true,
          CorpusMetadataResolutionPanel: true,
          CorpusTextCleanupDialog: true,
          CorpusRevisionHistory: true,
          CorpusBoundarySliceDialog: true,
          CorpusBoundaryAdjudication: true,
          CorpusSourceSummary: true,
          CorpusSourceQualityDialog: true,
          AppIcon: true,
        },
      },
    });
    await nextTick();
    expect(wrapper.find(".focus-source-issue").exists()).toBe(false);
    expect(wrapper.get(".source-warn-icon").exists()).toBe(true);
    wrapper.unmount();
  });
});
