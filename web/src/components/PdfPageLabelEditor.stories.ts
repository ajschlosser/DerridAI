import type { Meta, StoryObj } from "@storybook/vue3-vite";
import PdfPageLabelEditor from "./PdfPageLabelEditor.vue";
const meta:Meta<typeof PdfPageLabelEditor>={title:"PDF Corpus/Printed Page Mapping",component:PdfPageLabelEditor,args:{pages:[{pdf_page:12,printed_page_label:"xii",printed_page_label_source:"visible_folio"},{pdf_page:13,printed_page_label:"1",printed_page_label_source:"visible_folio"},{pdf_page:14,printed_page_label:"2",printed_page_label_source:"inferred_from_folios"}]}};
export default meta;
type Story=StoryObj<typeof PdfPageLabelEditor>;
export const Default:Story={};
export const Disabled:Story={args:{disabled:true}};
