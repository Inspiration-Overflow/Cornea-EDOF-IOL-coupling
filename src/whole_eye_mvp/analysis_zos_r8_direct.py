"""Direct acquisition of immutable R6/R7 serialized models for the R8 production matrix."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import shutil
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .analysis import (
    AberrationSummary,
    ConfigArtifacts,
    ConfigResult,
    MatchedPairDelta,
    summarize_mtfa_curve,
    validate_completed_result,
    with_shape_axis,
)
from .analysis_zos import (
    FIXED_CORNEA_POST_ROLE,
    IMAGE_ROLE,
    STOP_ROLE,
    TASK007_CARRIER_ANT_ROLE,
    TASK007_CARRIER_POST_ROLE,
    EntitySnapshot,
    _require_cycles_per_mm,
    _require_role,
    _write_plots,
    _write_through_focus_csv,
    acquire_footprints,
)
from .analysis_zos_pair_scale import (
    EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
    PAIR_MONO_FREQUENCY_SCALE_MODE,
    TASK009_PAIR_MONO_MTF_ACQUISITION,
    PairAngularScaleReference,
    frequencies_for_pair_reference,
)
from .b0_zos import object_thickness_for_defocus_d
from .carrier_scaffold import CONTROLLED_IOL_CARRIER_546_V1
from .domain import NOMINAL_MAIN_FFT_MTF_555_V2, AnalysisSettings, OpticState
from .manifest import NominalConfig
from .metrics import mm_per_degree, mtfa
from .model_revision import physical_stop_semi_diameter_mm
from .model_revision_zos import (
    configure_physical_pupil,
    read_revision_geometry,
    validate_revision_geometry,
)
from .quality import settings_hash
from .revision_r5_2 import R5_2_FREEZE_ID
from .revision_r6_zos import _read_binary4_zones
from .run72 import config_scalar_row, paired_delta_row, through_focus_rows
from .store import sha256_file
from .zos import MfeEfflRunner, MfeFullHoaRunner, MfeMtfGridRunner, MfeMtfGridSettings, ZosSession

DIRECT_MODEL_PROVENANCE_POLICY_ID = "R8_DIRECT_SERIALIZED_R5_2_MODEL_v1"
DIRECT_BINARY4_CARRIER_POWER_DIAGNOSTIC_D = 0.0
_DIRECT_MODEL_POLICY_PAYLOAD = {
    "policy_id": DIRECT_MODEL_PROVENANCE_POLICY_ID,
    "source": "R6/R7 ACTUAL_BINARY4_MONO/EDOF serialized models",
    "source_identity": "SHA-256 from MODEL_REVISION_R6_R7_EVIDENCE.json",
    "mutation": "copy-on-write; physical STOP only",
    "legacy_residual_reapplication": False,
}
DIRECT_MODEL_PROVENANCE_POLICY_HASH = hashlib.sha256(
    json.dumps(
        _DIRECT_MODEL_POLICY_PAYLOAD,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()

R8_CONFIG_REQUIRED_COLUMNS = (
    "run_id",
    "config_id",
    "pair_key",
    "carrier_id",
    "base_id",
    "cornea_id",
    "platform_id",
    "optic_state",
    "pupil_mm",
    "distance_peak_retina_d",
    "distance_peak_mtfa",
    "mtfa_at_zero_d",
    "dof50_far_d",
    "dof50_near_d",
    "dof50_width_d",
    "dof50_far_censored",
    "dof50_near_censored",
    "tf_mtfa_mean",
    "peak_search_censored",
    "c40_um",
    "c60_um",
    "hoa_rms_um",
    "analysis_settings_hash",
    "hoa_settings_id",
    "hoa_settings_hash",
    "model_sha256",
    "entity_fingerprint",
)
R8_THROUGH_FOCUS_REQUIRED_COLUMNS = (
    "run_id",
    "config_id",
    "pair_key",
    "base_id",
    "cornea_id",
    "platform_id",
    "optic_state",
    "pupil_mm",
    "defocus_retina_d",
    "defocus_shape_d",
    "mtfa",
    "mtf10",
    "mtf20",
    "mtf30",
    "mtf40",
    "mtf50",
    "mtf60",
)
R8_PAIRED_REQUIRED_COLUMNS = (
    "pair_key",
    "mono_config_id",
    "edof_config_id",
    "distance_peak_retina_d",
    "distance_peak_mtfa",
    "mtfa_at_zero_d",
    "dof50_width_d",
    "tf_mtfa_mean",
    "c40_um",
    "c60_um",
    "hoa_rms_um",
    "delta_f_residual_d",
)


class R8DirectAcquisitionError(RuntimeError):
    """Direct serialized-model acquisition violated the frozen R8 contract."""


def _direct_surface_payload(row: Any, surface_number: int) -> dict[str, object]:
    type_name = str(row.TypeName or row.GetType())
    payload: dict[str, object] = {
        "surface": surface_number,
        "comment": str(row.Comment),
        "type": type_name,
        "radius_mm": float(row.Radius),
        "conic": float(row.Conic),
        "thickness_mm": float(row.Thickness),
        "material": str(row.Material),
        "is_stop": bool(row.IsStop),
    }
    if surface_number != 3:
        payload["semi_diameter_mm"] = float(row.SemiDiameter)
    return payload


def _direct_binary4_zone_payload(zone: Any) -> dict[str, object]:
    return {
        "zone": int(zone.zone),
        "r_inner_mm": float(zone.r_inner_mm),
        "r_outer_mm": float(zone.r_outer_mm),
        "radius_mm": float(zone.radius_mm),
        "conic": float(zone.conic),
        "diffraction_order": float(zone.diffraction_order),
        "alpha_p2_native": float(zone.alpha_p2_native),
        "alpha_p4_native": float(zone.alpha_p4_native),
        "alpha_p6_native": float(zone.alpha_p6_native),
    }


def capture_direct_entity_snapshot(session: ZosSession, platform_id: str) -> EntitySnapshot:
    """Hash a direct R6/R7 Binary4 full eye without assuming symmetric biconvex radii.

    OBJECT thickness is intentionally excluded, as in the legacy snapshot. The physical
    STOP semi-diameter is also excluded because 3/5-mm pupil is an approved per-config
    acquisition setting. ``carrier_power_d`` is a finite compatibility diagnostic only;
    Binary4 zone geometry has no single symmetric-biconvex power representation.
    """

    lde = session.system.LDE
    if int(lde.NumberOfSurfaces) != 7:
        raise R8DirectAcquisitionError(
            "direct R8 physical model must contain exactly 7 surfaces"
        )
    _require_role(lde, 2, FIXED_CORNEA_POST_ROLE)
    _require_role(lde, 3, STOP_ROLE)
    _require_role(lde, 4, TASK007_CARRIER_ANT_ROLE)
    _require_role(lde, 5, TASK007_CARRIER_POST_ROLE)
    _require_role(lde, 6, IMAGE_ROLE)

    surfaces = [
        _direct_surface_payload(lde.GetSurfaceAt(index), index)
        for index in range(1, 7)
    ]
    zones = _read_binary4_zones(session, platform_id, standard_eye=False)
    zone_payload = [_direct_binary4_zone_payload(zone) for zone in zones]
    if not zone_payload:
        raise R8DirectAcquisitionError("direct R8 Binary4 snapshot has no zones")

    retina_position = math.fsum(
        float(lde.GetSurfaceAt(index).Thickness) for index in range(1, 6)
    )
    iol_position = (
        float(lde.GetSurfaceAt(2).Thickness)
        + float(lde.GetSurfaceAt(3).Thickness)
    )
    ant = lde.GetSurfaceAt(4)
    post = lde.GetSurfaceAt(5)
    payload = {
        "surface_count": int(lde.NumberOfSurfaces),
        "stop_surface": int(lde.StopSurface),
        "surfaces_1_to_image": surfaces,
        "retina_position_mm": retina_position,
        "iol_position_from_post_cornea_mm": iol_position,
        "binary4_platform_id": str(platform_id),
        "binary4_zones": zone_payload,
        "carrier_power_diagnostic_d": DIRECT_BINARY4_CARRIER_POWER_DIAGNOSTIC_D,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return EntitySnapshot(
        fingerprint=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        retina_position_mm=retina_position,
        iol_position_mm=iol_position,
        elp_mm=iol_position,
        carrier_power_d=DIRECT_BINARY4_CARRIER_POWER_DIAGNOSTIC_D,
        radius_ant_mm=float(ant.Radius),
        radius_post_mm=float(post.Radius),
        q_ant=float(ant.Conic),
        q_post=float(post.Conic),
    )


@dataclass(frozen=True, slots=True)
class DirectModelSpec:
    config_id: str
    pair_key: str
    carrier_id: str
    base_id: str
    cornea_id: str
    platform_id: str
    optic_state: str
    pupil_mm: float
    model_artifact_key: str
    source_path: Path
    source_sha256: str

    @property
    def stop_semi_diameter_mm(self) -> float:
        return physical_stop_semi_diameter_mm(self.pupil_mm)


@dataclass(frozen=True, slots=True)
class DirectMatchedPair:
    pair_key: str
    mono: DirectModelSpec
    edof: DirectModelSpec

    def validate(self) -> None:
        if self.mono.pair_key != self.pair_key or self.edof.pair_key != self.pair_key:
            raise R8DirectAcquisitionError(f"pair key mismatch: {self.pair_key}")
        if self.mono.optic_state != OpticState.MONO.value:
            raise R8DirectAcquisitionError(f"pair MONO state mismatch: {self.pair_key}")
        if self.edof.optic_state != OpticState.EDOF.value:
            raise R8DirectAcquisitionError(f"pair EDOF state mismatch: {self.pair_key}")
        identity = (
            self.mono.carrier_id,
            self.mono.base_id,
            self.mono.cornea_id,
            self.mono.platform_id,
            self.mono.pupil_mm,
        )
        if identity != (
            self.edof.carrier_id,
            self.edof.base_id,
            self.edof.cornea_id,
            self.edof.platform_id,
            self.edof.pupil_mm,
        ):
            raise R8DirectAcquisitionError(f"matched pair identity drift: {self.pair_key}")


@dataclass(frozen=True, slots=True)
class R8DirectRun:
    run_id: str
    results: tuple[ConfigResult, ...]
    paired_deltas: tuple[MatchedPairDelta, ...]
    pair_references: Mapping[str, PairAngularScaleReference]
    source_model_sha256: Mapping[str, str]
    config_rows: tuple[dict[str, object], ...]
    through_focus_rows: tuple[dict[str, object], ...]
    paired_rows: tuple[dict[str, object], ...]


def _is_sha256(value: object) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def build_direct_model_specs(
    project_dir: Path,
    plan: Sequence[object],
    model_hashes: Mapping[str, str],
    *,
    r6_r7_output_relative: Path,
    expected_config_count: int = 96,
    expected_model_count: int = 48,
) -> tuple[DirectModelSpec, ...]:
    """Map the validated R8 plan to immutable serialized R6/R7 model inputs."""

    project = Path(project_dir).resolve()
    required_keys = {str(row.model_artifact_key) for row in plan}
    if set(model_hashes) != required_keys:
        missing = sorted(required_keys - set(model_hashes))
        extra = sorted(set(model_hashes) - required_keys)
        raise R8DirectAcquisitionError(
            f"direct-model hash map differs from R8 plan; missing={missing}, extra={extra}"
        )
    specs: list[DirectModelSpec] = []
    for row in plan:
        key = str(row.model_artifact_key)
        expected_sha = model_hashes[key]
        if not _is_sha256(expected_sha):
            raise R8DirectAcquisitionError(f"invalid source SHA-256 for {key}")
        source = (project / r6_r7_output_relative / key).resolve()
        specs.append(
            DirectModelSpec(
                config_id=str(row.config_id),
                pair_key=str(row.pair_key),
                carrier_id=str(row.carrier_id),
                base_id=str(row.base_id),
                cornea_id=str(row.cornea_id),
                platform_id=str(row.platform_id),
                optic_state=str(row.optic_state),
                pupil_mm=float(row.pupil_mm),
                model_artifact_key=key,
                source_path=source,
                source_sha256=str(expected_sha),
            )
        )
    if len(specs) != expected_config_count:
        raise R8DirectAcquisitionError(
            f"direct input count must be {expected_config_count}, got {len(specs)}"
        )
    if len({item.model_artifact_key for item in specs}) != expected_model_count:
        raise R8DirectAcquisitionError(
            f"direct inputs must resolve exactly {expected_model_count} serialized models"
        )
    return tuple(specs)


def verify_direct_model_sources(
    specs: Sequence[DirectModelSpec],
    *,
    expected_model_count: int = 48,
) -> None:
    """Verify each unique serialized source exists and matches its R6/R7 SHA-256."""

    checked: dict[Path, str] = {}
    for spec in specs:
        prior = checked.get(spec.source_path)
        if prior is not None:
            if prior != spec.source_sha256:
                raise R8DirectAcquisitionError(
                    f"conflicting expected hashes for source model: {spec.source_path}"
                )
            continue
        if not spec.source_path.is_file():
            raise R8DirectAcquisitionError(
                f"serialized R6/R7 source is missing: {spec.source_path}"
            )
        actual = sha256_file(spec.source_path)
        if actual != spec.source_sha256:
            raise R8DirectAcquisitionError(
                f"serialized R6/R7 source hash mismatch: {spec.model_artifact_key}: "
                f"{actual} != {spec.source_sha256}"
            )
        checked[spec.source_path] = actual
    if len(checked) != expected_model_count:
        raise R8DirectAcquisitionError(
            "direct source verification expected "
            f"{expected_model_count} files, got {len(checked)}"
        )


def group_direct_pairs(
    specs: Sequence[DirectModelSpec],
    *,
    expected_pair_count: int = 48,
) -> tuple[DirectMatchedPair, ...]:
    grouped: dict[str, list[DirectModelSpec]] = defaultdict(list)
    for spec in specs:
        grouped[spec.pair_key].append(spec)
    if len(grouped) != expected_pair_count:
        raise R8DirectAcquisitionError(
            f"direct acquisition requires {expected_pair_count} pairs, got {len(grouped)}"
        )
    pairs: list[DirectMatchedPair] = []
    for pair_key in sorted(grouped):
        members = grouped[pair_key]
        by_state = {item.optic_state: item for item in members}
        if len(members) != 2 or set(by_state) != {OpticState.MONO.value, OpticState.EDOF.value}:
            raise R8DirectAcquisitionError(f"pair must contain MONO+EDOF exactly once: {pair_key}")
        pair = DirectMatchedPair(
            pair_key,
            by_state[OpticState.MONO.value],
            by_state[OpticState.EDOF.value],
        )
        pair.validate()
        pairs.append(pair)
    return tuple(pairs)


def validate_pair_reference_map(
    pairs: Sequence[DirectMatchedPair],
    references: Mapping[str, PairAngularScaleReference],
) -> None:
    expected = {pair.pair_key for pair in pairs}
    if set(references) != expected:
        raise R8DirectAcquisitionError("pair-reference keys differ from the exact R8 pair set")
    for pair in pairs:
        reference = references[pair.pair_key]
        reference.validate()
        if reference.pair_key != pair.pair_key:
            raise R8DirectAcquisitionError(f"pair-reference identity mismatch: {pair.pair_key}")
        if reference.mono_config_id != pair.mono.config_id:
            raise R8DirectAcquisitionError(f"pair-reference MONO config mismatch: {pair.pair_key}")
        expected_scale = mm_per_degree(reference.reference_effl_mm)
        if not math.isclose(reference.mm_per_degree, expected_scale, rel_tol=0.0, abs_tol=1.0e-12):
            raise R8DirectAcquisitionError(f"pair-reference mm/degree mismatch: {pair.pair_key}")
        frequencies = frequencies_for_pair_reference(
            reference.reference_effl_mm,
            NOMINAL_MAIN_FFT_MTF_555_V2.mtf_frequency_grid_cpd(),
        )
        if len(frequencies) != 61 or not all(
            math.isfinite(value) and value >= 0.0 for value in frequencies
        ):
            raise R8DirectAcquisitionError(f"invalid pair frequency grid: {pair.pair_key}")


def _direct_carrier_identity_hash(spec: DirectModelSpec) -> str:
    payload = {
        "r5_freeze_id": R5_2_FREEZE_ID,
        "carrier_id": spec.carrier_id,
        "base_id": spec.base_id,
        "cornea_id": spec.cornea_id,
        "platform_id": spec.platform_id,
    }
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def nominal_config_for_direct_model(spec: DirectModelSpec) -> NominalConfig:
    """Create ConfigResult-compatible metadata without invoking the legacy residual pipeline."""

    is_edof = spec.optic_state == OpticState.EDOF.value
    if spec.optic_state not in {OpticState.MONO.value, OpticState.EDOF.value}:
        raise R8DirectAcquisitionError(f"unsupported optic state: {spec.optic_state}")
    config = NominalConfig(
        config_id=spec.config_id,
        carrier_id=spec.carrier_id,
        base_id=spec.base_id,
        cornea_id=spec.cornea_id,
        platform_id=spec.platform_id,
        optic_state=spec.optic_state,
        pupil_mm=spec.pupil_mm,
        carrier_lock_hash=_direct_carrier_identity_hash(spec),
        residual_id=R5_2_FREEZE_ID if is_edof else None,
        residual_sha256=spec.source_sha256 if is_edof else None,
        residual_validation_policy_id=(
            DIRECT_MODEL_PROVENANCE_POLICY_ID if is_edof else None
        ),
        residual_validation_policy_hash=(
            DIRECT_MODEL_PROVENANCE_POLICY_HASH if is_edof else None
        ),
    )
    if config.pair_key != spec.pair_key:
        raise R8DirectAcquisitionError(
            f"direct NominalConfig pair key mismatch: {config.pair_key} != {spec.pair_key}"
        )
    return config


def validate_aggregate_rows(
    config_rows: Sequence[Mapping[str, object]],
    tf_rows: Sequence[Mapping[str, object]],
    paired_rows: Sequence[Mapping[str, object]],
    *,
    through_focus_planes: int = 15,
    config_count: int = 96,
    pair_count: int = 48,
) -> None:
    """Validate exact R8 aggregate counts and row schemas before formal evidence is written."""

    if through_focus_planes <= 0:
        raise R8DirectAcquisitionError("through-focus plane count must be positive")
    expectations = (
        (config_rows, config_count, R8_CONFIG_REQUIRED_COLUMNS, "config"),
        (
            tf_rows,
            config_count * through_focus_planes,
            R8_THROUGH_FOCUS_REQUIRED_COLUMNS,
            "through-focus",
        ),
        (paired_rows, pair_count, R8_PAIRED_REQUIRED_COLUMNS, "paired"),
    )
    for rows, count, columns, label in expectations:
        if len(rows) != count:
            raise R8DirectAcquisitionError(
                f"R8 {label} row count mismatch: expected {count}, got {len(rows)}"
            )
        expected_columns = set(columns)
        for index, row in enumerate(rows):
            if set(row) != expected_columns:
                raise R8DirectAcquisitionError(
                    f"R8 {label} row schema mismatch at {index}: "
                    f"{sorted(row)} != {sorted(expected_columns)}"
                )

    if len({str(row["config_id"]) for row in config_rows}) != config_count:
        raise R8DirectAcquisitionError("R8 aggregate config IDs are not unique")
    by_config: dict[str, int] = defaultdict(int)
    for row in tf_rows:
        by_config[str(row["config_id"])] += 1
    if set(by_config) != {str(row["config_id"]) for row in config_rows}:
        raise R8DirectAcquisitionError("R8 through-focus config IDs differ from config rows")
    if set(by_config.values()) != {through_focus_planes}:
        raise R8DirectAcquisitionError(
            f"R8 requires exactly {through_focus_planes} through-focus rows per config"
        )
    if len({str(row["pair_key"]) for row in paired_rows}) != pair_count:
        raise R8DirectAcquisitionError("R8 aggregate pair IDs are not unique")


def _write_csv(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    if not rows:
        raise R8DirectAcquisitionError(f"refusing to write empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    first = rows[0]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(first))
        writer.writeheader()
        writer.writerows(rows)


def _validate_loaded_direct_model(
    session: ZosSession,
    spec: DirectModelSpec,
) -> None:
    wavelength_nm = (
        float(session.system.SystemData.Wavelengths.GetWavelength(1).Wavelength) * 1000.0
    )
    if not math.isfinite(wavelength_nm) or abs(
        wavelength_nm - NOMINAL_MAIN_FFT_MTF_555_V2.wavelength_nm
    ) > 1.0e-6:
        raise R8DirectAcquisitionError(
            f"loaded R8 model wavelength mismatch: {wavelength_nm}"
        )
    _require_cycles_per_mm(session)
    geometry = read_revision_geometry(session, spec.base_id, full_eye=True)
    findings = validate_revision_geometry(
        geometry,
        spec.base_id,
        expected_pupil_diameter_mm=spec.pupil_mm,
    )
    if findings:
        raise R8DirectAcquisitionError(
            f"loaded R8 physical geometry failed for {spec.config_id}: {' | '.join(findings)}"
        )


@dataclass(slots=True)
class R8DirectModelAcquisitionAdapter:
    session: ZosSession
    pair_reference_effl_mm: Mapping[str, float]
    sampling: int = NOMINAL_MAIN_FFT_MTF_555_V2.fft_mtf_sampling
    diagnostics: dict[str, dict[str, object]] = field(default_factory=dict)
    analysis_settings: AnalysisSettings = NOMINAL_MAIN_FFT_MTF_555_V2
    peak_search_window_d: float = 0.5

    def __post_init__(self) -> None:
        self.analysis_settings.validate()
        if self.sampling != self.analysis_settings.fft_mtf_sampling:
            raise ValueError("acquisition sampling differs from analysis settings")
        if not math.isfinite(self.peak_search_window_d) or self.peak_search_window_d <= 0.0:
            raise ValueError("distance-peak search window must be finite and positive")
        normalized = {
            str(key): float(value) for key, value in self.pair_reference_effl_mm.items()
        }
        if not normalized or any(
            not key or not math.isfinite(value) or value <= 0.0
            for key, value in normalized.items()
        ):
            raise ValueError("R8 pair-reference EFFLs must be positive finite values")
        self.pair_reference_effl_mm = normalized
        if (
            TASK009_PAIR_MONO_MTF_ACQUISITION.contract_hash
            != EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH
        ):
            raise RuntimeError("TASK-009 paired-MONO acquisition contract hash drifted")

    def _prepare_working_model(
        self,
        spec: DirectModelSpec,
        destination: Path,
    ) -> tuple[str, str]:
        if not spec.source_path.is_file():
            raise R8DirectAcquisitionError(
                f"serialized R6/R7 source is missing: {spec.source_path}"
            )
        source_sha = sha256_file(spec.source_path)
        if source_sha != spec.source_sha256:
            raise R8DirectAcquisitionError(
                f"serialized R6/R7 source hash mismatch before acquisition: "
                f"{spec.model_artifact_key}"
            )

        output = Path(destination).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(spec.source_path, output)
        if sha256_file(output) != source_sha:
            raise R8DirectAcquisitionError("copy-on-write model differs from immutable source")

        self.session.system.LoadFile(str(output), False)
        source_entity = capture_direct_entity_snapshot(self.session, spec.platform_id)
        configure_physical_pupil(self.session, spec.pupil_mm, stop_surface=3)
        _validate_loaded_direct_model(self.session, spec)
        configured_entity = capture_direct_entity_snapshot(self.session, spec.platform_id)
        if configured_entity.fingerprint != source_entity.fingerprint:
            raise R8DirectAcquisitionError(
                f"physical-pupil setup changed model entity identity: {spec.config_id}"
            )
        self.session.system.SaveAs(str(output))
        configured_sha = sha256_file(output)

        self.session.system.LoadFile(str(output), False)
        _validate_loaded_direct_model(self.session, spec)
        replay_entity = capture_direct_entity_snapshot(self.session, spec.platform_id)
        if replay_entity.fingerprint != configured_entity.fingerprint:
            raise R8DirectAcquisitionError(
                f"configured working-model replay changed entity identity: {spec.config_id}"
            )
        if sha256_file(spec.source_path) != source_sha:
            raise R8DirectAcquisitionError(
                f"immutable R6/R7 source changed during copy-on-write preparation: "
                f"{spec.model_artifact_key}"
            )
        return source_sha, configured_sha

    def measure_pair_mono_reference(
        self,
        pair: DirectMatchedPair,
        destination: Path,
    ) -> PairAngularScaleReference:
        pair.validate()
        source_sha, configured_sha = self._prepare_working_model(pair.mono, destination)
        before = capture_direct_entity_snapshot(self.session, pair.mono.platform_id)
        baseline_mfe = int(self.session.system.MFE.NumberOfOperands)
        result = MfeEfflRunner(self.session.system, self.session.zosapi).run()
        if int(self.session.system.MFE.NumberOfOperands) != baseline_mfe:
            raise R8DirectAcquisitionError("EFFL acquisition left the MFE modified")
        after = capture_direct_entity_snapshot(self.session, pair.mono.platform_id)
        if before.fingerprint != after.fingerprint:
            raise R8DirectAcquisitionError(
                f"pair-reference EFFL changed entity identity: {pair.pair_key}"
            )
        if sha256_file(destination) != configured_sha:
            raise R8DirectAcquisitionError(
                f"pair-reference working model changed on disk: {pair.pair_key}"
            )
        if sha256_file(pair.mono.source_path) != source_sha:
            raise R8DirectAcquisitionError(
                f"pair-reference source model changed: {pair.pair_key}"
            )
        effl_mm = float(result.effective_focal_length_mm)
        reference = PairAngularScaleReference(
            pair_key=pair.pair_key,
            mono_config_id=pair.mono.config_id,
            reference_effl_mm=effl_mm,
            mm_per_degree=mm_per_degree(effl_mm),
            model_sha256=configured_sha,
            entity_fingerprint=before.fingerprint,
        )
        reference.validate()
        return reference

    def _reference_effl_mm(self, spec: DirectModelSpec) -> float:
        try:
            return float(self.pair_reference_effl_mm[spec.pair_key])
        except KeyError as exc:
            raise R8DirectAcquisitionError(
                f"missing paired-MONO EFFL for {spec.pair_key}"
            ) from exc

    def run_config(
        self,
        spec: DirectModelSpec,
        output_dir: Path,
        run_id: str,
    ) -> ConfigResult:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        working_model = output / "model.zmx"
        source_sha, model_hash_before = self._prepare_working_model(spec, working_model)

        config = nominal_config_for_direct_model(spec)
        before = capture_direct_entity_snapshot(self.session, spec.platform_id)
        footprints = acquire_footprints(self.session)
        if footprints.unintended_vignetting:
            raise R8DirectAcquisitionError(
                f"unexpected vignetting in R8 config {spec.config_id}: {footprints.failures}"
            )

        object_surface = self.session.system.LDE.GetSurfaceAt(0)
        saved_object_thickness = float(object_surface.Thickness)
        baseline_mfe = int(self.session.system.MFE.NumberOfOperands)
        state_effl_mm = float(
            MfeEfflRunner(self.session.system, self.session.zosapi).run().effective_focal_length_mm
        )
        reference_effl_mm = self._reference_effl_mm(spec)
        pair_scale = mm_per_degree(reference_effl_mm)
        state_scale = mm_per_degree(state_effl_mm)
        settings = self.analysis_settings
        cpd_grid = settings.mtf_frequency_grid_cpd()
        frequencies_mm = frequencies_for_pair_reference(reference_effl_mm, cpd_grid)
        runner = MfeMtfGridRunner(self.session.system, self.session.zosapi)
        defocus_grid = settings.defocus_grid()
        mtfa_values: list[float] = []
        fixed_columns: dict[float, list[float]] = {
            frequency: [] for frequency in settings.mtf_sample_frequencies_cpd
        }
        zero_mtf: tuple[float, ...] | None = None
        runtime_meta: dict[str, object] | None = None
        try:
            for defocus_d in defocus_grid:
                object_surface.Thickness = object_thickness_for_defocus_d(
                    defocus_d,
                    infinity_thickness_mm=saved_object_thickness,
                )
                result = runner.run(
                    MfeMtfGridSettings(
                        frequencies_cyc_per_mm=frequencies_mm,
                        sampling_grid_size=self.sampling,
                        operand_type=TASK009_PAIR_MONO_MTF_ACQUISITION.production_operand,
                        wavelength_number=TASK009_PAIR_MONO_MTF_ACQUISITION.wavelength_number,
                        field_number=TASK009_PAIR_MONO_MTF_ACQUISITION.field_number,
                        grid=TASK009_PAIR_MONO_MTF_ACQUISITION.grid,
                        data_type=TASK009_PAIR_MONO_MTF_ACQUISITION.data_type,
                    )
                )
                avg = tuple(float(value) for value in result.values)
                if len(avg) != len(cpd_grid) or not all(math.isfinite(value) for value in avg):
                    raise R8DirectAcquisitionError(
                        f"incomplete/non-finite MTFA result: {spec.config_id}"
                    )
                if runtime_meta is None:
                    runtime_meta = {
                        "acquisition_contract_id": TASK009_PAIR_MONO_MTF_ACQUISITION.contract_id,
                        "acquisition_contract_hash": EXPECTED_PAIR_MONO_MTF_ACQUISITION_HASH,
                        "production_operand": result.operand_type,
                        "grid": result.grid,
                        "data_type": result.data_type,
                        "wavelength_number": TASK009_PAIR_MONO_MTF_ACQUISITION.wavelength_number,
                        "field_number": TASK009_PAIR_MONO_MTF_ACQUISITION.field_number,
                        "sampling_grid_size": result.sampling_grid_size,
                        "sampling_index": result.sampling_index,
                        "parameter_headers": result.parameter_headers,
                        "frequency_min_cycles_per_mm": frequencies_mm[0],
                        "frequency_max_cycles_per_mm": frequencies_mm[-1],
                        "frequency_count": len(frequencies_mm),
                        "cpd_min": cpd_grid[0],
                        "cpd_max": cpd_grid[-1],
                        "cpd_count": len(cpd_grid),
                        "frequency_scale_mode": PAIR_MONO_FREQUENCY_SCALE_MODE,
                    }
                mtfa_values.append(mtfa(cpd_grid, avg, max_cpd=settings.mtfa_max_cpd))
                for frequency, values in fixed_columns.items():
                    index = round(frequency / settings.mtf_frequency_step_cpd)
                    values.append(avg[index])
                if abs(defocus_d) <= 1.0e-12:
                    zero_mtf = avg
        finally:
            object_surface.Thickness = saved_object_thickness

        if float(object_surface.Thickness) != saved_object_thickness:
            raise R8DirectAcquisitionError("OBJECT thickness was not restored")
        if int(self.session.system.MFE.NumberOfOperands) != baseline_mfe:
            raise R8DirectAcquisitionError("through-focus acquisition left the MFE modified")
        if zero_mtf is None or runtime_meta is None:
            raise R8DirectAcquisitionError(
                f"R8 through-focus acquisition is incomplete: {spec.config_id}"
            )

        rows = with_shape_axis(
            defocus_grid,
            tuple(mtfa_values),
            tuple(
                tuple(fixed_columns[frequency])
                for frequency in settings.mtf_sample_frequencies_cpd
            ),
            peak_window_d=self.peak_search_window_d,
        )
        summary = summarize_mtfa_curve(rows, peak_window_d=self.peak_search_window_d)
        hoa = MfeFullHoaRunner(self.session.system, self.session.zosapi).run()
        if int(self.session.system.MFE.NumberOfOperands) != baseline_mfe:
            raise R8DirectAcquisitionError("HOA acquisition left the MFE modified")
        after = capture_direct_entity_snapshot(self.session, spec.platform_id)
        model_hash_after = sha256_file(working_model)
        if sha256_file(spec.source_path) != source_sha:
            raise R8DirectAcquisitionError(
                f"immutable R6/R7 source changed during acquisition: {spec.model_artifact_key}"
            )

        through_focus_csv = output / "through_focus.csv"
        through_focus_plot = output / "through_focus_mtfa.png"
        mtf_plot = output / "mtf_at_zero_d.png"
        _write_through_focus_csv(through_focus_csv, rows)
        _write_plots(rows, cpd_grid, zero_mtf, through_focus_plot, mtf_plot)

        self.diagnostics[spec.config_id] = {
            "source_model_path": str(spec.source_path),
            "source_model_sha256": source_sha,
            "working_model_path": str(working_model),
            "working_model_sha256": model_hash_before,
            "copy_on_write": True,
            "configured_stop_semi_diameter_mm": spec.stop_semi_diameter_mm,
            "pair_key": spec.pair_key,
            "pair_reference_effl_mm": reference_effl_mm,
            "pair_mm_per_degree": pair_scale,
            "state_diagnostic_effl_mm": state_effl_mm,
            "state_diagnostic_mm_per_degree": state_scale,
            "state_to_pair_effl_ratio": state_effl_mm / reference_effl_mm,
            "target_frequencies_cycles_per_mm": frequencies_mm,
            "mtf_runtime": runtime_meta,
            "footprint_failures": footprints.failures,
            "entity_before": asdict(before),
            "entity_after": asdict(after),
            "hoa_settings_id": hoa.settings_id,
            "hoa_settings_hash": hoa.settings_hash,
            "direct_model_provenance_policy_id": DIRECT_MODEL_PROVENANCE_POLICY_ID,
            "direct_model_provenance_policy_hash": DIRECT_MODEL_PROVENANCE_POLICY_HASH,
        }

        result = ConfigResult(
            config=config,
            run_id=run_id,
            rows=rows,
            distance_peak_retina_d=float(summary["distance_peak_retina_d"]),
            distance_peak_mtfa=float(summary["distance_peak_mtfa"]),
            mtfa_at_zero_d=float(summary["mtfa_at_zero_d"]),
            dof50_far_d=summary["dof50_far_d"],
            dof50_near_d=summary["dof50_near_d"],
            dof50_width_d=float(summary["dof50_width_d"]),
            dof50_far_censored=bool(summary["dof50_far_censored"]),
            dof50_near_censored=bool(summary["dof50_near_censored"]),
            tf_mtfa_mean=float(summary["tf_mtfa_mean"]),
            peak_search_censored=bool(summary["peak_search_censored"]),
            aberrations=AberrationSummary(hoa.c40_um, hoa.c60_um, hoa.hoa_rms_um),
            analysis_settings_hash=settings_hash(settings),
            hoa_settings_id=hoa.settings_id,
            hoa_settings_hash=hoa.settings_hash,
            cornea_footprint_mm=footprints.cornea_footprint_mm,
            stop_footprint_mm=footprints.stop_footprint_mm,
            iol_footprint_mm=footprints.iol_footprint_mm,
            iol_optical_diameter_mm=CONTROLLED_IOL_CARRIER_546_V1.optical_diameter_mm,
            model_hash_before=model_hash_before,
            model_hash_after=model_hash_after,
            entity_fingerprint_before=before.fingerprint,
            entity_fingerprint_after=after.fingerprint,
            retina_position_before_mm=before.retina_position_mm,
            retina_position_after_mm=after.retina_position_mm,
            iol_position_before_mm=before.iol_position_mm,
            iol_position_after_mm=after.iol_position_mm,
            elp_before_mm=before.elp_mm,
            elp_after_mm=after.elp_mm,
            unintended_vignetting=footprints.unintended_vignetting,
            artifacts=ConfigArtifacts(
                str(working_model),
                str(through_focus_csv),
                str(through_focus_plot),
                str(mtf_plot),
            ),
            completed=True,
        )
        validate_completed_result(
            result,
            require_files=True,
            expected_config=config,
            expected_run_id=run_id,
            analysis_settings=settings,
            peak_window_d=self.peak_search_window_d,
        )
        config_result_path = output / "config_result.json"
        config_result_path.write_text(
            json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self.diagnostics[spec.config_id]["config_result_json"] = str(config_result_path)
        self.diagnostics[spec.config_id]["config_result_json_sha256"] = sha256_file(
            config_result_path
        )
        return result


def matched_pair_delta_direct(
    mono: ConfigResult,
    edof: ConfigResult,
    *,
    analysis_settings: AnalysisSettings = NOMINAL_MAIN_FFT_MTF_555_V2,
    peak_search_window_d: float = 0.5,
) -> MatchedPairDelta:
    """Use the existing delta contract after direct-model provenance is attached to configs."""

    from .analysis import matched_pair_delta

    return matched_pair_delta(
        mono,
        edof,
        analysis_settings=analysis_settings,
        peak_window_d=peak_search_window_d,
    )


def build_direct_run(
    *,
    run_id: str,
    results: Sequence[ConfigResult],
    pairs: Sequence[DirectMatchedPair],
    references: Mapping[str, PairAngularScaleReference],
    source_model_sha256: Mapping[str, str],
    through_focus_planes: int = 15,
    analysis_settings: AnalysisSettings = NOMINAL_MAIN_FFT_MTF_555_V2,
    peak_search_window_d: float = 0.5,
) -> R8DirectRun:
    config_count = len(results)
    pair_count = len(pairs)
    if config_count != pair_count * 2:
        raise R8DirectAcquisitionError(
            "direct run requires exactly two optic states per matched pair"
        )
    by_id = {result.config.config_id: result for result in results}
    if len(by_id) != config_count:
        raise R8DirectAcquisitionError("direct completed config IDs are not unique")
    validate_pair_reference_map(pairs, references)

    deltas: list[MatchedPairDelta] = []
    for pair in pairs:
        try:
            mono = by_id[pair.mono.config_id]
            edof = by_id[pair.edof.config_id]
        except KeyError as exc:
            raise R8DirectAcquisitionError(
                f"R8 matched pair result is missing: {pair.pair_key}"
            ) from exc
        deltas.append(
            matched_pair_delta_direct(
                mono,
                edof,
                analysis_settings=analysis_settings,
                peak_search_window_d=peak_search_window_d,
            )
        )
    if len(deltas) != pair_count:
        raise R8DirectAcquisitionError(
            "direct run did not reconstruct every matched pair delta"
        )

    config_rows = tuple(config_scalar_row(result) for result in results)
    tf_rows = tuple(
        row
        for result in results
        for row in through_focus_rows(result)
    )
    paired_rows = tuple(paired_delta_row(delta) for delta in deltas)
    validate_aggregate_rows(
        config_rows,
        tf_rows,
        paired_rows,
        through_focus_planes=through_focus_planes,
        config_count=config_count,
        pair_count=pair_count,
    )
    return R8DirectRun(
        run_id=run_id,
        results=tuple(results),
        paired_deltas=tuple(deltas),
        pair_references=dict(references),
        source_model_sha256=dict(source_model_sha256),
        config_rows=config_rows,
        through_focus_rows=tf_rows,
        paired_rows=paired_rows,
    )


def run_r8_direct_acquisition(
    session: ZosSession,
    *,
    project_dir: Path,
    specs: Sequence[DirectModelSpec],
    output_root: Path,
    run_id: str,
    analysis_settings: AnalysisSettings = NOMINAL_MAIN_FFT_MTF_555_V2,
    peak_search_window_d: float = 0.5,
    expected_pair_count: int = 48,
    expected_model_count: int = 48,
) -> tuple[R8DirectRun, dict[str, dict[str, object]]]:
    """Execute the 48 pair references and 96 direct-model configs after offline preflight."""

    verify_direct_model_sources(specs, expected_model_count=expected_model_count)
    pairs = group_direct_pairs(specs, expected_pair_count=expected_pair_count)
    root = Path(output_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise R8DirectAcquisitionError(
            f"R8 runtime output directory is not empty: {root}"
        )
    root.mkdir(parents=True, exist_ok=True)

    reference_adapter = R8DirectModelAcquisitionAdapter(
        session,
        pair_reference_effl_mm={"__bootstrap__": 1.0},
        analysis_settings=analysis_settings,
        peak_search_window_d=peak_search_window_d,
    )
    references: dict[str, PairAngularScaleReference] = {}
    for pair in pairs:
        references[pair.pair_key] = reference_adapter.measure_pair_mono_reference(
            pair,
            root / "pair_references" / f"{pair.pair_key}.zmx",
        )
    validate_pair_reference_map(pairs, references)

    backend = R8DirectModelAcquisitionAdapter(
        session,
        pair_reference_effl_mm={
            key: value.reference_effl_mm for key, value in references.items()
        },
        analysis_settings=analysis_settings,
        peak_search_window_d=peak_search_window_d,
    )
    results: list[ConfigResult] = []
    for spec in specs:
        results.append(
            backend.run_config(
                spec,
                root / "configs" / spec.config_id,
                run_id,
            )
        )

    source_map = {
        spec.model_artifact_key: spec.source_sha256
        for spec in specs
    }
    direct_run = build_direct_run(
        run_id=run_id,
        results=results,
        pairs=pairs,
        references=references,
        source_model_sha256=source_map,
        through_focus_planes=len(analysis_settings.defocus_grid()),
        analysis_settings=analysis_settings,
        peak_search_window_d=peak_search_window_d,
    )
    return direct_run, backend.diagnostics


def write_r8_aggregate_outputs(
    direct_run: R8DirectRun,
    *,
    output_root: Path,
    config_csv_name: str,
    through_focus_csv_name: str,
    paired_csv_name: str,
) -> dict[str, Path]:
    root = Path(output_root).resolve()
    config_path = root / config_csv_name
    tf_path = root / through_focus_csv_name
    paired_path = root / paired_csv_name
    _write_csv(config_path, direct_run.config_rows)
    _write_csv(tf_path, direct_run.through_focus_rows)
    _write_csv(paired_path, direct_run.paired_rows)
    return {
        "config_csv": config_path,
        "through_focus_csv": tf_path,
        "paired_csv": paired_path,
    }


def artifact_hashes(root: Path, *, exclude_names: Sequence[str] = ()) -> dict[str, str]:
    output: dict[str, str] = {}
    excluded = set(exclude_names)
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and path.name not in excluded:
            output[str(path.relative_to(root)).replace("\\", "/")] = sha256_file(path)
    return output
