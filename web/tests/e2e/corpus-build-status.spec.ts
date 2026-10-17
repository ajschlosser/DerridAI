// Copyright 2026 Aaron John Schlosser, PhD.
import { expect, test } from "@playwright/test";
import { serveBuiltApp, serveBuiltStorybook } from "./support/built-app";
import { CORPUS_BUILD_ID, mockBackend } from "./support/mock-backend";

test.beforeEach(async({page,baseURL})=>{
  if(process.env.CORPUS_OFFLINE_APP==='1'){
    await serveBuiltApp(page,`http://127.0.0.1:${process.env.APP_PORT||"5199"}`);
    await serveBuiltStorybook(page,baseURL!);
  }
});

test("running build keeps secondary details collapsed and preserves review selection",async({page})=>{
  const build={build_id:CORPUS_BUILD_ID,asset_id:"asset-1",source_filename:"source.pdf",source_sha256:"sha",
    status:"running",stage:"enriching",progress:.85,created_at:"2026-10-15T20:00:00Z",record_count:60,
    accepted_count:0,needs_review_count:23,profile_id:"test",metadata_tasks_total:180,
    metadata_tasks_completed:100,metadata_tasks_failed:10,metadata_tasks_skipped:0,
    metadata_tasks_running:2,metadata_tasks_queued:68,review_queue_counts:{all:60,ready:15,issues:23,pending:60},
    warnings:Array.from({length:100},(_,i)=>`record-${i}: work_profile metadata failed (structured_output_invalid); review required.`)};
  await mockBackend(page,{fixtures:{"/api/pdf/corpus-builds":{items:[build],total:1},[`/api/pdf/corpus-builds/${CORPUS_BUILD_ID}`]:build}});
  await page.goto(`http://127.0.0.1:${process.env.APP_PORT||"5199"}/pdf`);
  await expect(page.locator(".review-grid")).toBeVisible();
  const status=page.locator(".metadata-live-status");
  await expect(status).toBeVisible();
  await expect(status.locator(".activity-details")).not.toHaveAttribute("open");
  await expect(page.getByRole("dialog",{name:"Build details",exact:true})).toHaveCount(0);
  const selected=await page.locator(".review-grid").textContent();
  await page.getByRole("button",{name:"100 build warning(s)",exact:true}).focus();
  await page.keyboard.press("Enter");
  const details=page.getByRole("dialog",{name:"Build details",exact:true});
  await expect(details.getByRole("tab",{name:"Issues",exact:true})).toHaveAttribute("aria-selected","true");
  const warnings=details.locator(".build-warnings");
  await warnings.locator(":scope>summary").focus();
  await page.keyboard.press("Enter");
  await expect(warnings).toHaveAttribute("open","");
  await expect(warnings.locator(".warning-group")).toHaveCount(1);
  await warnings.locator(".warning-group>summary").click();
  await expect(warnings.locator("li")).toHaveCount(100);
  await expect(warnings.locator("li").first()).toContainText("record-0:");
  expect(await page.locator(".review-grid").textContent()).toBe(selected);
  await page.keyboard.press("Escape");
  await expect(details).toBeHidden();
});

test("compact task status discloses timing with the keyboard and reflows",async({page})=>{
  await page.setViewportSize({width:768,height:900});
  await page.goto('/iframe.html?id=corpus-builder-status-metadata-live-status--running&viewMode=story');
  const status=page.locator(".metadata-live-status");
  await expect(status).toBeVisible();
  await expect(status.locator(".active-tasks")).not.toBeVisible();
  await status.locator(".activity-details>summary").focus();
  await page.keyboard.press("Enter");
  await expect(status.locator(".active-tasks")).toBeVisible();
  expect(await status.evaluate(el=>el.scrollWidth-el.clientWidth)).toBeLessThanOrEqual(1);
});
