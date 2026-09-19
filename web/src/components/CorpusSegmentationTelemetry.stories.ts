import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusSegmentationTelemetry from "./CorpusSegmentationTelemetry.vue";

const meta={title:"Corpus Builder/Status/Segmentation Telemetry",component:CorpusSegmentationTelemetry,args:{candidateCount:54,deterministicSplits:5,deterministicKeeps:31,llmAdjudications:12,llmBatchCalls:2,llmSplits:4,llmKeeps:8,provisionalSplits:5,sizeOptimizedSplits:5,absoluteSafetySplits:0,budgetSkipped:6,classifierFailures:0,reviewCount:0}} satisfies Meta<typeof CorpusSegmentationTelemetry>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Typical:Story={};
export const RecoverableFailures:Story={args:{classifierFailures:3,llmSplits:2,llmKeeps:10,reviewCount:0}};
export const ProvenanceHazard:Story={args:{reviewCount:1,provisionalSplits:1}};
