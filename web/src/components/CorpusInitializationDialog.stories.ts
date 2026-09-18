import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusInitializationDialog from './CorpusInitializationDialog.vue';

const build={
  build_id:'build-demo',source_filename:'On Cosmopolitanism and Forgiveness.pdf',status:'running',stage:'segmenting',progress:.18,
  record_count:0,accepted_count:0,
} as any;
const meta:Meta<typeof CorpusInitializationDialog>={
  title:'Corpus Builder/Build/Initialization Dialog',component:CorpusInitializationDialog,
  args:{build},
};
export default meta;
type Story=StoryObj<typeof CorpusInitializationDialog>;
export const Segmenting:Story={};
export const Reconciling:Story={args:{build:{...build,stage:'reconciling',progress:.37} as any}};
