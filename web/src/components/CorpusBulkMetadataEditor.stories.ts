import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusBulkMetadataEditor from './CorpusBulkMetadataEditor.vue';
const meta:Meta<typeof CorpusBulkMetadataEditor>={title:'Corpus Builder/Review/Bulk Metadata Editor',component:CorpusBulkMetadataEditor,args:{selectedCount:4,totalCount:76,disabled:false}};
export default meta;
type Story=StoryObj<typeof CorpusBulkMetadataEditor>;
export const Default:Story={};
export const Disabled:Story={args:{disabled:true}};
