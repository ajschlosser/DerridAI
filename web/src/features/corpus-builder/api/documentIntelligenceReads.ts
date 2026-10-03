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

/**
 * Read-only Corpus Builder Document Intelligence over GraphQL.
 * Rerun remains a REST command because it changes persisted derived state.
 */
import type { DocumentIntelligenceRun } from "../../../api/corpus";
import { execute, type ExecuteOptions } from "../../../api/graphql/client";
import { CorpusDocumentIntelligenceDocument } from "../../../api/graphql/generated";

export async function readDocumentIntelligence(
  buildId: string,
  options: ExecuteOptions = {},
): Promise<DocumentIntelligenceRun | null> {
  const data = await execute(CorpusDocumentIntelligenceDocument, { build_id: buildId }, options);
  const value = data.corpus_build.document_intelligence;
  if (!value) return null;
  return value as DocumentIntelligenceRun;
}
