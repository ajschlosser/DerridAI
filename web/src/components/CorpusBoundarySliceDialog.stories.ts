import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusBoundarySliceDialog from './CorpusBoundarySliceDialog.vue';
const text='This sentence belongs to the previous record and was cut at the wrong boundary. This sentence begins the actual current record and should remain here.';
const meta={title:'Corpus Builder/Review/Boundary Slice Dialog',component:CorpusBoundarySliceDialog,args:{text,canPrevious:true,canNext:true}} satisfies Meta<typeof CorpusBoundarySliceDialog>;
export default meta;type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const NoPrevious:Story={args:{canPrevious:false}};
