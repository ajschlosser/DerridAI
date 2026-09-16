import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResponseFaqSelectionBar from "./ResponseFaqSelectionBar.vue";

const record={
  record_id:"cache-1",
  question:"How does Derrida distinguish unconditional hospitality from the conditional laws of hospitality?",
  provider:"Ollama",
  model:"qwen3:14b",
  created_at:"2026-09-14T18:30:00Z",
  evidence_count:8,
};
const meta={title:"Research/Response Library/Current Response",component:ResponseFaqSelectionBar,args:{record,evidenceCount:8,grade:9.2}} satisfies Meta<typeof ResponseFaqSelectionBar>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const LongQuestion:Story={args:{record:{...record,question:"How does Derrida distinguish the unconditional structure of hospitality from the conditional laws that make hospitality politically and juridically practicable, and what follows from that distinction for the sovereignty of the host?"},evidenceCount:14,grade:null}};
