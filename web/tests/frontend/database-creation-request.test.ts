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

import { describe, expect, it } from "vitest";
import { openDatabaseCreationFromResearch } from "../../src/domain/databaseCreationRequest";
import { vectorState } from "../../src/state/workspaceState";

describe("openDatabaseCreationFromResearch", () => {
  it("flags the request for the Databases view and navigates there", () => {
    const seen: CustomEvent[] = [];
    const listener = (event: Event) => seen.push(event as CustomEvent);
    window.addEventListener("derridai:navigate-native", listener);
    vectorState.vectorAutoCreateRequested = false;
    openDatabaseCreationFromResearch();
    window.removeEventListener("derridai:navigate-native", listener);

    expect(vectorState.vectorAutoCreateRequested).toBe(true);
    expect(seen).toHaveLength(1);
    expect(seen[0].detail).toEqual({ path: "/databases", runtimeView: "vector" });
    vectorState.vectorAutoCreateRequested = false;
  });
});
