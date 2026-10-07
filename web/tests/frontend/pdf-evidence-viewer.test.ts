/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 */

import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

const pdf = vi.hoisted(() => ({
  GlobalWorkerOptions: { workerSrc: "" },
  getDocument: vi.fn(),
}));

vi.mock("pdfjs-dist/legacy/build/pdf.mjs", () => pdf);
vi.mock("pdfjs-dist/legacy/build/pdf.worker.mjs?url", () => ({ default: "pdf.worker.mjs" }));

import PdfEvidenceViewer from "../../src/components/PdfEvidenceViewer.vue";

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function viewport(scale: number) {
  return { width: 600 * scale, height: 800 * scale };
}

describe("PdfEvidenceViewer page identity", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    pdf.getDocument.mockReset();
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      {} as CanvasRenderingContext2D,
    );
  });

  it("does not label retained canvas pixels or overlays as a newly requested page", async () => {
    const secondRender = deferred<void>();
    const firstTask = { promise: Promise.resolve(), cancel: vi.fn() };
    const secondTask = { promise: secondRender.promise, cancel: vi.fn() };
    const getPage = vi.fn(async (page: number) => ({
      getViewport: ({ scale }: { scale: number }) => viewport(scale),
      render: vi.fn(() => (page === 1 ? firstTask : secondTask)),
    }));
    const document = {
      numPages: 2,
      getPage,
      destroy: vi.fn(async () => undefined),
    };
    pdf.getDocument.mockReturnValue({
      promise: Promise.resolve(document),
      destroy: vi.fn(async () => undefined),
    });

    const wrapper = mount(PdfEvidenceViewer, {
      props: {
        pdfUrl: "/source.pdf",
        page: 1,
        pageWidth: 600,
        pageHeight: 800,
        blocks: [
          { block_id: "page-1", page: 1, bbox: [0, 0, 100, 100] },
          { block_id: "page-2", page: 2, bbox: [0, 0, 100, 100] },
        ] as never,
      },
    });
    await flushPromises();

    const canvas = wrapper.get("canvas");
    expect(canvas.attributes("aria-label")).toContain("1");
    expect(wrapper.findAll(".source-box")).toHaveLength(1);

    await wrapper.setProps({ page: 2 });
    await flushPromises();

    expect(canvas.attributes("aria-label")).not.toContain("2");
    expect(wrapper.findAll(".source-box")).toHaveLength(0);
    expect(wrapper.find(".viewer-caption").exists()).toBe(false);

    secondRender.resolve();
    await flushPromises();

    expect(canvas.attributes("aria-label")).toContain("2");
    expect(wrapper.findAll(".source-box")).toHaveLength(1);
    expect(wrapper.get(".viewer-caption").text()).toContain("2");

    wrapper.unmount();
  });
});
