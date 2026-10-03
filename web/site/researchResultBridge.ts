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
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program. If not, see <https://www.gnu.org/licenses/>.
 */

import { createApp, type App } from "vue";
import PublishedResearchResult from "./PublishedResearchResult.vue";

type PublicationRecord = {
  record_id?: string;
  inline_citation?: string;
  full_citation?: string;
  citation?: string;
  work?: string;
};

type EvidenceItem = {
  evidenceId: string;
  recordId: string;
  work?: string;
  citation?: string;
};

type RenderResearchResultOptions = {
  answerTarget: HTMLElement;
  evidenceTarget: HTMLElement;
  answer: string;
  evidence: EvidenceItem[];
  recordsById: Map<string, PublicationRecord>;
  evidenceLabel: string;
  openRecordLabel: string;
  onOpenRecord: (recordId: string) => void | Promise<void>;
};

const mountedResults = new WeakMap<HTMLElement, App<Element>>();

export function clearPublishedResearchResult(answerTarget: HTMLElement) {
  mountedResults.get(answerTarget)?.unmount();
  mountedResults.delete(answerTarget);
  answerTarget.replaceChildren();
}

export function renderPublishedResearchResult(options: RenderResearchResultOptions) {
  clearPublishedResearchResult(options.answerTarget);
  const app = createApp(PublishedResearchResult, {
    answer: options.answer,
    evidence: options.evidence,
    recordsById: options.recordsById,
    evidenceTarget: options.evidenceTarget,
    evidenceLabel: options.evidenceLabel,
    openRecordLabel: options.openRecordLabel,
    onOpenRecord: options.onOpenRecord,
  });
  app.mount(options.answerTarget);
  mountedResults.set(options.answerTarget, app);
}
