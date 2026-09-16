import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildProgress from "./CorpusBuildProgress.vue";

const meta={title:"PDF Corpus Builder/Build Progress",component:CorpusBuildProgress,args:{status:"running",stage:"enriching",progress:.63,recordCount:187,reviewCount:12,acceptedCount:0,warnings:[],validation:null,llmMetrics:{calls:81,retries:3,structured_output_failures:3,escalations:0}}} satisfies Meta<typeof CorpusBuildProgress>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Running:Story={};
export const NeedsReview:Story={args:{status:"awaiting_review",stage:"review",progress:1,recordCount:287,reviewCount:17,acceptedCount:270,validation:{valid:false,coverage:1,metadata_evidence_errors:[{field:"position_holder"}]},warnings:["One metadata record requires manual review."]}};
export const RecoverableFailure:Story={args:{status:"failed",stage:"failed",progress:.48,recordCount:84,reviewCount:0,acceptedCount:0,error:"Provider unavailable. Resume from the last checkpoint after restoring the provider.",warnings:["Completed segmentation and metadata checkpoints were preserved."]}};
