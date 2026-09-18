import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchComposer from "./ResearchComposer.vue";

const meta:Meta<typeof ResearchComposer>={
  title:"Research/Composer",
  component:ResearchComposer,
  parameters:{layout:"padded"},
  args:{
    prompt:"How does Derrida distinguish responsibility for the mortal other from Heideggerian being-toward-death?",
    instructions:"Distinguish Derrida's own claims from positions attributed to Levinas and Heidegger.",
    sourceCollection:"derrida_primary",
    providerProfileId:"phi4",
    responseLanguage:"auto",
    preset:"balanced",
    evidenceCount:4,
    stores:[{name:"derrida_primary",count:12844,collection_role:"primary",embedding_model:"bge-m3:latest"}],
    profiles:[{id:"phi4",name:"Phi-4 scholarly",type:"ollama",model:"phi4:14b"},{id:"qwen",name:"Qwen fast",type:"ollama",model:"qwen3:8b"}],
    history:[{id:"1",prompt:"What is the relation between hospitality and sovereignty?",timestamp:"2026-09-14T20:11:00Z"}],
    canRun:true,
    canManageRuns:true,
  },
};
export default meta;
type Story=StoryObj<typeof ResearchComposer>;
export const Default:Story={};
export const Empty:Story={args:{prompt:"",instructions:"",evidenceCount:0}};
