import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusReviewCompletionCard from "./CorpusReviewCompletionCard.vue";
const build:any={build_id:"build-aardvark",asset_id:"asset",source_filename:"book.pdf",source_sha256:"sha",status:"awaiting_metadata",stage:"metadata_review",progress:.96,created_at:"",record_count:63,needs_review_count:0,accepted_count:63,rejected_count:0,profile_id:"derrida-scholarly-v8",metadata_completed:60,metadata_total:63,validation:{valid:true,coverage:1}};
const meta={title:"Corpus Builder/Review Completion",component:CorpusReviewCompletionCard,args:{build}} satisfies Meta<typeof CorpusReviewCompletionCard>;
export default meta; type Story=StoryObj<typeof meta>;
export const MetadataBlocked:Story={};
export const Ready:Story={args:{build:{...build,status:"ready",stage:"ready",progress:.98,metadata_completed:63}}};
export const Published:Story={args:{build:{...build,status:"ready",stage:"ready",progress:1,metadata_completed:63,publication:{publication_id:"pub-1",filename:"book.jsonl",sha256:"sha",record_count:63,created_at:"2026-09-17T20:00:00Z"}}}};
