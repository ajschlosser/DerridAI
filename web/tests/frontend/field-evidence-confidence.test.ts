/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import FieldEvidenceList from "../../src/components/FieldEvidenceList.vue";
import { useI18nStore } from "../../src/stores/i18n";

describe("FieldEvidenceList confidence semantics", () => {
  beforeEach(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
    const i18n = useI18nStore();
    i18n.locale = "en-US";
  });

  function render(confidence: number | null | undefined) {
    return mount(FieldEvidenceList, {
      global: { plugins: [createPinia()] },
      props: {
        fields: ["speaker"],
        evidence: {
          speaker: { block_ids: ["b-1"], confidence },
        },
      },
    });
  }

  it("does not manufacture zero confidence when confidence is unavailable", () => {
    expect(render(null).text()).toContain("b-1");
    expect(render(null).text()).not.toContain("0%");
    expect(render(undefined).text()).not.toContain("0%");
  });

  it("renders an explicitly reported zero confidence as zero", () => {
    expect(render(0).text()).toContain("0%");
  });
});
