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

export function recordHasSourceWarning(
  record?: { source_quality_issues?: unknown[] } | null,
): boolean {
  return Boolean(record?.source_quality_issues?.length);
}

export function firstRecordWithSourceWarning<T extends { source_quality_issues?: unknown[] }>(
  records: T[],
): T | undefined {
  return records.find((record) => recordHasSourceWarning(record));
}

export const SOURCE_WARNING_HIDE_KEY = "derridai.pdf-corpus.hide-extraction-warnings";

export function sourceWarningsHidden(): boolean {
  try {
    return localStorage.getItem(SOURCE_WARNING_HIDE_KEY) === "1";
  } catch {
    return false;
  }
}

export function hideSourceWarnings(): void {
  try {
    localStorage.setItem(SOURCE_WARNING_HIDE_KEY, "1");
  } catch {
    // Browser storage is optional; the current dialog can still close.
  }
}

export function ingestWarningStorageKey(assetId: string): string {
  return `derridai.source-quality.seen.${assetId}`;
}
