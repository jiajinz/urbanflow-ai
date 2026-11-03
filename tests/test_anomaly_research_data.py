"""Pinned, portable research integrity and parsing tests; no network or fitting."""

from io import BytesIO
import os
from pathlib import Path
import shutil

import pandas as pd
import pytest

import urbanflow_ai.anomaly_research_data as data
from urbanflow_ai.data_access import DataAccessError


@pytest.fixture(scope="module")
def payloads():
    return data.verified_payloads()


@pytest.fixture(scope="module")
def bundle(payloads):
    return data.parse_bundle(payloads)


def test_pinned_inventory_and_normalized_public_lineage(bundle):
    assert (
        len(bundle.daily),
        len(bundle.cases),
        len(bundle.health),
        len(bundle.episodes),
    ) == (11200, 763, 11200, 200)
    assert bundle.provenance["prospective_validation_executed"] is False
    assert "NO-GO" in bundle.provenance["operational_readiness"]
    assert all(not key.startswith("/") for key in bundle.provenance["source_sha256"])


def test_portable_root_and_no_absolute_manifest_reads(payloads, tmp_path):
    for name, value in payloads.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    bundle = data.load_research_bundle(tmp_path)
    assert len(bundle.cases) == 763
    assert (
        data.load_research_bundle(Path(os.path.relpath(tmp_path))).provenance
        == bundle.provenance
    )


def test_missing_corrupt_pinned_manifest_and_unknown_version(tmp_path):
    with pytest.raises(DataAccessError, match="missing or incompatible"):
        data.verified_payloads(tmp_path)
    target = tmp_path / (data.C + "/manifest.json")
    target.parent.mkdir(parents=True)
    target.write_text("{}")
    with pytest.raises(DataAccessError, match="checksum"):
        data.verified_payloads(tmp_path)
    with pytest.raises(DataAccessError, match="version"):
        data.verified_payloads(version_id="unknown")


def test_source_change_cannot_hide_behind_cached_frames(payloads, tmp_path):
    from urbanflow_ai.anomaly_research_ui import cached_research

    for name, value in payloads.items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(value)
    before = data.verified_payloads(tmp_path)
    cached_research(before)
    path = tmp_path / (data.C + "/cases.csv")
    stamp = path.stat()
    content = path.read_bytes()
    path.write_bytes(content.replace(b"244454", b"244455", 1))
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
    with pytest.raises(DataAccessError, match="checksum"):
        cached_research(data.verified_payloads(tmp_path))


def test_path_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / "research-outside.txt"
    outside.write_text("untrusted")
    (tmp_path / "escaped").symlink_to(outside)
    with pytest.raises(DataAccessError, match="escapes"):
        data._read(tmp_path, "escaped")
    with pytest.raises(DataAccessError, match="escapes"):
        data._read(tmp_path, "../research-outside.txt")


def changed_table(payloads, name, callback):
    key = {
        "daily": data.B + "/daily.csv",
        "cases": data.C + "/cases.csv",
        "health": data.C + "/model_health.csv",
        "episodes": data.C + "/episode_registry.csv",
    }[name]
    frame = pd.read_csv(BytesIO(payloads[key]), keep_default_na=False)
    callback(frame)
    return {**payloads, key: frame.to_csv(index=False).encode()}


@pytest.mark.parametrize(
    "kind",
    [
        "schema",
        "boolean",
        "duplicate",
        "model",
        "score",
        "candidate",
        "case_direction",
        "episode",
        "health",
        "prior",
        "cross",
    ],
)
def test_semantic_contracts_even_after_byte_verification(payloads, kind):
    if kind == "schema":
        edited = changed_table(
            payloads,
            "daily",
            lambda f: f.rename(columns={"observed": "invented"}, inplace=True),
        )
    else:
        name, column, value = {
            "boolean": ("daily", "candidate", "false"),
            "duplicate": ("daily", "date", "2019-01-02"),
            "model": ("daily", "model", "unknown"),
            "score": ("daily", "score", 999),
            "candidate": ("daily", "candidate", True),
            "case_direction": ("cases", "actual_direction", "equal"),
            "episode": ("cases", "episode_id", "missing"),
            "health": ("health", "health_status", "healthy"),
            "prior": (
                "cases",
                "prior_comparable_observations",
                '[{"date":"2099-01-01","observed":1}]',
            ),
            "cross": ("cases", "cross_mode_observed", 1),
        }[kind]
        edited = changed_table(
            payloads,
            name,
            lambda f: f.__setitem__(column, f[column].where(f.index != 0, value)),
        )
    with pytest.raises(DataAccessError):
        data.parse_bundle(edited)
