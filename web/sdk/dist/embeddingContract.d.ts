import type { EmbeddingContract, ProviderDescriptor } from "./types";
export interface EmbeddingContractMismatch {
    field: "model" | "revision";
    expected: string;
    actual: string;
}
export declare function embeddingDescriptorMismatches(contract: EmbeddingContract | undefined, descriptor: ProviderDescriptor): EmbeddingContractMismatch[];
//# sourceMappingURL=embeddingContract.d.ts.map