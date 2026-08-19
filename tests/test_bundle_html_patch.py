from __future__ import annotations

import base64
import gzip
import sys
from pathlib import Path


SCRIPTS = Path("scripts").resolve()
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_distributable_html import patched_payload, read_payload  # noqa: E402
from bundle_html_patch import patch_bundle_source  # noqa: E402


def _reference_html() -> str:
    return gzip.decompress(base64.b64decode(read_payload())).decode("utf-8")


def test_bundle_patch_composes_against_reference_html():
    source = patch_bundle_source(_reference_html())

    assert "function isBundleData(data)" in source
    assert "function bundlePeopleIndex(data)" in source
    assert "function bundleApplicableHours" in source
    assert "function extractBundleData(data, scheduleSource)" in source
    assert "function collectInputDataDates(data)" in source
    assert "function bundleDocumentInfo(data, filename)" in source
    assert "function combinePlanningInputs(entries)" in source
    assert "D.isBundleData(entry.data)" in source
    assert "S.inputKind=combined.inputKind" in source
    assert "El bundle consolidado debe cargarse como un único fichero" in source


def test_full_distributable_patch_chain_keeps_bundle_and_existing_features():
    payload, source_bytes = patched_payload(read_payload())
    source = source_bytes.decode("utf-8")

    assert payload
    assert "function extractBundleData(data, scheduleSource)" in source
    assert "function combinePlanningInputs(entries)" in source
    assert 'id="wkendReqFull"' in source
    assert "Mix de plantilla" in source
    assert "wfv-workforce-insights-style" in source
    assert "wkNeutralizeAbs" in source
    assert "wfv-collapsible-sidebar-style" in source


def test_bundle_patch_preserves_legacy_entry_contract():
    source = patch_bundle_source(_reference_html())

    assert "function planningDocumentInfo(data, filename)" in source
    assert "function combinePlanningDocuments(entries)" in source
    assert 'if(months.length!==1)' in source
    assert 'return {...combined,inputKind:"legacy"};' in source
