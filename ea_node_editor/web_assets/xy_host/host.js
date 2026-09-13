// Purpose: Coordinate the data-only XY transport, view intent and host presentation.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py
import {render} from './xy-widget.js';
import {createXYControls} from './controls.js';
import {installMiddlePan} from './gestures.js';
import {createToolbar} from './toolbar.js';
import {createReadouts} from './readouts.js';

let bridge, session, model, cleanup, controls, toolbar, readouts, middlePan;
let baseline, completed, home, authored;
let initializing = true, closing = false, gesture = false, restoringGesture = false, escapeForwarding = false;
const changed = new Set(), automatic = new Set(), fitIntents = new Map();
const lifetime = new AbortController();
const {signal} = lifetime;
const chart = () => document.querySelector('.corex-xy-chart');
const clone = value => JSON.parse(JSON.stringify(value));
const frames = () => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
const send = value => bridge.post(JSON.stringify({session, ...value}));
const snapshot = () => clone(chart().xy.state());
const emptySelection = () => ({count: 0, signals: [], rows: []});

function fail(error) {
  const message = String(error?.stack || error);
  document.getElementById('error').textContent = message;
  bridge?.host_failed(message);
}
window.addEventListener('error', event => fail(event.error || event.message), {signal});
window.addEventListener('unhandledrejection', event => fail(event.reason), {signal});

function decode(buffers) {
  return buffers.map(text => {
    const bytes = atob(text), data = new Uint8Array(bytes.length);
    for (let i = 0; i < bytes.length; i++) data[i] = bytes.charCodeAt(i);
    return new DataView(data.buffer);
  });
}

class Model {
  constructor(event) {
    this.values = {spec: event.spec, buffers: decode(event.buffers)};
    this.listeners = new Map();
  }
  get(key) {return this.values[key];}
  on(key, fn) {
    if (!this.listeners.has(key)) this.listeners.set(key, new Set());
    this.listeners.get(key).add(fn);
  }
  off(key, fn) {this.listeners.get(key)?.delete(fn);}
  emit(key, ...args) {for (const fn of [...(this.listeners.get(key) || [])]) fn(...args);}
  send(message) {send({kind: 'message', message});}
}

function describeMode() {
  const mode = controls?.state().mode;
  const descriptions = {
    pan: ['Pan', 'Drag to move. Click Pan again to pause.'],
    zoom: ['Box zoom', 'Drag a rectangle to zoom into it.'],
    select: ['Box select', 'Drag a rectangle to select marker samples.'],
    'select-lasso': ['Lasso select', 'Draw around marker samples.'],
    'select-x': ['Select X', 'Drag to select an X range.'],
    'select-y': ['Select Y', 'Drag to select a Y range.'],
    none: ['Paused', 'Choose a navigation or selection tool.'],
  };
  const [label, hint] = middlePan?.active ? ['Temporary pan', 'Release the middle button to resume your tool.'] :
    descriptions[mode] || ['Preparing', 'Preparing the plot.'];
  readouts.setMode(label, hint + ' Wheel to zoom; hold the middle button and drag to pan temporarily.');
  if (chart()?.xy && !snapshot().selection) readouts.selection(emptySelection(), null);
}

function finishGesture(detail) {
  if (initializing || closing || restoringGesture || detail.phase !== 'end') return;
  completed = snapshot();
  for (const axis of detail.axes?.length ? detail.axes : ['x', 'y']) {
    if (!['x', 'y'].includes(axis)) continue;
    // XY emits API view changes on a later frame. Explicit fit intent also
    // applies to zero-delta fits, until a different gesture changes that axis.
    if (detail.source === 'api' && JSON.stringify(fitIntents.get(axis)) === JSON.stringify(completed.ranges[axis])) continue;
    fitIntents.delete(axis);
    if (detail.source === 'reset') {
      changed.add(axis); automatic.add(axis);
    } else if (JSON.stringify(completed.ranges[axis]) !== JSON.stringify(baseline.ranges[axis])) {
      changed.add(axis); automatic.delete(axis);
    } else {
      changed.delete(axis); automatic.delete(axis);
    }
  }
}

function resetIntent() {
  if (initializing || closing || !home) return;
  fitIntents.clear();
  for (const axis of ['x', 'y']) {changed.add(axis); automatic.add(axis);}
  completed = clone(home);
  completed.selection = snapshot().selection;
}

function fitView(mode) {
  if (initializing || closing || !home || !['x', 'y', 'data', 'limits'].includes(mode)) return;
  cancelGesture();
  const axes = ['x', 'y'].includes(mode) ? [mode] : ['x', 'y'];
  const ranges = Object.fromEntries(axes.map(axis => [axis,
    mode === 'limits' ? (authored[axis] || home.ranges[axis]) : home.ranges[axis]]));
  if (!chart().xy.applyState({ranges}, {animate: false})) return;
  completed = snapshot();
  for (const axis of axes) {
    fitIntents.set(axis, clone(completed.ranges[axis]));
    if (mode === 'limits') {changed.delete(axis); automatic.delete(axis);}
    else {changed.add(axis); automatic.add(axis);}
  }
  readouts.note({
    x: 'X fitted to all data; Y is unchanged.', y: 'Y fitted to all data; X is unchanged.',
    data: 'Both axes fitted to all data.', limits: 'Signal Plot limits restored; automatic axes show all data.',
  }[mode]);
}

function cancelGesture() {
  if (!controls) return false;
  const previous = escapeForwarding;
  escapeForwarding = true;
  try {
    if (middlePan?.cancel()) {gesture = false; return true;}
    if (gesture) {
      controls.canvas.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true, cancelable: true}));
      gesture = false;
      return true;
    }
    return false;
  } finally {escapeForwarding = previous;}
}

function cancelInteraction() {
  return cancelGesture() || toolbar?.cancelInteraction() || readouts?.cancelInteraction() || false;
}

async function requestClose() {
  if (closing) return;
  cancelGesture();
  await frames(); // Flush the last completed native gesture, never its preview.
  const state = completed || baseline;
  if (!state) {send({kind: 'flush', state: {}, changed_axes: [], automatic: []}); return;}
  if (chart()) state.selection = snapshot().selection;
  closing = true;
  send({kind: 'flush', state, changed_axes: [...changed], automatic: [...automatic]});
}

async function receive(event, initial) {
  if (event.session !== session) return;
  if (event.kind === 'mount') {
    model = new Model(event);
    cleanup = render({model, el: document.getElementById('chart')});
    await frames();
    const root = chart();
    if (!root?.xy) throw Error('XY renderer did not initialize.');
    home = snapshot();
    root.addEventListener('xy:view_change', event => finishGesture(event.detail), {signal});
    controls = createXYControls(root, {onReset: resetIntent});
    controls.canvas.addEventListener('dblclick', () => {
      if (['pan', 'zoom'].includes(controls.state().mode)) resetIntent();
    }, {capture: true, signal});
    middlePan = installMiddlePan(root, {controls, onModeChange: describeMode, onCancel: state => {
      restoringGesture = true; gesture = false;
      root.xy.applyState(state, {animate: false, history: false});
      frames().then(() => {restoringGesture = false;});
    }});
    controls.canvas.addEventListener('pointerdown', () => {gesture = true;}, {signal});
    window.addEventListener('pointerup', () => {gesture = false;}, {signal});
    controls.subscribe(describeMode);
    toolbar = createToolbar({controls, style: initial.toolbar_style, onFit: fitView,
      onStyle: value => bridge.set_toolbar_style(value), beforeAction: cancelGesture});
    root.xy.applyState(initial.state, {animate: false, history: false});
    await frames();
    baseline = snapshot(); completed = clone(baseline); initializing = false;
    controls.canvas.focus(); describeMode(); window.corexXY.ready = true;
  } else if (event.kind === 'reply') {
    model?.emit('msg:custom', event.message, decode(event.buffers));
  } else if (event.kind === 'hover') {
    readouts.hover(event.value);
  } else if (event.kind === 'selection') {
    const geometry = chart()?.xy?.state().selection;
    const value = geometry ? event.value : emptySelection();
    readouts.selection(value, geometry);
    window.corexXY.selection = value;
  } else if (event.kind === 'presentation_error') {
    readouts.note(event.message, true);
  }
}

new QWebChannel(qt.webChannelTransport, channel => {
  bridge = channel.objects.xyBridge;
  const initial = JSON.parse(bridge.initial_json);
  session = initial.session; authored = initial.authored_ranges;
  readouts = createReadouts({syncMessage: initial.sync_message, syncAxes: initial.sync_axes, onClear: () => {
    chart()?.xy.applyState({selection: null}, {animate: false});
    readouts.selection(emptySelection(), null);
    window.corexXY.selection = emptySelection();
  }});
  bridge.outbound.connect(raw => {receive(JSON.parse(raw), initial).catch(fail);});
  window.corexXY = {ready: false, requestClose, cancelInteraction, state: () => chart()?.xy.state(),
    applyState: patch => chart()?.xy.applyState(patch, {animate: false}), home: () => home, selection: null};
  send({kind: 'initialize'});
});

window.addEventListener('keydown', event => {
  if (event.key !== 'Escape' || escapeForwarding) return;
  event.preventDefault(); event.stopImmediatePropagation();
  if (!cancelInteraction()) bridge?.request_close();
}, {capture: true, signal});
window.addEventListener('pagehide', () => {
  closing = true;
  lifetime.abort(); middlePan?.dispose(); toolbar?.dispose(); controls?.dispose(); readouts?.dispose(); cleanup?.();
}, {once: true});
