from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2


ACTIVE_SPEC_FILES = (
    Path("docs/URD.md"),
    Path("docs/ADD.md"),
    Path("docs/MDD.md"),
    Path("docs/TDD.md"),
    Path("docs/RMD.md"),
    Path("docs/RMD_EXECUTION_STATUS.md"),
)

FORBIDDEN_ACTIVE_TOKENS = (
    "huygens",
    "complex otf",
    "complex_otf",
    "psf_to_complex_otf",
    "vsotf",
    "vsmtf",
)


@pytest.mark.unit
def test_active_main_analysis_settings_are_fft_mtf_only() -> None:
    settings = NOMINAL_MAIN_FFT_MTF_555_V2
    settings.validate()
    assert settings.settings_id == "NOMINAL_MAIN_FFT_MTF_555_v2"
    assert settings.wavelength_nm == 555.0
    assert settings.pupils_mm == (3.0, 5.0)
    assert settings.defocus_grid() == tuple(
        round(0.5 - 0.25 * index, 10) for index in range(15)
    )
    assert settings.fft_mtf_sampling == 128
    assert settings.fft_mtf_convergence_samplings == (64, 128, 256)
    assert settings.mtfa_max_cpd == 60.0
    assert settings.mtf_frequency_step_cpd == 1.0
    assert settings.mtf_sample_frequencies_cpd == (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)
    # DOF50 is a named fixed metric definition, not a mutable settings field.
    assert not hasattr(settings, "dof_relative_fraction")
    # B0 selection has its own independent settings identity.
    assert not hasattr(settings, "b0_q_lock_max_cycles_per_mm")


def _scan(paths) -> list[str]:
    findings: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8").casefold()
        for token in FORBIDDEN_ACTIVE_TOKENS:
            if token in text:
                findings.append(f"{path}:{token}")
    return findings


@pytest.mark.unit
def test_production_source_does_not_reintroduce_removed_paths() -> None:
    findings = _scan(Path("src/whole_eye_mvp").rglob("*.py"))
    assert not findings, "removed analysis path leaked into production source: " + ", ".join(findings)


@pytest.mark.unit
def test_active_scripts_do_not_reintroduce_removed_paths() -> None:
    findings = _scan(Path("scripts").glob("*task_009*.py"))
    findings += _scan(Path("scripts").glob("*run72*.py"))
    assert not findings, "removed analysis path leaked into active scripts: " + ", ".join(findings)


@pytest.mark.unit
def test_active_specs_do_not_reintroduce_removed_paths() -> None:
    findings = _scan(ACTIVE_SPEC_FILES)
    assert not findings, "removed analysis path leaked into active specs: " + ", ".join(findings)
