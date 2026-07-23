# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

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
