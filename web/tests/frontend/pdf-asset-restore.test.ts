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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const stored: { asset?: Record<string, unknown> } = {};
const getDocument = vi.fn();

vi.mock("pdfjs-dist/legacy/build/pdf.mjs", () => ({
  getDocument: (...a: unknown[]) => getDocument(...a),
}));
vi.mock("../../src/domain/sharedWorkspaceStorage", () => ({
  workspaceDb: { get: vi.fn(async () => stored.asset), put: vi.fn() },
}));

import { restoreCurrentPdfAsset } from "../../src/domain/pdfAssetPersistence";
import { loadPdfMetadata } from "../../src/domain/pdfMetadata";
import { state } from "../../src/domain/sharedUrlState";

describe("loadPdfMetadata", () => {
  it("prefers info, then XMP, then the file name", async () => {
    const doc = { getMetadata: async () => ({ info: { Title: " T ", Author: "A" } }) };
    expect(await loadPdfMetadata(doc, "x.pdf")).toEqual({ title: "T", author: "A" });
    const xmp = {
      getMetadata: async () => ({
        info: {},
        metadata: { get: (k: string) => (k === "dc:title" ? "X" : "") },
      }),
    };
    expect(await loadPdfMetadata(xmp, "x.pdf")).toEqual({ title: "X", author: "" });
    expect(await loadPdfMetadata(null, "x.pdf")).toEqual({ title: "x", author: "" });
  });

  it("falls back to the file name when metadata cannot be read", async () => {
    vi.spyOn(console, "warn").mockImplementation(() => undefined);
    const doc = {
      getMetadata: async () => {
        throw new Error("bad");
      },
    };
    expect(await loadPdfMetadata(doc, "x.pdf")).toEqual({ title: "x", author: "" });
  });
});

describe("restoreCurrentPdfAsset", () => {
  beforeEach(() => {
    URL.createObjectURL = vi.fn(() => "blob:restored");
    URL.revokeObjectURL = vi.fn();
    getDocument.mockReset();
    state.pdf = {};
  });

  it("restores the stored PDF into state and clamps the page to the document", async () => {
    stored.asset = {
      blob: new Blob(["%PDF"], { type: "application/pdf" }),
      name: "a.pdf",
      page: 9,
      rotation: 450,
      text: "t",
    };
    getDocument.mockReturnValue({
      promise: Promise.resolve({
        numPages: 3,
        getMetadata: async () => ({ info: { Title: "Doc" } }),
      }),
    });
    await restoreCurrentPdfAsset();
    expect(state.pdf.name).toBe("a.pdf");
    expect(state.pdf.title).toBe("Doc");
    expect(state.pdf.page).toBe(3);
    expect(state.pdf.rotation).toBe(90);
    expect(state.pdf.url).toBe("blob:restored");
  });

  it("keeps the file and records the error when PDF.js fails", async () => {
    stored.asset = { blob: new Blob(["%PDF"]), name: "b.pdf" };
    getDocument.mockImplementation(() => {
      throw new Error("boom");
    });
    await restoreCurrentPdfAsset();
    expect(state.pdf.doc).toBeNull();
    expect(state.pdf.extractError).toContain("boom");
    expect(state.pdf.name).toBe("b.pdf");
  });

  it("does nothing without a stored asset", async () => {
    stored.asset = undefined;
    await restoreCurrentPdfAsset();
    expect(state.pdf.name).toBeUndefined();
  });
});
