import type { Meta, StoryObj } from "@storybook/vue3";
import CorpusBuildLifecycleCard from "./CorpusBuildLifecycleCard.vue";
const build:any={build_id:"build-1",asset_id:"asset",source_filename:"book.pdf",source_sha256:"sha",status:"awaiting_review",stage:"review",progress:.94,created_at:"",record_count:63,needs_review_count:12,accepted_count:49,rejected_count:2,profile_id:"derrida-scholarly-v9",metadata_completed:58,metadata_total:63,pipeline_state:{extraction:{state:"complete"},construction:{state:"complete"},enrichment:{state:"complete"},review:{state:"active"},validation:{state:"waiting"},publication:{state:"waiting"}},publication_readiness:{next_action:"continue_review"}};
const meta={title:"Corpus Builder/Build Lifecycle Card",component:CorpusBuildLifecycleCard,args:{build}} satisfies Meta<typeof CorpusBuildLifecycleCard>;
export default meta; type Story=StoryObj<typeof meta>;
export const Reviewing:Story={};
export const Ready:Story={args:{build:{...build,status:"ready",stage:"ready",progress:.98,needs_review_count:0,accepted_count:63,rejected_count:0,metadata_completed:63}}};
export const Published:Story={args:{build:{...build,status:"ready",stage:"ready",progress:1,needs_review_count:0,accepted_count:63,rejected_count:0,metadata_completed:63,publication_status:"published",publication:{publication_id:"p1",filename:"book.jsonl",sha256:"abc",record_count:63,created_at:""}}}};
