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

// Read-only GraphQL client for the vector-store Data tab. Replaces the old REST
// GET /api/stores/{name}/records, which shipped full Records for a 4-column table.
import { execute } from "../../../api/graphql/client";
import { VectorStoreBrowseDocument } from "../../../api/graphql/generated";

export interface VectorBrowseRow {
  chroma_id: string;
  record_id: string | null;
  work: string | null;
  page_start: string | null;
  page_end: string | null;
  text_preview: string;
}

export interface VectorBrowseWork {
  work: string;
  count: number;
  total_words?: number;
  average_record_length?: number;
}

export interface VectorBrowsePage {
  rows: VectorBrowseRow[];
  total: number;
}

export interface VectorBrowseResult {
  works: VectorBrowseWork[];
  page?: VectorBrowsePage;
}

export interface VectorBrowseOptions {
  includeRecords: boolean;
  offset: number;
  limit: number;
  work?: string;
  signal?: AbortSignal;
}

export const vectorBrowseReads = {
  async browse(name: string, options: VectorBrowseOptions): Promise<VectorBrowseResult> {
    const { vector_store } = await execute(
      VectorStoreBrowseDocument,
      {
        name,
        includeRecords: options.includeRecords,
        offset: options.offset,
        limit: options.limit,
        work: options.work || null,
      },
      { signal: options.signal },
    );
    return {
      works: vector_store.works,
      page: vector_store.records
        ? {
            rows: vector_store.records.items.filter(
              (row: VectorBrowseRow | null): row is VectorBrowseRow => row != null,
            ),
            total: vector_store.records.count,
          }
        : undefined,
    };
  },
};
