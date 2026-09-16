import type { Meta, StoryObj } from "@storybook/vue3";
import BlockingUpsertProgress from "./BlockingUpsertProgress.vue";
const meta:Meta<typeof BlockingUpsertProgress>={title:"Operations/Blocking Upsert Progress",component:BlockingUpsertProgress,args:{done:1000,total:2500,status:"Committing records 1001–1500 of 2500"}};export default meta;type Story=StoryObj<typeof BlockingUpsertProgress>;export const Default:Story={};
