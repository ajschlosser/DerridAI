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

// Late-binding facade over two Vector Stores workflows the runtime still builds: the collection-creation wizard (it
// needs the runtime's work index, store list and modal host) and the upsert-queue launcher (it applies the
// `manageCorpus` capability check). The view imports these forwarders; the runtime registers the implementations once.
// Calling one before registration is an error rather than a silent no-op.
/* eslint-disable @typescript-eslint/no-explicit-any */
type Fn = (...args: any[]) => any;

export const vectorStoreActionNames = [
  "openCollectionCreationWizard",
  "triggerUpsertQueue",
] as const;
export type VectorStoreActionName = (typeof vectorStoreActionNames)[number];
export type VectorStoreActions = Record<VectorStoreActionName, Fn>;

let registered: Partial<VectorStoreActions> | null = null;

/** Called by the runtime with its implementations; pass null to clear (tests). Extra members are ignored. */
export function registerVectorStoreActions(actions: Partial<VectorStoreActions> | null) {
  registered = actions;
}

function forward(name: VectorStoreActionName): Fn {
  return (...args) => {
    const action = registered?.[name];
    if (!action)
      throw new Error(
        `Vector Stores workflow is not ready: ${name} was called before it registered`,
      );
    return action(...args);
  };
}

export const openCollectionCreationWizard = forward("openCollectionCreationWizard");
export const triggerUpsertQueue = forward("triggerUpsertQueue");
