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

import { createPdfExplorerRenderer } from "./pdfExplorerRenderer";
import { tr, trf } from "./sharedTranslate";
import { state } from "./sharedUrlState";

// The PDF Explorer renderer over the shared state, usable without the legacy runtime. The runtime destructures this
// same instance.
export const pdfExplorerRenderer = createPdfExplorerRenderer({ state, tr, trf });
export const {
  renderPdfCanvas,
  extractPdfPageBrowser,
  extractPdfApi,
  extractPdfPageSmart,
  extractPdfAllSmart,
} = pdfExplorerRenderer;
