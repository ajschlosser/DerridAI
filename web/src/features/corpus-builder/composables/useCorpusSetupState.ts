/* Copyright 2026 Aaron John Schlosser, PhD. */
import { computed, type Ref } from "vue";
import type { CorpusBuild, PdfAsset } from "../../../api/corpus";
import {
  corpusSetupIssues,
  corpusSetupSectionStates,
  type CorpusSetupInput,
  type CorpusSetupSectionId,
} from "../domain/setupState";
import {
  corpusPrimaryStatus,
  corpusWorkflowSteps,
  type PresentationText,
} from "../domain/workflowPresentation";
import type { CorpusWorkspace } from "../domain/workspace";

type Readable<T> = Readonly<Ref<T>>;

interface CorpusSetupStateOptions {
  text: PresentationText;
  currentBuild: Readable<CorpusBuild | null>;
  selectedAsset: Readable<PdfAsset | undefined | null>;
  workspaceMode: Readable<CorpusWorkspace>;
  hasRecordTopology: Readable<boolean>;
  canStart: Readable<boolean>;
  expandedSection: Ref<CorpusSetupSectionId | "">;
  /** The setup facts, read as one snapshot so the section states cannot disagree with each other. */
  setupFacts: () => Omit<CorpusSetupInput, "asset">;
}

/**
 * Derived UI state for Setup and the workflow header: structured issues, per-section status,
 * the lifecycle badge and the four workflow steps. Read-only interpretation; it changes no build state.
 */
export function useCorpusSetupState(options: CorpusSetupStateOptions) {
  const setupInput = computed<CorpusSetupInput>(() => {
    const asset = options.selectedAsset.value;
    return {
      ...options.setupFacts(),
      asset: asset
        ? {
            filename: asset.filename,
            media_kind: asset.media_kind,
            page_count: asset.page_count,
            block_count: asset.block_count,
            duration_seconds: asset.audio_provenance?.duration_seconds,
          }
        : null,
    };
  });
  const setupIssues = computed(() => corpusSetupIssues(setupInput.value, options.text));
  const setupSections = computed(() =>
    corpusSetupSectionStates(setupInput.value, setupIssues.value, options.text),
  );
  const primaryStatus = computed(() =>
    corpusPrimaryStatus(options.currentBuild.value, options.text),
  );
  const workflowSteps = computed(() =>
    corpusWorkflowSteps(
      options.workspaceMode.value,
      {
        hasBuild: Boolean(options.currentBuild.value),
        hasRecordTopology: options.hasRecordTopology.value,
      },
      {
        build: options.currentBuild.value,
        hasSource: Boolean(options.selectedAsset.value),
        setupCanStart: options.canStart.value,
        hasRecordTopology: options.hasRecordTopology.value,
      },
    ),
  );
  function toggleSetupSection(section: CorpusSetupSectionId) {
    options.expandedSection.value = options.expandedSection.value === section ? "" : section;
  }
  function openSetupSection(section: CorpusSetupSectionId) {
    options.expandedSection.value = section;
  }
  return {
    setupIssues,
    setupSections,
    primaryStatus,
    workflowSteps,
    toggleSetupSection,
    openSetupSection,
  };
}
