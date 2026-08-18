from __future__ import annotations

import pytest

from whole_eye_mvp.acceptance import AcceptanceError, RepeatabilityPoint, ResultEnvelope, validate_nominal_acceptance, validate_repeatability
from whole_eye_mvp.carriers import ProvisionalCarrier, expected_carrier_keys
from whole_eye_mvp.domain import PlatformId
from whole_eye_mvp.manifest import CarrierLock, build_manifests


def bundle():
    locks=[]
    for i,key in enumerate(expected_carrier_keys()):
        target={PlatformId.WFS:-.20,PlatformId.RAD:-.27,PlatformId.HOA:0.0}[key.platform_id]
        c=ProvisionalCarrier(key,20+i*.01,-.2,20+i*.01,12,-12,1,'IOL',4.5,target)
        locks.append(CarrierLock(c,f'RES_{key.platform_id}',.1,f'h{i}'))
    return build_manifests(locks)


@pytest.mark.unit
def test_nominal_acceptance_requires_72_36_1080_exactly() -> None:
    b=bundle(); rows=[ResultEnvelope(c.config_id,c.pair_key,True,15) for c in b.nominal_configs]
    pairs=sorted({c.pair_key for c in b.nominal_configs}); summary=validate_nominal_acceptance(rows,pairs)
    assert (summary.completed_configs,summary.matched_pairs,summary.through_focus_rows)==(72,36,1080)
    with pytest.raises(AcceptanceError,match='72'):
        validate_nominal_acceptance(rows[:-1],pairs)


@pytest.mark.unit
def test_duplicate_and_missing_pair_are_rejected() -> None:
    b=bundle(); rows=[ResultEnvelope(c.config_id,c.pair_key,True,15) for c in b.nominal_configs]
    pairs=sorted({c.pair_key for c in b.nominal_configs})
    with pytest.raises(AcceptanceError,match='duplicate'):
        validate_nominal_acceptance(rows[:-1]+[rows[0]],pairs)
    with pytest.raises(AcceptanceError,match='36'):
        validate_nominal_acceptance(rows,pairs[:-1])


@pytest.mark.unit
def test_repeatability_tolerances() -> None:
    a={'x':RepeatabilityPoint(.5,.4,.1,.02,0.0)}; b={'x':RepeatabilityPoint(.5004,.4003,.1005,.0205,0.0)}
    validate_repeatability(a,b)
    with pytest.raises(AcceptanceError,match='mtfa'):
        validate_repeatability(a,{'x':RepeatabilityPoint(.51,.4,.1,.02,0.0)})
    with pytest.raises(AcceptanceError,match='distance'):
        validate_repeatability(a,{'x':RepeatabilityPoint(.5,.4,.1,.02,.25)})
