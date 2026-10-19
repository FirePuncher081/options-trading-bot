'use strict';
const data = window.OPTIONS_DATA;
const $ = id => document.getElementById(id);
const number = new Intl.NumberFormat('en-US');
const price = value => Number.isFinite(value) ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD'}).format(value) : '—';
let page = 0;
const pageSize = 12;
$('contract-count').textContent = number.format(data.contracts.length);
$('ticker-count').textContent = Object.keys(data.tickerCounts).length;
$('training-count').textContent = number.format(data.trainingRows);
$('updated').textContent = data.latestCollection ? 'Collected ' + data.latestCollection.slice(0,10) : 'No usable collection dates';
const spreads = data.contracts.filter(r => r.bid > 0 && r.ask >= r.bid).map(r => r.ask-r.bid).sort((a,b)=>a-b);
const middle = Math.floor(spreads.length/2);
$('spread').textContent = spreads.length ? price(spreads.length % 2 ? spreads[middle] : (spreads[middle-1]+spreads[middle])/2) : '—';
function bars(target, entries) {
 const maximum = Math.max(1,...entries.map(e=>e[1]));
 for (const [label,count] of entries) {
  const row = document.createElement('div'); row.className='bar-row';
  const name=document.createElement('span'); name.textContent=label;
  const track=document.createElement('div'); track.className='bar-track';
  const fill=document.createElement('div'); fill.className='bar-fill'; fill.style.width=`${count/maximum*100}%`;track.append(fill);
  const value=document.createElement('span');value.textContent=number.format(count);value.className='bar-value';
  row.append(name,track,value);$(target).append(row);
 }
}
bars('coverage',Object.entries(data.tickerCounts).sort((a,b)=>b[1]-a[1]));
bars('liquidity',[['0–9',data.contracts.filter(r=>r.volume<10).length],['10–99',data.contracts.filter(r=>r.volume>=10&&r.volume<100).length],['100–999',data.contracts.filter(r=>r.volume>=100&&r.volume<1000).length],['1,000+',data.contracts.filter(r=>r.volume>=1000).length]]);
for (const [id,values] of [['ticker',Object.keys(data.tickerCounts).sort()],['expiry',[...new Set(data.contracts.map(r=>r.expiry.slice(0,10)))].sort()]]) {
 for(const value of values){const option=document.createElement('option');option.value=value;option.textContent=value;$(id).append(option);}
}
function render(){
 const query=$('search').value.trim().toUpperCase(),sort=$('sort').value;
 const filtered=data.contracts.filter(r=>(!$('ticker').value||r.ticker===$('ticker').value)&&(!$('expiry').value||r.expiry.slice(0,10)===$('expiry').value)&&r.volume>=Number($('volume').value)&&(!query||r.contractSymbol.toUpperCase().includes(query)));
 filtered.sort((a,b)=>sort==='expiry'?a.expiry.localeCompare(b.expiry):sort==='strike'?a.strike-b.strike:b[sort]-a[sort]);
 page=Math.min(page,Math.max(0,Math.ceil(filtered.length/pageSize)-1));
 $('contracts').replaceChildren();
 for(const r of filtered.slice(page*pageSize,(page+1)*pageSize)){
  const tr=document.createElement('tr');const identity=document.createElement('td');
  const symbol=document.createElement('strong');symbol.textContent=r.ticker;const contract=document.createElement('small');contract.textContent=r.contractSymbol;identity.append(symbol,contract);tr.append(identity);
  for(const value of [r.expiry.slice(0,10),price(r.strike),price(r.lastPrice),`${price(r.bid)} / ${price(r.ask)}`,number.format(r.volume),number.format(r.openInterest),`${(r.impliedVolatility*100).toFixed(1)}%`,r.date_collected.slice(0,10)]){const td=document.createElement('td');td.textContent=value;tr.append(td);}
  $('contracts').append(tr);
 }
 $('result-count').textContent=`${number.format(filtered.length)} contracts`;
 $('empty').hidden=filtered.length>0;
 $('page-info').textContent=filtered.length?`${number.format(page*pageSize+1)}–${number.format(Math.min((page+1)*pageSize,filtered.length))} of ${number.format(filtered.length)}`:'0 results';
 $('previous').disabled=page===0;$('next').disabled=(page+1)*pageSize>=filtered.length;
}
for(const id of ['search','ticker','expiry','volume','sort'])$(id).addEventListener(id==='search'?'input':'change',()=>{page=0;render();});
$('previous').addEventListener('click',()=>{page--;render();});$('next').addEventListener('click',()=>{page++;render();});
$('reset').addEventListener('click',()=>{for(const id of ['search','ticker','expiry'])$(id).value='';$('volume').value='0';$('sort').value='volume';page=0;render();});
render();

// Render only exported, provenance-checked results from the research pipeline.
const research = data.research;
$('research-status').textContent = research.status === 'ready' ? 'Evaluated' : 'More history needed';
$('research-context').textContent = `${research.dataset.usable_rows.toLocaleString()} usable snapshots · ${research.dataset.collection_dates} collection dates · ${research.labeled_rows.toLocaleString()} matched outcomes · Pipeline ${research.pipeline_version}`;
$('research-message').textContent = research.status === 'ready'
 ? `Selected model: ${research.selected_model}. Selection uses validation Brier score; the final test period is held out.`
 : `${research.reason} ${research.next_step}`;
const method = $('research-method');
for (const line of [research.target, research.split_method, research.model_selection, ...research.limitations,
 ...research.inputs.map(input => `${input.file} · SHA-256 ${input.sha256}`)]) {
 const p = document.createElement('p'); p.textContent = line; method.append(p);
}
function svgElement(name, attributes = {}) {
 const node = document.createElementNS('http://www.w3.org/2000/svg', name);
 for(const [key,value] of Object.entries(attributes)) node.setAttribute(key,value);
 return node;
}
function rocChart(points) {
 const svg=svgElement('svg',{viewBox:'0 0 360 245',role:'img','aria-label':'Held-out ROC curve: false positive rate on x axis, true positive rate on y axis'});
 svg.append(svgElement('line',{x1:40,y1:205,x2:340,y2:15,stroke:'#9aaabd','stroke-dasharray':'5 5'}));
 svg.append(svgElement('path',{d:'M40 15 V205 H340',fill:'none',stroke:'#9aaabd'}));
 svg.append(svgElement('polyline',{points:points.map(p=>`${40+p.fpr*300},${205-p.tpr*190}`).join(' '),fill:'none',stroke:'#61d6be','stroke-width':3}));
 for(const [x,y,text] of [[40,222,'0'],[333,222,'1'],[22,205,'0'],[22,20,'1'],[100,242,'False positive rate'],[45,12,'True positive rate']]) {
  const label=svgElement('text',{x,y,fill:'#9aaabd','font-size':11});label.textContent=text;svg.append(label);
 }
 return svg;
}
if(research.status === 'ready') {
 $('research-metrics').hidden=false;
 for(const [name,result] of Object.entries(research.models)) {
  const card=document.createElement('article');const title=document.createElement('h3');title.textContent=name;
  const score=document.createElement('p');score.textContent=`Test ROC-AUC: ${result.test.roc_auc === null ? 'Unavailable (one class)' : result.test.roc_auc.toFixed(3)}`;
  const brier=document.createElement('p');brier.textContent=`Brier loss: ${result.test.brier_score.toFixed(3)} · ${result.test.observations} test observations`;
  card.append(title,score,brier);$('research-metrics').append(card);
 }
 const selected=research.models[research.selected_model];
 $('verified-charts').hidden=false;
 if(selected.test.roc.length) $('roc-chart').append(rocChart(selected.test.roc));
 else $('roc-chart').textContent='ROC requires both outcome classes in the held-out period.';
 for(const row of research.feature_importance) {
  const p=document.createElement('p');p.className='importance-row';
  const label=document.createElement('span');label.textContent=row.feature;
  const value=document.createElement('span');value.textContent=`${row.importance.toFixed(4)} ± ${row.std.toFixed(4)}`;
  p.append(label,value);$('importance-chart').append(p);
 }
 const importanceNote=document.createElement('p');importanceNote.className='footnote';importanceNote.textContent=research.importance_method;$('importance-chart').append(importanceNote);
 const split=research.split;
 $('research-context').textContent+=` · Test ${split.test.start.slice(0,10)} → ${split.test.end.slice(0,10)}`;
 const bt=research.backtest;
 $('backtest-result').textContent=`Simulation: ${bt.trades} closed positions · net P&L ${price(bt.net_profit)} · return ${bt.return_pct.toFixed(2)}% · event-time drawdown ${bt.max_drawdown_pct.toFixed(2)}%. Initial cash ${price(bt.config.initial_cash)}; ${(bt.config.allocation*100).toFixed(0)}% allocation; ${bt.config.max_positions} maximum positions; fee ${price(bt.config.fee_per_contract)} per contract per side; ${bt.config.slippage_bps} bps slippage. ${bt.drawdown_method || ''}`;
} else {
 $('backtest-result').textContent='Backtest not run: no valid out-of-time signals are available. No model scores or simulated profits are published.';
}
