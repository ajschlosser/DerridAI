/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import UiRelationNodeShell from "./UiRelationNodeShell.vue";
import UiRelationToolbar from "./UiRelationToolbar.vue";
import UiRelationViewport from "./UiRelationViewport.vue";

const meta = {
  title: "Primitives/Relations/Viewport",
  component: UiRelationViewport,
  parameters: { layout: "padded" },
} satisfies Meta<typeof UiRelationViewport>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Interactive: Story = {
  render: () => ({
    components: { UiRelationNodeShell, UiRelationToolbar, UiRelationViewport },
    setup() {
      const viewport = ref<InstanceType<typeof UiRelationViewport> | null>(null);
      const nodes = ref([
        { id: "source", label: "Source span", x: 120, y: 120 },
        { id: "claim", label: "Generated claim", x: 420, y: 260 },
      ]);
      function move(id: string, point: { x: number; y: number }) {
        const node = nodes.value.find((item) => item.id === id);
        if (node) Object.assign(node, point);
      }
      return { viewport, nodes, move };
    },
    template: `
      <div style="display:grid;gap:8px;max-width:900px">
        <UiRelationToolbar
          aria-label="Map controls"
          zoom-out-label="Zoom out"
          zoom-in-label="Zoom in"
          fit-label="Fit map"
          reset-label="Reset layout"
          @zoom-out="viewport?.zoomBy(1 / 1.15)"
          @zoom-in="viewport?.zoomBy(1.15)"
          @fit="viewport?.fitView({ x: 80, y: 80, width: 520, height: 260 })"
          @reset="viewport?.resetView()"
        />
        <UiRelationViewport
          ref="viewport"
          style="height:420px"
          aria-label="Relationship map"
          help-text="Drag the background to pan. Drag nodes to reposition them. Hold Alt and use arrow keys to move a focused node."
          resize-label="Resize relationship map"
          :initial-center="{ x: 360, y: 220 }"
          :content-width="720"
          :content-height="440"
        >
          <template #default="{ zoom }">
            <svg aria-hidden="true" style="position:absolute;inset:0;width:720px;height:440px">
              <line
                :x1="nodes[0].x"
                :y1="nodes[0].y"
                :x2="nodes[1].x"
                :y2="nodes[1].y"
                stroke="currentColor"
              />
            </svg>
            <UiRelationNodeShell
              v-for="node in nodes"
              :key="node.id"
              :node-id="node.id"
              :x="node.x"
              :y="node.y"
              :zoom="zoom"
              :aria-label="node.label"
              style="padding:8px 12px;border:1px solid var(--border-subtle);border-radius:999px;background:var(--surface-card);color:var(--text-primary);transform:translate(-50%,-50%)"
              @move="move(node.id, $event)"
            >
              {{ node.label }}
            </UiRelationNodeShell>
          </template>
        </UiRelationViewport>
      </div>
    `,
  }),
};

export const FrenchLengthStress: Story = {
  ...Interactive,
  name: "French / long-string stress",
};
