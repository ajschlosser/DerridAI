// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { CorpusBuild } from "../api/pdfCorpus";
import CorpusBuildOverview from "./CorpusBuildOverview.vue";
const build:CorpusBuild={build_id:"b1",asset_id:"a1",source_filename:"La Prisonnière.html",source_sha256:"sha",status:"running",stage:"enriching",progress:.85,created_at:"",record_count:370,accepted_count:0,rejected_count:0,needs_review_count:251,profile_id:"test",review_queue_counts:{ready:18,preparing:101,issues:251},metadata_tasks_total:1110,metadata_tasks_completed:900,metadata_tasks_failed:70,metadata_tasks_skipped:3,metadata_tasks_running:0,metadata_tasks_queued:137};
const meta={title:"Corpus Builder/Workflow/Build Overview",component:CorpusBuildOverview,args:{build,locked:false}} satisfies Meta<typeof CorpusBuildOverview>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Running:Story={};
export const NoReady:Story={args:{build:{...build,review_queue_counts:{ready:0,preparing:119,issues:251}}}};
export const CountsUnavailable:Story={args:{build:{...build,review_queue_counts:undefined}}};
export const Locked:Story={args:{locked:true,build:{...build,stage:"constructing_records"}}};
export const Interrupted:Story={args:{build:{...build,status:"interrupted"}}};
