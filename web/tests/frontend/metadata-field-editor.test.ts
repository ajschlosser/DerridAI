import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import { describe, expect, it } from "vitest";
import CorpusMetadataFieldEditor from "../../src/components/CorpusMetadataFieldEditor.vue";
import { normalizeMetadataFieldValue } from "../../src/domain/metadataFieldRegistry";

const stanceOptions=["affirm","reject","criticize","question","qualify","suspend","neutral","describe"];

describe("CorpusMetadataFieldEditor auto-population", () => {
  it("selects a confident stance proposal when the record value arrives progressively", async () => {
    const wrapper=mount(CorpusMetadataFieldEditor,{
      props:{
        field:"stance",
        value:"",
        control:"enum",
        options:stanceOptions,
        open:true,
        status:{status:"unresolved",method:"llm",confidence:.4,auto_populated:false},
      },
    });
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("");

    await wrapper.setProps({
      value:"affirm",
      status:{status:"llm_inferred",method:"llm",confidence:.91,auto_populated:true,proposed_value:"affirm",llm_checked:true},
    });
    await nextTick();
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("affirm");
    wrapper.unmount();
  });

  it("normalizes direct grammatical stance aliases so older model output still selects an enum option", async () => {
    expect(normalizeMetadataFieldValue("stance","affirmed")).toBe("affirm");
    const wrapper=mount(CorpusMetadataFieldEditor,{
      props:{
        field:"stance",
        value:"",
        control:"enum",
        options:stanceOptions,
        open:true,
        status:{status:"llm_inferred",method:"llm",confidence:.92,auto_populated:true,proposed_value:"affirmed",raw_llm_value:"affirmed"},
      },
    });
    await nextTick();
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("affirm");
    wrapper.unmount();
  });

  it("keeps reviewer-defined deterministic region selected during an LLM disagreement", async () => {
    const wrapper=mount(CorpusMetadataFieldEditor,{
      props:{
        field:"region_type",
        value:"main_text",
        control:"enum",
        options:["front_matter","main_text","back_matter"],
        open:true,
        status:{
          status:"unresolved",
          method:"deterministic+llm",
          reason_code:"deterministic_llm_disagreement",
          deterministic_value:"main_text",
          llm_value:"front_matter",
          llm_confidence:.96,
          prefilled_candidate:"deterministic",
          llm_checked:true,
        },
      },
    });
    expect((wrapper.get("select").element as HTMLSelectElement).value).toBe("main_text");
    wrapper.unmount();
  });
});
