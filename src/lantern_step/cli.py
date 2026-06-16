"""Headless batch entry point for generating lantern STEP files."""
from __future__ import annotations

import argparse
import sys

from .core import (
    ModelParams,
    build_taper_model,
    export_step,
    load_profile,
    make_solid,
)
from .references import build_reference_bodies


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="lantern-step-cli",
        description="Generate a lantern taper STEP file from a fiber profile Excel file.",
    )
    parser.add_argument("input", help="Input Excel (.xlsx) profile file")
    parser.add_argument("-o", "--output", required=True, help="Output STEP file path")
    parser.add_argument("--start", type=float, default=None,
                        help="Start distance (mm); default = data start")
    parser.add_argument("--end", type=float, default=None,
                        help="End distance (mm); default = data end")
    parser.add_argument("--final-d", type=float, default=1.75,
                        help="Final diameter (mm); default 1.75")
    parser.add_argument("--ext", type=float, default=13.0,
                        help="Cylinder extension length (mm); default 13")
    parser.add_argument("--ref-d", type=float, nargs="*", default=[],
                        help="Reference-plane diameters (mm)")
    parser.add_argument("--ref-z", type=float, nargs="*", default=[],
                        help="Reference-plane axial positions z (mm)")
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.input)
    except Exception as e:  # missing file / bad columns
        print(f"error: {e}", file=sys.stderr)
        return 1

    start = args.start if args.start is not None else float(profile.z_raw.min())
    end = args.end if args.end is not None else float(profile.z_raw.max())
    params = ModelParams(start, end, args.final_d, args.ext)

    try:
        model = build_taper_model(profile, params)
        solid = make_solid(model)
        bodies, notes = build_reference_bodies(model, args.ref_d, args.ref_z)
        export_step(solid, bodies, args.output)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for note in notes:
        print(note)
    print(f"Wrote {args.output}  (length {model.z_cyl_end:.2f} mm, "
          f"final Ø {args.final_d:.2f} mm)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
