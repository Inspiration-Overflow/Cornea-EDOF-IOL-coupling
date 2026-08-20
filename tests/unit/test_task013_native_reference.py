from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.carriers import SA_TARGETS_UM, CarrierKey, ProvisionalCarrier
from whole_eye_mvp.domain import (
    CURRENT_SCIENTIFIC_BASELINE_ID,
    BaseId,
    CorneaId,
    OpticState,
    PlatformId,
    ScientificBaseline,
)
from whole_eye_mvp.model_archive import (
    ModelIndexRecord,
    archive_model,
    project_relative_path,
    validate_model_index,
    write_model_index,
)
from whole_eye_mvp.task013_native_reference import (
    NATIVE_REFERENCE_CORNEA_ID,
    TASK013_EXPECTED_CARRIER_COUNT,
    TASK013_EXPECTED_CONFIG_COUNT,
    TASK013_EXPECTED_PAIR_COUNT,
    ResidualProvenance,
    Task013Error,
    build_task013_manifest,
    make_native_carrier_lock,
    require_residual_power_envelopes,
)


def _carrier(base: str, cornea: str, platform: str, power_d: float) -> ProvisionalCarrier:
    radius = 10.0 + abs(power_d) / 10.0
    return ProvisionalCarrier(
        key=CarrierKey(base, cornea, platform),
        power_d=power_d,
        q=-1.0 if platform != str(PlatformId.HOA) else 0.0,
        q_source_power_d=power_d,
        r_ant_mm=radius,
        r_post_mm=-radius,
        center_thickness_mm=1.0,
        material="MODEL_N1460",
        iol_position_mm=4.5,
        achieved_sa_um=float(SA_TARGETS_UM[platform]),
    )


def _residual(platform: str) -> ResidualProvenance:
    return ResidualProvenance(
        platform_id=platform,
        residual_id=f"RESIDUAL_{platform}_LOCK",
        residual_sha256=f"sha-{platform}",
        residual_validation_policy_id="RESIDUAL_VALIDATION_546_V1",
        residual_validation_policy_hash="policy-sha",
    )


def _native_carriers() -> list[ProvisionalCarrier]:
    return [
        _carrier(str(base), NATIVE_REFERENCE_CORNEA_ID, str(platform), power)
        for base, power in ((BaseId.LB_AL2395, 20.0), (BaseId.ATC_M3_AL24477, 21.0))
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA)
    ]


def test_task013_is_extension_not_scientific_baseline_mutation() -> None:
    baseline = ScientificBaseline(CURRENT_SCIENTIFIC_BASELINE_ID)
    assert {str(spec.cornea_id) for spec in baseline.cornea_specs} == {
        str(CorneaId.A0),
        str(CorneaId.B0),
        str(CorneaId.C0),
    }
    assert NATIVE_REFERENCE_CORNEA_ID not in {
        str(spec.cornea_id) for spec in baseline.cornea_specs
    }


def test_task013_manifest_is_exact_6_carrier_24_config_12_pair_extension() -> None:
    locks = [
        make_native_carrier_lock(carrier, _residual(str(carrier.key.platform_id)))
        for carrier in _native_carriers()
    ]
    bundle = build_task013_manifest(locks)
    assert len(bundle.physical_carriers) == TASK013_EXPECTED_CARRIER_COUNT
    assert len(bundle.nominal_configs) == TASK013_EXPECTED_CONFIG_COUNT
    assert len({config.pair_key for config in bundle.nominal_configs}) == TASK013_EXPECTED_PAIR_COUNT
    assert {config.cornea_id for config in bundle.nominal_configs} == {NATIVE_REFERENCE_CORNEA_ID}
    assert {config.pupil_mm for config in bundle.nominal_configs} == {3.0, 5.0}
    assert {str(config.optic_state) for config in bundle.nominal_configs} == {
        str(OpticState.MONO),
        str(OpticState.EDOF),
    }
    assert all(
        config.residual_id is None
        for config in bundle.nominal_configs
        if config.optic_state == OpticState.MONO
    )
    assert all(
        config.residual_id is not None
        for config in bundle.nominal_configs
        if config.optic_state == OpticState.EDOF
    )


def test_task013_residual_power_envelope_is_fail_closed() -> None:
    existing = [
        _carrier(str(base), str(cornea), str(platform), power)
        for base, offset in ((BaseId.LB_AL2395, 0.0), (BaseId.ATC_M3_AL24477, 1.0))
        for cornea, cornea_offset in (
            (CorneaId.A0, -1.0),
            (CorneaId.B0, 0.0),
            (CorneaId.C0, 1.0),
        )
        for platform in (PlatformId.WFS, PlatformId.RAD, PlatformId.HOA)
        for power in (20.0 + offset + cornea_offset,)
    ]
    native = _native_carriers()
    checks = require_residual_power_envelopes(existing, native)
    assert len(checks) == 6
    assert all(check.passed for check in checks)

    outside = list(native)
    outside[0] = _carrier(
        str(BaseId.LB_AL2395),
        NATIVE_REFERENCE_CORNEA_ID,
        str(PlatformId.WFS),
        30.0,
    )
    with pytest.raises(Task013Error, match="additional residual replay validation"):
        require_residual_power_envelopes(existing, outside)


def test_model_archive_hashes_copy_and_index(tmp_path: Path) -> None:
    project = tmp_path / "project"
    source = project / "results" / "run" / "CFG" / "model.zmx"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"zmx-test-bytes\n")
    destination = project / "models" / "task013_native_reference" / "runs" / "run" / "configs" / "CFG.zmx"
    sha = archive_model(source, destination)
    assert destination.read_bytes() == source.read_bytes()
    assert archive_model(source, destination) == sha

    record = ModelIndexRecord(
        model_role="analyzed_config",
        run_id="run",
        config_id="CFG",
        pair_key="PAIR",
        carrier_id="CAR",
        base_id=str(BaseId.LB_AL2395),
        cornea_id=NATIVE_REFERENCE_CORNEA_ID,
        platform_id=str(PlatformId.WFS),
        optic_state=str(OpticState.MONO),
        pupil_mm=3.0,
        relative_path=project_relative_path(project, destination),
        sha256=sha,
    )
    index = project / "models" / "task013_native_reference" / "runs" / "run" / "MODEL_INDEX.csv"
    write_model_index(index, (record,))
    validate_model_index(project, (record,))
    assert index.is_file()
