from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from whole_eye_mvp.analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    ThroughFocusRow,
)
from whole_eye_mvp.carriers import (
    ProvisionalCarrier,
    ResidualCalibration,
    ResidualDefinition,
    ScientificInvariantError,
    expected_carrier_keys,
)
from whole_eye_mvp.domain import NOMINAL_MAIN_555_V1, PlatformId
from whole_eye_mvp.manifest import CarrierLock, build_manifests
from whole_eye_mvp.workflows import (
    export_manifest_bundle,
    finalize_carrier_locks,
    rerun_failed,
    run_analysis_batch,
)


def carrier(key, index: int) -> ProvisionalCarrier:
    target = {PlatformId.WFS: -0.20, PlatformId.RAD: -0.27, PlatformId.HOA: 0.0}[
        key.platform_id
    ]
    return ProvisionalCarrier(
        key,
        20 + index * 0.01,
        -0.2,
        20 + index * 0.01,
        12,
        -12,
        1,
        "IOL",
        4.5,
        target,
    )


def residual(tmp_path: Path, platform: str) -> ResidualDefinition:
    path = tmp_path / f"{platform}.dat"
    path.write_text(platform, encoding="utf-8")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    calibrations = tuple(
        ResidualCalibration(label, power, True, 0.05)
        for label, power in (("low", 18), ("median", 20), ("high", 22))
    )
    return ResidualDefinition(
        f"RES_{platform}",
        platform,
        "v1",
        "radial_sag_samples",
        str(path),
        "mm",
        (0, 3),
        True,
        True,
        sha,
        calibrations,
    )


@pytest.mark.unit
def test_formal_locks_require_all_gates_and_delta_f_map(tmp_path: Path) -> None:
    carriers = [carrier(key, i) for i, key in enumerate(expected_carrier_keys())]
    residuals = [residual(tmp_path, platform) for platform in ("WFS", "RAD", "HOA")]
    deltas = {c.key.carrier_id: 0.1 for c in carriers}
    locks = finalize_carrier_locks(carriers, residuals, deltas)
    assert len(locks) == 18
    assert len({lock.lock_hash for lock in locks}) == 18
    with pytest.raises(ScientificInvariantError, match="delta-F"):
        finalize_carrier_locks(carriers, residuals, {})
    with pytest.raises(ScientificInvariantError, match="residuals"):
        finalize_carrier_locks(carriers, residuals[:-1], deltas)


@pytest.mark.unit
def test_export_manifest_writes_exact_18_and_72_csv_rows(tmp_path: Path) -> None:
    locks = []
    for i, key in enumerate(expected_carrier_keys()):
        locks.append(CarrierLock(carrier(key, i), f"RES_{key.platform_id}", 0.1, f"hash-{i}"))
    bundle = build_manifests(locks)
    paths = export_manifest_bundle(bundle, tmp_path)
    with open(paths.physical_carriers_csv, encoding="utf-8", newline="") as handle:
        assert len(list(csv.DictReader(handle))) == 18
    with open(paths.nominal_72_csv, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
        assert len(rows) == 72
        assert len({row["config_id"] for row in rows}) == 72
    assert Path(paths.manifest_hash_file).read_text(encoding="utf-8").strip() == bundle.manifest_hash


def fake_result(config, output: Path) -> ConfigResult:
    output.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []
    for name in ("model.zos", "tf.png", "mtf.png", "p1.png", "p2.png", "p3.png"):
        path = output / name
        path.write_text("x", encoding="utf-8")
        paths.append(str(path))
    rows = tuple(
        ThroughFocusRow(d, d, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5)
        for d in NOMINAL_MAIN_555_V1.defocus_grid()
    )
    return ConfigResult(
        config,
        "backend-run",
        rows,
        0.0,
        AberrationSummary(0.1, 0.02, 0.1),
        5,
        3,
        5,
        6,
        "h",
        "h",
        23.95,
        23.95,
        ConfigArtifacts(paths[0], paths[1], paths[2], tuple(paths[3:])),
        True,
    )


class FakeBackend:
    def __init__(self, fail_id=None):
        self.fail_id = fail_id
        self.called: list[str] = []

    def run_config(self, config, output_dir):
        self.called.append(config.config_id)
        if config.config_id == self.fail_id:
            raise RuntimeError("injected export failure")
        return fake_result(config, output_dir)


@pytest.mark.unit
def test_analysis_batch_isolates_failure_and_reruns_only_failed(tmp_path: Path) -> None:
    locks = [
        CarrierLock(carrier(key, i), f"RES_{key.platform_id}", 0.1, f"h{i}")
        for i, key in enumerate(expected_carrier_keys())
    ]
    manifest = build_manifests(locks).nominal_configs[:3]
    backend = FakeBackend(fail_id=manifest[1].config_id)
    first = run_analysis_batch(backend, manifest, tmp_path)
    assert len(first.completed) == 2
    assert len(first.failed) == 1

    rerun_backend = FakeBackend()
    second = rerun_failed(rerun_backend, manifest, first, tmp_path)
    assert second.run_id != first.run_id
    assert rerun_backend.called == [manifest[1].config_id]
    assert len(second.completed) == 1
    assert not second.failed
