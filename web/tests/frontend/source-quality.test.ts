import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { assetHasExtractionWarning, recordHasSourceWarning } from "../../src/domain/sourceQuality";
import CorpusRecordFocusReview from "../../src/components/CorpusRecordFocusReview.vue";

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
