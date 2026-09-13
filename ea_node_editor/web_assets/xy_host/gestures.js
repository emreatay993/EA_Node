// Purpose: Provide temporary middle-button panning through XY's native gesture engine.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py
// The adapter changes no axis math: forwarded pointer events use XY constraints,
// logarithmic transforms, view notifications and viewport queries.
export function installMiddlePan(root, {controls, onCancel, onModeChange}) {
  const canvas=controls.canvas;
  let active=null, forwarding=false;
  const listeners=[];
  const listen=(target,type,fn,options)=>{target.addEventListener(type,fn,options);listeners.push(()=>target.removeEventListener(type,fn,options));};
  function tool(mode){
    controls.setTool(mode);
  }
  function forward(type,event){
    forwarding=true;
    try{
      canvas.dispatchEvent(new PointerEvent(type,{bubbles:true,cancelable:true,pointerId:active.pointerId,
        pointerType:'mouse',isPrimary:true,button:0,buttons:type==='pointerup'?0:1,
        clientX:event.clientX,clientY:event.clientY,screenX:event.screenX,screenY:event.screenY}));
    }finally{forwarding=false;}
  }
  function finish(cancelled){
    if(!active)return false;
    const saved=active;
    if(cancelled){
      const previousForwarding=forwarding;forwarding=true;
      try{canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));}
      finally{forwarding=previousForwarding;}
    }else forward('pointerup',saved.last);
    active=null;
    try{if(canvas.hasPointerCapture(saved.pointerId))canvas.releasePointerCapture(saved.pointerId);}catch{}
    tool(saved.mode);
    if(cancelled)onCancel(saved.state);
    onModeChange();
    return true;
  }
  listen(canvas,'pointerdown',event=>{
    if(forwarding||event.pointerType!=='mouse'||event.button!==1)return;
    event.preventDefault();event.stopImmediatePropagation();
    // Never turn a simultaneous left/right gesture into navigation. Modifiers
    // are intentionally ignored for middle-only panning (Shift still selects
    // during ordinary left-button gestures).
    if(active||event.buttons!==4)return;
    active={pointerId:event.pointerId,mode:canvas.dataset.xyDragmode,state:root.xy.state(),last:event};
    tool('pan');
    forward('pointerdown',event);
    onModeChange();
  },true);
  listen(window,'pointermove',event=>{
    if(forwarding||!active||event.pointerId!==active.pointerId)return;
    event.preventDefault();event.stopImmediatePropagation();
    active.last=event;
    if(!(event.buttons&4)){finish(false);return;}
    forward('pointermove',event);
  },true);
  listen(window,'pointerup',event=>{
    if(forwarding||!active||event.pointerId!==active.pointerId)return;
    event.preventDefault();event.stopImmediatePropagation();
    active.last=event;
    if(event.button===1||!(event.buttons&4))finish(false);
  },true);
  listen(window,'pointerdown',event=>{
    if(forwarding||!active)return;
    event.preventDefault();event.stopImmediatePropagation();
  },true);
  listen(window,'pointercancel',event=>{if(active&&event.pointerId===active.pointerId)finish(true);},true);
  listen(window,'blur',()=>finish(true));
  listen(window,'keydown',event=>{
    if(forwarding||!active||event.key!=='Escape')return;
    event.preventDefault();event.stopImmediatePropagation();
    // Prevent the synthetic native cancellation from re-entering this handler.
    forwarding=true;try{finish(true);}finally{forwarding=false;}
  },true);
  listen(canvas,'auxclick',event=>{if(event.button===1){event.preventDefault();event.stopImmediatePropagation();}},true);
  listen(canvas,'mousedown',event=>{if(event.button===1)event.preventDefault();},true);
  return {get active(){return active!==null;},cancel:()=>{
    forwarding=true;try{return finish(true);}finally{forwarding=false;}
  },dispose:()=>{forwarding=true;try{finish(true);}finally{forwarding=false;listeners.forEach(remove=>remove());}}};
}
