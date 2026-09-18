import type { Meta, StoryObj } from "@storybook/vue3-vite"; import AccessibleEmptyState from "./AccessibleEmptyState.vue";
const meta={title:"Foundations/Feedback/Empty State",component:AccessibleEmptyState,args:{title:"No records yet",description:"Choose a work or change the search filters.",actionLabel:"Browse works",icon:"books"}} satisfies Meta<typeof AccessibleEmptyState>;export default meta;type Story=StoryObj<typeof meta>;export const Default:Story={};

export const NeutralIcon: Story = { args: { title: "No saved responses", description: "Saved research responses will appear here.", icon: "spark", iconTone: "neutral" } };
