import type {Meta,StoryObj} from '@storybook/vue3-vite';
import CorpusBuildHistoryMenu from './CorpusBuildHistoryMenu.vue';
const builds:any[]=[{build_id:'b1',source_filename:'On Cosmopolitanism and Forgiveness.pdf',status:'running',stage:'enriching',progress:.62,record_count:31,created_at:new Date().toISOString()},{build_id:'b2',source_filename:'Rogues.pdf',status:'ready',stage:'ready',progress:1,record_count:82,created_at:new Date().toISOString()}];
const meta={title:'Corpus Builder/Workflow/Build History Menu',component:CorpusBuildHistoryMenu,args:{builds,total:2,selectedBuildId:'b1'}} satisfies Meta<typeof CorpusBuildHistoryMenu>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Default:Story={};
