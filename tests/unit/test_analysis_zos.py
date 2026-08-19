from __future__ import annotations

from types import SimpleNamespace

import pytest

from whole_eye_mvp.analysis_zos import capture_entity_snapshot
from whole_eye_mvp.base_assets import IMAGE_ROLE, STOP_ROLE
from whole_eye_mvp.carrier_zos import TASK007_CARRIER_ANT_ROLE, TASK007_CARRIER_POST_ROLE
from whole_eye_mvp.cornea_zos import FIXED_CORNEA_POST_ROLE


class Surface:
    def __init__(
        self,
        comment: str,
        *,
        radius: float = 0.0,
        conic: float = 0.0,
        thickness: float = 0.0,
        material: str = "",
        is_stop: bool = False,
        type_name: str = "Standard",
    ) -> None:
        self.Comment = comment
        self.Radius = radius
        self.Conic = conic
        self.Thickness = thickness
        self.Material = material
        self.IsStop = is_stop
        self.TypeName = type_name

    def GetType(self):
        return self.TypeName


class LDE:
    NumberOfSurfaces = 7
    StopSurface = 3

    def __init__(self) -> None:
        self.rows = {
            0: Surface("OBJECT", thickness=1.0e10),
            1: Surface("CORNEA_ANT", radius=7.8, thickness=0.55),
            2: Surface(FIXED_CORNEA_POST_ROLE, radius=6.5, thickness=3.15),
            3: Surface(STOP_ROLE, thickness=1.35, is_stop=True),
            4: Surface(
                TASK007_CARRIER_ANT_ROLE,
                radius=10.0,
                conic=-4.0,
                thickness=1.0,
                material="MODEL_IOL",
            ),
            5: Surface(TASK007_CARRIER_POST_ROLE, radius=-10.0, thickness=17.9),
            6: Surface(IMAGE_ROLE),
        }

    def GetSurfaceAt(self, index: int):
        return self.rows[index]


def session():
    return SimpleNamespace(system=SimpleNamespace(LDE=LDE()))


@pytest.mark.unit
def test_entity_fingerprint_excludes_object_vergence_but_covers_carrier_geometry() -> None:
    s = session()
    first = capture_entity_snapshot(s)
    s.system.LDE.GetSurfaceAt(0).Thickness = -1000.0
    second = capture_entity_snapshot(s)
    assert second.fingerprint == first.fingerprint

    s.system.LDE.GetSurfaceAt(4).Conic = -3.75
    third = capture_entity_snapshot(s)
    assert third.fingerprint != first.fingerprint
    assert third.q_ant == pytest.approx(-3.75)


@pytest.mark.unit
def test_entity_snapshot_reports_frozen_axial_landmarks() -> None:
    snap = capture_entity_snapshot(session())
    assert snap.iol_position_mm == pytest.approx(4.5)
    assert snap.elp_mm == pytest.approx(4.5)
    assert snap.retina_position_mm == pytest.approx(23.95)
    assert snap.radius_ant_mm == pytest.approx(10.0)
    assert snap.radius_post_mm == pytest.approx(-10.0)
