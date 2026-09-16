import type { Meta, StoryObj } from "@storybook/vue3";
import StorageLocationCard from "./StorageLocationCard.vue";
const meta:Meta<typeof StorageLocationCard>={title:"Vector Stores/Storage Location Card",component:StorageLocationCard,args:{hostPath:"./data/chroma",containerPath:"/data/chroma"}};export default meta;type Story=StoryObj<typeof StorageLocationCard>;export const Default:Story={};
