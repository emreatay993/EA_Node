# Pilot Backlog

## P0 (Must Fix Before Internal Pilot GO)

- No open P0 blockers as of packaged pilot evidence run `20260301_211523`.
- Closed:
  - Packaged interactive add/connect validation gap.
  - Autosave recovery validation gap.

## P1 (High Priority Release Readiness)

1. Packaging signing
   - Risk: unsigned executable decreases trust and can trigger SmartScreen friction.
   - Exit criteria: integrate Authenticode signing with certificate management and verification step in release flow.

2. Installer pipeline
   - Risk: OneDir artifact exists, but no installer artifact or install/uninstall validation gate.
   - Exit criteria: produce signed installer (MSI/EXE), include silent install/uninstall CI checks.

3. Optional dependency packaging policy
   - Risk: optional deps (notably `openpyxl`, `psutil`) require clear packaging/runtime contract.
   - Exit criteria: document dependency matrix and ensure user-facing runtime messaging remains deterministic in packaged builds.

## P2 (Post-Pilot Hardening)

1. Interactive desktop performance variance
   - Risk: current benchmark gate evidence is primarily offscreen; absolute desktop/GPU timings can differ.
   - Exit criteria: collect repeated interactive desktop perf baselines and set variance thresholds for pilot hardware classes.
