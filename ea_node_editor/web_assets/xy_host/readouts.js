// Purpose: Show compact point readouts and an optional bounded selection drawer.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_plot_qml.py
import {fileIcon} from './toolbar.js';

const number = value => typeof value === 'number' ?
  Number(value.toPrecision(10)).toLocaleString('en-US', {maximumSignificantDigits: 10}) : String(value ?? '—');

function table(target, labels, rows) {
  const element = document.createElement('table');
  const header = element.createTHead().insertRow();
  for (const label of labels) {
    const cell = document.createElement('th'); cell.textContent = label; header.append(cell);
  }
  const body = element.createTBody();
  for (const values of rows) {
    const row = body.insertRow();
    for (const [index, value] of values.entries()) {
      const cell = row.insertCell(); cell.textContent = number(value);
      cell.dataset.tooltip = String(value ?? '—');
      if (index > 0) cell.className = 'numeric';
    }
  }
  target.replaceChildren(element);
}

export function createReadouts({syncMessage, syncAxes, onClear}) {
  const lifetime = new AbortController();
  const {signal} = lifetime;
  const readout = document.getElementById('readout');
  const mode = document.getElementById('mode');
  const drawer = document.getElementById('inspection');
  const toggle = document.getElementById('selection-toggle');
  const count = document.getElementById('selection-count');
  const clear = document.getElementById('clear');
  const close = document.getElementById('inspection-close');
  const sync = document.getElementById('sync');
  const probeToggle = document.getElementById('probe-toggle');
  const tabs = {selection: document.getElementById('selection-tab'), probes: document.getElementById('probes-tab')};
  let activeTab = 'selection';
  toggle.prepend(fileIcon('format-list-bulleted'));
  toggle.append(fileIcon('chevron-down'));
  clear.append(fileIcon('x')); close.append(fileIcon('x'));
  sync.prepend(fileIcon('link'));
  probeToggle.prepend(fileIcon('focus'));
  const syncText = document.createElement('span');
  syncText.textContent = !syncAxes ? 'Range sync' : syncAxes.x && syncAxes.y ? 'Sync on close' :
    !syncAxes.x && !syncAxes.y ? 'Local view' : syncAxes.x ? 'Y local' : 'X local';
  sync.append(syncText); sync.dataset.tooltip = syncMessage;

  function open(value) {
    drawer.hidden = !value;
    toggle.setAttribute('aria-expanded', String(value && activeTab === 'selection'));
    probeToggle.setAttribute('aria-expanded', String(value && activeTab === 'probes'));
  }
  function showTab(tab) {
    activeTab = tab;
    document.getElementById('selection-panel').hidden = tab !== 'selection';
    document.getElementById('probe-panel').hidden = tab !== 'probes';
    document.getElementById('selection-summary').hidden = tab !== 'selection';
    for (const [name, button] of Object.entries(tabs)) button.setAttribute('aria-selected', String(name === tab));
    open(true);
  }
  const focusToggle = () => (activeTab === 'probes' && !probeToggle.hidden ? probeToggle : toggle).focus();
  toggle.addEventListener('click', () => {if (!drawer.hidden && activeTab === 'selection') open(false); else showTab('selection');}, {signal});
  probeToggle.addEventListener('click', () => {if (!drawer.hidden && activeTab === 'probes') open(false); else showTab('probes');}, {signal});
  for (const [tab, button] of Object.entries(tabs)) button.addEventListener('click', () => showTab(tab), {signal});
  document.getElementById('inspection-tabs').addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault(); event.stopPropagation();
    const next = event.key === 'Home' ? 'selection' : event.key === 'End' ? 'probes' : activeTab === 'selection' ? 'probes' : 'selection';
    showTab(next); tabs[next].focus();
  }, {signal});
  close.addEventListener('click', () => {open(false); focusToggle();}, {signal});
  clear.addEventListener('click', onClear, {signal});

  return {
    showTab,
    probeCount(value) {
      probeToggle.hidden = value === 0;
      document.getElementById('probe-count').textContent = `Probes (${value})`;
    },
    setMode(label, hint) {
      mode.textContent = label; mode.dataset.tooltip = hint;
    },
    note(message, warning = false) {
      readout.textContent = message; readout.dataset.tooltip = message;
      readout.classList.toggle('is-warning', warning);
    },
    hover(row) {
      this.note(`${row.label || 'Signal'} · #${Number(row.index) + 1}   X ${number(row.x)}   Y ${number(row.y)}`);
    },
    selection(value, geometry) {
      const total = geometry ? value.count : 0;
      count.textContent = total ? `${total.toLocaleString()} selected` : geometry ? '0 selected' : 'No selection';
      toggle.disabled = !total;
      clear.disabled = !geometry;
      toggle.dataset.tooltip = total ? 'Show selection statistics and sample rows.' :
        geometry ? 'No samples match the selection.' : 'Select marker samples to inspect statistics and rows.';
      if (!total) {
        if (activeTab === 'selection') open(false);
        document.getElementById('selection-summary').textContent = 'No selection';
        document.getElementById('statistics').textContent = 'Select marker samples to inspect statistics.';
        document.getElementById('sample-rows').replaceChildren();
        document.getElementById('preview-note').textContent = '';
        return;
      }
      document.getElementById('selection-summary').textContent = `${total.toLocaleString()} original samples`;
      document.getElementById('preview-note').textContent = `First ${value.rows.length} samples`;
      table(document.getElementById('statistics'), ['Signal', 'Count', 'Mean Y', 'Min Y', 'Max Y'],
        value.signals.map(row => [row.label, row.count, row.y_mean, row.y_min, row.y_max]));
      table(document.getElementById('sample-rows'), ['Signal', 'Sample', 'X', 'Y'],
        value.rows.map(row => [row.label, row.index + 1, row.x, row.y]));
    },
    cancelInteraction() {
      if (drawer.hidden) return false;
      open(false); focusToggle(); return true;
    },
    dispose() {lifetime.abort();},
  };
}
