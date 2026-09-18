import type { Meta,StoryObj } from "@storybook/vue3-vite";
import CorpusWorkflowStepper from "./CorpusWorkflowStepper.vue";
const meta={title:"Corpus Builder/Workflow/Lifecycle Stepper",component:CorpusWorkflowStepper,args:{hasAsset:true,hasManifest:true,stage:"enriching",status:"running",recordCount:84,acceptedCount:0,blockerCount:0,canPublish:false}} satisfies Meta<typeof CorpusWorkflowStepper>;
export default meta;type Story=StoryObj<typeof meta>;
export const CollaborativeReview:Story={};
export const ResolveExceptions:Story={args:{stage:"ready",status:"ready",blockerCount:3}};
export const ReadyToPublish:Story={args:{stage:"ready",status:"ready",blockerCount:0,canPublish:true}};
export const Published:Story={args:{stage:"published",status:"published",published:true,canPublish:true}};
export const FrenchLengthStress:Story={parameters:{locale:"fr-CA"},args:{stage:"ready",status:"ready",blockerCount:2}};
