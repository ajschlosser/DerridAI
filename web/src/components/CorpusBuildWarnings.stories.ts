// Copyright 2026 Aaron John Schlosser, PhD.
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusBuildWarnings from "./CorpusBuildWarnings.vue";
const warnings=Array.from({length:100},(_,i)=>`record-${i}: work_profile metadata failed (structured_output_invalid); review required.`);
const meta={title:"Corpus Builder/Status/Build Warnings",component:CorpusBuildWarnings,args:{warnings}} satisfies Meta<typeof CorpusBuildWarnings>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Repeated:Story={};
export const Mixed:Story={args:{warnings:[...warnings.slice(0,3),"Source coverage requires inspection.","Provider unavailable."]}};
export const Empty:Story={args:{warnings:[]}};
export const Many:Story={args:{warnings:Array.from({length:1000},(_,i)=>warnings[i%100])}};

export const CurrentRecords:Story={args:{warnings:warnings.slice(0,3),issueSummary:{issues:[{record_id:'record-1',field:'stance'},{record_id:'record-2',field:'target'}]}}};
export const ReviewLocked:Story={args:{...CurrentRecords.args,disabled:true}};
