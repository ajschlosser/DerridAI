import type { Meta, StoryObj } from "@storybook/vue3-vite";
import VectorBackendPanel from "./VectorBackendPanel.vue";
const health = {available: true, mode: "embedded" as const, path: "/data/chroma", host_path_hint: "./data/chroma", data_root: "/data", url: null, tenant: null, database: null, token_configured: false, writable: true, heartbeat_ok: true, chroma_version: "1.1.0", collection_count: 1, identity: "Local Chroma · ./data/chroma", error: null};
const meta = {title: "Corpus Data/Backend Panel", component: VectorBackendPanel, args: {health, probing: false, applying: false, probeResult: null, error: ""}} satisfies Meta<typeof VectorBackendPanel>;
export default meta;
type Story = StoryObj<typeof meta>;
export const Embedded: Story = {};
export const HttpServer: Story = {args: {health: {...health, mode: "http", path: null, url: "http://chroma:8000", tenant: "default_tenant", database: "default_database", identity: "Chroma server · http://chroma:8000"}}};
