"""Controller/session shell isolation targets."""
from __future__ import annotations

from functools import lru_cache

_SCRIPT_EDITOR_TEST_CLASS = "tests.test_script_editor_dock.ScriptEditorDockTests"
_RUN_CONTROLLER_TEST_CLASS = "tests.test_shell_run_controller.ShellRunControllerTests"


@lru_cache(maxsize=1)
def _build_targets():
    from tests.shell_isolation_runtime import ShellIsolationTarget

    return (
        ShellIsolationTarget.unittest_target(
            f"{_SCRIPT_EDITOR_TEST_CLASS}.test_script_editor_binds_to_selected_python_script_node",
            target_id="script_editor__test_script_editor_binds_to_selected_python_script_node",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_SCRIPT_EDITOR_TEST_CLASS}.test_script_editor_state_persists_in_metadata",
            target_id="script_editor__test_script_editor_state_persists_in_metadata",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_SCRIPT_EDITOR_TEST_CLASS}.test_script_editor_exposes_cursor_diagnostics_and_dirty_state",
            target_id="script_editor__test_script_editor_exposes_cursor_diagnostics_and_dirty_state",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_SCRIPT_EDITOR_TEST_CLASS}.test_set_script_editor_panel_visible_focuses_editor_for_script_node",
            target_id="script_editor__test_set_script_editor_panel_visible_focuses_editor_for_script_node",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_RUN_CONTROLLER_TEST_CLASS}.test_stream_log_events_are_scoped_to_active_run",
            target_id="run_controller__test_stream_log_events_are_scoped_to_active_run",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_RUN_CONTROLLER_TEST_CLASS}.test_stale_run_events_do_not_mutate_active_run_ui",
            target_id="run_controller__test_stale_run_events_do_not_mutate_active_run_ui",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_RUN_CONTROLLER_TEST_CLASS}.test_failure_focus_reveals_parent_chain_when_present",
            target_id="run_controller__test_failure_focus_reveals_parent_chain_when_present",
        ),
        ShellIsolationTarget.unittest_target(
            f"{_RUN_CONTROLLER_TEST_CLASS}.test_run_failed_event_centers_failed_node_and_reports_exception_details",
            target_id="run_controller__test_run_failed_event_centers_failed_node_and_reports_exception_details",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_session_restore_recovers_workspace_order_active_workspace_and_view_camera",
            target_id="project_session__test_session_restore_recovers_workspace_order_active_workspace_and_view_camera",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc",
            target_id="project_session__test_autosave_tick_writes_snapshot_and_keeps_valid_project_doc",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_recovery_prompt_accept_loads_newer_autosave",
            target_id="project_session__test_recovery_prompt_accept_loads_newer_autosave",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_recovery_prompt_reject_keeps_session_state_and_discards_autosave",
            target_id="project_session__test_recovery_prompt_reject_keeps_session_state_and_discards_autosave",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_recovery_prompt_is_skipped_when_autosave_matches_restored_session",
            target_id="project_session__test_recovery_prompt_is_skipped_when_autosave_matches_restored_session",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_restore_session_handles_corrupted_session_and_autosave_files",
            target_id="project_session__test_restore_session_handles_corrupted_session_and_autosave_files",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_recovery_prompt_is_deferred_until_main_window_is_visible",
            target_id="project_session__test_recovery_prompt_is_deferred_until_main_window_is_visible",
        ),
        ShellIsolationTarget.project_session_scenario(
            "test_recent_project_paths_are_owned_by_explicit_session_state",
            target_id="project_session__test_recent_project_paths_are_owned_by_explicit_session_state",
        ),
    )


def __getattr__(name: str):
    if name == "TARGETS":
        return _build_targets()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
