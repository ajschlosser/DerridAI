/* Copyright 2026 Aaron John Schlosser, PhD. */
import { ref, type Ref } from "vue";
import { corpusBuilderApi, type CorpusBuild, type CorpusRecord } from "../../../api/corpus";

type MessageTone = "error" | "notice";

export interface JsonlPreviewState {
  jsonl: string;
  validation_errors: string[];
  unresolved_fields: string[];
  would_publish: boolean;
}

export function useCorpusPublication(options: {
  currentBuild: Ref<CorpusBuild | null>;
  selectedRecord: Ref<CorpusRecord | null>;
  busy: Ref<string>;
  setMessage: (message: string, tone?: MessageTone) => void;
  refreshBuild: () => Promise<void>;
  refreshBuilds: () => Promise<void>;
  t: (key: string, fallback?: string) => string;
  tf: (key: string, values: Record<string, string | number>) => string;
}) {
  const jsonlPreviewOpen = ref(false);
  const jsonlPreview = ref<JsonlPreviewState>({
    jsonl: "",
    validation_errors: [],
    unresolved_fields: [],
    would_publish: false,
  });

  async function openJsonlPreview() {
    if (!options.currentBuild.value || !options.selectedRecord.value) return;
    options.busy.value = "preview";
    try {
      const result = await corpusBuilderApi.previewRecord(
        options.currentBuild.value.build_id,
        options.selectedRecord.value.record_id,
      );
      jsonlPreview.value = {
        jsonl: result.jsonl,
        validation_errors: result.validation_errors || [],
        unresolved_fields: result.unresolved_fields || [],
        would_publish: Boolean(result.would_publish),
      };
      jsonlPreviewOpen.value = true;
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
    } finally {
      options.busy.value = "";
    }
  }

  async function publish(
    publishOptions: { download?: boolean; automatic?: boolean } = {},
  ) {
    if (!options.currentBuild.value) return null;
    options.busy.value = "publish";
    try {
      const result = await corpusBuilderApi.publish(options.currentBuild.value.build_id);
      await options.refreshBuild();
      await options.refreshBuilds();
      options.setMessage(
        publishOptions.automatic
          ? options.tf("pdf_corpus.auto_published", { count: result.record_count })
          : options.tf("pdf_corpus.published", {
              count: result.record_count,
              hash: result.sha256.slice(0, 12),
            }),
      );
      if (publishOptions.download) {
        window.location.href = corpusBuilderApi.publicationUrl(result.publication_id);
      }
      return result;
    } catch (exc) {
      options.setMessage(exc instanceof Error ? exc.message : String(exc), "error");
      return null;
    } finally {
      options.busy.value = "";
    }
  }

  return {
    jsonlPreviewOpen,
    jsonlPreview,
    openJsonlPreview,
    publish,
  };
}
