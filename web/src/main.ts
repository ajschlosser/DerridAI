import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./style.css";
import "./styles/tokens.css";
import "./styles/page.css";

createApp(App).use(createPinia()).use(router).mount("#app");
