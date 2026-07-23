<!-- @import /home/lab/workspace/.claude/CLAUDE.md -->

# Project-Specific Configuration

This file imports workspace-level configuration from `/home/lab/workspace/.claude/CLAUDE.md`.
All workspace rules apply. Project-specific rules below strengthen or extend them.

The workspace `/home/lab/workspace/.claude/` directory and the global `~/.claude/` directory carry
additional standards through skills and instruction files (`mermaid-diagrams`, `jupyterlab-extension`,
`git`, `notebook-standards`, and others). Consult the workspace CLAUDE.md and its `.claude` directory
to discover all applicable standards.

## Mandatory Bans (Reinforced)

The following workspace rules are STRICTLY ENFORCED for this project:

- **No automatic git tags** - only create tags when user explicitly requests
- **No automatic version changes** - only modify version in package.json/pyproject.toml/etc. when user explicitly requests
- **No automatic publishing** - never run `make publish`, `npm publish`, `twine upload`, or similar without explicit user request
- **No manual package installs if Makefile exists** - use `make install` or equivalent Makefile targets, not direct `pip install`/`uv install`/`npm install`/`jlpm install`
- **No automatic git commits or pushes** - only when user explicitly requests

## Project Context

JupyterLab 4.x extension adding a "Show in File Browser" context-menu action to terminal tabs -
selecting it navigates the file browser to the terminal's current working directory.

**Architecture**:

- **Frontend** (TypeScript, `src/index.ts`) - registers the terminal-tab context-menu command using `IDefaultFileBrowser` and `ITerminalTracker`, then calls the server API via `ServerConnection`
- **Server** (Python, `jupyterlab_terminal_show_in_file_browser_extension/handlers.py`) - `TerminalCwdHandler` exposes `/api/terminal-cwd/{name}`, resolving the terminal PTY shell cwd by recursively walking the process tree and reading `/proc/{pid}/cwd` (Linux) or `lsof` (macOS), skipping pseudo-filesystem paths
- **Schema** (`schema/plugin.json`) - context-menu registration
- **Origin** - scaffolded from a copier template (`.copier-answers.yml`)

**Toolchain**:

- Build, install, test, and publish are Makefile-driven (`make build`, `make install`, `make test`, `make publish`) - Makefile v1.34, jlpm-based, project-local `.nodeenv/`
- Tests - jest frontend (`jlpm test`), pytest server (`tests/test_handlers.py`), Playwright `ui-tests/`
- CI/CD - GitHub Actions plus jupyter-releaser; follow the `jupyterlab-extension` skill

## Journal Rules (Project-Specific)

- **APPEND ONLY**: New journal entries MUST be appended at the end of the file, never inserted between existing entries
- Entries maintain strict chronological order by position - the last entry in the file is always the most recent work
- Never reorder, move, or insert entries out of sequence
- The Stellars **journal plugin** is the canonical tool for this file: create via `/journal:create`, append via `/journal:update`, archive via `/journal:archive`. The `journal:journal` skill auto-triggers on any mention of "journal" and runs `journal-tools check` after every write
- Direct edits to `JOURNAL.md` are a last resort - prefer the plugin so modus secundis format, continuous numbering and append-only order are enforced automatically

## Strengthened Rules

- **Makefile is the build authority** - never run `jlpm install`, `jlpm build`, `pip install`, or `python -m build` directly; use the `make` targets so the pinned project-local `.nodeenv/` toolchain is used
- **ASCII arrows in this repo** - use ASCII `->` in markdown and documentation, NOT unicode arrow characters (U+2192 and similar) preferred globally, so README and docs stay renderer-safe on GitHub
- **jupyterlab-extension skill** - always follow it for extension development, testing, and jupyter-releaser CI/CD
- **GitHub project** - follow the badge and link-checker conventions in `.claude/GITHUB.md`; validate badge URLs against `stellarshenson/jupyterlab_terminal_show_in_file_browser_extension`
