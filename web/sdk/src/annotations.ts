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

import type { Annotation, AnnotationInput, ClientStorage, PublicationManifest } from "./types";

function id(): string {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `annotation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export class AnnotationStore {
  private readonly namespace: string;

  constructor(
    manifest: PublicationManifest,
    private readonly storage: ClientStorage,
  ) {
    this.namespace = `annotations:${manifest.publication_id}`;
  }

  async list(filters: { work?: string } = {}): Promise<Annotation[]> {
    const items = await this.storage.list<Annotation>(this.namespace);
    return items
      .filter((item) => !filters.work || item.work === filters.work)
      .sort((left, right) => right.created_at.localeCompare(left.created_at));
  }

  async get(annotationId: string): Promise<Annotation | null> {
    return this.storage.get<Annotation>(this.namespace, annotationId);
  }

  async add(input: AnnotationInput): Promise<Annotation> {
    const now = new Date().toISOString();
    const annotation: Annotation = {
      id: id(),
      publication_id: this.namespace.slice("annotations:".length),
      record_id: String(input.recordId),
      record_revision: input.recordRevision,
      work: input.work,
      quote: String(input.quote ?? "").trim(),
      note: String(input.note ?? "").trim(),
      tags: (input.tags ?? [])
        .map(String)
        .map((tag) => tag.trim())
        .filter(Boolean),
      created_at: now,
      updated_at: now,
    };
    await this.storage.set(this.namespace, annotation.id, annotation);
    return annotation;
  }

  async update(
    annotationId: string,
    patch: Partial<Omit<AnnotationInput, "recordId">>,
  ): Promise<Annotation> {
    const current = await this.get(annotationId);
    if (!current) throw new Error(`Unknown annotation: ${annotationId}`);
    const next: Annotation = {
      ...current,
      record_revision:
        patch.recordRevision === undefined ? current.record_revision : patch.recordRevision,
      work: patch.work === undefined ? current.work : patch.work,
      quote: patch.quote === undefined ? current.quote : String(patch.quote).trim(),
      note: patch.note === undefined ? current.note : String(patch.note).trim(),
      tags:
        patch.tags === undefined
          ? current.tags
          : patch.tags
              .map(String)
              .map((tag) => tag.trim())
              .filter(Boolean),
      updated_at: new Date().toISOString(),
    };
    await this.storage.set(this.namespace, annotationId, next);
    return next;
  }

  async remove(annotationId: string): Promise<void> {
    await this.storage.delete(this.namespace, annotationId);
  }

  async export(): Promise<{ version: 1; annotations: Annotation[] }> {
    return { version: 1, annotations: await this.list() };
  }

  async import(payload: { annotations?: Annotation[] }): Promise<number> {
    const annotations = Array.isArray(payload.annotations) ? payload.annotations : [];
    let imported = 0;
    for (const annotation of annotations) {
      if (!annotation?.id || !annotation.record_id) continue;
      await this.storage.set(this.namespace, annotation.id, annotation);
      imported += 1;
    }
    return imported;
  }
}
