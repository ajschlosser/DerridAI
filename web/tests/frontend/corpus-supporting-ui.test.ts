// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusBuildReadiness from "../../src/components/CorpusBuildReadiness.vue";
import CorpusBuildStageNotice from "../../src/components/CorpusBuildStageNotice.vue";
import CorpusFieldOwnershipBadge from "../../src/components/CorpusFieldOwnershipBadge.vue";
import CorpusReviewSessionBar from "../../src/components/CorpusReviewSessionBar.vue";
import CorpusSourceIssuePanel from "../../src/components/CorpusSourceIssuePanel.vue";
import CorpusWorkflowStepper from "../../src/components/CorpusWorkflowStepper.vue";

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

  it("keeps page-specific readiness details out of audio sources", () => {
    const wrapper = mount(CorpusBuildReadiness, {
      props: {
        mediaKind: "audio",
        sourceFilename: "seminar-session.flac",
        pageCount: 99,
        blockCount: 12,
        structureSummary: "PDF page map",
        canStart: true,
        contextSafe: true,
      },
    });

    expect(wrapper.text()).toContain("seminar-session.flac");
    expect(wrapper.text()).toContain("12");
    expect(wrapper.text()).not.toContain("99");
    expect(wrapper.text()).not.toContain("PDF page map");
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
    const confirmed = mount(CorpusFieldOwnershipBadge, {
      props: { status: "human_confirmed" },
    });

    expect(inferred.text()).toContain("LLM");
    expect(inferred.text()).toContain("Auto");
    expect(confirmed.text()).toContain("Human");
    expect(confirmed.text()).not.toContain("Auto");
  });

  it("keeps review focus as an explicit user action", async () => {
    const wrapper = mount(CorpusReviewSessionBar, {
      props: {
        sourceFilename: "source.txt",
        accepted: 1,
        reviewable: 2,
        remaining: 3,
        issues: 4,
      },
    });

    await wrapper.get("button").trigger("click");

    expect(wrapper.emitted("focus")).toHaveLength(1);
  });

  it("marks the active workflow step semantically", () => {
    const wrapper = mount(CorpusWorkflowStepper, {
      props: { stage: "review", status: "awaiting_review" },
    });

    const current = wrapper.get('[aria-current="step"]');
    expect(current.text()).toContain("Review");
  });
});
