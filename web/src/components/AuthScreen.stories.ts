import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { useAuthStore } from "../stores/auth";
import AuthScreen from "./AuthScreen.vue";

const meta = {
  title: "Components/AuthScreen",
  component: AuthScreen,
  parameters: { layout: "fullscreen" },
} satisfies Meta<typeof AuthScreen>;

export default meta;
type Story = StoryObj<typeof meta>;

const authStateDecorator = (bootstrapRequired: boolean) => () => ({
  components: { AuthScreen },
  setup() {
    const auth = useAuthStore();
    auth.bootstrapRequired = bootstrapRequired;
    auth.error = "";
    return {};
  },
  template: "<AuthScreen />",
});

export const SignIn: Story = {
  render: authStateDecorator(false),
};

export const FirstRun: Story = {
  render: authStateDecorator(true),
};
