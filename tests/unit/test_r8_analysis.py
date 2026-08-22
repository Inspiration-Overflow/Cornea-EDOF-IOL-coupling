from __future__ import annotations

import pytest

from whole_eye_mvp.r8_analysis import (
    R8_BASE_IDS,
    R8_CORNEA_IDS,
    R8_PLATFORM_IDS,
    R8_PUPIL_MM,
    R8AnalysisError,
    build_coupling_matrix,
    build_n0_interactions,
    build_pairs,
    validate_factorial,
)
from whole_eye_mvp.run72_analysis import ConfigSummary, FactorKey


def _configs() -> tuple[ConfigSummary, ...]:
    rows: list[ConfigSummary] = []
    for base in R8_BASE_IDS:
        for cornea in R8_CORNEA_IDS:
            for platform in R8_PLATFORM_IDS:
                for pupil in R8_PUPIL_MM:
                    factors = FactorKey(base, cornea, platform, pupil)
                    pair_key = "|".join((base, cornea, platform, str(pupil)))
                    for state in ("MONO", "EDOF"):
                        width = 1.0 if state == "MONO" else 1.25
                        rows.append(
                            ConfigSummary(
                                run_id="test",
                                config_id=f"{pair_key}|{state}",
                                pair_key=pair_key,
                                carrier_id=f"{base}|{cornea}",
                                factors=factors,
                                optic_state=state,
                                distance_peak_retina_d=0.0,
                                distance_peak_mtfa=0.0,
                                mtfa_at_zero_d=0.5 if state == "MONO" else 0.4,
                                dof50_width_d=width,
                                dof50_far_censored=False,
                                dof50_near_censored=False,
                                tf_mtfa_mean=0.3 if state == "MONO" else 0.2,
                                peak_search_censored=False,
                                c40_um=0.1 if state == "MONO" else 0.08,
                                c60_um=0.1,
                                hoa_rms_um=0.2 if state == "MONO" else 0.25,
                            )
                        )
    return tuple(rows)


def test_r8_factorial_builds_pairs_interactions_and_cells() -> None:
    configs = _configs()
    validate_factorial(configs)
    pairs = build_pairs(configs)

    assert len(pairs) == 48
    assert len(build_n0_interactions(pairs)) == 288
    assert len(build_coupling_matrix(pairs)) == 12
    assert {pair.dof50_effect_status for pair in pairs} == {"exact"}


def test_r8_factorial_rejects_missing_config() -> None:
    with pytest.raises(R8AnalysisError, match="factor coverage|optic-state"):
        validate_factorial(_configs()[:-1])
