import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

function alphaFromCssColor(value:string):number {
  const rgba=value.match(/rgba?\(([^)]+)\)/i);
  if(!rgba)return 1;
  const parts=rgba[1].split(/[\s,\/]+/).filter(Boolean);
  if(parts.length<4)return 1;
  const alpha=Number(parts[3]);
  return Number.isFinite(alpha)?alpha:1;
}

async function expectWcag2AA(page:any, include:string){
  const results=await new AxeBuilder({page}).include(include).withTags(["wcag2a","wcag2aa"]).analyze();
  expect(results.violations, JSON.stringify(results.violations,null,2)).toEqual([]);
}

test("build summary is an opaque-enough glass surface and WCAG 2.0 AA clean", async ({page}) => {
  await page.goto("/iframe.html?id=corpus-build-readiness--ready&viewMode=story");
  const surface=page.locator(".build-readiness");
  await expect(surface).toBeVisible();
  const background=await surface.evaluate(el=>getComputedStyle(el).backgroundColor);
  expect(alphaFromCssColor(background)).toBeGreaterThanOrEqual(.9);
  const overflow=await surface.evaluate(el=>({scrollWidth:(el as HTMLElement).scrollWidth,clientWidth:(el as HTMLElement).clientWidth}));
  expect(overflow.scrollWidth).toBeLessThanOrEqual(overflow.clientWidth+1);
  await expectWcag2AA(page,".build-readiness");
});

test("corpus builds popover is opaque, keyboard focusable, and WCAG 2.0 AA clean", async ({page}) => {
  await page.goto("/iframe.html?id=corpus-builder-workflow-build-history-menu--default&viewMode=story");
  const summary=page.locator(".history-menu > summary");
  await summary.focus();
  await expect(summary).toBeFocused();
  const outline=await summary.evaluate(el=>getComputedStyle(el).outlineStyle);
  expect(outline).not.toBe("none");
  await summary.press("Enter");
  const popover=page.locator(".history-popover");
  await expect(popover).toBeVisible();
  const background=await popover.evaluate(el=>getComputedStyle(el).backgroundColor);
  expect(alphaFromCssColor(background)).toBeGreaterThanOrEqual(.9);
  await expectWcag2AA(page,".history-menu");
});

test("confident stance is visibly selected in the real Storybook component", async ({page}) => {
  await page.goto("/iframe.html?id=corpus-builder-review-metadata-field--auto-populated-stance&viewMode=story");
  const select=page.locator("select.control");
  await expect(select).toHaveValue("affirm");
});
