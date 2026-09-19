import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusMetadataFieldEditor from './CorpusMetadataFieldEditor.vue';
const meta={title:'Corpus Builder/Review/Metadata Field',component:CorpusMetadataFieldEditor,args:{field:'region_type',value:'front_matter',options:['front_matter','main_text','back_matter'],status:{status:'unresolved',method:'llm',confidence:.58,reason:'The opening pages appear to be publishing front matter.'},constraint:null}} satisfies Meta<typeof CorpusMetadataFieldEditor>;
export default meta; type Story=StoryObj<typeof meta>;
export const LlmSuggestion:Story={};
export const DeterministicConstraint:Story={args:{field:'primary_text',value:false,boolean:true,status:{status:'deterministic',method:'region_type_consistency',confidence:1},constraint:{value:false,reason:'Front matter cannot be primary text.'}}};
