import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusQualitySummary from "./CorpusQualitySummary.vue";
const base={build_id:"demo",boundary_count:91,record_count:92,metadata_completed:88,metadata_total:92,needs_review_count:4,boundary_review_count:0,record_sizing_policy:{preferred_record_chars:1750,record_length_tolerance:200,long_record_chars:3500,absolute_record_chars:6000},topology_quality:{valid:true,source_coverage:1,source_conservation_valid:true,record_count:92,median_record_chars:1788,p10_record_chars:1210,p90_record_chars:2315,max_record_chars:3420,records_over_preferred_range:13,records_over_long_limit:0},validation:{valid:false,source_valid:true,coverage:1}};
const meta={title:"Corpus Builder/Status/Quality Summary",component:CorpusQualitySummary,args:{build:base}} satisfies Meta<typeof CorpusQualitySummary>;
export default meta;
type Story=StoryObj<typeof meta>;
export const HealthyTopology:Story={};
export const LongExceptions:Story={args:{build:{...base,topology_quality:{...base.topology_quality,p90_record_chars:3180,max_record_chars:5200,records_over_preferred_range:24,records_over_long_limit:2}}}};
export const UnusableSource:Story={args:{build:{...base,trash_quality:{record_count:92,trash_record_count:80,trash_ratio:0.87,threshold:0.1,exceeds_threshold:true,unusable_page_ratio:0,median_noise:72,noise_unusable_threshold:45}}}};
