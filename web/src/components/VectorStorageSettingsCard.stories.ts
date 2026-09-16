import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorStorageSettingsCard from "./VectorStorageSettingsCard.vue";
const meta={title:"Vector Stores/Storage Settings Card",component:VectorStorageSettingsCard,args:{hostPath:"./data/chroma",containerPath:"/data/chroma"}} satisfies Meta<typeof VectorStorageSettingsCard>;export default meta;type Story=StoryObj<typeof meta>;export const Default:Story={};
