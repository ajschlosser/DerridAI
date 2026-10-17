// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusReviewSessionBar from "../../src/components/CorpusReviewSessionBar.vue";

describe("Review identity strip",()=>{
  it("keeps source and accepted/remaining scope in compact review and opens focus",async()=>{
    const wrapper=mount(CorpusReviewSessionBar,{props:{compact:true,sourceFilename:'La Prisonnière.html',accepted:5,remaining:365,reviewable:18,issues:251,model:'example-model',buildId:'b1'}});
    expect(wrapper.text()).toContain('La Prisonnière.html');
    expect(wrapper.findAll('dt').map(node=>node.text())).toEqual(['accepted','remaining']);
    expect(wrapper.text()).not.toContain('example-model');
    await wrapper.get('button').trigger('click');
    expect(wrapper.emitted('focus')).toHaveLength(1);
  });
  it("preserves expanded information and disabled focus behavior",()=>{
    const wrapper=mount(CorpusReviewSessionBar,{props:{sourceFilename:'source.pdf',model:'example-model',buildId:'b1',focusDisabled:true}});
    expect(wrapper.findAll('dt')).toHaveLength(4);
    expect(wrapper.text()).toContain('example-model');
    expect(wrapper.get('button').attributes('disabled')).toBeDefined();
  });
});
