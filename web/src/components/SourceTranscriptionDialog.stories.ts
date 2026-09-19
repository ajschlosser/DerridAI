import type {Meta,StoryObj} from '@storybook/vue3';
import SourceTranscriptionDialog from './SourceTranscriptionDialog.vue';
const meta={title:'Corpus Builder/Source/Transcription Workspace',component:SourceTranscriptionDialog,args:{open:true,pdfUrl:'/sample.pdf',page:13,pageCount:49,printedPage:1,text:'Reviewed record text.',blocks:[{block_id:'p00013-b0001',page:13,bbox:[40,80,500,260],type:'paragraph',text:'Extracted source text.',extraction_method:'native',confidence:.99}] as any}} satisfies Meta<typeof SourceTranscriptionDialog>;
export default meta; type Story=StoryObj<typeof meta>; export const Default:Story={};
