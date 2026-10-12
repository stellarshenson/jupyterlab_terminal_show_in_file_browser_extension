# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## [1.0.27] - 2026-10-12

### Added

- Galata integration tests for the menu item: hidden on a document tab, shown on a terminal tab where it opens the terminal's folder, shown inside a terminal

### Changed

- Updated to JupyterLab extension template 4.6.5: the extension builds with `@jupyter/builder` (Rspack) instead of the webpack-based builder, and lints with ESLint 9
- Requires JupyterLab 4.6 or later and Python 3.10 or later. Dependency floors are raised to the tested versions, and every CI job runs on Python 3.13
- Build tooling updated to Makefile 1.45: packages install with `jlpm` only, `package-lock.json` is removed, and `make publish` runs the tests before it releases
- The command's label and caption go through JupyterLab's translator, so a language pack can translate them. This adds `@jupyterlab/translation` as a dependency

### Fixed

- "Show in File Browser" of this extension appears only on terminal tabs and inside terminals. Before, it also appeared on every document tab beside JupyterLab's own item with the same label, and there it moved the file browser to the folder of the terminal used last instead of the file

## 1.0.26

- Fixed "CWD Not Available" for a terminal whose shell is sitting in a directory that has since been deleted - the file browser now opens the nearest existing parent directory instead of showing an error
- The terminal's working directory is read from `/proc` even when the directory was removed, then resolved up to the closest folder that still exists

## 1.0.25

- Fixed "Show in File Browser" resolving to the wrong directory when an agent CLI (e.g. claude) runs inside the terminal - a shared background daemon could graft another terminal's session into the process tree, and the old deepest-shell search returned that other project's directory
- Terminal cwd is now resolved from the controlling terminal's foreground process group (`tpgid`), which cannot reference a different terminal's session, so the wrong-directory case can no longer occur
- Navigation inside a subshell (e.g. Midnight Commander) is still tracked correctly
- Removed the environment-variable PWD fallback, which could report a stale directory

## 1.0.24

- Maintenance release - no user-facing extension changes
- Build tooling updated to canonical Makefile v1.34, adding a project-local node environment (`.nodeenv/`) instead of overwriting the Python prefix
- Dependency checks now self-heal a missing or empty `node_modules` via `jlpm install`
- Lockfiles formatted with the pinned `jlpm prettier` rather than `npx prettier`
- Project Claude Code configuration consolidated to import workspace-level rules

<!-- <END NEW CHANGELOG ENTRY> -->

## 1.0.12

- Context menu on terminal tabs and terminal area with "Show in File Browser" command
- Server-side cwd detection via `/proc/{pid}/cwd` (Linux) and `lsof` (macOS)
- PWD environment variable fallback for process cwd detection
- Path resolution with tilde expansion and absolute path navigation
- Fallback to workspace root when terminal cwd is outside Jupyter workspace
