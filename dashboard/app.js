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
$('updated').textContent = 'Collected ' + data.latestCollection.slice(0,10);
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
  for(const value of [r.expiry.slice(0,10),price(r.strike),price(r.lastPrice),`${price(r.bid)} / ${price(r.ask)}`,number.format(r.volume),number.format(r.openInterest),`${(r.impliedVolatility*100).toFixed(1)}%`]){const td=document.createElement('td');td.textContent=value;tr.append(td);}
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
