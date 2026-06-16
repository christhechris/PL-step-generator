"""Lantern taper STEP file generator."""
from .core import (
    ProfileData,
    ModelParams,
    TaperModel,
    load_profile,
    build_taper_model,
    make_solid,
    export_step,
)
from .references import (
    solve_z_for_diameter,
    local_radius_at,
    make_reference_disk,
    build_reference_bodies,
)

__version__ = "0.4.0"

__all__ = [
    "ProfileData", "ModelParams", "TaperModel",
    "load_profile", "build_taper_model", "make_solid", "export_step",
    "solve_z_for_diameter", "local_radius_at", "make_reference_disk",
    "build_reference_bodies", "__version__",
]
