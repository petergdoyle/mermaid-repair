# mermaid-repair — Development Makefile
# Stack: Python 3.11+ / uv
# Library + CLI for repairing LLM-generated Mermaid diagrams.

.DEFAULT_GOAL := help
.PHONY: help setup install uninstall fix check lint lint-fix test test-all clean build

UV := uv
PREFIX ?= /usr/local

# Inputs for the `fix` / `check` convenience targets
SOURCE ?=

help: ## Show available commands
	@echo "Usage: make [target]"
	@echo ""
	@echo "  Development:"
	@echo "  setup          Install dependencies (uv sync --extra dev)"
	@echo "  test           Run the test suite (fixture render checks skip without mmdc)"
	@echo "  test-all       Run the full suite including mmdc render verification"
	@echo "  lint           Run ruff"
	@echo "  lint-fix       Auto-fix lint issues (ruff)"
	@echo "  clean          Remove build artifacts and caches"
	@echo ""
	@echo "  Install:"
	@echo "  install        Install the mermaid-repair CLI for the current user"
	@echo "  uninstall      Remove the current-user installation"
	@echo "  build          Build a wheel into dist/"
	@echo ""
	@echo "  Utilities:"
	@echo "  fix SOURCE=f   Repair a .md/.mmd file in place"
	@echo "  check SOURCE=f Exit non-zero if SOURCE needs repairs (CI gate)"
	@echo ""
	@echo "  Variables:"
	@echo "  PREFIX         (reserved for system installs; default /usr/local)"

# ─── Setup ────────────────────────────────────────────────────────────────────

setup: ## Install dependencies
	@echo "📦 Installing dependencies (uv sync --extra dev)..."
	@$(UV) sync --extra dev
	@echo "✅ Setup complete."
	@if ! command -v mmdc >/dev/null 2>&1; then \
		echo "ℹ️  mmdc (Mermaid CLI) not found — render-verification tests will be skipped."; \
		echo "   Install for full verification: npm install -g @mermaid-js/mermaid-cli"; \
	fi

# ─── Quality ────────────────────────────────────────────────────────────────

test: ## Run the test suite (render checks skip without mmdc)
	@$(UV) run pytest -q

test-all: ## Run the full suite, requiring mmdc for render verification
	@if ! command -v mmdc >/dev/null 2>&1; then \
		echo "❌ mmdc not installed. Install it: npm install -g @mermaid-js/mermaid-cli"; exit 1; \
	fi
	@$(UV) run pytest -q -m "mmdc or not mmdc"

lint: ## Lint with ruff
	@$(UV) run ruff check src tests

lint-fix: ## Auto-fix lint issues
	@$(UV) run ruff check --fix src tests

# ─── Utilities ────────────────────────────────────────────────────────────────

fix: ## Repair a .md/.mmd file in place (SOURCE=path)
	@if [ -z "$(SOURCE)" ]; then echo "Usage: make fix SOURCE=path/to/file.md"; exit 1; fi
	@$(UV) run mermaid-repair fix "$(SOURCE)"

check: ## Exit non-zero if SOURCE needs repairs (SOURCE=path)
	@if [ -z "$(SOURCE)" ]; then echo "Usage: make check SOURCE=path/to/file.md"; exit 1; fi
	@$(UV) run mermaid-repair fix "$(SOURCE)" --check

# ─── Install ────────────────────────────────────────────────────────────────

install: ## Install the mermaid-repair CLI for the current user
	@echo "📦 Installing mermaid-repair CLI..."
	@# --force --reinstall --no-cache: version stays 0.1.0 between edits, so a
	@# plain install would reuse a stale cached wheel. Always build from source.
	@$(UV) tool install --force --reinstall --no-cache .
	@echo "✅ Installed. Run: mermaid-repair --help"
	@echo "ℹ️  Ensure ~/.local/bin is on your PATH if the command is not found."

uninstall: ## Remove the current-user installation
	@$(UV) tool uninstall mermaid-repair
	@echo "✅ mermaid-repair removed."

build: ## Build a wheel into dist/
	@$(UV) build --wheel
	@echo "✅ Wheel built in dist/"

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	@echo "🧹 Cleaning..."
	@rm -rf dist build .pytest_cache .ruff_cache
	@find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean."
