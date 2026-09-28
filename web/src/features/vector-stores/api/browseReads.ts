// Copyright 2026 Aaron John Schlosser, PhD.
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
