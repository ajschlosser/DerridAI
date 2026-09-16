import type { Preview } from "@storybook/vue3-vite";
import { setup } from "@storybook/vue3-vite";
import { createPinia } from "pinia";
import "../src/style.css";

// Storybook runs outside the application bootstrap path, so install the same
// global state plugin once for every story. Individual stories remain free to
// set the small slice of store state they need.
setup((app) => {
  app.use(createPinia());
});

const preview: Preview = {
  parameters: {
    layout: "centered",
    controls: { expanded: true },
  },
};

export default preview;
