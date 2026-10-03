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
    captures: source.captures.map((capture) => ({
      ...capture,
      discovery_method: capture.discovery_method || "",
      acquired_at: capture.acquired_at || "",
    })),
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
