import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorCollectionHero from "./VectorCollectionHero.vue";
const collection = {
  name: "derrida-primary",
  count: 12840,
  description: "Primary multilingual Derrida research corpus",
  embedding_provider: "ollama",
  embedding_model: "bge-m3:latest",
  embedding_dimension: 1024,
  distance_metric: "cosine",
  retrieval_mode: "hybrid",
  language_codes: ["en", "fr"],
  status: "ready",
  protected: true,
  build_id: "build-20260919-abcdef",
  last_synced_at: "2026-09-19T12:00:00.000Z",
  source_label: "browser workspace",
};
const meta = {title: "Vector Stores/Collection Hero", component: VectorCollectionHero, args: {collection, pendingCount: 12}} satisfies Meta<typeof VectorCollectionHero>;
export default meta;
type Story = StoryObj<typeof meta>;
export const ProtectedWithPending: Story = {};
export const UnprotectedEmpty: Story = {args: {collection: {...collection, protected: false, count: 0, status: "empty", last_synced_at: null}, pendingCount: 0}};
