import type { Meta, StoryObj } from '@storybook/vue3-vite';
import CorpusSourceIssuePanel from './CorpusSourceIssuePanel.vue';
const meta:Meta<typeof CorpusSourceIssuePanel>={title:'Corpus Builder/Review/Source Issue Panel',component:CorpusSourceIssuePanel};export default meta;type Story=StoryObj<typeof CorpusSourceIssuePanel>;
export const Fragmented:Story={args:{interactive:true,issues:[{code:'fragmented_glyph_layout',severity:'blocking',pages:[1,2],micro_line_ratio:.63,message:'Extracted text appears fragmented into individual glyphs or punctuation lines.'}]}};
export const FrenchLength:Story={args:{interactive:true,issues:[{code:'source_quality_blocking',severity:'blocking',pages:[14],message:'La couche de texte du PDF contient des caractères de remplacement ou de contrôle et doit être vérifiée avant l’acceptation savante.'}]}};
