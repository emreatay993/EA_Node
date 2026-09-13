// Purpose: Present cursor coordinates, reading methods and bounded result pages.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_probe_qml.py
import {fileIcon} from './toolbar.js';
import {formatProbePosition} from './probe_coordinates.js';

const number = value => typeof value === 'number' ? value.toLocaleString('en-US', {maximumSignificantDigits: 10}) : String(value ?? '—');

export function createProbeReadouts(metadata, actions) {
  const host = document.getElementById('probe-panel');
  const lifetime = new AbortController(), {signal} = lifetime;
  const signals = new Map(metadata.signals.map(item => [item.id, item]));
  let current, invalidEdit = false;
  const controls = document.createElement('div'); controls.className = 'probe-fields';
  function field(label, element) {
    const wrapper = document.createElement('label');
    const text = document.createElement('span'); text.textContent = label;
    wrapper.append(text, element); controls.append(wrapper);
    return text;
  }
  const active = document.createElement('select'); active.id = 'probe-active';
  for (const [value, label] of [['x', 'Vertical (X)'], ['y', 'Horizontal (Y)']]) active.add(new Option(label, value));
  field('Cursor', active);
  const input = document.createElement('input'); input.id = 'probe-position'; input.type = 'text'; input.autocomplete = 'off';
  const positionLabel = field('Position', input);
  const method = document.createElement('select'); method.id = 'probe-method';
  for (const [value, label] of [['intersections', 'Interpolated intersections'], ['nearest', 'Nearest samples']]) method.add(new Option(label, value));
  field('Reading', method);
  const remove = document.createElement('button');
  remove.id = 'probe-remove'; remove.className = 'status-button icon-button'; remove.type = 'button';
  remove.setAttribute('aria-label', 'Remove active probe'); remove.dataset.tooltip = 'Remove the selected cursor.'; remove.append(fileIcon('x'));
  controls.append(remove);
  const validation = document.createElement('div'); validation.id = 'probe-validation'; validation.className = 'probe-validation'; validation.setAttribute('role', 'alert');
  const status = document.createElement('div'); status.id = 'probe-status'; status.className = 'probe-status'; status.setAttribute('role', 'status');
  const scroll = document.createElement('div'); scroll.id = 'probe-results'; scroll.className = 'table-scroll probe-results';
  const pager = document.createElement('div'); pager.className = 'probe-pager';
  function pageButton(id, text, delta) {
    const button = document.createElement('button'); button.type = 'button'; button.id = id; button.textContent = text; button.className = 'status-button';
    button.addEventListener('click', () => actions.page(delta), {signal}); pager.append(button); return button;
  }
  const previous = pageButton('probe-previous', 'Previous', -1);
  const pageInfo = document.createElement('span'); pageInfo.id = 'probe-page-info'; pager.append(pageInfo);
  const next = pageButton('probe-next', 'Next', 1);
  host.replaceChildren(controls, validation, status, scroll, pager);

  function resetEdit() {invalidEdit = false; validation.textContent = ''; input.removeAttribute('aria-invalid');}
  function commit() {actions.position(input.value);}
  active.addEventListener('change', () => {resetEdit(); actions.active(active.value);}, {signal});
  method.addEventListener('change', () => actions.method(method.value), {signal});
  remove.addEventListener('click', () => {resetEdit(); actions.remove();}, {signal});
  input.addEventListener('change', commit, {signal});
  input.addEventListener('keydown', event => {
    if (event.key === 'Enter') {event.preventDefault(); event.stopPropagation(); commit();}
  }, {signal});

  return {
    update(state) {
      if (current && current.active !== state.active) resetEdit();
      current = state;
      active.value = state.active; method.value = state.method;
      method.options[0].disabled = !state.hasLines;
      positionLabel.textContent = state.active === 'x' && metadata.x_kind === 'datetime' ? 'X position (UTC)' : state.active.toUpperCase() + ' position';
      input.placeholder = state.active === 'x' && metadata.x_kind === 'datetime' ? 'YYYY-MM-DDTHH:mm:ss.sssZ' : 'Click the chart or enter a value';
      if (document.activeElement !== input && !invalidEdit) input.value = formatProbePosition(state.positions[state.active], state.active, metadata);
      remove.disabled = state.positions[state.active] === null;
      if (!state.hasPosition) this.empty('Place a cursor on the chart or enter its coordinate.');
    },
    inputError(message) {
      invalidEdit = true; validation.textContent = message; input.setAttribute('aria-invalid', 'true');
    },
    committed() {resetEdit(); input.value = formatProbePosition(current.positions[current.active], current.active, metadata);},
    cancelEdit() {
      if (!current || document.activeElement !== input) return false;
      const value = formatProbePosition(current.positions[current.active], current.active, metadata);
      if (!invalidEdit && input.value === value) return false;
      resetEdit(); input.value = value; return true;
    },
    empty(message, preserveResult = false) {
      status.textContent = message; status.classList.remove('is-warning'); scroll.replaceChildren();
      scroll.setAttribute('aria-busy', 'false');
      if (!preserveResult) for (const key of ['revision', 'total', 'page']) delete status.dataset[key];
      pageInfo.textContent = ''; previous.disabled = next.disabled = true;
    },
    pending() {this.empty('Updating probe results…'); scroll.setAttribute('aria-busy', 'true');},
    error(message) {this.empty(message); status.classList.add('is-warning');},
    result(value) {
      for (const key of ['revision', 'total', 'page']) status.dataset[key] = String(value[key]);
      scroll.setAttribute('aria-busy', 'false');
      if (value.outside_view) {this.empty('This cursor is outside the visible window. Pan back, edit its coordinate, or place it again.', true); return;}
      if (!value.counts.length) {this.empty('No traces are visible.', true); return;}
      const unavailable = value.counts.filter(item => item.status === 'no_line').map(item => signals.get(item.signal)?.label || item.signal);
      const noun = value.method === 'nearest' ? (value.total === 1 ? 'nearest sample' : 'nearest samples') :
        value.total === 1 ? 'intersection' : 'intersections';
      status.textContent = value.total ? `${value.total.toLocaleString()} ${noun}${value.overlaps ? ` (${value.overlaps.toLocaleString()} overlap intervals)` : ''} in the visible window.` : `No ${noun} in the visible window.`;
      if (unavailable.length) status.textContent += ` No visible line: ${unavailable.join(', ')}. Nearest samples remain available.`;
      status.classList.remove('is-warning');
      const table = document.createElement('table'), header = table.createTHead().insertRow();
      for (const label of ['Signal', 'Reading', metadata.x_kind === 'datetime' ? 'X (UTC)' : 'X', 'Y', 'Sample / segment',
        value.axis === 'x' && metadata.x_kind === 'datetime' ? 'Offset (ms)' : 'Offset (' + value.axis.toUpperCase() + ')']) {
        const cell = document.createElement('th'); cell.textContent = label; header.append(cell);
      }
      const body = table.createTBody();
      const kinds = {exact: 'Exact sample', nearest: 'Nearest sample', interpolated: 'Interpolated', overlap: 'Overlap interval'};
      for (const row of value.rows) {
        const tr = body.insertRow();
        let x = row.x_text || number(row.x), y = number(row.y);
        if (row.kind === 'overlap') {
          if (row.x_end !== row.x) x += ' – ' + (row.x_end_text || number(row.x_end));
          if (row.y_end !== row.y) y += ' – ' + number(row.y_end);
        }
        const sample = row.sample_start === row.sample_end ? row.sample_start + 1 : `${row.sample_start + 1}–${row.sample_end + 1}`;
        for (const text of [signals.get(row.signal)?.label || row.signal, kinds[row.kind], x, y, sample, row.offset === undefined ? '—' : number(row.offset)]) {
          const cell = tr.insertCell(); cell.textContent = String(text); cell.dataset.tooltip = String(text);
        }
      }
      scroll.replaceChildren(table);
      const first = value.total ? value.page * value.page_size + 1 : 0;
      pageInfo.textContent = value.rows.length ? `${first.toLocaleString()}–${(first + value.rows.length - 1).toLocaleString()} of ${value.total.toLocaleString()}` : 'No rows';
      previous.disabled = value.page === 0; next.disabled = (value.page + 1) * value.page_size >= value.total;
    },
    dispose() {lifetime.abort(); host.replaceChildren();},
  };
}
