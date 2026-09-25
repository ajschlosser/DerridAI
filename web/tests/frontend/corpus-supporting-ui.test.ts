// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusBuildStageNotice from "../../src/components/CorpusBuildStageNotice.vue";
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
