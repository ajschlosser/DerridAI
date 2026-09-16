import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordEditSheet from "./RecordEditSheet.vue";

const record={
  work:"Adieu to Emmanuel Levinas",
  document_author:"Jacques Derrida",
  publication_year:1999,
  publisher:"Stanford University Press",
  translator:"Pascale-Anne Brault and Michael Naas",
  page_start:20,
  page_end:21,
  speaker:"Derrida",
  position_holder:"Levinas",
  stance:"qualified endorsement",
  discourse_role:"analysis",
  concepts:["responsibility","the Other"],
  topics:["ethics","death"],
  needs_review:false,
  text:"Responsibility is exposed in the face of the other."
};
const meta={
  title:"Record Workspace/Edit Sheet",
  component:RecordEditSheet,
  args:{open:true,record}
} satisfies Meta<typeof RecordEditSheet>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Default:Story={};
