/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { Meta, StoryObj } from "@storybook/vue3-vite";
import type { RetentionOverview, RetentionStore } from "../../api/system";
import DataRetentionSettings from "./DataRetentionSettings.vue";

const store = (overrides: Partial<RetentionStore>): RetentionStore => ({
  store_id: "job_history",
  kind: "job_history",
  feature: null,
  rule: { mode: "inherit", value: null },
  effective_rule: { mode: "keep", value: null },
  count: 1240,
  bytes: 38_400_000,
  pinned_count: 0,
  oldest_at: "2026-03-02T09:00:00Z",
  remove_count: 0,
  remove_bytes: 0,
  warnings: [],
  ...overrides,
});

const overview = (
  stores: RetentionStore[],
  policy?: RetentionOverview["policy"],
): RetentionOverview => ({
  policy: policy || { default: { mode: "keep", value: null }, stores: {} },
  evaluated_at: "2026-09-29T12:00:00Z",
  applied: false,
  stores,
});

const stores = [
  store({
    store_id: "pipeline_traces:vector_store_search",
    kind: "pipeline_traces",
    feature: "vector_store_search",
    count: 184_220,
    bytes: 2_310_000_000,
  }),
  store({
    store_id: "pipeline_traces:research",
    kind: "pipeline_traces",
    feature: "research",
    count: 412,
    bytes: 96_000_000,
    pinned_count: 380,
  }),
  store({
    store_id: "pipeline_benchmark_runs",
    kind: "pipeline_benchmark_runs",
    count: 18,
    bytes: 4_200_000,
  }),
  store({}),
  store({ store_id: "response_cache", kind: "response_cache", count: 530, bytes: 212_000_000 }),
];

/** Serve a fixed overview so each story shows one state without a backend. */
function withOverview(data: RetentionOverview) {
  return () => {
    globalThis.fetch = async () =>
      new Response(JSON.stringify(data), { headers: { "Content-Type": "application/json" } });
    return { template: "<story />" };
  };
}

const meta = {
  title: "Settings/Data Retention",
  component: DataRetentionSettings,
  decorators: [withOverview(overview(stores))],
} satisfies Meta<typeof DataRetentionSettings>;
export default meta;
type Story = StoryObj<typeof meta>;

export const KeepEverything: Story = {};
export const WithPolicy: Story = {
  decorators: [
    withOverview(
      overview(
        stores.map((item) =>
          item.store_id === "pipeline_traces:vector_store_search"
            ? {
                ...item,
                rule: { mode: "max_size_gb", value: 1 },
                effective_rule: { mode: "max_size_gb", value: 1 },
                remove_count: 104_000,
                remove_bytes: 1_310_000_000,
              }
            : { ...item, effective_rule: { mode: "max_age_days", value: 90 } },
        ),
        {
          default: { mode: "max_age_days", value: 90 },
          stores: { "pipeline_traces:vector_store_search": { mode: "max_size_gb", value: 1 } },
        },
      ),
    ),
  ],
};
export const French: Story = { parameters: { locale: "fr-CA" } };
