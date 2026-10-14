/*
 * This file is part of DerridAI, a cELF-compliant research workspace
 * Copyright © 2026  Aaron John Schlosser, PhD
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

export * from "./types";
export { corpusSourcesApi, sourceListQuery } from "./sources";
export { corpusCaptureApi, type CandidateFilters } from "./capture";
export { corpusBuildsApi } from "./builds";
export { corpusRecordsApi } from "./records";
export { corpusReviewApi } from "./review";
export {
  corpusMetadataApi,
  type MetadataDecisionResult,
  type MetadataPrecedent,
  type MetadataPrecedents,
  type PrecedentCandidateUnit,
  type RecordResearchClaim,
} from "./metadata";
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
