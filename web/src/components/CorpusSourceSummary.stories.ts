import type {Meta,StoryObj} from '@storybook/vue3-vite';
import CorpusSourceSummary from './CorpusSourceSummary.vue';
const blocks=[{block_id:'p00001-b0001',page:1,bbox:[60,80,540,220],type:'paragraph',text:'A source block used to verify the record.',extraction_method:'native',confidence:1}];
const meta={title:'Corpus Builder/Source/Compact Source Summary',component:CorpusSourceSummary,args:{pdfUrl:'',page:1,pageCount:75,pageWidth:612,pageHeight:792,blocks,canPrevious:false,canNext:true}} satisfies Meta<typeof CorpusSourceSummary>;
export default meta;type Story=StoryObj<typeof meta>;
export const NarrowInspector:Story={parameters:{viewport:{defaultViewport:'mobile2'}}};
export const SourceUnavailable:Story={args:{pdfUrl:'',blocks:[]}};
