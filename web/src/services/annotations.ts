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

import type { AnnotationWorkspaceItem, AnnotationsWorkspaceSnapshot } from "../types/annotations";
import * as runtime from "../runtime/runtime.js";

export interface CreateAnnotationInput {
  scope?: "text" | "record" | "work";
  linkedRecordIds?: string[];
  field: string;
  quote: string;
  note: string;
  tags: string[];
}

export interface AnnotationService {
  loadWorkspace(force?: boolean): Promise<AnnotationsWorkspaceSnapshot>;
  setQuery(value: string): void;
  setView(value: "works" | "recent"): void;
  openRecord(annotation: AnnotationWorkspaceItem): void;
  openWork(work: string): void;
  openWorkAnnotations(work: string): void;
  removeWorkspaceItem(annotation: AnnotationWorkspaceItem): Promise<void>;
  addToCurrentRecord(input: CreateAnnotationInput): Promise<unknown>;
  removeFromCurrentRecord(id: string): Promise<unknown>;
  replyToAnnotation(
    id: string,
    input: Pick<CreateAnnotationInput, "quote" | "note" | "tags">,
  ): Promise<unknown>;
}

export const annotationsService: AnnotationService = {
  loadWorkspace: (force) =>
    runtime.loadAnnotationsWorkspace(force) as Promise<AnnotationsWorkspaceSnapshot>,
  setQuery: (value) => runtime.setAnnotationsWorkspaceQuery(value),
  setView: (value) => runtime.setAnnotationsWorkspaceView(value),
  openRecord: (annotation) => runtime.openAnnotationsWorkspaceRecord(annotation),
  openWork: (work) => runtime.openAnnotationsWorkspaceWork(work),
  openWorkAnnotations: (work) => runtime.openWorkAnnotations(work),
  removeWorkspaceItem: (annotation) => runtime.removeAnnotationsWorkspaceItem(annotation),
  addToCurrentRecord: (input) => runtime.addCurrentRecordAnnotation(input),
  removeFromCurrentRecord: (id) => runtime.removeCurrentRecordAnnotation(id),
  replyToAnnotation: (id, input) => runtime.replyToCurrentAnnotation(id, input),
};
