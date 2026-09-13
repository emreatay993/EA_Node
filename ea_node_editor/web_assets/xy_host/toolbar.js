// Purpose: Present XY actions in one accessible toolbar with owned menus/tooltips.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py

export function fileIcon(name) {
  const icon = document.createElement('span');
  icon.className = 'tool-icon file-icon';
  icon.setAttribute('aria-hidden', 'true');
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `#icon-${name}`);
  svg.append(use); icon.append(svg);
  return icon;
}

function placePopup(popup, anchor) {
  const rect = anchor.getBoundingClientRect();
  const width = popup.offsetWidth, height = popup.offsetHeight;
  const below = rect.bottom + 7;
  popup.style.left = `${Math.max(8, Math.min(rect.left, innerWidth - width - 8))}px`;
  popup.style.top = `${Math.max(8, Math.min(below + height <= innerHeight - 8 ? below : rect.top - height - 7,
    innerHeight - height - 8))}px`;
}

function installTooltips(signal) {
  const tip = document.createElement('div');
  tip.id = 'plot-tooltip';
  tip.className = 'plot-tooltip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  document.body.append(tip);
  let target = null;
  function hide() {
    tip.hidden = true;
    target?.removeAttribute('aria-describedby');
    target = null;
  }
  function show(element) {
    if (element === target) return;
    hide();
    if (!element || document.querySelector('.plot-menu:not([hidden])')) return;
    target = element;
    tip.textContent = element.dataset.tooltip;
    element.setAttribute('aria-describedby', tip.id);
    tip.hidden = false;
    placePopup(tip, element);
  }
  document.addEventListener('pointerover', event => show(event.target.closest('[data-tooltip]')), {signal});
  document.addEventListener('pointerout', event => {
    if (target && !target.contains(event.relatedTarget)) hide();
  }, {signal});
  document.addEventListener('focusin', event => show(event.target.closest('[data-tooltip]')), {signal});
  document.addEventListener('focusout', hide, {signal});
  document.addEventListener('pointerdown', hide, {signal});
  document.addEventListener('click', hide, {signal});
  window.addEventListener('resize', hide, {signal});
  return {hide, dispose() {hide(); tip.remove();}};
}

const SELECTIONS = [
  ['select', 'Box select'], ['select-lasso', 'Lasso select'],
  ['select-x', 'Select X range'], ['select-y', 'Select Y range'],
];

export function createToolbar({controls, style, onFit, onStyle, beforeAction}) {
  const host = document.getElementById('toolbar');
  host.replaceChildren();
  const lifetime = new AbortController();
  const {signal} = lifetime;
  const tooltips = installTooltips(signal);
  const menus = new Map();
  let openMenu = null;

  function icon(name, native = false) {
    if (!native) return fileIcon(name);
    const wrapper = document.createElement('span');
    wrapper.className = 'tool-icon';
    wrapper.setAttribute('aria-hidden', 'true');
    const svg = controls.icon(name);
    if (svg) wrapper.append(svg);
    return wrapper;
  }

  function button(key, label, hint, image, native = false) {
    const element = document.createElement('button');
    element.type = 'button';
    element.className = 'tool-button';
    element.dataset.action = key;
    element.dataset.tooltip = hint;
    element.setAttribute('aria-label', label);
    element.append(icon(image, native));
    const text = document.createElement('span');
    text.className = 'tool-label'; text.textContent = label;
    element.append(text);
    return element;
  }

  function group(label) {
    const element = document.createElement('div');
    element.className = 'toolbar-group';
    element.setAttribute('role', 'group');
    element.setAttribute('aria-label', label);
    host.append(element);
    return element;
  }

  function closeMenu(restoreFocus = true) {
    if (!openMenu) return false;
    const {popup, trigger} = openMenu;
    openMenu = null;
    popup.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    if (restoreFocus) trigger.focus();
    return true;
  }

  function menu(key, label, trigger) {
    const popup = document.createElement('div');
    popup.id = `menu-${key}`;
    popup.className = 'plot-menu';
    // The host owns positioning, keyboard focus and dismissal consistently.
    popup.hidden = true;
    popup.setAttribute('role', 'menu');
    popup.setAttribute('aria-label', label);
    trigger.setAttribute('aria-haspopup', 'menu');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', popup.id);
    trigger.append(fileIcon('chevron-down'));
    trigger.lastChild.classList.add('menu-chevron');
    trigger.dataset.menu = key;
    document.body.append(popup);
    menus.set(key, popup);
    function open() {
      closeMenu(false); tooltips.hide();
      popup.hidden = false;
      placePopup(popup, trigger);
      trigger.setAttribute('aria-expanded', 'true');
      openMenu = {popup, trigger};
    }
    trigger.addEventListener('click', () => {
      if (openMenu?.popup === popup) closeMenu(); else open();
    }, {signal});
    trigger.addEventListener('keydown', event => {
      if (!['ArrowDown', 'ArrowUp'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation(); open();
      const items = [...popup.querySelectorAll('button:not(:disabled)')];
      items[event.key === 'ArrowUp' ? items.length - 1 : 0]?.focus();
    }, {signal});
    popup.addEventListener('keydown', event => {
      if (event.key === 'Tab') {
        event.preventDefault(); event.stopPropagation(); closeMenu(false);
        const tools = [...host.querySelectorAll('button:not(:disabled)')];
        const next = tools.indexOf(trigger) + (event.shiftKey ? -1 : 1);
        (tools[next] || controls.canvas).focus();
        return;
      }
      const items = [...popup.querySelectorAll('button:not(:disabled)')];
      const index = items.indexOf(document.activeElement);
      if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 :
        (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
      items[next]?.focus();
    }, {signal});
    return popup;
  }

  function item(popup, key, label, action, radio = false) {
    const element = document.createElement('button');
    element.type = 'button'; element.className = 'menu-item';
    element.dataset.command = key;
    element.setAttribute('role', radio ? 'menuitemradio' : 'menuitem');
    if (radio) element.setAttribute('aria-checked', 'false');
    element.append(icon(key, true));
    const text = document.createElement('span'); text.textContent = label;
    element.append(text);
    element.addEventListener('click', () => {
      closeMenu(); beforeAction(); action();
    }, {signal});
    popup.append(element);
    return element;
  }

  const navigation = group('Navigation');
  const pan = button('pan', 'Pan', 'Drag to pan. Click again to pause. Middle-drag temporarily pans in any tool.', 'pan', true);
  const zoom = button('zoom', 'Box zoom', 'Drag a rectangle to zoom into it. Wheel zoom is available in every tool.', 'zoom-fit');
  for (const [mode, element] of [['pan', pan], ['zoom', zoom]]) {
    element.setAttribute('aria-pressed', 'false');
    element.addEventListener('click', () => {
      closeMenu(false); beforeAction(); controls.setTool(controls.state().mode === mode ? 'none' : mode);
    }, {signal});
  }
  const select = button('selection', 'Select', 'Choose a selection tool to inspect original samples.', 'select', true);
  const view = button('view', 'Zoom', 'Zoom steps, view history and reset.', 'zoomin', true);
  navigation.append(pan, zoom, select, view);
  const selectMenu = menu('selection', 'Selection tools', select);
  for (const [mode, label] of SELECTIONS) item(selectMenu, mode, label, () => controls.setTool(mode), true);
  const viewMenu = menu('view', 'View navigation', view);
  for (const [key, label] of [['back', 'Previous view'], ['forward', 'Next view'], ['zoomin', 'Zoom in'], ['zoomout', 'Zoom out'], ['reset', 'Reset view and selection']]) {
    item(viewMenu, key, label, () => controls.perform(key));
  }

  const fits = group('Axis fitting');
  for (const [key, label, image, hint] of [
    ['x', 'Fit X', 'fit-width', 'Fit all data on X; keep Y unchanged. Eligible X limits become automatic on close.'],
    ['y', 'Fit Y', 'fit-height', 'Fit all data on Y; keep X unchanged. Eligible Y limits become automatic on close.'],
    ['data', 'Fit data', 'fullscreen', 'Fit all data on both axes. Eligible limits become automatic on close.'],
    ['limits', 'Fit to limits', 'video-fit', 'Restore the Signal Plot limits and discard pending range edits.'],
  ]) {
    const element = button(`fit-${key}`, label, hint, image);
    element.dataset.fit = key;
    element.addEventListener('click', () => {closeMenu(false); beforeAction(); onFit(key);}, {signal});
    fits.append(element);
  }

  const appearance = group('Toolbar appearance');
  appearance.classList.add('toolbar-appearance');
  const display = button('appearance', 'Display', 'Choose icons with tool names, or icons only.', 'settings');
  appearance.append(display);
  const displayMenu = menu('appearance', 'Toolbar display', display);
  const heading = document.createElement('div');
  heading.className = 'menu-heading'; heading.textContent = 'Toolbar display'; displayMenu.append(heading);
  for (const [value, label] of [['icons_with_names', 'Icons and names'], ['icons_only', 'Icons only']]) {
    const element = item(displayMenu, value, label, () => {setStyle(value); onStyle(value);}, true);
    element.dataset.toolbarStyle = value;
    element.firstChild.classList.add('radio-indicator');
  }
  const help = document.createElement('p');
  help.className = 'menu-help';
  help.textContent = 'Wheel to zoom · Middle-drag to pan · Escape cancels a gesture or menu before closing.';
  displayMenu.append(help);

  function setStyle(value) {
    document.body.dataset.toolbarStyle = value;
    for (const element of displayMenu.querySelectorAll('[data-toolbar-style]')) {
      element.setAttribute('aria-checked', String(element.dataset.toolbarStyle === value));
    }
  }
  setStyle(style);

  const unsubscribe = controls.subscribe(state => {
    for (const [mode, element] of [['pan', pan], ['zoom', zoom]]) {
      element.setAttribute('aria-pressed', String(state.mode === mode));
      element.disabled = !state.enabled[mode];
    }
    select.disabled = !state.canSelect;
    select.setAttribute('aria-pressed', String(state.mode.startsWith('select')));
    select.dataset.tooltip = state.canSelect ? 'Choose a selection tool to inspect original samples.' :
      'Selection needs individual marker samples. Enable markers or zoom in from the density view.';
    select.setAttribute('aria-description', select.dataset.tooltip);
    select.querySelector('.tool-label').textContent = SELECTIONS.find(([mode]) => mode === state.mode)?.[1] || 'Select';
    for (const element of selectMenu.querySelectorAll('[data-command]')) {
      element.setAttribute('aria-checked', String(element.dataset.command === state.mode));
    }
    for (const element of viewMenu.querySelectorAll('[data-command]')) element.disabled = !state.enabled[element.dataset.command];
    view.dataset.tooltip = `Zoom: ${state.zoom}. Zoom steps, view history and reset.`;
    if (!state.canSelect && openMenu?.popup === selectMenu) closeMenu();
  });

  host.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    const items = [...host.querySelectorAll('button:not(:disabled)')];
    const index = items.indexOf(document.activeElement);
    if (index < 0) return;
    event.preventDefault(); event.stopPropagation();
    const next = event.key === 'Home' ? 0 : event.key === 'End' ? items.length - 1 :
      (index + (event.key === 'ArrowRight' ? 1 : -1) + items.length) % items.length;
    items[next]?.focus();
  }, {signal});
  window.addEventListener('resize', () => closeMenu(false), {signal});
  document.addEventListener('pointerdown', event => {
    if (openMenu && !openMenu.popup.contains(event.target) && !openMenu.trigger.contains(event.target)) closeMenu(false);
  }, {signal});

  return {
    cancelInteraction() {tooltips.hide(); return closeMenu();},
    dispose() {
      unsubscribe(); lifetime.abort(); tooltips.dispose();
      for (const popup of menus.values()) popup.remove();
      host.replaceChildren();
    },
  };
}
