import type { Meta,StoryObj } from '@storybook/vue3-vite';
import CorpusJsonlPreviewDialog from './CorpusJsonlPreviewDialog.vue';
const jsonl='{"record_id":"derrida-test-00012","text":"A reviewed passage.","region_type":"main_text","primary_text":true,"discourse_role":"analysis"}';
const meta={title:'Corpus Builder/Review/JSONL Preview',component:CorpusJsonlPreviewDialog,args:{open:true,jsonl,validationErrors:[],unresolvedFields:[],wouldPublish:true}} satisfies Meta<typeof CorpusJsonlPreviewDialog>;
export default meta;type Story=StoryObj<typeof meta>;
export const Ready:Story={};
export const Blocked:Story={args:{wouldPublish:false,validationErrors:['reported_position requires a position_holder'],unresolvedFields:['position_holder']}};
export const FrenchLengthStress:Story={parameters:{locale:'fr-CA'}};
