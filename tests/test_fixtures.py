"""Parser-verified fixture tests.

Each ``.mmd`` fixture is a real broken diagram (captured from LLM output). The
guarantee this suite enforces, using the actual Mermaid engine (``mmdc``):

    1. the ORIGINAL fixture FAILS to render, and
    2. the REPAIRED fixture RENDERS.

This is what keeps the project out of whack-a-mole territory: correctness is
proven against Mermaid itself, not against our own regex confidence. When a new
failure pattern appears in the wild, drop the raw broken diagram into
``tests/fixtures/`` and (if needed) add/extend a rule — the test proves it.

If ``mmdc`` is not installed, the render-verification tests are skipped (and a
regex-only sanity check still runs so the suite remains useful in bare CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mermaid_repair import mmdc_available, renders, repair

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES = sorted(FIXTURES_DIR.glob("*.mmd"))

# Guard against an empty glob silently passing.
assert FIXTURES, f"no fixtures found in {FIXTURES_DIR}"


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_repair_changes_broken_fixture(fixture: Path):
    """Every broken fixture should actually be modified by the sanitizer."""
    src = fixture.read_text(encoding="utf-8")
    result = repair(src)
    assert result.changed, f"{fixture.name}: expected sanitizer to change broken source"
    assert result.rules_applied, f"{fixture.name}: expected at least one rule to fire"


@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_repair_is_idempotent(fixture: Path):
    """Repairing an already-repaired fixture must be a no-op."""
    src = fixture.read_text(encoding="utf-8")
    once = repair(src).text
    twice = repair(once)
    assert not twice.changed, f"{fixture.name}: repair is not idempotent"


@pytest.mark.mmdc
@pytest.mark.skipif(not mmdc_available(), reason="mmdc (Mermaid CLI) not installed")
@pytest.mark.parametrize("fixture", FIXTURES, ids=lambda p: p.stem)
def test_original_fails_repaired_renders(fixture: Path):
    """Ground truth: original fails in Mermaid, repaired renders."""
    src = fixture.read_text(encoding="utf-8")

    assert not renders(src), (
        f"{fixture.name}: original was expected to FAIL rendering but it rendered. "
        "Either the fixture is not actually broken, or it no longer represents a real defect."
    )

    repaired = repair(src).text
    assert renders(repaired), (
        f"{fixture.name}: repaired source still does NOT render. "
        "A rule needs to be added or extended for this failure pattern."
    )
