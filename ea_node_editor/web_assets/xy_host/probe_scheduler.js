// Purpose: Keep one probe request in flight and coalesce movement to the latest state.
// Map: feature_routes/plotter_nodes.md
// Tests: tests/test_xy_probe_scheduler.py
export function createProbeScheduler({send, pending, result, error,
  now = () => performance.now(), setTimer = setTimeout, clearTimer = clearTimeout}) {
  let revision = 0, latest = null, inFlight = null, timer = null, lastSent = -Infinity, disposed = false;

  function pump() {
    if (disposed || inFlight || !latest) return;
    const delay = latest.immediate ? 0 : Math.max(0, 100 - (now() - lastSent));
    if (delay) {
      if (timer === null) timer = setTimer(() => {timer = null; pump();}, delay);
      return;
    }
    const request = latest;
    latest = null;
    inFlight = request.query.revision;
    lastSent = now();
    try {send(request.query);}
    catch (failure) {
      inFlight = null;
      if (request.query.revision === revision) error(String(failure));
    }
  }

  return {
    update(query, immediate = false) {
      if (disposed) return;
      revision += 1;
      if (timer !== null) {clearTimer(timer); timer = null;}
      latest = query ? {query: Object.assign({}, query, {revision}), immediate} : null;
      pending(Boolean(query));
      pump();
    },
    receive(value, failure = false) {
      if (disposed || value.revision !== inFlight) return;
      inFlight = null;
      if (value.revision === revision) {
        if (failure) error(value.message); else result(value);
      }
      pump();
    },
    dispose() {
      disposed = true; latest = null; inFlight = null;
      if (timer !== null) clearTimer(timer);
      timer = null;
    },
  };
}
