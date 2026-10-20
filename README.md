# mermaid-repair

Grammar-driven repair for LLM-generated Mermaid diagrams, verified against the real Mermaid parser.

LLMs reliably produce *nearly* valid Mermaid — then trip on a small, finite set of grammar edges (unquoted labels, dropped arrowheads, unclosed subgraphs, dangling style refs). Every model makes the same mistakes because the failure space is defined by Mermaid's grammar, not by the model. `mermaid-repair` fixes those mistakes in one place so diagrams render instead of failing, and every app that generates Mermaid (actor-factory, solutionforge-ai, storyforge-ai, md2pdf) can share a single implementation.

## Why this exists

- **One canonical sanitizer.** No per-app copies drifting out of sync; no per-model branching.
- **Grammar-specialized, not model-specialized.** Rules target Mermaid syntax, so they generalize across models and model versions.
- **Proven against the real engine.** A fixture corpus of real broken diagrams is verified with the Mermaid CLI (`mmdc`): a repair counts only when the original fails to render AND the repaired source renders.

## Install

With `uv` (recommended):

```bash
uv pip install "mermaid-repair @ git+https://github.com/petergdoyle/mermaid-repair.git@v0.1.1"
```

Or add to a consuming project's `pyproject.toml`:

```toml
dependencies = [
    "mermaid-repair @ git+https://github.com/petergdoyle/mermaid-repair.git@v0.1.1",
]
```

## Usage

### Library

```python
from mermaid_repair import repair, repair_markdown

# Repair a single diagram (no fences)
result = repair("A[Svc<br/>(x)]\nA --|go| B")
print(result.changed)         # True
print(result.rules_applied)   # ['fix_arrows', 'quote_labels']
print(result.text)
# A["Svc<br/>(x)"]
# A -->|go| B

# Repair every ```mermaid block inside a markdown document
md_result = repair_markdown(markdown_text)
print(md_result.blocks_repaired, "of", md_result.blocks_total, "blocks repaired")
cleaned_markdown = md_result.text
```

### Optional parser verification

```python
from mermaid_repair import mmdc_available, renders, repair

if mmdc_available():
    repaired = repair(src).text
    assert renders(repaired)   # renders via the real Mermaid CLI
```

### CLI

```bash
mermaid-repair fix solution.md                # repair mermaid blocks in place
mermaid-repair fix diagram.mmd -o fixed.mmd   # repair a raw diagram
mermaid-repair fix solution.md --check        # exit 1 if repairs are needed (CI gate)
cat diagram.mmd | mermaid-repair fix -         # stdin -> stdout
```

## Repair rules

Each rule is independent and individually tested.

| Rule | Fixes |
|------|-------|
| `fix_arrows` | Completes edges missing an arrowhead: `A --|x| B` → `A -->|x| B`; `-.|x|` → `-.->|x|` |
| `quote_labels` | Quotes labels containing `()`, `<br/>`, `/`, `<>`, `&`; cylinder quotes go inside: `D[(Orders)]` → `D[("Orders")]` |
| `close_subgraphs` | Appends missing `end` for unbalanced `subgraph` blocks |
| `dedupe_subgraph_ids` | Renames `subgraph X` → `subgraph X_grp [X]` when a node `X` also exists (avoids the id/parent collision error) |
| `strip_bad_style` | Drops `style <id>` directives referencing an undefined node id |

## Development

```bash
make setup     # install deps with uv
make test      # run the test suite (fixture render checks skip without mmdc)
make lint      # ruff
make install   # install the CLI for the current user
```

To run the parser-verified fixture tests, install the Mermaid CLI:

```bash
npm install -g @mermaid-js/mermaid-cli
```

## Adding a new failure pattern

1. Drop the raw broken diagram into `tests/fixtures/<name>.mmd`.
2. Run `make test`. If it fails the "repaired renders" check, add or extend a rule in `src/mermaid_repair/rules.py`.
3. The fixture now guards that pattern forever. Additive, measurable, no whack-a-mole.

## License

MIT
