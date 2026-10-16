"""Command-line interface for mermaid-repair.

Usage:
    mermaid-repair fix FILE [-o OUT]     repair a .md or .mmd file
    mermaid-repair fix FILE --check      exit non-zero if repairs are needed
    mermaid-repair fix -                 read stdin, write repaired to stdout
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .markdown import repair_markdown
from .sanitizer import repair


def _is_markdown(path: str) -> bool:
    return path.lower().endswith((".md", ".markdown"))


@click.group()
@click.version_option(package_name="mermaid-repair")
def main() -> None:
    """Repair LLM-generated Mermaid diagrams."""


@main.command()
@click.argument("source")
@click.option("-o", "--output", "output", default=None, help="Write repaired output to this path.")
@click.option("--check", is_flag=True, help="Do not write; exit 1 if repairs are needed.")
@click.option(
    "--markdown/--diagram",
    "force_markdown",
    default=None,
    help="Force treating input as markdown (repair ```mermaid blocks) or as a raw diagram.",
)
def fix(source: str, output: str | None, check: bool, force_markdown: bool | None) -> None:
    """Repair SOURCE (a .md/.mmd file, or '-' for stdin)."""
    if source == "-":
        text = sys.stdin.read()
        as_markdown = force_markdown if force_markdown is not None else False
    else:
        path = Path(source)
        if not path.exists():
            raise click.ClickException(f"File not found: {source}")
        text = path.read_text(encoding="utf-8")
        as_markdown = force_markdown if force_markdown is not None else _is_markdown(source)

    if as_markdown:
        md_result = repair_markdown(text)
        new_text = md_result.text
        changed = md_result.changed
        summary = (
            f"{md_result.blocks_repaired}/{md_result.blocks_total} mermaid block(s) repaired"
        )
    else:
        result = repair(text)
        new_text = result.text
        changed = result.changed
        summary = (
            f"rules applied: {', '.join(result.rules_applied)}"
            if result.rules_applied
            else "no changes needed"
        )

    if check:
        if changed:
            click.echo(f"Repairs needed ({summary}).", err=True)
            sys.exit(1)
        click.echo("No repairs needed.", err=True)
        return

    if source == "-" and not output:
        sys.stdout.write(new_text)
        return

    target = Path(output) if output else Path(source)
    target.write_text(new_text, encoding="utf-8")
    click.echo(f"Wrote {target} ({summary}).", err=True)


if __name__ == "__main__":
    main()
