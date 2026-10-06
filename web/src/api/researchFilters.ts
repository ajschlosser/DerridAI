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

import { apiRequest } from "./http";

export type ResearchFilterPreviewRequest = {
  collection: string;
  metadata_filter: Record<string, unknown> | null;
  document_filter: Record<string, unknown> | null;
  source?: "explicit" | "deterministic_natural_language" | "model_assisted";
  locales?: string[];
};

export type ResearchFilterDiagnostic = {
  code: string;
  params: Record<string, unknown>;
};

export type ResearchFilterPreview = {
  valid: boolean;
  fields_referenced: string[];
  collection_filter_fields: string[];
  unsupported_fields: string[];
  errors: ResearchFilterDiagnostic[];
  warnings: ResearchFilterDiagnostic[];
};

export type ResearchFilterInventory = {
  works: Array<{ work: string; authors: string[] }>;
  truncated: boolean;
};

/** Non-mutating server check of a filter against a collection's declared filter fields. */
export const researchFiltersApi = {
  preview: (body: ResearchFilterPreviewRequest, signal?: AbortSignal) =>
    apiRequest<ResearchFilterPreview>("/api/research/filters/preview", {
      method: "POST",
      body: JSON.stringify({ source: "explicit", ...body }),
      signal,
    }),
  /** Work/author names (no passages) used to resolve named scopes in instructions. */
  inventory: (body: { collection: string; locales?: string[] }, signal?: AbortSignal) =>
    apiRequest<ResearchFilterInventory>("/api/research/filters/inventory", {
      method: "POST",
      body: JSON.stringify(body),
      signal,
    }),
};
