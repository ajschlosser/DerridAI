import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchSettingsDrawer from "./ResearchSettingsDrawer.vue";

const baseConfig={
  source_collection:"derrida_primary",locales:["en","fr"],search_types:["mmr","similarity"],k:64,fetch_k:500,lambda_mult:.7,rrf_k:60,
  rerank_top_n:24,reranker:"cross_encoder",cross_encoder_model:"cross-encoder/ms-marco-MiniLM-L-6-v2",query_decomposition:true,
  query_decomposition_num_predict:640,response_language:"auto",evidence_record_char_limit:12000,evidence_total_char_limit:100000,
  bind_citations:true,include_works_cited:true,auto_grade:false,auto_grade_provider_profile_id:"phi4",provider_profile_id:"phi4",skip_retrieval:false,prompt:"",instructions:"",
};
const meta:Meta<typeof ResearchSettingsDrawer>={
  title:"Research/Expert Settings",
  component:ResearchSettingsDrawer,
  parameters:{layout:"fullscreen"},
  args:{
    config:baseConfig,
    profiles:[{id:"phi4",name:"Phi-4 scholarly",type:"ollama",model:"phi4:14b"}],
    selectedProfileId:"phi4",
    generation:{num_ctx:32768,num_predict:4096,temperature:0,top_p:1,top_k:0,repeat_penalty:1.1,extra_options:{}},
    model:"phi4:14b",
    models:["phi4:14b","qwen3:14b"],
    researcher:false,
  },
  render:(args)=>({
    components:{ResearchSettingsDrawer},
    setup(){return {args}},
    template:`<div style="padding:32px"><ResearchSettingsDrawer v-bind="args" ref="drawer"/><button class="btn primary" type="button" @click="$refs.drawer.open()">Open expert settings</button></div>`,
  }),
};
export default meta;
type Story=StoryObj<typeof ResearchSettingsDrawer>;
export const Administrator:Story={};
export const ResearcherLockedGeneration:Story={args:{researcher:true}};
