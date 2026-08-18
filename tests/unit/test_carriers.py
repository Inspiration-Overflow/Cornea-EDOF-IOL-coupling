from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from whole_eye_mvp.carriers import (
    CarrierKey,
    ProvisionalCarrier,
    ResidualCalibration,
    ResidualDefinition,
    ScientificInvariantError,
    expected_carrier_keys,
    make_matched_pair,
    residuals_ready,
    validate_18_provisional_carriers,
    validate_provisional_carrier,
)
from whole_eye_mvp.domain import PlatformId


def carrier(key: CarrierKey) -> ProvisionalCarrier:
    target = {PlatformId.WFS:-.20, PlatformId.RAD:-.27, PlatformId.HOA:0.0}[key.platform_id]
    return ProvisionalCarrier(key, 20.0, -0.2, 20.0, 12.0, -12.0, 1.0, 'IOL_1.46', 4.5, target)


def residual(tmp_path: Path, platform: str, *, all_gates: bool = True) -> ResidualDefinition:
    path = tmp_path / f'{platform}.txt'; path.write_text('payload')
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    labels = ('low','median','high') if all_gates else ('low','median')
    return ResidualDefinition(f'RES_{platform}', platform, 'v1', 'radial_sag_samples', str(path), 'mm', (0.0,3.0), True, True, sha, tuple(ResidualCalibration(x,20,True,0.1) for x in labels))


@pytest.mark.unit
def test_expected_carrier_key_space_is_exactly_18() -> None:
    keys = expected_carrier_keys()
    assert len(keys) == len(set(keys)) == 18


@pytest.mark.unit
def test_power_specific_q_and_sa_target_are_enforced() -> None:
    c = carrier(expected_carrier_keys()[0])
    validate_provisional_carrier(c)
    with pytest.raises(ScientificInvariantError, match='source power'):
        validate_provisional_carrier(ProvisionalCarrier(c.key,20,c.q,19.5,c.r_ant_mm,c.r_post_mm,c.center_thickness_mm,c.material,c.iol_position_mm,c.achieved_sa_um))
    with pytest.raises(ScientificInvariantError, match='SA'):
        validate_provisional_carrier(ProvisionalCarrier(c.key,20,c.q,20,c.r_ant_mm,c.r_post_mm,c.center_thickness_mm,c.material,c.iol_position_mm,0.2))


@pytest.mark.unit
def test_residual_payload_and_three_actual_power_gates_are_required(tmp_path: Path) -> None:
    rs = [residual(tmp_path,p) for p in ('WFS','RAD','HOA')]
    assert residuals_ready(rs)
    assert not residuals_ready([residual(tmp_path,'WFS',all_gates=False), *rs[1:]])


@pytest.mark.unit
def test_formal_18_set_validation_rejects_missing_key() -> None:
    carriers = [carrier(k) for k in expected_carrier_keys()]
    validate_18_provisional_carriers(carriers)
    with pytest.raises(ScientificInvariantError, match='exactly'):
        validate_18_provisional_carriers(carriers[:-1])


@pytest.mark.unit
def test_matched_pair_reuses_same_physical_carrier(tmp_path: Path) -> None:
    c = carrier(next(k for k in expected_carrier_keys() if k.platform_id == 'WFS'))
    pair = make_matched_pair(c, residual(tmp_path,'WFS'), delta_f_residual_d=0.125)
    assert pair.carrier is c and pair.mono_residual_id is None and pair.edof_residual_id == 'RES_WFS'
    assert pair.delta_f_residual_d == 0.125
