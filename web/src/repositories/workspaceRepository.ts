// Copyright 2026 Aaron John Schlosser, PhD.

export interface WorkspaceRecord {
  work?: string;
  document_title?: string;
  text?: string;
  needs_review?: boolean;
  updates?: unknown[];
}

export interface WorkspaceFile {
  id: string;
  name: string;
  records: WorkspaceRecord[];
}

const databaseName = "derridai-corpus-viewer";

function result<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function loadWorkspaceFiles(userId?: number): Promise<WorkspaceFile[]> {
  if (typeof indexedDB === "undefined") return [];
  const request = indexedDB.open(userId ? `${databaseName}-researcher-${userId}` : databaseName, 2);
  const database = await result(request);
  try {
    if (!database.objectStoreNames.contains("files")) return [];
    const transaction = database.transaction("files", "readonly");
    const files = await result(transaction.objectStore("files").getAll());
    return files.filter((file): file is WorkspaceFile => Array.isArray(file?.records));
  } finally {
    database.close();
  }
}
