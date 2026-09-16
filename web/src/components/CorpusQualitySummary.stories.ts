import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
const meta={title:"PDF Corpus Builder/Quality Summary",component:CorpusQualitySummary,args:{build:{build_id:"demo",boundary_count:286,record_count:287,metadata_completed:270,metadata_total:287,needs_review_count:17,segmentation_unresolved_regions:[],validation:{valid:false,coverage:1}}}} satisfies Meta<typeof CorpusQualitySummary>;
export default meta;
type Story=StoryObj<typeof meta>;
export const ReviewRequired:Story={};
export const Blocked:Story={args:{build:{build_id:"blocked",boundary_count:0,record_count:0,metadata_completed:0,metadata_total:0,needs_review_count:0,segmentation_unresolved_regions:[{kind:"pair"},{kind:"pair"}],validation:null}}};
