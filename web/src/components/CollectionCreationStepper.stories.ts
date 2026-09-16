import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CollectionCreationStepper from "./CollectionCreationStepper.vue";
const meta={title:"Vector Stores/Collection Creation Stepper",component:CollectionCreationStepper,args:{steps:["Collection","Embeddings","Sync works"],activeStep:1}} satisfies Meta<typeof CollectionCreationStepper>;export default meta;type Story=StoryObj<typeof meta>;export const Embeddings:Story={};export const SyncWorks:Story={args:{activeStep:2}};
