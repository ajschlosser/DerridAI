// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { CorpusBuild } from "../../src/api/pdfCorpus";
import CorpusBuildOverview from "../../src/components/CorpusBuildOverview.vue";
const build=(overrides:Partial<CorpusBuild>={}):CorpusBuild=>({build_id:"b1",asset_id:"a1",source_filename:"source.pdf",source_sha256:"sha",status:"running",stage:"enriching",progress:.8,created_at:"",record_count:370,accepted_count:0,needs_review_count:251,profile_id:"test",review_queue_counts:{ready:18,preparing:101,issues:251,metadata:200,source:100},...overrides});
const open=(overrides:Partial<CorpusBuild>={},locked=false,disabled=false)=>mount(CorpusBuildOverview,{props:{build:build(overrides),locked,disabled},global:{stubs:{CorpusMetadataLiveStatus:true}}});
describe("Build overview",()=>{
  it("makes ready records the primary action and emits the correct queues",async()=>{
    const wrapper=open();
    expect(wrapper.get("h3").text()).toBe("18 records are ready to review");
    await wrapper.get(".overview-actions .primary").trigger("click");
    await wrapper.findAll(".overview-actions button")[1].trigger("click");
    expect(wrapper.emitted("review")).toEqual([["ready"],["issues"]]);
    expect(wrapper.findAll(".overview-tiles .tile-count").map(x=>x.text())).toEqual(["18","101","251"]);
  });
  it("shows a waiting state without a fake ready action",()=>{
    const wrapper=open({review_queue_counts:{ready:0,preparing:119,issues:251}});
    expect(wrapper.get("h3").text()).toContain("No records are ready");
    expect(wrapper.find(".overview-actions .primary").exists()).toBe(false);
  });
  it("does not infer ready records or zero counts from absent queues",async()=>{
    const wrapper=open({review_queue_counts:undefined});
    expect(wrapper.get("h3").text()).toBe("Inspect the available records");
    expect(wrapper.findAll(".overview-tiles .tile-count").map(x=>x.text())).toEqual(["—","—","—"]);
    await wrapper.get(".overview-actions button").trigger("click");
    expect(wrapper.emitted("review")).toEqual([["all"]]);
  });
  it.each([[true,false],[false,true]])("preserves lock=%s and busy=%s",async(locked,disabled)=>{
    const wrapper=open({},locked,disabled);
    expect(wrapper.findAll("button").every(x=>x.attributes("disabled")!==undefined)).toBe(true);
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("review")).toBeUndefined();
  });
  it("does not display running task controls after interruption",()=>{
    const wrapper=open({status:"interrupted"});
    expect(wrapper.findComponent({name:"CorpusMetadataLiveStatus"}).exists()).toBe(false);
    expect(wrapper.text()).toContain("Publication still requires");
  });
});
