"""Launch the GUI with `python -m lantern_step`.

Uses an absolute import (not ``from .gui``) so this module also works as a
PyInstaller entry script, where it runs as top-level ``__main__`` with no parent
package and a relative import would raise ImportError.
"""
from lantern_step.gui import main

if __name__ == "__main__":
    main()
