/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import UiRelationCardNode from "./UiRelationCardNode.vue";
import UiRelationChipNode from "./UiRelationChipNode.vue";
import UiRelationDotNode from "./UiRelationDotNode.vue";
import UiRelationEdge from "./UiRelationEdge.vue";
import UiRelationNodeShell from "./UiRelationNodeShell.vue";
import UiRelationToolbar from "./UiRelationToolbar.vue";
import UiRelationViewport from "./UiRelationViewport.vue";

const meta = {
  title: "Primitives/Relations/Viewport",
  component: UiRelationViewport,
  parameters: { layout: "padded" },
  args: { accessibleLabel: "Relationship map", resizeLabel: "Resize relationship map" },
} satisfies Meta<typeof UiRelationViewport>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Interactive: Story = {
  render: () => ({
    components: {
      UiRelationCardNode,
      UiRelationEdge,
      UiRelationNodeShell,
      UiRelationToolbar,
      UiRelationViewport,
    },
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
      function edgePath() {
        return `M ${nodes.value[0].x} ${nodes.value[0].y} L ${nodes.value[1].x} ${nodes.value[1].y}`;
      }
      return { viewport, nodes, move, edgePath };
    },
    template: `
      <div style="display:grid;gap:8px;max-width:900px">
        <UiRelationToolbar
          accessible-label="Map controls"
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
          accessible-label="Relationship map"
          help-text="Drag the background to pan. Drag nodes to reposition them. Hold Alt and use arrow keys to move a focused node."
          resize-label="Resize relationship map"
          :initial-center="{ x: 360, y: 220 }"
          :content-width="720"
          :content-height="440"
        >
          <template #default="{ zoom }">
            <svg aria-hidden="true" style="position:absolute;inset:0;width:720px;height:440px">
              <UiRelationEdge :path="edgePath()" />
            </svg>
            <UiRelationNodeShell
              v-for="node in nodes"
              :key="node.id"
              :node-id="node.id"
              :x="node.x"
              :y="node.y"
              :zoom="zoom"
              :accessible-label="node.label"
              style="width:170px;height:64px;padding:0;border:0;background:transparent;color:inherit;transform:translate(-50%,-50%)"
              @move="move(node.id, $event)"
            >
              <UiRelationCardNode compact>
                <small>Research object</small>
                <strong>{{ node.label }}</strong>
                <span>Presentation-only node position</span>
              </UiRelationCardNode>
            </UiRelationNodeShell>
          </template>
        </UiRelationViewport>
      </div>
    `,
  }),
};

export const VisualPrimitives: Story = {
  render: () => ({
    components: { UiRelationCardNode, UiRelationChipNode, UiRelationDotNode, UiRelationEdge },
    template: `
      <div style="display:grid;gap:18px;max-width:720px">
        <div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center">
          <UiRelationChipNode label="Concept: différance" />
          <div style="width:190px;height:72px">
            <UiRelationCardNode>
              <small>Generated claim</small>
              <strong>Claim c1</strong>
              <span>Bound to exact evidence</span>
            </UiRelationCardNode>
          </div>
        </div>
        <svg width="420" height="130" viewBox="0 0 420 130" aria-label="Dot and edge primitives">
          <UiRelationEdge path="M 70 65 Q 210 10 350 65" title="supports" />
          <g transform="translate(70 65)" style="--relation-node-dot:var(--viz-cat-1)">
            <UiRelationDotNode :radius="8" label="Source" show-label />
          </g>
          <g transform="translate(350 65)" style="--relation-node-dot:var(--viz-cat-3)">
            <UiRelationDotNode :radius="11" label="Claim" show-label />
          </g>
        </svg>
      </div>
    `,
  }),
};

export const FrenchLengthStress: Story = {
  ...Interactive,
  name: "French / long-string stress",
};
