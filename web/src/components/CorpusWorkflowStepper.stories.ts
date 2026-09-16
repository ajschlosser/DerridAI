import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
const meta={title:"PDF Corpus Builder/Workflow Stepper",component:CorpusWorkflowStepper,args:{hasAsset:true,hasManifest:true,stage:"enriching",status:"running"}} satisfies Meta<typeof CorpusWorkflowStepper>;
export default meta;
type Story=StoryObj<typeof meta>;
export const DocumentReview:Story={args:{stage:"document_review",status:"awaiting_manifest_review",hasAsset:true,hasManifest:true}};
export const Enriching:Story={};
export const SegmentationBlocked:Story={args:{stage:"segmentation_review",status:"blocked"}};
export const Review:Story={args:{stage:"review",status:"awaiting_review"}};
