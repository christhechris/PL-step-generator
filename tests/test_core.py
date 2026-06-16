from pathlib import Path
import numpy as np
import pytest
from lantern_step import core

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "PL-260114-01-1550-19_profile.xlsx"


def test_load_profile_units_and_normalization():
    profile = core.load_profile(SAMPLE)
    # Z normalized to start at 0, in mm
    assert profile.z_raw.min() == pytest.approx(0.0)
    assert profile.z_raw.max() == pytest.approx(64.982, abs=1e-2)
    # radius in mm: known data range ~0.023 - 0.48 mm
    assert 0.02 < profile.r_raw.min() < 0.03
    assert 0.45 < profile.r_raw.max() < 0.50
    assert profile.z_raw.shape == profile.r_raw.shape


def test_load_profile_missing_columns(tmp_path):
    import pandas as pd
    bad = tmp_path / "bad.xlsx"
    pd.DataFrame({"foo": [1, 2], "bar": [3, 4]}).to_excel(bad, index=False)
    with pytest.raises(ValueError, match="missing expected column"):
        core.load_profile(bad)
