import type { Meta, StoryObj } from '@storybook/vue3-vite';
import DocumentManifestDialog from './DocumentManifestDialog.vue';

const manifest={title:'On Cosmopolitanism and Forgiveness',document_author:'Jacques Derrida',translator:'Mark Dooley; Michael Hughes',publisher:'Routledge',publication_year:2001,document_language:'en',original_language:'fr'};
const meta:Meta<typeof DocumentManifestDialog>={title:'Corpus Builder/Review/Document Metadata Dialog',component:DocumentManifestDialog,args:{manifest}};
export default meta;
type Story=StoryObj<typeof DocumentManifestDialog>;
export const Default:Story={};
export const Disabled:Story={args:{disabled:true}};
