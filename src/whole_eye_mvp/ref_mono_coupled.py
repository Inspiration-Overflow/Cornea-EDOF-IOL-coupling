from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .domain import ScientificBaseline
from .ref_mono import REF_MONO_ENVELOPE
from .ref_mono_calibration import (
    REF_MONO_SA_NEUTRAL_TOLERANCE_UM,
    RefMonoSaCalibration,
    measure_ref_mono_sa_delta,
    solve_ref_mono_neutral_conic,
)
from .ref_mono_zos import (
    RefMonoMeasurements,
    build_ref_mono_on_cornea_candidate,
    measure_ref_mono_candidate,
    solve_ref_mono_radius_mm,
    validate_ref_mono_measurements,
)
from .zos import SequentialEditor, ZosSession

MAX_REF_MONO_COUPLED_ROUNDS = 2


class RefMonoCoupledError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RefMonoCoupledResult:
    rounds: int
    ref_mono: RefMonoMeasurements
    standard_eye: RefMonoSaCalibration

    @property
    def passed(self) -> bool:
        return (
            abs(self.ref_mono.focus_shift_mm) <= 0.001
            and abs(self.standard_eye.delta_c40_um) <= REF_MONO_SA_NEUTRAL_TOLERANCE_UM
        )


def _enforce_optic_and_refocus(
    session: ZosSession,
    baseline: ScientificBaseline,
    path: Path,
    initial_radius_mm: float,
) -> RefMonoMeasurements:
    session.system.LoadFile(str(path.resolve()), False)
    editor = SequentialEditor(session.system, session.zosapi)
    semi_diameter = REF_MONO_ENVELOPE.optic_diameter_mm / 2.0
    editor.surface(4).SemiDiameter = semi_diameter
    editor.surface(5).SemiDiameter = semi_diameter
    solve_ref_mono_radius_mm(
        session,
        baseline,
        initial_radius_mm=initial_radius_mm,
    )
    editor.save_as(path)
    return measure_ref_mono_candidate(session, baseline, path)


def calibrate_ref_mono_for_cornea(
    session: ZosSession,
    baseline: ScientificBaseline,
    cornea_path: str | Path,
    standard_eye_path: str | Path,
    destination: str | Path,
    *,
    max_rounds: int = MAX_REF_MONO_COUPLED_ROUNDS,
) -> RefMonoCoupledResult:
    """Solve candidate-specific REF_MONO focus and near-neutral standard-eye C40."""

    if max_rounds < 1 or max_rounds > MAX_REF_MONO_COUPLED_ROUNDS:
        raise ValueError(
            f"REF_MONO coupled rounds must lie in [1, {MAX_REF_MONO_COUPLED_ROUNDS}]"
        )

    output = Path(destination)
    ref = build_ref_mono_on_cornea_candidate(
        session,
        baseline,
        cornea_path,
        output,
    )
    ref = _enforce_optic_and_refocus(session, baseline, output, ref.radius_ant_mm)
    findings = validate_ref_mono_measurements(ref, baseline)
    if findings:
        raise RefMonoCoupledError("initial REF_MONO validation failed: " + " | ".join(findings))

    radius = ref.radius_ant_mm
    for round_number in range(1, max_rounds + 1):
        standard_eye = solve_ref_mono_neutral_conic(
            session,
            baseline,
            standard_eye_path,
            radius,
        )
        ref = build_ref_mono_on_cornea_candidate(
            session,
            baseline,
            cornea_path,
            output,
            conic=standard_eye.conic,
            initial_radius_mm=radius,
        )
        ref = _enforce_optic_and_refocus(session, baseline, output, ref.radius_ant_mm)
        findings = validate_ref_mono_measurements(ref, baseline)
        if findings:
            raise RefMonoCoupledError(
                f"REF_MONO round {round_number} validation failed: " + " | ".join(findings)
            )
        final_standard_eye = measure_ref_mono_sa_delta(
            session,
            baseline,
            standard_eye_path,
            ref.radius_ant_mm,
            ref.conic,
        )
        result = RefMonoCoupledResult(round_number, ref, final_standard_eye)
        if result.passed:
            return result
        radius = ref.radius_ant_mm

    raise RefMonoCoupledError(
        "REF_MONO coupled power/conic solve did not satisfy both focus and SA-neutral gates"
    )
