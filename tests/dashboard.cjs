// Browser fixtures are synthetic UI checks and are never saved to dashboard/data.js.
const {chromium} = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const http = require('node:http');
const ROOT = path.resolve(__dirname, '..');
const context = {window: {}};
vm.runInNewContext(fs.readFileSync(path.join(ROOT, 'dashboard/data.js'), 'utf8'), context);
const payload = JSON.parse(JSON.stringify(context.window.OPTIONS_DATA));
const types = {'.html':'text/html','.js':'application/javascript','.css':'text/css'};
const server = http.createServer((req,res)=>{
 const file=path.resolve(ROOT,'.'+decodeURIComponent(req.url.split('?')[0]==='/'?'/index.html':req.url.split('?')[0]));
 if(!file.startsWith(ROOT+path.sep)){res.writeHead(403);return res.end();}
 fs.readFile(file,(error,body)=>{res.writeHead(error?404:200,{'Content-Type':types[path.extname(file)]||'application/octet-stream'});res.end(error?'Not found':body);});
});
(async()=>{
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({headless:true,...(process.env.CHROMIUM_PATH?{executablePath:process.env.CHROMIUM_PATH}:{}),args:['--no-sandbox']});
 try {
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  const url=`http://127.0.0.1:${server.address().port}`;
  await page.goto(url);await page.waitForSelector('#contracts tr');
  assert.equal(await page.locator('#contract-count').innerText(),payload.contracts.length.toLocaleString('en-US'));
  await page.selectOption('#ticker','AAPL');assert(await page.locator('#contracts tr td:first-child strong').evaluateAll(ns=>ns.length&&ns.every(n=>n.textContent==='AAPL')));
  await page.fill('#search','NO_MATCH');assert(await page.locator('#empty').isVisible());assert(await page.locator('#next').isDisabled());
  await page.click('#reset');const first=await page.locator('#contracts tr').first().innerText();await page.click('#next');assert.notEqual(await page.locator('#contracts tr').first().innerText(),first);await page.click('#previous');
  await page.selectOption('#volume','1000');assert(await page.locator('#contracts tr td:nth-child(6)').evaluateAll(ns=>ns.length&&ns.every(n=>Number(n.textContent.replaceAll(',',''))>=1000)));
  await page.click('#reset');
  const expiration=await page.locator('#expiry option').nth(1).getAttribute('value');await page.selectOption('#expiry',expiration);
  assert(await page.locator('#contracts tr td:nth-child(2)').evaluateAll((ns,expiry)=>ns.length&&ns.every(n=>n.textContent===expiry),expiration));
  await page.selectOption('#sort','strike');const strikes=await page.locator('#contracts tr td:nth-child(3)').allTextContents();assert(strikes.every((v,i)=>!i||Number(v.replace(/[$,]/g,''))>=Number(strikes[i-1].replace(/[$,]/g,''))));
  await page.click('#reset');
  if(payload.research.status!=='ready'){
   assert.equal(await page.locator('#research-status').innerText(),'More history needed');
   assert(await page.locator('#verified-charts').isHidden());assert((await page.locator('#backtest-result').innerText()).includes('not run'));
  }
  for(const width of [390,768,1440]){await page.setViewportSize({width,height:900});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));}
  if(process.env.SCREENSHOT){await page.screenshot({path:process.env.SCREENSHOT,fullPage:true});}
  // Exercise the future ready-state rendering without exporting simulated scores.
  const fixture=JSON.parse(JSON.stringify(payload));
  fixture.research={...fixture.research,status:'ready',selected_model:'logistic',split:{test:{start:'2026-01-01',end:'2026-02-01'}},
   models:{logistic:{test:{roc_auc:.7,brier_score:.2,observations:50,roc:[{fpr:0,tpr:0},{fpr:.2,tpr:.8},{fpr:1,tpr:1}]}}},
   feature_importance:[{feature:'mid',importance:-.01,std:.02}],importance_method:'Synthetic browser fixture',
   backtest:{...fixture.research.backtest,trades:2,net_profit:-20,return_pct:-.2,max_drawdown_pct:1.2,drawdown_method:'Event-time marks'}};
  await page.route('**/dashboard/data.js',route=>route.fulfill({contentType:'application/javascript',body:'window.OPTIONS_DATA='+JSON.stringify(fixture)}));
  await page.reload();assert(await page.locator('#verified-charts').isVisible());assert.equal(await page.locator('#roc-chart svg').count(),1);assert((await page.locator('#importance-chart').innerText()).includes('-0.0100'));assert((await page.locator('#backtest-result').innerText()).includes('-$20.00'));
  fixture.research.models.logistic.test.roc_auc=null;fixture.research.models.logistic.test.roc=[];
  await page.reload();assert((await page.locator('#roc-chart').innerText()).includes('both outcome classes'));
  assert.deepEqual(errors,[]);console.log('Browser checks passed: dataset rendering, filters, sorting, pagination, responsive layout, insufficient-data and evaluated states.');
 } finally {await browser.close();server.close();}
})().catch(error=>{console.error(error);server.close();process.exitCode=1;});
