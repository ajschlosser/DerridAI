import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AuthScreen from "../../src/components/AuthScreen.vue";
import pkg from "../../package.json";

describe("AuthScreen", () => {
  it("never shows a version other than the package version", () => {
    const text=mount(AuthScreen).text();
    for(const found of text.match(/\d+\.\d+\.\d+/g)??[])expect(found).toBe(pkg.version);
  });

  it("shows the build stamp next to the product name", () => {
    expect(mount(AuthScreen).text()).toContain(`DerridAI ${pkg.version} (vitest)`);
  });
});

describe("AuthScreen lockout", () => {
  it("tells the user how long to wait when the server locks the username", async () => {
    const { flushPromises } = await import("@vue/test-utils");
    const { useAuthStore } = await import("../../src/stores/auth");
    const { ApiError } = await import("../../src/api/http");
    const wrapper = mount(AuthScreen);
    const auth = useAuthStore();
    auth.bootstrapRequired = false;
    auth.login = (async () => { throw new ApiError("HTTP 429 · locked", 429, { detail: { code: "login_locked", retry_after_seconds: 125 } }); }) as never;
    await wrapper.get("input[autocomplete=username]").setValue("scholar");
    await wrapper.get("input[type=password]").setValue("wrong-guess");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Try again in 3 minute(s)");
  });

  it("shows other sign-in errors unchanged", async () => {
    const { flushPromises } = await import("@vue/test-utils");
    const { useAuthStore } = await import("../../src/stores/auth");
    const { ApiError } = await import("../../src/api/http");
    const wrapper = mount(AuthScreen);
    const auth = useAuthStore();
    auth.bootstrapRequired = false;
    auth.login = (async () => { throw new ApiError("HTTP 401 · Invalid username or password.", 401); }) as never;
    await wrapper.get("input[autocomplete=username]").setValue("scholar");
    await wrapper.get("input[type=password]").setValue("wrong-guess");
    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(wrapper.text()).toContain("Invalid username or password.");
  });
});
