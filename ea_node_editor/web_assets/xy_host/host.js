// Purpose: Adapt XY's bundled widget to the data-only desktop channel.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py
import {render} from './xy-widget.js';
import {installMiddlePan} from './gestures.js';
let bridge, session, model, cleanup, observer, baseline, completed, home, authored;
let initializing=true, closing=false, gesture=false, restoringGesture=false, escapeForwarding=false, middlePan;
const changed=new Set(), automatic=new Set();
const fitIntents=new Map();
const chart=()=>document.querySelector('.corex-xy-chart');
const clone=value=>JSON.parse(JSON.stringify(value));
const frames=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
const send=value=>bridge.post(JSON.stringify({session,...value}));
function fail(error){
  const message=String(error?.stack||error);document.getElementById('error').textContent=message;
  bridge?.host_failed(message);
}
window.addEventListener('error',event=>fail(event.error||event.message));
window.addEventListener('unhandledrejection',event=>fail(event.reason));
function decode(buffers){return buffers.map(text=>{const bytes=atob(text),data=new Uint8Array(bytes.length);for(let i=0;i<bytes.length;i++)data[i]=bytes.charCodeAt(i);return new DataView(data.buffer);});}
class Model{
  constructor(event){this.values={spec:event.spec,buffers:decode(event.buffers)};this.listeners=new Map();}
  get(key){return this.values[key];}
  on(key,fn){if(!this.listeners.has(key))this.listeners.set(key,new Set());this.listeners.get(key).add(fn);}
  off(key,fn){this.listeners.get(key)?.delete(fn);}
  emit(key,...args){for(const fn of [...(this.listeners.get(key)||[])])fn(...args);}
  send(message){send({kind:'message',message});}
}
function describeMode(){
  const canvas=chart()?.querySelector('[data-xy-slot="canvas"]');
  const names={pan:'Pan — drag to move; click Pan again to pause.',zoom:'Box zoom — drag a rectangle.',select:'Box select — drag to select samples.',
    'select-lasso':'Lasso select — draw around samples.','select-x':'X range selection.','select-y':'Y range selection.',none:'Navigation paused — choose a tool to continue.'};
  let text=middlePan?.active?'Temporary pan — release the middle button to resume your tool.':names[canvas?.dataset.xyDragmode]||'Preparing chart…';
  if(!middlePan?.active)text+=' Hold the middle button and drag to pan temporarily.';
  const selection=chart()?.querySelector('[data-xy-modebar-select-trigger]');
  if(selection?.style.display==='none')text+=' Selection is available when individual marker samples are visible.';
  document.getElementById('mode').textContent=text;
}
const number=value=>typeof value==='number'?Number(value.toPrecision(10)).toLocaleString('en-US',{maximumSignificantDigits:10}):String(value);
function selectionReadout(value){
  const target=document.getElementById('selection');target.replaceChildren();
  const title=document.createElement('strong');title.textContent=`${value.count.toLocaleString()} samples selected`;target.append(title);
  for(const signal of value.signals){
    const summary=document.createElement('p');
    summary.textContent=`${signal.label}: ${signal.count.toLocaleString()} samples · Mean Y ${number(signal.y_mean)} · Y range ${number(signal.y_min)} to ${number(signal.y_max)}`;
    target.append(summary);
  }
  if(!value.rows.length)return;
  const table=document.createElement('table'),head=table.createTHead().insertRow();
  for(const label of ['Signal','Sample','X','Y']){const cell=document.createElement('th');cell.textContent=label;head.append(cell);}
  const body=table.createTBody();
  for(const row of value.rows){
    const cells=body.insertRow();
    for(const value of [row.label,row.index+1,row.x,row.y]){const cell=cells.insertCell();cell.textContent=number(value);cell.title=String(value);}
  }
  target.append(table);
}
function snapshot(){return clone(chart().xy.state());}
function finishGesture(detail){
  if(initializing||closing||restoringGesture||detail.phase!=='end')return;
  completed=snapshot();
  for(const axis of detail.axes?.length?detail.axes:['x','y']){
    if(!['x','y'].includes(axis))continue;
    // The native API emits its view event on a later frame. Keep the explicit
    // fit intent, including zero-delta fits, until a different gesture occurs.
    if(detail.source==='api'&&JSON.stringify(fitIntents.get(axis))===JSON.stringify(completed.ranges[axis]))continue;
    fitIntents.delete(axis);
    if(detail.source==='reset'){changed.add(axis);automatic.add(axis);}
    else if(JSON.stringify(completed.ranges[axis])!==JSON.stringify(baseline.ranges[axis])){changed.add(axis);automatic.delete(axis);}
    else{changed.delete(axis);automatic.delete(axis);}
  }
}
function resetIntent(){
  if(initializing||closing||!home)return;
  fitIntents.clear();
  for(const axis of ['x','y']){changed.add(axis);automatic.add(axis);}
  completed=clone(home);
  completed.selection=snapshot().selection;
}
function fitView(mode){
  if(initializing||closing||!home||!['x','y','data','limits'].includes(mode))return;
  cancelInteraction();
  const axes=['x','y'].includes(mode)?[mode]:['x','y'];
  const ranges=Object.fromEntries(axes.map(axis=>[axis,
    mode==='limits'?(authored[axis]||home.ranges[axis]):home.ranges[axis]]));
  if(!chart().xy.applyState({ranges},{animate:false}))return;
  completed=snapshot();
  for(const axis of axes){
    fitIntents.set(axis,clone(completed.ranges[axis]));
    if(mode==='limits'){changed.delete(axis);automatic.delete(axis);}
    else{changed.add(axis);automatic.add(axis);}
  }
  document.getElementById('readout').textContent={
    x:'X fitted to all data; Y is unchanged.',y:'Y fitted to all data; X is unchanged.',
    data:'Both axes fitted to all data.',limits:'Signal Plot limits restored; automatic axes show all data.',
  }[mode];
}
function cancelInteraction(){
  const root=chart();if(!root)return false;
  const previous=escapeForwarding;escapeForwarding=true;
  try{
    if(middlePan?.cancel()){gesture=false;return true;}
    const menu=[...root.querySelectorAll('[role="menu"]')].find(element=>getComputedStyle(element).display!=='none');
    if(menu){
      const trigger=root.querySelector('[aria-expanded="true"]');
      if(trigger)trigger.click();else menu.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}));
      return true;
    }
    if(gesture){
      root.querySelector('[data-xy-slot="canvas"]').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));
      gesture=false;return true;
    }
    return false;
  }finally{escapeForwarding=previous;}
}
async function requestClose(){
  if(closing)return;
  if(gesture)cancelInteraction();
  await frames(); // XY completes gesture events on the next animation frame.
  const state=completed||baseline;
  if(!state){send({kind:'flush',state:{},changed_axes:[],automatic:[]});return;}
  if(!gesture&&chart())state.selection=snapshot().selection;
  closing=true;
  send({kind:'flush',state,changed_axes:[...changed],automatic:[...automatic]});
}
async function receive(event, initial){
  if(event.session!==session)return;
  if(event.kind==='mount'){
    model=new Model(event);cleanup=render({model,el:document.getElementById('chart')});
    await frames();
    const root=chart();if(!root?.xy)throw Error('XY renderer did not initialize.');
    home=snapshot();
    root.addEventListener('xy:view_change',event=>finishGesture(event.detail));
    root.addEventListener('click',event=>{
      if(event.target.closest('[data-xy-modebar-menu-item="reset"], [data-xy-modebar-menu-item="fit"]'))resetIntent();
    },true);
    const canvas=root.querySelector('[data-xy-slot="canvas"]');
    canvas.addEventListener('dblclick',()=>{
      if(['pan','zoom'].includes(canvas.dataset.xyDragmode))resetIntent();
    },true);
    middlePan=installMiddlePan(root,{onModeChange:describeMode,onCancel:state=>{
      restoringGesture=true;gesture=false;
      root.xy.applyState(state,{animate:false,history:false});
      frames().then(()=>{restoringGesture=false;});
    }});
    canvas.addEventListener('pointerdown',()=>{gesture=true;});
    window.addEventListener('pointerup',()=>{gesture=false;});
    observer=new MutationObserver(describeMode);
    observer.observe(root,{subtree:true,attributes:true,attributeFilter:['data-xy-dragmode','style']});
    root.xy.applyState(initial.state,{animate:false,history:false});
    await frames();baseline=snapshot();completed=clone(baseline);initializing=false;
    document.querySelectorAll('[data-fit]').forEach(button=>{button.disabled=false;});
    canvas.focus();describeMode();window.corexXY.ready=true;
  }else if(event.kind==='reply')model?.emit('msg:custom',event.message,decode(event.buffers));
  else if(event.kind==='hover'){
    const row=event.value;
    document.getElementById('readout').textContent=`${row.label || 'Signal'} · Sample ${Number(row.index)+1} · X ${number(row.x)} · Y ${number(row.y)}`;
  }
  else if(event.kind==='selection'){
    selectionReadout(event.value);
    window.corexXY.selection=event.value;
  }
}
new QWebChannel(qt.webChannelTransport,channel=>{
  bridge=channel.objects.xyBridge;
  const initial=JSON.parse(bridge.initial_json);session=initial.session;authored=initial.authored_ranges;
  bridge.outbound.connect(raw=>{receive(JSON.parse(raw),initial).catch(fail);});
  document.getElementById('sync').textContent=initial.sync_message;
  document.getElementById('clear').addEventListener('click',()=>chart()?.xy.applyState({selection:null},{animate:false}));
  document.querySelectorAll('[data-fit]').forEach(button=>button.addEventListener('click',()=>fitView(button.dataset.fit)));
  window.corexXY={ready:false,requestClose,cancelInteraction,state:()=>chart()?.xy.state(),
    applyState:patch=>chart()?.xy.applyState(patch,{animate:false}),home:()=>home,selection:null};
  send({kind:'initialize'});
});
// Classify Escape before XY's accessibility handler consumes an idle Escape.
// Active gestures still receive a forwarded native cancellation first.
window.addEventListener('keydown',event=>{
  if(event.key!=='Escape'||escapeForwarding)return;
  event.preventDefault();event.stopImmediatePropagation();
  if(!cancelInteraction())bridge?.request_close();
},true);
window.addEventListener('pagehide',()=>{middlePan?.dispose();observer?.disconnect();cleanup?.();});
