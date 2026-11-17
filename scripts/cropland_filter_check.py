# ruff: noqa: E501  (embedded HTML/JS)
"""Open question #7: score cropland filters (WorldCover 2021, Dynamic World 2024) on FTW polygons.

For the 12 FTW check cells, takes polygons >= 0.1 ha (D-016), computes per polygon the
WorldCover cropland fraction and Dynamic World crop probabilities in Earth Engine, and writes
data/interim/cropland_check/index.html: Eashwar rates each polygon blind (real field / not a
field / can't tell), then the filter layers unlock for comparison.
Usage: uv run python scripts/cropland_filter_check.py
"""

import json
from pathlib import Path

import ee
import geopandas as gpd
import pandas as pd
from shapely.geometry import box

from rice_fallow_radar.ingest import earth_engine

HALF = 0.0045 / 2  # FTW check cells are 0.0045° squares; ratings.csv stores the centre
MIN_M2 = 1000  # D-016
OUT = Path("data/interim/cropland_check")

earth_engine.init()
wc_crop = ee.ImageCollection("ESA/WorldCover/v200").first().eq(40).rename("wc_crop")
# FTW polygons come from 2024 imagery, so use the same year of Dynamic World
dw = ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1").filterDate("2024-01-01", "2025-01-01")

cells = pd.read_csv("data/interim/ftw_check/ratings.csv")
frames = []
for district, grp in cells.groupby("district"):
    g = gpd.read_parquet(f"data/raw/ftw/{district}.parquet")
    g = g[g.area_m2 >= MIN_M2]
    for c in grp.itertuples():
        cell = box(c.lon - HALF, c.lat - HALF, c.lon + HALF, c.lat + HALF)
        sub = g[g.intersects(cell)][["id", "area_m2", "geometry"]].copy()
        if sub.empty:
            continue
        dwc = dw.filterBounds(ee.Geometry.Rectangle(list(cell.bounds)))
        img = wc_crop.addBands(
            [
                dwc.select("crops").mean().rename("dw_crops"),
                dwc.map(lambda i: i.select("crops").add(i.select("flooded_vegetation")))
                .mean()
                .rename("dw_crop_flood"),
            ]
        )
        fc = ee.FeatureCollection(json.loads(sub[["id", "geometry"]].to_json()))
        stats = img.reduceRegions(fc, ee.Reducer.mean(), scale=10).getInfo()["features"]
        vals = pd.DataFrame([f["properties"] for f in stats])
        sub = sub.merge(vals, on="id", how="left")
        sub["cell_id"] = c.cell_id
        sub["ha"] = (sub.pop("area_m2") / 1e4).round(3)
        frames.append(sub)
        print(c.cell_id, len(sub), "polygons")

polys = gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")
for col in ["wc_crop", "dw_crops", "dw_crop_flood"]:
    polys[col] = polys[col].astype(float).round(2)
OUT.mkdir(parents=True, exist_ok=True)
polys.drop(columns="geometry").to_csv(OUT / "filter_values.csv", index=False)
cell_list = cells[cells.cell_id.isin(polys.cell_id)][["cell_id", "verdict", "lat", "lon"]]

html = """<!doctype html><html><head><meta charset="utf-8"><title>Cropland filter check</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{margin:0;font:14px system-ui;display:flex;height:100vh;color:#222;background:#fff}
#side{width:330px;overflow:auto;padding:10px;background:#f6f6f6}#map{flex:1}
.c{padding:6px;margin:4px 0;background:#fff;border:1px solid #ddd;cursor:pointer}
.c.on{border-color:#06c;background:#eef5ff}button,select{margin:4px 0;font:inherit}
.k span{display:inline-block;width:12px;height:12px;margin:0 4px 0 8px}</style></head><body>
<div id="side"><b>Cropland filter check (open question #7)</b>
<p><b>Step 1, rate blind.</b> Click an outline to cycle:
<span style="color:#1a9850">real field</span> → <span style="color:#d73027">not a field</span>
→ <span style="color:#7570b3">can't tell</span> → unrated (white).<br>
n / p = next / previous cell, h = hide outlines.</p>
<p id="prog"></p>
<p><b>Step 2</b> (unlocks when all are rated): colour by
<select id="mode" disabled><option value="r">your rating</option>
<option value="wc_crop">WorldCover 2021: cropland fraction</option>
<option value="dw_crops">Dynamic World 2024: crops probability</option>
<option value="dw_crop_flood">Dynamic World 2024: crops + flooded veg.</option></select></p>
<div class="k" id="ramp" style="display:none">0<span style="background:#d73027"></span>
<span style="background:#fee08b"></span><span style="background:#1a9850"></span>1</div>
<button onclick="dl()">Download ratings CSV</button>
<p style="font-size:12px">Save it as <code>data/interim/cropland_check/polygon_ratings.csv</code>.
Ratings also persist in this browser.</p>
<div id="list"></div></div><div id="map"></div><script>
const CELLS=__CELLS__, P=__POLYS__, KEY='rfr-cropland-ratings';
const R=['','real','not_field','cant_tell'], RC={'':'#fff',real:'#1a9850',not_field:'#d73027',cant_tell:'#7570b3'};
let rat={};try{rat=JSON.parse(localStorage.getItem(KEY))||{}}catch(e){}
const save=()=>{try{localStorage.setItem(KEY,JSON.stringify(rat))}catch(e){}};
const map=L.map('map').setView([21,85],8);L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/'+
 'World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxNativeZoom:17,maxZoom:20,attribution:'Esri World Imagery'}).addTo(map);
const ramp=v=>v==null?'#888':v<0.5?(v<0.25?'#d73027':'#fc8d59'):(v<0.75?'#fee08b':'#1a9850');
const mode=document.getElementById('mode');let shown=true,cur=0;
const layer=L.geoJSON(P,{style:f=>sty(f),onEachFeature:(f,l)=>{l.on('click',()=>{const id=f.properties.id;
 rat[id]=R[(R.indexOf(rat[id]||'')+1)%R.length];save();layer.setStyle(sty);prog();});
 l.bindTooltip(()=>f.properties.ha+' ha'+(mode.value=='r'?'':' | WC '+f.properties.wc_crop+
 ' | DW '+f.properties.dw_crops+' | DW+flood '+f.properties.dw_crop_flood));}}).addTo(map);
function sty(f){const m=mode.value;return m=='r'?{color:RC[rat[f.properties.id]||''],weight:2,fillOpacity:0.15}
 :{color:ramp(f.properties[m]),weight:2,fillOpacity:0.35};}
function prog(){const n=P.features.filter(f=>rat[f.properties.id]).length,t=P.features.length;
 document.getElementById('prog').textContent=n+' / '+t+' rated';mode.disabled=n<t;}
mode.onchange=()=>{layer.setStyle(sty);document.getElementById('ramp').style.display=mode.value=='r'?'none':'block';};
function show(i){cur=(i+CELLS.length)%CELLS.length;const c=CELLS[cur],h=0.00225;
 map.fitBounds([[c.lat-h,c.lon-h],[c.lat+h,c.lon+h]]);
 document.querySelectorAll('.c').forEach((e,j)=>e.classList.toggle('on',j==cur));}
document.getElementById('list').innerHTML=CELLS.map((c,i)=>`<div class="c" onclick="show(${i})"><b>${c.cell_id}</b>
 (your cell verdict: ${c.verdict}) ${P.features.filter(f=>f.properties.cell_id==c.cell_id).length} outlines</div>`).join('');
function dl(){const rows=['id,cell_id,ha,rating'].concat(P.features.map(f=>[f.properties.id,f.properties.cell_id,
 f.properties.ha,rat[f.properties.id]||''].join(',')));const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([rows.join('\\n')],{type:'text/csv'}));a.download='polygon_ratings.csv';a.click();}
document.onkeydown=e=>{if(e.key=='n')show(cur+1);if(e.key=='p')show(cur-1);
 if(e.key=='h'){shown=!shown;shown?layer.addTo(map):map.removeLayer(layer);}};
prog();show(0);</script></body></html>"""
html = html.replace("__CELLS__", cell_list.to_json(orient="records")).replace(
    "__POLYS__", polys.to_json()
)
(OUT / "index.html").write_text(html)
print(f"\n{len(polys)} polygons in {polys.cell_id.nunique()} cells -> {OUT}/index.html")
print(polys[["wc_crop", "dw_crops", "dw_crop_flood"]].describe().round(2).to_string())
