import type { Preview } from "@storybook/vue3-vite";
import { setup } from "@storybook/vue3-vite";
import { createPinia } from "pinia";
import "../src/style.css";
import "../src/styles/tokens.css";

// Storybook runs outside the application bootstrap path, so install the same
// global state plugin once for every story. Individual stories remain free to
// set the small slice of store state they need.
setup((app) => {
  app.use(createPinia());
});

function directionForLocale(locale: string) {
  try {
    const script = new Intl.Locale(locale).maximize().script || "";
    return ["Arab", "Hebr", "Syrc", "Thaa", "Nkoo", "Adlm", "Rohg", "Mand"].includes(script) ? "rtl" : "ltr";
  } catch {
    return "ltr";
  }
}

const preview: Preview = {
  globalTypes: {
    locale: {
      description: "Document language used to review localized layouts",
      toolbar: {
        icon: "globe",
        items: [
          { value: "en-US", title: "English (United States)" },
          { value: "fr-CA", title: "Français" },
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: {
    locale: "en-US",
    // Static Storybook builds are scanned explicitly by Playwright in CI. Avoid
    // racing the addon's automatic axe run against the CI-owned scan. Local
    // Storybook development remains automatic.
    a11y: { manual: import.meta.env.PROD },
  },
  parameters: {
    layout: "padded",
    a11y: { test: "error" },
    controls: { expanded: true },
  },
  decorators: [
    (story, context) => {
      const locale = String(context.parameters.locale || context.globals.locale || "en-US");
      document.documentElement.lang = locale;
      document.documentElement.dir = directionForLocale(locale);
      return { components: { story }, template: "<story />" };
    },
  ],
};

export default preview;
