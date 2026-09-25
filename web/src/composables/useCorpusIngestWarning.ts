// Copyright 2026 Aaron John Schlosser, PhD.
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
