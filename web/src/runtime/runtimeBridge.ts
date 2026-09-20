/* Copyright 2026 Aaron John Schlosser, PhD. */

import * as runtime from "./runtime.js";

export const getNavItems = runtime.getNavItems;
export const getShellSnapshot = runtime.getShellSnapshot;
export const setTranslationDictionary = runtime.setTranslationDictionary;
export const renderView = runtime.renderView;
export const setUserContext = runtime.setUserContext;
export const setShellRefreshHook = runtime.setShellRefreshHook;
export const setUrlSyncHook = runtime.setUrlSyncHook;
export const bootstrapRuntime = runtime.bootstrapRuntime;
export const pauseRuntime = runtime.pauseRuntime;
export const navigateView = runtime.navigateView;
export const triggerBack = runtime.triggerBack;
export const triggerForward = runtime.triggerForward;
export const triggerImport = runtime.triggerImport;
export const triggerOperations = runtime.triggerOperations;

export default runtime;
