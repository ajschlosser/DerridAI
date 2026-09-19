import type { Meta,StoryObj } from '@storybook/vue3-vite';
import CorpusLlmTextTouchupDialog from './CorpusLlmTextTouchupDialog.vue';
const meta={title:'Corpus Builder/Review/LLM Text Touch-up',component:CorpusLlmTextTouchupDialog,args:{open:true,profiles:[{id:'primary',name:'Local scholarly',type:'ollama',model:'gemma4:e4b'} as any],providerProfileId:'primary',recordId:'r1',sourceText:'This is a sentence\nbroken by PDF layout.  It has OCR artefacts ﬁ and odd spacing.',proposedText:'This is a sentence broken by PDF layout. It has OCR artefacts fi and odd spacing.',changes:['Joined an accidental line wrap','Normalized an OCR ligature'],warnings:[],model:'gemma4:e4b'}} satisfies Meta<typeof CorpusLlmTextTouchupDialog>;
export default meta;type Story=StoryObj<typeof meta>;
export const Proposal:Story={};
export const WithWarning:Story={args:{warnings:['A possible authorial spelling was left unchanged.']}};
export const FrenchLengthStress:Story={parameters:{locale:'fr-CA'}};
