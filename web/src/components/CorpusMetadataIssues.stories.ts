import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusMetadataIssues from "./CorpusMetadataIssues.vue";
const build:any={build_id:"build-aardvark",asset_id:"asset",source_filename:"book.pdf",source_sha256:"sha",status:"awaiting_metadata",stage:"metadata_review",progress:.96,created_at:"",record_count:63,needs_review_count:0,accepted_count:63,rejected_count:0,profile_id:"derrida-scholarly-v8",provider:"ollama",model:"Qwen3.8-27B",metadata_completed:58,metadata_total:63,request:{provider_profile_id:"primary"},metadata_issue_summary:{records_incomplete:5,fields_unresolved:7,by_field:{discourse_role:3,region_type:2,primary_text:2},invalid_by_field:{},records:[{record_id:"record-00012",fields:["discourse_role"],page_start:18,page_end:19},{record_id:"record-00031",fields:["region_type","primary_text"],page_start:47,page_end:48}]}};
const meta={title:"Corpus Builder/Metadata Issues",component:CorpusMetadataIssues,args:{build}} satisfies Meta<typeof CorpusMetadataIssues>;
export default meta; type Story=StoryObj<typeof meta>;
export const NeedsAttention:Story={};
export const RetryRunning:Story={args:{busy:true}};
