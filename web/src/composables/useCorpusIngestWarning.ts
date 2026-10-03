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

import { ref, type Ref } from "vue";
import {
  assetHasExtractionWarning,
  ingestWarningStorageKey,
  hideSourceWarnings,
  sourceWarningsHidden,
  type AssetQualityHint,
} from "../domain/sourceQuality";

export function useCorpusIngestWarning(asset: Ref<AssetQualityHint | null>) {
  const open = ref(false);
  function maybeOpen(nextAsset = asset.value) {
    if (!assetHasExtractionWarning(nextAsset) || !nextAsset?.asset_id) return;
    try {
      if (sourceWarningsHidden()) return;
      if (sessionStorage.getItem(ingestWarningStorageKey(nextAsset.asset_id))) return;
    } catch {
      // Private browsing still gets one in-memory acknowledgement per mount.
    }
    open.value = true;
  }

  function acknowledge(dontShowAgain = false) {
    const assetId = asset.value?.asset_id;
    try {
      if (dontShowAgain) hideSourceWarnings();
      if (assetId) {
        sessionStorage.setItem(ingestWarningStorageKey(assetId), "1");
      }
    } catch {
      // Browser storage is optional; closing the warning remains reliable.
    }
    open.value = false;
  }

  return { open, maybeOpen, acknowledge };
}
