/* Copyright 2026 Aaron John Schlosser, PhD. */

import type { SemanticMapSource } from "../domain/semanticMap";
import * as runtime from "../runtime/runtime.js";

export interface SemanticMapSourceSnapshot {
  records: SemanticMapSource[];
  focusId: string;
}

export interface SemanticMapService {
  listSources(): SemanticMapSourceSnapshot;
}

/**
 * Typed compatibility boundary for semantic-map source discovery.
 *
 * Views should depend on this service rather than the general runtime facade so
 * the source implementation can move without another component rewrite.
 */
export const semanticMapService: SemanticMapService = {
  listSources() {
    const result = runtime.listSemanticMapSources?.();
    return {
      records: Array.isArray(result?.records) ? result.records : [],
      focusId: String(result?.focusId || ""),
    };
  },
};
