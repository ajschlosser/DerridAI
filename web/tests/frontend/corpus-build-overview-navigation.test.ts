// Copyright 2026 Aaron John Schlosser, PhD.
import { shallowMount, flushPromises } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PdfCorpusBuilder from "../../src/components/PdfCorpusBuilder.vue";
import { ApiError } from "../../src/api/http";

const fixture=vi.hoisted(()=>({
  build:{build_id:"b1",asset_id:"a1",source_filename:"source.pdf",source_sha256:"sha",status:"awaiting_review",stage:"review",progress:.9,record_count:2,accepted_count:0,needs_review_count:0,review_queue_counts:{all:2,ready:2,pending:2},profile_id:"test",warnings:[] as string[],metadata_issue_summary:{issues:[] as Array<{record_id:string;field:string}>}},
  record:{record_id:"r1",record_revision:1,text:"Original source text",text_length:20,source_block_ids:[] as string[],source_spans:[],metadata_complete:true,metadata_incomplete_fields:[] as string[],metadata_review_fields:[] as string[]},
  calls:vi.fn(),
  buildRead:undefined as (()=>Promise<unknown>)|undefined,
  blockRead:undefined as ((ids:string[])=>Promise<unknown>)|undefined,
  listRead:undefined as ((offset:number)=>Promise<unknown>)|undefined,
  saveText:undefined as (()=>Promise<unknown>)|undefined,
  recordRead:undefined as ((query:string)=>Promise<{items:unknown[];total:number;offset:number;limit:number}>)|undefined,
  twoRecords:false,
}));
vi.mock("../../src/runtime/runtime.js",()=>({__v_isRef:false,getProviderProfilesForUi:()=>[],getDefaultProviderProfileId:()=>"",getProviderRequestConfigForUi:()=>null,registerExternalJob:vi.fn()}));
vi.mock("vue-router",()=>({useRoute:()=>({query:{build:"b1"}}),useRouter:()=>({replace:vi.fn()})}));
vi.mock("../../src/api/system",()=>({systemApi:{researcherProviders:async()=>({profiles:[]})}}));
vi.mock("../../src/api/metadataSchemas",()=>({metadataSchemasApi:{list:async()=>({items:[]})}}));
vi.mock("../../src/api/pdfCorpus",()=>({pdfCorpusApi:new Proxy({}, {get:(_,method)=>method==='assetContentUrl'?()=>'/source.pdf':async(...args:unknown[])=>{
  fixture.calls(method,...args);
  if(method==='listBuilds')return fixture.listRead?fixture.listRead(Number(args[0])):{items:[fixture.build],total:1};
  if(method==='build')return fixture.buildRead?fixture.buildRead():fixture.build;
  if(method==='listAssets')return {items:['a1','a2'].map(asset_id=>({asset_id,filename:asset_id+'.pdf',sha256:'sha',page_count:1,block_count:1,ocr_pages:0,pages:[]}))};
  if(method==='records'&&fixture.recordRead)return fixture.recordRead(String(args[4]||''));
  if(method==='records')return {items:fixture.twoRecords?[fixture.record,{...fixture.record,record_id:'r2',text:'Second record',source_block_ids:['block-2']}]:[fixture.record],total:2,offset:0,limit:50};
  if(method==='blocks')return fixture.blockRead?fixture.blockRead(args[3] as string[]):{items:[]};
  if(method==='patchText'&&fixture.saveText)return fixture.saveText();
  return {items:[],profiles:[],blocks:[]};
}})}));

describe("Build overview navigation",()=>{
  beforeEach(()=>{fixture.record.metadata_incomplete_fields=[];fixture.record.metadata_review_fields=[];fixture.record.source_block_ids=[];fixture.buildRead=undefined;fixture.blockRead=undefined;fixture.listRead=undefined;fixture.saveText=undefined;fixture.twoRecords=false;fixture.recordRead=undefined;fixture.build.warnings=[];fixture.build.metadata_issue_summary.issues=[]});
  it("keeps the review editor and draft mounted, and disables hidden review shortcuts",async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();
      const edit=wrapper.findAll("button").find(button=>button.text()==='Edit text');
      expect(edit).toBeDefined();
      await edit!.trigger('click');
      const editor=wrapper.get<HTMLTextAreaElement>('.record-text-editor');
      await editor.setValue('Unsaved reviewed text');
      const element=editor.element;
      await wrapper.get('.build-view-switch button').trigger('click');
      expect(wrapper.get('.review-content').attributes('style')).toContain('display: none');
      expect(wrapper.get('.record-text-editor').element).toBe(element);
      fixture.calls.mockClear();
      window.dispatchEvent(new KeyboardEvent('keydown',{key:'r',cancelable:true}));
      await flushPromises();
      expect(fixture.calls.mock.calls.some(([method])=>method==='reviewDecision')).toBe(false);
      await wrapper.findAll('.build-view-switch button')[1].trigger('click');
      expect(wrapper.get('.record-text-editor').element).toBe(element);
      expect(editor.element.value).toBe('Unsaved reviewed text');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it("opens required metadata decisions without discarding the text draft",async()=>{
    fixture.record.metadata_incomplete_fields=['target','stance'];
    fixture.record.metadata_review_fields=['target'];
    const originalScroll=HTMLElement.prototype.scrollIntoView;
    HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();
      expect(wrapper.get('#record-metadata-blocker').text()).toContain('2 required fields before acceptance');
      const edit=wrapper.findAll('button').find(button=>button.text()==='Edit text');
      await edit!.trigger('click');
      const editor=wrapper.get<HTMLTextAreaElement>('.record-text-editor');
      await editor.setValue('Keep this unsaved draft');
      await wrapper.get('#record-metadata-blocker button').trigger('click');
      expect(wrapper.get('.review-grid').classes()).toContain('metadata-workspace');
      expect(wrapper.get('.record-text-editor').element).toBe(editor.element);
      await wrapper.get('.workspace-switcher button').trigger('click');
      expect(editor.element.value).toBe('Keep this unsaved draft');
      expect(wrapper.get('.review-grid').classes()).not.toContain('detail-mode');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('restores the separate setup draft and rejects a late inspected-build response',async()=>{
    localStorage.setItem('derridai.pdf-corpus-builder.draft.v2',JSON.stringify({selectedAssetId:'a2',manualModel:'draft-model',semanticIndexing:false}));
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();
      expect(JSON.parse(localStorage.getItem('derridai.pdf-corpus-builder.draft.v2')!).selectedAssetId).toBe('a2');
      let resolve!:(value:unknown)=>void;
      fixture.buildRead=()=>new Promise(done=>{resolve=done});
      wrapper.findComponent({name:'CorpusBuildHistoryMenu'}).vm.$emit('select',{...fixture.build,build_id:'b2'});
      await wrapper.vm.$nextTick();
      const setup=wrapper.findAll('button').find(button=>button.text()==='Start new build')!;
      await setup.trigger('click');
      expect(wrapper.get<HTMLSelectElement>('#pdf-corpus-source').element.value).toBe('a2');
      resolve({...fixture.build,build_id:'b2'});await flushPromises();
      expect(wrapper.find('.builder-setup').exists()).toBe(true);
      expect(wrapper.get<HTMLSelectElement>('#pdf-corpus-source').element.value).toBe('a2');
      wrapper.findComponent({name:'CorpusBuildHistoryMenu'}).vm.$emit('refresh');await flushPromises();
      expect(wrapper.find('.builder-setup').exists()).toBe(true);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it.each(['resolve','reject','denied'])('ignores a late source-block %s after record selection changes',async(outcome)=>{
    fixture.record.source_block_ids=['block-1'];fixture.twoRecords=true;
    let resolve!:(value:unknown)=>void,reject!:(reason:Error)=>void;
    const oldRead=new Promise((done,fail)=>{resolve=done;reject=fail});
    fixture.blockRead=ids=>ids.includes('block-1')?oldRead:Promise.resolve({items:[{block_id:'block-2',text:'Current source evidence',page:1,type:'text'}]});
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();await wrapper.findAll('.record-row')[1].trigger('click');await flushPromises();
      await wrapper.findAll('.workspace-switcher button')[2].trigger('click');
      expect(wrapper.get('.source-block').text()).toContain('Current source evidence');
      if(outcome==='resolve')resolve({items:[{block_id:'block-1',text:'Old source evidence',page:1,type:'text'}]});
      else reject(outcome==='denied'?new ApiError('Old source read failed',403):new Error('Old source read failed'));
      await flushPromises();
      expect(wrapper.get('.source-block').text()).toContain('Current source evidence');
      expect(wrapper.text()).not.toContain('Old source read failed');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('retains current source evidence on refresh failure and retries locally',async()=>{
    fixture.record.source_block_ids=['block-1'];
    const block=(text:string)=>({items:[{block_id:'block-1',text,page:1,type:'text'}]});
    fixture.blockRead=async()=>block('Saved source evidence');
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();await wrapper.findAll('.workspace-switcher button')[2].trigger('click');
      fixture.blockRead=async()=>{throw new Error('Source unavailable')};
      await wrapper.get('.record-row').trigger('click');await flushPromises();
      expect(wrapper.get('.source-block').text()).toContain('Saved source evidence');
      expect(wrapper.get('.source-read-error').text()).toContain('Source unavailable');
      fixture.blockRead=async()=>block('Refreshed source evidence');
      await wrapper.get('.source-read-error button').trigger('click');await flushPromises();
      expect(wrapper.get('.source-block').text()).toContain('Refreshed source evidence');
      expect(wrapper.find('.source-read-error').exists()).toBe(false);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('suppresses an old build failure after returning to setup',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();let reject!:(reason:Error)=>void;
      fixture.buildRead=()=>new Promise((_,fail)=>{reject=fail});
      wrapper.findComponent({name:'CorpusBuildHistoryMenu'}).vm.$emit('select',{...fixture.build,build_id:'b2'});
      await wrapper.vm.$nextTick();
      await wrapper.findAll('button').find(button=>button.text()==='Start new build')!.trigger('click');
      reject(new Error('Old build failure'));await flushPromises();
      expect(wrapper.find('.builder-setup').exists()).toBe(true);
      expect(wrapper.text()).not.toContain('Old build failure');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it.each([401,403])('clears retained source blocks when the current read is denied (%s)',async(status)=>{
    fixture.record.source_block_ids=['block-1'];
    fixture.blockRead=async()=>({items:[{block_id:'block-1',text:'Restricted source evidence',page:1,type:'text'}]});
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();await wrapper.findAll('.workspace-switcher button')[2].trigger('click');
      expect(wrapper.get('.source-block').text()).toContain('Restricted source evidence');
      fixture.blockRead=async()=>{throw new ApiError('Access denied',status)};
      await wrapper.get('.record-row').trigger('click');await flushPromises();
      expect(wrapper.find('.source-block').exists()).toBe(false);
      expect(wrapper.get('.source-read-error').text()).toContain('Access denied');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('deduplicates changing history pages without losing already loaded builds',async()=>{
    fixture.listRead=async offset=>({items:offset===0?[fixture.build]:offset===1?[{...fixture.build,status:'ready'},{...fixture.build,build_id:'b2'}]:[{...fixture.build,build_id:'b3'}],total:3});
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();const history=wrapper.findComponent({name:'CorpusBuildHistoryMenu'});
      history.vm.$emit('loadMore');await flushPromises();
      expect(history.props('builds').map((build:{build_id:string})=>build.build_id)).toEqual(['b1','b2']);
      history.vm.$emit('loadMore');await flushPromises();
      expect(history.props('builds').map((build:{build_id:string})=>build.build_id)).toEqual(['b1','b2','b3']);
      expect(history.props('total')).toBe(3);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('disables review shortcuts while build details are open',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder);
    try{
      await flushPromises();
      wrapper.findComponent({name:'CorpusBuildDetailsPanel'}).vm.$emit('openChange',true);
      await wrapper.vm.$nextTick();fixture.calls.mockClear();
      window.dispatchEvent(new KeyboardEvent('keydown',{key:'r',cancelable:true}));
      await flushPromises();
      expect(fixture.calls.mock.calls.some(([method])=>method==='reviewDecision')).toBe(false);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  function warningNavigation(){
    fixture.build.warnings=['r2: work_profile metadata failed (structured_output_invalid); review required.'];
    fixture.build.metadata_issue_summary.issues=[{record_id:'r2',field:'stance'}];
    fixture.twoRecords=true;
    return shallowMount(PdfCorpusBuilder,{global:{stubs:{CorpusBuildDetailsPanel:{template:'<div><slot name="issues" /></div>',methods:{close(){}}}}}});
  }
  it('opens only the exact verified warning record in the metadata workspace',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=warningNavigation();
    try{
      await flushPromises();fixture.calls.mockClear();
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','unverified');await flushPromises();
      expect(fixture.calls).not.toHaveBeenCalled();
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await flushPromises();
      expect(fixture.calls).toHaveBeenCalledWith('records','b1',0,50,'all','r2');
      expect(wrapper.findComponent({name:'CorpusMetadataResolutionPanel'}).props('record').record_id).toBe('r2');
      expect(wrapper.get('.review-grid').classes()).toContain('metadata-workspace');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('keeps the current draft when a warning lookup fails or has no exact match',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=warningNavigation();
    try{
      await flushPromises();await wrapper.findAll('button').find(button=>button.text()==='Edit text')!.trigger('click');
      await wrapper.get('.record-text-editor').setValue('Keep my current draft');
      fixture.recordRead=async()=>({items:[{...fixture.record,record_id:'r20'}],total:1,offset:0,limit:50});
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await flushPromises();
      expect(wrapper.get('.warning-record-error').text()).toContain('could not be verified');
      expect(wrapper.get<HTMLTextAreaElement>('.record-text-editor').element.value).toBe('Keep my current draft');
      fixture.recordRead=async()=>{throw new Error('Record read unavailable')};
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await flushPromises();
      expect(wrapper.get('.warning-record-error').text()).toBe('Record read unavailable');
      expect(wrapper.findComponent({name:'CorpusMetadataResolutionPanel'}).props('record').record_id).toBe('r1');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('ignores a warning lookup after build identity changes',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=warningNavigation();
    try{
      await flushPromises();let resolve!:(value:{items:unknown[];total:number;offset:number;limit:number})=>void;
      fixture.recordRead=()=>new Promise(done=>{resolve=done});
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await wrapper.vm.$nextTick();
      fixture.recordRead=undefined;fixture.buildRead=async()=>({...fixture.build,build_id:'b2'});
      wrapper.findComponent({name:'CorpusBuildHistoryMenu'}).vm.$emit('select',{...fixture.build,build_id:'b2'});await flushPromises();
      resolve({items:[{...fixture.record,record_id:'r2'}],total:1,offset:0,limit:50});await flushPromises();
      expect(wrapper.findComponent({name:'CorpusMetadataResolutionPanel'}).props('record').record_id).toBe('r1');
      expect(wrapper.find('.warning-record-error').exists()).toBe(false);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('preserves text and metadata drafts when a warning points to the selected record',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=warningNavigation();
    try{
      await flushPromises();
      fixture.build.warnings=['r1: work_profile metadata failed (structured_output_invalid); review required.'];fixture.build.metadata_issue_summary.issues=[{record_id:'r1',field:'stance'}];
      await wrapper.findAll('button').find(button=>button.text()==='Edit text')!.trigger('click');
      const editor=wrapper.get<HTMLTextAreaElement>('.record-text-editor');await editor.setValue('Same-record draft');
      await wrapper.get('.metadata-json').setValue('{"stance":"questions"}');
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r1');await flushPromises();
      expect(wrapper.get('.record-text-editor').element).toBe(editor.element);
      expect(editor.element.value).toBe('Same-record draft');
      expect(wrapper.get<HTMLTextAreaElement>('.metadata-json').element.value).toBe('{"stance":"questions"}');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('rechecks current issue membership after the record read',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=warningNavigation();
    try{
      await flushPromises();let resolve!:(value:{items:unknown[];total:number;offset:number;limit:number})=>void;
      fixture.recordRead=()=>new Promise(done=>{resolve=done});
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await wrapper.vm.$nextTick();
      fixture.build.metadata_issue_summary.issues=[];
      resolve({items:[{...fixture.record,record_id:'r2'}],total:1,offset:0,limit:50});await flushPromises();
      expect(wrapper.findComponent({name:'CorpusMetadataResolutionPanel'}).props('record').record_id).toBe('r1');
      expect(wrapper.get('.warning-record-error').text()).toContain('could not be verified');
      expect(wrapper.findComponent({name:'CorpusBuildWarnings'}).props('disabled')).toBe(false);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('opens metadata review from a completed review session without returning to the finish page',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    fixture.build.accepted_count=2;
    const wrapper=warningNavigation();
    try{
      await flushPromises();fixture.calls.mockClear();
      wrapper.findComponent({name:'CorpusBuildWarnings'}).vm.$emit('review','r2');await flushPromises();
      expect(fixture.calls).toHaveBeenCalledWith('records','b1',0,50,'metadata','r2');
      expect(wrapper.findComponent({name:'CorpusMetadataResolutionPanel'}).props('record').record_id).toBe('r2');
      expect(wrapper.get('.review-grid').classes()).toContain('metadata-workspace');
    }finally{wrapper.unmount();fixture.build.accepted_count=0;HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('uses the saved setup draft from the settings shortcut',async()=>{
    localStorage.setItem('derridai.pdf-corpus-builder.draft.v2',JSON.stringify({selectedAssetId:'a2'}));
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder,{global:{stubs:{CorpusBuildDetailsPanel:{template:'<div><slot name="settings" /></div>'}}}});
    try{
      await flushPromises();await wrapper.get('.active-build-settings button').trigger('click');
      expect(wrapper.get<HTMLSelectElement>('#pdf-corpus-source').element.value).toBe('a2');
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
  it('does not switch builds or reset setup while text is saving',async()=>{
    const originalScroll=HTMLElement.prototype.scrollIntoView;HTMLElement.prototype.scrollIntoView=vi.fn();
    const wrapper=shallowMount(PdfCorpusBuilder,{global:{stubs:{CorpusBuildDetailsPanel:{template:'<div><slot name="settings" /></div>'}}}});
    try{
      await flushPromises();let resolve!:(value:unknown)=>void;
      fixture.saveText=()=>new Promise(done=>{resolve=done});
      await wrapper.findAll('button').find(button=>button.text()==='Edit text')!.trigger('click');
      await wrapper.get('.record-text-editor').setValue('Saving this draft');
      await wrapper.findAll('button').find(button=>button.text()==='Save & mark reviewed')!.trigger('click');
      const history=wrapper.findComponent({name:'CorpusBuildHistoryMenu'});
      expect(history.props('disabled')).toBe(true);
      history.vm.$emit('select',{...fixture.build,build_id:'b2'});await wrapper.vm.$nextTick();
      expect(history.props('selectedBuildId')).toBe('b1');
      expect(wrapper.get('.active-build-settings button').attributes('disabled')).toBeDefined();
      resolve(fixture.record);await flushPromises();
      expect(history.props('disabled')).toBe(false);
    }finally{wrapper.unmount();HTMLElement.prototype.scrollIntoView=originalScroll}
  });
});
