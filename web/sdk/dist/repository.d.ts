import { EventBus } from "./events";
import type { ChunkDescriptor, PublicationDataSource, PublicationRecord, SearchFilters } from "./types";
export declare class RecordRepository {
    private readonly dataSource;
    private readonly descriptors;
    private readonly events;
    private readonly recordChunks;
    private readonly vectorChunks;
    private readonly vectorsByRecordId;
    constructor(dataSource: PublicationDataSource, descriptors: ChunkDescriptor[], events: EventBus, cache?: {
        recordChunks?: number;
        vectorChunks?: number;
    });
    private selectedDescriptors;
    private loadRecords;
    private loadVectors;
    candidates(filters: SearchFilters, locale: string, runId: string, signal?: AbortSignal): Promise<{
        records: PublicationRecord[];
        chunksLoaded: number;
    }>;
    totalRecords(): number;
    /** Visit every Record chunk in publication order, yielding to the browser between chunks. */
    eachChunk(signal: AbortSignal | undefined, visit: (records: PublicationRecord[], index: number, total: number) => Promise<void>): Promise<void>;
    ensureVectors(filters: SearchFilters, runId: string, signal?: AbortSignal): Promise<void>;
    vector(recordId: string): Float32Array | undefined;
    get(recordId: string, signal?: AbortSignal): Promise<PublicationRecord | null>;
    clear(): void;
    stats(): {
        recordChunks: number;
        vectorChunks: number;
        vectors: number;
    };
}
//# sourceMappingURL=repository.d.ts.map