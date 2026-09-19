import {chromium} from 'playwright';
import AxeBuilder from '@axe-core/playwright';
import {makeJobs} from '/tmp/opsfixture.mjs';
const b=await chromium.launch();
for (const [w,h,tag,opts] of [[1440,1000,'desktop',{}],[390,844,'mobile',{}],[1200,900,'forced',{forcedColors:'active'}]]) {
 const ctx=await b.newContext({viewport:{width:w,height:h},...opts});const p=await ctx.newPage();
 await p.route('**/api/jobs',async r=>{ if(r.request().method()==='GET') return r.fulfill({json:{jobs:makeJobs(0)}}); return r.continue()});
 await p.goto('http://127.0.0.1:15173');await p.waitForTimeout(1500);
 await p.fill('input[type=text],input:not([type])','admin');await p.fill('input[type=password]',process.env.PW);
 await p.click('button:has-text("Sign in")');await p.waitForTimeout(3500);
 await p.locator('aside button[title="Operations"]').first().click();await p.waitForTimeout(3000);
 if(tag==='desktop'){
   const full=await new AxeBuilder({page:p}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
   console.log('WHOLE PAGE violations:',full.violations.map(v=>v.id+'('+v.nodes.map(n=>n.target.join(' ').slice(0,40)).join('; ')+')').join(' | ')||'none');
   const panel=await new AxeBuilder({page:p}).include('#operationsPanel').withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']).analyze();
   console.log('PANEL violations:',panel.violations.length,'| incomplete:',panel.incomplete.map(v=>v.id+'('+v.nodes.length+')').join(', ')||'none');
 }
 console.log(tag,'overflow x:',await p.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth));
 await p.locator('#operationsPanel').scrollIntoViewIfNeeded();
 await p.screenshot({path:`/tmp/shots/ops3-${tag}.png`,fullPage:false});
 await ctx.close();
}
await b.close();
