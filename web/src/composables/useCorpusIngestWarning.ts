// Copyright 2026 Aaron John Schlosser, PhD.
import { ref, type Ref } from "vue";
import {
  assetHasExtractionWarning,
  ingestWarningStorageKey,
  type AssetQualityHint,
} from "../domain/sourceQuality";

export function useCorpusIngestWarning(asset: Ref<AssetQualityHint | null>) {
  const open = ref(false);
  const globalStorageKey = "derridai.pdf-corpus.hide-extraction-warnings";

  function maybeOpen(nextAsset = asset.value) {
    if (!assetHasExtractionWarning(nextAsset) || !nextAsset?.asset_id) return;
    try {
      if (localStorage.getItem(globalStorageKey) === "1") return;
      if (sessionStorage.getItem(ingestWarningStorageKey(nextAsset.asset_id))) return;
    } catch {
      // Private browsing still gets one in-memory acknowledgement per mount.
    }
    open.value = true;
  }

  function acknowledge(dontShowAgain = false) {
    const assetId = asset.value?.asset_id;
    try {
      if (dontShowAgain) localStorage.setItem(globalStorageKey, "1");
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
