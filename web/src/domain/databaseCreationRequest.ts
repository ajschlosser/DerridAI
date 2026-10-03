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

import { vectorState } from "../state/workspaceState";

// Ask the Databases view to open its creation wizard. Research, Search and the dashboard call this when the corpus has
// no database yet; the flag is consumed (and cleared) by VectorStoresView once it mounts.
export function openDatabaseCreationFromResearch() {
  vectorState.vectorAutoCreateRequested = true;
  window.dispatchEvent(
    new CustomEvent("derridai:navigate-native", {
      detail: { path: "/databases", runtimeView: "vector" },
    }),
  );
}
