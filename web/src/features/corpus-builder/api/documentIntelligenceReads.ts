/* Copyright 2026 Aaron John Schlosser, PhD. */
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
  const data = await execute(
    CorpusDocumentIntelligenceDocument,
    { build_id: buildId },
    options,
  );
  const value = data.corpus_build.document_intelligence;
  if (!value) return null;
  return value as DocumentIntelligenceRun;
}
