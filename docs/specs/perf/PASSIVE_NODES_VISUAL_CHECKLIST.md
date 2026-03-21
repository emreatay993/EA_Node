# Passive Nodes Visual Checklist

Use this checklist with the reference workspace at `tests/fixtures/passive_nodes/reference_flowchart.sfe`.

- Open the reference workspace and confirm it loads as a passive-only canvas with no executable nodes.
- If the repo has moved since the fixture was generated, relink the media panels to `tests/fixtures/passive_nodes/reference_preview.png` and `tests/fixtures/passive_nodes/reference_preview.pdf` with the inspector browse buttons before continuing.
- Verify the flowchart can be recreated from the existing layout: mixed flowchart silhouettes are present, every flowchart node shows four exposed handles, and the decision branches are distinguished by edge labels rather than branch-specific port names.
- Confirm the main authored path reads cleanly after open: `Start -> Capture Request -> Ready for Review? -> Review Packet -> Revise -> Approval Board -> Archive -> Complete`, while the `Needs input` branch still targets `Stakeholder Input`.
- Verify per-node overrides render after open: the decision, document, input/output, planning card, annotation note, image panel, and PDF panel each keep their distinct colors.
- Verify the image panel shows the local PNG preview and the PDF panel shows page 1 of the local reference PDF.
- Optional file check: open `tests/fixtures/passive_nodes/reference_flowchart.sfe` in a text editor and confirm the flowchart edges and exposed-port overrides use only `top`, `right`, `bottom`, and `left`; there should be no `flow_in`, `flow_out`, `branch_a`, or `branch_b` keys left in the fixture.
- Reopen the project and confirm the image preview, PDF preview, four flowchart handles, edge labels, and node colors still render.
- Open a passive node style dialog and a flow-edge style dialog, confirm the project presets `Review Accent` and `Review Loop` are available, apply one, then use reset to confirm presets and overrides behave correctly after reopen.
- Click `Run` and confirm the passive-only workspace does not produce executable work or runtime graph side effects.
