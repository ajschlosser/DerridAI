/* Copyright 2026 Aaron John Schlosser, PhD. */
/**
 * Read-only SourceDocument intelligence over the typed GraphQL façade.
 * Commands and uploads stay in api/corpus; this module only reads.
 */
import { execute, type ExecuteOptions } from "../../../api/graphql/client";
import {
  SourceDocumentInspectorDocument,
  SourceDocumentPreviewDocument,
} from "../../../api/graphql/generated";
import type { SourceDetail } from "../../../api/corpus";

export async function sourceDocumentDetail(
  sourceDocumentId: string,
  options: ExecuteOptions = {},
): Promise<SourceDetail> {
  const data = await execute(
    SourceDocumentInspectorDocument,
    { source_document_id: sourceDocumentId },
    options,
  );
  const source = data.source_document;
  return {
    asset_id: source.source_document_id,
    sha256: source.sha256,
    filename: source.filename,
    created_at: source.created_at || "",
    media_type: source.media_type,
    media_kind: source.media_kind,
    content_suffix: source.content_suffix,
    source_url: source.source_url,
    page_count: source.page_count,
    block_count: source.source_unit_count,
    ocr_pages: source.ocr_pages,
    extraction_provenance: (source.extraction_provenance || {}) as Record<string, unknown>,
    catalog_metadata: (source.catalog_metadata || {}) as Record<string, unknown>,
    initial_metadata: (source.initial_metadata || {}) as Record<string, string | number | null>,
    derived_from_asset_id: source.derived_from_source_document_id,
    captures: source.captures,
    builds: source.builds,
  };
}

export async function sourceDocumentPreview(
  sourceDocumentId: string,
  limit = 8,
  options: ExecuteOptions = {},
): Promise<Array<{ block_id: string; text: string }>> {
  const data = await execute(
    SourceDocumentPreviewDocument,
    { source_document_id: sourceDocumentId, limit },
    options,
  );
  return data.source_document.source_units.items.map((item) => ({
    block_id: item.source_unit_id,
    text: item.text,
  }));
}
