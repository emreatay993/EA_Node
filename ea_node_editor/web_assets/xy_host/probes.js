// Purpose: Own pinned cursor gestures, clipped overlays and visible-window queries.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_probe_qml.py
import {createProbeScheduler} from './probe_scheduler.js';
import {createProbeReadouts} from './probe_readouts.js';
import {parseProbePosition} from './probe_coordinates.js';

const SVG = 'http://www.w3.org/2000/svg';
const AXES = ['x', 'y'];
const COLORS = {x: '#2563eb', y: '#b77916'};

export function createProbes({root, controls, metadata, initial, send, openPanel, onChange, temporaryPan}) {
  const lifetime = new AbortController(), {signal} = lifetime;
  const positions = {...initial.positions};
  const hidden = new Set(), subscribers = new Set();
  let active = initial.active, method = initial.method, explicitMethod = Boolean(method);
  let placement = null, drag = null, preview = null, rows = [], page = 0, total = 0;
  let started = false, disposed = false, rangeSignature = '', handles = [];
  let swallowClick = false, lastClickWasProbe = false;
  const originalCursor = controls.canvas.style.cursor;
  const colors = new Map(metadata.signals.map(item => [item.id, item.color]));
  const overlay = document.createElementNS(SVG, 'svg');
  overlay.classList.add('probe-overlay'); overlay.setAttribute('aria-hidden', 'true');
  root.append(overlay);

  function hasLines() {return metadata.marks.some(mark => mark.kind === 'line' && !hidden.has(mark.id));}
  if (!method) method = hasLines() ? 'intersections' : 'nearest';
  function effective() {
    const value = {...positions};
    const operation = drag || placement;
    if (operation && preview !== null) value[operation.axis] = preview;
    return value;
  }
  function uiState() {
    const values = effective();
    return {positions: values, active, method, hasPosition: values[active] !== null,
      count: AXES.filter(axis => positions[axis] !== null).length,
      mode: drag ? `Move ${drag.axis.toUpperCase()} probe` : placement ? `Place ${placement.axis.toUpperCase()} probe` : '',
      busy: Boolean(drag || placement), hasLines: hasLines()};
  }
  function announce() {
    const state = uiState();
    panel.update(state); onChange(state);
    for (const callback of subscribers) callback(state);
  }
  function node(name, attributes) {
    const element = document.createElementNS(SVG, name);
    for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, String(value));
    overlay.append(element); return element;
  }
  function redraw() {
    if (disposed) return;
    const geometry = controls.geometry(), values = effective();
    overlay.style.left = geometry.offsetX + 'px'; overlay.style.top = geometry.offsetY + 'px';
    overlay.style.width = geometry.width + 'px'; overlay.style.height = geometry.height + 'px';
    overlay.setAttribute('viewBox', `0 0 ${geometry.width} ${geometry.height}`);
    overlay.replaceChildren(); handles = [];
    root.classList.toggle('xy-probing', Boolean(placement || drag));
    if (!geometry.width || !geometry.height) return;
    for (const row of rows) {
      const point = controls.project(row.x, row.y), color = colors.get(row.signal) || '#475569';
      if (row.kind === 'overlap') {
        const end = controls.project(row.x_end, row.y_end);
        node('line', {x1: point.x, y1: point.y, x2: end.x, y2: end.y, stroke: color, 'stroke-width': 5, opacity: .55});
      } else {
        if (row.kind === 'nearest' && values[active] !== null) {
          const anchor = active === 'x' ? controls.project(values.x, row.y) : controls.project(row.x, values.y);
          node('line', {x1: anchor.x, y1: anchor.y, x2: point.x, y2: point.y,
            stroke: color, 'stroke-dasharray': '2 3', opacity: .5});
        }
        node('circle', {cx: point.x, cy: point.y, r: 4, fill: '#fff', stroke: color, 'stroke-width': 2});
      }
    }
    // Paint the active handle last so corner hit-testing has a stable priority.
    for (const axis of AXES.filter(axis => axis !== active).concat(active)) {
      const value = values[axis], bounds = geometry.ranges[axis];
      if (value === null || value < bounds[0] || value > bounds[1]) continue;
      const point = controls.project(axis === 'x' ? value : geometry.ranges.x[0], axis === 'y' ? value : geometry.ranges.y[0]);
      const coordinate = axis === 'x' ? point.x : point.y;
      if (!Number.isFinite(coordinate)) continue;
      node('line', {x1: axis === 'x' ? coordinate : 0, y1: axis === 'y' ? coordinate : 0,
        x2: axis === 'x' ? coordinate : geometry.width, y2: axis === 'y' ? coordinate : geometry.height,
        stroke: COLORS[axis], 'stroke-width': axis === active ? 1.75 : 1.25,
        'stroke-dasharray': axis === 'y' ? '6 4' : '', opacity: placement?.axis === axis ? .6 : 1});
      const x = axis === 'x' ? Math.max(0, Math.min(geometry.width - 32, coordinate - 16)) : geometry.width - 32;
      const y = axis === 'y' ? Math.max(0, Math.min(geometry.height - 22, coordinate - 11)) : 2;
      node('rect', {x, y, width: 32, height: 22, rx: 5, fill: '#fff', stroke: COLORS[axis], 'stroke-width': 1.5, 'data-probe-handle': axis});
      const text = node('text', {x: x + 16, y: y + 15, fill: COLORS[axis], 'text-anchor': 'middle', 'font-size': 12, 'font-weight': 600});
      text.textContent = axis.toUpperCase();
      handles.push({axis, x, y, width: 32, height: 22});
    }
  }

  const scheduler = createProbeScheduler({send,
    pending: hasQuery => {rows = []; redraw(); if (hasQuery) panel.pending();},
    result: value => {
      total = value.total;
      if (total && page * value.page_size >= total) {
        page = Math.floor((total - 1) / value.page_size); invalidate(true, false); return;
      }
      rows = value.rows; panel.result(value); redraw();
    },
    error: message => {rows = []; panel.error(message); redraw();},
  });

  function invalidate(immediate = false, resetPage = true) {
    if (disposed) return;
    if (resetPage) {page = 0; total = 0;}
    announce(); redraw();
    if (!started) return;
    const position = effective()[active];
    const ranges = controls.geometry().ranges;
    scheduler.update(position === null ? null : {axis: active, position, method,
      ranges: {x: [...ranges.x], y: [...ranges.y]}, page}, immediate);
  }

  function cancel(restoreTool = true) {
    if (disposed) return false;
    if (!placement && !drag) return panel.cancelEdit();
    const saved = placement;
    const captured = drag;
    placement = null; drag = null; preview = null;
    if (captured && controls.canvas.hasPointerCapture(captured.pointerId)) controls.canvas.releasePointerCapture(captured.pointerId);
    if (saved) {
      active = saved.previousActive;
      if (restoreTool) controls.setTool(saved.previousMode);
    }
    controls.canvas.style.cursor = originalCursor;
    invalidate(true);
    return true;
  }

  function place(axis) {
    if (!AXES.includes(axis)) return;
    cancel();
    placement = {axis, previousMode: controls.state().mode, previousActive: active};
    active = axis; preview = null; explicitMethod = true;
    controls.setTool('none'); controls.canvas.style.cursor = 'crosshair';
    openPanel(); invalidate(true); controls.canvas.focus();
  }

  function setPosition(text) {
    const axis = active;
    let value;
    try {value = parseProbePosition(text, axis, metadata);}
    catch (error) {panel.inputError(error.message); return;}
    if (!placement && !drag && positions[axis] === value) {panel.committed(); return;}
    cancel(); active = axis; positions[axis] = value; explicitMethod = true;
    invalidate(true); panel.committed();
  }
  function setMethod(value) {
    if (!['intersections', 'nearest'].includes(value)) return;
    cancel(); method = value; explicitMethod = true; invalidate(true);
  }
  function remove(axis = active) {
    cancel(); active = axis; positions[axis] = null; invalidate(true);
  }
  function clear() {cancel(); positions.x = positions.y = null; invalidate(true);}
  const panel = createProbeReadouts(metadata, {
    active: axis => {cancel(); active = axis; invalidate(true);},
    position: setPosition, method: setMethod, remove,
    page: delta => {page = Math.max(0, Math.min(Math.max(0, Math.ceil(total / 50) - 1), page + delta)); invalidate(true, false);},
  });

  function hit(event) {
    const view = controls.geometry(), x = event.clientX - view.left, y = event.clientY - view.top;
    return [...handles].reverse().find(box => x >= box.x - 3 && x <= box.x + box.width + 3 && y >= box.y - 3 && y <= box.y + box.height + 3);
  }
  function move(event) {
    const point = controls.dataAt(event.clientX, event.clientY);
    if (!point) return;
    preview = point[(drag || placement).axis];
    invalidate(false);
  }
  controls.canvas.addEventListener('pointerdown', event => {
    if (event.button !== 0 || event.buttons !== 1 || temporaryPan()) return;
    const placing = Boolean(placement), axis = placement?.axis || hit(event)?.axis;
    lastClickWasProbe = false;
    if (!axis) {swallowClick = false; return;}
    event.preventDefault(); event.stopImmediatePropagation();
    active = axis; drag = {axis, pointerId: event.pointerId}; swallowClick = true;
    controls.canvas.setPointerCapture(event.pointerId);
    move(event); if (placing) openPanel();
  }, {capture: true, signal});
  window.addEventListener('pointermove', event => {
    if (disposed || temporaryPan()) return;
    if (drag && event.pointerId === drag.pointerId) {
      event.preventDefault(); event.stopImmediatePropagation(); move(event);
    } else if (placement && event.target === controls.canvas) {
      event.stopImmediatePropagation(); move(event);
    } else if (!placement && !drag) {
      const axis = event.target === controls.canvas ? hit(event)?.axis : null;
      controls.canvas.style.cursor = axis ? (axis === 'x' ? 'ew-resize' : 'ns-resize') : originalCursor;
    }
  }, {capture: true, signal});
  window.addEventListener('pointerup', event => {
    if (!drag || event.pointerId !== drag.pointerId || event.button !== 0) return;
    event.preventDefault(); event.stopImmediatePropagation();
    const axis = drag.axis, previousMode = placement?.previousMode;
    positions[axis] = preview; active = axis; explicitMethod = true;
    drag = null; placement = null; preview = null;
    if (controls.canvas.hasPointerCapture(event.pointerId)) controls.canvas.releasePointerCapture(event.pointerId);
    controls.canvas.style.cursor = originalCursor;
    if (previousMode) controls.setTool(previousMode);
    invalidate(true);
  }, {capture: true, signal});
  controls.canvas.addEventListener('click', event => {
    if (swallowClick) {event.preventDefault(); event.stopImmediatePropagation(); swallowClick = false; lastClickWasProbe = true;}
  }, {capture: true, signal});
  controls.canvas.addEventListener('dblclick', event => {
    if (lastClickWasProbe || placement || drag) {event.preventDefault(); event.stopImmediatePropagation();}
  }, {capture: true, signal});
  window.addEventListener('pointercancel', event => {if (drag?.pointerId === event.pointerId) cancel();}, {capture: true, signal});
  controls.canvas.addEventListener('lostpointercapture', event => {if (drag?.pointerId === event.pointerId) cancel();}, {signal});
  window.addEventListener('blur', () => {if (drag || placement) cancel();}, {signal});
  const resize = new ResizeObserver(redraw); resize.observe(controls.canvas);

  function dispose() {
    if (disposed) return;
    disposed = true; lifetime.abort(); resize.disconnect(); scheduler.dispose(); subscribers.clear(); panel.dispose();
    controls.canvas.style.cursor = originalCursor; root.classList.remove('xy-probing'); overlay.remove();
  }

  announce(); redraw();
  return {
    place, setMethod, clear, setPosition, cancelInteraction: cancel,
    show() {openPanel();},
    state() {return {positions: {...positions}, active, method: explicitMethod ? method : null};},
    status: uiState,
    subscribe(callback) {subscribers.add(callback); callback(uiState()); return () => subscribers.delete(callback);},
    start() {started = true; rangeSignature = JSON.stringify(controls.geometry().ranges); invalidate(true);},
    viewChanged(detail = {}) {
      redraw();
      const signature = JSON.stringify(controls.geometry().ranges);
      if (signature !== rangeSignature) {rangeSignature = signature; invalidate(detail.phase === 'end');}
      else if (detail.phase === 'end') invalidate(true);
    },
    legendChanged(message) {
      if (message.type !== 'legend_toggle' || message.category != null || typeof message.hidden !== 'boolean' || !metadata.marks.some(mark => mark.id === message.trace)) return;
      if (message.hidden) hidden.add(message.trace); else hidden.delete(message.trace);
      if (!explicitMethod) method = hasLines() ? 'intersections' : 'nearest';
      invalidate(true);
    },
    receive(value, error = false) {scheduler.receive(value, error);},
    suspendHover() {controls.canvas.style.cursor = originalCursor;},
    prepareClose() {started = false; cancel(); dispose();},
    dispose,
  };
}
