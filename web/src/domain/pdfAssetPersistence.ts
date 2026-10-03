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

import { getDocument } from "pdfjs-dist/legacy/build/pdf.mjs";
import { loadPdfMetadata } from "./pdfMetadata";
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

/** The record persistCurrentPdfAsset stores under "current_pdf". */
type PdfAsset = {
  blob?: Blob;
  name?: string;
  title?: string;
  author?: string;
  page?: number;
  rotation?: number;
  text?: string;
  search?: string;
  relatedSearch?: string;
  extractionSource?: string;
  extractError?: string;
};

// Reload the PDF kept by persistCurrentPdfAsset, if any.
export async function restoreCurrentPdfAsset() {
  try {
    const asset = (await workspaceDb.get("assets", "current_pdf")) as PdfAsset | undefined;
    if (!asset?.blob) return;
    const file = new File([asset.blob], asset.name || "restored.pdf", {
      type: asset.blob.type || "application/pdf",
    });
    const buffer = await file.arrayBuffer();
    if (state.pdf.url) URL.revokeObjectURL(state.pdf.url);
    state.pdf.file = file;
    state.pdf.url = URL.createObjectURL(new Blob([buffer], { type: "application/pdf" }));
    state.pdf.name = file.name;
    state.pdf.title = asset.title || file.name.replace(/\.pdf$/i, "");
    state.pdf.author = asset.author || "";
    state.pdf.page = Math.max(1, Number(asset.page) || 1);
    state.pdf.rotation = Number(asset.rotation || 0) % 360;
    state.pdf.text = String(asset.text || "");
    state.pdf.search = String(asset.search || "");
    state.pdf.relatedSearch = String(asset.relatedSearch || "");
    state.pdf.extractionSource = String(asset.extractionSource || "");
    state.pdf.extractError = String(asset.extractError || "");
    try {
      state.pdf.doc = await getDocument({ data: new Uint8Array(buffer.slice(0)) }).promise;
      const metadata = await loadPdfMetadata(state.pdf.doc, file.name);
      state.pdf.title = asset.title || metadata.title || state.pdf.title;
      state.pdf.author = asset.author || metadata.author || state.pdf.author;
      state.pdf.page = Math.min(state.pdf.page, state.pdf.doc.numPages || state.pdf.page);
    } catch (error) {
      state.pdf.doc = null;
      state.pdf.extractError = `Restored PDF.js initialization failed (${error instanceof Error ? error.message : String(error)}).`;
    }
  } catch (error) {
    console.warn("Could not restore current PDF asset", error);
  }
}
