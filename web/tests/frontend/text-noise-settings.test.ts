import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusTextNoiseSettings from "../../src/components/CorpusTextNoiseSettings.vue";

describe("text noise settings", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("exposes the threshold on a labelled range and emits a new copy", async () => {
    const wrapper = mount(CorpusTextNoiseSettings, { props: { threshold: 45, llmAssist: false } });
    expect(wrapper.text()).toContain("Source illegibility");
    const slider = wrapper.get('input[type="range"]');
    expect(slider.attributes("aria-valuenow")).toBe("45");
    await slider.setValue("60");
    expect(wrapper.emitted("update:threshold")?.[0]).toEqual([60]);
  });

  it("LLM assist is off until switched on", async () => {
    const wrapper = mount(CorpusTextNoiseSettings, { props: { threshold: 45, llmAssist: false } });
    const box = wrapper.get('input[type="checkbox"]');
    expect((box.element as HTMLInputElement).checked).toBe(false);
    await box.setValue(true);
    expect(wrapper.emitted("update:llmAssist")?.[0]).toEqual([true]);
  });
});
