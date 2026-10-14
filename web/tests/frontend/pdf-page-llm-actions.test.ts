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

const renderer = vi.hoisted(() => ({
  extractPdfPageSmart: vi.fn(async () => ({ text: "", source: "pdf.js", warning: "" })),
}));
vi.mock("../../src/domain/sharedPdfExplorerRenderer", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  ...renderer,
}));
const toast = vi.hoisted(() => vi.fn());
vi.mock("../../src/composables/notifications", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  toast,
}));

import "../../src/domain/appBootstrap";
import {
  cleanPdfPageWithLlm,
  linkPdfPageWithLlm,
  registerPdfLlmTaskHooks,
} from "../../src/domain/pdfPageLlmActions";
import { state } from "../../src/domain/sharedUrlState";

describe("PDF page LLM actions", () => {
  const openLlmTaskLauncher = vi.fn();
  beforeEach(() => {
    vi.clearAllMocks();
    registerPdfLlmTaskHooks({ openLlmTaskLauncher, openPdfDraftRecord: vi.fn() });
    Object.assign(state.pdf, { name: "glas.pdf", title: "Glas", page: 3, text: "" });
    state.files = [];
  });

  it("warns instead of launching a task when the page has no text", async () => {
    await cleanPdfPageWithLlm();
    expect(openLlmTaskLauncher).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: "warning" });
  });

  it("launches the cleanup task with the extracted page text through the registered hook", async () => {
    renderer.extractPdfPageSmart.mockResolvedValueOnce({
      text: "la différance",
      source: "pdf.js",
      warning: "",
    });
    await cleanPdfPageWithLlm();
    expect(openLlmTaskLauncher).toHaveBeenCalledWith(
      expect.objectContaining({
        task: "pdf_clean_text",
        payload: expect.objectContaining({ raw_text: "la différance", pdf_page: 3 }),
      }),
    );
    expect(state.pdf.text).toBe("la différance");
  });

  it("refuses to match a page when no records are loaded", async () => {
    await linkPdfPageWithLlm();
    expect(openLlmTaskLauncher).not.toHaveBeenCalled();
    expect(toast).toHaveBeenCalledWith(expect.any(String), { tone: "warning" });
  });
});
