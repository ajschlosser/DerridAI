import type { ProviderDescriptor, VectorIndexStore, VectorIndexSummary } from "./types";
/** Stable identity of the embedding model that produced a set of vectors. */
export declare function embeddingFingerprint(descriptor: ProviderDescriptor): string;
/** Vectors are comparable only when the model is exactly the one that embedded the publication. */
export declare function matchesPublicationModel(descriptor: ProviderDescriptor, contract: {
    model?: string;
    revision?: string;
} | undefined): boolean;
export declare class MemoryVectorStore implements VectorIndexStore {
    readonly persistent = false;
    private readonly indexes;
    ids(publicationId: string, fingerprint: string): Promise<Set<string>>;
    load(publicationId: string, fingerprint: string): Promise<{
        dimension: number;
        vectors: Map<string, Float32Array>;
    } | null>;
    put(publicationId: string, fingerprint: string, descriptor: ProviderDescriptor, entries: {
        recordId: string;
        vector: Float32Array;
    }[]): Promise<void>;
    summaries(publicationId: string): Promise<VectorIndexSummary[]>;
    clear(publicationId: string, fingerprint?: string): Promise<void>;
}
/**
 * Persistent browser store for locally computed embeddings. One index per publication and embedding model;
 * these are derived data and can always be rebuilt from the published Records.
 */
export declare class IndexedDbVectorStore implements VectorIndexStore {
    private readonly name;
    private readonly factory;
    readonly persistent = true;
    private opened?;
    constructor(name?: string, factory?: IDBFactory);
    private database;
    private range;
    ids(publicationId: string, fingerprint: string): Promise<Set<string>>;
    load(publicationId: string, fingerprint: string): Promise<{
        dimension: number;
        vectors: Map<string, Float32Array>;
    } | null>;
    put(publicationId: string, fingerprint: string, descriptor: ProviderDescriptor, entries: {
        recordId: string;
        vector: Float32Array;
    }[]): Promise<void>;
    summaries(publicationId: string): Promise<VectorIndexSummary[]>;
    clear(publicationId: string, fingerprint?: string): Promise<void>;
}
/** IndexedDB when the browser offers and allows it; otherwise a session-only memory store. */
export declare function defaultVectorStore(): VectorIndexStore;
export declare const vectorIndex: {
    indexedDb: (name?: string) => VectorIndexStore;
    /** IndexedDB that degrades to memory for the session if the browser refuses it. */
    resilient: (name?: string) => VectorIndexStore;
    memory: () => VectorIndexStore;
};
//# sourceMappingURL=vectorIndex.d.ts.map