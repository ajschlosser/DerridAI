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
import { corpusReviewCommandFromKeydown } from "../../src/features/corpus-builder/domain/reviewCommands";

function keydown(key: string, init: KeyboardEventInit = {}) {
  return new KeyboardEvent("keydown", { key, ...init });
}

describe("Corpus Builder review commands", () => {
  it.each([
    ["a", "accept"],
    ["r", "reject"],
    ["n", "needs-attention"],
    ["j", "next"],
    ["ArrowDown", "next"],
    ["k", "previous"],
    ["ArrowUp", "previous"],
    ["z", "undo"],
    ["f", "focus"],
    ["m", "metadata"],
  ])("maps %s to %s", (key, command) => {
    expect(corpusReviewCommandFromKeydown(keydown(key))).toBe(command);
  });

  it("maps shift+z to redo", () => {
    expect(corpusReviewCommandFromKeydown(keydown("z", { shiftKey: true }))).toBe("redo");
  });

  it("ignores modified shortcuts", () => {
    expect(corpusReviewCommandFromKeydown(keydown("a", { ctrlKey: true }))).toBeNull();
    expect(corpusReviewCommandFromKeydown(keydown("a", { metaKey: true }))).toBeNull();
    expect(corpusReviewCommandFromKeydown(keydown("a", { altKey: true }))).toBeNull();
  });

  it("does not execute shortcuts in editable controls", () => {
    const input = document.createElement("input");
    const event = keydown("a");
    Object.defineProperty(event, "target", { value: input });
    expect(corpusReviewCommandFromKeydown(event)).toBeNull();

    const editor = document.createElement("div");
    editor.setAttribute("contenteditable", "true");
    const editorEvent = keydown("r");
    Object.defineProperty(editorEvent, "target", { value: editor });
    expect(corpusReviewCommandFromKeydown(editorEvent)).toBeNull();
  });
});
