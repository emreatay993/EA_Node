# Core Integrations: File, Process, Email, Spreadsheet

## Purpose
Use this for built-in integration nodes, process execution policies, file IO nodes, email nodes, spreadsheet nodes, and integration catalog metadata.

## Start Here
- `ea_node_editor/nodes/builtins/integrations.py`
- `ea_node_editor/nodes/builtins/integrations_common.py`
- `ea_node_editor/nodes/builtins/integrations_file_io.py`
- `ea_node_editor/nodes/builtins/integrations_process.py`
- `ea_node_editor/nodes/builtins/process_subprocess_policy.py`
- `ea_node_editor/nodes/builtins/integrations_email.py`
- `ea_node_editor/nodes/builtins/integrations_spreadsheet.py`
- `ea_node_editor/nodes/file_dialog_filters.py`
- `tests/test_integrations_track_f.py`
- `tests/test_process_run_node.py`

## Notes
- File Read/Write and Excel Read/Write native browse filters are declared on their path `PropertySpec.file_filter` values. Keep file-type changes in the node definition and shared filter constants, not in shell presenter conditionals.
- Process Run declares its command input mandatory with a same-key property fallback. Email Send declares SMTP host, sender, and recipient settings centrally, and requires a password only when Username is nonblank. Missing configuration waits/yellows before plugin construction; subprocess and SMTP failures remain runtime errors.
- Stored Process Run stdout/stderr form one transactional typed-artifact pair. Reruns replace seeded slots, partial registration rolls back only attempted transcripts, and cleanup failures do not mask the primary process error.
- `process_subprocess_policy.py` remains the shared process allow/deny owner after the old HPC node family is removed; SSH/SFTP uses Paramiko and does not route through this subprocess policy.

## Focused Verification
```powershell
.\venv\Scripts\python.exe -m pytest tests/test_integrations_track_f.py --ignore=venv -q
.\venv\Scripts\python.exe -m pytest tests/test_process_run_node.py --ignore=venv -q
```

## Breadcrumbs
- [Nodes, Registry, Built-ins, And Plugin Loading](../subsystems/nodes_registry_builtins.md)
- [SSH/SFTP Nodes](ssh_sftp_nodes.md)

## Update Triggers
Update when integration node ports, path browse filters, readiness metadata, stored process transcript transactions, runtime behavior, or integration tests change.
