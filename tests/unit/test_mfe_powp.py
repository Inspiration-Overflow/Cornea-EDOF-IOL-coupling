from __future__ import annotations

import pytest

from whole_eye_mvp.zos.mfe_powp import MfePowpError, MfePowpRunner, MfePowpSettings


class _Cell:
    def __init__(self, header: str) -> None:
        self.Header = header


class _Operand:
    def __init__(self, headers: dict[int, str]) -> None:
        self._headers = headers

    def GetCellAt(self, position: int) -> _Cell:
        if position not in self._headers:
            raise IndexError(position)
        return _Cell(self._headers[position])


def test_powp_settings_are_frozen_to_center_pupil_spherical_power() -> None:
    MfePowpSettings(surface=4).validate()
    with pytest.raises(ValueError, match="spherical power"):
        MfePowpSettings(surface=4, data=4).validate()
    with pytest.raises(ValueError, match="\[-1, 1\]"):
        MfePowpSettings(surface=4, px=1.1).validate()


def test_powp_header_resolution_requires_documented_cells() -> None:
    headers = {
        2: "Surf",
        3: "Wave",
        4: "Hx",
        5: "Hy",
        6: "Px",
        7: "Py",
        8: "Data",
    }
    operand = _Operand(headers)
    parsed = MfePowpRunner._parameter_headers(operand)
    cells = MfePowpRunner._resolve_cells(operand, parsed)
    assert set(cells) == {"Surf", "Wave", "Hx", "Hy", "Px", "Py", "Data"}

    broken = _Operand({key: value for key, value in headers.items() if value != "Data"})
    with pytest.raises(MfePowpError, match="Data"):
        MfePowpRunner._resolve_cells(broken, MfePowpRunner._parameter_headers(broken))
