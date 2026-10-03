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

import { computed, type Ref } from "vue";
import {
  corpusBuilderApi,
  type CorpusRecord,
  type PdfAsset,
  type SourceBlock,
} from "../../../api/corpus";
import { sourceMediaCapabilities } from "../../../domain/sourceMedia";

interface CorpusSourceViewOptions {
  selectedAsset: Readonly<Ref<PdfAsset | undefined | null>>;
  selectedAssetId: Readonly<Ref<string>>;
  selectedRecord: Readonly<Ref<CorpusRecord | null>>;
  selectedPdfPage: Readonly<Ref<number>>;
  visibleBlocks: Readonly<Ref<SourceBlock[]>>;
  evidenceBlockIds: Readonly<Ref<Set<string>>>;
}

/**
 * What the source inspector needs to show: which viewers apply to the source's medium, where its bytes
 * are served from, and the page/block slice for the selected Record. Read-only derivation; PDF pages
 * only exist for media with printed pagination, so other media never inherit page semantics.
 */
export function useCorpusSourceView(options: CorpusSourceViewOptions) {
  const selectedSourceCapabilities = computed(() =>
    sourceMediaCapabilities(options.selectedAsset.value?.media_kind),
  );
  // Printed-page mapping is a source capability, not a synonym for "has pages".
  const paginatedSource = computed(() => selectedSourceCapabilities.value.printedPagination);
  const contentUrl = (applies: boolean) =>
    applies && options.selectedAssetId.value
      ? corpusBuilderApi.assetContentUrl(options.selectedAssetId.value)
      : "";
  const imageSourceUrl = computed(() => contentUrl(selectedSourceCapabilities.value.imageViewer));
  const audioSourceUrl = computed(() => contentUrl(selectedSourceCapabilities.value.audioPlayer));
  const sourcePdfUrl = computed(() => contentUrl(selectedSourceCapabilities.value.pdfViewer));
  const recordPdfPages = computed(() =>
    Array.from(
      new Set(
        (options.selectedRecord.value?.pdf_pages || []).map(Number).filter((value) => value > 0),
      ),
    ).sort((a, b) => a - b),
  );
  const selectedPdfPageIndex = computed(() =>
    Math.max(0, recordPdfPages.value.indexOf(options.selectedPdfPage.value)),
  );
  const selectedPageMeta = computed(
    () =>
      options.selectedAsset.value?.pages?.find(
        (page) => Number(page.pdf_page) === Number(options.selectedPdfPage.value),
      ) || null,
  );
  const selectedPageBlocks = computed(() =>
    options.visibleBlocks.value.filter(
      (block) =>
        !paginatedSource.value || Number(block.page) === Number(options.selectedPdfPage.value),
    ),
  );
  const evidenceIdsArray = computed(() => Array.from(options.evidenceBlockIds.value));
  return {
    selectedSourceCapabilities,
    paginatedSource,
    imageSourceUrl,
    audioSourceUrl,
    sourcePdfUrl,
    recordPdfPages,
    selectedPdfPageIndex,
    selectedPageMeta,
    selectedPageBlocks,
    evidenceIdsArray,
  };
}
