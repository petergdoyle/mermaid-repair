"""Optional verification of Mermaid source against the real Mermaid engine.

Uses the Mermaid CLI (``mmdc``) if it is installed. This is the ground truth
the fixture test suite relies on: a repair is only "proven" when the original
fails to render AND the repaired source renders. ``mmdc`` is the same tool
md2pdf already depends on for rendering diagrams to PNG.

If ``mmdc`` is not installed, ``mmdc_available()`` returns False and callers
should skip verification rather than fail.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def mmdc_available() -> bool:
    """True if the Mermaid CLI (``mmdc``) is on PATH."""
    return shutil.which("mmdc") is not None


def renders(src: str, timeout: float = 60.0) -> bool:
    """Return True if ``mmdc`` renders ``src`` to SVG without error.

    Raises RuntimeError if ``mmdc`` is not installed — call ``mmdc_available()``
    first when you want to skip gracefully.
    """
    if not mmdc_available():
        raise RuntimeError("mmdc (Mermaid CLI) is not installed; cannot verify rendering.")

    with tempfile.TemporaryDirectory() as tmp:
        in_path = Path(tmp) / "diagram.mmd"
        out_path = Path(tmp) / "diagram.svg"
        in_path.write_text(src, encoding="utf-8")
        try:
            proc = subprocess.run(
                ["mmdc", "-i", str(in_path), "-o", str(out_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
        return proc.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0
