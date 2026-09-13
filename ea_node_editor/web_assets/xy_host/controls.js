// Purpose: Isolate the pinned XY client's native control contract from host UI.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py

const SELECTORS = {
  pan: '[data-xy-modebar-action="pan"]',
  zoom: '[data-xy-modebar-menu-item="zoom"]',
  select: '[data-xy-modebar-select-item="select"]',
  'select-lasso': '[data-xy-modebar-select-item="select-lasso"]',
  'select-x': '[data-xy-modebar-select-item="select-x"]',
  'select-y': '[data-xy-modebar-select-item="select-y"]',
  zoomin: '[data-xy-modebar-menu-item="zoomin"]',
  zoomout: '[data-xy-modebar-menu-item="zoomout"]',
  back: '[data-xy-modebar-history="back"]',
  forward: '[data-xy-modebar-history="forward"]',
  reset: '[data-xy-modebar-menu-item="reset"]',
  fit: '[data-xy-modebar-menu-item="fit"]',
};

export function createXYControls(root, {onReset}) {
  const canvas = root.querySelector('[data-xy-slot="canvas"]');
  const nativeBar = root.querySelector('[data-xy-slot="modebar"]');
  if (!canvas || !nativeBar) throw Error('The XY client control contract is unavailable.');
  const buttons = Object.fromEntries(Object.entries(SELECTORS).map(([key, selector]) => [key, root.querySelector(selector)]));
  const selectionTrigger = root.querySelector('[data-xy-modebar-select-trigger]');
  const zoomLabel = root.querySelector('[data-xy-modebar-zoom-percent]');
  const subscribers = new Set();
  // Keep the engine-owned controls for its gestures and accessibility state.
  // The host presents them through one visible toolbar; no engine math is copied.
  nativeBar.setAttribute('aria-hidden', 'true');

  function state() {
    return {
      mode: canvas.dataset.xyDragmode || 'none',
      canSelect: Boolean(selectionTrigger && selectionTrigger.style.display !== 'none'),
      zoom: zoomLabel?.textContent || '100%',
      enabled: Object.fromEntries(Object.entries(buttons).map(([key, button]) => [key, Boolean(button && !button.disabled)])),
    };
  }

  function notify() {
    const value = state();
    for (const callback of subscribers) callback(value);
  }

  const observer = new MutationObserver(notify);
  observer.observe(canvas, {attributes: true, attributeFilter: ['data-xy-dragmode']});
  observer.observe(nativeBar, {subtree: true, attributes: true, childList: true, characterData: true,
    attributeFilter: ['disabled', 'style', 'aria-pressed']});

  function perform(action) {
    const button = buttons[action];
    if (!button || button.disabled) return false;
    button.click();
    notify();
    return true;
  }

  function setTool(mode) {
    const current = state().mode;
    if (current === mode) return;
    if (mode === 'pan' || mode === 'none') {
      if (current !== 'pan') perform('pan');
      if (mode === 'none') perform('pan');
    } else if (!mode.startsWith('select') || state().canSelect) {
      perform(mode);
    }
  }

  function resetClick(event) {
    if (event.target.closest(SELECTORS.reset + ', ' + SELECTORS.fit)) onReset();
  }
  root.addEventListener('click', resetClick, true);

  return {
    canvas, state, perform, setTool,
    icon(action) {
      return buttons[action]?.querySelector('svg')?.cloneNode(true) || null;
    },
    subscribe(callback) {
      subscribers.add(callback);
      callback(state());
      return () => subscribers.delete(callback);
    },
    dispose() {
      observer.disconnect();
      subscribers.clear();
      root.removeEventListener('click', resetClick, true);
    },
  };
}
