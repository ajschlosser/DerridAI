import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusBuildReadiness from "../../src/components/CorpusBuildReadiness.vue";
import CorpusExecutionSettings from "../../src/components/CorpusExecutionSettings.vue";
import CorpusRecordSizingSettings from "../../src/components/CorpusRecordSizingSettings.vue";
import CorpusWorkflowStepper from "../../src/components/CorpusWorkflowStepper.vue";
import DocumentStructureConfigurator from "../../src/components/DocumentStructureConfigurator.vue";

function buttonByText(wrapper: any, text: string) {
  const button = wrapper.findAll("button").find((node: any) => node.text().includes(text));
  if (!button) throw new Error(`Button not found: ${text}`);
  return button;
}
function lastEmission(wrapper: any, event: string) {
  const events = wrapper.emitted(event) || [];
  return events[events.length - 1] || [];
}

describe("Corpus Builder setup and launch controls", () => {
  it("gates launch on source, readiness, context safety, and busy state", async () => {
    const wrapper = mount(CorpusBuildReadiness, { props: { canStart: true, contextSafe: true } });
    const action = wrapper.get(".build-action");
    expect(action.attributes("disabled")).toBeDefined();
    expect(wrapper.attributes("data-ready")).toBe("false");

    await wrapper.setProps({ sourceFilename: "book.pdf", pageCount: 80, blockCount: 300 });
    expect(wrapper.attributes("data-ready")).toBe("true");
    expect(wrapper.get(".build-action").attributes("disabled")).toBeUndefined();
    await wrapper.get(".build-action").trigger("click");
    expect(wrapper.emitted("build")).toHaveLength(1);

    await wrapper.setProps({ busy: true });
    expect(wrapper.get(".build-action").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".build-action").text()).toContain("Starting");

    await wrapper.setProps({ busy: false, contextSafe: false });
    expect(wrapper.get('[role="alert"]').text()).toContain("Context budget");
    expect(wrapper.get(".build-action").attributes("disabled")).toBeDefined();
  });

  it.each([
    [{ stage: "", status: "" }, "1"],
    [{ stage: "segmenting", status: "running" }, "2"],
    [{ stage: "enriching", status: "running", recordCount: 12 }, "3"],
    [{ stage: "ready", status: "ready", canPublish: true }, "4"],
    [{ stage: "published", status: "published", published: true }, "4"],
  ])("maps pipeline state %o onto the correct user-facing lifecycle phase", (props, expected) => {
    const wrapper = mount(CorpusWorkflowStepper, { props });
    const current = wrapper.get('[aria-current="step"]');
    expect(current.get(".marker").text()).toBe(expected);
    expect(current.attributes("data-state")).toBe("current");
  });

  it("keeps record sizing exception limits consistent when the preferred size grows", async () => {
    const wrapper = mount(CorpusRecordSizingSettings, {
      props: {
        modelValue: {
          preferred_record_chars: 1750,
          record_length_tolerance: 200,
          long_record_chars: 3500,
          absolute_record_chars: 6000,
        },
      },
    });
    await wrapper.get("#corpus-preferred-chars").setValue("5000");
    const emitted = wrapper.emitted("update:modelValue");
    expect(emitted).toBeTruthy();
    const next = emitted![emitted!.length - 1][0] as any;
    expect(next.preferred_record_chars).toBe(5000);
    expect(next.long_record_chars).toBeGreaterThanOrEqual(5200);
    expect(next.absolute_record_chars).toBeGreaterThanOrEqual(next.long_record_chars);
  });

  it("clamps execution concurrency and deadlines and exposes unsafe context", async () => {
    const wrapper = mount(CorpusExecutionSettings, {
      props: {
        generation: { num_ctx: 4096 },
        stageLimits: { segmentation_window_tokens: 5000, segmentation_num_predict: 1200 },
        stageTimeouts: { manifest: 300 },
        maxConcurrentRequests: 2,
        useProfileDefaults: false,
      },
    });
    expect(wrapper.get(".context-check").attributes("role")).toBe("alert");
    expect(wrapper.get(".context-check").text()).toContain("Context budget is too small");
    expect(wrapper.get(".execution-settings-shell").attributes("open")).toBeDefined();

    await wrapper.get("#corpus-concurrency").setValue("99");
    expect(lastEmission(wrapper, "update:maxConcurrentRequests")[0]).toBe(16);
    await wrapper.get("#corpus-timeout-manifest").setValue("5");
    const timeout = lastEmission(wrapper, "update:stageTimeouts")[0] as Record<string, number>;
    expect(timeout.manifest).toBe(30);
  });

  it("disables generation overrides when provider defaults are selected", () => {
    const wrapper = mount(CorpusExecutionSettings, {
      props: {
        generation: { num_ctx: 32768, temperature: 0 },
        useProfileDefaults: true,
        maxConcurrentRequests: 2,
      },
    });
    expect(wrapper.get("#corpus-num-ctx").attributes("disabled")).toBeDefined();
    expect(wrapper.get("#corpus-temperature").attributes("disabled")).toBeDefined();
    expect(wrapper.get("#corpus-concurrency").attributes("disabled")).toBeUndefined();
  });

  it("prefills a suggested first main-text page with its clues, and leaves a confirmed one alone", async () => {
    const base: any = {
      asset_id: "asset-2",
      sha256: "sha",
      filename: "clean.pdf",
      created_at: "",
      page_count: 12,
      block_count: 42,
      ocr_pages: 0,
      warnings: [],
      metadata: {},
      pages: Array.from({ length: 12 }, (_, index) => ({
        pdf_page: index + 1,
        width: 612,
        height: 792,
      })),
      main_text_start_inference: {
        page: 7,
        confidence: 0.93,
        offered: true,
        clues: [
          { kind: "outline_first_chapter", detail: "Bookmark “Chapter One” points to PDF page 7." },
        ],
      },
    };
    const mountWith = (asset: any) =>
      mount(DocumentStructureConfigurator, {
        props: { asset, pdfUrl: "/c.pdf", blocks: [] },
        global: { stubs: { PdfEvidenceViewer: true, PdfPageLabelEditor: true } },
      });
    const suggested = mountWith({ ...base, document_layout: null });
    expect((suggested.get(".anchor input").element as HTMLInputElement).value).toBe("7");
    expect(suggested.text()).toContain("93% confident");
    expect(suggested.text()).toContain("Chapter One");
    expect(
      buttonByText(suggested, "Save document structure").attributes("disabled"),
    ).toBeUndefined(); // the reviewer confirms it by saving
    const confirmed = mountWith({
      ...base,
      document_layout: {
        page_layout: "single",
        reading_order: "left_to_right",
        thread_mode: "continuous",
        main_text_pdf_start: 9,
        confirmed_by: "human",
      },
    });
    expect(confirmed.text()).not.toContain("confident");
  });

  it("puts Save document structure below the PDF, not above it", () => {
    const asset: any = {
      asset_id: "asset-3",
      sha256: "sha",
      filename: "book.pdf",
      created_at: "",
      page_count: 12,
      block_count: 42,
      ocr_pages: 0,
      warnings: [],
      metadata: {},
      document_layout: null,
      pages: Array.from({ length: 12 }, (_, index) => ({
        pdf_page: index + 1,
        width: 612,
        height: 792,
      })),
    };
    const wrapper = mount(DocumentStructureConfigurator, {
      props: { asset, pdfUrl: "/book.pdf", blocks: [] },
      global: {
        stubs: {
          PdfEvidenceViewer: { template: '<div data-test="pdf"/>' },
          PdfPageLabelEditor: true,
        },
      },
    });
    const html = wrapper.html();
    expect(html.indexOf('data-test="pdf"')).toBeGreaterThan(-1);
    expect(html.indexOf("Save document structure")).toBeGreaterThan(
      html.indexOf('data-test="pdf"'),
    );
  });

  it("tracks document-structure edits as dirty and saves the reviewer-owned plan", async () => {
    const asset: any = {
      asset_id: "asset-1",
      sha256: "sha",
      filename: "book.pdf",
      created_at: "",
      page_count: 12,
      block_count: 42,
      ocr_pages: 0,
      warnings: [],
      metadata: {},
      document_layout: {
        page_layout: "single",
        reading_order: "left_to_right",
        thread_mode: "continuous",
        main_text_pdf_start: 8,
        main_text_printed_start: 1,
      },
      pages: Array.from({ length: 12 }, (_, index) => ({
        pdf_page: index + 1,
        width: 612,
        height: 792,
      })),
    };
    const wrapper = mount(DocumentStructureConfigurator, {
      props: { asset, pdfUrl: "/book.pdf", blocks: [] },
      global: { stubs: { PdfEvidenceViewer: true, PdfPageLabelEditor: true } },
    });
    const save = buttonByText(wrapper, "Save document structure");
    expect(save.attributes("disabled")).toBeDefined();

    await buttonByText(wrapper, "Next").trigger("click");
    expect(lastEmission(wrapper, "pageChange")[0]).toBe(2);
    await buttonByText(wrapper, "Set current as main-text start").trigger("click");
    expect(wrapper.get('[data-state="dirty"]').text()).toContain("Unsaved changes");
    expect(buttonByText(wrapper, "Save document structure").attributes("disabled")).toBeUndefined();

    await buttonByText(wrapper, "Save document structure").trigger("click");
    const plan = lastEmission(wrapper, "save")[0] as any;
    expect(plan.main_text_pdf_start).toBe(2);
    expect(plan.page_layout).toBe("single");
  });
});
