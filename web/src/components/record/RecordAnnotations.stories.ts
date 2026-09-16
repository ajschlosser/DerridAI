import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordAnnotations from "./RecordAnnotations.vue";
const meta={title:"Record Workspace/Annotations",component:RecordAnnotations,args:{canAdd:true,annotations:[{id:"1",field:"text",quote:"I am responsible for the other insofar as he is mortal",note:"Compare this with the discussion of substitution.",tags:["Levinas","responsibility"],author:"aaron",created_at:"2026-09-14T20:30:00Z",removable:true},{id:"2",field:"stance",quote:"qualified endorsement",note:"The attribution matters here.",tags:["provenance"],author:"researcher",created_at:"2026-09-13T16:15:00Z",removable:false}]}} satisfies Meta<typeof RecordAnnotations>;
export default meta;type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const Empty:Story={args:{annotations:[]}};
