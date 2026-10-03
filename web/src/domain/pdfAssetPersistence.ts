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

import { state } from "./sharedUrlState";
import { workspaceDb } from "./sharedWorkspaceStorage";

// The loaded PDF is kept in the browser-local "assets" store so a reload can restore it.
export async function persistCurrentPdfAsset() {
  if (!state.pdf.file) return;
  try {
    const blob =
      state.pdf.file instanceof Blob
        ? state.pdf.file
        : new Blob([await state.pdf.file.arrayBuffer()], { type: "application/pdf" });
    await workspaceDb.put("assets", {
      key: "current_pdf",
      blob,
      name: state.pdf.name || state.pdf.file.name || "current.pdf",
      title: state.pdf.title || "",
      author: state.pdf.author || "",
      page: state.pdf.page || 1,
      rotation: state.pdf.rotation || 0,
      text: state.pdf.text || "",
      search: state.pdf.search || "",
      relatedSearch: state.pdf.relatedSearch || "",
      extractionSource: state.pdf.extractionSource || "",
      extractError: state.pdf.extractError || "",
      saved_at: new Date().toISOString(),
    });
  } catch (error) {
    console.warn("Could not persist current PDF asset", error);
  }
}
