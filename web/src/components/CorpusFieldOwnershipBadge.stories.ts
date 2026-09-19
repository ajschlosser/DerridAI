import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusFieldOwnershipBadge from './CorpusFieldOwnershipBadge.vue';
const meta:Meta<typeof CorpusFieldOwnershipBadge>={title:'Corpus Builder/Review/Field Ownership Badge',component:CorpusFieldOwnershipBadge,args:{status:'inherited'}};export default meta;
type Story=StoryObj<typeof CorpusFieldOwnershipBadge>;
export const Inherited:Story={args:{status:'inherited'}};
export const LlmInferred:Story={args:{status:'llm_inferred'}};
export const HumanOverride:Story={args:{status:'human_override'}};
export const NeedsReview:Story={args:{status:'unresolved'}};
