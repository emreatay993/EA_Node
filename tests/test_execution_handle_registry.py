from __future__ import annotations

import unittest

from ea_node_editor.execution.handle_registry import HandleRegistry, StaleHandleError
from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.types import ExecutionContext, RuntimeHandleRef


class HandleRegistryTests(unittest.TestCase):
    def test_registry_tracks_ref_counts_until_final_release(self) -> None:
        registry = HandleRegistry(worker_generation=4)
        payload = object()

        handle_ref = registry.register(
            payload,
            kind="tests.payload",
            owner_scope="run:run_registry",
            metadata={"label": "demo"},
        )

        self.assertEqual(handle_ref.worker_generation, 4)
        self.assertEqual(handle_ref.metadata, {"label": "demo"})
        self.assertIs(registry.resolve(handle_ref, expected_kind="tests.payload"), payload)
        self.assertEqual(registry.ref_count(handle_ref), 1)

        retained_ref = registry.acquire(handle_ref)

        self.assertEqual(registry.ref_count(handle_ref), 2)
        self.assertFalse(registry.release(handle_ref))
        self.assertEqual(registry.ref_count(retained_ref), 1)
        self.assertTrue(registry.release(retained_ref))
        self.assertEqual(registry.active_handle_count, 0)

        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            registry.resolve(handle_ref)

    def test_registry_promotion_invalidates_previous_owner_scope_and_skips_run_cleanup(self) -> None:
        registry = HandleRegistry()
        payload = {"value": "cached"}

        run_ref = registry.register(payload, kind="tests.payload", owner_scope="run:run_cache")
        cache_ref = registry.promote(
            run_ref,
            owner_scope="cache:mesh:primary",
            metadata={"cache_key": "mesh:primary"},
        )

        self.assertEqual(cache_ref.owner_scope, "cache:mesh:primary")
        self.assertEqual(cache_ref.metadata, {"cache_key": "mesh:primary"})
        self.assertIs(registry.resolve(cache_ref), payload)
        self.assertEqual(registry.release_owner_scope("run:run_cache"), 0)

        with self.assertRaisesRegex(StaleHandleError, "owner_scope is stale"):
            registry.resolve(run_ref)

    def test_registry_reset_invalidates_generation_mismatched_refs(self) -> None:
        registry = HandleRegistry(worker_generation=2)
        handle_ref = registry.register(object(), kind="tests.payload", owner_scope="run:run_reset")
        mismatched_ref = RuntimeHandleRef(
            handle_id=handle_ref.handle_id,
            kind=handle_ref.kind,
            owner_scope=handle_ref.owner_scope,
            worker_generation=handle_ref.worker_generation + 1,
        )

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            registry.resolve(mismatched_ref)

        self.assertEqual(registry.reset(), 1)
        self.assertEqual(registry.worker_generation, 3)

        with self.assertRaisesRegex(StaleHandleError, "worker_generation is stale"):
            registry.resolve(handle_ref)


class ExecutionContextHandleTests(unittest.TestCase):
    def test_execution_context_routes_handle_apis_through_worker_services(self) -> None:
        services = WorkerServices()
        ctx = ExecutionContext(
            run_id="run_ctx",
            node_id="node_ctx",
            workspace_id="ws_main",
            inputs={},
            properties={},
            emit_log=lambda _level, _message: None,
            worker_services=services,
        )

        payload = {"value": "runtime"}
        handle_ref = ctx.register_handle(payload, kind="tests.payload")
        retained_ref = ctx.handle_ref(handle_ref)

        self.assertEqual(handle_ref.owner_scope, "run:run_ctx")
        self.assertIs(ctx.resolve_handle(handle_ref, expected_kind="tests.payload"), payload)
        self.assertEqual(services.handle_registry.ref_count(handle_ref), 2)
        self.assertFalse(ctx.release_handle(retained_ref))
        self.assertTrue(ctx.release_handle(handle_ref))

        with self.assertRaisesRegex(StaleHandleError, "stale or unknown"):
            ctx.resolve_handle(handle_ref)


if __name__ == "__main__":
    unittest.main()
