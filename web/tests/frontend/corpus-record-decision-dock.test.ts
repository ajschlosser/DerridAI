/* Copyright 2026 Aaron John Schlosser, PhD. */
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it } from "vitest";
import CorpusRecordDecisionDock from "../../src/components/corpus-builder/CorpusRecordDecisionDock.vue";

describe("Corpus Builder decision dock", () => {
  beforeEach(() => setActivePinia(createPinia()));

  const blockerText = (count: number) =>
    mount(CorpusRecordDecisionDock, {
      props: { blockingCount: count, blockingLabel: "target" },
    })
      .get(".dock-blocker .sr-only")
      .text();

  it("says 'decision' for one open field and 'decisions' for several, never '(s)'", () => {
    expect(blockerText(1)).toBe("1 decision left");
    expect(blockerText(3)).toBe("3 decisions left");
    expect(blockerText(3)).not.toContain("(s)");
  });
});
