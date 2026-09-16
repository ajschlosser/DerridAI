import type { Meta, StoryObj } from "@storybook/vue3-vite";
import ResponseFaqList from "./ResponseFaqList.vue";

const records = [
  {
    record_id:"cache-1",
    question:"What is responsibility after deconstruction?",
    text:"Derrida treats responsibility as irreducible to the application of a rule because a responsible decision must answer to singularity while remaining exposed to the undecidable.",
    provider:"Ollama",
    model:"qwen3:14b",
    created_at:"2026-09-14T18:30:00Z",
    evidence_count:8,
    grade:{overall:9},
  },
  {
    record_id:"cache-2",
    question:"How does hospitality complicate sovereignty?",
    text:"The tension between unconditional hospitality and the conditional laws of hospitality prevents sovereignty from becoming a self-contained power over the threshold.",
    provider:"OpenAI-compatible",
    model:"gpt-oss:20b",
    created_at:"2026-09-14T16:10:00Z",
    evidence_count:11,
  },
  {
    record_id:"cache-3",
    question:"Trace the role of undecidability in decision.",
    text:"Undecidability is not an obstacle that precedes decision and then disappears; it names the structure within which a decision can become responsible rather than programmed.",
    provider:"Ollama",
    model:"phi4:14b",
    created_at:"2026-09-13T22:15:00Z",
    evidence_count:6,
    grade:{overall:8},
  },
];

const meta:Meta<typeof ResponseFaqList>={
  title:"Research/Response FAQ Library",
  component:ResponseFaqList,
  parameters:{layout:"padded"},
  args:{selectedId:"cache-1",records},
};
export default meta;
type Story=StoryObj<typeof ResponseFaqList>;

export const Default:Story={};
export const NoSelection:Story={args:{selectedId:"",records}};
export const LongScholarlyQuestions:Story={args:{selectedId:"cache-long",records:[
  {
    record_id:"cache-long",
    question:"How does Derrida distinguish the unconditional structure of hospitality from the conditional laws that make hospitality politically and juridically practicable, and what follows from this distinction for sovereignty?",
    text:"The distinction does not permit a simple choice between ideality and law. Instead, each side remains exposed to the other, producing an aporetic demand on institutions and decisions.",
    provider:"Ollama",
    model:"qwen3:14b",
    created_at:"2026-09-14T19:42:00Z",
    evidence_count:14,
    grade:{overall:9.4},
  },
  ...records,
]}};
export const CompactViewport:Story={
  parameters:{viewport:{defaultViewport:"mobile2"}},
  args:{selectedId:"cache-2",records},
};
