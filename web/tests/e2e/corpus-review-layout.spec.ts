/* Copyright 2026 Aaron John Schlosser, PhD. */
import { expect, test, type Page } from "@playwright/test";
import { mockBackend, CORPUS_BUILD, CORPUS_RECORDS } from "./support/mock-backend";
import { serveBuiltApp } from "./support/built-app";
import AxeBuilder from "@axe-core/playwright";

// The Corpus Builder review workspace in the real app: it should fill the screen under the top bar,
// keep its decisions in reach, scroll each pane on its own, and be usable from the keyboard. Rendered
// against the mock API from the production build (see app-views.spec.ts).
const APP = `http://127.0.0.1:${process.env.APP_PORT || "5199"}`;
test.beforeEach(async({page})=>{
  if(process.env.CORPUS_OFFLINE_APP==='1')await serveBuiltApp(page,APP);
});

async function open(page: Page) {
  await mockBackend(page);
  await page.goto(`${APP}/pdf`);
  await page.locator(".review-grid").waitFor();
  // Entering the workspace scrolls it to the top of the screen; wait for that to settle.
  await expect
    .poll(async () =>
      page.evaluate(() =>
        Math.round(document.querySelector(".review-frame")!.getBoundingClientRect().top - document.querySelector(".shell-topbar")!.getBoundingClientRect().bottom),
      ),
    )
    .toBeLessThanOrEqual(2);
}
const rect = (page: Page, selector: string) =>
  page
    .locator(selector)
    .first()
    .evaluate((el) => {
      const r = el.getBoundingClientRect();
      return { x: r.x, y: r.y, w: r.width, h: r.height, right: r.right, bottom: r.bottom };
    });

test.describe("at a wide desktop", () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the workspace fills the screen under the top bar and adds no phantom scroll", async ({
    page,
  }) => {
    await open(page);
    const m = await page.evaluate(() => {
      const frame = document.querySelector(".review-frame")!.getBoundingClientRect();
      const bar = document.querySelector(".shell-topbar")!.getBoundingClientRect();
      const doc = document.documentElement;
      return {
        top: frame.top,
        bottom: frame.bottom,
        topbar: bar.bottom,
        view: innerHeight,
        below: doc.scrollHeight - (frame.bottom + scrollY),
      };
    });
    expect(
      Math.abs(m.top - m.topbar),
      "the frame sits right under the top bar",
    ).toBeLessThanOrEqual(2);
    expect(m.bottom, "and reaches the bottom of the window").toBeGreaterThan(m.view - 24);
    expect(m.bottom).toBeLessThanOrEqual(m.view);
    // The queue's visually-hidden labels used to stretch the page by thousands of pixels.
    expect(m.below, "nothing but the footer is below the workspace").toBeLessThan(160);
  });

  test("the decisions are one row, in reach, with the primary action last", async ({ page }) => {
    await open(page);
    const bar = await rect(page, ".decision-bar");
    expect(bar.h).toBeLessThanOrEqual(72);
    const [skip, reject, accept] = await Promise.all(
      ["Skip", "Reject & next", "Accept & next"].map(
        async (name) => (await page.getByRole("button", { name, exact: true }).boundingBox())!,
      ),
    );
    expect(Math.abs(skip.y - accept.y)).toBeLessThanOrEqual(4);
    expect(Math.abs(reject.y - accept.y)).toBeLessThanOrEqual(4);
    expect(accept.x).toBeGreaterThan(reject.x);
    expect(reject.x).toBeGreaterThan(skip.x);
    expect(accept.y + accept.height, "inside the window without scrolling").toBeLessThanOrEqual(
      900,
    );
  });

  test("each pane scrolls on its own, and the page does not move", async ({ page }) => {
    await open(page);
    const before = await page.evaluate(() => scrollY);
    const queue = page.locator(".records-pane");
    expect(await queue.evaluate((el) => el.scrollHeight > el.clientHeight)).toBe(true);
    await queue.hover();
    await page.mouse.wheel(0, 400);
    await expect.poll(() => queue.evaluate((el) => el.scrollTop)).toBeGreaterThan(0);
    expect(await page.evaluate(() => scrollY)).toBe(before);
  });

  test("scrolling passes to the page at the edge of a pane, so nothing above the workspace is out of reach", async ({
    page,
  }) => {
    await open(page);
    const before = await page.evaluate(() => scrollY);
    expect(before, "the workspace is scrolled into place").toBeGreaterThan(0);
    for (const selector of [".records-pane", ".record-review-pane", ".review-inspector"]) {
      await page.evaluate((y) => scrollTo(0, y), before);
      const box = (await page.locator(selector).first().boundingBox())!;
      await page.mouse.move(box.x + box.width / 2, box.y + 80);
      await page.mouse.wheel(0, -1200); // each pane is already at its top
      await expect
        .poll(() => page.evaluate(() => scrollY), { message: `wheel over ${selector}` })
        .toBeLessThan(before);
    }
  });

  test("a record's state is shown by a shape and its name, not by colour alone", async ({
    page,
  }) => {
    await open(page);
    const rows = page.locator(".record-row");
    expect(await rows.count()).toBeGreaterThan(5);
    for (const row of await rows.all()) {
      await expect(row.locator(".record-state-icon")).toHaveCount(1);
      expect((await row.locator(".record-row-status").innerText()).trim().length).toBeGreaterThan(
        0,
      );
    }
    // The status is stated once: a row never repeats it in a second line.
    const texts = await page
      .locator(".record-row")
      .first()
      .evaluate((el) => (el.textContent || "").toLowerCase());
    expect(texts.split("metadata").length - 1).toBeLessThanOrEqual(1);
  });

  test("More actions is a menu: it says why an action is unavailable and returns focus on Escape", async ({
    page,
  }) => {
    await open(page);
    const trigger = page.getByRole("button", { name: /More (record )?actions/ });
    await trigger.focus();
    await page.keyboard.press("Enter");
    const menu = page.getByRole("menu");
    await expect(menu).toBeVisible();
    // The first record has no previous record to combine with.
    const combine = menu.getByRole("menuitem", { name: /Combine with previous record/ });
    await expect(combine).toHaveAttribute("aria-disabled", "true");
    await expect(combine).toContainText("no previous record");
    await page.keyboard.press("ArrowDown");
    await expect(menu.getByRole("menuitem").nth(1)).toBeFocused();
    await page.keyboard.press("Escape");
    await expect(menu).toBeHidden();
    await expect(trigger).toBeFocused();
  });

  test("the panes can be resized from the keyboard, and the size is remembered", async ({
    page,
  }) => {
    await open(page);
    const width = () =>
      page
        .locator(".review-grid")
        .evaluate((el) => parseInt((el as HTMLElement).style.getPropertyValue("--rw-queue")));
    const separator = page.getByRole("separator", { name: /Resize review queue/ });
    await expect(separator).toHaveAttribute("aria-valuenow", "256");
    await separator.focus();
    await page.keyboard.press("ArrowRight");
    expect(await width()).toBe(272);
    await page.keyboard.press("Shift+ArrowRight");
    expect(await width()).toBe(336);
    await page.keyboard.press("Home");
    expect(await width()).toBe(224);
    await page.keyboard.press("ArrowRight");
    await page.reload();
    await page.locator(".review-grid").waitFor();
    expect(await width()).toBe(240);
  });
});

test.describe("on a laptop", () => {
  test.use({ viewport: { width: 1024, height: 768 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the queue and record fill the window, with metadata available in its own workspace", async ({
    page,
  }) => {
    await open(page);
    const [queue, record, inspector, bar] = await Promise.all(
      [".records-pane", ".record-review-pane", ".review-inspector", ".decision-bar"].map((s) =>
        rect(page, s),
      ),
    );
    expect(queue.x).toBeLessThan(record.x);
    expect(Math.abs(queue.y - record.y)).toBeLessThanOrEqual(2);
    expect(inspector.h).toBe(0);
    expect(record.h).toBeGreaterThan(450);
    expect(bar.bottom, "the decisions are still in the window").toBeLessThanOrEqual(768);
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth),
      "and nothing overflows sideways",
    ).toBe(true);
    await page.getByRole('button',{name:'Review required fields',exact:true}).click();
    await expect(page.locator('.review-inspector')).toBeVisible();
    await expect(page.locator('.record-review-pane')).toBeHidden();
    await page.locator('.workspace-switcher button').first().click();
    await expect(page.locator('.record-review-pane')).toBeVisible();
  });
});

test.describe('compact desktop and tablet reflow',()=>{
  test.beforeEach(({},info)=>test.skip(info.project.name!=='chromium-desktop','Runs once at explicit viewports.'));
  test('1280px gives the record room and keeps the decision dock in view',async({page})=>{
    await page.setViewportSize({width:1280,height:720});
    await open(page);
    const record=await rect(page,'.record-review-pane');
    const dock=await rect(page,'.record-decision-dock');
    expect(record.w).toBeGreaterThan(600);
    expect(dock.h).toBeLessThan(120);
    expect(dock.bottom).toBeLessThanOrEqual(720);
    await expect(page.locator('.review-inspector')).toBeHidden();
  });
  test('768px uses natural text height and clears the collapsed navigation rail',async({page})=>{
    await page.setViewportSize({width:768,height:900});
    await mockBackend(page);
    await page.goto(`${APP}/pdf`);
    await expect(page.locator('.record-primary-text')).toBeVisible();
    const record=await rect(page,'.record-review-pane');
    const sidebar=await rect(page,'.shell-sidebar');
    expect(record.x).toBeGreaterThanOrEqual(sidebar.right);
    expect(record.h).toBeGreaterThan(450);
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
    await page.getByRole('button',{name:'Review required fields',exact:true}).click();
    await expect(page.locator('.review-inspector')).toBeVisible();
    expect((await rect(page,'.review-inspector')).x).toBeGreaterThanOrEqual(sidebar.right);
  });
  test('320px metadata view wraps long translated controls without page overflow',async({page})=>{
    await page.setViewportSize({width:320,height:800});
    await mockBackend(page,{fixtures:{'/api/i18n/languages/en-US':{code:'en-US',name:'English',dictionary:{
      'pdf_corpus.build_overview':'Vue d’ensemble de la construction',
      'pdf_corpus.metadata_family.all':'Toutes les familles de métadonnées',
    }}}});
    await page.goto(`${APP}/pdf`);
    await page.getByRole('button',{name:'Review required fields',exact:true}).click();
    await expect(page.locator('.review-inspector')).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  });
});

test('build history side panel preserves the editor and restores focus on Escape',async({page})=>{
  await mockBackend(page);
  await page.goto(`${APP}/pdf`);
  await page.getByRole('button',{name:'Edit text',exact:true}).click();
  await page.locator('.record-text-editor').fill('Unsaved review draft');
  const trigger=page.getByRole('button',{name:/Corpus builds/}).first();
  await trigger.click();
  const dialog=page.getByRole('dialog');
  await expect(dialog).toBeVisible();
  const panel=await dialog.boundingBox();
  expect(panel!.width).toBeLessThanOrEqual(440);
  expect(panel!.x).toBeGreaterThanOrEqual(page.viewportSize()!.width-450);
  await expect(dialog).toContainText('1 of 1 builds loaded');
  await dialog.getByRole('button',{name:/Active \(/}).click();
  await expect(dialog.locator('.history-row')).toHaveCount(0);
  await dialog.getByRole('button',{name:'All',exact:true}).click();
  await expect(dialog.locator('.history-row')).toHaveCount(1);
  const accessibility=await new AxeBuilder({page}).include('[role="dialog"]').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
  expect(accessibility.violations).toEqual([]);
  await dialog.getByRole('button',{name:'All',exact:true}).focus();
  await page.keyboard.press('r');
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
  await expect(page.locator('.record-text-editor')).toHaveValue('Unsaved review draft');
});

test('source refresh retains evidence, retries locally, and restores keyboard focus',async({page})=>{
  const endpoint='/api/pdf/assets/asset-1/blocks';
  const payload=(text:string)=>({items:[{block_id:'b12a',text,page:5,type:'text'}],total:1});
  await mockBackend(page,{fixtures:{[endpoint]:payload('Retained source evidence')}});
  await page.goto(`${APP}/pdf`);
  await page.locator('.workspace-switcher button').nth(2).click();
  await expect(page.locator('.source-block')).toContainText('Retained source evidence');
  await page.route(url=>url.pathname===endpoint,route=>route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({detail:'Source unavailable '+ 'x'.repeat(160)})}));
  await page.locator('.record-row').first().click();
  await expect(page.locator('.source-read-error')).toContainText('Source unavailable');
  await expect(page.locator('.source-block')).toContainText('Retained source evidence');
  await page.setViewportSize({width:320,height:800});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  await page.setViewportSize({width:1440,height:900});
  const accessibility=await new AxeBuilder({page}).include('.source-read-error').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
  expect(accessibility.violations).toEqual([]);
  await page.route(url=>url.pathname===endpoint,route=>route.fulfill({contentType:'application/json',body:JSON.stringify(payload('Refreshed source evidence'))}));
  await page.getByRole('button',{name:'Retry source blocks',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.source-read-error')).toHaveCount(0);
  await expect(page.locator('.source-block')).toContainText('Refreshed source evidence');
  await expect(page.locator('.review-inspector')).toBeFocused();
  await page.route(url=>url.pathname===endpoint,route=>route.fulfill({status:500,contentType:'application/json',body:JSON.stringify({detail:'Source unavailable again'})}));
  await page.locator('.record-row').first().click();
  await expect(page.locator('.source-read-error')).toContainText('Source unavailable again');
  let release! : ()=>void;
  await page.route(url=>url.pathname===endpoint,async route=>{
    await new Promise<void>(resolve=>{release=resolve});
    await route.fulfill({contentType:'application/json',body:JSON.stringify(payload('Second refreshed source'))});
  });
  await page.getByRole('button',{name:'Retry source blocks',exact:true}).focus();
  await page.keyboard.press('Enter');
  await expect.poll(()=>Boolean(release)).toBe(true);
  const search=page.locator('#pdf-corpus-record-search');
  await search.focus();release();
  await expect(page.locator('.source-block')).toContainText('Second refreshed source');
  await expect(search).toBeFocused();
});

for(const width of [1440,320])test(`build details tabs preserve drafts and fit ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  await mockBackend(page);
  await page.goto(`${APP}/pdf`);
  await page.locator('.review-grid').waitFor();
  await page.getByRole('button',{name:'Edit text',exact:true}).click();
  const editor=page.locator('.record-text-editor');
  await editor.fill('Draft preserved through build details');
  const trigger=page.getByRole('button',{name:'Build details',exact:true});
  await trigger.click();
  const dialog=page.getByRole('dialog',{name:'Build details',exact:true});
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('tab',{name:'Activity',exact:true})).toHaveAttribute('aria-selected','true');
  await dialog.getByRole('tab',{name:'Activity',exact:true}).focus();
  await page.keyboard.press('ArrowRight');
  await expect(dialog.getByRole('tab',{name:'Issues',exact:true})).toBeFocused();
  await expect(dialog.locator('[role="tabpanel"]:visible')).toContainText('Record review decisions are separate');
  await page.keyboard.press('End');
  await expect(dialog.getByRole('tab',{name:'Settings',exact:true})).toBeFocused();
  await expect(dialog.locator('[role="tabpanel"]:visible')).toContainText('Provider profile');
  const accessibility=await new AxeBuilder({page}).include('[role="dialog"]').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
  expect(accessibility.violations).toEqual([]);
  expect(await dialog.evaluate(el=>el.scrollWidth-el.clientWidth)).toBeLessThanOrEqual(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  if(process.env.CORPUS_CAPTURE_DETAILS==='1')await page.screenshot({path:`../docs/design/corpus-builder-ux/details-implemented-${width}.png`});
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(trigger).toBeFocused();
  await expect(editor).toHaveValue('Draft preserved through build details');
});

for(const width of [1440,320])test(`verified warning navigation preserves selection through failed reads at ${width}px`,async({page})=>{
  await page.setViewportSize({width,height:900});
  const target=CORPUS_RECORDS[5].record_id;
  const warning=(id:string)=>`${id}: work_profile metadata failed (structured_output_invalid); review required.`;
  await mockBackend(page,{fixtures:{[`/api/pdf/corpus-builds/${CORPUS_BUILD.build_id}`]:{...CORPUS_BUILD,warnings:[warning(target),warning('historical-record')],metadata_issue_summary:{issues:[{record_id:target,field:'stance'}]}}}});
  let mode:'fail'|'missing'|'ok'='fail';
  await page.route(url=>url.pathname===`/api/pdf/corpus-builds/${CORPUS_BUILD.build_id}/records`,async route=>{
    const url=new URL(route.request().url());
    if(url.searchParams.get('query')!==target||mode==='ok'){await route.fallback();return}
    await route.fulfill({status:mode==='fail'?500:200,contentType:'application/json',body:JSON.stringify(mode==='fail'?{detail:'Record temporarily unavailable'}:{items:[{...CORPUS_RECORDS[0],record_id:target+'-other'}],total:1,offset:0,limit:50})});
  });
  await page.goto(`${APP}/pdf`);await page.locator('.review-grid').waitFor();
  await page.getByRole('button',{name:'Edit text',exact:true}).click();
  await page.locator('.record-text-editor').fill('Keep this review draft');
  await page.getByRole('button',{name:'2 build warning(s)',exact:true}).click();
  const dialog=page.getByRole('dialog',{name:'Build details',exact:true});
  await dialog.locator('.build-warnings>summary').click();
  await dialog.locator('.warning-group>summary').click();
  const review=dialog.getByRole('button',{name:`Review current metadata: ${target}`,exact:true});
  await expect(dialog.locator('.warning-records button')).toHaveCount(1);
  await expect(dialog.locator('li')).toHaveCount(2);
  const axe=await new AxeBuilder({page}).include('[role="dialog"]').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
  expect(axe.violations).toEqual([]);
  expect(await dialog.evaluate(el=>el.scrollWidth-el.clientWidth)).toBeLessThanOrEqual(1);
  if(process.env.CORPUS_CAPTURE_WARNINGS==='1')await page.screenshot({path:`../docs/design/corpus-builder-ux/warnings-implemented-${width}.png`});
  await review.click();await expect(dialog.locator('.warning-record-error')).toContainText('Record temporarily unavailable');
  await expect(page.locator('.record-text-editor')).toHaveValue('Keep this review draft');
  mode='missing';await review.click();await expect(dialog.locator('.warning-record-error')).toContainText('could not be verified');
  await expect(page.locator('.record-text-editor')).toHaveValue('Keep this review draft');
  mode='ok';await review.click();await expect(dialog).toBeHidden();
  await expect(page.locator('#pdf-corpus-record-search')).toHaveValue(target);
  await expect(page.locator('.review-grid')).toHaveClass(/metadata-workspace/);
  await expect(page.locator('.review-inspector')).toBeFocused();
  expect(await page.evaluate(id=>localStorage.getItem(`derridai.pdf-corpus.text-draft.build-0001.${id}`),CORPUS_RECORDS[0].record_id)).toBe('Keep this review draft');
});

test('wide build details dock beside review and retain settings through modal reflow',async({page})=>{
  await page.setViewportSize({width:1920,height:1080});
  await mockBackend(page,{fixtures:{[`/api/pdf/corpus-builds/${CORPUS_BUILD.build_id}`]:{...CORPUS_BUILD,status:'running',stage:'enriching'}}});
  await page.goto(`${APP}/pdf`);await page.locator('.review-grid').waitFor();
  await page.getByRole('button',{name:'Edit text',exact:true}).click();
  const editor=page.locator('.record-text-editor');await editor.fill('Review draft beside dock');
  const trigger=page.getByRole('button',{name:'Build details',exact:true});await trigger.click();
  const dock=page.locator('.build-details-dock .ui-dialog');
  await expect(dock).toBeVisible();await expect(dock).toHaveAttribute('role','region');
  await expect(dock).not.toHaveAttribute('aria-modal','true');
  expect((await rect(page,'.build-main')).right).toBeLessThanOrEqual((await rect(page,'.build-details-dock')).x+1);
  expect((await rect(page,'.record-review-pane')).w).toBeGreaterThan(600);
  await dock.getByRole('tab',{name:'Settings',exact:true}).click();
  const model=page.getByRole('combobox',{name:'Model for newly scheduled tasks',exact:true});
  await model.fill('pending-model');await model.evaluate(el=>el.setAttribute('data-retained','true'));
  await editor.fill('Edited while dock stays open');await page.keyboard.press('Escape');
  await expect(dock).toBeVisible();
  await model.focus();await page.setViewportSize({width:1280,height:900});
  const modal=page.getByRole('dialog',{name:'Build details',exact:true});await expect(modal).toBeVisible();
  await expect(model).toHaveValue('pending-model');await expect(model).toHaveAttribute('data-retained','true');await expect(model).toBeFocused();
  await page.setViewportSize({width:1920,height:1080});await expect(dock).toBeVisible();
  await expect(model).toHaveValue('pending-model');await expect(model).toHaveAttribute('data-retained','true');await expect(model).toBeFocused();
  const axe=await new AxeBuilder({page}).include('.build-details-dock').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();expect(axe.violations).toEqual([]);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth)).toBeLessThanOrEqual(1);
  await page.locator('.review-frame').evaluate(el=>el.scrollIntoView({block:'start'}));
  expect((await rect(page,'.build-details-dock .ui-dialog')).y).toBeLessThanOrEqual((await rect(page,'.shell-topbar')).bottom+2);
  expect((await rect(page,'.record-decision-dock')).bottom).toBeLessThanOrEqual(1080);
  if(process.env.CORPUS_CAPTURE_DOCK==='1')await page.screenshot({path:'../docs/design/corpus-builder-ux/details-docked-1920.png'});
  await page.keyboard.press('Escape');await expect(dock).toBeHidden();await expect(trigger).toBeFocused();
  await expect(editor).toHaveValue('Edited while dock stays open');
});

test.describe("on a short window", () => {
  test.use({ viewport: { width: 1366, height: 650 } });
  test.beforeEach(({}, info) =>
    test.skip(info.project.name !== "chromium-desktop", "Runs once, at its own viewports."),
  );

  test("the decisions stay on one row and the record text is readable", async ({ page }) => {
    await open(page);
    const bar = await rect(page, ".decision-bar");
    expect(bar.h).toBeLessThanOrEqual(72);
    const text = await rect(page, ".record-primary-text");
    const dock = await rect(page, ".record-decision-dock");
    // At least a couple of lines of the record show above the dock.
    expect(Math.min(text.bottom, dock.y) - text.y).toBeGreaterThan(60);
    // The compact menu is still named for assistive technology.
    await expect(page.getByRole("button", { name: /More (record )?actions/ })).toBeVisible();
  });
});
