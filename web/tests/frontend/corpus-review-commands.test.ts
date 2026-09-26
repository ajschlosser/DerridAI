/* Copyright 2026 Aaron John Schlosser, PhD. */
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
