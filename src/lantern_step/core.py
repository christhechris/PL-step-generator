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


@dataclass
class ModelParams:
    start_distance: float    # mm
    end_distance: float      # mm
    final_diameter: float    # mm
    extension_length: float  # mm


@dataclass
class TaperModel:
    z_model: np.ndarray
    r_model: np.ndarray
    z_extrap_points: np.ndarray
    r_extrap_points: np.ndarray
    z_model_extended: np.ndarray
    r_model_extended: np.ndarray
    z_extrapolated: float
    radius_final: float
    extension_length: float
    z_cyl_end: float


def build_taper_model(profile: ProfileData, params: ModelParams) -> TaperModel:
    """Smooth the profile, extrapolate to the final diameter, build modeled arrays."""
    z_raw, r_raw = profile.z_raw, profile.r_raw

    # Cubic spline smoothing over the full measured profile.
    spline = make_interp_spline(z_raw, r_raw, k=3)
    z_smooth = np.linspace(z_raw.min(), z_raw.max(), 100)
    r_smooth = spline(z_smooth)

    # Restrict to the requested axial range.
    mask = (z_smooth >= params.start_distance) & (z_smooth <= params.end_distance)
    z_model = z_smooth[mask]
    r_model = r_smooth[mask]
    if len(z_model) < 2:
        raise ValueError("Selected start/end range contains too few points to model.")

    radius_final = params.final_diameter / 2.0

    # Linear fit over the last 1 mm (or all points if the range is short).
    if z_model[-1] - 1 < z_model[0]:
        idx = np.arange(len(z_model))
    else:
        idx = np.where(z_model >= (z_model[-1] - 1))[0]
    m, b = np.polyfit(z_model[idx], r_model[idx], 1)

    if np.abs(m) < 1e-6:
        z_extrapolated = z_model[-1]
    else:
        z_extrapolated = (radius_final - b) / m
    z_extrapolated = max(z_extrapolated, z_model[-1])  # never go backwards

    z_extrap_points = np.linspace(z_model[-1], z_extrapolated, 101)[1:]
    r_extrap_points = np.linspace(r_model[-1], radius_final, 101)[1:]
    z_model_extended = np.concatenate([z_model, z_extrap_points])
    r_model_extended = np.concatenate([r_model, r_extrap_points])

    # Guard against spline overshoot producing non-physical radii (floor at 1 µm).
    r_model_extended = np.clip(r_model_extended, 1e-3, None)

    z_cyl_end = z_extrapolated + params.extension_length
    return TaperModel(
        z_model=z_model,
        r_model=r_model,
        z_extrap_points=z_extrap_points,
        r_extrap_points=r_extrap_points,
        z_model_extended=z_model_extended,
        r_model_extended=r_model_extended,
        z_extrapolated=float(z_extrapolated),
        radius_final=float(radius_final),
        extension_length=float(params.extension_length),
        z_cyl_end=float(z_cyl_end),
    )
