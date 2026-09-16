import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusExecutionSettings from "./CorpusExecutionSettings.vue";
const meta={title:"PDF Corpus Builder/Execution Settings",component:CorpusExecutionSettings,args:{generation:{num_ctx:32768,temperature:0,top_k:0,top_p:1,repeat_penalty:1.1,think:"false"},stageLimits:{manifest_num_predict:1800,segmentation_num_predict:1200,reconciliation_num_predict:1000,discourse_num_predict:1600,quotation_num_predict:1500,indexing_num_predict:1200,segmentation_window_tokens:5000},maxConcurrentRequests:2,useProfileDefaults:false}} satisfies Meta<typeof CorpusExecutionSettings>;
export default meta;type Story=StoryObj<typeof meta>;
export const Overrides:Story={};
export const ProfileDefaults:Story={args:{useProfileDefaults:true}};
export const UnsafeContext:Story={args:{generation:{num_ctx:4096},stageLimits:{segmentation_window_tokens:5000,segmentation_num_predict:1200}}};
