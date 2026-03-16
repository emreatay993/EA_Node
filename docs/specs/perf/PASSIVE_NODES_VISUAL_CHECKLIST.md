# Passive Nodes Visual Checklist

Use this checklist with the reference workspace at `tests/fixtures/passive_nodes/reference_flowchart.sfe`.

- Open the reference workspace and confirm it loads as a passive-only canvas with no executable nodes.
- If the repo has moved since the fixture was generated, relink the media panels to `tests/fixtures/passive_nodes/reference_preview.png` and `tests/fixtures/passive_nodes/reference_preview.pdf` with the inspector browse buttons before continuing.
- Verify the flowchart can be recreated from the existing layout: mixed flowchart silhouettes are present, the decision branches show edge labels, and the connector accepts the two incoming `flow` edges.
- Verify per-node overrides render after open: the decision, document, input/output, planning card, annotation note, image panel, and PDF panel each keep their distinct colors.
- Verify the image panel shows the local PNG preview and the PDF panel shows page 1 of the local reference PDF.
- Reopen the project and confirm the image preview, PDF preview, edge labels, and node colors still render.
- Open a passive node style dialog and a flow-edge style dialog, confirm the project presets `Review Accent` and `Review Loop` are available, apply one, then use reset to confirm presets and overrides behave correctly after reopen.
- Click `Run` and confirm the passive-only workspace does not produce executable work or runtime graph side effects.
