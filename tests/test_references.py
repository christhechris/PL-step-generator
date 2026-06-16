from pathlib import Path
import re
import numpy as np
import pytest
from lantern_step import core, references
from OCP.BRepCheck import BRepCheck_Analyzer

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "PL-260114-01-1550-19_profile.xlsx"


def _model():
    profile = core.load_profile(SAMPLE)
    return core.build_taper_model(profile, core.ModelParams(5.0, 65.0, 1.2, 13.0))


def test_solve_z_for_diameter_dedupes_monotonic():
    z = np.array([0.0, 1.0, 2.0, 3.0])
    r = np.array([0.0, 0.5, 1.0, 1.5])  # diameter 0,1,2,3
    zs = references.solve_z_for_diameter(z, r, target_d=2.0)  # radius 1.0 at z=2
    assert zs == pytest.approx([2.0])


def test_build_reference_bodies_counts_and_notes():
    model = _model()
    bodies, notes = references.build_reference_bodies(
        model, diameters=[1.2, 0.5], positions=[10.0, 30.0, 999.0]
    )
    # 1.2 reached once on taper, 0.5 reached once (start=5 trims early crossing),
    # z=10 and z=30 valid, z=999 skipped.
    assert len(bodies) == 4
    assert any("outside part" in n for n in notes)


def test_reference_bodies_export_as_surface_bodies(tmp_path):
    model = _model()
    solid = core.make_solid(model)
    bodies, _ = references.build_reference_bodies(model, [1.2], [10.0])
    out = tmp_path / "refs.step"
    core.export_step(solid, bodies, out)
    text = out.read_text()
    assert "MANIFOLD_SOLID_BREP" in text          # solid intact
    assert "SHELL_BASED_SURFACE_MODEL" in text     # disks are surface bodies
    assert BRepCheck_Analyzer(solid.wrapped).IsValid()
