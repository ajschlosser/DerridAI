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

import type { SemanticMapSource } from "../domain/semanticMap";
import { listSemanticMapSources } from "../domain/semanticMapSources";

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
    const result = listSemanticMapSources();
    return {
      records: Array.isArray(result?.records) ? result.records : [],
      focusId: String(result?.focusId || ""),
    };
  },
};
