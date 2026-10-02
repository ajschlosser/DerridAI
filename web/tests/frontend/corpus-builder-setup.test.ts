import { mount } from "@vue/test-utils";
import { describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/corpus", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../src/api/corpus")>();
  return {
    ...actual,
    corpusBuilderApi: {
      ...actual.corpusBuilderApi,
      blocks: vi.fn().mockResolvedValue({ items: [], total: 0 }),
    },
  };
});
import CorpusBuildReadiness from "../../src/components/CorpusBuildReadiness.vue";
import CorpusExecutionSettings from "../../src/components/CorpusExecutionSettings.vue";
import CorpusRecordSizingSettings from "../../src/components/CorpusRecordSizingSettings.vue";
import DocumentStructureConfigurator from "../../src/components/DocumentStructureConfigurator.vue";
import DocumentManifestEditor from "../../src/components/DocumentManifestEditor.vue";
import CorpusTopologyPolicy from "../../src/components/corpus-builder/CorpusTopologyPolicy.vue";
import PdfPageLabelEditor from "../../src/components/PdfPageLabelEditor.vue";

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
    expect(wrapper.get(".build-plan-eyebrow").text()).toBe("Build plan");
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

    await wrapper.setProps({ busy: false, contextSafe: true, canStart: false });
    expect(wrapper.get("#build-readiness-title").text()).toBe("Complete setup to build");
    await wrapper.setProps({ contextSafe: false });
    expect(wrapper.get('[role="alert"]').text()).toContain("Context budget");
    expect(wrapper.get(".build-action").attributes("disabled")).toBeDefined();
  });

  it("keeps the Build plan as one visible preflight and opens the section behind each summary", async () => {
    const wrapper = mount(CorpusBuildReadiness, {
      props: {
        mediaKind: "pdf",
        sourceFilename: "book.pdf",
        pageCount: 80,
        blockCount: 300,
        structureSummary: "Main text PDF 9",
        schemaLabel: "Scholarly default",
        providerLabel: "Local Ollama",
        modelLabel: "qwen",
        targetChars: 1750,
        toleranceChars: 200,
        canStart: true,
      },
    });

    expect(wrapper.find(".build-command-details").exists()).toBe(false);
    expect(wrapper.find(".build-command-popover").exists()).toBe(false);
    expect(wrapper.get(".build-command-summary").text()).toContain("1,750");
    await wrapper.get('button[aria-label="Edit Source"]').trigger("click");
    await wrapper.get('button[aria-label="Edit Metadata"]').trigger("click");
    expect(wrapper.emitted("editSection")).toEqual([["source"], ["metadata"]]);
  });

  it("names the first blocking setup issue and sends Fix to its section", async () => {
    const wrapper = mount(CorpusBuildReadiness, {
      props: {
        sourceFilename: "",
        canStart: false,
        issues: [
          {
            id: "sizing",
            section: "structure",
            severity: "blocking",
            message: "Fix Record sizing",
          },
          {
            id: "source",
            section: "source",
            severity: "blocking",
            message: "Choose a source to continue",
          },
          { id: "warn", section: "metadata", severity: "warning", message: "2 document fields" },
        ],
      },
    });
    // Setup order decides priority, not list order.
    expect(wrapper.get("#build-readiness-title").text()).toBe("Choose a source to continue");
    await buttonByText(wrapper, "Fix").trigger("click");
    expect(wrapper.emitted("editSection")).toEqual([["source"]]);
    expect(wrapper.get(".build-command-warning").text()).toContain("1");
    expect(wrapper.get(".readiness-warnings").text()).toContain("2 document fields");
  });

  it("supports exact SourceUnit-to-Record grouping and optional synthetic pages", async () => {
    const wrapper = mount(CorpusTopologyPolicy, {
      props: {
        modelValue: {
          mode: "semantic",
          source_units_per_record: 1,
          records_per_page: null,
        },
        syntheticPagesAvailable: true,
      },
    });

    await wrapper.get('input[value="source_units"]').setValue(true);
    let next = lastEmission(wrapper, "update:modelValue")[0] as any;
    expect(next.mode).toBe("source_units");

    await wrapper.setProps({ modelValue: next });
    await wrapper.get("#corpus-source-units-per-record").setValue("2");
    next = lastEmission(wrapper, "update:modelValue")[0] as any;
    expect(next.source_units_per_record).toBe(2);

    await wrapper.setProps({ modelValue: next });
    await wrapper.get(".page-toggle input").setValue(true);
    next = lastEmission(wrapper, "update:modelValue")[0] as any;
    expect(next.records_per_page).toBe(1);

    await wrapper.setProps({ modelValue: next });
    await wrapper.get("#corpus-records-per-page").setValue("4");
    next = lastEmission(wrapper, "update:modelValue")[0] as any;
    expect(next.records_per_page).toBe(4);
  });

  it("keeps authoritative source pages separate from synthetic Record pages", () => {
    const wrapper = mount(CorpusTopologyPolicy, {
      props: {
        modelValue: {
          mode: "source_units",
          source_units_per_record: 1,
          records_per_page: null,
        },
        syntheticPagesAvailable: false,
      },
    });
    expect(wrapper.find(".page-toggle").exists()).toBe(false);
    expect(wrapper.get(".page-authority-note").text()).toContain("authoritative page structure");
  });

  it("edits detected manifest values before Build without post-build reanalysis controls", async () => {
    const wrapper = mount(DocumentManifestEditor, {
      props: {
        mediaKind: "text",
        manifest: {
          title: "Detected title",
          document_author: "Detected author",
        },
        showReanalyze: false,
      },
    });
    expect(wrapper.text()).not.toContain("Reanalyze");
    const inputs = wrapper.findAll('input.control[type="text"]');
    expect(inputs[0].element.value).toBe("Detected title");
    await inputs[0].setValue("Reviewed title");
    await buttonByText(wrapper, "Save manifest changes").trigger("click");
    expect(wrapper.emitted("save")?.[0]?.[0]).toEqual({ title: "Reviewed title" });
  });

  it("keeps automatic limits valid as the target changes, without touching custom ones", async () => {
    const value = {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 3500,
      absolute_record_chars: 6000,
    };
    const wrapper = mount(CorpusRecordSizingSettings, { props: { modelValue: value } });
    // Defaults are automatic, so the limits follow the target and are valid by construction.
    await wrapper.get("#corpus-preferred-chars").setValue("5000");
    const emitted = wrapper.emitted("update:modelValue")!;
    const next = emitted[emitted.length - 1][0] as any;
    expect(next.preferred_record_chars).toBe(5000);
    expect(next.long_record_chars).toBeGreaterThanOrEqual(5200);
    expect(next.absolute_record_chars).toBeGreaterThanOrEqual(next.long_record_chars);
    expect(wrapper.find(".sizing-warning").exists()).toBe(false);
  });

  it("never rewrites custom limits, and explains and fixes an invalid one", async () => {
    const custom = {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 4000,
      absolute_record_chars: 9000,
    };
    const wrapper = mount(CorpusRecordSizingSettings, { props: { modelValue: custom } });
    await wrapper.get("#corpus-preferred-chars").setValue("5000");
    let emitted = wrapper.emitted("update:modelValue")!;
    expect(emitted[emitted.length - 1][0]).toEqual({ ...custom, preferred_record_chars: 5000 });
    await wrapper.setProps({ modelValue: emitted[emitted.length - 1][0] as never });
    expect(wrapper.get("#long-hint").attributes("role")).toBe("alert");
    expect(wrapper.get("#corpus-long-chars").attributes("aria-invalid")).toBe("true");
    await wrapper.get("#long-hint .fix").trigger("click");
    emitted = wrapper.emitted("update:modelValue")!;
    expect((emitted[emitted.length - 1][0] as any).long_record_chars).toBe(5200);
  });

  it("switches back to automatic limits on request and offers common targets", async () => {
    const custom = {
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 4000,
      absolute_record_chars: 9000,
    };
    const wrapper = mount(CorpusRecordSizingSettings, { props: { modelValue: custom } });
    await wrapper.get('.auto-switch input[type="checkbox"]').setValue(true);
    expect(wrapper.emitted("update:modelValue")!.at(-1)![0]).toEqual({
      preferred_record_chars: 1750,
      record_length_tolerance: 200,
      long_record_chars: 3500,
      absolute_record_chars: 6000,
    });
    await wrapper.findAll(".preset")[0].trigger("click");
    const sentence = wrapper.emitted("update:modelValue")!.at(-1)![0] as any;
    expect(sentence.preferred_record_chars).toBe(150);
    expect(sentence.long_record_chars).toBeGreaterThanOrEqual(180);
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

  it("applies a margin column as one repeating region instead of a per-page drawing", async () => {
    const asset: any = {
      asset_id: "asset-margin",
      sha256: "sha",
      filename: "gloss.pdf",
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
      },
      pages: [{ pdf_page: 1, width: 1000, height: 1400 }],
    };
    const wrapper = mount(DocumentStructureConfigurator, {
      props: { asset, pdfUrl: "/gloss.pdf", blocks: [] },
      global: { stubs: { PdfEvidenceViewer: true, PdfPageLabelEditor: true } },
    });
    const margin = wrapper.findAll('input[name="layout-recipe"]')[2];
    await margin.trigger("change");
    expect(wrapper.text()).toContain("A separate region is read after the main text");
    await buttonByText(wrapper, "Save document structure").trigger("click");
    const plan = lastEmission(wrapper, "save")[0] as any;
    const roles = plan.layout_regions.map(
      (region: { role: string; flow: string; applies_to: string }) => ({
        role: region.role,
        flow: region.flow,
        applies_to: region.applies_to,
      }),
    );
    expect(roles).toEqual([
      { role: "main", flow: "with_main", applies_to: "all" },
      { role: "margin_apparatus", flow: "separate", applies_to: "all" },
    ]);
  });

  it("pages through printed labels and emits only edited mapping overrides", async () => {
    const pages = Array.from({ length: 27 }, (_, index) => ({
      pdf_page: index + 1,
      printed_page_label: String(index + 1),
      printed_page_label_source: "detected",
    }));
    const wrapper = mount(PdfPageLabelEditor, { props: { pages } });
    expect(wrapper.get(".range").text()).toBe("1–25 / 27");
    await wrapper.get("#pdf-label-1").setValue("i");
    expect(wrapper.get("button").attributes("disabled")).toBeUndefined();
    await buttonByText(wrapper, "Save 1 override").trigger("click");
    expect(lastEmission(wrapper, "save")[0]).toEqual({ 1: "i" });
    await buttonByText(wrapper, "Next").trigger("click");
    expect(wrapper.get(".range").text()).toBe("26–27 / 27");
    expect(wrapper.find("#pdf-label-26").exists()).toBe(true);
  });
});
