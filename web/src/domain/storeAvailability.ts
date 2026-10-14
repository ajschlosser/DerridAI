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

import { isResponseCacheStore } from "./recordPayloads";
import { localRecordKey } from "./recordTableHelpers";
import { tr } from "./sharedTranslate";
import { state } from "./sharedUrlState";

// Which vector stores and Chroma ids the loaded corpus can use, over the shared state.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Any = any;

export function recordStores(): Any[] {
  return state.stores.filter((store: Any) => !isResponseCacheStore(store));
}
export function corpusStoreExists(name: string): boolean {
  return Boolean(name && recordStores().some((store) => store.name === name));
}
export function hasChromaService(): boolean {
  return state.health?.chroma?.available === true;
}
export function hasCorpusDb(): boolean {
  return hasChromaService() && recordStores().length > 0;
}
export function dbUnavailableReason(): string {
  if (!hasChromaService())
    return tr(
      "runtime.disabled.chroma_unavailable",
      "ChromaDB is unavailable. Start/connect ChromaDB before using database features.",
    );
  if (!recordStores().length)
    return tr(
      "runtime.disabled.create_corpus_db",
      "Create or restore a corpus vector database first.",
    );
  return "";
}
export function storeReceipt(store: string, file: Any, index: Any) {
  return state.upsertState?.[store]?.[localRecordKey(file, index)] || null;
}
export function candidateChromaIds(file: Any, index: Any, record: Any): string[] {
  const ids: string[] = [];
  const receipt = storeReceipt(state.activeStore, file, index);
  if (receipt?.chroma_id) ids.push(receipt.chroma_id);
  const logical = record?.record_id;
  if (logical != null && String(logical) !== "") {
    ids.push(String(logical));
    ids.push(`${file.name}::${logical}`);
  }
  return [...new Set(ids)];
}
