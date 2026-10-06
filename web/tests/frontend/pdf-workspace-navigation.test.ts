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
import {
  queryForPdfWorkspace,
  queryForPdfWorkspaceTransition,
} from "../../src/domain/pdfWorkspaceNavigation";

describe("PDF workspace route-state boundaries", () => {
  const mixed = {
    workspace: "review",
    build: "build-1",
    queue: "metadata",
    record: "record-42",
    sources: "source-a,source-b",
    file: "local-file",
    pdfpage: "12",
    ts: "compressed-table-state",
    mode: "builder",
    unrelated: "drop-me",
  };

  it("keeps only Corpus Builder state when entering Builder", () => {
    expect(queryForPdfWorkspace("builder", mixed)).toEqual({
      workspace: "review",
      build: "build-1",
      queue: "metadata",
      record: "record-42",
      sources: "source-a,source-b",
    });
  });

  it("keeps only Source Explorer state within Explorer", () => {
    expect(queryForPdfWorkspace("explorer", mixed)).toEqual({
      record: "record-42",
      file: "local-file",
      pdfpage: "12",
      ts: "compressed-table-state",
    });
  });

  it("drops the ambiguous record key when crossing between Builder and Explorer", () => {
    expect(queryForPdfWorkspaceTransition("builder", "explorer", mixed)).toEqual({
      file: "local-file",
      pdfpage: "12",
      ts: "compressed-table-state",
    });
    expect(
      queryForPdfWorkspaceTransition("explorer", "builder", {
        ...mixed,
        record: "7",
      }),
    ).toEqual({
      workspace: "review",
      build: "build-1",
      queue: "metadata",
      sources: "source-a,source-b",
    });
  });

  it("never preserves the obsolete mode query", () => {
    expect(queryForPdfWorkspace("builder", { mode: "builder" })).toEqual({});
    expect(queryForPdfWorkspace("explorer", { mode: "explorer" })).toEqual({});
  });
});
