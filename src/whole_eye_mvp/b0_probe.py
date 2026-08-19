from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .domain import CORNEA_LOCK_B0_555_V2

B0_MTFA_PROBE_RELATIVE_PATH = (
    Path("diagnostics")
    / "task005d"
    / "b0_mtfa_probe"
    / "TASK_005D_MTFA_PROBE.json"
)


class B0ProbeEvidenceError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class B0ProbeEvidence:
    path: str
    runtime_passed: bool
    max_abs_q_difference_sampling_2_to_3: float
    max_abs_q_difference_sampling_3_to_4: float
    max_abs_q_difference_frequency_5_to_2_5: float


def _json_normalized(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise B0ProbeEvidenceError("Phase B.1 probe settings are not JSON-serializable") from exc


def validate_b0_probe_payload(
    payload: Mapping[str, Any],
    *,
    path: str = "<memory>",
) -> B0ProbeEvidence:
    """Validate Phase B.1 runtime evidence against the frozen v2 production settings.

    Historical probe JSON written before the consistency patch used ``passed=true``
    to mean that acquisition completed.  Accept that field only as a compatibility
    alias for ``runtime_passed``; neither spelling is treated as an automatic
    convergence threshold decision.
    """

    runtime_passed = payload.get("runtime_passed")
    if runtime_passed is None:
        runtime_passed = payload.get("passed")
    if runtime_passed is not True:
        raise B0ProbeEvidenceError("Phase B.1 MTFA probe did not complete successfully")

    expected_settings = _json_normalized(asdict(CORNEA_LOCK_B0_555_V2))
    actual_settings = _json_normalized(payload.get("settings"))
    if actual_settings != expected_settings:
        raise B0ProbeEvidenceError(
            "Phase B.1 probe settings do not match frozen CORNEA_LOCK_B0_555_v2"
        )

    sampling_results = payload.get("sampling_results")
    if not isinstance(sampling_results, Mapping) or not {"2", "3", "4"}.issubset(
        sampling_results
    ):
        raise B0ProbeEvidenceError("Phase B.1 probe lacks Samp=2/3/4 evidence")

    frequency_results = payload.get("frequency_step_results")
    if not isinstance(frequency_results, Mapping) or not {"5", "2.5"}.issubset(
        frequency_results
    ):
        raise B0ProbeEvidenceError("Phase B.1 probe lacks 5 vs 2.5 cycles/mm evidence")

    summary = payload.get("summary")
    if not isinstance(summary, Mapping):
        raise B0ProbeEvidenceError("Phase B.1 probe summary is missing")
    keys = (
        "max_abs_q_difference_sampling_2_to_3",
        "max_abs_q_difference_sampling_3_to_4",
        "max_abs_q_difference_frequency_5_to_2_5",
    )
    values: list[float] = []
    for key in keys:
        try:
            value = float(summary[key])
        except (KeyError, TypeError, ValueError) as exc:
            raise B0ProbeEvidenceError(f"Phase B.1 probe summary lacks finite {key}") from exc
        if not math.isfinite(value) or value < 0:
            raise B0ProbeEvidenceError(f"Phase B.1 probe summary has invalid {key}")
        values.append(value)

    return B0ProbeEvidence(
        path=path,
        runtime_passed=True,
        max_abs_q_difference_sampling_2_to_3=values[0],
        max_abs_q_difference_sampling_3_to_4=values[1],
        max_abs_q_difference_frequency_5_to_2_5=values[2],
    )


def require_b0_probe_evidence(project_dir: str | Path) -> B0ProbeEvidence:
    path = Path(project_dir).resolve() / B0_MTFA_PROBE_RELATIVE_PATH
    if not path.is_file():
        raise B0ProbeEvidenceError(
            "Phase B.1 MTFA evidence is missing; full B0 scan is blocked until the probe exists"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise B0ProbeEvidenceError("Phase B.1 MTFA evidence is unreadable") from exc
    if not isinstance(payload, Mapping):
        raise B0ProbeEvidenceError("Phase B.1 MTFA evidence must be a JSON object")
    return validate_b0_probe_payload(payload, path=str(path))
