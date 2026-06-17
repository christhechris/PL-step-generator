"""The frozen-app self-test hook (LANTERN_STEP_SELFTEST) used by CI smoke tests."""
import os
import subprocess
import sys


def test_selftest_mode_exits_zero():
    # Run the real module entry point the way the frozen app does, with the
    # self-test env var set. It must import the GUI/core/OCCT graph and exit 0
    # WITHOUT opening a window.
    env = dict(os.environ, LANTERN_STEP_SELFTEST="1", QT_QPA_PLATFORM="offscreen")
    result = subprocess.run(
        [sys.executable, "-m", "lantern_step"],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert result.returncode == 0, result.stderr
    assert "LANTERN_STEP_SELFTEST OK" in result.stdout
