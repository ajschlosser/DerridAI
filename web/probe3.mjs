import {chromium} from 'playwright';
import {makeJobs} from '/tmp/opsfixture.mjs';
const b=await chromium.launch();const ctx=await b.newContext({viewport:{width:1440,height:1000}});const p=await ctx.newPage();
let tick=0;await p.route('**/api/jobs',async r=>{ if(r.request().method()==='GET') return r.fulfill({json:{jobs:makeJobs(tick)}}); return r.continue()});
await p.goto('http://127.0.0.1:15173');await p.waitForTimeout(1200);
await p.fill('input[type=text],input:not([type])','admin');await p.fill('input[type=password]',process.env.PW);
await p.click('button:has-text("Sign in")');await p.waitForTimeout(3500);
await p.locator('aside button[title="Operations"]').first().click();await p.waitForTimeout(2500);
import AxeBuilder from '@axe-core/playwright';
const RUN_AXE=process.env.AXE==='1', SHOT=process.env.SHOT==='1';
if(RUN_AXE){await new AxeBuilder({page:p}).include('#operationsPanel').withTags(['wcag2aa']).analyze();}
if(SHOT){await p.locator('#operationsPanel').screenshot({path:'/tmp/shots/x.png'});}
await p.evaluate(()=>{window.__log=[];const ob=HTMLElement.prototype.blur;HTMLElement.prototype.blur=function(){window.__log.push('blur() '+(this.getAttribute('aria-label')||this.id||this.tagName)+' :: '+new Error().stack.split('\n').slice(2,5).map(s=>s.trim().replace(/http:\/\/127.0.0.1:15173/,'')).join(' <- '));return ob.apply(this,arguments)};
 document.addEventListener('focusout',e=>{window.__log.push(Date.now()%100000+' focusout '+(e.target.getAttribute?.('aria-label')||e.target.tagName)+' related='+(e.relatedTarget?.tagName||'null')+' connected='+e.target.isConnected)},true)});
await p.locator('[data-op-id="ok-1"] button').first().focus();
tick++;await p.waitForTimeout(9500);tick++;await p.waitForTimeout(4500);tick++;await p.waitForTimeout(5000);
console.log(await p.evaluate(()=>({active:document.activeElement?.tagName,log:window.__log})));
await b.close();
