// Purpose: Parse exact numeric/UTC cursor positions independently of the UI.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_probe_scheduler.py
export function formatProbePosition(value, axis, metadata) {
  if (value === null || value === undefined) return '';
  if (axis !== 'x' || metadata.x_kind !== 'datetime') return String(value);
  let milliseconds = Math.floor(value), fraction = Math.round((value - milliseconds) * 1000);
  if (fraction === 1000) {milliseconds += 1; fraction = 0;}
  const date = new Date(milliseconds);
  if (!Number.isFinite(date.getTime())) return String(value);
  const text = date.toISOString();
  return fraction ? text.slice(0, -1) + String(fraction).padStart(3, '0') + 'Z' : text;
}

export function parseProbePosition(text, axis, metadata) {
  const value = String(text).trim();
  let position;
  if (axis === 'x' && metadata.x_kind === 'datetime') {
    const match = /^((?:\d{4}|[+-]\d{6})-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
    if (!match) throw Error('Enter a UTC timestamp, for example 2026-01-01T12:00:00.000Z.');
    const fraction = (match[2] || '').padEnd(6, '0');
    const base = Date.parse(match[1] + '.' + fraction.slice(0, 3) + 'Z');
    if (!Number.isFinite(base) || new Date(base).toISOString().split('.')[0] !== match[1]) throw Error('Enter a valid UTC date and time.');
    position = base + Number(fraction.slice(3)) / 1000;
  } else {
    if (!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(value)) throw Error('Enter a finite numeric coordinate.');
    position = Number(value);
  }
  if (!Number.isFinite(position)) throw Error('Enter a finite coordinate.');
  if (axis === 'y' && metadata.y_log && position <= 0) throw Error('A logarithmic Y coordinate must be positive.');
  return position;
}
