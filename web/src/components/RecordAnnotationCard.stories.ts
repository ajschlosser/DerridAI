import type { Meta, StoryObj } from "@storybook/vue3";
import RecordAnnotationCard from "./RecordAnnotationCard.vue";
const meta: Meta<typeof RecordAnnotationCard>={title:"Records/Record Annotation Card",component:RecordAnnotationCard,args:{field:"Text",quote:"Justice, if such a thing exists, outside or beyond law...",note:"Useful formulation for the law/justice distinction.",tags:["justice","law"],author:"Researcher",timestamp:"Sep 14, 2026, 10:42 AM",removable:true}};export default meta;type Story=StoryObj<typeof RecordAnnotationCard>;export const Default:Story={};
