from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2


ACTIVE_POLICY_FILES = (
    Path("docs/URD.md"),
    Path("docs/ADD.md"),
    Path("docs/MDD.md"),
    Path("docs/TDD.md"),
    Path("docs/RMD.md"),
    Path("docs/RMD_EXECUTION_STATUS.md"),
    Path("src/whole_eye_mvp/domain.py"),
    Path("src/whole_eye_mvp/metrics.py"),
    Path("src/whole_eye_mvp/analysis.py"),
)

FORBIDDEN_ACTIVE_TOKENS = (
    "Huygens PSF",
    "Huygens MTF",
    "AS_Huygens",
    "psf_to_complex_otf",
    "vsotf",
    "VSOTF",
    "VSMTF",
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
    assert settings.dof_relative_fraction == 0.5
    assert settings.mtf_sample_frequencies_cpd == (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)


@pytest.mark.unit
def test_active_source_and_specs_do_not_reintroduce_removed_main_paths() -> None:
    findings: list[str] = []
    for path in ACTIVE_POLICY_FILES:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN_ACTIVE_TOKENS:
            if token in text:
                findings.append(f"{path}:{token}")
    assert not findings, "removed main-analysis path leaked into active files: " + ", ".join(findings)
