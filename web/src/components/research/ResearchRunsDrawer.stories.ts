import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResearchRunsDrawer from "./ResearchRunsDrawer.vue";

const meta:Meta<typeof ResearchRunsDrawer>={
  title:"Research/Runs Drawer",
  component:ResearchRunsDrawer,
  parameters:{layout:"fullscreen"},
  args:{
    canManage:true,
    selectedJobId:"run-2",
    selectedJob:{id:"run-2",status:"completed",prompt:"How are ethics and mortality linked?",provider:"ollama",model:"phi4:14b",source_collection:"derrida_primary",result:{stages:[{name:"query_decomposition",seconds:.42},{name:"retrieval",seconds:.71},{name:"rerank",seconds:1.18},{name:"generation",seconds:16.43}],query_metadata:{canonical_work:"Adieu to Emmanuel Levinas"},retrieval:{candidates:64,reranked:24}}},
    jobs:[
      {id:"run-3",status:"running",prompt:"How does hospitality complicate sovereignty?",source_collection:"derrida_primary",model:"phi4:14b",stage:"rerank",stage_detail:"Reranking candidate passages",created_at:"2026-09-14T22:10:00Z"},
      {id:"run-2",status:"completed",prompt:"How are ethics and mortality linked?",source_collection:"derrida_primary",model:"phi4:14b",finished_at:"2026-09-14T21:42:00Z"},
      {id:"run-1",status:"failed",prompt:"Compare forgiveness and the gift.",source_collection:"derrida_primary",model:"qwen3:14b",finished_at:"2026-09-14T20:30:00Z",fatal_error:"Provider unavailable"},
    ],
  },
  render:(args)=>({
    components:{ResearchRunsDrawer},
    setup(){return {args}},
    template:`<div style="padding:32px"><ResearchRunsDrawer v-bind="args" ref="drawer"/><button class="btn primary" type="button" @click="$refs.drawer.open()">Open Research runs</button></div>`,
  }),
};
export default meta;
type Story=StoryObj<typeof ResearchRunsDrawer>;
export const Default:Story={};
