import type { Meta, StoryObj } from "@storybook/vue3-vite";
import WorkInsightsPanel from "./WorkInsightsPanel.vue";

const metrics = [
  { id: "persons", field: "persons", title: "Persons mentioned", items: [{ label: "Emmanuel Levinas", count: 48 }, { label: "Martin Heidegger", count: 37 }, { label: "Immanuel Kant", count: 19 }] },
  { id: "concepts", field: "concepts", title: "Concepts", items: [{ label: "responsibility", count: 34 }, { label: "hospitality", count: 23 }, { label: "death", count: 18 }] },
  { id: "topics", field: "topics", title: "Topics", items: [{ label: "ethics", count: 41 }, { label: "mourning", count: 17 }] },
  { id: "speakers", field: "speaker", title: "Speakers", items: [{ label: "Derrida", count: 72 }, { label: "Levinas", count: 11 }] },
  { id: "position-holders", field: "position_holder", title: "Position holders", items: [{ label: "Levinas", count: 16 }, { label: "Heidegger", count: 10 }] },
];

const meta = {
  title: "Works/Work Insights Panel",
  component: WorkInsightsPanel,
  args: { work: "Adieu to Emmanuel Levinas", metrics },
  parameters: { layout: "padded" },
} satisfies Meta<typeof WorkInsightsPanel>;

export default meta;
type Story = StoryObj<typeof meta>;
export const Default: Story = {};
export const SparseMetadata: Story = { args: { metrics: metrics.map((metric, index) => index < 2 ? metric : { ...metric, items: [] }) } };
