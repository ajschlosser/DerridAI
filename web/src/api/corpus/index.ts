/* Copyright 2026 Aaron John Schlosser, PhD. */
export * from "./types";
export { corpusSourcesApi } from "./sources";
export { corpusBuildsApi } from "./builds";
export { corpusRecordsApi } from "./records";
export { corpusReviewApi } from "./review";
export { corpusMetadataApi } from "./metadata";
export { corpusPublicationsApi } from "./publications";

import { corpusSourcesApi } from "./sources";
import { corpusBuildsApi } from "./builds";
import { corpusRecordsApi } from "./records";
import { corpusReviewApi } from "./review";
import { corpusMetadataApi } from "./metadata";
import { corpusPublicationsApi } from "./publications";

/** Media-generic Corpus Builder client. Legacy endpoint naming is isolated in compatibility.ts. */
export const corpusBuilderApi = {
  ...corpusSourcesApi,
  ...corpusBuildsApi,
  ...corpusRecordsApi,
  ...corpusReviewApi,
  ...corpusMetadataApi,
  ...corpusPublicationsApi,
};
