from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base_assets import BaseAssetPrescription, base_asset_prescriptions, build_base_asset
from .domain import ScientificBaseline
from .model_revision import MODEL_REVISION_ID
from .model_revision_zos import (
    RevisionGeometryReadback,
    apply_revision_to_cornea_scaffold,
    read_revision_geometry,
    validate_revision_geometry,
)
from .zos import SequentialEditor, ZosSession


class RevisionBaseZosError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RevisionBasePrescription:
    source: BaseAssetPrescription
    artifact_id: str
    relative_path: str

    def validate(self) -> None:
        self.source.validate()
        if not self.artifact_id.strip() or not self.relative_path.strip():
            raise ValueError("revision base artifact ID/path are required")
        if not self.relative_path.lower().endswith(".zmx"):
            raise ValueError("revision base path must end in .zmx")


@dataclass(frozen=True, slots=True)
class RevisionBaseBuildResult:
    revision_id: str
    base_id: str
    path: str
    geometry: RevisionGeometryReadback


_REVISION_BASE_PATHS = {
    "LB_AL2395": (
        "REVISION_R2_BASE_LB",
        "models/revision/r2/REVISION_R2_BASE_LB.zmx",
    ),
    "ATC_M3_AL24477": (
        "REVISION_R2_BASE_ATC_M3",
        "models/revision/r2/REVISION_R2_BASE_ATC_M3.zmx",
    ),
}


def revision_base_prescriptions(
    baseline: ScientificBaseline,
) -> tuple[RevisionBasePrescription, ...]:
    result: list[RevisionBasePrescription] = []
    for source in base_asset_prescriptions(baseline):
        try:
            artifact_id, relative_path = _REVISION_BASE_PATHS[str(source.base_spec.base_id)]
        except KeyError as exc:
            raise RevisionBaseZosError(
                f"no post-audit base path for {source.base_spec.base_id}"
            ) from exc
        item = RevisionBasePrescription(source, artifact_id, relative_path)
        item.validate()
        result.append(item)
    return tuple(result)


def build_revision_base_asset(
    session: ZosSession,
    prescription: RevisionBasePrescription,
    destination: str | Path,
    *,
    pupil_diameter_mm: float = 3.0,
) -> RevisionBaseBuildResult:
    """Build a new post-audit base without touching the locked TASK-005B asset."""

    prescription.validate()
    output = Path(destination)
    build_base_asset(session, prescription.source, output)
    apply_revision_to_cornea_scaffold(
        session,
        prescription.source.base_spec.base_id,
        pupil_diameter_mm=pupil_diameter_mm,
    )
    SequentialEditor(session.system, session.zosapi).save_as(output)

    # Reload the exact serialized file before accepting the geometry.
    session.system.LoadFile(str(output.resolve()), False)
    geometry = read_revision_geometry(
        session,
        prescription.source.base_spec.base_id,
        full_eye=False,
    )
    findings = validate_revision_geometry(
        geometry,
        prescription.source.base_spec.base_id,
        expected_pupil_diameter_mm=pupil_diameter_mm,
    )
    if findings:
        raise RevisionBaseZosError(
            "revised base readback failed: " + " | ".join(findings)
        )
    return RevisionBaseBuildResult(
        revision_id=MODEL_REVISION_ID,
        base_id=str(prescription.source.base_spec.base_id),
        path=str(output.resolve()),
        geometry=geometry,
    )
