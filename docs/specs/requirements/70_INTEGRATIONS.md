# Integration Starter Pack Requirements

## Mandatory Nodes (Skeleton Core)
- `REQ-INT-001`: Core nodes: Start, End, Constant, Logger, Python Script.
- `REQ-INT-002`: I/O nodes: Excel Read, Excel Write, File Read, File Write, Email Send.
- `REQ-INT-006`: I/O nodes shall include a generic external process runner (`io.process_run`) for command-line tool integration.

## Behavior
- `REQ-INT-003`: Excel nodes shall support CSV and XLSX (XLSX requiring `openpyxl`).
- `REQ-INT-004`: File nodes shall support text and JSON payload writing.
- `REQ-INT-005`: Email node shall support SMTP host/port and optional TLS/auth.
- `REQ-INT-007`: Built-in integration implementation shall be split by domain module (spreadsheet, file I/O, email, process-run) with stable type IDs.

## Acceptance
- `AC-REQ-INT-001-01`: Starter nodes appear in node library and can be placed in graph.
- `AC-REQ-INT-003-01`: CSV read/write path works end to end.
- `AC-REQ-INT-005-01`: Email node validates required sender/recipient before sending.
- `AC-REQ-INT-006-01`: Process runner executes command, captures stdout/stderr/exit code, and supports timeout/non-zero validation.
