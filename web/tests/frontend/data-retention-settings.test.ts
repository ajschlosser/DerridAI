/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const systemApi = vi.hoisted(() => ({
  dataRetention: vi.fn(),
  setDataRetention: vi.fn(),
  applyDataRetention: vi.fn(),
  reclaimDataRetentionSpace: vi.fn(),
}));
vi.mock("../../src/api/system", () => ({ systemApi }));

import type { RetentionPolicy, RetentionRule } from "../../src/api/system";
import DataRetentionSettings from "../../src/components/settings/DataRetentionSettings.vue";

const keep: RetentionRule = { mode: "keep", value: null };
const inherit: RetentionRule = { mode: "inherit", value: null };

function overview(
  overrides: Record<string, unknown> = {},
  policy: RetentionPolicy = { default: keep, stores: {} },
) {
  return {
    policy,
    evaluated_at: "2026-09-29T12:00:00Z",
    applied: false,
    stores: [
      {
        store_id: "pipeline_traces:vector_store_search",
        kind: "pipeline_traces",
        feature: "vector_store_search",
        rule: inherit,
        effective_rule: policy.default,
        count: 10,
        bytes: 2_000_000,
        pinned_count: 0,
        oldest_at: "2026-01-01T00:00:00Z",
        remove_count: 0,
        remove_bytes: 0,
        ...overrides,
      },
      {
        store_id: "job_history",
        kind: "job_history",
        feature: null,
        rule: inherit,
        effective_rule: policy.default,
        count: 3,
        bytes: 900,
        pinned_count: 1,
        oldest_at: null,
        remove_count: 0,
        remove_bytes: 0,
      },
    ],
  };
}

describe("Data retention settings", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    systemApi.dataRetention.mockResolvedValue(overview());
  });

  it("lists operational stores with their size, pins, and effective rule", async () => {
    const wrapper = mount(DataRetentionSettings);
    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain("Pipeline traces: vector_store_search");
    expect(text).toContain("Finished job history");
    expect(text).toContain("1 kept because other retained data depends on them");
    expect(text).toContain("In effect: keep everything");
    expect(wrapper.get("select").attributes("aria-label")).toBe(
      "Rule for Pipeline traces: vector_store_search",
    );
  });

  it("saves a system-wide age limit and a per-store size cap", async () => {
    systemApi.setDataRetention.mockImplementation(async (policy) => overview({}, policy));
    const wrapper = mount(DataRetentionSettings);
    await flushPromises();

    await wrapper.findAll('input[type="radio"]')[1].setValue(true);
    const select = wrapper.get("select");
    await select.setValue("max_size_gb");
    const sizes = wrapper.findAll('input[type="number"]');
    await sizes[1].setValue("0.5");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "Save retention policy")!
      .trigger("click");
    await flushPromises();

    expect(systemApi.setDataRetention).toHaveBeenCalledWith({
      default: { mode: "max_age_days", value: 90 },
      stores: { "pipeline_traces:vector_store_search": { mode: "max_size_gb", value: 0.5 } },
    });
    expect(wrapper.text()).toContain("Retention policy saved.");
  });

  it("blocks invalid limits before they reach the server", async () => {
    const wrapper = mount(DataRetentionSettings);
    await flushPromises();
    await wrapper.findAll('input[type="radio"]')[1].setValue(true);
    await wrapper.get('input[type="number"]').setValue("2.5");

    expect(wrapper.text()).toContain("Enter whole days from 1 to 36500.");
    const save = wrapper
      .findAll("button")
      .find((button) => button.text() === "Save retention policy")!;
    expect(save.attributes("disabled")).toBeDefined();
  });

  it("previews and confirms before removing anything", async () => {
    systemApi.dataRetention.mockResolvedValue(
      overview(
        { remove_count: 4, remove_bytes: 1_000_000 },
        {
          default: { mode: "max_age_days", value: 30 },
          stores: {},
        },
      ),
    );
    systemApi.applyDataRetention.mockResolvedValue({
      ...overview(),
      applied: true,
      stores: [{ ...overview().stores[0], removed_count: 4 }],
    });
    const wrapper = mount(DataRetentionSettings, { attachTo: document.body });
    await flushPromises();

    await wrapper
      .findAll("button")
      .find((button) => button.text() === "Apply now…")!
      .trigger("click");
    await flushPromises();
    expect(systemApi.applyDataRetention).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain("This permanently removes 4 records");

    const confirm = [...document.body.querySelectorAll("button")].find(
      (button) => button.textContent?.trim() === "Remove 4 records",
    )!;
    confirm.click();
    await flushPromises();
    expect(systemApi.applyDataRetention).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Removed 4 records.");
    wrapper.unmount();
  });

  it("does not mount confirmation dialogs before they are opened", async () => {
    const wrapper = mount(DataRetentionSettings, { attachTo: document.body });
    await flushPromises();

    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    wrapper.unmount();
  });

  it("says so when the saved policy removes nothing", async () => {
    const wrapper = mount(DataRetentionSettings);
    await flushPromises();
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "Apply now…")!
      .trigger("click");
    await flushPromises();

    expect(wrapper.text()).toContain("The saved policy removes nothing right now.");
    expect(systemApi.applyDataRetention).not.toHaveBeenCalled();
  });
});
