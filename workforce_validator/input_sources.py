from __future__ import annotations

from typing import Any

from workforce_validator.adapters import BundleAdapter
from workforce_validator.config import SETTINGS, ValidatorSettings
from workforce_validator.engine import run_canonical_validation, run_validation as run_current_validation
from workforce_validator.multi_file import combine_planning_documents as combine_current_documents
from workforce_validator.schedule_sources import detect_schedule_sources as detect_current_sources


def is_bundle_data(data: dict[str, Any]) -> bool:
    if not isinstance(data, dict):
        return False
    return (
        isinstance(data.get("config"), dict)
        and isinstance(data.get("people"), dict)
        and isinstance(data.get("times"), dict)
        and isinstance((data.get("times") or {}).get("storeDayTimes"), list)
    )


def combine_planning_inputs(documents: list[dict[str, Any]]) -> dict[str, Any]:
    """Accept one consolidated bundle or the legacy one/two-file input."""
    if not documents:
        raise ValueError("No se ha recibido ningun fichero de planificacion.")
    bundle_flags = [is_bundle_data(document) for document in documents]
    if any(bundle_flags):
        if len(documents) != 1 or not all(bundle_flags):
            raise ValueError(
                "El bundle consolidado debe cargarse como un unico fichero y no puede "
                "mezclarse con planificaciones del formato anterior."
            )
        BundleAdapter(documents[0])
        return documents[0]
    return combine_current_documents(documents)


def detect_input_schedule_sources(data: dict[str, Any]):
    if not is_bundle_data(data):
        return detect_current_sources(data)
    times = data.get("times") or {}
    return detect_current_sources({"storeDayTimes": times.get("storeDayTimes") or []})


def run_input_validation(
    data: dict[str, Any],
    schedule_source: str = "plannedDraft",
    manual_edit_filter: str = "all",
    settings: ValidatorSettings = SETTINGS,
):
    if not is_bundle_data(data):
        return run_current_validation(
            data, schedule_source, manual_edit_filter, settings
        )
    dataset = BundleAdapter(data, settings).build_canonical_dataset(
        schedule_source, manual_edit_filter
    )
    store_id = ((data.get("config") or {}).get("store") or {}).get("id")
    source_data = {
        "store": {"id": store_id},
        "_input_kind": "bundle",
        "_bundle_metadata": data.get("_metadata") or {},
    }
    return run_canonical_validation(dataset, source_data=source_data, settings=settings)
