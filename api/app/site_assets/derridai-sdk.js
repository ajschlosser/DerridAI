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

var DerridAI = (function(exports) {
  "use strict";
  function id() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `annotation-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  class AnnotationStore {
    constructor(manifest, storage2) {
      this.storage = storage2;
      this.namespace = `annotations:${manifest.publication_id}`;
    }
    storage;
    namespace;
    async list(filters = {}) {
      const items = await this.storage.list(this.namespace);
      return items.filter((item) => !filters.work || item.work === filters.work).sort((left, right) => right.created_at.localeCompare(left.created_at));
    }
    async get(annotationId) {
      return this.storage.get(this.namespace, annotationId);
    }
    async add(input) {
      const now = (/* @__PURE__ */ new Date()).toISOString();
      const annotation = {
        id: id(),
        publication_id: this.namespace.slice("annotations:".length),
        record_id: String(input.recordId),
        record_revision: input.recordRevision,
        work: input.work,
        quote: String(input.quote ?? "").trim(),
        note: String(input.note ?? "").trim(),
        tags: (input.tags ?? []).map(String).map((tag) => tag.trim()).filter(Boolean),
        created_at: now,
        updated_at: now
      };
      await this.storage.set(this.namespace, annotation.id, annotation);
      return annotation;
    }
    async update(annotationId, patch) {
      const current = await this.get(annotationId);
      if (!current) throw new Error(`Unknown annotation: ${annotationId}`);
      const next = {
        ...current,
        record_revision: patch.recordRevision === void 0 ? current.record_revision : patch.recordRevision,
        work: patch.work === void 0 ? current.work : patch.work,
        quote: patch.quote === void 0 ? current.quote : String(patch.quote).trim(),
        note: patch.note === void 0 ? current.note : String(patch.note).trim(),
        tags: patch.tags === void 0 ? current.tags : patch.tags.map(String).map((tag) => tag.trim()).filter(Boolean),
        updated_at: (/* @__PURE__ */ new Date()).toISOString()
      };
      await this.storage.set(this.namespace, annotationId, next);
      return next;
    }
    async remove(annotationId) {
      await this.storage.delete(this.namespace, annotationId);
    }
    async export() {
      return { version: 1, annotations: await this.list() };
    }
    async import(payload) {
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
  function firstPrintedPage(record) {
    const direct = record.printed_page ?? record.page_start ?? record.page;
    if (direct != null) return direct;
    for (const span of record.source_spans ?? []) {
      if (span.printed_page != null) return span.printed_page;
    }
    return void 0;
  }
  function formatCitation(record) {
    const base = String(
      record.full_citation || record.citation || record.work || record.record_id || ""
    ).trim();
    const start = firstPrintedPage(record);
    const end = record.page_end;
    let plain = base;
    if (start != null && !/\bp{1,2}\.\s*\d/i.test(base)) {
      plain = end != null && String(end) !== String(start) ? `${base}, pp. ${start}–${end}` : `${base}, p. ${start}`;
    }
    return {
      plain,
      locator: {
        recordId: String(record.record_id),
        printedPageStart: start,
        printedPageEnd: end
      }
    };
  }
  function citationForEvidence(evidence) {
    return {
      plain: evidence.citation,
      locator: {
        recordId: evidence.recordId
      }
    };
  }
  class EventBus {
    listeners = /* @__PURE__ */ new Set();
    subscribe(listener) {
      this.listeners.add(listener);
      return () => this.listeners.delete(listener);
    }
    emit(event) {
      for (const listener of this.listeners) listener(event);
    }
  }
  function isAbortError(error) {
    return Boolean(
      error && typeof error === "object" && "name" in error && error.name === "AbortError"
    );
  }
  const SEPARATOR = "\0";
  function embeddingFingerprint(descriptor) {
    return [
      descriptor.type ?? "",
      descriptor.model ?? "",
      descriptor.revision ?? "",
      descriptor.variant ?? ""
    ].join("|");
  }
  function modelName(value) {
    return String(value ?? "").replace(/:latest$/, "");
  }
  function matchesPublicationModel(descriptor, contract) {
    const expected = modelName(contract?.model);
    const actual = modelName(descriptor.model);
    if (!expected || !actual || expected !== actual) return false;
    const expectedRevision = String(contract?.revision ?? "");
    const actualRevision = String(descriptor.revision ?? "");
    if (expectedRevision && actualRevision && expectedRevision !== actualRevision) return false;
    const expectedVariant = String(contract?.variant ?? "");
    const actualVariant = String(descriptor.variant ?? "");
    if (!expectedVariant) return !actualVariant;
    return expectedVariant === actualVariant;
  }
  function indexKey(publicationId, fingerprint) {
    return `${publicationId}${SEPARATOR}${fingerprint}`;
  }
  function summaryOf(publicationId, fingerprint, descriptor, dimension, count) {
    return {
      publicationId,
      fingerprint,
      model: String(descriptor.model ?? ""),
      provider: String(descriptor.type ?? ""),
      dimension,
      count,
      updatedAt: (/* @__PURE__ */ new Date()).toISOString()
    };
  }
  class MemoryVectorStore {
    persistent = false;
    indexes = /* @__PURE__ */ new Map();
    async ids(publicationId, fingerprint) {
      return new Set(this.indexes.get(indexKey(publicationId, fingerprint))?.vectors.keys() ?? []);
    }
    async load(publicationId, fingerprint) {
      const entry = this.indexes.get(indexKey(publicationId, fingerprint));
      if (!entry) return null;
      return { dimension: entry.summary.dimension, vectors: new Map(entry.vectors) };
    }
    async put(publicationId, fingerprint, descriptor, entries) {
      const key = indexKey(publicationId, fingerprint);
      let entry = this.indexes.get(key);
      if (!entry) {
        entry = {
          summary: summaryOf(
            publicationId,
            fingerprint,
            descriptor,
            entries[0]?.vector.length ?? 0,
            0
          ),
          vectors: /* @__PURE__ */ new Map()
        };
        this.indexes.set(key, entry);
      }
      for (const item of entries) entry.vectors.set(item.recordId, new Float32Array(item.vector));
      entry.summary = {
        ...entry.summary,
        count: entry.vectors.size,
        updatedAt: (/* @__PURE__ */ new Date()).toISOString()
      };
    }
    async summaries(publicationId) {
      return [...this.indexes.values()].map((entry) => entry.summary).filter((summary) => summary.publicationId === publicationId);
    }
    async clear(publicationId, fingerprint) {
      for (const key of [...this.indexes.keys()]) {
        const [id2, print] = key.split(SEPARATOR);
        if (id2 === publicationId && (fingerprint === void 0 || print === fingerprint)) {
          this.indexes.delete(key);
        }
      }
    }
  }
  function request(req) {
    return new Promise((resolve, reject) => {
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error ?? new Error("IndexedDB request failed."));
    });
  }
  function transactionDone(tx) {
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error ?? new Error("IndexedDB transaction failed."));
      tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted."));
    });
  }
  class IndexedDbVectorStore {
    constructor(name = "derridai-sdk-vectors", factory = globalThis.indexedDB) {
      this.name = name;
      this.factory = factory;
    }
    name;
    factory;
    persistent = true;
    opened;
    database() {
      if (!this.opened) {
        this.opened = new Promise((resolve, reject) => {
          const open = this.factory.open(this.name, 1);
          open.onupgradeneeded = () => {
            open.result.createObjectStore("vectors");
            open.result.createObjectStore("indexes");
          };
          open.onsuccess = () => resolve(open.result);
          open.onerror = () => reject(open.error ?? new Error("IndexedDB could not be opened."));
          open.onblocked = () => reject(new Error("IndexedDB upgrade was blocked."));
        });
        this.opened.catch(() => {
          this.opened = void 0;
        });
      }
      return this.opened;
    }
    range(publicationId, fingerprint) {
      const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
      return IDBKeyRange.bound(prefix, `${prefix}￿`);
    }
    async ids(publicationId, fingerprint) {
      const db = await this.database();
      const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
      const keys = await request(
        db.transaction("vectors", "readonly").objectStore("vectors").getAllKeys(this.range(publicationId, fingerprint))
      );
      return new Set(keys.map((key) => String(key).slice(prefix.length)));
    }
    async load(publicationId, fingerprint) {
      const db = await this.database();
      const tx = db.transaction(["vectors", "indexes"], "readonly");
      const meta = await request(
        tx.objectStore("indexes").get(indexKey(publicationId, fingerprint))
      );
      if (!meta) return null;
      const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
      const range = this.range(publicationId, fingerprint);
      const store = tx.objectStore("vectors");
      const [keys, values] = await Promise.all([
        request(store.getAllKeys(range)),
        request(store.getAll(range))
      ]);
      const vectors = /* @__PURE__ */ new Map();
      keys.forEach((key, index) => {
        vectors.set(String(key).slice(prefix.length), values[index]);
      });
      return { dimension: meta.dimension, vectors };
    }
    async put(publicationId, fingerprint, descriptor, entries) {
      const db = await this.database();
      const tx = db.transaction(["vectors", "indexes"], "readwrite");
      const done = transactionDone(tx);
      const vectors = tx.objectStore("vectors");
      const prefix = `${indexKey(publicationId, fingerprint)}${SEPARATOR}`;
      for (const item of entries) vectors.put(item.vector, `${prefix}${item.recordId}`);
      const count = await request(vectors.count(this.range(publicationId, fingerprint)));
      const indexes = tx.objectStore("indexes");
      const key = indexKey(publicationId, fingerprint);
      const existing = await request(indexes.get(key));
      indexes.put(
        {
          ...summaryOf(
            publicationId,
            fingerprint,
            descriptor,
            existing?.dimension || entries[0]?.vector.length || 0,
            count
          )
        },
        key
      );
      await done;
    }
    async summaries(publicationId) {
      const db = await this.database();
      const all = await request(
        db.transaction("indexes", "readonly").objectStore("indexes").getAll()
      );
      return all.filter((summary) => summary.publicationId === publicationId);
    }
    async clear(publicationId, fingerprint) {
      const targets = fingerprint !== void 0 ? [fingerprint] : (await this.summaries(publicationId)).map((summary) => summary.fingerprint);
      const db = await this.database();
      const tx = db.transaction(["vectors", "indexes"], "readwrite");
      const done = transactionDone(tx);
      for (const print of targets) {
        tx.objectStore("vectors").delete(this.range(publicationId, print));
        tx.objectStore("indexes").delete(indexKey(publicationId, print));
      }
      await done;
    }
  }
  class FallbackVectorStore {
    active;
    fallback = new MemoryVectorStore();
    constructor(primary) {
      this.active = primary;
    }
    get persistent() {
      return this.active.persistent;
    }
    async run(operation) {
      if (this.active === this.fallback) return operation(this.active);
      try {
        return await operation(this.active);
      } catch {
        this.active = this.fallback;
        return operation(this.active);
      }
    }
    ids(publicationId, fingerprint) {
      return this.run((store) => store.ids(publicationId, fingerprint));
    }
    load(publicationId, fingerprint) {
      return this.run((store) => store.load(publicationId, fingerprint));
    }
    put(publicationId, fingerprint, descriptor, entries) {
      return this.run((store) => store.put(publicationId, fingerprint, descriptor, entries));
    }
    summaries(publicationId) {
      return this.run((store) => store.summaries(publicationId));
    }
    clear(publicationId, fingerprint) {
      return this.run((store) => store.clear(publicationId, fingerprint));
    }
  }
  function defaultVectorStore() {
    try {
      if (typeof globalThis.indexedDB !== "undefined" && globalThis.indexedDB) {
        return new FallbackVectorStore(new IndexedDbVectorStore());
      }
    } catch {
    }
    return new MemoryVectorStore();
  }
  const vectorIndex = {
    indexedDb: (name) => new IndexedDbVectorStore(name),
    /** IndexedDB that degrades to memory for the session if the browser refuses it. */
    resilient: (name) => new FallbackVectorStore(new IndexedDbVectorStore(name)),
    memory: () => new MemoryVectorStore()
  };
  const DEFAULT_BATCH_SIZE = 16;
  function throwIfAborted$2(signal) {
    if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
  }
  async function yieldBetweenIndexBatches(signal) {
    throwIfAborted$2(signal);
    const scheduler = globalThis.scheduler;
    if (scheduler?.yield) {
      await scheduler.yield();
    } else {
      await new Promise((resolve) => setTimeout(resolve, 0));
    }
    throwIfAborted$2(signal);
  }
  class LocalVectorIndex {
    constructor(manifest, repository, store, events) {
      this.manifest = manifest;
      this.repository = repository;
      this.store = store;
      this.events = events;
    }
    manifest;
    repository;
    store;
    events;
    loaded = /* @__PURE__ */ new Map();
    get publicationId() {
      return this.manifest.publication_id;
    }
    textOf(record) {
      const field = String(this.manifest.vector_index?.text_field || "text");
      return String(record[field] ?? "").trim();
    }
    usesPublishedVectors(provider) {
      return Boolean(
        this.manifest.features?.semantic_search && this.manifest.vector_index?.dimension && matchesPublicationModel(provider.descriptor(), this.manifest.vector_index)
      );
    }
    async status(provider) {
      const descriptor = provider.descriptor();
      const fingerprint = embeddingFingerprint(descriptor);
      const total = this.repository.totalRecords();
      const usesPublishedVectors = this.usesPublishedVectors(provider);
      const indexed = (await this.store.ids(this.publicationId, fingerprint)).size;
      return {
        usesPublishedVectors,
        complete: usesPublishedVectors || total > 0 && indexed >= total,
        indexed: usesPublishedVectors ? total : indexed,
        total,
        persistent: this.store.persistent,
        model: descriptor.model
      };
    }
    async vectorsFor(provider) {
      const fingerprint = embeddingFingerprint(provider.descriptor());
      const cached = this.loaded.get(fingerprint);
      if (cached) return cached;
      const stored = await this.store.load(this.publicationId, fingerprint);
      if (stored) this.loaded.set(fingerprint, stored);
      return stored;
    }
    async build(provider, runId2, options = {}) {
      const { signal } = options;
      const batchSize = Math.max(1, Math.min(128, options.batchSize ?? DEFAULT_BATCH_SIZE));
      const descriptor = provider.descriptor();
      const fingerprint = embeddingFingerprint(descriptor);
      const total = this.repository.totalRecords();
      const existing = await this.store.ids(this.publicationId, fingerprint);
      const summary = (await this.store.summaries(this.publicationId)).find(
        (item) => item.fingerprint === fingerprint
      );
      let dimension = summary?.dimension ?? 0;
      let indexed = existing.size;
      const deferredEmpty = [];
      this.loaded.delete(fingerprint);
      this.events.emit({ type: "index-progress", runId: runId2, indexed, total });
      const writeEmpty = async (ids) => {
        if (!ids.length || !dimension) return;
        await this.store.put(
          this.publicationId,
          fingerprint,
          descriptor,
          ids.map((recordId) => ({ recordId, vector: new Float32Array(dimension) }))
        );
        indexed += ids.length;
      };
      await this.repository.eachChunk(signal, async (records) => {
        const pending = records.filter((record) => !existing.has(String(record.record_id)));
        const embeddable = pending.filter((record) => this.textOf(record));
        const empty = pending.filter((record) => !this.textOf(record)).map((record) => String(record.record_id));
        for (let start = 0; start < embeddable.length; start += batchSize) {
          throwIfAborted$2(signal);
          const batch = embeddable.slice(start, start + batchSize);
          const result = await provider.embed(
            batch.map((record) => this.textOf(record)),
            { signal, purpose: "document" }
          );
          if (result.vectors.length !== batch.length) {
            throw new Error("The embedding provider returned the wrong number of vectors.");
          }
          const entries = batch.map((record, index) => {
            const vector = Float32Array.from(result.vectors[index] ?? []);
            if (!vector.length || vector.some((value) => !Number.isFinite(value))) {
              throw new Error("The embedding provider returned an invalid vector.");
            }
            if (!dimension) dimension = vector.length;
            if (vector.length !== dimension) {
              throw new Error("The embedding provider returned vectors of differing sizes.");
            }
            return { recordId: String(record.record_id), vector };
          });
          await this.store.put(this.publicationId, fingerprint, descriptor, entries);
          indexed += entries.length;
          this.events.emit({ type: "index-progress", runId: runId2, indexed, total });
          if (start + batchSize < embeddable.length) {
            await yieldBetweenIndexBatches(signal);
          }
        }
        if (dimension) await writeEmpty(empty);
        else deferredEmpty.push(...empty);
        this.events.emit({ type: "index-progress", runId: runId2, indexed, total });
      });
      await writeEmpty(deferredEmpty);
      this.events.emit({ type: "index-progress", runId: runId2, indexed, total });
      return this.status(provider);
    }
    async clear(provider) {
      if (provider) {
        const fingerprint = embeddingFingerprint(provider.descriptor());
        this.loaded.delete(fingerprint);
        await this.store.clear(this.publicationId, fingerprint);
        return;
      }
      this.loaded.clear();
      await this.store.clear(this.publicationId);
    }
    async summaries() {
      return this.store.summaries(this.publicationId);
    }
  }
  class LruCache {
    constructor(capacity) {
      this.capacity = capacity;
    }
    capacity;
    values = /* @__PURE__ */ new Map();
    get(key) {
      const value = this.values.get(key);
      if (value === void 0) return void 0;
      this.values.delete(key);
      this.values.set(key, value);
      return value;
    }
    set(key, value) {
      if (this.capacity <= 0) return;
      this.values.delete(key);
      this.values.set(key, value);
      while (this.values.size > this.capacity) {
        const oldest = this.values.keys().next().value;
        if (oldest === void 0) break;
        this.values.delete(oldest);
      }
    }
    clear() {
      this.values.clear();
    }
    get size() {
      return this.values.size;
    }
  }
  function throwIfAborted$1(signal) {
    if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
  }
  async function yieldToBrowser() {
    const scheduler = globalThis.scheduler;
    if (scheduler?.yield) {
      await scheduler.yield();
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 0));
  }
  function scalarText(value) {
    if (Array.isArray(value)) return value.map(scalarText).join(" ");
    if (value && typeof value === "object") return JSON.stringify(value);
    return String(value ?? "");
  }
  function normalized(value, locale) {
    return scalarText(value).toLocaleLowerCase(locale);
  }
  function matchesFilter(record, field, expected, locale) {
    if (expected == null || expected === "") return true;
    const actual = record[field];
    if (Array.isArray(expected)) {
      const candidates = expected.map((value) => normalized(value, locale));
      if (Array.isArray(actual)) {
        const values = actual.map((value) => normalized(value, locale));
        return candidates.some((candidate) => values.includes(candidate));
      }
      return candidates.includes(normalized(actual, locale));
    }
    if (typeof expected === "string") {
      const needle = expected.toLocaleLowerCase(locale);
      if (field === "work") return normalized(actual, locale) === needle;
      return normalized(actual, locale).includes(needle);
    }
    return actual === expected;
  }
  class RecordRepository {
    constructor(dataSource, descriptors, events, cache = {}) {
      this.dataSource = dataSource;
      this.descriptors = descriptors;
      this.events = events;
      this.recordChunks = new LruCache(cache.recordChunks ?? 8);
      this.vectorChunks = new LruCache(cache.vectorChunks ?? 4);
    }
    dataSource;
    descriptors;
    events;
    recordChunks;
    vectorChunks;
    vectorsByRecordId = /* @__PURE__ */ new Map();
    selectedDescriptors(filters = {}) {
      const requested = filters.work;
      if (requested == null || requested === "") return this.descriptors;
      const works = (Array.isArray(requested) ? requested : [requested]).map(String);
      return this.descriptors.filter(
        (descriptor) => descriptor.work && works.includes(descriptor.work)
      );
    }
    async loadRecords(chunkId, signal) {
      throwIfAborted$1(signal);
      const cached = this.recordChunks.get(chunkId);
      if (cached) return cached;
      const records = await this.dataSource.loadRecords(chunkId, { signal });
      throwIfAborted$1(signal);
      this.recordChunks.set(chunkId, records);
      return records;
    }
    async loadVectors(chunkId, signal) {
      throwIfAborted$1(signal);
      const cached = this.vectorChunks.get(chunkId);
      if (cached !== void 0) return cached;
      const chunk = this.dataSource.loadVectors ? await this.dataSource.loadVectors(chunkId, { signal }) : null;
      throwIfAborted$1(signal);
      if (chunk) {
        chunk.ids.forEach((id2, index) => {
          const recordId = String(id2);
          if (this.vectorsByRecordId.has(recordId)) return;
          const start = index * chunk.dimension;
          this.vectorsByRecordId.set(recordId, chunk.values.subarray(start, start + chunk.dimension));
        });
      }
      this.vectorChunks.set(chunkId, chunk);
      return chunk;
    }
    async candidates(filters, locale, runId2, signal) {
      const descriptors = this.selectedDescriptors(filters);
      const records = [];
      for (let index = 0; index < descriptors.length; index += 1) {
        throwIfAborted$1(signal);
        const descriptor = descriptors[index];
        const chunkRecords = await this.loadRecords(descriptor.id, signal);
        for (const record of chunkRecords) {
          if (Object.entries(filters).every(
            ([field, expected]) => matchesFilter(record, field, expected, locale)
          )) {
            records.push(record);
          }
        }
        this.events.emit({
          type: "load-progress",
          runId: runId2,
          stage: "records",
          chunkId: descriptor.id,
          work: descriptor.work,
          completed: index + 1,
          total: descriptors.length
        });
        if (index + 1 < descriptors.length) await yieldToBrowser();
      }
      return { records, chunksLoaded: descriptors.length };
    }
    totalRecords() {
      return this.descriptors.reduce((sum, descriptor) => sum + descriptor.recordCount, 0);
    }
    /** Visit every Record chunk in publication order, yielding to the browser between chunks. */
    async eachChunk(signal, visit) {
      for (let index = 0; index < this.descriptors.length; index += 1) {
        throwIfAborted$1(signal);
        await visit(
          await this.loadRecords(this.descriptors[index].id, signal),
          index,
          this.descriptors.length
        );
        if (index + 1 < this.descriptors.length) await yieldToBrowser();
      }
    }
    async ensureVectors(filters, runId2, signal) {
      const descriptors = this.selectedDescriptors(filters);
      for (let index = 0; index < descriptors.length; index += 1) {
        throwIfAborted$1(signal);
        const descriptor = descriptors[index];
        await this.loadVectors(descriptor.id, signal);
        this.events.emit({
          type: "load-progress",
          runId: runId2,
          stage: "vectors",
          chunkId: descriptor.id,
          work: descriptor.work,
          completed: index + 1,
          total: descriptors.length
        });
        if (index + 1 < descriptors.length) await yieldToBrowser();
      }
    }
    vector(recordId) {
      return this.vectorsByRecordId.get(recordId);
    }
    async get(recordId, signal) {
      for (const descriptor of this.descriptors) {
        const records = await this.loadRecords(descriptor.id, signal);
        const record = records.find((item) => String(item.record_id) === String(recordId));
        if (record) return record;
        await yieldToBrowser();
      }
      return null;
    }
    clear() {
      this.recordChunks.clear();
      this.vectorChunks.clear();
      this.vectorsByRecordId.clear();
    }
    stats() {
      return {
        recordChunks: this.recordChunks.size,
        vectorChunks: this.vectorChunks.size,
        vectors: this.vectorsByRecordId.size
      };
    }
  }
  function evidenceRef(manifest, record, index) {
    return {
      evidenceId: `E${index + 1}`,
      recordId: String(record.record_id),
      recordRevision: record.record_revision == null ? void 0 : String(record.record_revision),
      publicationId: manifest.publication_id,
      work: record.work == null ? void 0 : String(record.work),
      citation: formatCitation(record).plain,
      text: String(record.text ?? ""),
      speaker: record.speaker == null ? void 0 : String(record.speaker),
      quotedSpeaker: record.quoted_speaker == null ? void 0 : String(record.quoted_speaker),
      positionHolder: record.position_holder == null ? void 0 : String(record.position_holder),
      stance: record.stance == null ? void 0 : String(record.stance),
      target: record.target == null ? void 0 : String(record.target),
      discourseRole: record.discourse_role == null ? void 0 : String(record.discourse_role)
    };
  }
  function prompt(question, packet) {
    const evidence = packet.evidence.map(
      (item) => `[${item.evidenceId}] ${item.citation}
Record ID: ${item.recordId}
Record revision: ${item.recordRevision ?? ""}
Speaker: ${item.speaker ?? ""}
Quoted speaker: ${item.quotedSpeaker ?? ""}
Position holder: ${item.positionHolder ?? ""}
Stance: ${item.stance ?? ""}
Target: ${item.target ?? ""}
Discourse role: ${item.discourseRole ?? ""}
TEXT:
${item.text}`
    ).join("\n\n");
    return `Answer the research question using only the supplied evidence. Preserve attribution: distinguish the passage speaker, quoted speaker, position holder, stance, target, and discourse role. Do not attribute a quoted or analyzed position to Derrida unless the evidence supports that attribution. Cite evidence IDs such as [E1]. If the evidence is insufficient, say so rather than inventing support.

Question: ${question}

Evidence:
${evidence}`;
  }
  class ResearchEngine {
    constructor(manifest, searchEngine, events, generation) {
      this.manifest = manifest;
      this.searchEngine = searchEngine;
      this.events = events;
      this.generation = generation;
    }
    manifest;
    searchEngine;
    events;
    generation;
    async run(request2, runId2) {
      const question = String(request2.question ?? "").trim();
      if (!question) throw new Error("Research question is required.");
      const retrieval = await this.searchEngine.search(
        {
          query: question,
          mode: request2.retrieval?.mode ?? "hybrid",
          filters: request2.retrieval?.filters,
          limit: request2.retrieval?.limit ?? 24,
          signal: request2.signal
        },
        runId2
      );
      const selected = this.searchEngine.diversify(
        retrieval.results,
        request2.retrieval?.evidenceLimit ?? 10,
        request2.retrieval?.mmrLambda ?? 0.72
      );
      const evidencePacket = {
        publicationId: this.manifest.publication_id,
        evidence: selected.map((item, index) => evidenceRef(this.manifest, item.record, index))
      };
      const warnings = [];
      if (retrieval.warnings.length) {
        warnings.push({
          code: "semantic_fallback",
          message: retrieval.warnings.map((warning) => warning.message).join(" ")
        });
      }
      if (!evidencePacket.evidence.length) {
        return {
          runId: runId2,
          publicationId: this.manifest.publication_id,
          question,
          answer: null,
          evidencePacket,
          retrieval,
          generation: null,
          warnings
        };
      }
      if (!this.generation) {
        warnings.push({
          code: "generation_unavailable",
          message: "No generation capability was supplied. The retrieved evidence packet remains available."
        });
        return {
          runId: runId2,
          publicationId: this.manifest.publication_id,
          question,
          answer: null,
          evidencePacket,
          retrieval,
          generation: null,
          warnings
        };
      }
      this.events.emit({ type: "generation-start", runId: runId2 });
      try {
        const generated = await this.generation.generate(
          {
            prompt: prompt(question, evidencePacket),
            question,
            evidencePacket
          },
          { signal: request2.signal }
        );
        this.events.emit({ type: "generation-complete", runId: runId2 });
        return {
          runId: runId2,
          publicationId: this.manifest.publication_id,
          question,
          answer: String(generated.text ?? "") || null,
          evidencePacket,
          retrieval,
          generation: generated.provider ?? this.generation.descriptor(),
          warnings
        };
      } catch (error) {
        if (isAbortError(error)) throw error;
        warnings.push({
          code: "generation_unavailable",
          message: error instanceof Error ? error.message : "Generation failed. The retrieved evidence packet remains available."
        });
        return {
          runId: runId2,
          publicationId: this.manifest.publication_id,
          question,
          answer: null,
          evidencePacket,
          retrieval,
          generation: this.generation.descriptor(),
          warnings
        };
      }
    }
  }
  function embeddingDescriptorMismatches(contract, descriptor) {
    if (!contract) return [];
    const mismatches = [];
    const pairs = ["model", "revision", "variant"];
    for (const field of pairs) {
      const expected = String(contract[field] ?? "").trim();
      const actual = String(descriptor[field] ?? "").trim();
      if (expected && actual && expected !== actual) {
        mismatches.push({ field, expected, actual });
      }
    }
    return mismatches;
  }
  function dedupeRecords(records) {
    const seen = /* @__PURE__ */ new Set();
    const unique = [];
    let duplicatesRemoved = 0;
    for (const record of records) {
      const id2 = String(record.record_id);
      if (seen.has(id2)) {
        duplicatesRemoved += 1;
        continue;
      }
      seen.add(id2);
      unique.push(record);
    }
    return { records: unique, duplicatesRemoved };
  }
  function tokens(value, locale) {
    return String(value ?? "").toLocaleLowerCase(locale).match(/[\p{L}\p{N}’'_-]+/gu) ?? [];
  }
  function searchable(record) {
    return Object.entries(record).filter(([key]) => !["source_spans", "field_assertions", "updates"].includes(key)).map(([, value]) => {
      if (Array.isArray(value)) return value.map(String).join(" ");
      if (value && typeof value === "object") return "";
      return String(value ?? "");
    }).join(" ");
  }
  function lexicalScores(query, candidates, locale) {
    const queryTerms = [...new Set(tokens(query, locale))];
    if (!queryTerms.length) {
      return candidates.map((record) => ({ record, score: 0, lexicalScore: 0 }));
    }
    const docs = candidates.map((record) => {
      const body = searchable(record);
      return {
        record,
        body: body.toLocaleLowerCase(locale),
        terms: tokens(body, locale)
      };
    });
    const count = docs.length || 1;
    const averageLength = Math.max(1, docs.reduce((sum, item) => sum + item.terms.length, 0) / count);
    const documentFrequency = new Map(
      queryTerms.map((term) => [term, docs.filter((doc) => doc.terms.includes(term)).length])
    );
    return docs.map((doc) => {
      const frequencies = /* @__PURE__ */ new Map();
      for (const term of doc.terms) {
        if (!queryTerms.includes(term)) continue;
        frequencies.set(term, (frequencies.get(term) ?? 0) + 1);
      }
      let score = 0;
      for (const term of queryTerms) {
        const tf = frequencies.get(term) ?? 0;
        if (!tf) continue;
        const df = documentFrequency.get(term) ?? 0;
        const idf = Math.log(1 + (count - df + 0.5) / (df + 0.5));
        const k1 = 1.2;
        const b = 0.75;
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc.terms.length / averageLength));
      }
      if (query && doc.body.includes(query.toLocaleLowerCase(locale))) score += 2.5;
      return { record: doc.record, score, lexicalScore: score };
    }).sort(compareScored);
  }
  function cosine(a, b) {
    if (!a || !b || !a.length || a.length !== b.length) return -1;
    let dot = 0;
    let aa = 0;
    let bb = 0;
    for (let index = 0; index < a.length; index += 1) {
      const x = Number(a[index]);
      const y = Number(b[index]);
      dot += x * y;
      aa += x * x;
      bb += y * y;
    }
    return aa && bb ? dot / Math.sqrt(aa * bb) : -1;
  }
  function compareScored(left, right) {
    if (right.score !== left.score) return right.score - left.score;
    return String(left.record.record_id).localeCompare(String(right.record.record_id));
  }
  function fallbackWarning(code, message, details) {
    return { code, message, details };
  }
  class SearchEngine {
    constructor(manifest, repository, events, embeddings, locale = "en-US", localIndex) {
      this.manifest = manifest;
      this.repository = repository;
      this.events = events;
      this.embeddings = embeddings;
      this.locale = locale;
      this.localIndex = localIndex;
    }
    manifest;
    repository;
    events;
    embeddings;
    locale;
    localIndex;
    vectorLookup = (id2) => this.repository.vector(id2);
    async search(request2, runId2) {
      const query = String(request2.query ?? "");
      const modeRequested = request2.mode ?? "hybrid";
      const filters = request2.filters ?? {};
      const limit = Math.max(1, Math.min(500, request2.limit ?? 30));
      const signal = request2.signal;
      this.events.emit({ type: "search-start", runId: runId2, query });
      const candidateSet = await this.repository.candidates(filters, this.locale, runId2, signal);
      const deduped = dedupeRecords(candidateSet.records);
      const candidates = deduped.records;
      const lexical = lexicalScores(query, candidates, this.locale);
      const publishedAvailable = Boolean(
        this.manifest.features?.semantic_search && this.manifest.vector_index?.dimension
      );
      const semanticAvailable = publishedAvailable || Boolean(this.embeddings);
      if (modeRequested === "keyword" || !query.trim()) {
        return this.finish(
          lexical.slice(0, limit),
          modeRequested,
          "keyword",
          [],
          candidateSet.records.length,
          candidateSet.chunksLoaded,
          semanticAvailable,
          deduped.duplicatesRemoved,
          runId2
        );
      }
      const fallback = (warning, available = semanticAvailable) => this.finish(
        lexical.slice(0, limit),
        modeRequested,
        "keyword",
        [warning],
        candidateSet.records.length,
        candidateSet.chunksLoaded,
        available,
        deduped.duplicatesRemoved,
        runId2
      );
      if (!this.embeddings) {
        return publishedAvailable ? fallback(
          fallbackWarning(
            "embedding_provider_unavailable",
            "No embedding capability was supplied; keyword results were returned."
          )
        ) : fallback(
          fallbackWarning(
            "semantic_unavailable",
            "This publication has no semantic vectors and no embedding provider is configured; keyword results were returned."
          ),
          false
        );
      }
      const descriptor = this.embeddings.descriptor();
      const usesPublished = publishedAvailable && matchesPublicationModel(descriptor, this.manifest.vector_index);
      if (!usesPublished && publishedAvailable) {
        const expectedModel = String(this.manifest.vector_index?.model ?? "").replace(/:latest$/, "");
        const actualModel = String(descriptor.model ?? "").replace(/:latest$/, "");
        const revisionMismatches = embeddingDescriptorMismatches(
          this.manifest.vector_index,
          descriptor
        ).filter((mismatch) => mismatch.field === "revision");
        if (expectedModel && expectedModel === actualModel && revisionMismatches.length) {
          return fallback(
            fallbackWarning(
              "embedding_contract_mismatch",
              "The supplied embedding capability does not match the publication embedding contract; keyword results were returned.",
              { mismatches: revisionMismatches }
            )
          );
        }
      }
      let expectedDimension = Number(this.manifest.vector_index?.dimension || 0);
      let localVectors;
      if (!usesPublished) {
        const local = this.localIndex ? await this.localIndex.vectorsFor(this.embeddings) : null;
        const indexed = local ? candidates.filter((record) => local.vectors.has(String(record.record_id))).length : 0;
        if (!local || indexed < candidates.length) {
          return fallback(
            fallbackWarning(
              "local_index_required",
              "Semantic search with this embedding model needs a local index of the published Records; keyword results were returned.",
              {
                expectedModel: String(this.manifest.vector_index?.model ?? ""),
                actualModel: String(descriptor.model ?? ""),
                indexed,
                total: candidates.length
              }
            )
          );
        }
        expectedDimension = local.dimension;
        localVectors = local.vectors;
      }
      this.events.emit({ type: "embedding-start", runId: runId2 });
      let vector;
      try {
        const embedded = await this.embeddings.embed([query], { signal, purpose: "query" });
        vector = embedded.vectors[0] ?? [];
        if (embedded.provider) {
          if (usesPublished) {
            const resultMismatches = embeddingDescriptorMismatches(
              this.manifest.vector_index,
              embedded.provider
            );
            if (resultMismatches.length) {
              return fallback(
                fallbackWarning(
                  "embedding_contract_mismatch",
                  "The embedding result provenance does not match the publication embedding contract; keyword results were returned.",
                  { mismatches: resultMismatches }
                )
              );
            }
          } else if (embeddingFingerprint(embedded.provider) !== embeddingFingerprint(descriptor)) {
            return fallback(
              fallbackWarning(
                "embedding_contract_mismatch",
                "The embedding result provenance does not match the configured embedding provider; keyword results were returned.",
                {
                  expected: embeddingFingerprint(descriptor),
                  actual: embeddingFingerprint(embedded.provider)
                }
              )
            );
          }
        }
      } catch (error) {
        if (isAbortError(error)) throw error;
        return fallback(
          fallbackWarning(
            "embedding_provider_unavailable",
            error instanceof Error ? error.message : "Embedding generation failed; keyword results were returned."
          )
        );
      }
      if (expectedDimension && vector.length !== expectedDimension) {
        return fallback(
          fallbackWarning(
            "embedding_dimension_mismatch",
            "The supplied embedding dimension does not match the vectors being searched; keyword results were returned.",
            { expected: expectedDimension, actual: vector.length }
          )
        );
      }
      if (usesPublished) await this.repository.ensureVectors(filters, runId2, signal);
      this.vectorLookup = usesPublished ? (id2) => this.repository.vector(id2) : (id2) => localVectors?.get(id2);
      const semantic = candidates.map((record) => {
        const id2 = String(record.record_id);
        const semanticScore = cosine(
          vector,
          usesPublished ? this.repository.vector(id2) : localVectors?.get(id2)
        );
        return { record, score: semanticScore, semanticScore };
      }).filter((item) => item.semanticScore > -1).sort(compareScored);
      if (modeRequested === "semantic") {
        return this.finish(
          semantic.slice(0, limit),
          modeRequested,
          "semantic",
          [],
          candidateSet.records.length,
          candidateSet.chunksLoaded,
          true,
          deduped.duplicatesRemoved,
          runId2
        );
      }
      const lexicalMax = Math.max(...lexical.map((item) => item.score), 1);
      const semanticById = new Map(
        semantic.map((item) => [String(item.record.record_id), item.semanticScore])
      );
      const lexicalById = new Map(
        lexical.map((item) => [String(item.record.record_id), item.lexicalScore ?? 0])
      );
      const merged = candidates.map((record) => {
        const id2 = String(record.record_id);
        const lexicalScore = lexicalById.get(id2) ?? 0;
        const semanticScore = semanticById.get(id2);
        const semanticNormalized = semanticScore == null ? 0 : (semanticScore + 1) / 2;
        return {
          record,
          lexicalScore,
          semanticScore,
          score: 0.45 * (lexicalScore / lexicalMax) + 0.55 * semanticNormalized
        };
      });
      return this.finish(
        merged.sort(compareScored).slice(0, limit),
        modeRequested,
        "hybrid",
        [],
        candidates.length,
        candidateSet.chunksLoaded,
        true,
        deduped.duplicatesRemoved,
        runId2
      );
    }
    diversify(items, limit = 10, lambda = 0.72) {
      const remaining = [...items];
      const selected = [];
      const boundedLambda = Math.max(0, Math.min(1, lambda));
      while (remaining.length && selected.length < limit) {
        let bestIndex = 0;
        let bestScore = Number.NEGATIVE_INFINITY;
        for (let index = 0; index < remaining.length; index += 1) {
          const item = remaining[index];
          const vector = this.vectorLookup(String(item.record.record_id));
          const redundancy = selected.length && vector ? Math.max(
            ...selected.map(
              (chosen) => cosine(vector, this.vectorLookup(String(chosen.record.record_id)))
            )
          ) : 0;
          const score = boundedLambda * Number(item.score || 0) - (1 - boundedLambda) * Math.max(0, redundancy);
          if (score > bestScore || score === bestScore && String(item.record.record_id).localeCompare(
            String(remaining[bestIndex]?.record.record_id ?? "")
          ) < 0) {
            bestScore = score;
            bestIndex = index;
          }
        }
        selected.push(remaining.splice(bestIndex, 1)[0]);
      }
      return selected.map((item, index) => ({ ...item, rank: index + 1 }));
    }
    finish(items, modeRequested, modeUsed, warnings, candidateCount, chunksLoaded, semanticAvailable, duplicatesRemoved, runId2) {
      const results = items.map((item, index) => ({
        record: item.record,
        score: item.score,
        lexicalScore: item.lexicalScore,
        semanticScore: item.semanticScore,
        rank: index + 1
      }));
      this.events.emit({ type: "retrieval-complete", runId: runId2, resultCount: results.length });
      return {
        results,
        modeRequested,
        modeUsed,
        warnings,
        diagnostics: {
          candidateCount,
          chunksLoaded,
          semanticAvailable,
          duplicatesRemoved
        }
      };
    }
  }
  class MemoryStorage {
    values = /* @__PURE__ */ new Map();
    async get(namespace, key) {
      return this.values.get(namespace)?.get(key) ?? null;
    }
    async set(namespace, key, value) {
      let bucket = this.values.get(namespace);
      if (!bucket) {
        bucket = /* @__PURE__ */ new Map();
        this.values.set(namespace, bucket);
      }
      bucket.set(key, structuredClone(value));
    }
    async delete(namespace, key) {
      this.values.get(namespace)?.delete(key);
    }
    async list(namespace) {
      return [...this.values.get(namespace)?.values() ?? []].map(
        (value) => structuredClone(value)
      );
    }
  }
  class BrowserStorage {
    constructor(prefix = "derridai.sdk", fallback = new MemoryStorage()) {
      this.prefix = prefix;
      this.fallback = fallback;
    }
    prefix;
    fallback;
    storageKey(namespace, key) {
      return `${this.prefix}:${namespace}:${key}`;
    }
    available() {
      try {
        const probe = `${this.prefix}:probe`;
        localStorage.setItem(probe, "1");
        localStorage.removeItem(probe);
        return true;
      } catch {
        return false;
      }
    }
    async get(namespace, key) {
      if (!this.available()) return this.fallback.get(namespace, key);
      try {
        const raw = localStorage.getItem(this.storageKey(namespace, key));
        return raw == null ? null : JSON.parse(raw);
      } catch {
        return this.fallback.get(namespace, key);
      }
    }
    async set(namespace, key, value) {
      await this.fallback.set(namespace, key, value);
      if (!this.available()) return;
      try {
        localStorage.setItem(this.storageKey(namespace, key), JSON.stringify(value));
      } catch {
      }
    }
    async delete(namespace, key) {
      await this.fallback.delete(namespace, key);
      if (!this.available()) return;
      try {
        localStorage.removeItem(this.storageKey(namespace, key));
      } catch {
      }
    }
    async list(namespace) {
      if (!this.available()) return this.fallback.list(namespace);
      const prefix = `${this.prefix}:${namespace}:`;
      const values = [];
      try {
        for (let index = 0; index < localStorage.length; index += 1) {
          const key = localStorage.key(index);
          if (!key?.startsWith(prefix)) continue;
          const raw = localStorage.getItem(key);
          if (raw != null) values.push(JSON.parse(raw));
        }
        return values;
      } catch {
        return this.fallback.list(namespace);
      }
    }
  }
  const storage = {
    memory: () => new MemoryStorage(),
    browser: () => new BrowserStorage()
  };
  function runId(prefix) {
    if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
    return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  class DerridAIClient {
    constructor(manifest, options, repository, events) {
      this.manifest = manifest;
      this.events = events;
      this.repository = repository;
      this.embeddings = options.embeddings;
      this.hasEmbeddings = Boolean(options.embeddings);
      this.localIndex = new LocalVectorIndex(
        manifest,
        repository,
        options.vectorIndex ?? defaultVectorStore(),
        events
      );
      this.hasGeneration = Boolean(options.generation);
      const locale = options.locale ?? manifest.locale ?? "en-US";
      this.searchEngine = new SearchEngine(
        manifest,
        repository,
        this.events,
        options.embeddings,
        locale,
        this.localIndex
      );
      this.researchEngine = new ResearchEngine(
        manifest,
        this.searchEngine,
        this.events,
        options.generation
      );
      this.annotations = new AnnotationStore(manifest, options.storage ?? new BrowserStorage());
      this.publication = {
        info: () => this.manifest,
        works: () => [...this.manifest.works]
      };
      this.records = {
        get: (recordId, operation = {}) => this.repository.get(recordId, operation.signal)
      };
      this.index = {
        status: async () => this.embeddings ? this.localIndex.status(this.embeddings) : null,
        build: async (operation = {}) => {
          if (!this.embeddings) throw new Error("No embedding provider is configured.");
          const id2 = runId("index");
          try {
            return await this.localIndex.build(this.embeddings, id2, operation);
          } catch (error) {
            if (isAbortError(error)) {
              this.events.emit({ type: "operation-cancelled", runId: id2 });
            }
            throw error;
          }
        },
        clear: () => this.localIndex.clear(this.embeddings)
      };
      this.cache = {
        clear: () => this.repository.clear(),
        stats: () => this.repository.stats()
      };
    }
    manifest;
    events;
    annotations;
    citations = {
      format: formatCitation,
      forEvidence: (evidence) => citationForEvidence(evidence)
    };
    publication;
    records;
    cache;
    /** Locally computed vectors for embedding models other than the one the publication shipped with. */
    index;
    repository;
    localIndex;
    embeddings;
    searchEngine;
    researchEngine;
    hasEmbeddings;
    hasGeneration;
    static async create(options) {
      const events = new EventBus();
      const [manifest, descriptors] = await Promise.all([
        options.dataSource.getManifest(),
        options.dataSource.getChunkDescriptors()
      ]);
      const repository = new RecordRepository(options.dataSource, descriptors, events, options.cache);
      return new DerridAIClient(manifest, options, repository, events);
    }
    async search(request2) {
      const id2 = runId("search");
      try {
        return await this.searchEngine.search(request2, id2);
      } catch (error) {
        if (isAbortError(error)) {
          this.events.emit({ type: "operation-cancelled", runId: id2 });
        }
        throw error;
      }
    }
    async research(request2) {
      const id2 = runId("research");
      try {
        return await this.researchEngine.run(request2, id2);
      } catch (error) {
        if (isAbortError(error)) {
          this.events.emit({ type: "operation-cancelled", runId: id2 });
        }
        throw error;
      }
    }
    async capabilities() {
      return {
        browse: this.manifest.features?.browse !== false,
        lexicalSearch: this.manifest.features?.lexical_search !== false,
        semanticSearch: Boolean(this.manifest.features?.semantic_search),
        annotations: this.manifest.features?.local_annotations !== false,
        research: this.manifest.features?.research !== false,
        publicationVectors: {
          available: Boolean(
            this.manifest.features?.semantic_search && this.manifest.vector_index?.dimension
          ),
          model: this.manifest.vector_index?.model,
          dimension: this.manifest.vector_index?.dimension
        },
        provider: {
          embeddings: this.hasEmbeddings,
          generation: this.hasGeneration
        },
        localIndex: this.embeddings ? await this.localIndex.status(this.embeddings) : null
      };
    }
  }
  async function createClient(options) {
    return DerridAIClient.create(options);
  }
  function throwIfAborted(signal) {
    if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
  }
  function decodeBase64Bytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }
  function decodeRecords(value) {
    const bytes = decodeBase64Bytes(value);
    const decoded = JSON.parse(new TextDecoder("utf-8").decode(bytes));
    if (!Array.isArray(decoded)) throw new Error("Published record chunk is invalid.");
    return decoded;
  }
  function decodeFloat32(value) {
    if (!value) return new Float32Array();
    const bytes = decodeBase64Bytes(value);
    if (bytes.byteLength % 4 !== 0) throw new Error("Published vector chunk is invalid.");
    const count = bytes.byteLength / 4;
    const nativeLittleEndian = new Uint8Array(new Uint16Array([1]).buffer)[0] === 1;
    if (nativeLittleEndian) return new Float32Array(bytes.buffer, bytes.byteOffset, count);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    const values = new Float32Array(count);
    for (let index = 0; index < count; index += 1) {
      values[index] = view.getFloat32(index * 4, true);
    }
    return values;
  }
  class InlineDataSource {
    constructor(publication) {
      this.publication = publication;
      this.chunksById = new Map(publication.chunks.map((chunk) => [chunk.id, chunk]));
    }
    publication;
    chunksById;
    async getManifest(options = {}) {
      throwIfAborted(options.signal);
      return this.publication.manifest;
    }
    async getChunkDescriptors(options = {}) {
      throwIfAborted(options.signal);
      return this.publication.chunks.map((chunk) => ({
        id: chunk.id,
        work: chunk.work,
        recordCount: chunk.record_count,
        hasVectors: Boolean(chunk.vector_ids?.length && chunk.vectors_b64)
      }));
    }
    async loadRecords(chunkId, options = {}) {
      throwIfAborted(options.signal);
      const chunk = this.chunksById.get(chunkId);
      if (!chunk) throw new Error(`Unknown publication chunk: ${chunkId}`);
      const records = decodeRecords(chunk.records_b64);
      throwIfAborted(options.signal);
      return records;
    }
    async loadVectors(chunkId, options = {}) {
      throwIfAborted(options.signal);
      const chunk = this.chunksById.get(chunkId);
      if (!chunk) throw new Error(`Unknown publication chunk: ${chunkId}`);
      const dimension = Number(this.publication.manifest.vector_index?.dimension || 0);
      const ids = chunk.vector_ids ?? [];
      if (!dimension || !ids.length || !chunk.vectors_b64) return null;
      const values = decodeFloat32(chunk.vectors_b64);
      if (values.length !== ids.length * dimension) {
        throw new Error("Published vector chunk does not match its embedding contract.");
      }
      return { ids: [...ids], dimension, values };
    }
  }
  class HttpDataSource {
    constructor(options) {
      this.options = options;
      this.fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);
    }
    options;
    manifestValue = null;
    descriptors = null;
    fetchImpl;
    async json(url, options) {
      const response = await this.fetchImpl(url, { signal: options.signal });
      if (!response.ok) throw new Error(`Unable to load publication asset (${response.status}).`);
      return await response.json();
    }
    async getManifest(options = {}) {
      if (!this.manifestValue) {
        this.manifestValue = await this.json(this.options.manifest, options);
      }
      return this.manifestValue;
    }
    async getChunkDescriptors(options = {}) {
      if (this.descriptors) return this.descriptors;
      const manifest = await this.getManifest(options);
      const raw = manifest["chunks"];
      if (!Array.isArray(raw)) {
        throw new Error("HTTP publication manifest must expose chunk descriptors.");
      }
      this.descriptors = raw.map((item) => {
        const chunk = item;
        return {
          id: String(chunk.id),
          work: chunk.work == null ? void 0 : String(chunk.work),
          recordCount: Number(chunk.record_count || 0),
          hasVectors: Boolean(chunk.has_vectors)
        };
      });
      return this.descriptors;
    }
    chunkUrl(chunkId) {
      return typeof this.options.chunks === "function" ? this.options.chunks(chunkId) : this.options.chunks.replace("{id}", encodeURIComponent(chunkId));
    }
    async loadRecords(chunkId, options = {}) {
      const payload = await this.json(this.chunkUrl(chunkId), options);
      return payload.records;
    }
    async loadVectors(chunkId, options = {}) {
      const payload = await this.json(this.chunkUrl(chunkId), options);
      const manifest = await this.getManifest(options);
      const dimension = Number(manifest.vector_index?.dimension || 0);
      const ids = payload.vector_ids ?? [];
      if (!dimension || !ids.length || !payload.vectors_b64) return null;
      const values = decodeFloat32(payload.vectors_b64);
      if (values.length !== ids.length * dimension) {
        throw new Error("Published vector chunk does not match its embedding contract.");
      }
      return { ids, dimension, values };
    }
  }
  const dataSources = {
    inline: (publication) => new InlineDataSource(publication),
    http: (options) => new HttpDataSource(options)
  };
  const version = "0.1.1";
  exports.BrowserStorage = BrowserStorage;
  exports.DerridAIClient = DerridAIClient;
  exports.HttpDataSource = HttpDataSource;
  exports.IndexedDbVectorStore = IndexedDbVectorStore;
  exports.InlineDataSource = InlineDataSource;
  exports.MemoryStorage = MemoryStorage;
  exports.MemoryVectorStore = MemoryVectorStore;
  exports.createClient = createClient;
  exports.dataSources = dataSources;
  exports.embeddingFingerprint = embeddingFingerprint;
  exports.matchesPublicationModel = matchesPublicationModel;
  exports.storage = storage;
  exports.vectorIndex = vectorIndex;
  exports.version = version;
  Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
  return exports;
})({});
