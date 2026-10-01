// Copyright 2026 Aaron John Schlosser, PhD.

export type SearchMode = "keyword" | "semantic" | "hybrid";

export interface SourceSpan {
  source_document_id: string;
  source_unit_id?: string;
  printed_page?: string | number;
  physical_page?: string | number;
  [key: string]: unknown;
}

export interface PublicationRecord {
  record_id: string;
  source_document_id: string;
  text: string;
  source_spans: SourceSpan[];
  work?: string;
  citation?: string;
  full_citation?: string;
  printed_page?: string | number;
  page_start?: string | number;
  page_end?: string | number;
  page?: string | number;
  speaker?: string;
  quoted_speaker?: string;
  position_holder?: string;
  stance?: string;
  target?: string;
  discourse_role?: string;
  record_revision?: string;
  [key: string]: unknown;
}

export interface WorkSummary {
  work: string;
  record_count: number;
  authors?: string[];
  years?: string[];
  citation?: string;
}

export interface EmbeddingContract {
  provider?: string;
  model?: string;
  dimension?: number | null;
  revision?: string;
  distance_metric?: "cosine" | "dot" | "euclidean" | string;
  text_field?: string;
}

export interface PublicationFeatures {
  browse?: boolean;
  lexical_search?: boolean;
  semantic_search?: boolean;
  semantic_record_count?: number;
  local_annotations?: boolean;
  research?: boolean;
  shared_state?: boolean;
  progressive_work_loading?: boolean;
  [key: string]: unknown;
}

export interface PublicationManifest {
  format: string;
  publication_id: string;
  corpus_id?: string;
  publication_version?: number;
  celf_version?: string;
  created_at?: string;
  title: string;
  description?: string;
  locale?: string;
  works: WorkSummary[];
  vector_index?: EmbeddingContract;
  source_collection?: Record<string, unknown>;
  features?: PublicationFeatures;
  integrity?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ChunkDescriptor {
  id: string;
  work?: string;
  recordCount: number;
  hasVectors: boolean;
}

export interface VectorChunk {
  ids: string[];
  dimension: number;
  values: Float32Array;
}

export interface PublicationDataSource {
  getManifest(options?: OperationOptions): Promise<PublicationManifest>;
  getChunkDescriptors(options?: OperationOptions): Promise<ChunkDescriptor[]>;
  loadRecords(chunkId: string, options?: OperationOptions): Promise<PublicationRecord[]>;
  loadVectors?(chunkId: string, options?: OperationOptions): Promise<VectorChunk | null>;
}

export interface OperationOptions {
  signal?: AbortSignal;
}

export interface ProviderDescriptor {
  id?: string;
  type?: string;
  model?: string;
  revision?: string;
  /** Anything besides the model that changes the vectors (for example text prefixes). */
  variant?: string;
  [key: string]: unknown;
}

export interface EmbedOptions extends OperationOptions {
  /** Retrieval models often embed queries and documents differently. */
  purpose?: "query" | "document";
}

export interface EmbeddingResult {
  vectors: number[][];
  provider?: ProviderDescriptor;
}

export interface EmbeddingProvider {
  descriptor(): ProviderDescriptor;
  embed(input: string[], options?: EmbedOptions): Promise<EmbeddingResult>;
}

export interface GenerationRequest {
  prompt: string;
  question: string;
  evidencePacket: EvidencePacket;
}

export interface GenerationResult {
  text: string;
  provider?: ProviderDescriptor;
}

export interface GenerationProvider {
  descriptor(): ProviderDescriptor;
  generate(request: GenerationRequest, options?: OperationOptions): Promise<GenerationResult>;
}

export interface VectorIndexSummary {
  publicationId: string;
  fingerprint: string;
  model: string;
  provider: string;
  dimension: number;
  count: number;
  updatedAt: string;
}

/** Persistent store for vectors computed in this client; derived data that can be rebuilt. */
export interface VectorIndexStore {
  readonly persistent: boolean;
  ids(publicationId: string, fingerprint: string): Promise<Set<string>>;
  load(
    publicationId: string,
    fingerprint: string,
  ): Promise<{ dimension: number; vectors: Map<string, Float32Array> } | null>;
  put(
    publicationId: string,
    fingerprint: string,
    descriptor: ProviderDescriptor,
    entries: { recordId: string; vector: Float32Array }[],
  ): Promise<void>;
  summaries(publicationId: string): Promise<VectorIndexSummary[]>;
  clear(publicationId: string, fingerprint?: string): Promise<void>;
}

export interface LocalIndexStatus {
  /** Whether the supplied embedding model is exactly the one that embedded the publication. */
  usesPublishedVectors: boolean;
  /** True once every embeddable Record has a locally computed vector for the current model. */
  complete: boolean;
  indexed: number;
  total: number;
  persistent: boolean;
  model?: string;
}

export interface LocalIndexBuildOptions extends OperationOptions {
  batchSize?: number;
}

export interface ClientStorage {
  get<T = unknown>(namespace: string, key: string): Promise<T | null>;
  set(namespace: string, key: string, value: unknown): Promise<void>;
  delete(namespace: string, key: string): Promise<void>;
  list<T = unknown>(namespace: string): Promise<T[]>;
}

export interface SearchFilters {
  work?: string | string[];
  [field: string]: unknown;
}

export interface SearchRequest extends OperationOptions {
  query: string;
  mode?: SearchMode;
  filters?: SearchFilters;
  limit?: number;
}

export interface SearchWarning {
  code:
    | "semantic_unavailable"
    | "embedding_provider_unavailable"
    | "embedding_contract_mismatch"
    | "embedding_dimension_mismatch"
    | "local_index_required";
  message: string;
  details?: Record<string, unknown>;
}

export interface SearchResult {
  record: PublicationRecord;
  score: number;
  lexicalScore?: number;
  semanticScore?: number;
  rank: number;
}

export interface SearchResponse {
  results: SearchResult[];
  modeRequested: SearchMode;
  modeUsed: SearchMode;
  warnings: SearchWarning[];
  diagnostics: {
    candidateCount: number;
    chunksLoaded: number;
    semanticAvailable: boolean;
    duplicatesRemoved: number;
  };
}

export interface EvidenceRef {
  evidenceId: string;
  recordId: string;
  recordRevision?: string;
  publicationId: string;
  work?: string;
  citation: string;
  text: string;
  speaker?: string;
  quotedSpeaker?: string;
  positionHolder?: string;
  stance?: string;
  target?: string;
  discourseRole?: string;
}

export interface EvidencePacket {
  publicationId: string;
  evidence: EvidenceRef[];
}

export interface ResearchRequest extends OperationOptions {
  question: string;
  retrieval?: {
    mode?: SearchMode;
    limit?: number;
    evidenceLimit?: number;
    mmrLambda?: number;
    filters?: SearchFilters;
  };
}

export interface ResearchWarning {
  code: "semantic_fallback" | "generation_unavailable";
  message: string;
}

export interface ResearchResponse {
  runId: string;
  publicationId: string;
  question: string;
  answer: string | null;
  evidencePacket: EvidencePacket;
  retrieval: SearchResponse;
  generation: ProviderDescriptor | null;
  warnings: ResearchWarning[];
}

export interface Annotation {
  id: string;
  publication_id: string;
  record_id: string;
  record_revision?: string;
  work?: string;
  quote?: string;
  note?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface AnnotationInput {
  recordId: string;
  recordRevision?: string;
  work?: string;
  quote?: string;
  note?: string;
  tags?: string[];
}

export interface CitationResult {
  plain: string;
  locator: {
    recordId: string;
    printedPageStart?: string | number;
    printedPageEnd?: string | number;
  };
}

export type ClientEvent =
  | { type: "search-start"; runId: string; query: string }
  | {
      type: "load-progress";
      runId: string;
      stage: "records" | "vectors";
      chunkId: string;
      work?: string;
      completed: number;
      total: number;
    }
  | { type: "embedding-start"; runId: string }
  | { type: "index-progress"; runId: string; indexed: number; total: number }
  | { type: "retrieval-complete"; runId: string; resultCount: number }
  | { type: "generation-start"; runId: string }
  | { type: "generation-complete"; runId: string }
  | { type: "operation-cancelled"; runId: string };

export interface DerridAIClientOptions {
  dataSource: PublicationDataSource;
  storage?: ClientStorage;
  embeddings?: EmbeddingProvider;
  generation?: GenerationProvider;
  /** Where locally computed vectors live. Defaults to IndexedDB, or memory when it is unavailable. */
  vectorIndex?: VectorIndexStore;
  locale?: string;
  cache?: {
    recordChunks?: number;
    vectorChunks?: number;
  };
}
