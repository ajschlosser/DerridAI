import type { Annotation, AnnotationInput, ClientStorage, PublicationManifest } from "./types";
export declare class AnnotationStore {
    private readonly storage;
    private readonly namespace;
    constructor(manifest: PublicationManifest, storage: ClientStorage);
    list(filters?: {
        work?: string;
    }): Promise<Annotation[]>;
    get(annotationId: string): Promise<Annotation | null>;
    add(input: AnnotationInput): Promise<Annotation>;
    update(annotationId: string, patch: Partial<Omit<AnnotationInput, "recordId">>): Promise<Annotation>;
    remove(annotationId: string): Promise<void>;
    export(): Promise<{
        version: 1;
        annotations: Annotation[];
    }>;
    import(payload: {
        annotations?: Annotation[];
    }): Promise<number>;
}
//# sourceMappingURL=annotations.d.ts.map