"""Repair every ```mermaid fenced block inside a Markdown document.

Leaves all other content untouched. Preserves the fence's indentation and the
exact info string (e.g. ```mermaid vs ```mermaid {theme}).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .sanitizer import RepairResult, repair

# Matches a fenced mermaid block, capturing indentation, the fence run, and the
# block body. Handles ``` and longer fences, and trailing info after "mermaid".
_MERMAID_BLOCK = re.compile(
    r"(?P<indent>[ \t]*)(?P<fence>`{3,})[ \t]*mermaid[^\n]*\n"
    r"(?P<body>.*?)"
    r"(?P=indent)(?P=fence)[ \t]*(?=\n|$)",
    re.DOTALL,
)


@dataclass
class MarkdownRepairResult:
    """Outcome of repairing all mermaid blocks in a markdown document."""

    text: str
    original: str
    changed: bool = False
    blocks_total: int = 0
    blocks_repaired: int = 0
    # One RepairResult per mermaid block found, in document order.
    block_results: list[RepairResult] = field(default_factory=list)


def repair_markdown(md: str) -> MarkdownRepairResult:
    """Find and repair every ```mermaid block in a markdown string."""
    block_results: list[RepairResult] = []
    counters = {"total": 0, "repaired": 0}

    def _replace(match: re.Match[str]) -> str:
        counters["total"] += 1
        indent = match.group("indent")
        fence = match.group("fence")
        info_line = match.group(0).split("\n", 1)[0]  # full opening fence line
        body = match.group("body")

        # The body may carry a trailing newline before the closing fence;
        # preserve layout by splitting that off.
        trailing_nl = "\n" if body.endswith("\n") else ""
        core = body[: -len(trailing_nl)] if trailing_nl else body

        result = repair(core)
        block_results.append(result)
        if result.changed:
            counters["repaired"] += 1

        return f"{info_line}\n{result.text}{trailing_nl}{indent}{fence}"

    new_text = _MERMAID_BLOCK.sub(_replace, md)

    return MarkdownRepairResult(
        text=new_text,
        original=md,
        changed=new_text != md,
        blocks_total=counters["total"],
        blocks_repaired=counters["repaired"],
        block_results=block_results,
    )
