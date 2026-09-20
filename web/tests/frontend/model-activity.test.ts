import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusModelActivity from "../../src/components/CorpusModelActivity.vue";

const activity = (over = {}) => ({ state: "loading_model" as const, task: "manifest" as const, model: "qwen-14b", provider: "ollama", seconds: 108, calls_in_flight: 1, ...over });

describe("model activity line", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("says a large model is still loading, with the elapsed time", () => {
    const text = mount(CorpusModelActivity, { props: { activity: activity() } }).text();
    expect(text).toContain("Waiting for qwen-14b to load into memory");
    expect(text).toContain("1 min 48 s");
  });
  it("says what a loaded model is working on", () => {
    const text = mount(CorpusModelActivity, { props: { activity: activity({ state: "working", task: "segmentation", seconds: 12 }) } }).text();
    expect(text).toContain("qwen-14b is working on the record boundaries (12 s)");
  });
  it("falls back to plain waiting when the provider cannot say, and shows nothing when idle", () => {
    expect(mount(CorpusModelActivity, { props: { activity: activity({ state: "unknown", seconds: 5 }) } }).text()).toContain("Waiting for qwen-14b to answer");
    expect(mount(CorpusModelActivity, { props: { activity: null } }).find("p").exists()).toBe(false);
  });
});

describe("a load that runs long", () => {
  beforeEach(() => setActivePinia(createPinia()));
  it("suggests restarting Ollama only after three minutes", () => {
    expect(mount(CorpusModelActivity, { props: { activity: activity({ seconds: 100 }) } }).text()).not.toContain("longer than usual");
    expect(mount(CorpusModelActivity, { props: { activity: activity({ seconds: 240 }) } }).text()).toContain("longer than usual");
    expect(mount(CorpusModelActivity, { props: { activity: activity({ state: "working", seconds: 240 }) } }).text()).not.toContain("longer than usual");
  });
});
