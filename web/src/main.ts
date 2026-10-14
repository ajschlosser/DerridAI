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

import { createApp } from "vue";
import { createPinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import App from "./App.vue";
import { queryClient } from "./realtime/dataQuery";
import router from "./router";
import { installStaleChunkRecovery } from "./router/staleChunkRecovery";
import "./style.css";
import "./styles/tokens.css";
import "./styles/page.css";

// Install before the first route navigation can lazy-load a view. A long-lived
// tab can otherwise keep an old entry bundle after Docker replaces the web
// image and request route chunks that no longer exist on the server.
installStaleChunkRecovery(router);

createApp(App).use(createPinia()).use(VueQueryPlugin, { queryClient }).use(router).mount("#app");
