# Purpose: Request built-in worker warm-up after the first usable shell frame.
# Map: subsystems/startup_and_bootstrap.md
# Tests: tests/test_generation_readiness.py, tests/test_shell_submission.py
from __future__ import annotations

from PyQt6.QtCore import QObject, Qt, pyqtSlot


class StartupWorkerWarmup(QObject):
    def __init__(self, host) -> None:
        super().__init__(host)
        self._host = host
        self._started = False
        self.enabled = True
        self.future = None
        self._quick_window = host.qml_host.quick_window()
        self._quick_window.afterRendering.connect(
            self._after_frame, Qt.ConnectionType.QueuedConnection
        )

    @pyqtSlot()
    def _after_frame(self) -> None:
        host = self._host
        if self._started or host._shell_teardown_started or not host.isVisible():
            return
        handle = host.windowHandle()
        if handle is None or not handle.isExposed():
            return
        self._started = True
        self._quick_window.afterRendering.disconnect(self._after_frame)
        if (
            not self.enabled
            or host.run_state.active_run_id
            or host.run_state.active_submission_id
        ):
            return
        # Capture UI-owned configuration here. Background readiness receives
        # only the runtime's already-published immutable registry.
        if host.app_preferences_controller.default_python_executable():
            return
        environment = host.project_session_controller.workflow_settings_payload().get(
            "environment", {}
        )
        if environment.get("python_path"):
            return
        warm_up = getattr(host.execution_client, "warm_up_builtin_generation", None)
        if callable(warm_up):
            self.future = warm_up()
