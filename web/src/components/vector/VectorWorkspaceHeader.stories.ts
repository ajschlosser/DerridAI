import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorWorkspaceHeader from "./VectorWorkspaceHeader.vue";
const health = {available: true, mode: "embedded" as const, path: "/data/chroma", host_path_hint: "./data/chroma", data_root: "/data", url: null, tenant: null, database: null, token_configured: false, writable: true, heartbeat_ok: true, chroma_version: "1.1.0", collection_count: 2, identity: "Local Chroma · ./data/chroma", error: null};
const meta = {title: "Vector Stores/Workspace Header", component: VectorWorkspaceHeader, args: {health, collectionCount: 2}} satisfies Meta<typeof VectorWorkspaceHeader>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Ready: Story = {};
export const Unavailable: Story = {args: {health: {...health, available: false, heartbeat_ok: false, error: "connection refused", identity: "Chroma server · http://chroma:8000", mode: "http", path: null, url: "http://chroma:8000"}}};
