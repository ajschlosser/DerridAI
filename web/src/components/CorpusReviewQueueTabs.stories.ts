import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewQueueTabs from "./CorpusReviewQueueTabs.vue";
const meta={title:"Corpus Builder/Review Queue Tabs",component:CorpusReviewQueueTabs,args:{modelValue:"pending",total:63,pending:12,attention:3,metadata:5,sourceProblems:2,accepted:47,rejected:1}} satisfies Meta<typeof CorpusReviewQueueTabs>;
export default meta; type Story=StoryObj<typeof meta>;
export const Pending:Story={};
export const AllReviewed:Story={args:{modelValue:"accepted",pending:0,attention:0,metadata:0,sourceProblems:0,accepted:63,rejected:0}};

export const SourceProblems:Story={args:{modelValue:"source",pending:10,attention:0,metadata:0,sourceProblems:4,accepted:49,rejected:0}};
