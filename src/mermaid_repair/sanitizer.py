"""Apply the repair rules to a Mermaid diagram and report what changed."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from .rules import ALL_RULES, RuleOutcome

Rule = Callable[[str], RuleOutcome]


@dataclass
class RepairResult:
    """Outcome of repairing a single Mermaid diagram."""

    text: str
    original: str
    changed: bool = False
    # Names of rules that actually modified the source, in application order.
    rules_applied: list[str] = field(default_factory=list)
    # Per-rule human-readable notes, keyed by rule name.
    notes: dict[str, list[str]] = field(default_factory=dict)


def repair(src: str, rules: Sequence[Rule] | None = None) -> RepairResult:
    """Repair a single Mermaid diagram by applying each rule in order.

    Args:
        src: the raw Mermaid diagram source (without the ```mermaid fence).
        rules: optional override of the rule sequence (defaults to ALL_RULES).

    Returns:
        A RepairResult carrying the repaired text, whether anything changed,
        and which rules fired.
    """
    active = list(rules) if rules is not None else list(ALL_RULES)

    original = src
    current = src
    rules_applied: list[str] = []
    notes: dict[str, list[str]] = {}

    for rule in active:
        outcome = rule(current)
        if outcome.changed:
            rules_applied.append(rule.__name__)
            if outcome.notes:
                notes[rule.__name__] = outcome.notes
        current = outcome.text

    return RepairResult(
        text=current,
        original=original,
        changed=current != original,
        rules_applied=rules_applied,
        notes=notes,
    )
