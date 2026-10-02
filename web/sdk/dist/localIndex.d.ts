import { EventBus } from "./events";
import { RecordRepository } from "./repository";
import type { EmbeddingProvider, LocalIndexBuildOptions, LocalIndexStatus, PublicationManifest, VectorIndexStore } from "./types";
/**
 * Vectors computed in this client with the reader's own embedding model. They are derived from the published
 * Records, keyed by publication and exact model, and never replace or alter the publication's own vectors.
 */
export declare class LocalVectorIndex {
    private readonly manifest;
    private readonly repository;
    private readonly store;
    private readonly events;
    private readonly loaded;
    constructor(manifest: PublicationManifest, repository: RecordRepository, store: VectorIndexStore, events: EventBus);
    private get publicationId();
    private textOf;
    usesPublishedVectors(provider: EmbeddingProvider): boolean;
    status(provider: EmbeddingProvider): Promise<LocalIndexStatus>;
    vectorsFor(provider: EmbeddingProvider): Promise<{
        dimension: number;
        vectors: Map<string, Float32Array>;
    } | null>;
    build(provider: EmbeddingProvider, runId: string, options?: LocalIndexBuildOptions): Promise<LocalIndexStatus>;
    clear(provider?: EmbeddingProvider): Promise<void>;
    summaries(): ReturnType<VectorIndexStore["summaries"]>;
}
//# sourceMappingURL=localIndex.d.ts.map