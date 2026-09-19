import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusMetadataResolutionPanel from "../../src/components/CorpusMetadataResolutionPanel.vue";

function lastEmission(wrapper:any,event:string){const events=wrapper.emitted(event)||[];return events[events.length-1]||[]}
function record(overrides:Record<string,unknown>={}){
  return {record_id:"r-1",record_revision:1,text:"A passage under review.",source_block_ids:["b1"],source_spans:[],pdf_pages:[1],needs_review:true,review_disposition:"pending",metadata_complete:false,metadata_incomplete_fields:[],metadata_review_fields:[],metadata_field_status:{},...overrides} as any;
}
const mountPanel=(item:any)=>mount(CorpusMetadataResolutionPanel,{
  props:{record:item,regionTypes:["main_text","front_matter","back_matter"],discourseRoles:["assertion","analysis","quotation"]},
  global:{stubs:{CorpusMetadataFieldEditor:true,CorpusFieldOwnershipBadge:true}},
});

describe("Corpus Builder metadata resolution",()=>{
  it("offers one-click confirmation for unresolved LLM proposals without filtering them by raw confidence",async()=>{
    const wrapper=mountPanel(record({discourse_role:"analysis",metadata_incomplete_fields:["discourse_role"],metadata_review_fields:["discourse_role"],metadata_field_status:{discourse_role:{status:"unresolved",method:"llm",confidence:.42,reason:"Model proposal requires review."}}}));
    expect(wrapper.get(".suggestion-toolbar").text()).toContain("1 LLM suggestion");
    await wrapper.get(".suggestion-toolbar button").trigger("click");
    expect(lastEmission(wrapper,"resolveMany")[0]).toEqual({discourse_role:"analysis"});
  });

  it("shows progressive enrichment as processing rather than falsely settled",()=>{
    const wrapper=mountPanel(record({metadata_enrichment_state:"running",metadata_incomplete_fields:["position_holder"],metadata_review_fields:["position_holder"],metadata_field_status:{position_holder:{status:"unresolved",method:"llm"}}}));
    expect(wrapper.get(".review-status").attributes("data-state")).toBe("processing");
    expect(wrapper.get('[role="status"]').text()).toContain("LLM enrichment pending");
  });

  it("separates inherited document metadata from record-level decisions",()=>{
    const wrapper=mountPanel(record({work:"On Cosmopolitanism and Forgiveness",document_author:"Jacques Derrida",region_type:"main_text",metadata_field_status:{
      work:{status:"inherited",method:"document_manifest",confidence:1},
      document_author:{status:"inherited",method:"document_manifest",confidence:1},
      region_type:{status:"human_confirmed",method:"human",confidence:1},
    }}));
    expect(wrapper.get(".inherited-metadata").text()).toContain("Inherited document metadata");
    expect(wrapper.get(".settled-metadata").exists()).toBe(true);
    expect(wrapper.find(".suggestion-toolbar").exists()).toBe(false);
  });

  it("keeps invalid or unresolved active fields in the attention group",()=>{
    const wrapper=mountPanel(record({stance:"affirm",metadata_field_status:{stance:{status:"invalid",method:"llm",confidence:.9}}}));
    expect(wrapper.get('.metadata-grid[role="list"]').exists()).toBe(true);
    expect(wrapper.get(".review-status").attributes("data-state")).toBe("attention");
  });
});
