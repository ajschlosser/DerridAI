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

  it("marks uncertain speaker spans and makes audio timestamps seekable", () => {
    mount(SourceTranscriptionDialog, {
      props: {
        open: true,
        mediaKind: "audio",
        audioUrl: "/clip.wav",
        pdfUrl: "",
        page: 1,
        pageCount: 1,
        text: "Transcript",
        blocks: [
          {
            ...blocks[0],
            speaker_assignment: {
              method: "word_overlap",
              confidence: 0.55,
              ambiguous_word_count: 1,
              word_count: 2,
              review_recommended: true,
            },
          },
        ],
      },
      attachTo: document.body,
    });

    expect(document.body.querySelector(".speaker-timeline")).toBeTruthy();
    expect(document.body.querySelector(".timeline-segment")).toBeTruthy();
    expect(document.body.querySelector(".time-seek")).toBeTruthy();
    expect(document.body.querySelector(".speaker-review-needed")).toBeTruthy();
    expect(document.body.querySelector(".speaker-review-note")?.textContent).toContain(
      "uncertain",
    );
  });

  it("marks transcription edits busy while save is pending", () => {
    mount(SourceTranscriptionDialog, {
      props: { open: true, pdfUrl: "", page: 1, pageCount: 1, text: "Transcript", busy: true },
      attachTo: document.body,
    });
    expect(document.body.querySelector(".transcription-pane")?.getAttribute("aria-busy")).toBe(
      "true",
    );
    expect(document.body.querySelector("textarea")?.hasAttribute("disabled")).toBe(true);
  });
});
