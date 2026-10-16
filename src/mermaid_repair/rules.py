"""Independent, named repair rules for Mermaid diagram source.

Each rule is a pure function ``(src: str) -> RuleOutcome`` that repairs one
class of common LLM syntax mistake. Rules are deliberately small and isolated
so they can be tested one at a time and reasoned about in isolation.

The failure space these rules target is defined by *Mermaid's grammar*, not by
any particular model: every LLM trips on the same finite set of sharp edges
(unquoted labels, dropped arrowheads, unclosed subgraphs, dangling style refs).
We specialize on the grammar, never on a model id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class RuleOutcome:
    """Result of applying a single rule."""

    text: str
    changed: bool = False
    # Human-readable notes describing what was changed (for diagnostics).
    notes: list[str] = field(default_factory=list)


# Lines that must never be rewritten by label/arrow rules.
_SKIP_PREFIXES = ("%%", "classDef", "class ", "style ", "linkStyle")


def _skip_line(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith(_SKIP_PREFIXES)


# ──────────────────────────────────────────────────────────────────────────
# Rule: fix_arrows
# ──────────────────────────────────────────────────────────────────────────
def fix_arrows(src: str) -> RuleOutcome:
    """Complete malformed edges that are missing an arrowhead.

    LLMs frequently drop the final ``-`` or ``>`` of an arrow:
      ``A --|label| B``   -> ``A -->|label| B``   (solid)
      ``A -.|label| B``   -> ``A -.->|label| B``  (dotted)
    """
    notes: list[str] = []
    out_lines: list[str] = []
    for line in src.split("\n"):
        if _skip_line(line):
            out_lines.append(line)
            continue
        original = line
        # Solid: `--|` (not already `-->|` or part of a longer dash run that
        # forms a valid arrow). Require a non-dash/dot/angle char before.
        line = re.sub(r"([^-.<>])--\|", r"\1-->|", line)
        # Dotted: `-.|` -> `-.->|`
        line = re.sub(r"-\.\|", r"-.->|", line)
        if line != original:
            notes.append(f"fixed edge arrow: {original.strip()!r} -> {line.strip()!r}")
        out_lines.append(line)
    text = "\n".join(out_lines)
    return RuleOutcome(text=text, changed=bool(notes), notes=notes)


# ──────────────────────────────────────────────────────────────────────────
# Rule: quote_labels (+ cylinder labels)
# ──────────────────────────────────────────────────────────────────────────
# Node shapes ordered so composite delimiters ([( )], ([ ])) are handled before
# the simple ones. Each entry is (open, close, compiled_regex). The regex uses a
# guard so a simple shape never matches the inner bracket of a composite shape,
# and matches the closing delimiter as a whole token so inner parentheses stay
# inside the label.
_NODE_SHAPE_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    # cylinder/database: id[( ... )]
    ("[(", ")]", re.compile(r"([A-Za-z0-9_]+)\[\(((?:(?!\)\]).)*)\)\]")),
    # stadium: id([ ... ])
    ("([", "])", re.compile(r"([A-Za-z0-9_]+)\(\[((?:(?!\]\)).)*)\]\)")),
    # rectangle: id[ ... ]  (not id[( )
    ("[", "]", re.compile(r"([A-Za-z0-9_]+)\[(?!\()((?:(?!\]).)*)\]")),
    # round: id( ... )  — the id must be a word char run; the cylinder's inner
    # "(" is preceded by "[" (not a word char) so it is never matched here, and
    # "(?!\[)" avoids matching the "([" stadium opener.
    ("(", ")", re.compile(r"([A-Za-z0-9_]+)\((?!\[)((?:(?!\)).)*)\)")),
    # rhombus: id{ ... }
    ("{", "}", re.compile(r"([A-Za-z0-9_]+)\{((?:(?!\}).)*)\}")),
]

# Characters that force a label to be quoted in Mermaid.
_NEEDS_QUOTE = re.compile(r"[<>()/&]")
_BR_TAG = re.compile(r"<br\s*/?>", re.IGNORECASE)


def quote_labels(src: str) -> RuleOutcome:
    """Wrap node labels in double quotes when they contain characters Mermaid
    cannot parse unquoted: parentheses, ``<br/>``, slashes, angle brackets, ``&``.

    Cylinder/database shapes keep the quotes *inside* the brackets:
      ``D[(Orders)]`` -> ``D[("Orders")]``
    Other shapes quote the label directly:
      ``A[Svc<br/>(x)]`` -> ``A["Svc<br/>(x)"]``
    """
    notes: list[str] = []
    out_lines: list[str] = []

    for line in src.split("\n"):
        if _skip_line(line):
            out_lines.append(line)
            continue

        original = line
        for open_delim, close_delim, pattern in _NODE_SHAPE_RULES:

            def _replace(match: re.Match[str], _open=open_delim, _close=close_delim) -> str:
                node_id = match.group(1)
                label = match.group(2)
                stripped = label.strip()
                if stripped.startswith('"') and stripped.endswith('"'):
                    return match.group(0)  # already quoted
                if _NEEDS_QUOTE.search(label) or _BR_TAG.search(label):
                    safe = label.replace('"', "&quot;")
                    return f'{node_id}{_open}"{safe}"{_close}'
                return match.group(0)

            line = pattern.sub(_replace, line)

        if line != original:
            notes.append(f"quoted label(s): {original.strip()!r} -> {line.strip()!r}")
        out_lines.append(line)

    text = "\n".join(out_lines)
    return RuleOutcome(text=text, changed=bool(notes), notes=notes)


# ──────────────────────────────────────────────────────────────────────────
# Rule: close_subgraphs
# ──────────────────────────────────────────────────────────────────────────
_SUBGRAPH_OPEN = re.compile(r"^\s*subgraph\b")
_END = re.compile(r"^\s*end\s*$")


def close_subgraphs(src: str) -> RuleOutcome:
    """Append missing ``end`` statements for unbalanced ``subgraph`` blocks.

    Counts opens vs. ends; if there are more opens, append the needed number of
    ``end`` lines. Conservative: only adds, never removes. Does nothing when the
    counts already balance (or when there are more ``end`` than ``subgraph``,
    which this rule is not responsible for).
    """
    opens = 0
    ends = 0
    for line in src.split("\n"):
        if _SUBGRAPH_OPEN.match(line):
            opens += 1
        elif _END.match(line):
            ends += 1

    missing = opens - ends
    if missing <= 0:
        return RuleOutcome(text=src, changed=False)

    # Match the indentation style of the source (default to no indent).
    trailing = src.rstrip("\n")
    additions = "\n".join(["end"] * missing)
    text = f"{trailing}\n{additions}\n"
    return RuleOutcome(
        text=text,
        changed=True,
        notes=[f"added {missing} missing 'end' statement(s) for unbalanced subgraph(s)"],
    )


# ──────────────────────────────────────────────────────────────────────────
# Rule: strip_bad_style
# ──────────────────────────────────────────────────────────────────────────
_STYLE_LINE = re.compile(r"^\s*(style|linkStyle)\s+(\S+)")


def strip_bad_style(src: str) -> RuleOutcome:
    """Drop ``style``/``linkStyle`` directives that reference an id not defined
    anywhere else in the diagram, since those crash the parser.

    ``linkStyle`` targets (numeric indices or ``default``) are left alone — only
    ``style <id>`` directives whose ``<id>`` never appears as a node are removed.
    """
    lines = src.split("\n")

    # Collect candidate node ids: a token that appears followed by an opening
    # shape delimiter, or on the left/right of an edge. This is a heuristic but
    # errs toward keeping styles (only strips clearly-dangling ones).
    defined_ids: set[str] = set()
    node_def = re.compile(r"\b([A-Za-z0-9_]+)\s*(?:\[|\(|\{)")
    for line in lines:
        for m in node_def.finditer(line):
            defined_ids.add(m.group(1))

    notes: list[str] = []
    out_lines: list[str] = []
    for line in lines:
        m = _STYLE_LINE.match(line)
        if m and m.group(1) == "style":
            target = m.group(2)
            if target not in defined_ids:
                notes.append(f"removed dangling style directive: {line.strip()!r}")
                continue  # drop the line
        out_lines.append(line)

    text = "\n".join(out_lines)
    return RuleOutcome(text=text, changed=bool(notes), notes=notes)


# Ordered list of all rules. Order matters: arrows and labels first, structural
# fixes (subgraphs) after, dangling-reference cleanup last.
ALL_RULES = [
    fix_arrows,
    quote_labels,
    close_subgraphs,
    strip_bad_style,
]
