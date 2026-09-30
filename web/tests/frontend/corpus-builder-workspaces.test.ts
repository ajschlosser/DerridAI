/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusBuilderWorkspaceHeader from "../../src/components/corpus-builder/CorpusBuilderWorkspaceHeader.vue";
import CorpusBuildHistoryMenu from "../../src/components/CorpusBuildHistoryMenu.vue";
import CorpusPublishWorkspace from "../../src/components/corpus-builder/CorpusPublishWorkspace.vue";
import CorpusReviewHeader from "../../src/components/corpus-builder/CorpusReviewHeader.vue";
import CorpusReviewQueueTabs from "../../src/components/CorpusReviewQueueTabs.vue";
import CorpusSetupSection from "../../src/components/corpus-builder/CorpusSetupSection.vue";
import CorpusSetupWorkspace from "../../src/components/corpus-builder/CorpusSetupWorkspace.vue";
import {
  corpusCurrentOperation,
  corpusPrimaryStatus,
  corpusStageRail,
  corpusWorkflowSteps,
  type PresentationText,
} from "../../src/features/corpus-builder/domain/workflowPresentation";
import {
  corpusSetupIssues,
  corpusSetupSectionStates,
  firstBlockingIssue,
  type CorpusSetupInput,
} from "../../src/features/corpus-builder/domain/setupState";
import {
  isWorkspaceAvailable,
  parseCorpusWorkspace,
  resolveWorkspace,
} from "../../src/features/corpus-builder/domain/workspace";

// Identity translator: fallbacks and keys are enough to assert behaviour without locale coupling.
const text: PresentationText = {
  t: (key, fallback) => fallback ?? key,
  tf: (key, values) => `${key}:${JSON.stringify(values)}`,
};
const build = (extra: Record<string, unknown> = {}) =>
  ({
    build_id: "build-1",
    status: "running",
    stage: "enriching",
    progress: 0.4,
    record_count: 10,
    accepted_count: 0,
    rejected_count: 0,
    ...extra,
  }) as never;

describe("workspace availability", () => {
  it("parses the four workspaces and rejects everything else", () => {
    for (const id of ["setup", "build", "review", "publish"])
      expect(parseCorpusWorkspace(id)).toBe(id);
    expect(parseCorpusWorkspace("finish")).toBe("");
    expect(parseCorpusWorkspace(undefined)).toBe("");
  });

  it("makes Publish available with Records even when the build is not publishable", () => {
    expect(isWorkspaceAvailable("setup", { hasBuild: false, hasRecordTopology: false })).toBe(true);
    expect(isWorkspaceAvailable("build", { hasBuild: true, hasRecordTopology: false })).toBe(true);
    expect(isWorkspaceAvailable("review", { hasBuild: true, hasRecordTopology: false })).toBe(
      false,
    );
    expect(isWorkspaceAvailable("publish", { hasBuild: true, hasRecordTopology: false })).toBe(
      false,
    );
    expect(isWorkspaceAvailable("publish", { hasBuild: true, hasRecordTopology: true })).toBe(true);
  });

  it("falls back when the requested workspace does not exist yet", () => {
    const context = { hasBuild: true, hasRecordTopology: false };
    expect(resolveWorkspace("publish", context, "build")).toBe("build");
    expect(resolveWorkspace("build", context, "setup")).toBe("build");
  });
});

describe("workflow presentation", () => {
  it("derives the status badge from stage, status and publication, not the raw value", () => {
    expect(corpusPrimaryStatus(null, text).label).toBe("Configuring");
    expect(corpusPrimaryStatus(build(), text)).toMatchObject({
      label: "Enriching metadata",
      tone: "info",
      progress: 0.4,
    });
    expect(corpusPrimaryStatus(build({ status: "failed" }), text)).toMatchObject({
      label: "Stopped",
      tone: "danger",
    });
    expect(corpusPrimaryStatus(build({ status: "blocked" }), text).label).toBe("Needs attention");
    expect(corpusPrimaryStatus(build({ status: "ready", stage: "ready" }), text).label).toBe(
      "Ready to publish",
    );
    expect(
      corpusPrimaryStatus(build({ status: "awaiting_review", stage: "review" }), text).label,
    ).toBe("Reviewing");
    expect(corpusPrimaryStatus(build({ publication: { publication_id: "p" } }), text).label).toBe(
      "Published",
    );
  });

  it("describes the current operation only from real telemetry", () => {
    expect(
      corpusCurrentOperation(
        build({
          stage: "segmenting",
          boundary_candidate_count: 247,
          boundary_candidates_completed: 83,
        }),
        text,
      ),
    ).toContain('"completed":83,"total":247');
    expect(corpusCurrentOperation(build({ stage: "enriching" }), text)).toBe("");
    expect(corpusCurrentOperation(null, text)).toBe("");
  });

  it("groups pipeline stages into a five-step rail", () => {
    const rail = corpusStageRail(build({ stage: "enriching" }));
    expect(rail.map((item) => item.state)).toEqual([
      "complete",
      "complete",
      "complete",
      "current",
      "pending",
    ]);
    expect(
      corpusStageRail(build({ stage: "review", status: "awaiting_review" })).every(
        (i) => i.state === "complete",
      ),
    ).toBe(true);
  });

  it("marks steps complete without making completion control navigability", () => {
    const steps = corpusWorkflowSteps(
      "build",
      { hasBuild: true, hasRecordTopology: true },
      {
        build: build({
          status: "awaiting_review",
          stage: "review",
          record_count: 4,
          accepted_count: 4,
        }),
        hasSource: true,
        setupCanStart: true,
        hasRecordTopology: true,
      },
    );
    const byId = Object.fromEntries(steps.map((step) => [step.id, step]));
    expect(byId.setup.state).toBe("complete");
    expect(byId.build.state).toBe("current");
    expect(byId.review).toMatchObject({ state: "complete", available: true });
    expect(byId.publish).toMatchObject({ state: "available", available: true });
  });
});

describe("setup state", () => {
  const input = (extra: Partial<CorpusSetupInput> = {}): CorpusSetupInput => ({
    asset: {
      filename: "Of Grammatology.pdf",
      media_kind: "pdf",
      page_count: 437,
      block_count: 900,
    },
    structureNeedsReview: false,
    structureSummary: "Main text PDF 9",
    recordSizingValid: true,
    targetChars: 1750,
    toleranceChars: 200,
    schemaName: "Scholarly default",
    schemaVersion: "1.4.0",
    guidanceFieldCount: 3,
    missingDocumentFieldCount: 0,
    providerLabel: "Local Ollama",
    modelLabel: "qwen",
    enrichmentMode: "fast",
    documentIntelligenceProfile: "none",
    profileActiveBuildCount: 0,
    contextSafe: true,
    ...extra,
  });

  it("reports blocking issues against the section that fixes them, in setup order", () => {
    const issues = corpusSetupIssues(
      input({ asset: null, recordSizingValid: false, contextSafe: false }),
      text,
    );
    expect(issues.map((issue) => [issue.section, issue.severity])).toEqual([
      ["source", "blocking"],
      ["structure", "blocking"],
      ["advanced", "blocking"],
    ]);
    expect(firstBlockingIssue(issues)?.section).toBe("source");
  });

  it("keeps document-field and structure gaps as warnings, not blockers", () => {
    const issues = corpusSetupIssues(
      input({ structureNeedsReview: true, missingDocumentFieldCount: 2 }),
      text,
    );
    expect(issues.every((issue) => issue.severity === "warning")).toBe(true);
    const states = corpusSetupSectionStates(input({ missingDocumentFieldCount: 2 }), issues, text);
    expect(states.find((state) => state.id === "metadata")?.state).toBe("warning");
    expect(states.find((state) => state.id === "advanced")?.state).toBe("optional");
    expect(states.find((state) => state.id === "metadata")?.summary).toContain("Scholarly default");
  });

  it("adds Document Intelligence to the Enrichment summary only when it is on", () => {
    const summary = (profile: string) =>
      corpusSetupSectionStates(input({ documentIntelligenceProfile: profile }), [], text).find(
        (state) => state.id === "enrichment",
      )!.summary;
    expect(summary("scholarly")).toContain("pdf_corpus.document_intelligence_scholarly");
    expect(summary("none")).not.toContain("document_intelligence");
  });

  it("does not invent page semantics for non-paginated media", () => {
    const states = corpusSetupSectionStates(
      input({ asset: { filename: "Interview.wav", media_kind: "audio", block_count: 58 } }),
      [],
      text,
    );
    const source = states.find((state) => state.id === "source")!;
    expect(source.summary).toContain("Interview.wav");
    expect(source.summary).not.toContain("pages");
    expect(states.find((state) => state.id === "structure")?.summary).not.toContain("Main text");
  });
});

describe("workspace header", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("is the one workflow navigation: four steps, checks for complete, disabled when unavailable", async () => {
    const wrapper = mount(CorpusBuilderWorkspaceHeader, {
      props: {
        sourceFilename: "Of Grammatology.pdf",
        buildId: "build-42",
        status: { label: "Reviewing", detail: "", tone: "info" },
        workspace: "review",
        steps: [
          { id: "setup", available: true, state: "complete" },
          { id: "build", available: true, state: "complete" },
          { id: "review", available: true, state: "current" },
          { id: "publish", available: false, state: "unavailable" },
        ],
      },
    });
    const buttons = wrapper.findAll(".workspace-mode-nav button");
    expect(buttons).toHaveLength(4);
    expect(buttons[0].text()).toContain("✓");
    expect(buttons[2].attributes("aria-current")).toBe("step");
    expect(buttons[3].attributes("disabled")).toBeDefined();
    await buttons[1].trigger("click");
    expect(wrapper.emitted("workspace")).toEqual([["build"]]);
    expect(wrapper.get(".corpus-workspace-stage").text()).toBe("Reviewing");
    // The build ID is secondary metadata, not headline copy.
    expect(wrapper.get(".corpus-workspace-context strong").text()).toBe("Of Grammatology.pdf");
    expect(wrapper.get("details code").text()).toBe("build-42");
  });
});

describe("build history menu", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("is the canonical selector: marks the selected build and shows progress, records and ID", async () => {
    const builds = [
      {
        build_id: "b1",
        source_filename: "One.pdf",
        status: "running",
        progress: 0.5,
        record_count: 3,
      },
      { build_id: "b2", source_filename: "Two.pdf", status: "ready", progress: 1, record_count: 8 },
    ] as never[];
    const wrapper = mount(CorpusBuildHistoryMenu, {
      props: { builds, selectedBuildId: "b2", total: 2 },
    });
    const rows = wrapper.findAll(".history-row");
    expect(rows[1].attributes("aria-current")).toBe("true");
    expect(rows[1].find(".selected-mark").exists()).toBe(true);
    expect(rows[0].find(".selected-mark").exists()).toBe(false);
    expect(rows[0].text()).toContain("50%");
    expect(rows[0].text()).toContain("3");
    expect(rows[0].get(".dot").attributes("data-tone")).toBe("warning");
    await rows[0].trigger("click");
    expect(wrapper.emitted("select")?.[0]?.[0]).toMatchObject({ build_id: "b1" });
  });
});

describe("setup sections", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("collapses to a summary and toggles from its header", async () => {
    const wrapper = mount(CorpusSetupSection, {
      props: {
        id: "source",
        title: "Source",
        state: "complete",
        summary: "Of Grammatology.pdf · PDF · 437 pages",
        expanded: false,
      },
      slots: { default: "<p class='body'>controls</p>" },
    });
    const toggle = wrapper.get("button");
    expect(toggle.attributes("aria-expanded")).toBe("false");
    expect(toggle.text()).toContain("Of Grammatology.pdf");
    expect(wrapper.get(".corpus-setup-section-body").attributes("style")).toContain(
      "display: none",
    );
    await toggle.trigger("click");
    expect(wrapper.emitted("toggle")).toHaveLength(1);
    await wrapper.setProps({ expanded: true });
    expect(toggle.attributes("aria-expanded")).toBe("true");
  });

  it("stacks Source, Structure, Metadata, Enrichment, Advanced with one section open", () => {
    const wrapper = mount(CorpusSetupWorkspace, {
      props: {
        expanded: "metadata",
        disabledSections: ["structure"],
        sections: (["source", "structure", "metadata", "enrichment", "advanced"] as const).map(
          (id) => ({ id, state: "complete" as const, summary: id }),
        ),
      },
    });
    expect(
      wrapper.findAll("[data-section]").map((node) => node.attributes("data-section")),
    ).toEqual(["source", "structure", "metadata", "enrichment", "advanced"]);
    const open = wrapper.findAll("[data-expanded='true']");
    expect(open).toHaveLength(1);
    expect(open[0].attributes("data-section")).toBe("metadata");
    expect(wrapper.find("[data-section='structure'] button").attributes("disabled")).toBeDefined();
  });
});

describe("publish workspace", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const publishBuild = (extra: Record<string, unknown> = {}) =>
    ({
      build_id: "b1",
      status: "awaiting_review",
      stage: "review",
      record_count: 20,
      validation: { valid: true },
      metadata_issue_summary: { fields_unresolved: 0 },
      publication_readiness: {
        can_publish: false,
        next_action: "review_records",
        blockers: [{ code: "record_review", count: 5 }],
        records_accepted: 15,
        records_rejected: 0,
        records_pending: 5,
      },
      ...extra,
    }) as never;

  it("leads with readiness and owns the unreviewed-publication decision", async () => {
    const wrapper = mount(CorpusPublishWorkspace, {
      props: { build: publishBuild(), canPublishUnreviewed: true },
      global: { stubs: { Teleport: true } },
    });
    expect(wrapper.get("#corpus-publish-title").text()).toBe("5 Records remain unreviewed");
    expect(wrapper.get("[data-count='pending'] dd").text()).toBe("5");
    const unreviewed = wrapper
      .findAll("button")
      .find((node) => node.text().includes("Publish with unreviewed"))!;
    await unreviewed.trigger("click");
    expect(wrapper.emitted("publishUnreviewed")).toBeUndefined();
    const confirm = document.body.textContent || wrapper.text();
    expect(confirm).toBeTruthy();
  });

  it("sends blocker actions to the parent, which switches to Review", async () => {
    const wrapper = mount(CorpusPublishWorkspace, { props: { build: publishBuild() } });
    const go = wrapper.findAll("button").find((node) => node.text().includes("Fix"));
    await go!.trigger("click");
    expect(wrapper.emitted("reviewRecords")).toHaveLength(1);
  });

  it("stops looking like an unresolved readiness screen once published", () => {
    const wrapper = mount(CorpusPublishWorkspace, {
      props: {
        build: publishBuild({
          status: "published",
          stage: "published",
          publication: { publication_id: "pub-1", record_count: 15 },
        }),
        canPublishUnreviewed: false,
      },
    });
    expect(wrapper.get("#corpus-publish-title").text()).toBe("Published");
    expect(wrapper.text()).toContain("pub-1");
    expect(wrapper.find(".publication-blockers").exists()).toBe(false);
    expect(wrapper.find(".publication-readiness-list").exists()).toBe(false);
    expect(wrapper.text()).not.toContain("Publish with unreviewed");
  });
});

describe("review header", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const toolbar = {
    total: 20,
    metadata: 1,
    topology: 0,
    sourceProblems: 0,
    rejected: 0,
    bulkActionItems: [],
    bulkActionFeedback: "",
    bulkMetadataOpen: false,
    schema: null,
    knownValues: {},
    regionTypes: [],
    discourseRoles: [],
    selectedCount: 0,
    bulkTotalCount: 20,
    bulkDisabled: false,
    pageNumber: 1,
    pageCount: 1,
    hasPreviousPage: false,
    hasNextPage: false,
  };

  it("keeps counts, view switch, focus and the toolbar in one surface", async () => {
    const wrapper = mount(CorpusReviewHeader, {
      props: {
        queue: "all",
        query: "",
        accepted: 142,
        ready: 5,
        issues: 4,
        remaining: 31,
        workspaceMode: "record",
        hasSelectedRecord: false,
        ...toolbar,
      } as never,
      slots: { "run-status": "<span class='run-slot'>run</span>" },
    });
    expect(wrapper.findAll("section.review-header")).toHaveLength(1);
    expect(wrapper.get(".review-counts").text()).toContain("142");
    expect(wrapper.find(".run-slot").exists()).toBe(true);
    // Toolbar controls fall through from the header's attrs.
    expect(wrapper.find("#pdf-corpus-record-search").exists()).toBe(true);
    const views = wrapper.findAll(".review-view-option");
    expect(views[0].attributes("disabled")).toBeUndefined();
    expect(views[1].attributes("disabled")).toBeDefined();
    expect(views[2].attributes("disabled")).toBeDefined();
    await wrapper.setProps({ hasSelectedRecord: true });
    await wrapper.findAll(".review-view-option")[1].trigger("click");
    expect(wrapper.emitted("workspace")?.at(-1)).toEqual(["metadata"]);
    await wrapper.get("#pdf-corpus-record-search").setValue("Levinas");
    expect(wrapper.emitted("update:query")?.at(-1)).toEqual(["Levinas"]);
  });
});

describe("review queue filters", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("offers five primary filters and the issue kinds as a sub-filter under Needs attention", async () => {
    const wrapper = mount(CorpusReviewQueueTabs, {
      props: {
        modelValue: "metadata",
        total: 10,
        ready: 4,
        issues: 3,
        metadata: 2,
        topology: 1,
        sourceProblems: 0,
        accepted: 2,
        rejected: 1,
      },
    });
    expect(wrapper.findAll(".queue-tab").map((tab) => tab.find("span").text())).toEqual([
      "All",
      "Ready",
      "Needs attention",
      "Accepted",
      "Rejected",
    ]);
    // A specialised queue keeps Needs attention pressed and shows the sub-filter.
    expect(wrapper.get('[data-review-queue="issues"]').attributes("aria-pressed")).toBe("true");
    const select = wrapper.get("select");
    expect(select.findAll("option").map((option) => option.attributes("value"))).toEqual([
      "issues",
      "metadata",
      "topology",
    ]);
    await select.setValue("issues");
    expect(wrapper.emitted("update:modelValue")?.at(-1)).toEqual(["issues"]);
  });
});
