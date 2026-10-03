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

import * as runtime from "./runtime.js";

// Each export reads the runtime when it is called, not when this module loads, so a test that mocks only part of the
// runtime does not fail just by importing the stores.

export const getNavItems = (...args: Parameters<typeof runtime.getNavItems>) =>
  runtime.getNavItems(...args);
export const getShellSnapshot = (...args: Parameters<typeof runtime.getShellSnapshot>) =>
  runtime.getShellSnapshot(...args);
export const setTranslationDictionary = (
  ...args: Parameters<typeof runtime.setTranslationDictionary>
) => runtime.setTranslationDictionary(...args);
export const renderView = (...args: Parameters<typeof runtime.renderView>) =>
  runtime.renderView(...args);
export const setUserContext = (...args: Parameters<typeof runtime.setUserContext>) =>
  runtime.setUserContext(...args);
export const setShellRefreshHook = (...args: Parameters<typeof runtime.setShellRefreshHook>) =>
  runtime.setShellRefreshHook(...args);
export const setUrlSyncHook = (...args: Parameters<typeof runtime.setUrlSyncHook>) =>
  runtime.setUrlSyncHook(...args);
export const bootstrapRuntime = (...args: Parameters<typeof runtime.bootstrapRuntime>) =>
  runtime.bootstrapRuntime(...args);
export const syncFromLocation = (...args: Parameters<typeof runtime.syncFromLocation>) =>
  runtime.syncFromLocation(...args);
export const repaintAfterLocationChange = (
  ...args: Parameters<typeof runtime.repaintAfterLocationChange>
) => runtime.repaintAfterLocationChange(...args);
export const viewForPath = (...args: Parameters<typeof runtime.viewForPath>) =>
  runtime.viewForPath(...args);
export const responseCacheStore = (...args: Parameters<typeof runtime.responseCacheStore>) =>
  runtime.responseCacheStore(...args);
export const getResponseFaqPage = (...args: Parameters<typeof runtime.getResponseFaqPage>) =>
  runtime.getResponseFaqPage(...args);
export const gradeResponseFaqRecord = (
  ...args: Parameters<typeof runtime.gradeResponseFaqRecord>
) => runtime.gradeResponseFaqRecord(...args);
export const rerunResponseFaqRecord = (
  ...args: Parameters<typeof runtime.rerunResponseFaqRecord>
) => runtime.rerunResponseFaqRecord(...args);

export default runtime;
