from __future__ import annotations

import hashlib
import importlib.util
import math
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import whole_eye_mvp.analysis_zos_r8_direct as direct
from whole_eye_mvp.analysis_zos_pair_scale import PairAngularScaleReference
from whole_eye_mvp.analysis_zos_r8_direct import (
    DIRECT_BINARY4_CARRIER_POWER_DIAGNOSTIC_D,
    DIRECT_MODEL_PROVENANCE_POLICY_ID,
    R8_CONFIG_REQUIRED_COLUMNS,
    R8_PAIRED_REQUIRED_COLUMNS,
    R8_THROUGH_FOCUS_REQUIRED_COLUMNS,
    R8DirectAcquisitionError,
    build_direct_model_specs,
    capture_direct_entity_snapshot,
    group_direct_pairs,
    nominal_config_for_direct_model,
    validate_aggregate_rows,
    validate_pair_reference_map,
    verify_direct_model_sources,
)
from whole_eye_mvp.metrics import mm_per_degree

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "run_model_revision_r8_96.py"
)
R6_RELATIVE = Path("diagnostics/model_revision/r6_r7")


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_model_revision_r8_96_direct_tests", SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


r8 = _load_runner()


def _hashes(plan):
    return {
        key: f"{index + 1:064x}"[-64:]
        for index, key in enumerate(sorted({row.model_artifact_key for row in plan}))
    }


def test_direct_model_mapping_and_physical_stop_are_exact(tmp_path: Path) -> None:
    plan = r8.build_r8_plan()
    specs = build_direct_model_specs(
        tmp_path,
        plan,
        _hashes(plan),
        r6_r7_output_relative=R6_RELATIVE,
    )
    assert len(specs) == 96
    assert len({item.source_path for item in specs}) == 48
    assert {item.stop_semi_diameter_mm for item in specs} == {1.5, 2.5}
    for item in specs:
        assert item.source_path == (
            tmp_path / R6_RELATIVE / item.model_artifact_key
        ).resolve()


def test_direct_pair_grouping_and_compatibility_metadata(tmp_path: Path) -> None:
    plan = r8.build_r8_plan()
    specs = build_direct_model_specs(
        tmp_path,
        plan,
        _hashes(plan),
        r6_r7_output_relative=R6_RELATIVE,
    )
    pairs = group_direct_pairs(specs)
    assert len(pairs) == 48
    for pair in pairs:
        pair.validate()
        mono = nominal_config_for_direct_model(pair.mono)
        edof = nominal_config_for_direct_model(pair.edof)
        assert mono.pair_key == edof.pair_key == pair.pair_key
        assert mono.carrier_lock_hash == edof.carrier_lock_hash
        assert mono.residual_id is None
        assert edof.residual_id == r8.R5_2_FREEZE_ID
        assert edof.residual_validation_policy_id == DIRECT_MODEL_PROVENANCE_POLICY_ID


def test_pair_reference_map_is_exact_and_uses_one_mono_scale_per_pair(
    tmp_path: Path,
) -> None:
    plan = r8.build_r8_plan()
    specs = build_direct_model_specs(
        tmp_path,
        plan,
        _hashes(plan),
        r6_r7_output_relative=R6_RELATIVE,
    )
    pairs = group_direct_pairs(specs)
    references = {
        pair.pair_key: PairAngularScaleReference(
            pair_key=pair.pair_key,
            mono_config_id=pair.mono.config_id,
            reference_effl_mm=16.0,
            mm_per_degree=mm_per_degree(16.0),
            model_sha256="a" * 64,
            entity_fingerprint="b" * 64,
        )
        for pair in pairs
    }
    validate_pair_reference_map(pairs, references)

    first = pairs[0]
    broken = dict(references)
    broken[first.pair_key] = replace(
        references[first.pair_key],
        mono_config_id="wrong",
    )
    with pytest.raises(R8DirectAcquisitionError, match="MONO config mismatch"):
        validate_pair_reference_map(pairs, broken)


def _blank_row(columns):
    return {column: "" for column in columns}


def test_aggregate_schema_and_exact_output_cardinality() -> None:
    config_rows = []
    tf_rows = []
    paired_rows = []
    for index in range(96):
        config_id = f"CFG_{index:03d}"
        pair_key = f"PAIR_{index // 2:02d}"
        row = _blank_row(R8_CONFIG_REQUIRED_COLUMNS)
        row["config_id"] = config_id
        row["pair_key"] = pair_key
        config_rows.append(row)
        for plane in range(15):
            tf = _blank_row(R8_THROUGH_FOCUS_REQUIRED_COLUMNS)
            tf["config_id"] = config_id
            tf["pair_key"] = pair_key
            tf["defocus_retina_d"] = 0.50 - 0.25 * plane
            tf_rows.append(tf)
    for index in range(48):
        row = _blank_row(R8_PAIRED_REQUIRED_COLUMNS)
        row["pair_key"] = f"PAIR_{index:02d}"
        row["mono_config_id"] = f"CFG_{2 * index:03d}"
        row["edof_config_id"] = f"CFG_{2 * index + 1:03d}"
        paired_rows.append(row)

    validate_aggregate_rows(config_rows, tf_rows, paired_rows)
    with pytest.raises(R8DirectAcquisitionError, match="through-focus row count mismatch"):
        validate_aggregate_rows(config_rows, tf_rows[:-1], paired_rows)


def test_source_verification_fails_closed_on_missing_or_hash_drift(tmp_path: Path) -> None:
    plan = r8.build_r8_plan()
    specs = build_direct_model_specs(
        tmp_path,
        plan,
        _hashes(plan),
        r6_r7_output_relative=R6_RELATIVE,
    )
    with pytest.raises(R8DirectAcquisitionError, match="source is missing"):
        verify_direct_model_sources(specs)

    unique = {item.model_artifact_key: item for item in specs}
    for item in unique.values():
        item.source_path.parent.mkdir(parents=True, exist_ok=True)
        item.source_path.write_bytes(item.model_artifact_key.encode("utf-8"))

    actual_specs = tuple(
        replace(
            item,
            source_sha256=hashlib.sha256(item.source_path.read_bytes()).hexdigest(),
        )
        for item in specs
    )
    verify_direct_model_sources(actual_specs)

    first = actual_specs[0]
    first.source_path.write_bytes(b"drift")
    with pytest.raises(R8DirectAcquisitionError, match="source hash mismatch"):
        verify_direct_model_sources(actual_specs)


class _FakeSurface:
    def __init__(
        self,
        *,
        comment: str,
        radius: float,
        conic: float,
        thickness: float,
        material: str = "",
        is_stop: bool = False,
        semi_diameter: float = 3.0,
        type_name: str = "Standard",
    ) -> None:
        self.Comment = comment
        self.Radius = radius
        self.Conic = conic
        self.Thickness = thickness
        self.Material = material
        self.IsStop = is_stop
        self.SemiDiameter = semi_diameter
        self.TypeName = type_name

    def GetType(self) -> str:
        return self.TypeName


class _FakeLde:
    NumberOfSurfaces = 7
    StopSurface = 3

    def __init__(self, surfaces: dict[int, _FakeSurface]) -> None:
        self.surfaces = surfaces

    def GetSurfaceAt(self, index: int) -> _FakeSurface:
        return self.surfaces[index]


def _fake_snapshot_session():
    surfaces = {
        0: _FakeSurface(comment="OBJECT", radius=0.0, conic=0.0, thickness=1.0e9),
        1: _FakeSurface(comment="CORNEA_ANT", radius=7.8, conic=-0.2, thickness=0.55),
        2: _FakeSurface(
            comment=direct.FIXED_CORNEA_POST_ROLE,
            radius=6.5,
            conic=-0.1,
            thickness=3.15,
        ),
        3: _FakeSurface(
            comment=direct.STOP_ROLE,
            radius=0.0,
            conic=0.0,
            thickness=1.35,
            is_stop=True,
            semi_diameter=1.5,
        ),
        4: _FakeSurface(
            comment=direct.TASK007_CARRIER_ANT_ROLE,
            radius=0.0,
            conic=0.0,
            thickness=1.0,
            material="IOL",
            type_name="Binary 4",
        ),
        5: _FakeSurface(
            comment=direct.TASK007_CARRIER_POST_ROLE,
            radius=-12.0,
            conic=0.0,
            thickness=16.0,
            material="VITREOUS",
        ),
        6: _FakeSurface(
            comment=direct.IMAGE_ROLE,
            radius=-12.0,
            conic=0.0,
            thickness=0.0,
            semi_diameter=5.0,
        ),
    }
    session = SimpleNamespace(system=SimpleNamespace(LDE=_FakeLde(surfaces)))
    return session, surfaces


def _fake_binary4_zones():
    return [
        SimpleNamespace(
            zone=1,
            r_inner_mm=0.0,
            r_outer_mm=0.9,
            radius_mm=12.3,
            conic=-0.1,
            diffraction_order=0.0,
            alpha_p2_native=0.0,
            alpha_p4_native=0.001,
            alpha_p6_native=0.002,
        ),
        SimpleNamespace(
            zone=2,
            r_inner_mm=0.9,
            r_outer_mm=3.0,
            radius_mm=12.3,
            conic=-0.1,
            diffraction_order=0.0,
            alpha_p2_native=0.0,
            alpha_p4_native=-0.001,
            alpha_p6_native=-0.002,
        ),
    ]


def test_direct_binary4_snapshot_excludes_object_and_requested_stop(monkeypatch) -> None:
    session, surfaces = _fake_snapshot_session()
    zones = _fake_binary4_zones()

    def fake_read_binary4_zones(session_arg, platform_id, *, standard_eye):
        assert session_arg is session
        assert platform_id == "WFS"
        assert standard_eye is False
        return tuple(zones)

    monkeypatch.setattr(direct, "_read_binary4_zones", fake_read_binary4_zones)
    first = capture_direct_entity_snapshot(session, "WFS")
    assert first.carrier_power_d == DIRECT_BINARY4_CARRIER_POWER_DIAGNOSTIC_D == 0.0
    assert math.isfinite(first.carrier_power_d)

    surfaces[0].Thickness = 250.0
    surfaces[3].SemiDiameter = 2.5
    second = capture_direct_entity_snapshot(session, "WFS")
    assert second.fingerprint == first.fingerprint
    assert second.retina_position_mm == first.retina_position_mm
    assert second.iol_position_mm == first.iol_position_mm
    assert second.elp_mm == first.elp_mm


def test_direct_binary4_snapshot_detects_zone_and_surface_mutation(monkeypatch) -> None:
    session, surfaces = _fake_snapshot_session()
    zones = _fake_binary4_zones()
    monkeypatch.setattr(
        direct,
        "_read_binary4_zones",
        lambda *_args, **_kwargs: tuple(zones),
    )
    baseline = capture_direct_entity_snapshot(session, "WFS")

    zones[0].alpha_p6_native += 1.0e-6
    zone_changed = capture_direct_entity_snapshot(session, "WFS")
    assert zone_changed.fingerprint != baseline.fingerprint

    zones[0].alpha_p6_native -= 1.0e-6
    surfaces[5].Thickness += 0.01
    surface_changed = capture_direct_entity_snapshot(session, "WFS")
    assert surface_changed.fingerprint != baseline.fingerprint
    assert surface_changed.retina_position_mm != baseline.retina_position_mm
