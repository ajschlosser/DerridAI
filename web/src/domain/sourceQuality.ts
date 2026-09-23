/* Copyright 2026 Aaron John Schlosser, PhD. */

export type ExtractionNoise = {
  page_count?: number;
  unusable_page_count?: number;
  unusable_page_ratio?: number;
  median_noise?: number | null;
  threshold?: number;
  exceeds_threshold?: boolean;
  pages?: Array<{ page?: number; score?: number; unusable?: boolean; reasons?: string[] }>;
};

export type AssetQualityHint = {
  asset_id?: string;
  extraction_noise?: ExtractionNoise;
  source_quality?: {
    blocking_page_count?: number;
    warning_page_count?: number;
  };
};

export function assetHasExtractionWarning(asset?: AssetQualityHint | null): boolean {
  if (!asset) return false;
  if (asset.extraction_noise?.exceeds_threshold) return true;
  const blocking = Number(asset.source_quality?.blocking_page_count || 0);
  const warning = Number(asset.source_quality?.warning_page_count || 0);
  return blocking > 0 || warning > 0;
}

export function recordHasSourceWarning(record?: { source_quality_issues?: unknown[] } | null): boolean {
  return Boolean(record?.source_quality_issues?.length);
}

export function firstRecordWithSourceWarning<T extends { source_quality_issues?: unknown[] }>(
  records: T[],
): T | undefined {
  return records.find((record) => recordHasSourceWarning(record));
}

export function ingestWarningStorageKey(assetId: string): string {
  return `derridai.source-quality.seen.${assetId}`;
}
