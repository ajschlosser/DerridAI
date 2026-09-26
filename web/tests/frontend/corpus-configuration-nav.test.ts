/* Copyright 2026 Aaron John Schlosser, PhD. */
import { defineComponent, ref } from "vue";
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import CorpusConfigurationNav from "../../src/components/corpus-builder/CorpusConfigurationNav.vue";

describe("Corpus Builder configuration navigation", () => {
  it("moves the active tab state when a configuration section is selected", async () => {
    const Harness = defineComponent({
      components: { CorpusConfigurationNav },
      setup() {
        const section = ref<"source" | "structure" | "enrichment" | "metadata" | "advanced">(
          "source",
        );
        return { section };
      },
      template: `
        <div>
          <CorpusConfigurationNav
            v-model="section"
            :has-source="true"
            :structure-available="true"
          />
          <output data-testid="active-section">{{ section }}</output>
        </div>
      `,
    });
    const wrapper = mount(Harness);

    const source = wrapper.get("#corpus-config-tab-source");
    const enrichment = wrapper.get("#corpus-config-tab-enrichment");
    expect(source.attributes("aria-selected")).toBe("true");
    expect(source.attributes("data-active")).toBe("true");

    await enrichment.trigger("click");

    expect(wrapper.get('[data-testid="active-section"]').text()).toBe("enrichment");
    expect(source.attributes("aria-selected")).toBe("false");
    expect(enrichment.attributes("aria-selected")).toBe("true");
    expect(enrichment.attributes("data-active")).toBe("true");
  });
});
