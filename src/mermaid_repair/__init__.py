"""mermaid-repair: grammar-driven repair for LLM-generated Mermaid diagrams.

Public API
----------
    repair(src)            -> RepairResult          repair a single diagram
    repair_markdown(md)    -> MarkdownRepairResult  repair every ```mermaid block
    ALL_RULES                                        the ordered rule list
    mmdc_available(), renders(src)                   optional parser verification

Example
-------
    >>> from mermaid_repair import repair
    >>> result = repair('A[Svc<br/>(x)]\\nA --|go| B')
    >>> result.changed
    True
    >>> print(result.text)
    A["Svc<br/>(x)"]
    A -->|go| B
"""

from __future__ import annotations

from .markdown import MarkdownRepairResult, repair_markdown
from .rules import ALL_RULES, RuleOutcome
from .sanitizer import RepairResult, repair
from .verify import mmdc_available, renders

__all__ = [
    "ALL_RULES",
    "MarkdownRepairResult",
    "RepairResult",
    "RuleOutcome",
    "mmdc_available",
    "renders",
    "repair",
    "repair_markdown",
]

__version__ = "0.1.0"
