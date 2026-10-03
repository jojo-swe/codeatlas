"""Zero-dependency local web explorer for CodeAtlas graphs."""

from __future__ import annotations

import json
import threading
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .analysis import GraphAnalysis
from .indexer import CodeIndex


def build_payload(index: CodeIndex, analysis: GraphAnalysis) -> dict[str, Any]:
    """Build the compact browser payload used by the interactive explorer."""
    cycle_members = {member for cycle in analysis.cycles() for member in cycle.members}
    hotspot_by_symbol = {item.symbol: asdict(item) for item in analysis.hotspots(limit=len(analysis.symbols))}
    nodes = []
    for name, symbol in sorted(analysis.symbols.items()):
        hotspot = hotspot_by_symbol[name]
        nodes.append(
            {
                "id": name,
                "label": symbol.name,
                "kind": symbol.kind,
                "file": symbol.file,
                "line": symbol.line,
                "risk": hotspot["risk_score"],
                "inbound": hotspot["inbound"],
                "outbound": hotspot["outbound"],
                "cycle": name in cycle_members,
            }
        )
    edges = [
        {"source": edge.source, "target": edge.target, "kind": edge.kind}
        for edge in sorted(analysis.edges, key=lambda item: (item.source, item.target, item.kind))
    ]
    return {
        "root": index.root,
        "summary": index.to_dict()["summary"],
        "analysis": analysis.summary(),
        "nodes": nodes,
        "edges": edges,
    }


_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeAtlas Explorer</title>
<style>
:root{color-scheme:dark;--bg:#09111f;--panel:#101b2d;--panel2:#14233a;--text:#edf5ff;--muted:#92a8c7;--accent:#62d9ff;--warn:#ffb95e;--danger:#ff6b7a;--ok:#79e6ad;--line:#29405f}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 20% 0,#142644 0,#09111f 42%);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,sans-serif;height:100vh;overflow:hidden}
header{height:68px;display:flex;align-items:center;gap:18px;padding:0 20px;border-bottom:1px solid var(--line);background:#09111fe8;backdrop-filter:blur(12px)}
h1{font-size:20px;margin:0;letter-spacing:.2px}.badge{padding:4px 9px;border:1px solid #315176;border-radius:999px;color:var(--accent);font-size:12px}.root{color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}
main{display:grid;grid-template-columns:300px 1fr 330px;height:calc(100vh - 68px)}aside{background:linear-gradient(180deg,var(--panel),#0d1727);overflow:auto;padding:16px;border-right:1px solid var(--line)}aside.right{border-right:0;border-left:1px solid var(--line)}
input,select,button{width:100%;background:#0b1627;color:var(--text);border:1px solid #2b4568;border-radius:8px;padding:9px 10px;margin-bottom:9px}button{cursor:pointer;font-weight:650}button:hover{border-color:var(--accent)}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin:12px 0}.stat{background:var(--panel2);border:1px solid #243b5b;border-radius:9px;padding:10px}.stat strong{font-size:20px;display:block}.stat span,.muted{color:var(--muted);font-size:12px}
h2{font-size:13px;text-transform:uppercase;letter-spacing:.12em;color:var(--muted);margin:18px 0 8px}.item{padding:9px;border:1px solid transparent;border-radius:8px;cursor:pointer;margin-bottom:5px;overflow-wrap:anywhere}.item:hover,.item.active{background:#172942;border-color:#315176}.risk{float:right;color:var(--warn)}.cycle{color:var(--danger)}
#stage{position:relative;overflow:hidden}svg{width:100%;height:100%;display:block}.edge{stroke:#3b587d;stroke-opacity:.62}.node circle{stroke:#08101d;stroke-width:2;cursor:pointer}.node text{fill:#dceaff;font-size:11px;pointer-events:none}.node.dim{opacity:.12}.edge.dim{opacity:.05}.node.selected circle{stroke:#fff;stroke-width:3}.tooltip{position:absolute;display:none;pointer-events:none;background:#07101dcc;border:1px solid #37577f;border-radius:8px;padding:8px 10px;max-width:300px;box-shadow:0 10px 28px #0008}
.kv{display:grid;grid-template-columns:90px 1fr;gap:6px;margin:7px 0}.kv b{color:var(--muted)}.pill{display:inline-block;padding:3px 7px;border-radius:999px;background:#203653;margin:2px;font-size:12px}.impact{color:var(--ok)}
.empty{color:var(--muted);padding:12px 0}.legend{display:flex;gap:10px;flex-wrap:wrap;color:var(--muted);font-size:11px}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:4px}
</style>
</head>
<body>
<header><h1>CodeAtlas</h1><span class="badge">Interactive Explorer</span><div class="root" id="root"></div></header>
<main>
<aside>
<input id="search" placeholder="Search symbol or file…" autocomplete="off">
<select id="kind"><option value="">All symbol kinds</option></select>
<select id="edgeKind"><option value="">All relationship kinds</option></select>
<button id="reset">Reset graph view</button>
<div class="stats" id="stats"></div>
<div class="legend"><span><i class="dot" style="background:#62d9ff"></i>function</span><span><i class="dot" style="background:#ae8cff"></i>class</span><span><i class="dot" style="background:#ff6b7a"></i>cycle</span></div>
<h2>Hotspots</h2><div id="hotspots"></div>
<h2>Dependency cycles</h2><div id="cycles"></div>
</aside>
<section id="stage"><svg id="graph"></svg><div class="tooltip" id="tooltip"></div></section>
<aside class="right"><h2>Selection</h2><div id="detail" class="empty">Select a node to inspect its dependencies and change impact.</div></aside>
</main>
<script>
const data=__DATA__;
const byId=new Map(data.nodes.map(n=>[n.id,n]));
const root=document.getElementById('root');root.textContent=data.root;
const stats=document.getElementById('stats');
stats.innerHTML=[['Files',data.summary.file_count],['Symbols',data.summary.symbol_count],['Resolved edges',data.analysis.resolved_edge_count],['Cycles',data.analysis.cycles.length]].map(([k,v])=>`<div class="stat"><strong>${v}</strong><span>${k}</span></div>`).join('');
const kind=document.getElementById('kind'),edgeKind=document.getElementById('edgeKind');
[...new Set(data.nodes.map(n=>n.kind))].sort().forEach(v=>kind.insertAdjacentHTML('beforeend',`<option>${v}</option>`));
[...new Set(data.edges.map(e=>e.kind))].sort().forEach(v=>edgeKind.insertAdjacentHTML('beforeend',`<option>${v}</option>`));
const hotspots=document.getElementById('hotspots');
data.analysis.hotspots.slice(0,15).forEach(h=>hotspots.insertAdjacentHTML('beforeend',`<div class="item" data-id="${esc(h.symbol)}"><span class="risk">${h.risk_score}</span>${esc(h.symbol)}<div class="muted">${h.inbound} in · ${h.outbound} out</div></div>`));
const cycles=document.getElementById('cycles');
if(!data.analysis.cycles.length) cycles.innerHTML='<div class="empty">No resolved cycles found.</div>';
data.analysis.cycles.forEach((c,i)=>cycles.insertAdjacentHTML('beforeend',`<div class="item cycle" data-cycle="${i}">Cycle ${i+1}<div class="muted">${c.length} symbols</div></div>`));
function esc(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const svg=document.getElementById('graph'),NS='http://www.w3.org/2000/svg',stage=document.getElementById('stage');
let width=stage.clientWidth,height=stage.clientHeight,selected=null,filterText='',filterKind='',filterEdge='';
const nodes=data.nodes.map((n,i)=>({...n,x:width/2+Math.cos(i)*Math.min(width,height)*.28,y:height/2+Math.sin(i)*Math.min(width,height)*.28,vx:0,vy:0}));
const nodeMap=new Map(nodes.map(n=>[n.id,n]));
const links=data.edges.map(e=>({...e,a:nodeMap.get(e.source),b:nodeMap.get(e.target)})).filter(e=>e.a&&e.b);
const edgeEls=links.map(l=>{const el=document.createElementNS(NS,'line');el.classList.add('edge');el.setAttribute('stroke-width',l.kind==='calls'?1.2:2);svg.appendChild(el);return el});
const nodeEls=nodes.map(n=>{const g=document.createElementNS(NS,'g');g.classList.add('node');const c=document.createElementNS(NS,'circle');c.setAttribute('r',Math.max(6,Math.min(18,6+Math.sqrt(n.risk||0)*1.4)));c.setAttribute('fill',n.cycle?'#ff6b7a':n.kind.includes('class')?'#ae8cff':'#62d9ff');const t=document.createElementNS(NS,'text');t.textContent=n.label;t.setAttribute('x',12);t.setAttribute('y',4);g.append(c,t);svg.appendChild(g);g.addEventListener('click',()=>select(n.id));g.addEventListener('mouseenter',e=>tip(e,n));g.addEventListener('mouseleave',()=>tooltip.style.display='none');return g});
const tooltip=document.getElementById('tooltip');function tip(e,n){tooltip.innerHTML=`<b>${esc(n.id)}</b><br><span class="muted">${esc(n.file)}:${n.line} · risk ${n.risk}</span>`;tooltip.style.display='block';tooltip.style.left=(e.clientX-stage.getBoundingClientRect().left+12)+'px';tooltip.style.top=(e.clientY-stage.getBoundingClientRect().top+12)+'px'}
function simulate(){for(let k=0;k<220;k++){for(const n of nodes){n.vx+=(width/2-n.x)*.0005;n.vy+=(height/2-n.y)*.0005}for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){const a=nodes[i],b=nodes[j],dx=a.x-b.x,dy=a.y-b.y,d2=Math.max(80,dx*dx+dy*dy),f=180/d2;a.vx+=dx*f;a.vy+=dy*f;b.vx-=dx*f;b.vy-=dy*f}for(const l of links){const dx=l.b.x-l.a.x,dy=l.b.y-l.a.y,d=Math.max(1,Math.hypot(dx,dy)),f=(d-95)*.002;l.a.vx+=dx*f;l.a.vy+=dy*f;l.b.vx-=dx*f;l.b.vy-=dy*f}for(const n of nodes){n.vx*=.86;n.vy*=.86;n.x=Math.max(24,Math.min(width-100,n.x+n.vx));n.y=Math.max(24,Math.min(height-24,n.y+n.vy))}}render()}
function render(){links.forEach((l,i)=>{const e=edgeEls[i];e.setAttribute('x1',l.a.x);e.setAttribute('y1',l.a.y);e.setAttribute('x2',l.b.x);e.setAttribute('y2',l.b.y)});nodes.forEach((n,i)=>nodeEls[i].setAttribute('transform',`translate(${n.x},${n.y})`));applyFilters()}
function matches(n){return(!filterText||n.id.toLowerCase().includes(filterText)||n.file.toLowerCase().includes(filterText))&&(!filterKind||n.kind===filterKind)}
function applyFilters(){nodes.forEach((n,i)=>nodeEls[i].classList.toggle('dim',!matches(n)));links.forEach((l,i)=>edgeEls[i].classList.toggle('dim',!matches(l.a)||!matches(l.b)||(filterEdge&&l.kind!==filterEdge)))}
function impactOf(id){const seen=new Set([id]),q=[id],out=[];while(q.length){const cur=q.shift();links.filter(l=>l.target===cur).forEach(l=>{if(!seen.has(l.source)){seen.add(l.source);out.push(l.source);q.push(l.source)}})}return out}
function select(id){selected=id;nodeEls.forEach((e,i)=>e.classList.toggle('selected',nodes[i].id===id));const n=byId.get(id),incoming=links.filter(l=>l.target===id),outgoing=links.filter(l=>l.source===id),impact=impactOf(id);document.getElementById('detail').innerHTML=`<h3>${esc(id)}</h3><div class="kv"><b>Kind</b><span>${esc(n.kind)}</span><b>Source</b><span>${esc(n.file)}:${n.line}</span><b>Risk</b><span>${n.risk}</span><b>Fan-in</b><span>${n.inbound}</span><b>Fan-out</b><span>${n.outbound}</span><b>Cycle</b><span>${n.cycle?'Yes':'No'}</span></div><h2>Outgoing</h2>${relationList(outgoing,'target')}<h2>Incoming</h2>${relationList(incoming,'source')}<h2>Transitive change impact</h2>${impact.length?impact.map(v=>`<span class="pill impact" data-id="${esc(v)}">${esc(v)}</span>`).join(''):'<div class="empty">No indexed callers affected.</div>'}`;document.querySelectorAll('[data-id]').forEach(e=>e.onclick=()=>select(e.dataset.id))}
function relationList(items,key){return items.length?items.map(l=>`<div class="item" data-id="${esc(l[key])}"><span class="muted">${esc(l.kind)}</span><br>${esc(l[key])}</div>`).join(''):'<div class="empty">None</div>'}
document.querySelectorAll('#hotspots [data-id]').forEach(e=>e.onclick=()=>select(e.dataset.id));document.querySelectorAll('[data-cycle]').forEach(e=>e.onclick=()=>{const ids=data.analysis.cycles[+e.dataset.cycle];filterText='';nodes.forEach((n,i)=>nodeEls[i].classList.toggle('dim',!ids.includes(n.id)));links.forEach((l,i)=>edgeEls[i].classList.toggle('dim',!(ids.includes(l.source)&&ids.includes(l.target))))});
document.getElementById('search').oninput=e=>{filterText=e.target.value.trim().toLowerCase();applyFilters()};kind.onchange=e=>{filterKind=e.target.value;applyFilters()};edgeKind.onchange=e=>{filterEdge=e.target.value;applyFilters()};document.getElementById('reset').onclick=()=>{filterText=filterKind=filterEdge='';document.getElementById('search').value='';kind.value=edgeKind.value='';selected=null;nodeEls.forEach(e=>e.classList.remove('selected','dim'));edgeEls.forEach(e=>e.classList.remove('dim'));simulate()};
window.onresize=()=>{width=stage.clientWidth;height=stage.clientHeight;simulate()};simulate();
</script>
</body></html>'''


def render_html(payload: dict[str, Any]) -> str:
    """Render a self-contained explorer document."""
    encoded = json.dumps(payload, separators=(",", ":")).replace("</", "<\\/")
    return _HTML.replace("__DATA__", encoded)


def serve(index: CodeIndex, analysis: GraphAnalysis, *, host: str = "127.0.0.1", port: int = 8765, open_browser: bool = True) -> None:
    """Serve the explorer until interrupted."""
    document = render_html(build_payload(index, analysis)).encode("utf-8")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if self.path not in {"/", "/index.html"}:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(document)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(document)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer((host, port), Handler)
    url = f"http://{host}:{server.server_port}/"
    print(f"CodeAtlas Explorer: {url}")
    if open_browser:
        threading.Timer(0.25, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
