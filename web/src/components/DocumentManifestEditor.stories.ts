import type { Meta, StoryObj } from "@storybook/vue3-vite";
import DocumentManifestEditor from "./DocumentManifestEditor.vue";
const meta:Meta<typeof DocumentManifestEditor>={title:"PDF Corpus/Document Manifest Editor",component:DocumentManifestEditor,args:{manifest:{title:"Rogues",document_author:"Jacques Derrida",translator:"Pascale-Anne Brault and Michael Naas",publication_year:2005,language:"English",original_language:"French",main_text_start_page:11,main_text_end_page:191}}};
export default meta;
type Story=StoryObj<typeof DocumentManifestEditor>;
export const Default:Story={};
export const ReadOnlyWhileBuilding:Story={args:{disabled:true}};
