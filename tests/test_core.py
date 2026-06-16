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


def test_build_taper_model_basic():
    profile = core.load_profile(SAMPLE)
    params = core.ModelParams(start_distance=5.0, end_distance=65.0,
                              final_diameter=1.2, extension_length=13.0)
    model = core.build_taper_model(profile, params)
    # final radius reached, radii floored positive, z stations ordered
    assert model.radius_final == pytest.approx(0.6)
    assert model.r_model_extended.min() >= 1e-3
    assert model.z_extrapolated >= model.z_model[-1]
    assert model.z_cyl_end == pytest.approx(model.z_extrapolated + 13.0)
    assert model.r_model_extended[-1] == pytest.approx(0.6, abs=1e-6)


def test_build_taper_model_clamps_when_final_smaller():
    profile = core.load_profile(SAMPLE)
    params = core.ModelParams(5.0, 65.0, final_diameter=0.5, extension_length=13.0)
    model = core.build_taper_model(profile, params)
    # final diameter below the measured end -> extrapolation cannot go backwards
    assert model.z_extrapolated == pytest.approx(model.z_model[-1])


def test_build_taper_model_empty_range_raises():
    profile = core.load_profile(SAMPLE)
    params = core.ModelParams(100.0, 200.0, 1.2, 13.0)  # outside data
    with pytest.raises(ValueError, match="too few points"):
        core.build_taper_model(profile, params)
