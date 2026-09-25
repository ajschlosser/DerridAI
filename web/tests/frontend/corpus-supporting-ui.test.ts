// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusBuildStageNotice from "../../src/components/CorpusBuildStageNotice.vue";
import CorpusEnrichmentChanges from "../../src/components/CorpusEnrichmentChanges.vue";
import CorpusHandsFreeReport from "../../src/components/CorpusHandsFreeReport.vue";
import CorpusHandsFreeSettings from "../../src/components/CorpusHandsFreeSettings.vue";
import CorpusFieldOwnershipBadge from "../../src/components/CorpusFieldOwnershipBadge.vue";
import CorpusSourceIssuePanel from "../../src/components/CorpusSourceIssuePanel.vue";

describe("Corpus Builder supporting UI", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("announces the current build stage without requiring visual styling", () => {
    const wrapper = mount(CorpusBuildStageNotice, {
      props: { stage: "semantic segmentation" },
    });

    expect(wrapper.attributes("role")).toBe("status");
    expect(wrapper.attributes("aria-live")).toBe("polite");
    expect(wrapper.text()).toContain("semantic segmentation");
  });

  it("does not invent page locations for non-paginated source issues", () => {
    const wrapper = mount(CorpusSourceIssuePanel, {
      props: {
        issues: [
          {
            code: "source_quality_warning",
            severity: "warning",
            message: "Transcript region requires review.",
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("Transcript region requires review.");
    expect(wrapper.text()).not.toContain("Pages —");
  });

  it("emits both source-review actions through shared controls", async () => {
    const wrapper = mount(CorpusSourceIssuePanel, {
      props: {
        interactive: true,
        issues: [
          {
            code: "source_quality_warning",
            severity: "warning",
            message: "Source region requires review.",
          },
        ],
      },
    });

    const buttons = wrapper.findAll("button");
    expect(buttons).toHaveLength(2);

    await buttons[0].trigger("click");
    await buttons[1].trigger("click");

    expect(wrapper.emitted("openSource")).toHaveLength(1);
    expect(wrapper.emitted("editText")).toHaveLength(1);
  });

  it("emits enrichment resolutions through the shared action controls", async () => {
    const wrapper = mount(CorpusEnrichmentChanges, {
      props: {
        record: {
          stance: "critical",
          metadata_field_status: {
            stance: { status: "model_inferred" },
          },
          metadata_enrichment_history: [
            {
              replaced: [{ field: "stance", previous: "descriptive", value: "critical" }],
            },
          ],
        },
      },
    });

    await wrapper.get("button").trigger("click");

    expect(wrapper.emitted("resolve")?.at(-1)).toEqual(["stance", "descriptive"]);
  });

  it("updates hands-free policy without mutating the supplied value", async () => {
    const policy = {
      enabled: true,
      passes: 1,
      min_confidence: 0.8,
      unresolved: "leave" as const,
      accept_records: false,
      publish: false,
    };
    const wrapper = mount(CorpusHandsFreeSettings, {
      props: { modelValue: policy },
    });

    await wrapper.get('input[type="number"]').setValue(3);

    expect(policy.passes).toBe(1);
    expect(wrapper.emitted("update:modelValue")?.at(-1)?.[0]).toEqual({
      ...policy,
      passes: 3,
    });
  });

  it("opens a specific hands-free exception record", async () => {
    const wrapper = mount(CorpusHandsFreeReport, {
      props: {
        report: {
          records: 1,
          accepted: 0,
          fields_filled: 0,
          left_for_review: 1,
          passes_run: 1,
          ran_at: "2026-09-25T12:00:00Z",
          exceptions: [{ record_id: "record-0001", reasons: ["needs review"] }],
          notes: [],
          policy: {
            enabled: true,
            passes: 1,
            min_confidence: 0.8,
            unresolved: "leave",
            accept_records: false,
            publish: false,
          },
        },
      },
    });

    await wrapper.get("button").trigger("click");

    expect(wrapper.emitted("open-record")?.at(-1)).toEqual(["record-0001"]);
  });

  it("keeps provenance and verification as separate visible badge concepts", () => {
    const inferred = mount(CorpusFieldOwnershipBadge, {
      props: { status: "model_inferred" },
    });
    const confirmedModel = mount(CorpusFieldOwnershipBadge, {
      props: {
        status: "human_confirmed",
        method: "llm",
        derivationMethod: "model",
      },
    });
    const confirmedHuman = mount(CorpusFieldOwnershipBadge, {
      props: { status: "human_confirmed", derivationMethod: "human" },
    });

    expect(inferred.text()).toContain("LLM");
    expect(inferred.text()).toContain("Auto");
    expect(confirmedModel.text()).toContain("LLM");
    expect(confirmedModel.text()).toContain("Human");
    expect(confirmedHuman.text()).toContain("Human");
    expect(confirmedHuman.text()).not.toContain("LLM");
  });
});
