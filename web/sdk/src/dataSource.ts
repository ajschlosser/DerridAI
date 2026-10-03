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

import type {
  ChunkDescriptor,
  OperationOptions,
  PublicationDataSource,
  PublicationManifest,
  PublicationRecord,
  VectorChunk,
} from "./types";

export interface InlinePublicationChunk {
  id: string;
  work?: string;
  record_count: number;
  records_b64: string;
  vector_ids?: string[];
  vectors_b64?: string;
}

export interface InlinePublicationPackage {
  manifest: PublicationManifest;
  chunks: InlinePublicationChunk[];
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException("Operation aborted.", "AbortError");
}

function decodeBase64Bytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

function decodeRecords(value: string): PublicationRecord[] {
  const bytes = decodeBase64Bytes(value);
  const decoded = JSON.parse(new TextDecoder("utf-8").decode(bytes)) as unknown;
  if (!Array.isArray(decoded)) throw new Error("Published record chunk is invalid.");
  return decoded as PublicationRecord[];
}

function decodeFloat32(value: string): Float32Array {
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

export class InlineDataSource implements PublicationDataSource {
  private readonly chunksById: Map<string, InlinePublicationChunk>;

  constructor(private readonly publication: InlinePublicationPackage) {
    this.chunksById = new Map(publication.chunks.map((chunk) => [chunk.id, chunk]));
  }

  async getManifest(options: OperationOptions = {}): Promise<PublicationManifest> {
    throwIfAborted(options.signal);
    return this.publication.manifest;
  }

  async getChunkDescriptors(options: OperationOptions = {}): Promise<ChunkDescriptor[]> {
    throwIfAborted(options.signal);
    return this.publication.chunks.map((chunk) => ({
      id: chunk.id,
      work: chunk.work,
      recordCount: chunk.record_count,
      hasVectors: Boolean(chunk.vector_ids?.length && chunk.vectors_b64),
    }));
  }

  async loadRecords(chunkId: string, options: OperationOptions = {}): Promise<PublicationRecord[]> {
    throwIfAborted(options.signal);
    const chunk = this.chunksById.get(chunkId);
    if (!chunk) throw new Error(`Unknown publication chunk: ${chunkId}`);
    const records = decodeRecords(chunk.records_b64);
    throwIfAborted(options.signal);
    return records;
  }

  async loadVectors(chunkId: string, options: OperationOptions = {}): Promise<VectorChunk | null> {
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

export interface HttpDataSourceOptions {
  manifest: string;
  chunks: string | ((chunkId: string) => string);
  fetch?: typeof globalThis.fetch;
}

interface HttpChunkPayload {
  id: string;
  work?: string;
  records: PublicationRecord[];
  vector_ids?: string[];
  vectors_b64?: string;
}

export class HttpDataSource implements PublicationDataSource {
  private manifestValue: PublicationManifest | null = null;
  private descriptors: ChunkDescriptor[] | null = null;
  private readonly fetchImpl: typeof globalThis.fetch;

  constructor(private readonly options: HttpDataSourceOptions) {
    this.fetchImpl = options.fetch ?? globalThis.fetch.bind(globalThis);
  }

  private async json<T>(url: string, options: OperationOptions): Promise<T> {
    const response = await this.fetchImpl(url, { signal: options.signal });
    if (!response.ok) throw new Error(`Unable to load publication asset (${response.status}).`);
    return (await response.json()) as T;
  }

  async getManifest(options: OperationOptions = {}): Promise<PublicationManifest> {
    if (!this.manifestValue) {
      this.manifestValue = await this.json<PublicationManifest>(this.options.manifest, options);
    }
    return this.manifestValue;
  }

  async getChunkDescriptors(options: OperationOptions = {}): Promise<ChunkDescriptor[]> {
    if (this.descriptors) return this.descriptors;
    const manifest = await this.getManifest(options);
    const raw = manifest["chunks"];
    if (!Array.isArray(raw)) {
      throw new Error("HTTP publication manifest must expose chunk descriptors.");
    }
    this.descriptors = raw.map((item) => {
      const chunk = item as Record<string, unknown>;
      return {
        id: String(chunk.id),
        work: chunk.work == null ? undefined : String(chunk.work),
        recordCount: Number(chunk.record_count || 0),
        hasVectors: Boolean(chunk.has_vectors),
      };
    });
    return this.descriptors;
  }

  private chunkUrl(chunkId: string): string {
    return typeof this.options.chunks === "function"
      ? this.options.chunks(chunkId)
      : this.options.chunks.replace("{id}", encodeURIComponent(chunkId));
  }

  async loadRecords(chunkId: string, options: OperationOptions = {}): Promise<PublicationRecord[]> {
    const payload = await this.json<HttpChunkPayload>(this.chunkUrl(chunkId), options);
    return payload.records;
  }

  async loadVectors(chunkId: string, options: OperationOptions = {}): Promise<VectorChunk | null> {
    const payload = await this.json<HttpChunkPayload>(this.chunkUrl(chunkId), options);
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

export const dataSources = {
  inline: (publication: InlinePublicationPackage): PublicationDataSource =>
    new InlineDataSource(publication),
  http: (options: HttpDataSourceOptions): PublicationDataSource => new HttpDataSource(options),
};
