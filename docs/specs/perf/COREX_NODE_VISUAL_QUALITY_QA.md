# COREX Node Visual Quality

Status: **visual implementation complete; performance acceptance not achieved**.
The user explicitly authorized publication to `main` with these limits documented
on 2026-09-23. The agreed 5% maximum slowdown has not been demonstrated;
publication approval does not change the measured acceptance result.

## Agreed outcome

Sharper shared canvas controls and node outlines under FluentWinUI3. Scalar and
interval sliders use macOS-inspired light circular thumbs. Switches retain a
Fluent-inspired capsule. Settings use open vector chevrons without enclosing
circles. Port anchors, interaction regions, node semantics, and unrelated work
remain unchanged. Publish accepted task changes to main and origin/main.

## Acceptance

- Matched production screenshots at 50, 100, 125, 200, 300, and 500 percent zoom,
  light/dark themes, native DPR and supplemental 1.0/1.5/2.0 probes.
- Full-card and transparent-notch checks, including pills, gradients, locked
  hatching, selected/error/warning states, groups, and fractional resize.
- Existing interaction/commit/accessibility behavior and focused regression tests.
- Three matched isolated baseline/candidate runs: each gated median run-level p95
  must be at most 1.05 times baseline. Preserve absolute gates and feature parity;
  report existing failures separately. Screenshots stay outside timed samples.
- Independent review, broader GUI integration, documentation hygiene, exact-path
  staging, normal push, and remote parity verification.

## Execution progress

| Task | Status | Owner | Evidence / next action |
|---|---|---|---|
| T01 Baseline and proof tooling | Complete; signal-observer correction reviewed | visual_proof_tooling / tooling_review | Frozen original source, matched instrumentation, strict animation validation; observer followup passes 15 tests |
| T02 Controls and chevrons | Integrated, focus/disabled refinement accepted | controls_implementation / controls_review | 2821b1ae and c8a73b78 integrated as 09e5ebf9/eea654f0; focus curves and opaque disabled thumbs additionally pass Basic17/Fluent17 |
| T03 Chrome and ports | Reviewed and integrated, followup fixed | chrome_implementation / chrome_review | 00b0c814 and retention followup 6c5da637 integrated as 699176c8/e13bbe06; strict identity/change-count and animated geometry checks pass |
| T04 Production visual proof | Complete | Coordinator / implementation owners | GUI passes; native98+98, valid DPR1.5/2 pairs22each, six focus/state PNGs; failed oversized-DPR captures excluded |
| T05 Performance acceptance | Not achieved | Coordinator / final_performance_verification | Final typical/stress comparison retains timing and variance failures; baseline controls still cannot provide valid animation evidence at 500% |
| T06 Documentation and publication | Publication authorized with documented limits | Coordinator | User explicitly approved pushing the visual improvements; performance gate remains not passed |

## Baseline

Initial HEAD: `9b1cc056e8d61a86a81bb64f29546a82704f1aa6`.

The baseline source is a detached worktree with the pre-existing tracked dirty
files copied exactly, including the Fluent startup selection. Both sides use
the original project Python/Qt runtime. The inventory and original files are
retained locally; unrelated changes are excluded from task staging.

The stress fixture was copied byte-for-byte after worktree creation to eliminate
Git checkout line-ending differences. Its SHA-256 is
`dbe1b48ccd611b762615dab9d8ce5fca1935441449eaffc362979126f445c4fb`.

Qt reports one active 1920x1080 screen, DPR 1.0, approximately 144 Hz. The installed
Qt runtime and matching QuickTest SDK are 6.11.1. Full run metadata remains the
authority for benchmark environment validity.

Control implementation, chrome geometry, and measurement tooling used disjoint
write scopes and isolated source checkouts. Integration and benchmark jobs were
serialized; performance runs did not overlap tests, builds, or screenshots.

Full evidence location: `artifacts/visual_quality/20260923/` (ignored).

Concurrent independent work committed the original Fluent/startup edits as
`c1ad525d`, followed by unrelated sample/manifest commits `b2dced10` and
`d514fb70`. Those changes were preserved. The Fluent source content matches the
initial frozen overlay, so the rendering baseline remains applicable.

## Delivered changes and publication boundary

Shared scalar/range sliders now have aligned tracks and macOS-inspired light
circular thumbs. Explicit QtQuick.Templates sizing removes inherited Fluent
padding. Switches, focus frames and port rings use retained curves; disabled
slider thumbs are opaque. Node bodies use analytic curves and transparent
cutouts, with full-card and colored-background checks. Settings use rounded
open right/down vector chevrons. Existing anchors, input, keyboard, accessibility
and value-commit behavior are preserved.

Independent integration review found no blocking code defects. A separate
evidence review checked 350 measurement, arithmetic and provenance conditions
without finding a mismatch. Visual and GUI
verification are complete. The user approved publication despite the unresolved
performance gate. The thresholds and failed evidence remain unchanged.

## Results

Visual and integration review found no blocking defects. The performance gate has not passed.

The performance-harness/tooling pytest run passed 60 tests plus 6 subtests
in 25.43 seconds (`performance-harness-tests-final.log`). The subsequent
signal-observer correction passed 15 focused tests and independent review.
Final map, Markdown-link and traceability checks passed. Ruff passed; Markdown
and traceability hygiene passed 102 tests plus 15 subtests.
The full passing run supersedes the
earlier uncompleted unittest attempt as the proving harness correctness check.

GUI correctness closeout: QuickTest phase passed; parallel Python GUI passed
640 tests with 2 skips. The serial phase initially had an unexplained 180-second
flow-label probe timeout; current and frozen baseline exact probes passed, and
the complete serial rerun passed 50 tests plus 40 subtests with 1 skip. The
initial failure remains in the verification log; no application change or
timeout relaxation was used to obtain the serial pass. Native XY activation and
the two fixed-duration animation checks now use the existing serial lane, with
unchanged assertions. Verification-runner contract tests pass 42 + 4 subtests.

Typical round1 (`performance/typical-round1/comparison.json`) is not accepted:
median pan/zoom improves 9.4%, full drag 17.0%, and loading 12.4%, but repeated-run
variance exceeds the declared limits. The legacy single-offset drag diagnostic
is 14.1% slower. All samples are retained.

Typical round2 (`performance/typical-round2/comparison.json`) also fails timing
and variance gates. It shows a steady-offset increase from 0.215 to 0.302 ms and
noisy pan timings, although full drag and loading improve. This prompted a
strict-reference diagnostic: position-only and paint-only payload publication
rebuilt equal contour objects. Followup 6c5da637 suppresses unchanged numeric
center notifications; actual resize/topology/animation still updates geometry.
The fix is independently reviewed. Its followup measurements are retained below; no threshold is waived.

The post-fix set (`performance/typical-retention-fix/comparison.json`) still fails:
full drag is 29.898 to 45.801 ms and steady-offset 0.223 to 0.244 ms. Pan and load
improve, but several variance checks also fail. The retained-geometry fix is a
proven correctness/per-work optimization, not proof of overall non-regression.
Two short rendering-stat diagnostics followed this result.

The two diagnostics completed but emitted no batching/render-timing output, so
they do not support attributing a regression to GPU draw calls. They show mixed
outcomes and are not acceptance runs. Source review also confirms that steady
offset timing includes signal dispatch plus one event pass (no rendered-frame
barrier), full-gesture timing includes a final image grab, and the aggregate frame
interval metric includes between-gesture idle gaps. These limits are retained
alongside all failed comparisons; no result has been relabeled as a pass.

The final matrix completed three matched fresh-process runs per side for both
200-node typical and 1200-node stress cases. Display diagnostics and feature
parity passed in all 12 runs. The controls case stopped on baseline run 1 because
settings expansion changed state but did not provide observed animation progress.
That failed run is retained and cannot prove candidate performance. The completed
cases are summarized in `performance/final-matrix/partial-comparison.json`:

| Case / metric | Baseline p95 median (ms) | Candidate p95 median (ms) | Change | Timing <=5% | Variance |
|---|---:|---:|---:|---|---|
| Typical full drag | 17.709 | 15.748 | -11.1% | Pass | Pass |
| Typical drag cleanup | 22.772 | 30.538 | +34.1% | Fail | Pass |
| Typical loading | 421.435 | 407.083 | -3.4% | Pass | Pass |
| Typical zoom | 498.280 | 533.904 | +7.1% | Fail | Fail |
| Stress full drag | 22.943 | 23.106 | +0.7% | Pass | Pass |
| Stress drag cleanup | 31.511 | 31.968 | +1.4% | Pass | Pass |
| Stress loading | 1820.752 | 1800.061 | -1.1% | Pass | Pass |
| Stress pan | 521.151 | 550.631 | +5.7% | Fail | Fail |

These are incomplete-matrix results, not acceptance. Existing absolute pan/zoom
requirements fail on both sides. No evidence was discarded to improve a result.

The polling observer missed real QML progress and completion emitted inside one
Qt event-processing call. The reviewed correction connects production signals
before dispatch and disconnects after measurement; existing progress, geometry,
completion and multiple-frame validation remain unchanged. A subsequent
one-sample baseline diagnostic still fails at settings collapse, zoom 500%,
because fewer than two active frames render. No complete matched control timing
report exists. The coarse baseline animation is not counted as zero-time success.

A bounded drag-cleanup diagnostic found zero candidate silhouette rebuilds,
center-signature changes, or center publications during clear. Its p95 was
13.511 to 14.796 ms; the original +7.8 ms effect was not reproduced at that
magnitude, and mean time decreased. Render/readback phase p95 decreased overall.
Instrumentation perturbs timing: this diagnostic does not replace the final
matrix or establish acceptance. No further source change is justified by it.
Evidence is in `chrome_source/artifacts/clear-attribution/`.

[Machine-readable performance proof](../../assets/corex-node-visual-quality/performance.json)
contains every final metric row, individual run p95 values, variability, CPU/RSS,
absolute requirements, prior failed comparisons and diagnostic limitations.
The acceptance limits are unchanged: median run-level p95 ratio <=1.05, CV <=0.20
and range <=8 ms (24 ms for full drag); loading permits CV <=0.25/range <=500 ms.
The final matrix used identical instrumentation hashes in
`instrumentation-freeze.json`. The later signal-observer correction is recorded
separately and does not modify ordinary benchmark timing paths.

## Native visual evidence

Both full native matrices each contain 98 captures: two themes, six zoom levels,
eight target regions, and overview frames. Representative unmodified PNG pairs:

| Surface | Before | After |
|---|---|---|
| Slider and track | [Before](../../assets/corex-node-visual-quality/slider-before.png) | [After](../../assets/corex-node-visual-quality/slider-after.png) |
| Switches | [Before](../../assets/corex-node-visual-quality/switches-before.png) | [After](../../assets/corex-node-visual-quality/switches-after.png) |
| Port circles and notches | [Before](../../assets/corex-node-visual-quality/ports-before.png) | [After](../../assets/corex-node-visual-quality/ports-after.png) |
| Settings chevrons | [Before](../../assets/corex-node-visual-quality/chevrons-before.png) | [After](../../assets/corex-node-visual-quality/chevrons-after.png) |

Forced-DPR warning: original `baseline/dpr150`, `baseline/dpr200`,
`candidate/dpr150`, and `candidate/dpr200` files are rejected evidence. They are
uniform dark frames; diagnostics report Direct3D device loss, and Windows clamped
the oversized capture viewport. Their successful file saves and API/DPR metadata
do not prove rendering. The native-DPR matrices contain actual rendered content.

The corrected capture tool chooses a display-fitting logical viewport before
widget creation, preserves the benchmark's 1280x720 default, and rejects invalid
pixels/device errors. The matched `dpr150-valid` and `dpr200-valid` directories
contain 22 valid images per side and scale. Viewports are 1166x656 at DPR1.5 and
846x476 at DPR2. Root inspection confirms smooth curved grips/notches and controls.
In total, 284 matched native/DPR PNGs pass validation, plus six control-state
images. All 98 baseline/native and 98 candidate/native-final images also pass the new
pixel-content validation. No driver or global display setting was changed.

Additional actual control-state captures cover keyboard focus, enabled/disabled
controls, reversed intervals and equal endpoints at 100/500 percent:
[light](../../assets/corex-node-visual-quality/light-control-states.png) and
[dark](../../assets/corex-node-visual-quality/dark-control-states.png). These found
and verified the correction of faceted focus frames and translucent disabled
thumbs; the normal slider/switch colors and interactions remain intact.

T02 full Fluent QuickTest has one pre-existing failure:
`test_selection_envelope_minimal_tooltip_stays_clear_of_affordance`. The exact
case fails on the frozen original source too. Retained logs are in
`controls_source/artifacts/control_tests/fluent-baseline-tooltip.txt` and
`fluent-full.txt`; the issue is outside the changed controls. The candidate
passes the other 59 cases, all 60 Basic cases, and the 30-case focused Fluent set.
