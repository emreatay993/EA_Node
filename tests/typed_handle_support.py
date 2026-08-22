from __future__ import annotations

from ea_node_editor.execution.worker_services import WorkerServices
from ea_node_editor.nodes.ansys_dpf_data_types import (
    DPF_DATA_CONVERSIONS,
    DPF_DATA_TYPE_FAMILIES,
    DPF_DATA_TYPE_OWNER_ID,
    DPF_DATA_TYPES,
)
from ea_node_editor.nodes.core_data_types import (
    CORE_DATA_CONVERSIONS,
    CORE_DATA_TYPE_FAMILIES,
    CORE_DATA_TYPE_OWNER_ID,
    CORE_DATA_TYPE_OWNER_VERSION,
    CORE_DATA_TYPES,
)
from ea_node_editor.runtime_contracts import DataTypeCatalog


def _data_type_catalog(*, include_dpf: bool) -> DataTypeCatalog:
    catalog = DataTypeCatalog()
    catalog.register_many(
        families=CORE_DATA_TYPE_FAMILIES,
        types=CORE_DATA_TYPES,
        conversions=CORE_DATA_CONVERSIONS,
        owner_id=CORE_DATA_TYPE_OWNER_ID,
        owner_version=CORE_DATA_TYPE_OWNER_VERSION,
    )
    if include_dpf:
        catalog.register_many(
            families=DPF_DATA_TYPE_FAMILIES,
            types=DPF_DATA_TYPES,
            conversions=DPF_DATA_CONVERSIONS,
            owner_id=DPF_DATA_TYPE_OWNER_ID,
        )
    catalog.freeze()
    return catalog


def core_data_type_catalog() -> DataTypeCatalog:
    return _data_type_catalog(include_dpf=False)


def dpf_data_type_catalog() -> DataTypeCatalog:
    return _data_type_catalog(include_dpf=True)


def _worker_services(*, include_dpf: bool) -> WorkerServices:
    services = WorkerServices()
    services.bind_data_types(_data_type_catalog(include_dpf=include_dpf))
    return services


def core_worker_services() -> WorkerServices:
    return _worker_services(include_dpf=False)


def dpf_worker_services() -> WorkerServices:
    return _worker_services(include_dpf=True)


__all__ = [
    "core_data_type_catalog",
    "core_worker_services",
    "dpf_data_type_catalog",
    "dpf_worker_services",
]
