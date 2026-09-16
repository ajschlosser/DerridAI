import type { Meta, StoryObj } from "@storybook/vue3-vite";
import RecordHistoryTimeline from "./RecordHistoryTimeline.vue";
const meta={title:"Record Workspace/History Timeline",component:RecordHistoryTimeline,args:{total:17,canOpen:true,items:[{id:"1",field_name:"speaker",timestamp:"2026-09-14T20:00:00Z",source:"manual",initiated_by:"admin"},{id:"2",field_name:"text",timestamp:"2026-09-14T19:30:00Z",source:"ocr_cleanup",initiated_by:"admin"},{id:"3",field_name:"concepts",timestamp:"2026-09-14T18:10:00Z",source:"record_workspace",initiated_by:"admin"}]}} satisfies Meta<typeof RecordHistoryTimeline>;
export default meta;type Story=StoryObj<typeof meta>;
export const Default:Story={};
