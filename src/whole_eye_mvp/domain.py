from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from enum import StrEnum
from typing import Any


class BaseId(StrEnum):
    LB_AL2395 = "LB_AL2395"
    ATC_M3_AL24477 = "ATC_M3_AL24477"


class CorneaId(StrEnum):
    A0 = "A0"
    B0 = "B0"
    C0 = "C0"


class PlatformId(StrEnum):
    WFS = "WFS"
    RAD = "RAD"
    HOA = "HOA"


class OpticState(StrEnum):
    MONO = "MONO"
    EDOF = "EDOF"


class RunStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AnalysisSettings:
    """Frozen main-analysis settings that materially affect FFT-MTF/MTFa results.

    TASK-009 intentionally keeps B0-lock and Zernike-acquisition settings out of this
    identity. Those acquisitions have separate versioned contracts and therefore cannot
    silently change the Run72 FFT-MTF settings hash.
    """

    settings_id: str
    wavelength_nm: float
    pupils_mm: tuple[float, ...]
    defocus_start_d: float
    defocus_stop_d: float
    defocus_step_d: float
    fft_mtf_sampling: int = 128
    fft_mtf_convergence_samplings: tuple[int, ...] = (64, 128, 256)
    fft_mtf_use_polarization: bool = False
    mtf_frequency_step_cpd: float = 1.0
    mtfa_max_cpd: float = 60.0
    mtf_sample_frequencies_cpd: tuple[float, ...] = (10.0, 20.0, 30.0, 40.0, 50.0, 60.0)

    def validate(self) -> None:
        if not self.settings_id.strip():
            raise ValueError("settings_id is required")
        scalar_values = (
            self.wavelength_nm,
            self.defocus_start_d,
            self.defocus_stop_d,
            self.defocus_step_d,
            self.mtf_frequency_step_cpd,
            self.mtfa_max_cpd,
        )
        if not all(math.isfinite(float(value)) for value in scalar_values):
            raise ValueError("analysis settings must contain only finite numeric values")
        if not self.pupils_mm or not all(
            math.isfinite(float(pupil)) and pupil > 0 for pupil in self.pupils_mm
        ):
            raise ValueError("pupils must be finite and positive")
        if self.wavelength_nm <= 0:
            raise ValueError("wavelength must be positive")
        if self.defocus_step_d == 0:
            raise ValueError("defocus_step_d must not be zero")
        if self.defocus_start_d > self.defocus_stop_d and self.defocus_step_d > 0:
            raise ValueError("defocus step direction does not reach stop")
        if self.defocus_start_d < self.defocus_stop_d and self.defocus_step_d < 0:
            raise ValueError("defocus step direction does not reach stop")
        if self.fft_mtf_sampling <= 0:
            raise ValueError("FFT MTF sampling must be positive")
        if not self.fft_mtf_convergence_samplings or not all(
            isinstance(value, int) and value > 0 for value in self.fft_mtf_convergence_samplings
        ):
            raise ValueError("FFT MTF convergence samplings must be positive integers")
        if self.fft_mtf_sampling not in self.fft_mtf_convergence_samplings:
            raise ValueError("production FFT MTF sampling must be included in convergence samplings")
        if tuple(sorted(set(self.fft_mtf_convergence_samplings))) != self.fft_mtf_convergence_samplings:
            raise ValueError("FFT MTF convergence samplings must be unique and increasing")
        if self.mtf_frequency_step_cpd <= 0 or self.mtfa_max_cpd <= 0:
            raise ValueError("MTF frequency settings must be positive")
        ratio = self.mtfa_max_cpd / self.mtf_frequency_step_cpd
        if not math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("MTF cpd step must divide MTFa maximum exactly")
        if not self.mtf_sample_frequencies_cpd or not all(
            math.isfinite(float(frequency)) and 0 < frequency <= self.mtfa_max_cpd
            for frequency in self.mtf_sample_frequencies_cpd
        ):
            raise ValueError("MTF sample frequencies must be finite and inside the MTFa domain")

    def defocus_grid(self) -> tuple[float, ...]:
        self.validate()
        values: list[float] = []
        value = self.defocus_start_d
        if self.defocus_step_d < 0:
            while value >= self.defocus_stop_d - 1e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        else:
            while value <= self.defocus_stop_d + 1e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        return tuple(values)

    def mtf_frequency_grid_cpd(self) -> tuple[float, ...]:
        self.validate()
        count = round(self.mtfa_max_cpd / self.mtf_frequency_step_cpd)
        return tuple(round(index * self.mtf_frequency_step_cpd, 10) for index in range(count + 1))


@dataclass(frozen=True, slots=True)
class B0LockMtfaSettings:
    """TASK-005D B0 selection settings for the MFE MTFA production path."""

    settings_id: str
    wavelength_nm: float
    pupils_mm: tuple[float, ...]
    defocus_start_d: float
    defocus_stop_d: float
    defocus_step_d: float
    q_lock_max_cycles_per_mm: float
    mtfa_frequency_step_cyc_per_mm: float
    mtfa_sampling: int
    mtfa_grid: int = 0
    mtfa_data_type: int = 0
    wavelength_number: int = 1
    field_number: int = 1

    def validate(self) -> None:
        if not self.settings_id.strip():
            raise ValueError("B0 MTFA settings_id is required")
        scalar_values = (
            self.wavelength_nm,
            self.defocus_start_d,
            self.defocus_stop_d,
            self.defocus_step_d,
            self.q_lock_max_cycles_per_mm,
            self.mtfa_frequency_step_cyc_per_mm,
        )
        if not all(math.isfinite(float(value)) for value in scalar_values):
            raise ValueError("B0 MTFA settings must contain only finite numeric values")
        if self.wavelength_nm <= 0:
            raise ValueError("B0 MTFA wavelength must be positive")
        if not self.pupils_mm or not all(
            math.isfinite(float(pupil)) and pupil > 0 for pupil in self.pupils_mm
        ):
            raise ValueError("B0 MTFA pupils must be finite and positive")
        if self.defocus_step_d == 0:
            raise ValueError("B0 MTFA defocus step must not be zero")
        if self.defocus_start_d > self.defocus_stop_d and self.defocus_step_d > 0:
            raise ValueError("B0 MTFA defocus step direction does not reach stop")
        if self.defocus_start_d < self.defocus_stop_d and self.defocus_step_d < 0:
            raise ValueError("B0 MTFA defocus step direction does not reach stop")
        if self.q_lock_max_cycles_per_mm <= 0 or self.mtfa_frequency_step_cyc_per_mm <= 0:
            raise ValueError("B0 MTFA frequency settings must be positive")
        ratio = self.q_lock_max_cycles_per_mm / self.mtfa_frequency_step_cyc_per_mm
        if not math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("B0 MTFA frequency step must divide Q-lock maximum exactly")
        if self.mtfa_sampling < 1:
            raise ValueError("B0 MTFA sampling index must be positive")
        if self.mtfa_grid != 0:
            raise ValueError("B0 MTFA production Grid is frozen to 0")
        if self.mtfa_data_type != 0:
            raise ValueError("B0 MTFA production Data Type is frozen to modulation (0)")
        if self.wavelength_number != 1 or self.field_number != 1:
            raise ValueError("B0 MTFA production Wave/Field are frozen to 1")

    def defocus_grid(self) -> tuple[float, ...]:
        self.validate()
        values: list[float] = []
        value = self.defocus_start_d
        if self.defocus_step_d < 0:
            while value >= self.defocus_stop_d - 1.0e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        else:
            while value <= self.defocus_stop_d + 1.0e-12:
                values.append(round(value, 10))
                value += self.defocus_step_d
        return tuple(values)

    def frequency_grid(self, *, step_cyc_per_mm: float | None = None) -> tuple[float, ...]:
        self.validate()
        step = self.mtfa_frequency_step_cyc_per_mm if step_cyc_per_mm is None else step_cyc_per_mm
        if not math.isfinite(float(step)) or step <= 0:
            raise ValueError("B0 MTFA frequency step must be finite and positive")
        ratio = self.q_lock_max_cycles_per_mm / step
        if not math.isclose(ratio, round(ratio), rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("B0 MTFA frequency step must divide Q-lock maximum exactly")
        return tuple(round(index * step, 10) for index in range(round(ratio) + 1))


CORNEA_LOCK_B0_555_V2 = B0LockMtfaSettings(
    settings_id="CORNEA_LOCK_B0_555_v2",
    wavelength_nm=555.0,
    pupils_mm=(3.0, 5.0),
    defocus_start_d=0.50,
    defocus_stop_d=-3.50,
    defocus_step_d=-0.25,
    q_lock_max_cycles_per_mm=50.0,
    mtfa_frequency_step_cyc_per_mm=5.0,
    mtfa_sampling=3,
)

NOMINAL_MAIN_FFT_MTF_555_V2 = AnalysisSettings(
    settings_id="NOMINAL_MAIN_FFT_MTF_555_v2",
    wavelength_nm=555.0,
    pupils_mm=(3.0, 5.0),
    defocus_start_d=0.50,
    defocus_stop_d=-3.00,
    defocus_step_d=-0.25,
    fft_mtf_sampling=128,
    fft_mtf_convergence_samplings=(64, 128, 256),
    fft_mtf_use_polarization=False,
    mtf_frequency_step_cpd=1.0,
    mtfa_max_cpd=60.0,
    mtf_sample_frequencies_cpd=(10.0, 20.0, 30.0, 40.0, 50.0, 60.0),
)

# URD-0001 v1.4 changed the standard-eye SA calibration pupil from 3 mm to 6 mm.
# Because the full ScientificBaseline is hashed by ProjectStore, this is a real
# scientific-baseline revision rather than an implementation-only setting change.
CURRENT_SCIENTIFIC_BASELINE_ID = "MVP_2026_v2"


@dataclass(frozen=True, slots=True)
class BaselineBaseSpec:
    base_id: str
    source_model_id: str
    source_refraction_d: float | None
    axial_length_mm: float
    post_cornea_to_stop_mm: float
    post_cornea_to_iol_ant_mm: float
    aqueous_index: float
    vitreous_index: float

    def validate(self) -> None:
        if not self.base_id.strip() or not self.source_model_id.strip():
            raise ValueError("base_id and source_model_id are required")
        finite_values = (
            self.axial_length_mm,
            self.post_cornea_to_stop_mm,
            self.post_cornea_to_iol_ant_mm,
            self.aqueous_index,
            self.vitreous_index,
        )
        if not all(math.isfinite(value) for value in finite_values):
            raise ValueError("base prescription values must be finite")
        if self.source_refraction_d is not None and not math.isfinite(self.source_refraction_d):
            raise ValueError("source refraction must be finite when provided")
        if not (
            0 < self.post_cornea_to_stop_mm
            < self.post_cornea_to_iol_ant_mm
            < self.axial_length_mm
        ):
            raise ValueError("base axial landmarks must be positive and strictly ordered")
        if self.aqueous_index <= 1 or self.vitreous_index <= 1:
            raise ValueError("base medium indices must be greater than one")


@dataclass(frozen=True, slots=True)
class BaselineStandardEyeSpec:
    eye_id: str
    corneal_c40_um: float
    iol_footprint_mm: float
    iol_footprint_tolerance_mm: float
    medium_index: float
    aperture_mm: float
    wavelength_nm: float


@dataclass(frozen=True, slots=True)
class BaselineCorneaSpec:
    cornea_id: str
    treatment_d: float
    optical_zone_mm: float
    target_delta_c40_um: float | None = None
    near_diameter_mm: float | None = None
    add_rx_d: float | None = None
    transition_width_mm: float | None = None


@dataclass(frozen=True, slots=True)
class BaselinePlatformSpec:
    platform_id: str
    user_label: str
    standard_eye_sa_target_um: float


@dataclass(frozen=True, slots=True)
class NominalConditionSpec:
    wavelength_nm: float = 555.0
    pupils_mm: tuple[float, ...] = (3.0, 5.0)
    field_deg: float = 0.0
    cornea_decentration_mm: float = 0.0
    iol_decentration_mm: float = 0.0
    iol_tilt_deg: float = 0.0
    micro_monovision_defocus_d: float = 0.0


BASELINE_BASE_SPECS = (
    BaselineBaseSpec(
        base_id=BaseId.LB_AL2395,
        source_model_id="Liou_Brennan_1997",
        source_refraction_d=None,
        axial_length_mm=23.950,
        post_cornea_to_stop_mm=3.150,
        post_cornea_to_iol_ant_mm=4.500,
        aqueous_index=1.336,
        vitreous_index=1.336,
    ),
    BaselineBaseSpec(
        base_id=BaseId.ATC_M3_AL24477,
        source_model_id="Atchison_2006_Model_1",
        source_refraction_d=-3.0,
        axial_length_mm=24.477,
        post_cornea_to_stop_mm=3.150,
        post_cornea_to_iol_ant_mm=4.500,
        aqueous_index=1.336,
        vitreous_index=1.336,
    ),
)
BASELINE_STANDARD_EYE_SPEC = BaselineStandardEyeSpec(
    "STD_IOL_EYE_2024", 0.258, 5.15, 0.10, 1.336, 6.0, 546.0
)
BASELINE_CORNEA_SPECS = (
    BaselineCorneaSpec(CorneaId.A0, -3.0, 5.0, target_delta_c40_um=0.13),
    BaselineCorneaSpec(CorneaId.B0, -3.0, 6.0),
    BaselineCorneaSpec(
        CorneaId.C0,
        -3.0,
        6.5,
        near_diameter_mm=3.0,
        add_rx_d=1.75,
        transition_width_mm=0.75,
    ),
)
BASELINE_B_CANDIDATES_DELTA_C40_UM = (0.10, 0.15, 0.20, 0.25, 0.30)
BASELINE_PLATFORM_SPECS = (
    BaselinePlatformSpec(PlatformId.WFS, "WFS-like surrogate", -0.20),
    BaselinePlatformSpec(PlatformId.RAD, "RAD-like surrogate", -0.27),
    BaselinePlatformSpec(PlatformId.HOA, "HOA-like surrogate", 0.00),
)


@dataclass(frozen=True, slots=True)
class ScientificBaseline:
    baseline_id: str
    base_specs: tuple[BaselineBaseSpec, ...] = BASELINE_BASE_SPECS
    standard_eye_spec: BaselineStandardEyeSpec = BASELINE_STANDARD_EYE_SPEC
    cornea_specs: tuple[BaselineCorneaSpec, ...] = BASELINE_CORNEA_SPECS
    b_candidate_delta_c40_um: tuple[float, ...] = BASELINE_B_CANDIDATES_DELTA_C40_UM
    platform_specs: tuple[BaselinePlatformSpec, ...] = BASELINE_PLATFORM_SPECS
    nominal_condition: NominalConditionSpec = NominalConditionSpec()
    iteration_limit: int = 2

    @property
    def base_ids(self) -> tuple[str, ...]:
        return tuple(spec.base_id for spec in self.base_specs)

    @property
    def cornea_ids(self) -> tuple[str, ...]:
        return tuple(spec.cornea_id for spec in self.cornea_specs)

    @property
    def platform_ids(self) -> tuple[str, ...]:
        return tuple(spec.platform_id for spec in self.platform_specs)


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    artifact_id: str
    artifact_type: str
    relative_path: str
    baseline_id: str
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    artifact_type: str
    relative_path: str
    sha256: str
    baseline_id: str
    run_id: str | None
    locked: bool


@dataclass(frozen=True, slots=True)
class RunEnvironment:
    program_version: str
    opticstudio_version: str
    baseline_id: str
    analysis_settings_id: str
    manifest_hash: str
    lock_set_hash: str

    def validate(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field.name} is required")


@dataclass(frozen=True, slots=True)
class RunRecord:
    run_id: str
    action: str
    target_id: str
    status: RunStatus
    started_at: str
    finished_at: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    environment_ref: str | None = None


def strict_dataclass_from_mapping(cls: type[Any], payload: Mapping[str, Any]) -> Any:
    if not is_dataclass(cls):
        raise TypeError("cls must be a dataclass type")
    expected = {f.name for f in fields(cls)}
    actual = set(payload)
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        raise ValueError(f"schema mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    return cls(**payload)


def dataclass_to_dict(value: Any) -> dict[str, Any]:
    if not is_dataclass(value):
        raise TypeError("value must be a dataclass instance")
    return asdict(value)
