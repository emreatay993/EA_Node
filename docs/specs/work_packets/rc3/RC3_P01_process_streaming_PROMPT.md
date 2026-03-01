Implement `RC3_P01_process_streaming.md`.

Constraints:
- Keep protocol backward compatible for consumers expecting current terminal events.
- Preserve stop/cancel semantics for active subprocess nodes.
- Ensure console streaming remains bounded (no unbounded memory growth).

Deliverables:
1. Streaming execution/event updates in allowed files.
2. Regression and new tests in listed suites.
3. Validation summary and artifact paths.
4. Status ledger update for `P01`.
