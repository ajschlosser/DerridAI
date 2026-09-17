import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusMetadataResolutionPanel from "./CorpusMetadataResolutionPanel.vue";
const record:any={record_id:"record-00018",record_revision:3,text:"A passage of primary text.",source_block_ids:["p032-b001"],pdf_pages:[32],page_start:32,page_end:32,needs_review:false,accepted:true,review_disposition:"accepted",metadata_complete:false,metadata_incomplete_fields:["region_type","discourse_role"],metadata_field_status:{region_type:{status:"unresolved",method:"llm",reason:"Deterministic and model classifications disagreed.",confidence:.62},discourse_role:{status:"unresolved",method:"llm",reason:"Available source evidence is ambiguous.",confidence:.58}}};
const meta={title:"Corpus Builder/Metadata Resolution",component:CorpusMetadataResolutionPanel,args:{record,regionTypes:["main_text","front_matter","back_matter","footnote"],discourseRoles:["assertion","analysis","quotation","reported_position","critique","transition"]}} satisfies Meta<typeof CorpusMetadataResolutionPanel>;
export default meta; type Story=StoryObj<typeof meta>;
export const AmbiguousFields:Story={};
export const Resolved:Story={args:{record:{...record,metadata_complete:true,metadata_incomplete_fields:[],metadata_field_status:{region_type:{status:"human_confirmed",method:"human"},discourse_role:{status:"human_confirmed",method:"human"}}}}};
