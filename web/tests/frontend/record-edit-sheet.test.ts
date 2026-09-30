/* Copyright 2026 Aaron John Schlosser, PhD. */
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import RecordEditSheet from "../../src/components/record/RecordEditSheet.vue";

function fieldLabel(wrapper: ReturnType<typeof mount>, text: string) {
  return wrapper
    .findAll("label")
    .find((label) => label.find("span").text().trim() === text)!;
}

describe("RecordEditSheet metadata cardinality", () => {
  beforeEach(() => setActivePinia(createPinia()));

  it("does not infer known scalar cardinality from a legacy array value", async () => {
    const wrapper = mount(RecordEditSheet, {
      attachTo: document.body,
      props: {
        open: true,
        record: {
          record_id: "r1",
          quoted_speaker: ["Levinas", "Heidegger"],
          topics: ["hospitality", "democracy"],
        },
      },
    });
    await flushPromises();

    const quotedSpeaker = fieldLabel(wrapper, "Quoted speaker");
    expect((quotedSpeaker.get("input").element as HTMLInputElement).value).toBe(
      "Levinas | Heidegger",
    );
    expect(quotedSpeaker.find("small").exists()).toBe(false);

    const topics = fieldLabel(wrapper, "Topics");
    expect((topics.get("input").element as HTMLInputElement).value).toBe(
      "hospitality, democracy",
    );
    expect(topics.get("small").text()).toContain("Separate multiple values");

    wrapper.unmount();
  });
});
