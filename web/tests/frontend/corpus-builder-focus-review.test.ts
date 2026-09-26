import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CorpusRecordFocusReview from "../../src/components/CorpusRecordFocusReview.vue";

function buttonByText(wrapper: any, text: string) {
  const button = wrapper.findAll("button").find((node: any) => node.text().includes(text));
  if (!button) throw new Error("Button not found: " + text);
  return button;
}
function lastEmission(wrapper: any, event: string) {
  const events = wrapper.emitted(event) || [];
  return events[events.length - 1] || [];
}

const record: any = {
  record_id: "record-00014",
  record_revision: 2,
  text: "A representative passage under review.",
  text_length: 42,
  page_start: 22,
  page_end: 23,
  pdf_pages: [24],
  source_block_ids: ["p24-b1"],
  source_spans: [],
  needs_review: true,
  review_reason: "Boundary requires review.",
  review_disposition: "pending",
  metadata_field_status: {},
  metadata_evidence: {},
  metadata_incomplete_fields: [],
  metadata_review_fields: [],
  region_type: "main_text",
  primary_text: true,
};
const stubs = {
  CorpusSourceIssuePanel: true,
  CorpusMetadataResolutionPanel: true,
  CorpusTextCleanupDialog: true,
  CorpusRevisionHistory: true,
  CorpusBoundarySliceDialog: true,
  CorpusBoundaryAdjudication: true,
  CorpusSourceSummary: true,
};

describe("Corpus Builder focus review interactions", () => {
  it("focuses the close action on open and exposes modal semantics", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      attachTo: document.body,
      props: { record, canPreviousRecord: true, canNextRecord: true },
      global: { stubs },
    });
    await nextTick();
    expect(wrapper.get('[role="dialog"]').attributes("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(buttonByText(wrapper, "Close").element);
    wrapper.unmount();
  });

  it("supports Escape and record-navigation keyboard shortcuts", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      attachTo: document.body,
      props: { record, canPreviousRecord: true, canNextRecord: true },
      global: { stubs },
    });
    const dialog = wrapper.get(".focus-review");
    await dialog.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    await dialog.trigger("keydown", { key: "ArrowLeft", altKey: true });
    expect(wrapper.emitted("previousRecord")).toHaveLength(1);
    await dialog.trigger("keydown", { key: "ArrowRight", altKey: true });
    expect(wrapper.emitted("nextRecord")).toHaveLength(1);
    wrapper.unmount();
  });

  it("implements arrow-key tab navigation across metadata, evidence, and source", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      attachTo: document.body,
      props: { record },
      global: { stubs },
    });
    expect(wrapper.get("#focus-tab-metadata").attributes("aria-selected")).toBe("true");
    await wrapper.get(".tabs").trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    expect(wrapper.get("#focus-tab-evidence").attributes("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(wrapper.get("#focus-tab-evidence").element);
    await wrapper.get(".tabs").trigger("keydown", { key: "End" });
    await nextTick();
    expect(wrapper.get("#focus-tab-source").attributes("aria-selected")).toBe("true");
    wrapper.unmount();
  });

  it("uses parent-owned text state and requests save with Ctrl/Cmd+S", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      attachTo: document.body,
      props: { record },
      global: { stubs },
    });

    await buttonByText(wrapper, "Edit text").trigger("click");
    expect(wrapper.emitted("beginTextEdit")).toHaveLength(1);

    await wrapper.setProps({
      editingText: true,
      textDraft: record.text,
      resolveSourceIssues: false,
    });
    const editor = wrapper.get("textarea.focus-text-editor");
    expect((editor.element as HTMLTextAreaElement).value).toBe(record.text);

    await editor.setValue("A corrected reviewed passage.");
    expect(lastEmission(wrapper, "textDraftChange")).toEqual(["A corrected reviewed passage."]);

    // A controlled parent applies the emitted draft before the save shortcut.
    await wrapper.setProps({ textDraft: "A corrected reviewed passage." });
    await wrapper.get(".focus-review").trigger("keydown", { key: "s", ctrlKey: true });

    expect(wrapper.emitted("saveText")).toHaveLength(1);
    expect(lastEmission(wrapper, "saveText")).toEqual([]);
    expect(record.text).toBe("A representative passage under review.");
    wrapper.unmount();
  });

  it("saves the value with the selected text as evidence and stays on the metadata tab", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      props: { record, sourceBlocks: [] },
      global: {
        stubs: {
          ...stubs,
          CorpusMetadataResolutionPanel: {
            template:
              "<button data-selection-evidence @click=\"$emit('resolveWithEvidence','position_holder','Levinas','responsibility precedes freedom')\">Save with evidence</button>",
          },
        },
      },
    });

    await wrapper.get("[data-selection-evidence]").trigger("click");

    expect(lastEmission(wrapper, "resolveMetadataWithEvidence")).toEqual([
      "position_holder",
      "Levinas",
      "responsibility precedes freedom",
    ]);
    // The reviewer proceeds to the next value; the evidence tab is not opened.
    expect(wrapper.get("#focus-tab-metadata").attributes("aria-selected")).toBe("true");
    expect(wrapper.emitted("assignEvidence")).toBeUndefined();
  });

  it("passes the pinned metadata schema into focus-mode field review", () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      props: {
        record,
        schema: {
          format_version: 1,
          schema_version: "review-schema-v1",
          id: "review-schema",
          name: "Review schema",
          description: "Focus-mode schema fixture",
          groups: [],
          fields: [
            {
              field_id: "field-quoted-author",
              name: "quoted_author",
              label: "Quoted author",
              type: "text",
              group: "core",
              instruction: "",
              definitions_heading: "",
              values: [],
              strict: false,
              evidence: true,
              assess: true,
              review: true,
              pos_tags: [],
              ner_tags: [],
              retrieval_profile: {
                enabled: true,
                include_corrections: true,
                include_confirmed_absence: false,
                max_items: 4,
                min_similarity: 0.8,
              },
            },
          ],
        },
      },
      global: {
        stubs: {
          ...stubs,
          CorpusMetadataResolutionPanel: {
            props: ["schema"],
            template:
              '<div data-focus-schema>{{ schema?.fields?.[0]?.label || "missing schema" }}</div>',
          },
        },
      },
    });
    expect(wrapper.get("[data-focus-schema]").text()).toBe("Quoted author");
    wrapper.unmount();
  });

  it("forwards Save all suggestions from focus-mode metadata review", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      props: { record },
      global: {
        stubs: {
          ...stubs,
          CorpusMetadataResolutionPanel: {
            template:
              "<button data-save-all @click=\"$emit('resolveMany',{ speaker: 'Jacques Derrida', target: 'hospitality' })\">Save all</button>",
          },
        },
      },
    });

    await wrapper.get("[data-save-all]").trigger("click");

    expect(lastEmission(wrapper, "resolveMetadataMany")).toEqual([
      { speaker: "Jacques Derrida", target: "hospitality" },
    ]);
    wrapper.unmount();
  });

  it("disables acceptance when the parent marks the record unsafe to accept", () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      props: { record, canAccept: false },
      global: { stubs },
    });
    const accept = buttonByText(wrapper, "Accept");
    expect(accept.attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("emits front-of-queue requeue and disables the action while busy", async () => {
    const wrapper = mount(CorpusRecordFocusReview, { props: { record }, global: { stubs } });
    const requeue = buttonByText(wrapper, "Send back through current LLM run");
    await requeue.trigger("click");
    expect(wrapper.emitted("requeueMetadata")).toHaveLength(1);
    await wrapper.setProps({ busy: true });
    expect(
      buttonByText(wrapper, "Send back through current LLM run").attributes("disabled"),
    ).toBeDefined();
    wrapper.unmount();
  });

  it("exposes noise status and linked queue context", async () => {
    const wrapper = mount(CorpusRecordFocusReview, {
      props: {
        record: { ...record, text_noise: { score: 52, unusable: true } },
        justProcessedRecordId: "record-00013",
        nextRecordId: "record-00015",
      },
      global: { stubs },
    });
    expect(wrapper.get(".record-noise-summary").text()).toContain("52% noise");
    const links = wrapper.findAll(".queue-context .text-link");
    expect(links).toHaveLength(3);
    await links[0].trigger("click");
    expect(lastEmission(wrapper, "navigateRecord")[0]).toBe("record-00013");
    await links[2].trigger("click");
    expect(lastEmission(wrapper, "navigateRecord")[0]).toBe("record-00015");
    wrapper.unmount();
  });
});
