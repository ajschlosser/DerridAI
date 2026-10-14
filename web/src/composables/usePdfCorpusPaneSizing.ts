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

import { ref } from "vue";
import { useSplitter } from "./useSplitter";

/**
 * Owns the persistent review workspace pane sizes used by PdfCorpusBuilder.
 *
 * The splitters share one grid container because their pointer measurements
 * must use the same writing direction and outer bounds.
 */
export function usePdfCorpusPaneSizing() {
  const reviewGridEl = ref<HTMLElement | null>(null);
  const container = () => reviewGridEl.value;

  const queueSplitter = useSplitter({
    key: "derridai.review.queueWidth",
    min: 224,
    max: 420,
    initial: 256,
    edge: "start",
    container,
  });
  const inspectorSplitter = useSplitter({
    key: "derridai.review.inspectorWidth",
    min: 320,
    max: 640,
    initial: 368,
    edge: "end",
    container,
  });
  const reviewHeightSplitter = useSplitter({
    key: "derridai.review.height",
    min: 420,
    max: 1200,
    initial: 680,
    edge: "start",
    axis: "vertical",
    container,
  });

  return {
    reviewGridEl,
    queueSplitter,
    inspectorSplitter,
    reviewHeightSplitter,
  };
}
