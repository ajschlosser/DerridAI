/* Copyright 2026 Aaron John Schlosser, PhD. */
import type { AnnotationWorkspaceItem, AnnotationsWorkspaceSnapshot } from "../types/annotations";
import * as runtime from "../runtime/runtime.js";

export interface CreateAnnotationInput {
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
}

export const annotationsService: AnnotationService = {
  loadWorkspace: (force) => runtime.loadAnnotationsWorkspace(force) as Promise<AnnotationsWorkspaceSnapshot>,
  setQuery: (value) => runtime.setAnnotationsWorkspaceQuery(value),
  setView: (value) => runtime.setAnnotationsWorkspaceView(value),
  openRecord: (annotation) => runtime.openAnnotationsWorkspaceRecord(annotation),
  openWork: (work) => runtime.openAnnotationsWorkspaceWork(work),
  openWorkAnnotations: (work) => runtime.openWorkAnnotations(work),
  removeWorkspaceItem: (annotation) => runtime.removeAnnotationsWorkspaceItem(annotation),
  addToCurrentRecord: (input) => runtime.addCurrentRecordAnnotation(input),
  removeFromCurrentRecord: (id) => runtime.removeCurrentRecordAnnotation(id),
};
