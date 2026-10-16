# Changelog

All notable changes to `mermaid-repair` are documented here.

## [0.1.1] - 2026-10-16

### Added
- New rule `dedupe_subgraph_ids`: renames a bare `subgraph X` to
  `subgraph X_grp [X]` when a node with id `X` also exists, fixing Mermaid's
  "Setting X as parent of X would create a cycle" error. Only touches
  single-token bare titles that collide with a node id; leaves multi-word
  titles and explicit `id [Title]` forms untouched.
- Fixture `subgraph_node_id_collision.mmd` (captured from a real model output),
  parser-verified: original fails to render, repaired renders.

## [0.1.0] - 2026-10-15

### Added
- Initial release. Grammar-driven repair for LLM-generated Mermaid diagrams.
- Rules: `fix_arrows`, `quote_labels` (incl. cylinder shapes), `close_subgraphs`,
  `strip_bad_style`.
- `repair()` and `repair_markdown()` APIs; optional `mmdc` parser verification.
- CLI `mermaid-repair fix` with `--check` gate.
- Fixture corpus verified against the real Mermaid engine.
