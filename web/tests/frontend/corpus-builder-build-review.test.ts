/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusBuildPrimaryStatus from "../../src/components/corpus-builder/CorpusBuildPrimaryStatus.vue";
import CorpusBuildTelemetry from "../../src/components/CorpusBuildTelemetry.vue";
import CorpusBuildWorkspace from "../../src/components/corpus-builder/CorpusBuildWorkspace.vue";
import CorpusFinishWorkspace from "../../src/components/CorpusFinishWorkspace.vue";
import CorpusInitializationDialog from "../../src/components/CorpusInitializationDialog.vue";
import CorpusReviewQueueTabs from "../../src/components/CorpusReviewQueueTabs.vue";

function buttonByText(wrapper: any, text: string) {
  const button = wrapper.findAll("button").find((node: any) => node.text().includes(text));
  if (!button) throw new Error("Button not found: " + text);
  return button;
}
function lastEmission(wrapper: any, event: string) {
  const events = wrapper.emitted(event) || [];
  return events[events.length - 1] || [];
}

const buildBase: any = {
  build_id: "build-1",
  asset_id: "asset",
  source_filename: "book.pdf",
  source_sha256: "sha",
  status: "awaiting_review",
  stage: "review",
  progress: 1,
  created_at: "",
  record_count: 10,
  accepted_count: 10,
  rejected_count: 0,
  validation: { valid: true, source_valid: true, metadata_valid: true, coverage: 1 },
  source_quality: { blocking_page_count: 0 },
  metadata_issue_summary: {
    records_incomplete: 0,
    fields_unresolved: 0,
    auto_retry_fields: 0,
    human_review_fields: 0,
  },
  publication_readiness: {
    can_publish: true,
    next_action: "publish",
    records_total: 10,
    records_reviewed: 10,
    records_accepted: 10,
    records_rejected: 0,
    records_pending: 0,
    blockers: [],
  },
};

describe("Corpus Builder build, review, and finish states", () => {
  it("reports progress, unresolved topology, LLM telemetry, and validation hazards accessibly", () => {
    const wrapper = mount(CorpusBuildTelemetry, {
      props: {
        stage: "review",
        unresolvedCount: 2,
        llmMetrics: { calls: 12, retries: 2, structured_output_failures: 1 },
        validation: {
          valid: false,
          coverage: 0.98,
          metadata_evidence_errors: [{ record_id: "r1", reason: "Speaker evidence is invalid." }],
          metadata_schema_errors: [{ record_id: "r1", reason: "Stance value is invalid." }],
          citation_errors: ["r1"],
        },
      },
    });
    expect(wrapper.get(".unresolved-line").text()).toContain("2");
    expect(wrapper.get(".llm-metrics").text()).toContain("12");
    expect(wrapper.get(".validation-strip").text()).toContain("Validation needs attention");
    expect(wrapper.find(".validation-details").exists()).toBe(true);
  });

  it("reports the active metadata family and real task counts during enrichment", () => {
    const wrapper = mount(CorpusBuildPrimaryStatus, {
      props: {
        build: {
          ...buildBase,
          status: "running",
          stage: "enriching",
          progress: 0.72,
          record_count: 112,
          accepted_count: 0,
          metadata_active_tasks: [{ record_id: "record-36", task: "quotation" }],
          metadata_tasks_total: 336,
          metadata_tasks_completed: 214,
          metadata_tasks_failed: 1,
          metadata_tasks_skipped: 2,
          metadata_tasks_running: 3,
          metadata_tasks_queued: 116,
        },
        running: true,
        canResume: false,
        hasRecordTopology: true,
        readyCount: 8,
        enrichingCount: 3,
        preparingCount: 92,
        attentionCount: 9,
      },
    });
    const operation = wrapper.get(".primary-status-operation").text();
    expect(operation).toContain("record-36");
    expect(operation).toContain("quotation");
    expect(operation).toContain("217/336");
    expect(operation).toContain("3 active");
    expect(wrapper.get("h2").text()).toBe("Enriching metadata");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("72");
    expect(wrapper.get('[aria-current="step"]').text()).toContain("Enrich");
    const handoff = wrapper.get(".primary-status-handoff");
    expect(handoff.get('[data-flow-state="ready"] dd').text()).toBe("8");
    expect(handoff.get('[data-flow-state="enriching"] dd').text()).toBe("3");
    expect(handoff.get('[data-flow-state="preparing"] dd').text()).toBe("92");
    expect(handoff.get('[data-flow-state="attention"] dd').text()).toBe("9");
    expect(buttonByText(wrapper, "Review 8 ready Records").exists()).toBe(true);
    expect(wrapper.get(".primary-status-review-help").text()).toContain(
      "while automated build work continues in the background",
    );
  });

  it("makes Review primary when issue Records are available even before clean-ready Records", () => {
    const wrapper = mount(CorpusBuildPrimaryStatus, {
      props: {
        build: {
          ...buildBase,
          status: "running",
          stage: "enriching",
          progress: 0.4,
          record_count: 20,
        },
        running: true,
        canResume: false,
        hasRecordTopology: true,
        readyCount: 0,
        enrichingCount: 2,
        preparingCount: 16,
        attentionCount: 2,
      },
    });

    const review = buttonByText(wrapper, "Review Records");
    expect(review.exists()).toBe(true);
    expect(review.classes()).toContain("variant-primary");
    expect(wrapper.get('[data-flow-state="attention"] dd').text()).toBe("2");
  });

  it("shows recent authoritative stage changes on the live Build surface", async () => {
    const wrapper = mount(CorpusBuildWorkspace, {
      props: {
        build: {
          ...buildBase,
          status: "running",
          stage: "enriching",
          progress: 0.72,
          record_count: 12,
          build_events: [
            { at: "2026-09-30T18:00:00Z", stage: "preparing", status: "running", progress: 0.02 },
            {
              at: "2026-09-30T18:02:00Z",
              stage: "constructing_records",
              status: "running",
              progress: 0.4,
            },
            { at: "2026-09-30T18:04:00Z", stage: "enriching", status: "running", progress: 0.72 },
          ],
        },
        running: true,
        canResume: false,
        hasRecordTopology: true,
        readyCount: 3,
        awaitingManifestReview: false,
        retryingSegmentation: false,
        segmentationNeedsReview: false,
        contextSafe: true,
      },
    });
    expect(wrapper.find(".build-activity").exists()).toBe(false);
    const runDetails = wrapper.get("details.corpus-build-diagnostics");
    expect(runDetails.text()).toContain("Run details");
    (runDetails.element as HTMLDetailsElement).open = true;
    await runDetails.trigger("toggle");
    expect(wrapper.get(".build-activity").text()).toContain("Build timeline");
    expect(wrapper.findAll(".build-activity li")).toHaveLength(3);
    expect(wrapper.get(".build-activity").text()).toContain("72%");
  });

  it("surfaces recoverable build failures as alerts without hiding preserved warnings", async () => {
    const wrapper = mount(CorpusBuildWorkspace, {
      props: {
        build: {
          ...buildBase,
          status: "failed",
          stage: "failed",
          progress: 0.48,
          record_count: 84,
          error: "Provider unavailable.",
          warnings: ["Completed checkpoints were preserved."],
        },
        running: false,
        canResume: true,
        hasRecordTopology: true,
        awaitingManifestReview: false,
        retryingSegmentation: false,
        segmentationNeedsReview: false,
        contextSafe: true,
      },
    });
    expect(wrapper.get('[role="alert"]').text()).toContain("Provider unavailable");
    expect(wrapper.text()).toContain("Completed checkpoints were preserved.");
    // Diagnostics stay closed until asked for; actionable failure is not inside them.
    expect(wrapper.get("details.corpus-build-diagnostics").attributes("open")).toBeUndefined();
    await buttonByText(wrapper, "Resume").trigger("click");
    expect(wrapper.emitted("resume")).toHaveLength(1);
  });

  it("shows initialization as an inline panel, not a modal, with explicit cancellation", async () => {
    const wrapper = mount(CorpusInitializationDialog, {
      props: {
        build: {
          ...buildBase,
          status: "running",
          stage: "segmenting",
          progress: 0.18,
          record_count: 0,
          accepted_count: 0,
        },
      },
      global: { stubs: { Teleport: true } },
    });
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.find("[aria-modal]").exists()).toBe(false);
    expect(wrapper.get("section").attributes("aria-labelledby")).toBe("corpus-init-title");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("18");
    expect(wrapper.findAll("li")[1].attributes("data-state")).toBe("current");
    await buttonByText(wrapper, "Cancel build").trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });

  it("maps reconciliation to the record-construction initialization step", () => {
    const wrapper = mount(CorpusInitializationDialog, {
      props: {
        build: {
          ...buildBase,
          status: "running",
          stage: "reconciling",
          progress: 0.37,
          record_count: 0,
          accepted_count: 0,
        },
      },
      global: { stubs: { Teleport: true } },
    });
    expect(wrapper.findAll("li")[2].attributes("data-state")).toBe("current");
  });

  it("lists issue subqueues under Needs attention in one filter list", async () => {
    const wrapper = mount(CorpusReviewQueueTabs, {
      props: {
        modelValue: "metadata",
        total: 76,
        ready: 7,
        issues: 4,
        metadata: 4,
        topology: 0,
        sourceProblems: 2,
        accepted: 65,
        rejected: 0,
      },
    });
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("metadata");
    await wrapper.get("select").setValue("source");
    expect(lastEmission(wrapper, "update:modelValue")[0]).toBe("source");
    await wrapper.get("select").setValue("accepted");
    expect(lastEmission(wrapper, "update:modelValue")[0]).toBe("accepted");
    expect(wrapper.get("#review-queue-count-help").text()).toContain("counts may overlap");
  });

  it("routes a ready corpus to publication", async () => {
    const wrapper = mount(CorpusFinishWorkspace, { props: { build: buildBase } });
    expect(wrapper.get(".publish-decision").attributes("data-state")).toBe("ready");
    const details = wrapper.get(".readiness-details-toggle");
    expect(details.attributes("aria-expanded")).toBe("false");
    await details.trigger("click");
    expect(details.attributes("aria-expanded")).toBe("true");
    expect(wrapper.get(".finish-primary button").text()).toContain("Publish");
    await wrapper.get(".finish-primary button").trigger("click");
    expect(wrapper.emitted("publish")).toHaveLength(1);
  });

  it("treats an all-rejected corpus as a deliberate no-publication state", async () => {
    const build: any = {
      ...buildBase,
      accepted_count: 0,
      rejected_count: 10,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "no_publishable_records",
        records_accepted: 0,
        records_rejected: 10,
        no_publishable_records: true,
        blockers: [{ code: "no_publishable_records", count: 10 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });
    expect(wrapper.get(".no-publishable").text()).toContain("All records are currently rejected");
    await buttonByText(wrapper, "Return to review").trigger("click");
    expect(wrapper.emitted("reviewRejected")).toBeTruthy();
    await buttonByText(wrapper, "Restore all rejected").trigger("click");
    expect(wrapper.emitted("restoreRejected")).toHaveLength(1);
  });

  it("never leaves 'Inspect remaining work' as a dead button: it goes to the first blocker", async () => {
    const build: any = {
      ...buildBase,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "inspect",
        blockers: [{ code: "boundary_attention", count: 2 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });
    expect(wrapper.get(".publish-decision").attributes("data-state")).toBe("blocked");
    const primary = wrapper.get(".finish-primary button");
    expect(primary.attributes("disabled")).toBeUndefined();
    await primary.trigger("click");
    expect(wrapper.emitted("reviewTopology")).toHaveLength(1);
    await wrapper.setProps({
      build: { ...build, publication_readiness: { ...build.publication_readiness, blockers: [] } },
    });
    await wrapper.get(".finish-primary button").trigger("click");
    expect(wrapper.emitted("reviewRecords")).toHaveLength(1);
  });

  it("routes blocker repair actions to the owning review surface", async () => {
    const build: any = {
      ...buildBase,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "resolve_document_metadata",
        missing_document_fields: ["document_author"],
        blockers: [{ code: "required_document_metadata", count: 1 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });
    expect(wrapper.get(".publish-decision").attributes("data-state")).toBe("blocked");
    expect(wrapper.find(".blockers").exists()).toBe(true);
    expect(wrapper.find(".document-blocker").exists()).toBe(false);
    expect(wrapper.get(".blocker-detail").text().length).toBeGreaterThan(0);
    expect(wrapper.get(".readiness-details-toggle").attributes("aria-expanded")).toBe("false");
    await buttonByText(wrapper, "Fix").trigger("click");
    expect(wrapper.emitted("editDocumentMetadata")).toHaveLength(1);
  });

  it("routes metadata validation blockers to validation review", async () => {
    const build: any = {
      ...buildBase,
      validation: { valid: false, source_valid: true, metadata_valid: false, coverage: 1 },
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "resolve_validation",
        blockers: [{ code: "metadata_validation", count: 12 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });

    await buttonByText(wrapper, "Fix").trigger("click");

    expect(wrapper.emitted("reviewValidation")).toHaveLength(1);
    expect(wrapper.emitted("reviewMetadata")).toBeUndefined();
  });

  it("routes the primary Continue review action to the first actionable blocker", async () => {
    const build: any = {
      ...buildBase,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "review_records",
        blockers: [
          { code: "required_metadata", count: 3 },
          { code: "record_attention", count: 2 },
        ],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });

    await wrapper.get(".finish-primary button").trigger("click");

    expect(wrapper.emitted("reviewMetadata")).toHaveLength(1);
    expect(wrapper.emitted("reviewRecords")).toBeUndefined();
    expect(wrapper.emitted("reviewIssues")).toBeUndefined();
  });

  it("routes structural record-attention blockers to the Issues queue", async () => {
    const build: any = {
      ...buildBase,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "review_records",
        blockers: [{ code: "record_attention", count: 4 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });

    await buttonByText(wrapper, "Fix").trigger("click");

    expect(wrapper.emitted("reviewIssues")).toHaveLength(1);
  });

  it("routes structural boundary blockers to topology review", async () => {
    const build: any = {
      ...buildBase,
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "review_records",
        blockers: [{ code: "boundary_attention", count: 3 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });

    await buttonByText(wrapper, "Fix").trigger("click");

    expect(wrapper.emitted("reviewTopology")).toHaveLength(1);
  });

  it("groups several validation findings on the same record into one fixable row", async () => {
    const build: any = {
      ...buildBase,
      validation: {
        valid: false,
        source_valid: true,
        metadata_valid: false,
        coverage: 1,
        validation_issues: [
          {
            code: "metadata_evidence",
            record_id: "r1",
            field: "speaker",
            reason: "no valid source block",
          },
          {
            code: "citation",
            record_id: "r1",
            field: "",
            reason: "citation is missing or incomplete",
          },
          { code: "metadata_schema", record_id: "r2", field: "stance", reason: "value is invalid" },
        ],
      },
      publication_readiness: {
        ...buildBase.publication_readiness,
        can_publish: false,
        next_action: "resolve_validation",
        blockers: [{ code: "metadata_validation", count: 3 }],
      },
    };
    const wrapper = mount(CorpusFinishWorkspace, { props: { build } });

    // Two findings on r1 read as one row with a count, not two look-alike rows.
    const groups = wrapper.findAll(".issue-group");
    expect(groups).toHaveLength(2);
    expect(groups[0].text()).toContain("r1");
    expect(groups[0].get(".count-pill").text()).toBe("2");
    expect(groups[0].findAll(".issue-group-reasons li")).toHaveLength(2);

    await groups[0].get("button").trigger("click");
    const [issue] = lastEmission(wrapper, "fixIssue");
    expect(issue.record_id).toBe("r1");
    expect(issue.field).toBe("speaker");
  });
});
