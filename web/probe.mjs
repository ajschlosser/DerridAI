import {chromium} from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import {makeJobs} from '/tmp/opsfixture.mjs';
const b=await chromium.launch();
async function open(opts={}){
  const ctx=await b.newContext({viewport:{width:opts.w||1440,height:opts.h||1000},reducedMotion:opts.rm||'no-preference',forcedColors:opts.fc||'none'});const p=await ctx.newPage();
  let tick=0;p.__tick=()=>tick++;
  await p.route('**/api/jobs',async r=>{ if(r.request().method()==='GET') return r.fulfill({json:{jobs:makeJobs(tick)}}); return r.continue()});
  await p.goto('http://127.0.0.1:15173');await p.waitForTimeout(1200);
  await p.fill('input[type=text],input:not([type])','admin');await p.fill('input[type=password]',process.env.PW);
  await p.click('button:has-text("Sign in")');await p.waitForTimeout(3500);
  await p.locator('aside button[title="Operations"]').first().click();await p.waitForTimeout(2500);
  return {ctx,p};
}
{const {ctx,p}=await open();
 console.log('panel present:',await p.locator('#operationsPanel.ops').count(),'rows:',await p.locator('li.ops-row').count(),'h2:',await p.locator('#operationsPanel h2').count());
 const res=await new AxeBuilder({page:p}).include('#operationsPanel').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
 console.log('AXE panel (2.0-2.2 A/AA) violations:',res.violations.length);for(const v of res.violations){console.log(' -',v.id,v.impact,v.help);for(const n of v.nodes.slice(0,4))console.log('     ',n.target.join(' '),'|',(n.any[0]?.message||'').slice(0,140))}
 console.log('needs-review:',res.incomplete.map(v=>v.id+'('+v.nodes.length+')').join(', '));
 await p.locator('#operationsPanel').screenshot({path:'/tmp/shots/ops2-desktop.png'});
 // focus retention while polling updates progress
 await p.locator('[data-op-id="ok-1"] button').first().focus();
 const before=await p.evaluate(()=>document.activeElement?.getAttribute('aria-label'));
 p.__tick();await p.waitForTimeout(9500);p.__tick();await p.waitForTimeout(4500);
 const after=await p.evaluate(()=>({label:document.activeElement?.getAttribute('aria-label'),tag:document.activeElement?.tagName}));
 console.log('focus before:',before,'| after 2 polls:',JSON.stringify(after));
 console.log('bar now:',await p.locator('[data-op-id="build-1"] [role=progressbar]').getAttribute('aria-valuenow'));
 await ctx.close();}
await b.close();
