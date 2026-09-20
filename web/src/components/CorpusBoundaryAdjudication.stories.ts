import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusBoundaryAdjudication from './CorpusBoundaryAdjudication.vue';

const meta: Meta<typeof CorpusBoundaryAdjudication> = {title:'Corpus Builder/Boundary Adjudication',component:CorpusBoundaryAdjudication};
export default meta;
type Story=StoryObj<typeof CorpusBoundaryAdjudication>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
export const RecommendedMove:Story={args:{record:{record_id:'r-12',text:'Example',text_length:7,source_block_ids:['b12'],source_spans:[],boundary_llm_before:{decision:'keep',confidence:.91,reason:'The prior seam closes a complete argumentative unit.'},boundary_llm_after:{decision:'move_later',confidence:.82,reason:'The next paragraph completes the same quotation frame.',suggested_after_block_id:'b14'}} as any,canPrevious:true,canNext:true,busy:false}};
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- SA-16: intentionally sparse Storybook fixture exercises partial/loading data without fabricating unrelated fields.
export const NotYetChecked:Story={args:{record:{record_id:'r-1',text:'Example',text_length:7,source_block_ids:['b1'],source_spans:[]} as any,canPrevious:false,canNext:true,busy:false}};
