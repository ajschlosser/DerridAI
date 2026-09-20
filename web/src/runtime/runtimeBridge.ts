/* Copyright 2026 Aaron John Schlosser, PhD. */

import * as runtime from "./runtime.js";

// Each export reads the runtime when it is called, not when this module loads, so a test that mocks only part of the
// runtime does not fail just by importing the stores.

export const getNavItems = (...args: Parameters<typeof runtime.getNavItems>) => runtime.getNavItems(...args);
export const getShellSnapshot = (...args: Parameters<typeof runtime.getShellSnapshot>) => runtime.getShellSnapshot(...args);
export const setTranslationDictionary = (...args: Parameters<typeof runtime.setTranslationDictionary>) => runtime.setTranslationDictionary(...args);
export const renderView = (...args: Parameters<typeof runtime.renderView>) => runtime.renderView(...args);
export const setUserContext = (...args: Parameters<typeof runtime.setUserContext>) => runtime.setUserContext(...args);
export const setShellRefreshHook = (...args: Parameters<typeof runtime.setShellRefreshHook>) => runtime.setShellRefreshHook(...args);
export const setUrlSyncHook = (...args: Parameters<typeof runtime.setUrlSyncHook>) => runtime.setUrlSyncHook(...args);
export const bootstrapRuntime = (...args: Parameters<typeof runtime.bootstrapRuntime>) => runtime.bootstrapRuntime(...args);
export const pauseRuntime = (...args: Parameters<typeof runtime.pauseRuntime>) => runtime.pauseRuntime(...args);
export const navigateView = (...args: Parameters<typeof runtime.navigateView>) => runtime.navigateView(...args);
export const triggerBack = (...args: Parameters<typeof runtime.triggerBack>) => runtime.triggerBack(...args);
export const triggerForward = (...args: Parameters<typeof runtime.triggerForward>) => runtime.triggerForward(...args);
export const triggerImport = (...args: Parameters<typeof runtime.triggerImport>) => runtime.triggerImport(...args);
export const triggerOperations = (...args: Parameters<typeof runtime.triggerOperations>) => runtime.triggerOperations(...args);

export default runtime;
