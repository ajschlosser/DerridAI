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

import { applyAppearance as applyAppearanceCompat } from "./legacyCompat.js";
import { state } from "./sharedUrlState";

// Appearance preferences live in the shared `appConfig` slice, so applying them needs no legacy runtime. The runtime
// delegates to this same function.
export const applyAppearance = (patch: object = {}) => applyAppearanceCompat(state, patch);
