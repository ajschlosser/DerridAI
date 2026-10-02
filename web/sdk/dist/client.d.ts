import { AnnotationStore } from "./annotations";
import { formatCitation } from "./citations";
import { EventBus } from "./events";
import { RecordRepository } from "./repository";
import type { DerridAIClientOptions, EvidenceRef, LocalIndexBuildOptions, LocalIndexStatus, PublicationManifest, ResearchRequest, ResearchResponse, SearchRequest, SearchResponse } from "./types";
export declare class DerridAIClient {
    private readonly manifest;
    readonly events: EventBus;
    readonly annotations: AnnotationStore;
    readonly citations: {
        format: typeof formatCitation;
        forEvidence: (evidence: EvidenceRef) => import("./types").CitationResult;
    };
    readonly publication: {
        info: () => PublicationManifest;
        works: () => PublicationManifest["works"];
    };
    readonly records: {
        get: (recordId: string, options?: {
            signal?: AbortSignal;
        }) => ReturnType<RecordRepository["get"]>;
    };
    readonly cache: {
        clear: () => void;
        stats: () => ReturnType<RecordRepository["stats"]>;
    };
    /** Locally computed vectors for embedding models other than the one the publication shipped with. */
    readonly index: {
        status: () => Promise<LocalIndexStatus | null>;
        build: (options?: LocalIndexBuildOptions) => Promise<LocalIndexStatus>;
        clear: () => Promise<void>;
    };
    private readonly repository;
    private readonly localIndex;
    private readonly embeddings?;
    private readonly searchEngine;
    private readonly researchEngine;
    private readonly hasEmbeddings;
    private readonly hasGeneration;
    private constructor();
    static create(options: DerridAIClientOptions): Promise<DerridAIClient>;
    search(request: SearchRequest): Promise<SearchResponse>;
    research(request: ResearchRequest): Promise<ResearchResponse>;
    capabilities(): Promise<{
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
        localIndex: LocalIndexStatus | null;
    }>;
}
export declare function createClient(options: DerridAIClientOptions): Promise<DerridAIClient>;
//# sourceMappingURL=client.d.ts.map