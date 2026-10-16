"""Unit tests for each repair rule in isolation."""

from __future__ import annotations

from mermaid_repair.markdown import repair_markdown
from mermaid_repair.rules import (
    close_subgraphs,
    fix_arrows,
    quote_labels,
    strip_bad_style,
)
from mermaid_repair.sanitizer import repair


# ── fix_arrows ─────────────────────────────────────────────────────────────
def test_fix_arrows_solid():
    out = fix_arrows("PaymentSvc --|Payment Success| SQS")
    assert out.changed
    assert "PaymentSvc -->|Payment Success| SQS" in out.text


def test_fix_arrows_dotted():
    out = fix_arrows("A -.|retry| B")
    assert out.changed
    assert "A -.->|retry| B" in out.text


def test_fix_arrows_leaves_valid_edges():
    src = "A -->|ok| B\nC -.->|async| D"
    out = fix_arrows(src)
    assert not out.changed
    assert out.text == src


def test_fix_arrows_skips_comments():
    src = "%% A --|x| B"
    out = fix_arrows(src)
    assert not out.changed


# ── quote_labels ─────────────────────────────────────────────────────────────
def test_quote_labels_slash():
    out = quote_labels("User[User Browser/Mobile App]")
    assert out.changed
    assert out.text == 'User["User Browser/Mobile App"]'


def test_quote_labels_br_and_parens():
    out = quote_labels("AuthSvc[Auth Service<br/>(Cognito Integration)]")
    assert out.changed
    assert out.text == 'AuthSvc["Auth Service<br/>(Cognito Integration)"]'


def test_quote_labels_cylinder_quotes_inside():
    out = quote_labels("UserDB[(DynamoDB<br/>Users/Auth)]")
    assert out.changed
    assert out.text == 'UserDB[("DynamoDB<br/>Users/Auth")]'


def test_quote_labels_already_quoted_untouched():
    src = 'A["already (quoted)"]'
    out = quote_labels(src)
    assert not out.changed
    assert out.text == src


def test_quote_labels_plain_label_untouched():
    src = "A[Plain Label]"
    out = quote_labels(src)
    assert not out.changed
    assert out.text == src


def test_quote_labels_skips_classdef():
    src = "classDef awsService fill:#f9f9f9,stroke:#333;"
    out = quote_labels(src)
    assert not out.changed


# ── close_subgraphs ─────────────────────────────────────────────────────────
def test_close_subgraphs_adds_missing_end():
    src = "graph TD\n  subgraph A\n    X[Node]"
    out = close_subgraphs(src)
    assert out.changed
    assert out.text.count("end") == 1


def test_close_subgraphs_balanced_untouched():
    src = "graph TD\n  subgraph A\n    X[Node]\n  end"
    out = close_subgraphs(src)
    assert not out.changed


def test_close_subgraphs_multiple_missing():
    src = "graph TD\n subgraph A\n subgraph B\n  X[n]\n end"
    out = close_subgraphs(src)
    assert out.changed
    # two opens, one end -> one more end added
    assert out.text.rstrip().endswith("end")


# ── strip_bad_style ─────────────────────────────────────────────────────────
def test_strip_bad_style_removes_dangling():
    src = "graph TD\n  A[Node]\n  style Ghost fill:#fff"
    out = strip_bad_style(src)
    assert out.changed
    assert "Ghost" not in out.text
    assert "A[Node]" in out.text


def test_strip_bad_style_keeps_valid():
    src = "graph TD\n  A[Node]\n  style A fill:#fff"
    out = strip_bad_style(src)
    assert not out.changed
    assert "style A" in out.text


def test_strip_bad_style_keeps_linkstyle():
    src = "graph TD\n  A[Node]\n  linkStyle 0 stroke:#f00"
    out = strip_bad_style(src)
    assert not out.changed


# ── sanitizer composition ─────────────────────────────────────────────────────
def test_repair_reports_rules_applied():
    src = "A[Svc/one]\nA --|go| B"
    result = repair(src)
    assert result.changed
    assert "quote_labels" in result.rules_applied
    assert "fix_arrows" in result.rules_applied


def test_repair_idempotent():
    src = "A[Svc/one]\nA --|go| B"
    once = repair(src).text
    twice = repair(once)
    assert not twice.changed
    assert twice.text == once


# ── markdown block handling ───────────────────────────────────────────────────
def test_repair_markdown_only_touches_mermaid_blocks():
    md = (
        "# Title\n\n"
        "Some prose with a `code` span.\n\n"
        "```python\nx = 1  # not mermaid\n```\n\n"
        "```mermaid\nA[Svc/one]\nA --|go| B\n```\n\n"
        "More prose.\n"
    )
    result = repair_markdown(md)
    assert result.changed
    assert result.blocks_total == 1
    assert result.blocks_repaired == 1
    # python block untouched
    assert "x = 1  # not mermaid" in result.text
    # mermaid block repaired
    assert 'A["Svc/one"]' in result.text
    assert "A -->|go| B" in result.text
    # prose untouched
    assert "More prose." in result.text


def test_repair_markdown_no_mermaid():
    md = "# Just prose\n\nNo diagrams here.\n"
    result = repair_markdown(md)
    assert not result.changed
    assert result.blocks_total == 0
