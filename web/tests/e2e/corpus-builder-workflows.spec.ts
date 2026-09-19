import { expect, test } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

async function expectWcag2AA(page:any,include:string){
  const results=await new AxeBuilder({page}).include(include).withTags(["wcag2a","wcag2aa"]).analyze();
  expect(results.violations,JSON.stringify(results.violations,null,2)).toEqual([]);
}
async function expectNoHorizontalOverflow(locator:any){
  const metrics=await locator.evaluate((el:HTMLElement)=>({scrollWidth:el.scrollWidth,clientWidth:el.clientWidth}));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth+1);
}
const story=(id:string)=>"/iframe.html?id="+id+"&viewMode=story";

test.describe("Corpus Builder composed workflow",()=>{
  test("lifecycle stepper maps configure, build, review, and publish states",async({page})=>{
    const states=[
      ["corpus-builder-workflow-lifecycle-stepper--configure","Source & configure"],
      ["corpus-builder-workflow-lifecycle-stepper--building","Build"],
      ["corpus-builder-workflow-lifecycle-stepper--review","Review"],
      ["corpus-builder-workflow-lifecycle-stepper--ready-to-publish","Publish"],
    ];
    for(const [id,label] of states){
      await page.goto(story(id));
      const current=page.locator('[aria-current="step"]');
      await expect(current).toBeVisible();
      await expect(current).toContainText(label);
      await expectWcag2AA(page,".workflow");
    }
  });

  test("document structure remains usable in the narrow laptop composition",async({page})=>{
    await page.goto(story("corpus-builder-source-document-structure-pagination--narrow-laptop"));
    const surface=page.locator(".structure-config");
    await expect(surface).toBeVisible();
    await expectNoHorizontalOverflow(surface);
    await expect(page.getByRole("button",{name:/Save document structure/i})).toBeDisabled();
    await page.getByRole("button",{name:/Next/i}).click();
    await page.getByRole("button",{name:/Set current as main-text start/i}).click();
    await expect(page.getByText(/Unsaved changes/i)).toBeVisible();
    await expect(page.getByRole("button",{name:/Save document structure/i})).toBeEnabled();
    await expectWcag2AA(page,".structure-config");
  });

  test("advanced execution exposes unsafe context as an alert",async({page})=>{
    await page.goto(story("corpus-builder-settings-execution--unsafe-context"));
    const shell=page.locator(".execution-settings-shell");
    await expect(shell).toHaveAttribute("open","");
    await expect(page.locator(".context-check")).toHaveAttribute("role","alert");
    await expect(page.locator(".context-check")).toContainText(/Context budget is too small/i);
    await expectNoHorizontalOverflow(shell);
    await expectWcag2AA(page,".execution-settings-shell");
  });

  test("build progress makes unresolved provenance and validation state visible",async({page})=>{
    await page.goto(story("corpus-builder-workflow-build-progress--provenance-hazard"));
    const surface=page.locator(".corpus-build-progress");
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow","100");
    await expect(page.locator(".unresolved-line")).toContainText("1");
    await expect(surface).toContainText(/boundary decision/i);
    await expectNoHorizontalOverflow(surface);
    await expectWcag2AA(page,".corpus-build-progress");
  });

  test("initialization owns focusable build state while topology is being prepared",async({page})=>{
    await page.goto(story("corpus-builder-build-initialization-dialog--segmenting"));
    const dialog=page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    await expect(dialog).toHaveAttribute("aria-modal","true");
    await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow","18");
    await expect(page.getByRole("button",{name:/Cancel build/i})).toBeEnabled();
    await expectWcag2AA(page,".init-dialog");
  });

  test("review queue supports keyboard traversal and explicit issue filtering",async({page})=>{
    await page.goto(story("corpus-builder-review-queue-tabs--metadata-queue"));
    const issues=page.locator('[data-review-queue="issues"]');
    await expect(issues).toHaveAttribute("aria-pressed","true");
    await expect(page.locator(".issue-filter select")).toHaveValue("metadata");
    await issues.focus();
    await issues.press("ArrowRight");
    await expect(page.locator('[data-review-queue="accepted"]')).toBeFocused();
    await expectWcag2AA(page,".queue-controls");
  });

  test("focus review supports keyboard tabs and reviewed-text editing",async({page})=>{
    await page.goto(story("corpus-builder-review-focus-view--pending"));
    const dialog=page.getByRole("dialog");
    await expect(dialog).toBeVisible();
    const metadata=page.locator("#focus-tab-metadata");
    await metadata.focus();
    await metadata.press("ArrowRight");
    await expect(page.locator("#focus-tab-evidence")).toBeFocused();
    await expect(page.locator("#focus-tab-evidence")).toHaveAttribute("aria-selected","true");
    await page.getByRole("button",{name:/Edit text/i}).click();
    const editor=page.locator("textarea.focus-text-editor");
    await expect(editor).toBeVisible();
    await editor.fill("A corrected reviewed passage.");
    await editor.press("Control+s");
    await expect(editor).toHaveCount(0);
    await expectWcag2AA(page,".focus-review");
  });

  test("metadata review distinguishes ambiguous and inherited states",async({page})=>{
    await page.goto(story("corpus-builder-review-metadata-resolution--ambiguous-fields"));
    await expect(page.locator(".review-status")).toContainText(/decision/i);
    await expect(page.locator('.metadata-grid[role="list"]')).toBeVisible();
    await expectWcag2AA(page,".metadata-review");
    await page.goto(story("corpus-builder-review-metadata-resolution--inherited-and-overridden-bibliography"));
    await expect(page.locator(".inherited-metadata")).toBeVisible();
    await expect(page.locator(".inherited-metadata")).toContainText(/Inherited document metadata/i);
    await expectWcag2AA(page,".metadata-review");
  });

  test("finish workspace covers publishable, mixed, and all-rejected outcomes",async({page})=>{
    await page.goto(story("corpus-builder-workflow-finish-workspace--ready-to-publish"));
    await expect(page.getByRole("heading",{name:/Ready to publish/i})).toBeVisible();
    await expect(page.getByRole("button",{name:/Publish corpus/i})).toBeEnabled();
    await expectWcag2AA(page,".finish-workspace");
    await page.goto(story("corpus-builder-workflow-finish-workspace--mixed-accepted-and-rejected"));
    await expect(page.locator(".finish-workspace")).toContainText("40");
    await expect(page.locator(".finish-workspace")).toContainText("23");
    await page.goto(story("corpus-builder-workflow-finish-workspace--no-publishable-records"));
    await expect(page.locator(".no-publishable")).toContainText(/All records are currently rejected/i);
    await expect(page.getByRole("button",{name:/Restore all rejected/i})).toBeEnabled();
    await expectWcag2AA(page,".finish-workspace");
  });

  test("review dialogs remain modal, width-safe, and accessible",async({page})=>{
    const dialogs=[
      "corpus-builder-review-llm-text-touch-up--proposal",
      "corpus-builder-review-metadata-enrichment-dialog--default",
      "corpus-builder-review-text-cleanup--default",
      "corpus-builder-review-bulk-metadata-editor--default",
      "corpus-builder-review-jsonl-preview--blocked",
    ];
    for(const id of dialogs){
      await page.goto(story(id));
      const dialog=page.getByRole("dialog");
      await expect(dialog).toBeVisible();
      await expectNoHorizontalOverflow(dialog);
      await expectWcag2AA(page,'[role="dialog"]');
    }
  });

  test("compact source and provider-switch surfaces stay usable without overflow",async({page})=>{
    await page.goto(story("corpus-builder-source-compact-source-summary--narrow-inspector"));
    const source=page.locator(".source-summary");
    await expect(source).toBeVisible();
    await expectNoHorizontalOverflow(source);
    await expectWcag2AA(page,".source-summary");
    await page.goto(story("corpus-builder-enrichment-provider-switcher--default"));
    const provider=page.locator(".provider-switcher");
    await expect(provider).toBeVisible();
    await expectNoHorizontalOverflow(provider);
    await expectWcag2AA(page,".provider-switcher");
  });

  test("finish and review surfaces survive 200 percent zoom-equivalent scaling",async({page})=>{
    await page.goto(story("corpus-builder-workflow-finish-workspace--french-length-stress"));
    await page.evaluate(()=>{document.documentElement.style.zoom="2"});
    const finish=page.locator(".finish-workspace");
    await expect(finish).toBeVisible();
    await expectNoHorizontalOverflow(finish);
    await expectWcag2AA(page,".finish-workspace");
  });
});
