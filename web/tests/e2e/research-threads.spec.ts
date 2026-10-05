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
  await expect(page.locator(".research-run-button")).toBeDisabled();
  await navigation.getByRole("button", { name: "Open answer and evidence" }).click();
  await expect(page).toHaveURL(/job=job-a/);
  await expect(page.locator(".research-answer-workspace")).toContainText("Answer A");
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
  for (const theme of ["light", "dark"]) {
    await page.evaluate(
      (value) => document.documentElement.setAttribute("data-color-scheme", value),
      theme,
    );
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
