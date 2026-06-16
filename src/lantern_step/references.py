"""Optional reference geometry (flat disks normal to the taper axis)."""
from __future__ import annotations

import numpy as np
import cadquery as cq

from .core import TaperModel


def solve_z_for_diameter(z_arr, r_arr, target_d):
    """Axial positions where the local diameter crosses target_d (sorted, deduped)."""
    target_r = target_d / 2.0
    g = np.asarray(r_arr) - target_r
    zs = []
    for i in range(len(g) - 1):
        a, b = g[i], g[i + 1]
        if a == 0.0:
            zs.append(float(z_arr[i]))
        elif a * b < 0:  # sign change -> crossing between samples
            t = a / (a - b)
            zs.append(float(z_arr[i] + t * (z_arr[i + 1] - z_arr[i])))
    if len(g) and g[-1] == 0.0:
        zs.append(float(z_arr[-1]))
    out = []
    for z in sorted(zs):
        if not out or abs(z - out[-1]) > 1e-3:
            out.append(z)
    return out


def local_radius_at(model: TaperModel, z) -> float:
    """Interpolate the part's local radius at axial position z."""
    z_full = np.concatenate([model.z_model_extended, [model.z_cyl_end]])
    r_full = np.concatenate([model.r_model_extended, [model.radius_final]])
    return float(np.interp(z, z_full, r_full))


def make_reference_disk(z, local_r):
    """A circular planar face (free surface body) normal to the Z axis at z."""
    margin = max(0.5, 0.25 * local_r)  # mm beyond the wall, for selectability
    wire = cq.Wire.makeCircle(local_r + margin, cq.Vector(0, 0, z), cq.Vector(0, 0, 1))
    return cq.Face.makeFromWires(wire)


def build_reference_bodies(model: TaperModel, diameters, positions):
    """Build reference disks for the given diameter and z stations.

    Returns (bodies, notes). Diameter stations are solved on the tapered portion
    only; out-of-range/unreachable stations are skipped and reported in notes.
    """
    z_full = np.concatenate([model.z_model_extended, [model.z_cyl_end]])
    bodies, notes = [], []
    for d in diameters:
        crossings = solve_z_for_diameter(
            model.z_model_extended, model.r_model_extended, d
        )
        if not crossings:
            notes.append(f"Ø{d:.3f} mm: not reached on taper - skipped")
            continue
        for zc in crossings:
            lr = local_radius_at(model, zc)
            bodies.append(make_reference_disk(zc, lr))
            notes.append(f"Ø{d:.3f} mm at z = {zc:.2f} mm")
    for zc in positions:
        if zc < z_full[0] or zc > z_full[-1]:
            notes.append(f"z = {zc:.2f} mm: outside part - skipped")
            continue
        lr = local_radius_at(model, zc)
        bodies.append(make_reference_disk(zc, lr))
        notes.append(f"z = {zc:.2f} mm (Ø{2 * lr:.3f} mm)")
    return bodies, notes
