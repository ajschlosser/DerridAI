/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, ref, type Ref } from "vue";
import {
  corpusBuilderApi,
  type DocumentLayoutPlan,
  type GutenbergHit,
  type WikisourceHit,
  type GutenbergStatus,
  type PdfAsset,
  type PageDetectionRequest,
  type SourceUnitPolicy,
} from "../../../api/corpus";
import { useI18nStore } from "../../../stores/i18n";

type MessageTone = "error" | "notice";

export function useCorpusSourceConfiguration(
  busy: Ref<string>,
  setMessage: (message: string, tone?: MessageTone) => void,
  providerProfileId: () => string = () => "",
  /** The selected profile's connection (provider, model, endpoint, key), as a build request carries it. */
  providerConnection: (profileId: string) => Record<string, unknown> | null = () => null,
) {
  const i18n = useI18nStore();
  const assets = ref<PdfAsset[]>([]);
  const selectedAssetId = ref("");
  const sourceIllegibility = ref(0);
  // Printed page numbers in text sources are detected deterministically unless turned off.
  const detectPageNumbers = ref(true);
  // If none are found, a model may pick candidate lines (its answer is still verified deterministically).
  const llmPageDetection = ref(true);
  function pageDetection(): PageDetectionRequest {
    if (!detectPageNumbers.value) return { mode: "off" };
    const profile = providerProfileId();
    if (!llmPageDetection.value || !profile) return { mode: "auto" };
    const config = providerConnection(profile) || {};
    const text = (value: unknown) => (typeof value === "string" && value ? value : undefined);
    return {
      mode: "auto_llm",
      providerProfileId: profile,
      connection: {
        provider: text(config.provider),
        model: text(config.model),
        base_url: text(config.base_url),
        api_key: text(config.api_key),
      },
    };
  }
  const sourceUrl = ref("");
  const gutenbergQuery = ref("");
  const gutenbergHits = ref<GutenbergHit[]>([]);
  const wikisourceHits = ref<WikisourceHit[]>([]);
  // Digital-library search state, shown inside the search dialog rather than behind it.
  const wikisourceLanguage = ref(String(i18n.locale || "en").slice(0, 2) === "fr" ? "fr" : "en");
  const librarySearched = ref<{ gutenberg: string; wikisource: string }>({
    gutenberg: "",
    wikisource: "",
  });
  const libraryError = ref("");
  /** The result being imported: `gutenberg:<id>` or `wikisource:<url>`. */
  const libraryImporting = ref("");
  /** Increments after each successful library import, so the dialog can close. */
  const libraryImported = ref(0);
  let searchTicket = 0;
  const gutenbergStatus = ref<GutenbergStatus | null>(null);
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

  function rememberAsset(asset: PdfAsset, ingested = false) {
    assets.value = assets.value.map((item) => (item.asset_id === asset.asset_id ? asset : item));
    if (!assets.value.some((item) => item.asset_id === asset.asset_id)) assets.value.push(asset);
    selectedAssetId.value = asset.asset_id;
    if (ingested) lastIngestedAsset.value = asset;
  }

  async function upload(file?: File | null) {
    if (!file) return;
    busy.value = "upload";
    setMessage("");
    try {
      const asset = await corpusBuilderApi.uploadAsset(
        file,
        "auto",
        sourceIllegibility.value,
        pageDetection(),
      );
      await refreshAssets();
      rememberAsset(asset, true);
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

  /** Switch the selected source to one whose evidence units follow `policy` (the original is kept). */
  async function applyUnitPolicy(policy: SourceUnitPolicy) {
    if (!selectedAssetId.value) return;
    busy.value = "units";
    setMessage("");
    try {
      const asset = await corpusBuilderApi.deriveUnits(selectedAssetId.value, policy);
      await refreshAssets();
      rememberAsset(asset);
      setMessage(i18n.tf("pdf_corpus.units_applied", { count: asset.block_count }));
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
      const asset = await corpusBuilderApi.importUrl(
        url,
        sourceIllegibility.value,
        pageDetection(),
      );
      await refreshAssets();
      rememberAsset(asset, true);
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  /** Import a Wikisource work or part chosen in the search dialog; errors stay in the dialog. */
  async function importLibraryUrl(url: string) {
    if (!url || libraryImporting.value) return;
    libraryImporting.value = `wikisource:${url}`;
    libraryError.value = "";
    busy.value = "upload";
    try {
      const asset = await corpusBuilderApi.importUrl(
        url,
        sourceIllegibility.value,
        pageDetection(),
      );
      await refreshAssets();
      rememberAsset(asset, true);
      libraryImported.value += 1;
    } catch (exc) {
      libraryError.value = exc instanceof Error ? exc.message : String(exc);
    } finally {
      libraryImporting.value = "";
      busy.value = "";
    }
  }

  // Searches run as the reviewer types, so an older, slower answer must never replace a newer one.
  async function searchGutenberg() {
    const query = gutenbergQuery.value.trim();
    const ticket = ++searchTicket;
    libraryError.value = "";
    if (!query) {
      gutenbergHits.value = [];
      librarySearched.value = { ...librarySearched.value, gutenberg: "" };
      return;
    }
    busy.value = "gutenberg";
    try {
      const result = await corpusBuilderApi.searchGutenberg(query);
      if (ticket !== searchTicket) return;
      gutenbergHits.value = result.items || [];
      librarySearched.value = { ...librarySearched.value, gutenberg: query };
    } catch (exc) {
      if (ticket === searchTicket)
        libraryError.value = exc instanceof Error ? exc.message : String(exc);
    } finally {
      if (busy.value === "gutenberg") busy.value = "";
    }
  }

  async function searchWikisource() {
    const query = gutenbergQuery.value.trim();
    const ticket = ++searchTicket;
    libraryError.value = "";
    if (!query) {
      wikisourceHits.value = [];
      librarySearched.value = { ...librarySearched.value, wikisource: "" };
      return;
    }
    busy.value = "wikisource";
    try {
      const result = await corpusBuilderApi.searchWikisource(query, wikisourceLanguage.value);
      if (ticket !== searchTicket) return;
      wikisourceHits.value = result.items || [];
      librarySearched.value = { ...librarySearched.value, wikisource: query };
    } catch (exc) {
      if (ticket === searchTicket)
        libraryError.value = exc instanceof Error ? exc.message : String(exc);
    } finally {
      if (busy.value === "wikisource") busy.value = "";
    }
  }

  async function refreshGutenbergStatus() {
    try {
      gutenbergStatus.value = await corpusBuilderApi.gutenbergStatus();
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    }
  }

  async function refreshGutenbergCatalogue() {
    busy.value = "gutenberg-catalogue";
    try {
      gutenbergStatus.value = await corpusBuilderApi.refreshGutenbergCatalogue();
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function updateGutenbergArchive(action: "start" | "pause" | "resume" | "refetch") {
    busy.value = "gutenberg-archive";
    try {
      gutenbergStatus.value = await corpusBuilderApi.gutenbergArchiveAction(action);
    } catch (exc) {
      setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      busy.value = "";
    }
  }

  async function importGutenberg(etextId: number) {
    if (libraryImporting.value) return;
    libraryImporting.value = `gutenberg:${etextId}`;
    libraryError.value = "";
    busy.value = "upload";
    try {
      const asset = await corpusBuilderApi.importGutenberg(
        etextId,
        sourceIllegibility.value,
        pageDetection(),
      );
      await refreshAssets();
      rememberAsset(asset, true);
      libraryImported.value += 1;
    } catch (exc) {
      libraryError.value = exc instanceof Error ? exc.message : String(exc);
    } finally {
      libraryImporting.value = "";
      busy.value = "";
    }
  }

  async function savePageLabels(labels: Record<number, string | null>) {
    if (!selectedAssetId.value || !Object.keys(labels).length) return;
    busy.value = "page-labels";
    try {
      const asset = await corpusBuilderApi.updatePageLabels(selectedAssetId.value, labels);
      rememberAsset(asset, true);
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
    detectPageNumbers,
    llmPageDetection,
    sourceUrl,
    gutenbergQuery,
    gutenbergHits,
    wikisourceHits,
    wikisourceLanguage,
    librarySearched,
    libraryError,
    libraryImporting,
    libraryImported,
    importLibraryUrl,
    gutenbergStatus,
    lastIngestedAsset,
    refreshAssets,
    upload,
    applyUnitPolicy,
    loadSourceUrl,
    searchGutenberg,
    searchWikisource,
    refreshGutenbergStatus,
    refreshGutenbergCatalogue,
    updateGutenbergArchive,
    importGutenberg,
    savePageLabels,
    saveDocumentLayout,
  };
}
