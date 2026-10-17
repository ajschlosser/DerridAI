// Copyright 2026 Aaron John Schlosser, PhD.
import fs from "node:fs";
import path from "node:path";
import type { Page } from "@playwright/test";

/** Serve production assets locally through browser routing; mockBackend still owns /api. */
export async function serveBuiltApp(page:Page,origin:string){return serveBuiltAssets(page,origin,"dist",true)}
export async function serveBuiltStorybook(page:Page,origin:string){return serveBuiltAssets(page,origin,"storybook-static",false)}
async function serveBuiltAssets(page:Page,origin:string,directory:string,spa:boolean){
  const root=path.resolve(directory);
  const types:Record<string,string>={".html":"text/html",".json":"application/json",".js":"application/javascript",".css":"text/css",".svg":"image/svg+xml",".woff2":"font/woff2",".png":"image/png"};
  await page.route(url=>url.origin===origin&&!url.pathname.startsWith("/api/"),async route=>{
    const url=new URL(route.request().url());
    let file=path.resolve(root,"."+decodeURIComponent(url.pathname));
    if(file!==root&&!file.startsWith(root+path.sep)){await route.abort();return}
    if(!fs.existsSync(file)||fs.statSync(file).isDirectory()){
      if(!spa||!route.request().isNavigationRequest()){await route.fulfill({status:404,body:""});return}
      file=path.join(root,"index.html");
    }
    await route.fulfill({body:fs.readFileSync(file),contentType:types[path.extname(file)]||"application/octet-stream"});
  });
}
