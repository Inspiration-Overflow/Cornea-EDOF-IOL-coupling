from __future__ import annotations

from pathlib import Path

import pytest

from whole_eye_mvp.analysis_zos import TASK009_MTF_ACQUISITION
from whole_eye_mvp.domain import NOMINAL_MAIN_FFT_MTF_555_V2
from whole_eye_mvp.quality import assert_trace_coverage

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
FORBIDDEN_RUNTIME_TOKENS = (
    "new_fftmtf",
    "zosfftmtfanalysisbackend",
)


@pytest.mark.unit
def test_active_main_analysis_settings_and_acquisition_contract() -> None:
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
    assert not hasattr(settings, "dof_relative_fraction")
    assert not hasattr(settings, "b0_q_lock_max_cycles_per_mm")

    assert TASK009_MTF_ACQUISITION.contract_id == "TASK009_MFE_MTFA_GRID1_v1"
    assert TASK009_MTF_ACQUISITION.production_operand == "MTFA"
    assert TASK009_MTF_ACQUISITION.grid == 1
    assert TASK009_MTF_ACQUISITION.data_type == 0
    assert len(TASK009_MTF_ACQUISITION.contract_hash) == 64


def _scan(paths, tokens=FORBIDDEN_ACTIVE_TOKENS) -> list[str]:
    findings: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8").casefold()
        for token in tokens:
            if token in text:
                findings.append(f"{path}:{token}")
    return findings


@pytest.mark.unit
def test_production_source_does_not_reintroduce_removed_paths() -> None:
    paths = tuple(Path("src/whole_eye_mvp").rglob("*.py"))
    findings = _scan(paths)
    findings += _scan(paths, FORBIDDEN_RUNTIME_TOKENS)
    assert not findings, "removed analysis path leaked into production source: " + ", ".join(findings)


@pytest.mark.unit
def test_active_scripts_do_not_reintroduce_removed_paths() -> None:
    paths = tuple(Path("scripts").glob("*task_009*.py")) + tuple(Path("scripts").glob("*run72*.py"))
    findings = _scan(paths)
    findings += _scan(paths, FORBIDDEN_RUNTIME_TOKENS)
    assert not findings, "removed analysis path leaked into active scripts: " + ", ".join(findings)


@pytest.mark.unit
def test_active_specs_do_not_reintroduce_removed_paths() -> None:
    findings = _scan(ACTIVE_SPEC_FILES)
    assert not findings, "removed analysis path leaked into active specs: " + ", ".join(findings)


@pytest.mark.unit
def test_current_trace_map_covers_the_current_document_id_universe() -> None:
    trace = Path("docs/TRACE.md").read_text(encoding="utf-8")
    assert_trace_coverage(trace)
    assert "URD-0001 v1.6" in trace
    assert "ADD-0001 v1.6" in trace
    assert "MDD-0001 v1.5" in trace
    assert "TDD-0001 v1.6" in trace
