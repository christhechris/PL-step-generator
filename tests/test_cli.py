from pathlib import Path
import re
from lantern_step import cli

SAMPLE = Path(__file__).resolve().parents[1] / "examples" / "PL-260114-01-1550-19_profile.xlsx"


def test_cli_generates_solid(tmp_path, capsys):
    out = tmp_path / "cli.step"
    rc = cli.main([str(SAMPLE), "-o", str(out),
                   "--start", "5", "--end", "65", "--final-d", "1.2", "--ext", "13",
                   "--ref-d", "1.2", "--ref-z", "10", "30"])
    assert rc == 0
    text = out.read_text()
    assert "MANIFOLD_SOLID_BREP" in text
    assert "SHELL_BASED_SURFACE_MODEL" in text
    captured = capsys.readouterr().out
    assert "z = 10.00 mm" in captured


def test_cli_missing_file_returns_error(tmp_path, capsys):
    out = tmp_path / "x.step"
    rc = cli.main(["does_not_exist.xlsx", "-o", str(out)])
    assert rc == 1
    assert "error:" in capsys.readouterr().err
