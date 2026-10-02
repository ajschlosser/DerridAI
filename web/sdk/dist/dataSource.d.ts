import type { ChunkDescriptor, OperationOptions, PublicationDataSource, PublicationManifest, PublicationRecord, VectorChunk } from "./types";
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
export declare class InlineDataSource implements PublicationDataSource {
    private readonly publication;
    private readonly chunksById;
    constructor(publication: InlinePublicationPackage);
    getManifest(options?: OperationOptions): Promise<PublicationManifest>;
    getChunkDescriptors(options?: OperationOptions): Promise<ChunkDescriptor[]>;
    loadRecords(chunkId: string, options?: OperationOptions): Promise<PublicationRecord[]>;
    loadVectors(chunkId: string, options?: OperationOptions): Promise<VectorChunk | null>;
}
export interface HttpDataSourceOptions {
    manifest: string;
    chunks: string | ((chunkId: string) => string);
    fetch?: typeof globalThis.fetch;
}
export declare class HttpDataSource implements PublicationDataSource {
    private readonly options;
    private manifestValue;
    private descriptors;
    private readonly fetchImpl;
    constructor(options: HttpDataSourceOptions);
    private json;
    getManifest(options?: OperationOptions): Promise<PublicationManifest>;
    getChunkDescriptors(options?: OperationOptions): Promise<ChunkDescriptor[]>;
    private chunkUrl;
    loadRecords(chunkId: string, options?: OperationOptions): Promise<PublicationRecord[]>;
    loadVectors(chunkId: string, options?: OperationOptions): Promise<VectorChunk | null>;
}
export declare const dataSources: {
    inline: (publication: InlinePublicationPackage) => PublicationDataSource;
    http: (options: HttpDataSourceOptions) => PublicationDataSource;
};
//# sourceMappingURL=dataSource.d.ts.map