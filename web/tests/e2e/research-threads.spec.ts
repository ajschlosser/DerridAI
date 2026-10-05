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
import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockBackend } from "./support/mock-backend";

const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
const summary = (id: string) => ({
  thread_id: id,
  owner: "admin",
  title: `Inquiry ${id}`,
  turn_count: 1,
  first_question: `Question ${id}`,
  last_question: `Question ${id}`,
  last_status: "failed",
  created_at: "2026-10-05T00:00:00Z",
  updated_at: "2026-10-05T00:00:00Z",
  archived_at: null,
  originating_response_record_id: null,
});
const detail = (id: string) => ({
  ...summary(id),
  turns: [
    {
      turn_id: `${id}-1`,
      thread_id: id,
      ordinal: 1,
      user_question: `Question ${id}`,
      status: id === "a" ? "completed" : "failed",
      job_id: id === "a" ? "job-a" : null,
      error: id === "a" ? null : "Provider unavailable",
      attempt: 1,
    },
  ],
});

test("thread navigation restores URL state and guards follow-ups, with keyboard and axe coverage", async ({
  page,
}) => {
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": { threads: [summary("a"), summary("b")] },
      "/api/research/threads/a": detail("a"),
      "/api/research/threads/b": detail("b"),
      "/api/jobs/job-a": {
        id: "job-a",
        status: "completed",
        type: "rag",
        prompt: "Question a",
        result: { answer: "Answer A", evidence: [] },
      },
    },
  });
  await page.goto(`${APP}/rag?thread=a`);
  const navigation = page.locator(".research-thread-navigation");
  await expect(navigation.getByRole("heading", { name: "Question a" })).toBeVisible();
  await expect(navigation.locator(".thread-answer-text")).toHaveText("Answer A");
  await expect(page.locator(".research-run-button")).toBeDisabled();
  await navigation.getByRole("button", { name: "Open answer and evidence" }).click();
  await expect(page).toHaveURL(/job=job-a/);
  await expect(page.locator("#research-selected-run .research-answer-workspace")).toContainText(
    "Answer A",
  );
  const next = navigation.getByRole("button", { name: "Inquiry b" });
  await next.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/thread=b/);
  await expect(navigation.getByRole("heading", { name: "Question b" })).toBeVisible();
  await expect(navigation.getByRole("heading", { name: "Question a" })).toHaveCount(0);
  await page.goBack();
  await expect(navigation.getByRole("heading", { name: "Question a" })).toBeVisible();
  await page.goForward();
  await expect(navigation.getByRole("heading", { name: "Question b" })).toBeVisible();
  await page.goBack();
  await expect(navigation.locator(".thread-answer-text")).toHaveText("Answer A");
  for (const theme of ["light", "dark"]) {
    await page.evaluate(async (value) => {
      document.documentElement.setAttribute("data-color-scheme", value);
      const dialog = document.documentElement;
      if (dialog)
        await Promise.all(
          dialog
            .getAnimations({ subtree: true })
            .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
            .map((animation) => animation.finished.catch(() => {})),
        );
    }, theme);
    const findings = await new AxeBuilder({ page })
      .include(".research-thread-navigation")
      .analyze();
    expect(findings.violations).toEqual([]);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(navigation).toBeVisible();
  const newQuestion = navigation.getByRole("button", { name: "New question", exact: true });
  await newQuestion.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(`${APP}/rag`);
  await expect(page.locator("#researchQuestion")).toBeFocused();
  await expect(page.locator("#researchQuestion")).toHaveValue("");
});

test("manage a thread through rename, archive, restore, and confirmed deletion", async ({
  page,
}) => {
  let record = { ...detail("a"), archived_at: null as string | null };
  let deleted = false;
  const mutations: { method: string; body?: Record<string, unknown> }[] = [];
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": (url: URL) => ({
        threads:
          deleted || (record.archived_at && url.searchParams.get("include_archived") !== "true")
            ? []
            : [{ ...summary("a"), title: record.title, archived_at: record.archived_at }],
      }),
    },
  });
  await page.route("**/api/research/threads/a", async (route) => {
    const method = route.request().method();
    if (method === "PATCH") {
      const body = route.request().postDataJSON();
      mutations.push({ method, body });
      record = {
        ...record,
        ...(body.title ? { title: body.title } : {}),
        ...(typeof body.archived === "boolean"
          ? { archived_at: body.archived ? "2026-10-05" : null }
          : {}),
      };
    } else if (method === "DELETE") {
      deleted = true;
      mutations.push({ method });
    }
    await route.fulfill({
      status: deleted ? (method === "DELETE" ? 204 : 404) : 200,
      contentType: "application/json",
      body:
        method === "DELETE"
          ? ""
          : JSON.stringify(deleted ? { detail: "Thread not found" } : record),
    });
  });
  await page.goto(APP + "/rag?thread=a");
  const nav = page.locator(".research-thread-navigation");
  const rename = nav.getByRole("button", { name: "Rename thread", exact: true });
  await rename.focus();
  await page.keyboard.press("Enter");
  let dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Thread title", { exact: true })).toBeFocused();
  for (const theme of ["light", "dark"]) {
    await page.evaluate(async (value) => {
      document.documentElement.setAttribute("data-color-scheme", value);
      const dialog = document.documentElement;
      if (dialog)
        await Promise.all(
          dialog
            .getAnimations({ subtree: true })
            .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
            .map((animation) => animation.finished.catch(() => {})),
        );
    }, theme);
    expect(
      (await new AxeBuilder({ page }).include('[role="dialog"]').analyze()).violations,
    ).toEqual([]);
  }
  await dialog.getByLabel("Thread title", { exact: true }).fill("New research title");
  await dialog.getByRole("button", { name: "Save", exact: true }).click();
  await expect(dialog).toHaveCount(0);
  await expect(rename).toBeFocused();
  await expect(nav.getByRole("heading", { name: "New research title", exact: true })).toBeVisible();
  expect(mutations[0]).toEqual({ method: "PATCH", body: { title: "New research title" } });
  await nav.getByRole("button", { name: "Archive thread", exact: true }).click();
  await expect(nav.getByRole("button", { name: "Unarchive thread", exact: true })).toBeVisible();
  await nav.getByLabel("Include archived threads", { exact: true }).check();
  await expect(
    nav.getByRole("navigation").getByRole("button", { name: "New research title" }),
  ).toBeVisible();
  await nav.getByRole("button", { name: "Unarchive thread", exact: true }).click();
  await expect(nav.getByRole("button", { name: "Archive thread", exact: true })).toBeVisible();
  const remove = nav.getByRole("button", { name: "Delete thread", exact: true });
  await remove.focus();
  await page.keyboard.press("Enter");
  dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("Saved responses, corpus records, and scholarly provenance");
  await expect(dialog.locator(".thread-dialog-cancel")).toBeFocused();
  for (const theme of ["light", "dark"]) {
    await page.evaluate(async (value) => {
      document.documentElement.setAttribute("data-color-scheme", value);
      const dialog = document.documentElement;
      if (dialog)
        await Promise.all(
          dialog
            .getAnimations({ subtree: true })
            .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
            .map((animation) => animation.finished.catch(() => {})),
        );
    }, theme);
    const findings = await new AxeBuilder({ page }).include('[role="dialog"]').analyze();
    expect(findings.violations).toEqual([]);
  }
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(remove).toBeFocused();
  expect(mutations.filter((item) => item.method === "DELETE")).toHaveLength(0);
  await remove.click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Delete thread", exact: true })
    .click();
  await expect(page).toHaveURL(APP + "/rag");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(mutations.filter((item) => item.method === "DELETE")).toHaveLength(1);
  await expect(nav.getByRole("heading", { name: "Question a", exact: true })).toHaveCount(0);
});

test("retry preserves a cancelled turn and opens its new attempt with keyboard focus", async ({
  page,
}) => {
  let record = {
    ...detail("b"),
    turns: [
      {
        ...detail("b").turns[0],
        status: "cancelled",
        user_instructions: "Preserve attribution",
        attempt: 1,
      },
    ],
  };
  const job = {
    id: "retry-job",
    type: "rag",
    status: "running",
    thread_id: "b",
    turn_id: "b-1",
    prompt: "Question b",
  };
  const requests: Record<string, unknown>[] = [];
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": { threads: [summary("b")] },
      "/api/research/threads/b": () => record,
      "/api/jobs/retry-job": job,
    },
  });
  await page.route("**/api/research/threads/b/turns/b-1/retry", async (route) => {
    expect(route.request().method()).toBe("POST");
    requests.push(route.request().postDataJSON());
    record = {
      ...record,
      turns: [
        { ...record.turns[0], status: "running", job_id: "retry-job", attempt: 2, error: null },
      ],
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(job),
    });
  });
  await page.goto(APP + "/rag?thread=b");
  const nav = page.locator(".research-thread-navigation");
  const retry = nav.getByRole("button", { name: "Retry with current settings", exact: true });
  await expect(retry).toBeEnabled();
  await expect(nav).toContainText("preserves the original question and instructions");
  for (const theme of ["light", "dark"]) {
    await page.evaluate(async (value) => {
      document.documentElement.setAttribute("data-color-scheme", value);
      await Promise.all(
        document.documentElement
          .getAnimations({ subtree: true })
          .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
          .map((animation) => animation.finished.catch(() => {})),
      );
    }, theme);
    expect(
      (await new AxeBuilder({ page }).include(".research-thread-navigation").analyze()).violations,
    ).toEqual([]);
  }
  await retry.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/thread=b&job=retry-job/);
  await expect(nav.locator("article")).toHaveCount(1);
  await expect(nav.getByRole("heading", { name: "Question b" })).toBeVisible();
  await expect(retry).toHaveCount(0);
  await expect(page.locator("#research-selected-run")).toBeFocused();
  await expect(page.locator(".research-run-button")).toBeDisabled();
  expect(requests).toHaveLength(1);
  expect(requests[0]).toMatchObject({
    prompt: "Question b",
    instructions: "Preserve attribution",
    selected_evidence: [],
  });
  expect(requests[0]).not.toHaveProperty("prior_answers");
});

test("active thread previews are labelled and accessible in both themes", async ({ page }) => {
  const active = detail("a");
  active.turns[0].status = "running";
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": { threads: [summary("a")] },
      "/api/research/threads/a": active,
    },
  });
  await page.goto(APP + "/rag?thread=a");
  const navigation = page.locator(".research-thread-navigation");
  await expect(navigation).toContainText("Drafting the answer");
  await expect(navigation).toContainText("citations are not yet bound");
  for (const theme of ["light", "dark"]) {
    await page.evaluate(
      (value) => document.documentElement.setAttribute("data-color-scheme", value),
      theme,
    );
    expect(
      (await new AxeBuilder({ page }).include(".research-thread-navigation").analyze()).violations,
    ).toEqual([]);
  }
});

test("each turn inspects its own evidence, including a recovered saved answer, with keyboard and axe", async ({
  page,
}) => {
  const a = detail("a");
  const b = {
    ...a.turns[0],
    turn_id: "a-2",
    ordinal: 2,
    job_id: "job-b",
    research_run_id: "job-b",
    response_record_id: "saved-b",
    user_question: "Question b",
  };
  const result = (label: string) => ({
    prompt: `Question ${label}`,
    answer: `Answer ${label} [[E0]].`,
    evidence: [0, 1].map((index) => ({
      evidence_id: `E${index}`,
      collection: "corpus",
      inline_citation: `Author ${label}: ${index + 1}`,
      full_citation: `Source ${label} ${index + 1}`,
      record: {
        record_id: `${label}-${index}`,
        work: `Work ${label}`,
        text: `Exact passage ${label} ${index}`,
        speaker: "Author",
        position_holder: "Other Thinker",
        stance: "questions",
      },
    })),
  });
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": { threads: [summary("a")] },
      "/api/research/threads/a": { ...a, turns: [a.turns[0], b] },
      "/api/jobs/job-a": { id: "job-a", status: "completed", result: result("a") },
      "/api/research/threads/a/turns/a-2/result": {
        id: "job-b",
        status: "completed",
        result: result("b"),
      },
    },
  });
  await page.route("**/api/jobs/job-b", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Unavailable" }),
    }),
  );
  await page.goto(APP + "/rag?thread=a");
  const navigation = page.locator(".research-thread-navigation");
  const turns = navigation.locator("article[aria-labelledby]");
  await expect(turns.nth(1).locator(".thread-answer-text")).toContainText("Answer b");
  for (const turn of [turns.nth(0), turns.nth(1)]) {
    const inspect = turn.getByText("Inspect this answer and its evidence", { exact: true });
    await inspect.focus();
    await page.keyboard.press("Enter");
  }
  const firstEvidence = turns.nth(0).locator(".research-evidence-index button").nth(1);
  await firstEvidence.focus();
  await page.keyboard.press("Enter");
  await expect(turns.nth(0).locator(".research-evidence-inspector")).toContainText(
    "Exact passage a 1",
  );
  await expect(turns.nth(1).locator(".research-evidence-inspector")).toContainText(
    "Exact passage b 0",
  );
  await expect(turns.nth(0).locator(".research-evidence-inspector")).toContainText("Other Thinker");
  await expect(navigation.getByRole("button", { name: "Re-run with parameters" })).toHaveCount(0);
  await expect(page.locator(".research-run-button")).toBeDisabled();
  await page.setViewportSize({ width: 390, height: 844 });
  for (const theme of ["light", "dark"]) {
    await page.evaluate(
      (value) => document.documentElement.setAttribute("data-color-scheme", value),
      theme,
    );
    expect(
      (await new AxeBuilder({ page }).include(".research-thread-navigation").analyze()).violations,
    ).toEqual([]);
  }
});

test("first question keeps the existing composer and submits one history-free run", async ({
  page,
}) => {
  const job = {
    id: "first-job",
    type: "rag",
    status: "queued",
    thread_id: "first-thread",
    turn_id: "first-turn",
  };
  const requests: Record<string, unknown>[] = [];
  await mockBackend(page, {
    fixtures: {
      "/api/jobs/first-job": job,
      "/api/research/threads/first-thread": {
        ...summary("first-thread"),
        turns: [
          {
            turn_id: "first-turn",
            thread_id: "first-thread",
            ordinal: 1,
            user_question: "What is not asserted?",
            status: "queued",
            job_id: "first-job",
            attempt: 1,
          },
        ],
      },
    },
  });
  await page.route("**/api/jobs/rag", async (route) => {
    requests.push(route.request().postDataJSON());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(job),
    });
  });
  await page.goto(APP + "/rag");
  const composer = page.locator("#researchQuestion");
  await expect(composer).toBeVisible();
  await composer.fill("What is not asserted?");
  await expect(page.locator(".research-run-button")).toBeEnabled();
  await page.locator(".research-run-button").click();
  await expect(page).toHaveURL(/thread=first-thread&job=first-job/);
  expect(requests).toHaveLength(1);
  expect(requests[0].prompt).toBe("What is not asserted?");
  expect(requests[0]).not.toHaveProperty("thread_context");
  expect(requests[0]).not.toHaveProperty("prior_answers");
  expect(requests[0]).not.toHaveProperty("retry_turn_id");
  await expect(composer).toBeVisible();
});

test("follow-up stays in its thread and preserves the previous answer", async ({ page }) => {
  const current = detail("a");
  const job = {
    id: "follow-job",
    type: "rag",
    status: "queued",
    thread_id: "a",
    turn_id: "follow-turn",
  };
  const requests: Record<string, unknown>[] = [];
  await mockBackend(page, {
    fixtures: {
      "/api/research/threads": { threads: [summary("a")] },
      "/api/research/threads/a": () => current,
      "/api/jobs/job-a": {
        id: "job-a",
        type: "rag",
        status: "completed",
        prompt: "Question a",
        result: { answer: "Previous answer", evidence: [] },
      },
      "/api/jobs/follow-job": job,
    },
  });
  await page.route("**/api/research/threads/a/turns", async (route) => {
    requests.push(route.request().postDataJSON());
    current.turns.push({
      ...current.turns[0],
      turn_id: "follow-turn",
      ordinal: 2,
      user_question: "What about Levinas?",
      status: "queued",
      job_id: "follow-job",
    });
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(job),
    });
  });
  await page.goto(APP + "/rag?thread=a&job=job-a");
  await expect(page.locator(".thread-answer-text").first()).toContainText("Previous answer");
  await page.locator("#researchQuestion").fill("What about Levinas?");
  await expect(page.locator(".research-run-button")).toBeEnabled();
  await page.locator(".research-run-button").click();
  await expect(page).toHaveURL(/thread=a&job=follow-job/);
  expect(requests).toHaveLength(1);
  expect(requests[0].prompt).toBe("What about Levinas?");
  expect(requests[0]).not.toHaveProperty("thread_context");
  await expect(page.locator(".thread-answer-text").first()).toContainText("Previous answer");
  await expect(page.locator(".research-run-button")).toBeDisabled();
});

test("Library imports legacy singletons and preserves thread search URL state", async ({
  page,
}) => {
  let imported = false;
  await mockBackend(page, {
    fixtures: {
      "POST /api/research/threads/import-legacy": () => {
        imported = true;
        return { created: 1, next_offset: 1, has_more: false };
      },
      "/api/research/threads": () => ({
        threads: imported ? [{ ...summary("legacy"), title: "Legacy Levinas" }] : [],
      }),
      "/api/research/threads/legacy": detail("legacy"),
    },
  });
  await page.goto(APP + "/faq");
  const library = page.locator(".research-thread-library");
  await expect(library.getByRole("button", { name: /Legacy Levinas/ })).toBeVisible();
  const search = library.getByLabel("Search thread titles and questions");
  await search.fill("Levinas");
  await search.press("Tab");
  await expect(page).toHaveURL(/thread_q=Levinas/);
  for (const theme of ["light", "dark"]) {
    await page.evaluate(
      (value) => document.documentElement.setAttribute("data-color-scheme", value),
      theme,
    );
    expect(
      (await new AxeBuilder({ page }).include(".research-thread-library").analyze()).violations,
    ).toEqual([]);
  }
  await library.getByRole("button", { name: /Legacy Levinas/ }).click();
  await expect(page).toHaveURL(/rag\?thread=legacy/);
});
