import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CorpusRecordFocusReview from "../../src/components/CorpusRecordFocusReview.vue";

function buttonByText(wrapper:any,text:string){
  const button=wrapper.findAll("button").find((node:any)=>node.text().includes(text));
  if(!button)throw new Error("Button not found: "+text);
  return button;
}
function lastEmission(wrapper:any,event:string){const events=wrapper.emitted(event)||[];return events[events.length-1]||[]}

const record:any={
  record_id:"record-00014",record_revision:2,text:"A representative passage under review.",text_length:42,page_start:22,page_end:23,pdf_pages:[24],
  source_block_ids:["p24-b1"],source_spans:[],needs_review:true,review_reason:"Boundary requires review.",review_disposition:"pending",
  metadata_field_status:{},metadata_evidence:{},metadata_incomplete_fields:[],metadata_review_fields:[],region_type:"main_text",primary_text:true,
};
const stubs={CorpusSourceIssuePanel:true,CorpusMetadataResolutionPanel:true,CorpusTextCleanupDialog:true,CorpusRevisionHistory:true,CorpusBoundarySliceDialog:true,CorpusBoundaryAdjudication:true,CorpusSourceSummary:true};

describe("Corpus Builder focus review interactions",()=>{
  it("focuses the close action on open and exposes modal semantics",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{attachTo:document.body,props:{record,canPreviousRecord:true,canNextRecord:true},global:{stubs}});
    await nextTick();
    expect(wrapper.get('[role="dialog"]').attributes("aria-modal")).toBe("true");
    expect(document.activeElement).toBe(buttonByText(wrapper,"Close").element);
    wrapper.unmount();
  });

  it("supports Escape and record-navigation keyboard shortcuts",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{attachTo:document.body,props:{record,canPreviousRecord:true,canNextRecord:true},global:{stubs}});
    const dialog=wrapper.get(".focus-review");
    await dialog.trigger("keydown",{key:"Escape"});
    expect(wrapper.emitted("close")).toHaveLength(1);
    await dialog.trigger("keydown",{key:"ArrowLeft",altKey:true});
    expect(wrapper.emitted("previousRecord")).toHaveLength(1);
    await dialog.trigger("keydown",{key:"ArrowRight",altKey:true});
    expect(wrapper.emitted("nextRecord")).toHaveLength(1);
    wrapper.unmount();
  });

  it("implements arrow-key tab navigation across metadata, evidence, and source",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{attachTo:document.body,props:{record},global:{stubs}});
    expect(wrapper.get("#focus-tab-metadata").attributes("aria-selected")).toBe("true");
    await wrapper.get(".tabs").trigger("keydown",{key:"ArrowRight"});
    await nextTick();
    expect(wrapper.get("#focus-tab-evidence").attributes("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(wrapper.get("#focus-tab-evidence").element);
    await wrapper.get(".tabs").trigger("keydown",{key:"End"});
    await nextTick();
    expect(wrapper.get("#focus-tab-source").attributes("aria-selected")).toBe("true");
    wrapper.unmount();
  });

  it("saves reviewed text with Ctrl/Cmd+S without mutating immutable source text",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{attachTo:document.body,props:{record},global:{stubs}});
    await buttonByText(wrapper,"Edit text").trigger("click");
    const editor=wrapper.get("textarea.focus-text-editor");
    expect((editor.element as HTMLTextAreaElement).value).toBe(record.text);
    await editor.setValue("A corrected reviewed passage.");
    await wrapper.get(".focus-review").trigger("keydown",{key:"s",ctrlKey:true});
    const event=lastEmission(wrapper,"saveText");
    expect(event?.[0]).toBe("A corrected reviewed passage.");
    expect(event?.[1]).toBe(false);
    expect(record.text).toBe("A representative passage under review.");
    wrapper.unmount();
  });

  it("binds selected review text to the nearest source block and opens Evidence",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{
      props:{
        record,
        sourceBlocks:[
          {block_id:"p24-b1",page:24,bbox:[0,0,1,1],type:"paragraph",text:"Derrida frames the question.",extraction_method:"native",confidence:1},
          {block_id:"p24-b2",page:24,bbox:[0,0,1,1],type:"paragraph",text:"For Levinas, responsibility precedes freedom.",extraction_method:"native",confidence:1},
        ],
      },
      global:{
        stubs:{
          ...stubs,
          CorpusMetadataResolutionPanel:{
            template:'<button data-selection-evidence @click="$emit(\'selectionEvidence\',\'position_holder\',\'Levinas responsibility precedes freedom\')">Bind evidence</button>',
          },
        },
      },
    });

    await wrapper.get("[data-selection-evidence]").trigger("click");

    expect(lastEmission(wrapper,"selectEvidence")).toEqual(["position_holder"]);
    expect(lastEmission(wrapper,"assignEvidence")).toEqual(["position_holder","p24-b2"]);
    expect(wrapper.get("#focus-tab-evidence").attributes("aria-selected")).toBe("true");
    wrapper.unmount();
  });

  it("disables acceptance when the parent marks the record unsafe to accept",()=>{
    const wrapper=mount(CorpusRecordFocusReview,{props:{record,canAccept:false},global:{stubs}});
    const accept=buttonByText(wrapper,"Accept");
    expect(accept.attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("emits front-of-queue requeue and disables the action while busy",async()=>{
    const wrapper=mount(CorpusRecordFocusReview,{props:{record},global:{stubs}});
    const requeue=buttonByText(wrapper,"Send back through current LLM run");
    await requeue.trigger("click");
    expect(wrapper.emitted("requeueMetadata")).toHaveLength(1);
    await wrapper.setProps({busy:true});
    expect(buttonByText(wrapper,"Send back through current LLM run").attributes("disabled")).toBeDefined();
    wrapper.unmount();
  });

  it("exposes noise status and linked queue context", async () => {
    const wrapper=mount(CorpusRecordFocusReview,{
      props:{
        record:{...record,text_noise:{score:52,unusable:true}},
        justProcessedRecordId:"record-00013",
        nextRecordId:"record-00015",
      },
      global:{stubs},
    });
    expect(wrapper.get(".record-noise-summary").text()).toContain("52% noise");
    const links=wrapper.findAll(".queue-context .text-link");
    expect(links).toHaveLength(3);
    await links[0].trigger("click");
    expect(lastEmission(wrapper,"navigateRecord")[0]).toBe("record-00013");
    await links[2].trigger("click");
    expect(lastEmission(wrapper,"navigateRecord")[0]).toBe("record-00015");
    wrapper.unmount();
  });
});
