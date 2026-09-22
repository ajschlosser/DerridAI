/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import SubsetCondition from "./SubsetCondition.vue";

const meta = {
  title: "Records/Subset Condition",
  component: SubsetCondition,
} satisfies Meta<typeof SubsetCondition>;
export default meta;
type Story = StoryObj<typeof SubsetCondition>;

const fields = [
  { key: "work", label: "Work" },
  { key: "exists_flag", label: "Needs review" },
];
const render = (operator: string, value: string) => () => ({
  components: { SubsetCondition },
  setup() {
    const state = { field: ref("work"), operator: ref(operator), value: ref(value) };
    return { ...state, fields, suggestions: ["Glas", "Margins of Philosophy"] };
  },
  template: `<SubsetCondition v-model:field="field" v-model:operator="operator" v-model:value="value" :fields="fields" :suggestions="suggestions" position="item 1" />`,
});

export const WithValue: Story = { render: render("equals", "Glas") };
/** Presence and truth tests take no value, so the value box is disabled. */
export const Valueless: Story = { render: render("exists", "") };
