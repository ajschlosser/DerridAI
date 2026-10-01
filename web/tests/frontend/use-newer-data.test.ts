/* Copyright 2026 Aaron John Schlosser, PhD. */
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, nextTick } from "vue";
import { mount, flushPromises } from "@vue/test-utils";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { queryClient } from "../../src/realtime/dataQuery";
import { useNewerData } from "../../src/composables/useNewerData";

let exposed: ReturnType<typeof useNewerData>;
const Probe = defineComponent({
  setup() {
    exposed = useNewerData();
    return () => h("div");
  },
});
const mounted = () => mount(Probe, { global: { plugins: [[VueQueryPlugin, { queryClient }]] } });

afterEach(() => queryClient.clear());

describe("useNewerData", () => {
  it("reports newer data only after a server invalidation and clears on acknowledge", async () => {
    const wrapper = mounted();
    await flushPromises();
    expect(exposed.hasNewer.value).toBe(false);

    // A refetch (focus, fallback poll) is not a change signal.
    await queryClient.refetchQueries({ queryKey: ["data", "corpus_records"] });
    expect(exposed.hasNewer.value).toBe(false);

    // Another resource changing is not ours.
    await queryClient.invalidateQueries({ queryKey: ["data", "users"] });
    expect(exposed.hasNewer.value).toBe(false);

    await queryClient.invalidateQueries({ queryKey: ["data", "corpus_records"] });
    await nextTick();
    expect(exposed.hasNewer.value).toBe(true);

    exposed.acknowledge();
    expect(exposed.hasNewer.value).toBe(false);
    wrapper.unmount();
  });
});
