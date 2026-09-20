import type { Meta, StoryObj } from "@storybook/vue3-vite";
import CorpusActionMenu from "./CorpusActionMenu.vue";

const items = [
  { id: "previous", label: "Combine with previous record" },
  {
    id: "next",
    label: "Combine with next record",
    reason: "There is no next record to combine with.",
  },
  { id: "slice", label: "Slice record" },
  { id: "preview", label: "Preview JSONL" },
];
const meta = {
  title: "Corpus Builder/Review/Action Menu",
  component: CorpusActionMenu,
  args: { label: "More actions", menuLabel: "More record actions", items, placement: "bottom" },
  // The menu opens below the button; leave room so the story shows it.
  decorators: [() => ({ template: '<div style="min-height:16rem;padding:1rem"><story /></div>' })],
} satisfies Meta<typeof CorpusActionMenu>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const AllAvailable: Story = {
  args: { items: items.map(({ id, label }) => ({ id, label })) },
};
export const OpensAbove: Story = {
  args: { placement: "top" },
  decorators: [() => ({ template: '<div style="padding-top:16rem"><story /></div>' })],
};
export const Disabled: Story = { args: { disabled: true } };
