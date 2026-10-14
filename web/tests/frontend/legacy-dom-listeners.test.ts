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

const searchByMetadata = vi.fn();
const importFiles = vi.fn();
vi.mock("../../src/domain/workspaceActions", () => ({
  searchByMetadata: (...args: unknown[]) => searchByMetadata(...args),
}));
vi.mock("../../src/domain/sharedFileLifecycle", () => ({
  importFiles: (...args: unknown[]) => importFiles(...args),
}));

import { wireMetadataSearchDelegation } from "../../src/domain/legacyDomListeners";
import { sessionState } from "../../src/state/workspaceState";

describe("legacy document listeners", () => {
  beforeEach(() => {
    searchByMetadata.mockReset();
    importFiles.mockReset();
    document.body.innerHTML = "";
  });

  it("shows a chart tooltip for an element carrying data-chart-tip", () => {
    document.body.innerHTML = '<span id="t" data-chart-tip="12 records"></span>';
    document
      .querySelector("#t")!
      .dispatchEvent(new MouseEvent("pointermove", { bubbles: true, clientX: 10, clientY: 10 }));
    const tip = document.querySelector(".chart-hover-tooltip");
    expect(tip?.textContent).toBe("12 records");
    expect(tip?.classList.contains("show")).toBe(true);
  });

  it("searches by metadata only for buttons inside #main, and wires once", () => {
    wireMetadataSearchDelegation();
    wireMetadataSearchDelegation();
    document.body.innerHTML =
      '<div id="main"><button id="in" data-meta-search-field="author" data-meta-search-value="Derrida" data-meta-search-contains="true"></button></div><button id="out" data-meta-search-field="a" data-meta-search-value="b"></button>';
    document.querySelector<HTMLElement>("#out")!.click();
    expect(searchByMetadata).not.toHaveBeenCalled();
    document.querySelector<HTMLElement>("#in")!.click();
    expect(searchByMetadata).toHaveBeenCalledTimes(1);
    expect(searchByMetadata).toHaveBeenCalledWith("author", "Derrida", { contains: true });
  });

  it("imports dropped JSON files for an administrator but never for a researcher", () => {
    const file = new File(["{}"], "records.jsonl");
    const drop = () => {
      const event = new Event("drop", { cancelable: true }) as Event & { dataTransfer: unknown };
      event.dataTransfer = { files: [file, new File(["x"], "notes.txt")] };
      window.dispatchEvent(event);
    };
    sessionState.userContext = { id: "r", role: "researcher" } as never;
    drop();
    expect(importFiles).not.toHaveBeenCalled();
    sessionState.userContext = { id: "a", role: "admin" } as never;
    drop();
    expect(importFiles).toHaveBeenCalledWith([file]);
  });
});
