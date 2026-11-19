# ruff: noqa: E501  (embedded HTML/JS)
"""P1b: build the offline harvest-labelling page from the pulled chips and NDVI series.

Same shape as scripts/cropland_filter_check.py -- one static HTML file, progress in localStorage,
keyboard shortcuts, CSV download -- but the unit of work is a field and the answer is a date
interval. Protocol: docs/LABELLING_PROTOCOL.md.

Usage: uv run python scripts/odisha_label_tool.py
Then open data/interim/odisha_labels/index.html.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

OUT = Path("data/interim/odisha_labels")
L = yaml.safe_load(Path("configs/districts.yaml").read_text())["labelling"]

HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Odisha harvest labelling</title>
<meta name="viewport" content="width=device-width, initial-scale=1"><style>
body{margin:0;font:14px system-ui;background:#fafafa;color:#222;display:flex;height:100vh}
#side{width:260px;padding:12px;overflow:auto;background:#f0f0f0;border-right:1px solid #ddd;overflow-wrap:anywhere}
#main{flex:1;overflow:auto;padding:14px}
h2{margin:0 0 6px;font-size:16px} .mut{color:#666;font-size:12px}
#strip{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.ch{width:130px;cursor:pointer;border:3px solid transparent;border-radius:4px;background:#fff;padding:2px}
.ch img{width:100%;display:block;image-rendering:pixelated;border-radius:2px}
.ch .d{font-size:11px;text-align:center;padding:1px} .ch .c{font-size:10px;color:#888;text-align:center}
.ch.green{border-color:#1a9850} .ch.brown{border-color:#d73027} .ch.between{background:#ffe9b0}
.ch.cloudy{opacity:.55}
button{font:inherit;margin:2px 0;padding:4px 7px;border:1px solid #bbb;background:#fff;border-radius:4px;cursor:pointer}
button.on{background:#06c;color:#fff;border-color:#06c}
#prog{font-weight:600;margin:8px 0} kbd{background:#fff;border:1px solid #bbb;border-bottom-width:2px;border-radius:3px;padding:0 4px;font-size:11px}
table.k{font-size:12px;border-collapse:collapse} table.k td{padding:1px 4px;vertical-align:top}
table.k td:first-child{white-space:nowrap}
#list{margin-top:8px;max-height:28vh;overflow:auto;font-size:12px}
#list div{padding:2px 4px;cursor:pointer;border-radius:3px}
#list div.cur{background:#06c;color:#fff} #list div.done{color:#1a9850}
textarea{width:100%;font:inherit;height:40px}
</style></head><body>
<div id="side">
<h2>Harvest labelling</h2>
<div class="mut">Protocol: docs/LABELLING_PROTOCOL.md. Read it before the first session.</div>
<div id="prog"></div>
<button onclick="dl()">Download CSV</button>
<button onclick="if(confirm('Clear ALL labels in this browser?')){lab={};save();render()}">Reset</button>
<p class="mut">Labels are saved in this browser after every action. Download the CSV at the end of
each session to <code>data/interim/odisha_labels/labels_&lt;date&gt;.csv</code>.</p>
<h2>Keys</h2>
<table class="k">
<tr><td><kbd>click</kbd></td><td>first clearly <b>harvested</b> image</td></tr>
<tr><td><kbd>shift</kbd>+click</td><td>last clearly <b>green</b> image</td></tr>
<tr><td><kbd>r</kbd></td><td>rice: yes / no / unsure</td></tr>
<tr><td><kbd>n</kbd></td><td>not rice (a crop, not kharif rice)</td></tr>
<tr><td><kbd>f</kbd></td><td>never green (fallow)</td></tr>
<tr><td><kbd>c</kbd></td><td>too cloudy</td></tr>
<tr><td><kbd>x</kbd></td><td>can't tell</td></tr>
<tr><td><kbd>z</kbd></td><td>not a field</td></tr>
<tr><td><kbd>u</kbd></td><td>clear this field</td></tr>
<tr><td><kbd>j</kbd> <kbd>k</kbd></td><td>prev / next field</td></tr>
<tr><td><kbd>enter</kbd></td><td>next unlabelled</td></tr>
</table>
<div id="list"></div></div>
<div id="main">
 <h2 id="title"></h2>
 <div class="mut" id="meta"></div>
 <div id="ndvi"></div>
 <div style="margin-top:8px">
  <span class="mut">rice?</span> <button id="rice" onclick="cycleRice()"></button>
  <span class="mut" style="margin-left:14px">status</span>
  <span id="codes"></span>
  <a id="cb" target="_blank" class="mut" style="margin-left:14px">open in Copernicus Browser &#8599;</a>
 </div>
 <div style="margin-top:6px"><textarea id="notes" placeholder="notes (optional)"></textarea></div>
 <div id="strip"></div>
</div>
<script>
const F=__FIELDS__, KEY='rfr-odisha-labels';
const CODES=[['not_rice','n'],['never_green','f'],['too_cloudy','c'],['cant_tell','x'],['not_a_field','z']];
const RICE=['','yes','no','unsure'];
let lab={}; try{lab=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
let cur=0;
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(lab))}catch(e){}};
const L=i=>lab[F[i].row_id]||(lab[F[i].row_id]={});
const done=i=>{const l=lab[F[i].row_id]; return l&&(l.status||l.first_brown)};

function ndviSvg(f,l){
  const W=620,H=110,P=28, xs=f.t.map(d=>Date.parse(d)), x0=Math.min(...xs), x1=Math.max(...xs);
  const X=d=>P+(Date.parse(d)-x0)/(x1-x0)*(W-P-8), Y=v=>H-12-(v+0.1)/1.1*(H-24);
  let pts=f.t.map((d,i)=>f.clear[i]?`${X(d)},${Y(f.v[i])}`:null).filter(Boolean).join(' ');
  let band='';
  if(l.last_green&&l.first_brown) band=`<rect x="${X(l.last_green)}" y="4" width="${Math.max(2,X(l.first_brown)-X(l.last_green))}" height="${H-16}" fill="#ffd27f" opacity=".6"/>`;
  const dots=f.t.map((d,i)=>`<circle cx="${X(d)}" cy="${Y(f.v[i])}" r="${f.clear[i]?2.5:1.5}" fill="${f.clear[i]?'#060':'#bbb'}"/>`).join('');
  const ticks=['2025-10-01','2025-11-01','2025-12-01','2026-01-01','2026-02-01'].filter(d=>Date.parse(d)>=x0&&Date.parse(d)<=x1)
    .map(d=>`<line x1="${X(d)}" y1="4" x2="${X(d)}" y2="${H-12}" stroke="#ddd"/><text x="${X(d)}" y="${H-2}" font-size="9" fill="#888" text-anchor="middle">${d.slice(2,7)}</text>`).join('');
  return `<svg width="${W}" height="${H}" style="background:#fff;border:1px solid #ddd;border-radius:4px">
   ${band}${ticks}<text x="2" y="${Y(0.8)}" font-size="9" fill="#888">0.8</text><text x="2" y="${Y(0.2)}" font-size="9" fill="#888">0.2</text>
   <polyline points="${pts}" fill="none" stroke="#060" stroke-width="1.5"/>${dots}</svg>`;
}

function render(){
  const f=F[cur], l=L(cur);
  document.getElementById('title').textContent=`${f.row_id}  (${cur+1} of ${F.length})`;
  document.getElementById('meta').textContent=
    `${f.district} · ${f.ha} ha · ${f.chips.length} clear images · WorldCover cropland ${f.wc}`;
  document.getElementById('ndvi').innerHTML=ndviSvg(f,l);
  document.getElementById('rice').textContent='rice: '+(l.rice||'—');
  document.getElementById('codes').innerHTML=CODES.map(([c,k])=>
    `<button class="${l.status==c?'on':''}" onclick="setStatus('${c}')">${c} <kbd>${k}</kbd></button>`).join(' ');
  document.getElementById('cb').href=
    `https://browser.dataspace.copernicus.eu/?zoom=16&lat=${f.lat}&lng=${f.lon}&themeId=DEFAULT-THEME&datasetId=S2_L2A_CDAS&fromTime=2025-11-01T00:00:00.000Z&toTime=2026-01-31T23:59:59.999Z`;
  document.getElementById('notes').value=l.notes||'';
  document.getElementById('strip').innerHTML=f.chips.map(c=>{
    let cls='ch'+(c.cloud>0.25?' cloudy':'');  // most clear scenes here sit at 0.12-0.22
    if(c.d==l.last_green)cls+=' green'; if(c.d==l.first_brown)cls+=' brown';
    if(l.last_green&&l.first_brown&&c.d>l.last_green&&c.d<l.first_brown)cls+=' between';
    return `<div class="${cls}" onclick="pick(event,'${c.d}')"><img loading="lazy" src="chips/${f.fid}/${c.d}.png">
      <div class="d">${c.d.slice(5)}</div><div class="c">ndvi ${c.v} · cloud ${c.cloud}</div></div>`;}).join('');
  document.getElementById('prog').textContent=F.filter((_,i)=>done(i)).length+' / '+F.length+' labelled';
  document.getElementById('list').innerHTML=F.map((g,i)=>
    `<div class="${i==cur?'cur':''} ${done(i)?'done':''}" onclick="go(${i})">${g.row_id} ${done(i)?'✓':''}</div>`).join('');
  document.querySelector('#list div.cur')?.scrollIntoView({block:'nearest'});
}
function pick(ev,d){
  const l=L(cur);
  if(ev.shiftKey){ l.last_green=(l.last_green==d)?null:d; }
  else {
    if(l.first_brown==d){ l.first_brown=null; }
    else {
      l.first_brown=d;
      // default the green end to the previous clear image, which is the usual answer
      const ds=F[cur].chips.map(c=>c.d), i=ds.indexOf(d);
      if(!l.last_green || l.last_green>=d) l.last_green = i>0?ds[i-1]:null;
    }
  }
  if(l.first_brown) l.status='ok';
  l.ts=new Date().toISOString(); save(); render();
}
function setStatus(c){ const l=L(cur); l.status=(l.status==c)?null:c;
  if(l.status&&l.status!='ok'){l.first_brown=null;l.last_green=null;}
  if(l.status=='not_rice')l.rice='no'; l.ts=new Date().toISOString(); save(); render(); }
function cycleRice(){ const l=L(cur); l.rice=RICE[(RICE.indexOf(l.rice||'')+1)%RICE.length];
  l.ts=new Date().toISOString(); save(); render(); }
function go(i){ cur=(i+F.length)%F.length; render(); window.scrollTo(0,0); }
function nextUnlabelled(){ for(let n=1;n<=F.length;n++){const i=(cur+n)%F.length; if(!done(i))return go(i);} }
document.getElementById('notes').addEventListener('input',e=>{L(cur).notes=e.target.value;save();});
document.onkeydown=e=>{
  if(e.target.tagName=='TEXTAREA') return;
  const m=CODES.find(([,k])=>k==e.key); if(m) return setStatus(m[0]);
  if(e.key=='r')cycleRice(); if(e.key=='j')go(cur-1); if(e.key=='k')go(cur+1);
  if(e.key=='Enter')nextUnlabelled();
  if(e.key=='u'){delete lab[F[cur].row_id];save();render();}
};
function dl(){
  const head='row_id,field_id,district,rice,status,last_green,first_brown,interval_days,midpoint,notes,labelled_at';
  const rows=F.map(f=>{const l=lab[f.row_id]||{};
    let iv='',mid='';
    if(l.last_green&&l.first_brown){const a=Date.parse(l.last_green),b=Date.parse(l.first_brown);
      iv=Math.round((b-a)/864e5); mid=new Date((a+b)/2).toISOString().slice(0,10);}
    return [f.row_id,f.fid,f.district,l.rice||'',l.status||'',l.last_green||'',l.first_brown||'',iv,mid,
            '"'+(l.notes||'').replace(/"/g,'""')+'"',l.ts||''].join(',');});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(new Blob([[head].concat(rows).join('\\n')],{type:'text/csv'}));
  a.download='labels_'+new Date().toISOString().slice(0,10)+'.csv'; a.click();
}
render();
</script></body></html>"""


def main() -> None:
    sel = pd.read_parquet(OUT / "selected.parquet").sort_values("order")
    ndvi = pd.read_parquet(OUT / "ndvi.parquet")
    pool = gpd.read_parquet(OUT / "sample.parquet").set_index("field_id")
    lo, hi = (str(d) for d in L["chip_window"])
    ndvi = ndvi[ndvi.date.between(lo, hi)].sort_values("date")

    fields, missing = [], 0
    for r in sel.itertuples():
        g = ndvi[ndvi.field_id == r.field_id].drop_duplicates("date")
        clear = g[g.cloud_mean <= L["cloud_max"]]
        chips = []
        for s in clear.itertuples():
            d = f"{s.date:%Y-%m-%d}"
            if (OUT / "chips" / r.field_id / f"{d}.png").exists():
                chips.append(
                    dict(d=d, v=round(float(s.ndvi_mean), 2), cloud=round(float(s.cloud_mean), 2))
                )
            else:
                missing += 1
        fields.append(
            dict(
                row_id=r.row_id,
                fid=r.field_id,
                district=r.district,
                ha=round(r.area_m2 / 1e4, 3),
                wc=round(float(r.wc_crop), 2) if pd.notna(r.wc_crop) else None,
                lat=round(float(pool.lat[r.field_id]), 5),
                lon=round(float(pool.lon[r.field_id]), 5),
                chips=chips,
                # the NDVI curve uses every scene, cloudy ones greyed, so gaps are visible
                t=[f"{d:%Y-%m-%d}" for d in g.date],
                v=[round(float(x), 2) for x in g.ndvi_mean],
                clear=[bool(c <= L["cloud_max"]) for c in g.cloud_mean],
            )
        )
    (OUT / "index.html").write_text(HTML.replace("__FIELDS__", json.dumps(fields)))
    n_chips = sum(len(f["chips"]) for f in fields)
    print(
        f"{len(fields)} rows ({sel.repeat_of.notna().sum()} repeats), {n_chips} chips "
        f"(median {int(pd.Series([len(f['chips']) for f in fields]).median())} per field), "
        f"{missing} clear dates without a chip"
    )
    print(f"open {OUT}/index.html")


if __name__ == "__main__":
    sys.exit(main())
