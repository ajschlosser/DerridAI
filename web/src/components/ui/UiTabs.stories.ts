import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import UiTabs from "./UiTabs.vue";

const tabs = [
  {id: "overview", label: "Overview"},
  {id: "data", label: "Data"},
  {id: "retrieval", label: "Retrieval"},
  {id: "builds", label: "Builds"},
  {id: "settings", label: "Settings"},
];
const meta = {
  title: "Foundations/Navigation/Tabs",
  component: UiTabs,
  args: {tabs, modelValue: "overview", tablistLabel: "Collection sections"},
} satisfies Meta<typeof UiTabs>;
export default meta;
type Story = StoryObj<typeof meta>;

export const CollectionSections: Story = {
  render: () => ({
    components: {UiTabs},
    setup() {
      const current = ref("overview");
      return {current, tabs};
    },
    template: '<UiTabs :tabs="tabs" v-model="current" tablist-label="Collection sections" />',
  }),
};
