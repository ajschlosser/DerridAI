// Copyright 2026 Aaron John Schlosser, PhD.

export { DerridAIClient, createClient } from "./client";
export { dataSources, HttpDataSource, InlineDataSource } from "./dataSource";
export {
  IndexedDbVectorStore,
  MemoryVectorStore,
  embeddingFingerprint,
  matchesPublicationModel,
  vectorIndex,
} from "./vectorIndex";
export { BrowserStorage, MemoryStorage, storage } from "./storage";
export type * from "./types";

export const version = "0.1.1";
