import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import ProviderModelPicker from "../../src/components/ProviderModelPicker.vue";
import { modelMatchesKind } from "../../src/domain/providerModels";

const models = [
  { name: "qwen3.5:4b", parameter_size: "4.7B", quantization_level: "Q4_K_M" },
  { name: "hf.co/x/Qwen3.6-14B:Q6_K", parameter_size: "14B", quantization_level: "Q6_K" },
  { name: "deepseek-r1:8b", parameter_size: "8B" },
];
const mountPicker = (props = {}) =>
  mount(ProviderModelPicker, {
    props: { profileName: "Local", modelValue: "qwen3.5:4b", models, ...props },
    attachTo: document.body,
  });

describe("provider model picker", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("still lets a model be typed, and offers the discovered names as suggestions", async () => {
    const wrapper = mountPicker();
    await wrapper.get("input.control").setValue("my-model");
    expect(wrapper.emitted("update:modelValue")![0]).toEqual(["my-model"]);
    expect(wrapper.findAll("datalist option")).toHaveLength(3);
    wrapper.unmount();
  });

  it("opens a searchable list with size and quantization, and chooses from it", async () => {
    const wrapper = mountPicker();
    await wrapper.get("button").trigger("click");
    const dialog = document.body.querySelector('[role="dialog"]')!;
    expect(dialog.textContent).toContain("3 discovered");
    expect(dialog.textContent).toContain("4.7B · Q4_K_M");
    const search = dialog.querySelector<HTMLInputElement>('input[type="search"]')!;
    search.value = "14b";
    search.dispatchEvent(new Event("input"));
    await wrapper.vm.$nextTick();
    expect(dialog.querySelector('[role="status"]')!.textContent).toContain("1 models match");
    dialog.querySelector<HTMLButtonElement>(".model-row")!.click();
    await wrapper.vm.$nextTick();
    expect(wrapper.emitted("update:modelValue")!.at(-1)).toEqual(["hf.co/x/Qwen3.6-14B:Q6_K"]);
    expect(document.body.querySelector('[role="dialog"]')).toBeNull();
    wrapper.unmount();
  });

  it("asks the endpoint for its models when none are known yet", async () => {
    const wrapper = mountPicker({ models: [] });
    await wrapper.get("button").trigger("click");
    expect(wrapper.emitted("discover")).toHaveLength(1);
    wrapper.unmount();
  });

  it("narrows the list by model kind", () => {
    expect(modelMatchesKind("deepseek-r1:8b", "reasoning")).toBe(true);
    expect(modelMatchesKind("qwen3.5:4b", "coding")).toBe(false);
    expect(modelMatchesKind("anything", "any")).toBe(true);
    const wrapper = mountPicker({ kind: "reasoning" });
    expect(wrapper.findAll("datalist option").map((o) => o.attributes("value"))).toEqual([
      "deepseek-r1:8b",
    ]);
    wrapper.unmount();
  });
});
