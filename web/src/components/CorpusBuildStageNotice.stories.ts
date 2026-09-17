import type { Meta, StoryObj } from "@storybook/vue3";
import CorpusBuildStageNotice from "./CorpusBuildStageNotice.vue";
const meta={title:"Corpus Builder/Build Stage Notice",component:CorpusBuildStageNotice,args:{stage:"semantic segmentation"}} satisfies Meta<typeof CorpusBuildStageNotice>;
export default meta; type Story=StoryObj<typeof meta>;
export const Segmenting:Story={};
export const DocumentStructure:Story={args:{stage:"document structure"}};
