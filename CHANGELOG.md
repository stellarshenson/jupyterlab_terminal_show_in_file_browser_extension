# Changelog

<!-- <START NEW CHANGELOG ENTRY> -->

## 1.0.12

- Context menu on terminal tabs and terminal area with "Show in File Browser" command
- Server-side cwd detection via `/proc/{pid}/cwd` (Linux) and `lsof` (macOS)
- PWD environment variable fallback for process cwd detection
- Path resolution with tilde expansion and absolute path navigation
- Fallback to workspace root when terminal cwd is outside Jupyter workspace

<!-- <END NEW CHANGELOG ENTRY> -->
