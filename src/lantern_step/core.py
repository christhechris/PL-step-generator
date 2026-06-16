"""Pure data-processing and geometry pipeline (no Qt)."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.interpolate import make_interp_spline
import cadquery as cq
from cadquery import exporters

# Column names as they appear in the measurement Excel files.
EXPECTED_COLUMNS = (
    "Left Z Motor  - Bottom Camera",
    "Fiber Diameter - Bottom Camera",
    "Fiber Diameter - Side Camera",
)


@dataclass
class ProfileData:
    z_raw: np.ndarray  # axial position, mm (normalized to start at 0)
    r_raw: np.ndarray  # radius, mm


def load_profile(path) -> ProfileData:
    """Load a fiber profile Excel file into mm-unit z/radius arrays."""
    df = pd.read_excel(path, sheet_name=0)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            "Excel file is missing expected column(s): "
            + ", ".join(repr(c) for c in missing)
        )
    df = df[list(EXPECTED_COLUMNS)].dropna()
    df.columns = ["Z", "Diameter_X", "Diameter_Y"]
    df["Z"] = df["Z"] - df["Z"].min()  # normalize start to 0 (µm)
    diameter = (df["Diameter_X"] + df["Diameter_Y"]) / 2.0  # µm
    radius = diameter / 2.0  # µm
    z_raw = df["Z"].values * 1e-3       # µm -> mm
    r_raw = radius.values * 1e-3        # µm -> mm
    return ProfileData(z_raw=z_raw, r_raw=r_raw)
