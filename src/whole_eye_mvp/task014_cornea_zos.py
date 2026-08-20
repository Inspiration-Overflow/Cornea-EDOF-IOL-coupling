from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .cornea_assets import (
    MAIN_CORNEA_SCAFFOLD,
    CorneaLockPrescription,
    distance_corrected_front_radius_mm,
)
from .cornea_candidates_zos import (
    A_CONIC_SCAN,
    C0_TRANSITION_SLICES_NOMINAL,
    CORNEA_SUPPORT_RADIUS_MM,
    CorneaCandidateMeasurement,
    _a_zones,
    _set_a_conic_profile,
    _solve_scalar_target,
    build_b_candidate,
    c0_binary4_zones,
    measure_best_focus_cornea_wavefront,
    measure_cornea_file_wavefront,
)
from .cornea_zos import DISTANCE_CORNEA_ANT_ROLE, build_reference_cornea_scaffold
from .domain import CorneaId, ScientificBaseline
from .task014_vertex_corrected_cornea import (
    TASK014_A0_ID,
    TASK014_B0_ID,
    TASK014_C0_ID,
    TASK014_RX_CONTRACT,
    task014_cornea_prescriptions,
)
from .zos import SequentialEditor, ZosSession


class Task014CorneaZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class Task014CorneaBuildResult:
    reference_path: str
    distance_path: str
    cornea_paths: dict[str, str]
    reference_wavefront: dict[str, float]
    distance_wavefront: dict[str, float]
    measurements: dict[str, dict[str, object]]


def build_task014_distance_cornea(
    session: ZosSession,
    baseline: ScientificBaseline,
    base_asset_path: str | Path,
    destination: str | Path,
) -> Path:
    """Build the TASK-014 distance cornea using the frozen spectacle-to-cornea conversion."""

    TASK014_RX_CONTRACT.validate()
    output = Path(destination)
    build_reference_cornea_scaffold(session, baseline, base_asset_path, output)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, f"{DISTANCE_CORNEA_ANT_ROLE}_V12")
    treatment = TASK014_RX_CONTRACT.corneal_plane_distance_treatment_d
    editor.set_radius_conic(
        1,
        radius_mm=distance_corrected_front_radius_mm(treatment),
        conic=MAIN_CORNEA_SCAFFOLD.front_conic,
    )
    editor.save_as(output)
    return output


def _build_a0v12(
    session: ZosSession,
    prescription: CorneaLockPrescription,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
) -> CorneaCandidateMeasurement:
    if prescription.candidate_id != TASK014_A0_ID or prescription.cornea_id != CorneaId.A0:
        raise Task014CorneaZosError("A0V12 prescription identity mismatch")
    session.system.LoadFile(str(Path(distance_cornea_path).resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, "CORNEA_ANT_A0V12")
    editor.configure_binary4(
        1,
        _a_zones(prescription, MAIN_CORNEA_SCAFFOLD.front_conic),
    )
    editor.set_radius_conic(
        1,
        radius_mm=prescription.distance_front_radius_mm,
        conic=MAIN_CORNEA_SCAFFOLD.front_conic,
    )
    editor.surface(1).SemiDiameter = CORNEA_SUPPORT_RADIUS_MM
    target = float(prescription.target_delta_c40_um)

    def setter(conic: float) -> None:
        _set_a_conic_profile(editor, prescription, conic)

    def evaluator() -> float:
        return measure_best_focus_cornea_wavefront(session).c40_um - reference_c40_um

    conic, _ = _solve_scalar_target(setter, evaluator, A_CONIC_SCAN, target)
    setter(conic)
    wavefront = measure_best_focus_cornea_wavefront(session)
    output = Path(destination)
    editor.save_as(output)
    return CorneaCandidateMeasurement(
        candidate_id=TASK014_A0_ID,
        surface_family=prescription.surface_family,
        target_delta_c40_um=target,
        achieved_delta_c40_um=wavefront.c40_um - reference_c40_um,
        reference_c40_um=reference_c40_um,
        candidate_c40_um=wavefront.c40_um,
        control_name="inner_zone_conic",
        control_value=conic,
        wavefront=wavefront,
    )


def _build_b0v12(
    session: ZosSession,
    prescription: CorneaLockPrescription,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
) -> CorneaCandidateMeasurement:
    if prescription.candidate_id != TASK014_B0_ID or prescription.cornea_id != CorneaId.B0:
        raise Task014CorneaZosError("B0V12 prescription identity mismatch")
    result = build_b_candidate(
        session,
        prescription,
        distance_cornea_path,
        destination,
        reference_c40_um,
    )
    if result.control_name != "even_asphere_r4":
        raise Task014CorneaZosError("B0V12 builder returned an unexpected control")
    return result


def _build_c0v12(
    session: ZosSession,
    prescription: CorneaLockPrescription,
    distance_cornea_path: str | Path,
    destination: str | Path,
    reference_c40_um: float,
) -> CorneaCandidateMeasurement:
    if prescription.candidate_id != TASK014_C0_ID or prescription.cornea_id != CorneaId.C0:
        raise Task014CorneaZosError("C0V12 prescription identity mismatch")
    session.system.LoadFile(str(Path(distance_cornea_path).resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    editor.set_comment(1, f"CORNEA_ANT_C0V12_N{C0_TRANSITION_SLICES_NOMINAL}")
    zones = c0_binary4_zones(prescription, C0_TRANSITION_SLICES_NOMINAL)
    editor.configure_binary4(1, zones)
    editor.set_radius_conic(1, radius_mm=zones[0].radius, conic=zones[0].conic)
    editor.surface(1).SemiDiameter = zones[-1].radial_aperture
    wavefront = measure_best_focus_cornea_wavefront(session)
    output = Path(destination)
    editor.save_as(output)
    return CorneaCandidateMeasurement(
        candidate_id=TASK014_C0_ID,
        surface_family=prescription.surface_family,
        target_delta_c40_um=None,
        achieved_delta_c40_um=wavefront.c40_um - reference_c40_um,
        reference_c40_um=reference_c40_um,
        candidate_c40_um=wavefront.c40_um,
        control_name="transition_slices",
        control_value=float(C0_TRANSITION_SLICES_NOMINAL),
        wavefront=wavefront,
    )


def build_task014_cornea_assets(
    session: ZosSession,
    baseline: ScientificBaseline,
    lb_base_path: str | Path,
    output_dir: str | Path,
) -> Task014CorneaBuildResult:
    """Build the three vertex-corrected postoperative corneas from one common reference."""

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    reference_path = root / "REFERENCE_CORNEA.zmx"
    distance_path = root / "DISTANCE_CORNEA_VERTEX12.zmx"
    a_path = root / f"CORNEA_{TASK014_A0_ID}.zmx"
    b_path = root / f"CORNEA_{TASK014_B0_ID}.zmx"
    c_path = root / f"CORNEA_{TASK014_C0_ID}.zmx"

    build_reference_cornea_scaffold(session, baseline, lb_base_path, reference_path)
    reference_wavefront = measure_cornea_file_wavefront(session, reference_path)
    reference_c40 = reference_wavefront.c40_um
    build_task014_distance_cornea(session, baseline, lb_base_path, distance_path)
    distance_wavefront = measure_cornea_file_wavefront(session, distance_path)

    a_rx, b_rx, c_rx = task014_cornea_prescriptions(baseline)
    a = _build_a0v12(session, a_rx, distance_path, a_path, reference_c40)
    b = _build_b0v12(session, b_rx, distance_path, b_path, reference_c40)
    c = _build_c0v12(session, c_rx, distance_path, c_path, reference_c40)
    if not a.target_passed:
        raise Task014CorneaZosError("A0V12 achieved ΔC40 is outside construction tolerance")
    if not b.target_passed:
        raise Task014CorneaZosError("B0V12 achieved ΔC40 is outside construction tolerance")

    return Task014CorneaBuildResult(
        reference_path=str(reference_path.resolve()),
        distance_path=str(distance_path.resolve()),
        cornea_paths={
            TASK014_A0_ID: str(a_path.resolve()),
            TASK014_B0_ID: str(b_path.resolve()),
            TASK014_C0_ID: str(c_path.resolve()),
        },
        reference_wavefront=asdict(reference_wavefront),
        distance_wavefront=asdict(distance_wavefront),
        measurements={
            TASK014_A0_ID: asdict(a),
            TASK014_B0_ID: asdict(b),
            TASK014_C0_ID: asdict(c),
        },
    )
