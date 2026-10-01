import { createApp } from "vue";
import { createPinia } from "pinia";
import { VueQueryPlugin } from "@tanstack/vue-query";
import App from "./App.vue";
import { queryClient } from "./realtime/dataQuery";
import router from "./router";
import "./style.css";
import "./styles/tokens.css";
import "./styles/page.css";

createApp(App).use(createPinia()).use(VueQueryPlugin, { queryClient }).use(router).mount("#app");
