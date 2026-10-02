/* Copyright 2026 Aaron John Schlosser, PhD. */
import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { MAX_REMEMBERED_TITLES, createNavigationHistory } from "../../src/router/navigationHistory";

const Blank = { render: () => null };

function setup(state: () => { back?: string | null; forward?: string | null } | null) {
  const routes = [
    {
      path: "/",
      name: "home",
      component: Blank,
      meta: { titleKey: "nav.home", titleFallback: "Home" },
    },
    {
      path: "/search",
      name: "search",
      component: Blank,
      meta: { titleKey: "nav.search", titleFallback: "Search" },
    },
    { path: "/untitled", name: "untitled", component: Blank },
    { path: "/n/:id", name: "n", component: Blank, meta: { titleFallback: "Numbered" } },
  ];
  const router = createRouter({ history: createMemoryHistory(), routes });
  return { router, history: createNavigationHistory(router, state) };
}

describe("router-owned navigation history", () => {
  it("reports Back from the history state and names the previous page", async () => {
    let current: { back?: string | null; forward?: string | null } | null = { back: null };
    const { router, history } = setup(() => current);
    await router.push("/");
    expect(history.canGoBack.value).toBe(false);
    expect(history.backTitle.value).toBeNull();

    await router.push("/search");
    current = { back: "/", forward: null };
    await router.push("/search?x=1");
    expect(history.canGoBack.value).toBe(true);
    expect(history.backTitle.value).toEqual({ key: "nav.home", fallback: "Home" });
  });

  it("reports Forward and clears it when the history state no longer has a next entry", async () => {
    let current: { back?: string | null; forward?: string | null } | null = {
      back: "/",
      forward: "/search",
    };
    const { router, history } = setup(() => current);
    await router.push("/");
    await router.push("/search");
    expect(history.canGoForward.value).toBe(true);
    expect(history.forwardTitle.value).toEqual({ key: "nav.search", fallback: "Search" });

    current = { back: "/", forward: null };
    history.refresh();
    expect(history.canGoForward.value).toBe(false);
  });

  it("still enables Back for a page it has no title for", async () => {
    const { router, history } = setup(() => ({ back: "/never-visited" }));
    await router.push("/");
    expect(history.canGoBack.value).toBe(true);
    expect(history.backTitle.value).toBeNull();
  });

  it("treats unreadable or missing history state as no history instead of failing navigation", async () => {
    const { router, history } = setup(() => {
      throw new Error("blocked");
    });
    await expect(router.push("/")).resolves.toBeUndefined();
    expect(history.canGoBack.value).toBe(false);
    expect(history.canGoForward.value).toBe(false);
  });

  it("does not remember titles for navigations that failed", async () => {
    const { router, history } = setup(() => ({ back: "/search" }));
    router.beforeEach((to) => (to.name === "search" ? false : true));
    await router.push("/");
    const failure = await router.push("/search");
    expect(failure).toBeTruthy();
    expect(history.backTitle.value).toBeNull();
  });

  it("bounds the number of remembered titles, keeping the most recent", async () => {
    let back: string | null = null;
    const { router, history } = setup(() => ({ back }));
    for (let i = 0; i < MAX_REMEMBERED_TITLES + 5; i += 1) await router.push(`/n/${i}`);
    back = "/n/0";
    history.refresh();
    expect(history.backTitle.value).toBeNull();
    back = `/n/${MAX_REMEMBERED_TITLES + 3}`;
    history.refresh();
    expect(history.backTitle.value).toEqual({ key: "", fallback: "Numbered" });
  });
});
