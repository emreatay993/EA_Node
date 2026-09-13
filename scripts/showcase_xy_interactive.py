# Purpose: Standalone, offline XY desktop showcase with live Python interactions.
# Map: docs/agent_maps/feature_routes/plotter_nodes.md
# Tests: tests/test_xy_interactive_showcase.py
r"""Run with ``venv\Scripts\python.exe scripts\showcase_xy_interactive.py``.

Requires the repository's XY 0.0.6, NumPy, PyQt6 and PyQt6-WebEngine packages.
``--points`` changes the density example; ``--smoke-test`` opens the real window,
checks every chart and a live append/reset cycle, then exits within 45 seconds.
No application imports, external server, notebook, or network assets are needed.

XY's widget ESM expects an anywidget-like model. The small JavaScript model below
adapts that contract to QWebChannel, retaining individual binary buffers (base64
on this JSON-only transport) and XY's native sequence numbers. All figures and
their canonical data remain on one worker thread.
"""

from __future__ import annotations

import argparse
import base64
import importlib.metadata
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any


DEFAULT_POINTS = 1_000_000
STREAM_BLOCK = 100
STREAM_INTERVAL_MS = 100
STREAM_LIMIT = 20_000
PREVIEW_LIMIT = 8
TAB_CHARTS = {
    "signals": ("signals",),
    "selections": ("selections",),
    "linked": ("linked-a", "linked-b"),
    "large": ("large",),
    "streaming": ("stream",),
}


def load_dependencies() -> None:
    """Delay imports so --help and missing-dependency errors remain useful."""
    global np, xy, ChannelCallbacks, handle_message
    import numpy as np
    import xy
    from xy.channel import ChannelCallbacks, handle_message

    if importlib.metadata.version("xy") != "0.0.6":
        raise RuntimeError("This transport demo targets xy==0.0.6; use the repository venv.")


def signal_data(start: int, count: int) -> tuple[Any, Any]:
    x = np.arange(start, start + count, dtype=np.float64) / 1000.0
    y = np.sin(2 * np.pi * 7 * x) + 0.22 * np.sin(2 * np.pi * 31 * x)
    return x, y


def scatter_data(count: int, seed: int = 42) -> tuple[Any, Any]:
    rng = np.random.default_rng(seed)
    cluster = rng.integers(0, 3, count)
    x = rng.normal(0, 0.75, count) + (cluster - 1) * 2.3
    y = 0.6 * x + rng.normal(0, 0.65, count) + (cluster == 1) * 1.8
    return x, y


def pack_buffers(buffers: Any) -> list[str]:
    return [base64.b64encode(memoryview(buf)).decode("ascii") for buf in (buffers or [])]


def selection_summary(selection: Any) -> dict[str, Any]:
    """Compute statistics on canonical f64 rows, bounding only the row preview."""
    traces = []
    for trace_id in sorted(selection.per_trace):
        x, y = selection.xy(trace_id)
        if len(x):
            traces.append({"trace": trace_id, "count": len(x),
                           "x_mean": float(np.mean(x)), "y_mean": float(np.mean(y)),
                           "y_min": float(np.min(y)), "y_max": float(np.max(y))})
    return {"count": len(selection), "traces": traces,
            "rows": selection.rows(PREVIEW_LIMIT), "preview_limit": PREVIEW_LIMIT}


class ShowcaseState:
    """Worker-owned figures, generation checks and bounded streaming state."""

    def __init__(self, points: int = DEFAULT_POINTS):
        self.points = points
        self.figures: dict[str, Any] = {}
        self.generations: dict[str, int] = {}
        self.active_tab = "signals"
        self.running = False
        self.stream_count = 0

    def _chart(self, marks: list[Any], title: str, xlabel: str, ylabel: str,
               *, linked: bool = False, selection: bool = False, height: int = 440) -> Any:
        return xy.chart(
            *marks, xy.x_axis(label=xlabel), xy.y_axis(label=ylabel),
            xy.legend(), xy.tooltip(), xy.modebar(),
            xy.theme(background="#ffffff", plot_background="#ffffff",
                     text_color="#17243a", grid_color="#e5ebf2"),
            title=title, width="100%", height=height,
            class_names={"root": "xy-chart-root", "canvas": "xy-canvas"},
            hover=True, select=True, crosshair=True,
            default_drag_action="select" if selection else "pan",
            link_group="showcase-time" if linked else None,
            link_axes=("x",) if linked else None,
        ).figure()

    @staticmethod
    def _transport_spec(spec: dict[str, Any]) -> dict[str, Any]:
        spec["interaction"] = {**spec.get("interaction", {}), "_transport_view_change": True}
        return spec

    def _envelope(self, chart: str, kind: str, **values: Any) -> dict[str, Any]:
        return {"kind": kind, "chart": chart, "generation": self.generations[chart], **values}

    def initialize(self, tab: str, generation: int) -> list[dict[str, Any]]:
        chart_ids = TAB_CHARTS[tab]
        if any(generation <= self.generations.get(chart, -1) for chart in chart_ids):
            return []
        figures = []
        if tab == "signals":
            x, y = signal_data(0, 12_000)
            figures = [self._chart([
                xy.line(x, y, name="Bearing A", color="#2563eb"),
                xy.line(x, 0.6 * y + 0.3 * np.cos(2 * np.pi * 3 * x),
                        name="Bearing B", color="#ea580c"),
            ], "Vibration channels", "Time (s)", "Acceleration (g)")]
        elif tab in {"selections", "large"}:
            count = 6000 if tab == "selections" else self.points
            x, y = scatter_data(count)
            mark = xy.scatter(x, y, color=y if tab == "selections" else "#2563eb",
                              name="Operating samples", size=4, density=tab == "large")
            figures = [self._chart([mark], f"{count:,} operating samples",
                                  "Displacement (mm)", "Response (MPa)", selection=True)]
        elif tab == "linked":
            x = np.linspace(0, 60, 6000)
            figures = [
                self._chart([xy.line(x, 65 + 14 * np.sin(x / 9), name="Temperature",
                                     color="#ea580c")], "Temperature", "Time (s)",
                            "Temperature (°C)", linked=True, height=280),
                self._chart([xy.line(x, 250 + 90 * np.cos(x / 8), name="Stress",
                                     color="#2563eb")], "Stress", "Time (s)",
                            "Stress (MPa)", linked=True, height=280),
            ]
        elif tab == "streaming":
            self.running = False
            self.stream_count = STREAM_BLOCK
            x, y = signal_data(0, self.stream_count)
            figures = [self._chart([xy.line(x, y, name="Live sensor", color="#0891b2")],
                                  "Live vibration", "Time (s)", "Acceleration (g)")]
        events = []
        for chart, figure in zip(chart_ids, figures, strict=True):
            self.figures[chart] = figure
            self.generations[chart] = generation
            spec, buffers = figure.build_payload_split()
            events.append(self._envelope(chart, "mount", spec=self._transport_spec(spec),
                                         buffers=pack_buffers(buffers)))
        if tab == "streaming":
            events.append(self.stream_status())
        return events

    def matches(self, chart: str, generation: int) -> bool:
        return chart in self.figures and self.generations.get(chart) == generation

    def message(self, chart: str, generation: int, message: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.matches(chart, generation):
            return []
        events = []
        def event(name: str, value: Any) -> None:
            events.append(self._envelope(chart, name, value=value))
        reply = handle_message(self.figures[chart], message, callbacks=ChannelCallbacks(
            on_hover=lambda row: event("hover", row),
            on_select=lambda selection: event("selection", selection_summary(selection)),
            on_view_change=lambda view: event("view", view),
        ))
        if reply is not None:
            msg, buffers = reply
            events.append(self._envelope(chart, "reply", message=msg, buffers=pack_buffers(buffers)))
        return events

    def stream_status(self) -> dict[str, Any]:
        return self._envelope("stream", "stream", count=self.stream_count,
                              running=self.running, limit=STREAM_LIMIT)

    def activate(self, tab: str) -> list[dict[str, Any]]:
        self.active_tab = tab
        if tab != "streaming" and "stream" in self.figures:
            self.running = False
            return [self.stream_status()]
        return []

    def control_stream(self, action: str, generation: int) -> list[dict[str, Any]]:
        if not self.matches("stream", generation):
            return []
        self.running = (action == "start" and self.active_tab == "streaming"
                        and self.stream_count < STREAM_LIMIT)
        return [self.stream_status()]

    def tick(self) -> list[dict[str, Any]]:
        if not self.running or self.active_tab != "streaming":
            return []
        count = min(STREAM_BLOCK, STREAM_LIMIT - self.stream_count)
        if count <= 0:
            self.running = False
            return [self.stream_status()]
        x, y = signal_data(self.stream_count, count)
        msg, buffers = self.figures["stream"].append(0, x, y)
        self.stream_count += count
        self.running = self.stream_count < STREAM_LIMIT
        return [self._envelope("stream", "update", spec=self._transport_spec(msg["spec"]),
                               buffers=pack_buffers(buffers)), self.stream_status()]


HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="color-scheme" content="light">
<title>XY interactive desktop showcase</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f2f5fa;color:#17243a;font:14px 'Segoe UI',sans-serif}
header{padding:22px 30px 15px;background:white;border-bottom:1px solid #dbe3ee}
h1{margin:0 0 5px;font-size:25px}header p{margin:0;color:#53647c}
nav{display:flex;gap:8px;margin-top:20px}.demo-button{font:inherit;cursor:pointer;border:1px solid #c8d4e4;
background:white;border-radius:7px;padding:9px 15px;color:#24364f}
.demo-button:hover{background:#eaf0fa}.demo-button[aria-selected=true]{background:#1d4ed8;color:white;border-color:#1d4ed8}
.demo-button:disabled{opacity:.45;cursor:default}main{padding:18px 28px}.tab[hidden]{display:none}
.intro{margin:0 0 14px;line-height:1.6;color:#435771}.chart{background:white;border:1px solid #dbe3ee;
border-radius:10px;padding:5px;min-height:280px;overflow:hidden}.status{padding:10px 0;color:#435771}
.readout{background:#fff;border:1px solid #dbe3ee;border-radius:8px;padding:12px;margin-top:10px}
.readout p{margin:4px 0}pre{font:12px Consolas,monospace;white-space:pre-wrap;max-height:170px;overflow:auto}
.error{color:#b42318;background:#fff1f0;padding:12px;border-radius:7px;white-space:pre-wrap}
.controls{display:flex;align-items:center;gap:8px;margin-bottom:12px}.linked{display:grid;gap:12px}
.hint{font-size:12px;color:#63758d}#global-error:empty{display:none}
/* XY's CSS is layered: unscoped host button rules override even its specific
   menu selectors. Keep host controls separate and use XY's published slots. */
.xy-chart-root{--chart-modebar-bg:#fff;--chart-modebar-active:#dbeafe;
--chart-selection:#2563eb;--chart-selection-fill:rgba(37,99,235,.10);
--chart-zoom-selection:#b45309;--chart-zoom-selection-fill:rgba(217,119,6,.10)}
.xy-chart-root [data-xy-slot="modebar"]{opacity:1!important;pointer-events:auto!important;transition:none!important}
.xy-chart-root button[data-xy-slot="modebar_button"].xy-active{background:#dbeafe;color:#1d4ed8;border-color:#93c5fd}
.xy-chart-root button[data-xy-modebar-action="pan"]{width:auto;gap:5px;padding:0 7px;font-size:12px}
.xy-chart-root button[data-xy-modebar-action="pan"]::after{content:"Pan"}
.xy-chart-root button[data-xy-modebar-select-trigger]::after{content:"Select"}
.mode-hint{display:flex;flex-wrap:wrap;gap:6px 16px;padding:7px 10px;color:#435771;font-size:12px;line-height:1.5}
.mode-hint strong{color:#17243a}
</style><script src="qrc:///qtwebchannel/qwebchannel.js"></script></head>
<body><header><h1>XY · interactive desktop lab</h1><p>Offline charts with a live Python data engine. Synthetic engineering data; XY 0.0.6.</p>
<nav role="tablist" aria-label="Plot examples">
<button class="demo-button" role="tab" data-tab="signals" aria-selected="true">Signals</button>
<button class="demo-button" role="tab" data-tab="selections" aria-selected="false">Selections</button>
<button class="demo-button" role="tab" data-tab="linked" aria-selected="false">Linked plots</button>
<button class="demo-button" role="tab" data-tab="large" aria-selected="false">Large data</button>
<button class="demo-button" role="tab" data-tab="streaming" aria-selected="false">Streaming</button></nav></header>
<main><div id="global-error" class="error" role="alert"></div>
<section class="tab" id="tab-signals"><p class="intro">Drag to pan; use the wheel to zoom around the pointer. Choose Box Zoom from the zoom menu; the active drag tool is shown above the plot. Double-click in Pan mode to reset. Hover for exact values and crosshairs; click legend entries to hide or show traces.</p><div class="chart" id="signals"></div><div class="status" id="status-signals">Connecting to Python…</div></section>
<section class="tab" id="tab-selections" hidden><p class="intro">Choose Select → Box Select or Lasso Select, then drag on the plot. Choose Pan to navigate; clicking an already active Pan pauses navigation. The Python count and statistics use all selected rows; the preview shows at most 8. Use Clear selection below to remove the selection.</p><div class="controls"><button class="demo-button" id="clear-selections" data-clear="selections" disabled>Clear selection</button></div><div class="chart" id="selections"></div><div class="status" id="status-selections">Loading…</div><div class="readout" id="selection-selections">Select a region to inspect canonical Python values.</div></section>
<section class="tab" id="tab-linked" hidden><p class="intro">Pan or zoom either chart: the X range follows in both charts. Each Y scale stays independent. Drag along an axis band to navigate just that axis; double-click to reset.</p><div class="linked"><div class="chart" id="linked-a"></div><div class="chart" id="linked-b"></div></div><div class="status" id="status-linked">Loading…</div></section>
<section class="tab" id="tab-large" hidden><p class="intro">Density summarizes the full dataset. Choose Box Zoom or use the wheel to drill into individual samples; Select becomes available when individual points are shown. Selections query the original Python data. Use Clear selection below to remove the selection.</p><div class="controls"><button class="demo-button" id="clear-large" data-clear="large" disabled>Clear selection</button></div><div class="chart" id="large"></div><div class="status" id="status-large">Loading…</div><div class="readout" id="selection-large">Select a region to inspect canonical Python values.</div></section>
<section class="tab" id="tab-streaming" hidden><p class="intro">Start appends 100 samples every 100 ms without reloading the chart. Pause to inspect it. Streaming pauses when you leave this tab or reach 20,000 retained samples; Reset starts a fresh, paused chart.</p><div class="controls"><button class="demo-button" id="start" disabled>Start</button><button class="demo-button" id="pause" disabled>Pause</button><button class="demo-button" id="reset" disabled>Reset</button><span id="stream-count" aria-live="polite">Loading…</span></div><div class="chart" id="stream"></div><div class="status" id="status-streaming">Loading…</div></section>
</main><script type="module">
import {render} from './xy-widget.js';
const tabCharts = {signals:['signals'],selections:['selections'],linked:['linked-a','linked-b'],large:['large'],streaming:['stream']};
const chartTab = Object.fromEntries(Object.entries(tabCharts).flatMap(([tab,ids])=>ids.map(id=>[id,tab])));
const generations = {}, models = new Map(), cleanups = new Map();
let bridge, activeTab='signals';
const diagnostic = {ready:{}, errors:[], messages:{}, replies:{}, selections:{}, views:{}, stream:null, mounts:{}, appends:0};
const status = (tab,text)=>document.getElementById('status-'+tab).textContent=text;
function fail(error){const text=String(error?.stack||error);diagnostic.errors.push(text);document.getElementById('global-error').textContent=text;bridge?.diagnostic(JSON.stringify({kind:'error',message:text}));}
window.addEventListener('error',e=>fail(e.error||e.message));
window.addEventListener('unhandledrejection',e=>fail(e.reason));
const send = value=>bridge.post(JSON.stringify(value));
function decode(buffers){return buffers.map(s=>{const b=atob(s), out=new Uint8Array(b.length);for(let i=0;i<b.length;i++)out[i]=b.charCodeAt(i);return new DataView(out.buffer);});}
class Model {
  constructor(id,event){this.id=id;this.generation=event.generation;this.values={spec:event.spec,buffers:decode(event.buffers)};this.listeners=new Map();}
  get(name){return this.values[name];}
  on(name,fn){if(!this.listeners.has(name))this.listeners.set(name,new Set());this.listeners.get(name).add(fn);}
  off(name,fn){this.listeners.get(name)?.delete(fn);}
  emit(name,...args){for(const fn of [...(this.listeners.get(name)||[])])fn(...args);}
  send(message){diagnostic.messages[message.type]=(diagnostic.messages[message.type]||0)+1;send({kind:'message',chart:this.id,generation:this.generation,message});}
  update(event){this.values={spec:event.spec,buffers:decode(event.buffers)};this.emit('change:spec');this.emit('change:buffers');}
}
function root(id){return document.getElementById(id).querySelector('.xy-chart-root');}
function describeControls(id){
  const chart=root(id),canvas=chart.querySelector('[data-xy-slot="canvas"]');
  const selection=chart.querySelector('[data-xy-modebar-select-trigger]');
  const hint=document.createElement('div');hint.className='mode-hint';hint.setAttribute('role','status');
  const label=document.createElement('strong'),help=document.createElement('span');hint.append(label,help);
  chart.before(hint);
  const descriptions={
    pan:['Pan','Drag to move the view. Click Pan again to pause navigation.'],
    zoom:['Box zoom','Drag a rectangle to zoom; choose Pan to move the view.'],
    select:['Box select','Drag a rectangle to select rows. Double-click to clear.'],
    'select-lasso':['Lasso select','Draw around points to select rows. Double-click to clear.'],
    'select-x':['X range','Drag horizontally to select rows.'],
    'select-y':['Y range','Drag vertically to select rows.'],
    none:['Navigation paused','Click Pan or choose a tool to resume.'],
  };
  function sync(){
    const [name,instruction]=descriptions[canvas.dataset.xyDragmode]||['Loading','Preparing chart controls…'];
    label.textContent='Drag tool: '+name;
    help.textContent=id==='large'&&selection?.style.display==='none'
      ? instruction+' Zoom in until individual points appear to enable Select.' : instruction;
  }
  const observer=new MutationObserver(sync);
  observer.observe(canvas,{attributes:true,attributeFilter:['data-xy-dragmode']});
  if(selection)observer.observe(selection,{attributes:true,attributeFilter:['style']});
  sync();return ()=>{observer.disconnect();hint.remove();};
}
function showTab(tab){
  activeTab=tab;
  document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-selected',String(b.dataset.tab===tab)));
  document.querySelectorAll('.tab').forEach(el=>el.hidden=el.id!=='tab-'+tab);
  send({kind:'activate',tab});
  if(generations[tab]===undefined){generations[tab]=0;send({kind:'initialize',tab,generation:0});}
  window.dispatchEvent(new Event('resize'));
}
function resetStream(){
  generations.streaming++;
  diagnostic.ready.stream=false;
  cleanups.get('stream')?.();cleanups.delete('stream');models.delete('stream');
  document.getElementById('stream').replaceChildren();
  ['start','pause','reset'].forEach(id=>document.getElementById(id).disabled=true);
  status('streaming','Resetting…');
  send({kind:'initialize',tab:'streaming',generation:generations.streaming});
}
function streamControl(action){send({kind:'stream',action,generation:generations.streaming});}
function clearSelection(id){return root(id)?.xy?.applyState({selection:null},{animate:false});}
async function auditControls(){
  // Rendered geometry and native tool changes: catches host CSS leaking into
  // XY's layered styles, which data-only tests cannot detect.
  const chart=root('selections'),canvas=chart.querySelector('[data-xy-slot="canvas"]');
  const find=selector=>{const el=chart.querySelector(selector);if(!el)throw Error('Missing control: '+selector);return el;};
  const settle=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
  const check=(condition,message)=>{if(!condition)throw Error(message);};
  const pan=find('[data-xy-modebar-action="pan"]');
  async function mode(expected){
    await settle();check(canvas.dataset.xyDragmode===expected,'Wrong drag tool: '+canvas.dataset.xyDragmode+'; expected '+expected);
    check(chart.parentElement.querySelector('.mode-hint strong').textContent!=='Drag tool: Loading','Missing drag tool readout');
    check(pan.getAttribute('aria-pressed')===String(expected==='pan'),'Pan active state disagrees with drag tool');
  }
  async function menu(triggerSelector,menuSelector){
    find(triggerSelector).click();await settle();
    const menu=find(menuSelector),box=menu.getBoundingClientRect();
    check(box.width>0&&box.height>0,'Dropdown did not open');
    const rects=[];
    for(const button of menu.querySelectorAll('button')){
      const rect=button.getBoundingClientRect();if(!rect.width||!rect.height)continue;
      check(rect.top>=box.top&&rect.bottom<=box.bottom+1,'Menu button extends outside dropdown');
      for(const other of rects)check(Math.min(rect.right,other.right)-Math.max(rect.left,other.left)<=1||
        Math.min(rect.bottom,other.bottom)-Math.max(rect.top,other.top)<=1,'Dropdown button rectangles overlap');
      rects.push(rect);
      const label=button.querySelector('[data-xy-slot="modebar_menu_label"]');
      if(label){const range=document.createRange();range.selectNodeContents(label);const text=range.getBoundingClientRect();
        check(text.top>=rect.top-1&&text.bottom<=rect.bottom+1&&text.right<=rect.right+1,'Dropdown label overflows its button');}
      check(button.contains(document.elementFromPoint(rect.left+rect.width/2,rect.top+rect.height/2)),
        'Dropdown button is covered at its center');
    }
    check(rects.length>1,'Dropdown has no usable commands');
  }
  try{
    if(canvas.dataset.xyDragmode!=='pan')pan.click();await mode('pan');
    pan.click();await mode('none');pan.click();await mode('pan');
    await menu('[data-xy-modebar-menu-trigger]','[role="menu"][aria-label="Zoom controls"]');
    find('[data-xy-modebar-menu-item="zoom"]').click();await mode('zoom');
    await menu('[data-xy-modebar-select-trigger]','[data-xy-modebar-select-menu]');
    find('[data-xy-modebar-select-item="select"]').click();await mode('select');
    pan.click();await mode('pan');
    await menu('[data-xy-modebar-select-trigger]','[data-xy-modebar-select-menu]');
    find('[data-xy-modebar-select-item="select-lasso"]').click();await mode('select-lasso');
    await menu('[data-xy-modebar-export-trigger]','[data-xy-modebar-export-menu]');
    find('[data-xy-modebar-export-trigger]').click();await mode('select-lasso');
    pan.click();await mode('pan');
    diagnostic.controls={ok:true};
  }catch(error){diagnostic.controls={ok:false,message:String(error)};}
}
function receive(event){
  const tab=chartTab[event.chart];
  if(event.kind==='error'){fail(event.message);return;}
  if(generations[tab]!==event.generation)return;
  if(event.kind==='mount'){
    cleanups.get(event.chart)?.();
    const el=document.getElementById(event.chart);el.replaceChildren();
    const model=new Model(event.chart,event);models.set(event.chart,model);
    const destroy=render({model,el}),stopDescribing=describeControls(event.chart);
    cleanups.set(event.chart,()=>{stopDescribing();destroy?.();});
    diagnostic.mounts[event.chart]=(diagnostic.mounts[event.chart]||0)+1;
    requestAnimationFrame(()=>requestAnimationFrame(()=>{
      if(generations[tab]!==event.generation)return;
      const canvas=el.querySelector('canvas');
      if(!root(event.chart)?.xy || !canvas || !canvas.width || !canvas.height){fail('Chart did not initialize: '+event.chart);return;}
      diagnostic.ready[event.chart]=true;status(tab,'Ready · hover for exact Python values.');
      const clear=document.getElementById('clear-'+event.chart);if(clear)clear.disabled=false;
      bridge.diagnostic(JSON.stringify({kind:'ready',chart:event.chart,generation:event.generation}));
    }));
  }else if(event.kind==='reply'){
    diagnostic.replies[event.message.type]=(diagnostic.replies[event.message.type]||0)+1;
    models.get(event.chart)?.emit('msg:custom',event.message,decode(event.buffers));
  }else if(event.kind==='update'){
    models.get(event.chart)?.update(event);diagnostic.appends++;
  }else if(event.kind==='stream'){
    diagnostic.stream=event;
    document.getElementById('stream-count').textContent=`${event.count.toLocaleString()} / ${event.limit.toLocaleString()} samples · ${event.running?'running':event.count>=event.limit?'limit reached':'paused'}`;
    document.getElementById('start').disabled=event.running||event.count>=event.limit;
    document.getElementById('pause').disabled=!event.running;
    document.getElementById('reset').disabled=false;
  }else if(event.kind==='selection'){
    diagnostic.selections[event.chart]=event.value;
    const target=document.getElementById('selection-'+event.chart);
    if(target){
      target.replaceChildren();const heading=document.createElement('strong');heading.textContent=`${event.value.count.toLocaleString()} rows selected in Python`;target.append(heading);
      for(const t of event.value.traces){const p=document.createElement('p');p.textContent=`Trace ${t.trace}: mean X ${t.x_mean.toFixed(5)}, mean Y ${t.y_mean.toFixed(5)}, Y range ${t.y_min.toFixed(5)} … ${t.y_max.toFixed(5)}`;target.append(p);}
      const preview=document.createElement('pre');preview.textContent=event.value.rows.length?JSON.stringify(event.value.rows,null,2):'No rows selected.';target.append(preview);
    }
    status(tab,`${event.value.count.toLocaleString()} canonical rows selected.`);
  }else if(event.kind==='hover'){
    status(tab,'Python hover · '+JSON.stringify(event.value));
  }else if(event.kind==='view'){
    diagnostic.views[event.chart]=event.value;
    status(tab,'View · '+Object.entries(event.value.ranges).map(([axis,r])=>`${axis}: ${r.map(x=>Number(x).toFixed(3)).join(' … ')}`).join(' | '));
  }
}
new QWebChannel(qt.webChannelTransport,channel=>{
  bridge=channel.objects.bridge;bridge.outbound.connect(raw=>{try{receive(JSON.parse(raw));}catch(e){fail(e);}});
  document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));
  document.getElementById('start').addEventListener('click',()=>streamControl('start'));
  document.getElementById('pause').addEventListener('click',()=>streamControl('pause'));
  document.getElementById('reset').addEventListener('click',resetStream);
  document.querySelectorAll('[data-clear]').forEach(button=>button.addEventListener('click',()=>clearSelection(button.dataset.clear)));
  // Small, explicit diagnostic surface for smoke checks and interactive inspection.
  window.showcase={diagnostic,showTab,resetStream,streamControl,clearSelection,auditControls,state:id=>root(id)?.xy?.state(),
    applyState:(id,patch)=>root(id)?.xy?.applyState(patch,{animate:false}),
    model:id=>models.get(id)};
  showTab('signals');
});
window.addEventListener('pagehide',()=>{for(const cleanup of cleanups.values())cleanup?.();});
</script></body></html>'''


def run_desktop(points: int, smoke_test: bool) -> int:
    from PyQt6.QtCore import QObject, QThread, QTimer, QUrl, pyqtSignal, pyqtSlot
    from PyQt6.QtWidgets import QApplication, QMainWindow
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtWebEngineCore import QWebEnginePage
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from xy import widget

    class Worker(QObject):
        outbound = pyqtSignal(str)

        def __init__(self):
            super().__init__()
            self.state = None
            self.timer = None

        @pyqtSlot()
        def start(self):
            self.state = ShowcaseState(points)
            self.timer = QTimer(self)
            self.timer.setInterval(STREAM_INTERVAL_MS)
            self.timer.timeout.connect(self.tick)

        def emit_events(self, events):
            for event in events:
                self.outbound.emit(json.dumps(event, allow_nan=False))

        @pyqtSlot(str)
        def receive(self, raw):
            try:
                request = json.loads(raw)
                kind = request["kind"]
                if kind == "initialize":
                    events = self.state.initialize(request["tab"], request["generation"])
                elif kind == "activate":
                    events = self.state.activate(request["tab"])
                elif kind == "message":
                    events = self.state.message(request["chart"], request["generation"], request["message"])
                elif kind == "stream":
                    events = self.state.control_stream(request["action"], request["generation"])
                else:
                    raise ValueError(f"Unknown showcase command: {kind}")
                self.emit_events(events)
                if self.state.running and not self.timer.isActive():
                    self.timer.start()
                elif not self.state.running:
                    self.timer.stop()
            except Exception as error:
                self.fail(error)

        @pyqtSlot()
        def tick(self):
            try:
                self.emit_events(self.state.tick())
                if not self.state.running:
                    self.timer.stop()
            except Exception as error:
                self.fail(error)

        def fail(self, error):
            if self.timer:
                self.timer.stop()
            if self.state:
                self.state.running = False
            self.outbound.emit(json.dumps({"kind": "error", "message": f"Python: {type(error).__name__}: {error}"}))

        @pyqtSlot()
        def stop(self):
            if self.timer:
                self.timer.stop()
            self.state = None
            QThread.currentThread().quit()

    class Bridge(QObject):
        outbound = pyqtSignal(str)
        command = pyqtSignal(str)
        reported = pyqtSignal(str)

        @pyqtSlot(str)
        def post(self, raw):
            self.command.emit(raw)

        @pyqtSlot(str)
        def diagnostic(self, raw):
            self.reported.emit(raw)

    class Page(QWebEnginePage):
        def javaScriptConsoleMessage(self, level, message, line, source):
            if level == self.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                print(f"JavaScript error ({line}): {message}", file=sys.stderr, flush=True)
                failures.append(message)

    class Window(QMainWindow):
        shutdown = pyqtSignal()

        def closeEvent(self, event):
            poll.stop()
            deadline.stop()
            self.shutdown.emit()
            # Worker drains prior commands before deleting figures in its own thread.
            thread.wait()
            super().closeEvent(event)

    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("XY interactive showcase")
    failures: list[str] = []
    result = {"code": 1 if smoke_test else 0}
    with tempfile.TemporaryDirectory(prefix="xy-showcase-") as temporary:
        assets = Path(temporary)
        # Exact asset copy: never regenerate or alter the library's bundled client.
        shutil.copyfile(Path(widget.__file__).parent / "static" / "index.js", assets / "xy-widget.js")
        (assets / "index.html").write_text(HTML, encoding="utf-8")
        window = Window()
        window.setWindowTitle("XY · interactive desktop showcase")
        window.resize(1260, 900)
        view = QWebEngineView(window)
        page = Page(view)
        view.setPage(page)
        window.setCentralWidget(view)
        bridge = Bridge(window)
        channel = QWebChannel(page)
        channel.registerObject("bridge", bridge)
        page.setWebChannel(channel)
        thread = QThread(window)
        worker = Worker()
        worker.moveToThread(thread)
        thread.started.connect(worker.start)
        bridge.command.connect(worker.receive)
        worker.outbound.connect(bridge.outbound)
        window.shutdown.connect(worker.stop)
        thread.finished.connect(worker.deleteLater)
        poll = QTimer(window)
        deadline = QTimer(window)
        deadline.setSingleShot(True)

        def finish(ok, detail):
            poll.stop()
            deadline.stop()
            result["code"] = 0 if ok else 1
            print(("PASS: " if ok else "FAIL: ") + detail, flush=True)
            window.close()

        def report(raw):
            event = json.loads(raw)
            if event["kind"] == "error":
                failures.append(event["message"])
                print(event["message"], file=sys.stderr, flush=True)
                if smoke_test:
                    finish(False, "browser reported an error")

        bridge.reported.connect(report)
        view.loadFinished.connect(lambda ok: None if ok else failures.append("Local page failed to load"))
        smoke = {"stage": 0, "busy": False}
        tabs = list(TAB_CHARTS)

        def inspect(snapshot):
            smoke["busy"] = False
            if failures:
                finish(False, failures[0])
                return
            if not isinstance(snapshot, dict):
                return
            stage = smoke["stage"]
            if stage < len(tabs):
                tab = tabs[stage]
                if all(snapshot["ready"].get(chart) for chart in TAB_CHARTS[tab]):
                    print(f"Ready: {tab}", flush=True)
                    smoke["stage"] += 1
                    if smoke["stage"] < len(tabs):
                        page.runJavaScript(f"showcase.showTab({json.dumps(tabs[smoke['stage']])})")
                    else:
                        page.runJavaScript("showcase.streamControl('start')")
            elif stage == 5 and snapshot.get("appends", 0) >= 3:
                page.runJavaScript("showcase.showTab('signals')")
                smoke["stage"] = 6
            elif stage == 6 and snapshot.get("stream", {}).get("running") is False:
                page.runJavaScript("showcase.showTab('streaming');showcase.resetStream()")
                smoke["stage"] = 7
            elif stage == 7:
                stream = snapshot.get("stream") or {}
                if stream.get("generation") == 1 and snapshot["ready"].get("stream"):
                    valid = stream.get("count") == STREAM_BLOCK and not stream.get("running")
                    if not valid:
                        finish(False, "stream reset did not restore a paused 100-sample chart")
                        return
                    page.runJavaScript("showcase.showTab('selections');showcase.applyState('selections',"
                                       "{selection:{polygon:[[-1,-1],[1,-1],[0,2]]}})")
                    smoke["stage"] = 8
            elif stage == 8:
                selected = snapshot.get("selections", {}).get("selections", {})
                if selected.get("count", 0) > 0 and snapshot["messages"].get("select_polygon", 0):
                    print(f"Python polygon selection: {selected['count']} rows", flush=True)
                    page.runJavaScript("document.getElementById('clear-selections').click()")
                    smoke["stage"] = 9
            elif stage == 9:
                selected = snapshot.get("selections", {}).get("selections", {})
                if selected.get("count") == 0 and snapshot["messages"].get("select_clear", 0):
                    valid = selected.get("rows") == [] and selected.get("traces") == []
                    if not valid:
                        finish(False, "cleared selection retained rows or statistics")
                        return
                    page.runJavaScript("showcase.auditControls()")
                    smoke["stage"] = 10
            elif stage == 10 and snapshot.get("controls"):
                controls = snapshot["controls"]
                finish(controls["ok"], controls.get("message", "six charts; streaming, selection/clear, tool transitions and expanded menu geometry checked"))

        def poll_smoke():
            if not smoke["busy"]:
                smoke["busy"] = True
                page.runJavaScript("window.showcase ? JSON.parse(JSON.stringify(showcase.diagnostic)) : null", inspect)

        poll.timeout.connect(poll_smoke)
        deadline.timeout.connect(lambda: finish(False, "45-second smoke timeout; " + "; ".join(failures)))
        thread.start()
        view.load(QUrl.fromLocalFile(str(assets / "index.html")))
        window.show()
        if smoke_test:
            poll.start(150)
            deadline.start(45_000)
        app.exec()
        # Destroy the local-file page before TemporaryDirectory removes its assets.
        view.setPage(QWebEnginePage(view))
        page.deleteLater()
        app.processEvents()
    return result["code"]


def positive_points(value: str) -> int:
    points = int(value)
    if points < 1:
        raise argparse.ArgumentTypeError("--points must be a positive integer")
    return points


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--points", type=positive_points, default=DEFAULT_POINTS,
                        help="sample count for the density tab (default: 1,000,000)")
    parser.add_argument("--smoke-test", action="store_true", help="open all tabs and check live updates; exit within 45 seconds")
    args = parser.parse_args(argv)
    try:
        load_dependencies()
        return run_desktop(args.points, args.smoke_test)
    except (ImportError, OSError, RuntimeError) as error:
        print(f"Cannot start XY showcase: {error}\nUse the repository venv with xy==0.0.6, numpy, PyQt6 and PyQt6-WebEngine installed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
