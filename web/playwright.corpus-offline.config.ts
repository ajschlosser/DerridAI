// Copyright 2026 Aaron John Schlosser, PhD.
import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

// Serve built assets through Playwright routing when local preview servers are unavailable.
process.env.CORPUS_OFFLINE_APP="1";
export default defineConfig({...base,webServer:[],testMatch:["**/corpus-review-layout.spec.ts","**/corpus-build-status.spec.ts","**/corpus-builder-theme-sweep.spec.ts"]});
