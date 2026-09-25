/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type Ref } from "vue";
import {
  corpusBuilderApi,
  type DocumentLayoutPlan,
  type GutenbergHit,
  type PdfAsset,
} from "../../../api/corpus";
import { useI18nStore } from "../../../stores/i18n";

type MessageTone = "error" | "notice";

export function useCorpusSourceConfiguration(
  busy: Ref<string>,
  setMessage: (message: string, tone?: MessageTone) => void,
) {
  const i18n = useI18nStore();
  const assets = ref<PdfAsset[]>([]);
  const selectedAssetId = ref("");
  const sourceIllegibility = ref(0);
  const sourceUrl = ref("");
  const gutenbergQuery = ref("");
  const gutenbergHits = ref<GutenbergHit[]>([]);
  const lastIngestedAsset = ref<PdfAsset | null>(null);

  const selectedAsset = computed(
    () => assets.value.find((item) => item.asset_id === selectedAssetId.value) || null,
  );

  async function refreshAssets() {
    assets.value = (await corpusBuilderApi.listAssets()).items;
    if (
      selectedAssetId.value &&
      !assets.value.some((item) => item.asset_id === selectedAssetId.value)
    )
      selectedAssetId.value = "";
  }

  function rememberAsset(asset: PdfAsset) {
    assets.value = assets.value.map((item) => (item.asset_id === asset.asset_id ? asset : item));
    if (!assets.value.some((item) => item.asset_id === asset.asset_id)) assets.value.push(asset);
    selectedAssetId.value = asset.asset_id;
    lastIngestedAsset.value = asset;
  }

  async function upload(file?: File | null) {
    if (!file) return;
    busy.value = "upload";
    setMessage("");
    try {
      const asset = await corpusBuilderApi.uploadAsset(file, "auto", sourceIllegibility.value);
      await refreshAssets();
      rememberAsset(asset);
      setMessage(
        i18n.tf("pdf_corpus.source_ingested_blocks", {
          blocks: asset.block_count,
        }),
      );
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function loadSourceUrl() {
    const url = sourceUrl.value.trim();
    if (!url) return;
    busy.value = "upload";
    setMessage("");
    try {
      const asset = await corpusBuilderApi.importUrl(url, sourceIllegibility.value);
      await refreshAssets();
      rememberAsset(asset);
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function searchGutenberg() {
    const query = gutenbergQuery.value.trim();
    if (!query) {
      gutenbergHits.value = [];
      return;
    }
    busy.value = "gutenberg";
    setMessage("");
    try {
      const result = await corpusBuilderApi.searchGutenberg(query);
      gutenbergHits.value = result.items || [];
      if (!gutenbergHits.value.length) setMessage(i18n.t("pdf_corpus.gutenberg_empty"));
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function importGutenberg(etextId: number) {
    busy.value = "upload";
    setMessage("");
    try {
      const asset = await corpusBuilderApi.importGutenberg(etextId, sourceIllegibility.value);
      await refreshAssets();
      rememberAsset(asset);
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function savePageLabels(labels: Record<number, string | null>) {
    if (!selectedAssetId.value || !Object.keys(labels).length) return;
    busy.value = "page-labels";
    try {
      const asset = await corpusBuilderApi.updatePageLabels(selectedAssetId.value, labels);
      rememberAsset(asset);
      setMessage(i18n.t("pdf_corpus.page_mapping_saved"));
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function saveDocumentLayout(plan: DocumentLayoutPlan) {
    if (!selectedAssetId.value) return;
    busy.value = "document-layout";
    try {
      const asset = await corpusBuilderApi.updateDocumentLayout(selectedAssetId.value, plan);
      rememberAsset(asset);
      const mapped = (asset.pages || []).filter(
        (page) =>
          Boolean(String(page.printed_page_label ?? "").trim()) ||
          (page.logical_pages || []).some((item) =>
            Boolean(String(item.printed_page_label ?? "").trim()),
          ),
      ).length;
      const exceptions = (asset.pages || []).filter((page) =>
        String(page.printed_page_label_source || "").includes("override"),
      ).length;
      setMessage(
        i18n.tf("pdf_corpus.document_structure_saved_impact", {
          mapped,
          total: asset.page_count,
          exceptions,
        }),
      );
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  return {
    assets,
    selectedAssetId,
    selectedAsset,
    sourceIllegibility,
    sourceUrl,
    gutenbergQuery,
    gutenbergHits,
    lastIngestedAsset,
    refreshAssets,
    upload,
    loadSourceUrl,
    searchGutenberg,
    importGutenberg,
    savePageLabels,
    saveDocumentLayout,
  };
}
