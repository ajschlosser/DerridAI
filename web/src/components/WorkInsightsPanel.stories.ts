import type { Meta, StoryObj } from "@storybook/vue3";
import WorkInsightsPanel from "./WorkInsightsPanel.vue";

const metrics = [
  { id: "persons", field: "persons", title: "Persons", items: [{ label: "Emmanuel Levinas", count: 31 }, { label: "Martin Heidegger", count: 24 }] },
  { id: "concepts", field: "concepts", title: "Concepts", items: [{ label: "responsibility", count: 42 }, { label: "death", count: 27 }] },
  { id: "topics", field: "topics", title: "Topics", items: [{ label: "ethics", count: 36 }, { label: "mourning", count: 18 }] },
  { id: "targets", field: "target", title: "Discourse targets", items: [{ label: "Levinasian ethics", count: 19 }, { label: "Heideggerian ontology", count: 12 }] },
  { id: "roles", field: "discourse_role", title: "Discourse roles", type: "pie" as const, items: [{ label: "analysis", count: 52 }, { label: "argument", count: 31 }, { label: "quotation", count: 11 }, { label: "Other", count: 6, other: true }] },
];

const meta = {
  title: "Works/WorkInsightsPanel",
  component: WorkInsightsPanel,
  args: { work: "Adieu to Emmanuel Levinas", metrics },
} satisfies Meta<typeof WorkInsightsPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const RankingAndDiscourseRoleShare: Story = {};
