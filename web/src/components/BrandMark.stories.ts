import type { Meta, StoryObj } from "@storybook/vue3-vite";
import BrandMark from "./BrandMark.vue";
const meta={title:"Foundations/Brand/Mark",component:BrandMark,args:{size:64,compact:false},parameters:{layout:"centered"}} satisfies Meta<typeof BrandMark>;export default meta;type Story=StoryObj<typeof meta>;export const Default:Story={};export const Compact:Story={args:{compact:true,size:40}};
