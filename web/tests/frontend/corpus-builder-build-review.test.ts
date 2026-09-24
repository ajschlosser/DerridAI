import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusBuildProgress from "../../src/components/CorpusBuildProgress.vue";
import CorpusFinishWorkspace from "../../src/components/CorpusFinishWorkspace.vue";
import CorpusInitializationDialog from "../../src/components/CorpusInitializationDialog.vue";
import CorpusReviewQueueTabs from "../../src/components/CorpusReviewQueueTabs.vue";

function buttonByText(wrapper:any, text:string) {
  const button=wrapper.findAll("button").find((node:any)=>node.text().includes(text));
  if(!button)throw new Error("Button not found: "+text);
  return button;
}
function lastEmission(wrapper:any,event:string){const events=wrapper.emitted(event)||[];return events[events.length-1]||[]}

const buildBase:any={
  build_id:"build-1",asset_id:"asset",source_filename:"book.pdf",source_sha256:"sha",status:"awaiting_review",stage:"review",progress:1,
  created_at:"",record_count:10,accepted_count:10,rejected_count:0,
  validation:{valid:true,source_valid:true,metadata_valid:true,coverage:1},source_quality:{blocking_page_count:0},
  metadata_issue_summary:{records_incomplete:0,fields_unresolved:0,auto_retry_fields:0,human_review_fields:0},
  publication_readiness:{can_publish:true,next_action:"publish",records_total:10,records_reviewed:10,records_accepted:10,records_rejected:0,records_pending:0,blockers:[]},
};

describe("Corpus Builder build, review, and finish states", () => {
  it("reports progress, unresolved topology, LLM telemetry, and validation hazards accessibly", () => {
    const wrapper=mount(CorpusBuildProgress,{props:{
      status:"awaiting_review",stage:"review",progress:.63,recordCount:31,reviewCount:4,acceptedCount:27,unresolvedCount:2,
      llmMetrics:{calls:12,retries:2,structured_output_failures:1},
      validation:{valid:false,coverage:.98,metadata_evidence_errors:[{record_id:"r1",reason:"Speaker evidence is invalid."}],metadata_schema_errors:["stance"],citation_errors:["r1"]},
      warnings:["One boundary remains unresolved."],
    }});
    const progress=wrapper.get('[role="progressbar"]');
    expect(progress.attributes("aria-valuenow")).toBe("63");
    expect(progress.attributes("aria-valuetext")).toContain("63%");
    expect(wrapper.get(".unresolved-line").text()).toContain("2");
    expect(wrapper.get(".llm-metrics").text()).toContain("12");
    expect(wrapper.get(".validation-strip").text()).toContain("Validation needs attention");
    expect(wrapper.find(".validation-details").exists()).toBe(true);
  });

  it("surfaces recoverable build failures as alerts without hiding preserved warnings", () => {
    const wrapper=mount(CorpusBuildProgress,{props:{
      status:"failed",stage:"failed",progress:.48,recordCount:84,reviewCount:0,acceptedCount:0,
      error:"Provider unavailable.",warnings:["Completed checkpoints were preserved."],validation:null,
    }});
    expect(wrapper.get('[role="alert"]').text()).toContain("Provider unavailable");
    expect(wrapper.get(".warnings").text()).toContain("build warning");
  });

  it("shows initialization as an inline panel, not a modal, with explicit cancellation", async () => {
    const wrapper=mount(CorpusInitializationDialog,{
      props:{build:{...buildBase,status:"running",stage:"segmenting",progress:.18,record_count:0,accepted_count:0}},
      global:{stubs:{Teleport:true}},
    });
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false);
    expect(wrapper.find('[aria-modal]').exists()).toBe(false);
    expect(wrapper.get("section").attributes("aria-labelledby")).toBe("corpus-init-title");
    expect(wrapper.get('[role="progressbar"]').attributes("aria-valuenow")).toBe("18");
    expect(wrapper.findAll("li")[1].attributes("data-state")).toBe("current");
    await buttonByText(wrapper,"Cancel build").trigger("click");
    expect(wrapper.emitted("cancel")).toHaveLength(1);
  });

  it("maps reconciliation to the record-construction initialization step", () => {
    const wrapper=mount(CorpusInitializationDialog,{
      props:{build:{...buildBase,status:"running",stage:"reconciling",progress:.37,record_count:0,accepted_count:0}},
      global:{stubs:{Teleport:true}},
    });
    expect(wrapper.findAll("li")[2].attributes("data-state")).toBe("current");
  });

  it("maps issue subqueues to the primary Issues tab and supports keyboard navigation", async () => {
    const wrapper=mount(CorpusReviewQueueTabs,{props:{modelValue:"metadata",total:76,ready:7,issues:4,metadata:4,topology:0,sourceProblems:2,accepted:65,rejected:0}});
    expect(wrapper.get('[data-review-queue="issues"]').attributes("aria-pressed")).toBe("true");
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("metadata");
    await wrapper.get("select").setValue("source");
    expect(lastEmission(wrapper,"update:modelValue")[0]).toBe("source");
    await wrapper.get('[data-review-queue="issues"]').trigger("keydown",{key:"ArrowRight"});
    expect(lastEmission(wrapper,"update:modelValue")[0]).toBe("accepted");
    expect(wrapper.get(".queue-count-help").text()).toContain("counts may overlap");
  });

  it("routes a ready corpus to publication", async () => {
    const wrapper=mount(CorpusFinishWorkspace,{props:{build:buildBase}});
    expect(wrapper.get("#finish-corpus-title").text()).toContain("Ready to publish");
    await wrapper.get(".finish-primary button").trigger("click");
    expect(wrapper.emitted("publish")).toHaveLength(1);
  });

  it("treats an all-rejected corpus as a deliberate no-publication state", async () => {
    const build:any={...buildBase,accepted_count:0,rejected_count:10,publication_readiness:{...buildBase.publication_readiness,can_publish:false,next_action:"no_publishable_records",records_accepted:0,records_rejected:10,no_publishable_records:true,blockers:[{code:"no_publishable_records",count:10}]}};
    const wrapper=mount(CorpusFinishWorkspace,{props:{build}});
    expect(wrapper.get(".no-publishable").text()).toContain("All records are currently rejected");
    await buttonByText(wrapper,"Return to review").trigger("click");
    expect(wrapper.emitted("reviewRejected")).toBeTruthy();
    await buttonByText(wrapper,"Restore all rejected").trigger("click");
    expect(wrapper.emitted("restoreRejected")).toHaveLength(1);
  });

  it("routes blocker repair actions to the owning review surface", async () => {
    const build:any={...buildBase,publication_readiness:{...buildBase.publication_readiness,can_publish:false,next_action:"resolve_document_metadata",missing_document_fields:["document_author"],blockers:[{code:"required_document_metadata",count:1}]}};
    const wrapper=mount(CorpusFinishWorkspace,{props:{build}});
    expect(wrapper.find(".blockers").exists()).toBe(true);
    await buttonByText(wrapper,"Go fix").trigger("click");
    expect(wrapper.emitted("editDocumentMetadata")).toHaveLength(1);
  });
});
