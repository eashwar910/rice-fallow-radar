"""P0 step 8: sample 500 m cells per district and map FTW polygons over imagery for a visual check.

Writes data/interim/ftw_check/{index.html, ratings.csv}. Open index.html in a browser.
Usage: uv run python scripts/ftw_sample_map.py [cells_per_district]
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

CELL = 0.0045  # degrees, ~500 m N-S, ~470 m E-W at 21°N
PER_DISTRICT = int(sys.argv[1]) if len(sys.argv) > 1 else 6
OUT = Path("data/interim/ftw_check")
rng = np.random.default_rng(20261106)


def sample_cells(g: gpd.GeoDataFrame, n: int) -> pd.DataFrame:
    b = g.bounds
    cx = np.floor((b.minx + b.maxx) / 2 / CELL).astype(int)
    cy = np.floor((b.miny + b.maxy) / 2 / CELL).astype(int)
    counts = pd.DataFrame({"cx": cx, "cy": cy}).value_counts().rename("n").reset_index()
    # stratify by polygon density terciles so sparse and dense areas are both seen
    counts["stratum"] = pd.qcut(counts.n, 3, labels=["sparse", "median", "dense"])
    k = -(-n // 3)
    picked = counts.groupby("stratum", observed=True).sample(k, random_state=rng.integers(1e9))
    return picked.head(n), cx, cy


cells, layers = [], {}
for district in ["bolangir", "baleswar"]:
    g = gpd.read_parquet(f"data/raw/ftw/{district}.parquet")
    picked, cx, cy = sample_cells(g, PER_DISTRICT)
    for i, r in enumerate(picked.itertuples(), 1):
        cid = f"{district[:3]}-{i:02d}"
        cell = box(r.cx * CELL, r.cy * CELL, (r.cx + 1) * CELL, (r.cy + 1) * CELL)
        sub = g[g.intersects(cell)][["id", "area_m2", "geometry"]].copy()
        assert len(sub) >= r.n, cid
        sub["ha"] = (sub.area_m2 / 1e4).round(3)
        layers[cid] = json.loads(sub.drop(columns="area_m2").to_json())
        a = sub.area_m2 / 1e4
        cells.append(
            dict(
                cell_id=cid,
                district=district,
                stratum=r.stratum,
                n_polygons=len(sub),
                median_ha=round(a.median(), 3),
                pct_lt_004ha=round((a < 0.04).mean() * 100),
                lat=round(cell.centroid.y, 5),
                lon=round(cell.centroid.x, 5),
                bounds=list(cell.bounds),
            )
        )

OUT.mkdir(parents=True, exist_ok=True)
cols = ["cell_id", "district", "stratum", "n_polygons", "median_ha", "pct_lt_004ha", "lat", "lon"]
rating = pd.DataFrame(cells)[cols].assign(
    verdict="", over_split="", merged="", missed="", false_fields="", notes=""
)
rating.to_csv(OUT / "ratings.csv", index=False)

html = """<!doctype html><html><head><meta charset="utf-8"><title>FTW visual check</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>body{margin:0;font:14px system-ui;display:flex;height:100vh}
#side{width:320px;overflow:auto;padding:10px;background:#f6f6f6}#map{flex:1}
.c{padding:6px;margin:4px 0;background:#fff;border:1px solid #ddd;cursor:pointer}
.c.on{border-color:#06c;background:#eef5ff}.k span{display:inline-block;width:12px;height:12px;
margin-right:4px}</style></head><body><div id="side"><b>FTW visual check (P0 step 8)</b>
<div class="k"><span style="background:#e41a1c"></span>&lt;0.04 ha
<span style="background:#ff7f00;margin-left:8px"></span>0.04–0.1
<span style="background:#4daf4a;margin-left:8px"></span>&ge;0.1 ha</div>
<p>Keys: n / p = next / previous cell, h = hide polygons. Click a polygon for its area.</p>
<div id="list"></div></div><div id="map"></div><script>
const CELLS=__CELLS__, LAYERS=__LAYERS__;
const map=L.map('map').setView([21,85],8), img=L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/'+
 'World_Imagery/MapServer/tile/{z}/{y}/{x}',
 {maxNativeZoom:17,maxZoom:20,attribution:'Esri World Imagery'}).addTo(map);
const col=h=>h<0.04?'#e41a1c':h<0.1?'#ff7f00':'#4daf4a';
let cur=0, poly=null, frame=null, shown=true;
function show(i){cur=(i+CELLS.length)%CELLS.length;const c=CELLS[cur];
 poly&&map.removeLayer(poly);frame&&map.removeLayer(frame);
 poly=L.geoJSON(LAYERS[c.cell_id],{style:f=>({color:col(f.properties.ha),weight:1.5,fillOpacity:0.08}),
  onEachFeature:(f,l)=>l.bindPopup(f.properties.ha+' ha (id '+f.properties.id+')')});
 if(shown)poly.addTo(map);const b=c.bounds;
 frame=L.rectangle([[b[1],b[0]],[b[3],b[2]]],{color:'#fff',weight:2,fill:false,dashArray:'4'}).addTo(map);
 map.fitBounds(frame.getBounds());
 document.querySelectorAll('.c').forEach((e,j)=>e.classList.toggle('on',j==cur));}
document.getElementById('list').innerHTML=CELLS.map((c,i)=>`<div class="c" onclick="show(${i})">
 <b>${c.cell_id}</b> ${c.stratum}<br>${c.n_polygons} polygons, median ${c.median_ha} ha,
 ${c.pct_lt_004ha}% &lt;0.04 ha</div>`).join('');
document.onkeydown=e=>{if(e.key=='n')show(cur+1);if(e.key=='p')show(cur-1);
 if(e.key=='h'){shown=!shown;shown?poly.addTo(map):map.removeLayer(poly);}};
show(0);</script></body></html>"""
html = html.replace("__CELLS__", json.dumps(cells, default=str)).replace(
    "__LAYERS__", json.dumps(layers)
)
(OUT / "index.html").write_text(html)
print(pd.DataFrame(cells)[cols].to_string(index=False))
print(f"\nwrote {OUT}/index.html ({len(html) / 1e6:.1f} MB) and {OUT}/ratings.csv")
