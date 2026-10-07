/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia } from "pinia";
import { beforeAll, beforeEach, describe, expect, it } from "vitest";
import LazyFeatureDialogHosts from "../../src/components/shell/LazyFeatureDialogHosts.vue";
import {
  closeRecordPreviewDialog,
  openRecordPreviewDialog,
} from "../../src/composables/recordPreviewDialog";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  };
});

describe("lazy feature dialog hosts", () => {
  beforeEach(() => {
    closeRecordPreviewDialog();
  });

  it("does not mount a feature dialog until that feature requests it", async () => {
    const wrapper = mount(LazyFeatureDialogHosts, {
      global: { plugins: [createPinia()] },
    });

    expect(wrapper.find(".record-preview-dialog").exists()).toBe(false);

    openRecordPreviewDialog({
      recordId: "r1",
      subtitle: "Glas · corpus.jsonl",
      stale: false,
      summary: {
        work: "Glas",
        pages: "1",
        citation: "Derrida, Glas",
        proposalCount: 0,
        needsReview: false,
      },
      fields: [],
      text: "trace",
      proposals: [],
      history: [],
      copyKey: "f1::0",
      openFull: () => undefined,
    });
    await flushPromises();

    expect(wrapper.find(".record-preview-dialog").exists()).toBe(true);
    expect(wrapper.get(".record-preview-dialog").attributes("open")).toBeDefined();

    closeRecordPreviewDialog();
    await flushPromises();

    // Once loaded, keep the host mounted so the child can observe closure and
    // let the native dialog restore focus before its implementation is removed.
    expect(wrapper.find(".record-preview-dialog").exists()).toBe(true);
    expect(wrapper.get(".record-preview-dialog").attributes("open")).toBeUndefined();
    wrapper.unmount();
  });
});
