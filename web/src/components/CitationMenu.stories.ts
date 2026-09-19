import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CitationMenu from "./CitationMenu.vue";

const meta={title:"Foundations/Actions/Citation Menu",component:CitationMenu,args:{compact:false}} satisfies Meta<typeof CitationMenu>;
export default meta;
type Story=StoryObj<typeof meta>;
export const Default:Story={};
export const Compact:Story={args:{compact:true}};
