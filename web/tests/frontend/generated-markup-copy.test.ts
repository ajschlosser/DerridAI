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

import { describe, expect, it } from "vitest";
import { createPdfExplorerCopy } from "../../src/domain/pdfExplorerCopy";

describe("PDF explorer copy module", () => {
  it("owns explorer strings so the Vue surface does not hardcode English", () => {
    const copy = createPdfExplorerCopy(
      (key, fallback = "") => (key === "pdf.explorer" ? "Explorateur PDF" : fallback),
      (_key, fallback, values = {}) =>
        Object.entries(values).reduce(
          (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
          fallback,
        ),
    );
    expect(copy.explorer).toBe("Explorateur PDF");
    expect(copy.pagesCount(3)).toBe("3 pages");
  });

  it("localizes extract fallbacks used by the live canvas renderer", () => {
    const copy = createPdfExplorerCopy(
      (key, fallback = "") =>
        key === "pdf.extract.file_gone"
          ? "Le fichier PDF n’est plus disponible dans cette session de navigateur."
          : fallback,
      (_key, fallback, values = {}) =>
        Object.entries(values).reduce(
          (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
          fallback,
        ),
    );
    expect(copy.fileGone).toBe(
      "Le fichier PDF n’est plus disponible dans cette session de navigateur.",
    );
    expect(copy.sourcePdfJsPage(4)).toBe("PDF.js (browser), page 4");
    expect(copy.pageMarker(2)).toBe("--- Page 2 ---");
  });
});

describe("LLM tool and record dialog markup", () => {
  it("owns job dialog toasts through copy, not hardcoded English", async () => {
    const { createJobDialogCopy } = await import("../../src/domain/jobDialogCopy");
    const copy = createJobDialogCopy(
      (key, fallback = "") =>
        key === "jobs.toast.configure_provider"
          ? "Configurez d’abord un fournisseur LLM"
          : fallback,
      (_key, fallback) => fallback,
    );
    expect(copy.configureProvider).toBe("Configurez d’abord un fournisseur LLM");
  });
});
