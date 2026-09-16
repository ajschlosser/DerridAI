import type { Meta, StoryObj } from "@storybook/vue3";
import SearchResultLayoutSwitcher from "./SearchResultLayoutSwitcher.vue";
const meta:Meta<typeof SearchResultLayoutSwitcher>={title:"Search/Search Result Layout Switcher",component:SearchResultLayoutSwitcher,args:{modelValue:"compact"}};export default meta;type Story=StoryObj<typeof SearchResultLayoutSwitcher>;export const Compact:Story={};export const Cards:Story={args:{modelValue:"cards"}};
