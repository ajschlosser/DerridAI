// Copyright 2026 Aaron John Schlosser, PhD.

import { AnnotationStore } from "./annotations";
import { citationForEvidence, formatCitation } from "./citations";
import { EventBus } from "./events";
import { isAbortError } from "./errors";
import { RecordRepository } from "./repository";
import { ResearchEngine } from "./research";
import { SearchEngine } from "./search";
import { BrowserStorage } from "./storage";
import type {
  DerridAIClientOptions,
  EvidenceRef,
  PublicationManifest,
  ResearchRequest,
  ResearchResponse,
  SearchRequest,
  SearchResponse,
} from "./types";

function runId(prefix: string): string {
  if (globalThis.crypto?.randomUUID) return `${prefix}-${globalThis.crypto.randomUUID()}`;
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export class DerridAIClient {
  readonly events: EventBus;
  readonly annotations: AnnotationStore;
  readonly citations = {
    format: formatCitation,
    forEvidence: (evidence: EvidenceRef) => citationForEvidence(evidence),
  };
  readonly publication: {
    info: () => PublicationManifest;
    works: () => PublicationManifest["works"];
  };
  readonly records: {
    get: (
      recordId: string,
      options?: { signal?: AbortSignal },
    ) => ReturnType<RecordRepository["get"]>;
  };
  readonly cache: {
    clear: () => void;
    stats: () => ReturnType<RecordRepository["stats"]>;
  };

  private readonly repository: RecordRepository;
  private readonly searchEngine: SearchEngine;
  private readonly researchEngine: ResearchEngine;
  private readonly hasEmbeddings: boolean;
  private readonly hasGeneration: boolean;

  private constructor(
    private readonly manifest: PublicationManifest,
    options: DerridAIClientOptions,
    repository: RecordRepository,
    events: EventBus,
  ) {
    this.events = events;
    this.repository = repository;
    this.hasEmbeddings = Boolean(options.embeddings);
    this.hasGeneration = Boolean(options.generation);
    const locale = options.locale ?? manifest.locale ?? "en-US";
    this.searchEngine = new SearchEngine(
      manifest,
      repository,
      this.events,
      options.embeddings,
      locale,
    );
    this.researchEngine = new ResearchEngine(
      manifest,
      this.searchEngine,
      this.events,
      options.generation,
    );
    this.annotations = new AnnotationStore(manifest, options.storage ?? new BrowserStorage());
    this.publication = {
      info: () => this.manifest,
      works: () => [...this.manifest.works],
    };
    this.records = {
      get: (recordId, operation = {}) => this.repository.get(recordId, operation.signal),
    };
    this.cache = {
      clear: () => this.repository.clear(),
      stats: () => this.repository.stats(),
    };
  }

  static async create(options: DerridAIClientOptions): Promise<DerridAIClient> {
    const events = new EventBus();
    const [manifest, descriptors] = await Promise.all([
      options.dataSource.getManifest(),
      options.dataSource.getChunkDescriptors(),
    ]);
    const repository = new RecordRepository(options.dataSource, descriptors, events, options.cache);
    return new DerridAIClient(manifest, options, repository, events);
  }

  async search(request: SearchRequest): Promise<SearchResponse> {
    const id = runId("search");
    try {
      return await this.searchEngine.search(request, id);
    } catch (error) {
      if (isAbortError(error)) {
        this.events.emit({ type: "operation-cancelled", runId: id });
      }
      throw error;
    }
  }

  async research(request: ResearchRequest): Promise<ResearchResponse> {
    const id = runId("research");
    try {
      return await this.researchEngine.run(request, id);
    } catch (error) {
      if (isAbortError(error)) {
        this.events.emit({ type: "operation-cancelled", runId: id });
      }
      throw error;
    }
  }

  async capabilities(): Promise<{
    browse: boolean;
    lexicalSearch: boolean;
    semanticSearch: boolean;
    annotations: boolean;
    research: boolean;
    publicationVectors: {
      available: boolean;
      model?: string;
      dimension?: number | null;
    };
    provider: {
      embeddings: boolean;
      generation: boolean;
    };
  }> {
    return {
      browse: this.manifest.features?.browse !== false,
      lexicalSearch: this.manifest.features?.lexical_search !== false,
      semanticSearch: Boolean(this.manifest.features?.semantic_search),
      annotations: this.manifest.features?.local_annotations !== false,
      research: this.manifest.features?.research !== false,
      publicationVectors: {
        available: Boolean(this.manifest.vector_index?.dimension),
        model: this.manifest.vector_index?.model,
        dimension: this.manifest.vector_index?.dimension,
      },
      provider: {
        embeddings: this.hasEmbeddings,
        generation: this.hasGeneration,
      },
    };
  }
}

export async function createClient(options: DerridAIClientOptions): Promise<DerridAIClient> {
  return DerridAIClient.create(options);
}
