// Copyright 2026 Aaron John Schlosser, PhD.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import SourceTranscriptionDialog from "../../src/components/SourceTranscriptionDialog.vue";
import { useI18nStore } from "../../src/stores/i18n";

const blocks = [
  {
    block_id: "audio-1",
    page: 1,
    bbox: [],
    type: "paragraph",
    text: "Bonjour depuis l'archive.",
    extraction_method: "whisper",
    confidence: 0.81,
    start: 1,
    end: 3,
    speaker: "S1",
  },
];

describe("SourceTranscriptionDialog", () => {
  it("localizes the shared dialog close label", () => {
    useI18nStore().dictionary = { "ui.close": "Fermer" };
    mount(SourceTranscriptionDialog, {
      props: { open: true, pdfUrl: "", page: 1, pageCount: 1, text: "Texte", blocks },
      attachTo: document.body,
    });
    expect(document.body.querySelector('button[aria-label="Fermer"]')).toBeTruthy();
  });

  it("keeps audio review keyboard reachable without PDF page controls", () => {
    mount(SourceTranscriptionDialog, {
      props: {
        open: true,
        mediaKind: "audio",
        audioUrl: "/clip.wav",
        pdfUrl: "",
        page: 1,
        pageCount: 1,
        text: "Transcript",
        blocks,
      },
      attachTo: document.body,
    });
    expect(document.body.querySelector(".source-toolbar")).toBeNull();
    expect(document.body.querySelector(".source-pane")?.getAttribute("tabindex")).toBe("0");
    expect(document.body.querySelector("audio")?.hasAttribute("controls")).toBe(true);
    expect(document.body.textContent).toContain("00:00:01–00:00:03 S1");
  });

  it("marks transcription edits busy while save is pending", () => {
    mount(SourceTranscriptionDialog, {
      props: { open: true, pdfUrl: "", page: 1, pageCount: 1, text: "Transcript", busy: true },
      attachTo: document.body,
    });
    expect(document.body.querySelector(".transcription-pane")?.getAttribute("aria-busy")).toBe("true");
    expect(document.body.querySelector("textarea")?.hasAttribute("disabled")).toBe(true);
  });
});
