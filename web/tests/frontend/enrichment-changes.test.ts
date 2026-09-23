import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusEnrichmentChanges from "../../src/components/CorpusEnrichmentChanges.vue";

const record=(over:Record<string,unknown>={})=>({
  needs_review:true,speaker:"Jacques Derrida",stance:"critique",target:"hospitality",
  metadata_field_status:{speaker:{status:"model_inferred"},stance:{status:"model_inferred"},target:{status:"unresolved",method:"llm",verification_status:"pending_review"}},
  metadata_enrichment_history:[{run_id:"r1",pass:2,model:"qwen3.5:4b",outcome:"disputed",added_fields:["speaker"],replaced:[{field:"stance",previous:"assertion",value:"critique"}],disputes:[]}],
  metadata_disputes:[{field:"target",existing:"cities of refuge",proposed:"hospitality",candidates:[
    {candidate_id:"c1",value:"cities of refuge",source:"current"},
    {candidate_id:"c2",value:"hospitality",source:"llm",model:"qwen3.5:4b",run_id:"r1",pass:2,confidence:.91},
  ]}],
  ...over,
});
const mountWith=(r:Record<string,unknown>)=>mount(CorpusEnrichmentChanges,{props:{record:r}});

describe("changes made by enrichment",()=>{
  beforeEach(()=>setActivePinia(createPinia()));
  it("shows authoritative candidates with provenance outside the action",()=>{
    const text=mountWith(record()).text();
    expect(text).toContain("cities of refuge");expect(text).toContain("hospitality");expect(text).toContain("qwen3.5:4b");expect(text).toContain("pass 2");expect(text).toContain("91%");
    expect(text).not.toContain("Use qwen3.5:4b");
  });
  it("restores, keeps, or uses a candidate with compact buttons",async()=>{
    const wrapper=mountWith(record());const buttons=wrapper.findAll("button");
    await buttons.find(b=>b.text()==="Restore previous")!.trigger("click");
    await buttons.find(b=>b.text()==="Keep current")!.trigger("click");
    await buttons.find(b=>b.text()==="Use this value")!.trigger("click");
    expect(wrapper.emitted("resolve")).toEqual([["stance","assertion"],["target","cities of refuge"],["target","hospitality"]]);
  });
  it("prefers metadata_disputes over stale history from an earlier pass",()=>{
    const wrapper=mountWith(record({metadata_enrichment_history:[{run_id:"r1",pass:1,outcome:"disputed",disputes:[{field:"target",existing:"cities of refuge",proposed:"hospitality"}]}],metadata_disputes:[{field:"target",existing:"cities of refuge",proposed:"cosmopolitanism",candidates:[{value:"cities of refuge",source:"current"},{value:"hospitality",source:"llm",model:"m1",pass:1},{value:"cosmopolitanism",source:"llm",model:"m2",pass:2}]}]}));
    expect(wrapper.text()).toContain("cosmopolitanism");expect(wrapper.text()).toContain("m2");expect(wrapper.text()).toContain("pass 2");
  });
  it("shows protected suggestions and agreement without requiring review",()=>{
    const wrapper=mountWith(record({
      needs_review:false,
      metadata_enrichment_history:[{
        run_id:"r2",pass:3,model:"qwen3.5:4b",outcome:"unchanged",disputes:[],
        informational:[
          {kind:"protected_suggestion",field:"speaker",authoritative_value:"Jacques Derrida",proposed_value:"Another author",model:"qwen3.5:4b",pass:3,confidence:.92,reason:"Human-owned value retained."},
          {kind:"agreement",field:"stance",authoritative_value:"critical",proposed_value:"critical",model:"qwen3.5:4b",pass:3,reason:"No new supported value."},
        ],
      }],
      metadata_disputes:[],
    }));
    expect(wrapper.text()).toContain("Protected value retained");
    expect(wrapper.text()).toContain("Another author");
    expect(wrapper.text()).toContain("No new supported value");
    expect(wrapper.findAll("button")).toHaveLength(0);
  });
});
