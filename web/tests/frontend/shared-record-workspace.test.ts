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

import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/domain/sharedWorkspaceStorage", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  persistPrefs: vi.fn(),
}));
vi.mock("../../src/domain/sharedNavigation", async (importOriginal) => ({
  ...(await importOriginal<object>()),
  syncUrl: vi.fn(),
}));

import "../../src/domain/appBootstrap";
import { sharedPdfLinking } from "../../src/domain/sharedPdfLinking";
import { sharedRecordWorkspace } from "../../src/domain/sharedRecordWorkspace";
import { state } from "../../src/domain/sharedUrlState";

describe("shared Record workspace", () => {
  beforeEach(() => {
    Object.assign(state, { files: [], activeFileId: null, userContext: null });
  });

  it("reports no record when nothing is loaded, from the shared state alone", async () => {
    const snapshot = await sharedRecordWorkspace.getRecordWorkspaceSnapshot();
    expect(snapshot.available).toBe(false);
  });

  it("finds the selected local record and moves between records", async () => {
    state.files = [
      {
        id: "f1",
        name: "glas.jsonl",
        dirty: new Set(),
        records: [
          { record_id: "r1", text: "one" },
          { record_id: "r2", text: "two" },
        ],
      },
    ];
    state.activeFileId = "f1";
    state.selected = { f1: 0 };
    const first = await sharedRecordWorkspace.getRecordWorkspaceSnapshot();
    expect((first as { record?: { record_id?: string } }).record?.record_id).toBe("r1");
    const next = await sharedRecordWorkspace.recordWorkspaceNavigate(1);
    expect((next as { record?: { record_id?: string } }).record?.record_id).toBe("r2");
  });

  it("exposes the PDF linking surface the Record workspace depends on", () => {
    for (const name of ["linkPdfPage", "unlinkPdfLink", "unlinkAllPdfLinks", "pdfDisplayTitle"])
      expect(typeof (sharedPdfLinking as Record<string, unknown>)[name]).toBe("function");
  });
});
