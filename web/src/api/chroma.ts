import { apiRequest } from "./http";
export interface ChromaCollection { name:string; count:number; metadata?:Record<string,unknown>; }
export const chromaApi = {
  collections: () => apiRequest<ChromaCollection[]>("/api/chroma/collections"),
};
