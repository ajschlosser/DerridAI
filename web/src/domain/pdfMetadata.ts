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

// Title and author of an opened PDF.js document, falling back to the file name.
type PdfDocumentLike = {
  getMetadata(): Promise<{
    info?: Record<string, unknown>;
    metadata?: { get?(name: string): unknown };
  }>;
};

export async function loadPdfMetadata(doc: unknown, fileName: unknown) {
  const fallback = String(fileName || "").replace(/\.pdf$/i, "");
  if (!doc) return { title: fallback, author: "" };
  try {
    const metadata = await (doc as PdfDocumentLike).getMetadata();
    const info = metadata?.info || {};
    const xmp = metadata?.metadata;
    const title = String(
      info.Title || xmp?.get?.("dc:title") || xmp?.get?.("pdf:title") || fallback || "",
    ).trim();
    const author = String(
      info.Author || xmp?.get?.("dc:creator") || xmp?.get?.("pdf:author") || "",
    ).trim();
    return { title: title || fallback, author };
  } catch (error) {
    console.warn("Could not read PDF metadata", error);
    return { title: fallback, author: "" };
  }
}
