import { EventBus } from "./events";
import { SearchEngine } from "./search";
import type { GenerationProvider, PublicationManifest, ResearchRequest, ResearchResponse } from "./types";
export declare class ResearchEngine {
    private readonly manifest;
    private readonly searchEngine;
    private readonly events;
    private readonly generation?;
    constructor(manifest: PublicationManifest, searchEngine: SearchEngine, events: EventBus, generation?: GenerationProvider | undefined);
    run(request: ResearchRequest, runId: string): Promise<ResearchResponse>;
}
//# sourceMappingURL=research.d.ts.map