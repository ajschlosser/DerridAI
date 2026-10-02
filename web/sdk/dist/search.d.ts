import { EventBus } from "./events";
import type { LocalVectorIndex } from "./localIndex";
import { RecordRepository } from "./repository";
import type { EmbeddingProvider, PublicationManifest, SearchRequest, SearchResponse, SearchResult } from "./types";
export declare class SearchEngine {
    private readonly manifest;
    private readonly repository;
    private readonly events;
    private readonly embeddings?;
    private readonly locale;
    private readonly localIndex?;
    constructor(manifest: PublicationManifest, repository: RecordRepository, events: EventBus, embeddings?: EmbeddingProvider | undefined, locale?: string, localIndex?: LocalVectorIndex | undefined);
    private vectorLookup;
    search(request: SearchRequest, runId: string): Promise<SearchResponse>;
    diversify(items: SearchResult[], limit?: number, lambda?: number): SearchResult[];
    private finish;
}
//# sourceMappingURL=search.d.ts.map