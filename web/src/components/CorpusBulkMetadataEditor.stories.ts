import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusBulkMetadataEditor from './CorpusBulkMetadataEditor.vue';
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
const meta:Meta<typeof CorpusBulkMetadataEditor>={title:'Corpus Builder/Review/Bulk Metadata Editor',component:CorpusBulkMetadataEditor,args:{selectedCount:4,totalCount:76,disabled:false,regionTypes:['front_matter','main_text','notes','back_matter'],discourseRoles:['assertion','analysis','quotation','paratext'],records:[{record_id:'r1',region_type:'main_text',speaker:'Derrida',topics:['hospitality','forgiveness']},{record_id:'r2',region_type:'front_matter',speaker:'Simon Critchley',topics:['cosmopolitanism']}] as any}};
export default meta;
type Story=StoryObj<typeof CorpusBulkMetadataEditor>;
export const Default:Story={};
export const Disabled:Story={args:{disabled:true}};
