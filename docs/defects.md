# Defects - jupyterlab_terminal_show_in_file_browser_extension

Bugs and regressions in the Show in File Browser extension.

## Authors

- `@kj` Konrad Jelen

## Context Menu `MENU`

Placement and behaviour of the Show in File Browser context-menu item

- log: 2026-11-04T20:41:01Z @kj category created

- [x] `DEF-MENU-1-ACTIVE-TAB` **Inactive terminal tab acts on the active terminal** - MAJOR; right-clicking a terminal tab that is not active and choosing Show in File Browser moves the browser to the active terminal's directory
  - evidence: Galata 5 passed, 0 failed on 2026-11-04 including 'an inactive terminal tab acts on that terminal, not the active one'; execute now uses the terminal the context menu hit-tested
  - repro: two terminals in different directories; right-click the first tab; Show in File Browser; the browser opens the active terminal's directory
  - test-tags: E2E
  - root-cause: 2026-11-04T20:41:01Z @kj execute reads terminalTracker.currentWidget instead of the terminal the context menu hit-tested
  - log: 2026-11-04T20:41:01Z @kj added
  - log: 2026-11-04T20:48:24Z @kj closed: fixed and verified
- [x] `DEF-MENU-3-HIDDEN-BROWSER` **Nothing visible when the file browser panel is hidden** - MEDIUM; the command changes the file browser path but does not show the file browser; with the left sidebar collapsed or on another panel the click has no visible effect
  - evidence: execute calls app.shell.activateById(fileBrowser.id) after cd; not tested with a collapsed sidebar; build_test.py 2026-11-13: Jest 1, pytest 28, Galata 5 passed at 1.0.35
  - root-cause: 2026-11-13T06:49:38Z @kj execute called fileBrowser.model.cd only and never activated the file browser widget
  - repro: collapse the left sidebar; right-click a terminal tab; Show in File Browser; the sidebar stays collapsed
  - test-tags: MANUAL
  - log: 2026-11-13T06:46:37Z @kj added
  - log: 2026-11-13T06:49:38Z @kj closed
- [x] `DEF-MENU-5-DEAD-LOGS` **Commented-out logging in src/index.ts** - MINOR; 7 commented-out console.log blocks remain in activate and execute; dead code
  - evidence: grep -c '// console.log' src/index.ts prints 0
  - repro: grep -n '// console.log' src/index.ts
  - log: 2026-11-13T06:46:37Z @kj added
  - log: 2026-11-13T06:49:38Z @kj closed

## Working Directory `CWD`

How the terminal's working directory is resolved and mapped to a file browser path

- log: 2026-11-13T06:46:36Z @kj category created

- [x] `DEF-CWD-2-HOME-ROOT` **Browser opens the root when home is not /home/<user>** - MAJOR; server root under the home directory is sent as ~/..., the frontend expands ~ only for /home/<user> and /Users/<user>; a root user (/root) or a symlinked root always lands in the workspace root
  - evidence: handler returns root = realpath(expanduser(server_root_dir)), frontend compares cwd with it, expandTilde removed; pytest TestServerRoot passes; build_test.py 2026-11-13: Jest 1, pytest 28, Galata 5 passed at 1.0.35
  - root-cause: 2026-11-13T06:49:38Z @kj expandTilde took the home directory from the cwd with a /home|/Users regex; jupyter_server collapses any home to ~, and /proc reports the symlink-free path
  - repro: run jupyter lab as root with notebook dir /root/work; cd /root/work/sub in a terminal; Show in File Browser opens the root, not sub
  - test-tags: UNIT
  - log: 2026-11-13T06:46:36Z @kj added
  - log: 2026-11-13T06:49:38Z @kj closed
- [x] `DEF-CWD-4-SPAWN` **Request for an unknown terminal starts a terminal** - MINOR; GET /api/terminal-cwd/<name> calls terminal_manager.get_terminal, which creates a terminal for an unknown name; the 404 branch is never reached
  - evidence: handler reads terminal_manager.terminals.get(name); pytest test_unknown_terminal_is_404_and_starts_none passes; build_test.py 2026-11-13: Jest 1, pytest 28, Galata 5 passed at 1.0.35
  - root-cause: 2026-11-13T06:49:38Z @kj terminado NamedTermManager.get_terminal creates a terminal for an unknown name
  - repro: GET /api/terminal-cwd/nope on a server with no such terminal; a new terminal named nope appears in the running terminals
  - test-tags: UNIT
  - log: 2026-11-13T06:46:37Z @kj added
  - log: 2026-11-13T06:49:38Z @kj closed
- [-] `DEF-CWD-6-LSOF-BLOCK` **lsof call blocks the server loop on macOS** - MINOR; _get_cwd_macos runs subprocess.run(lsof, timeout=5) inside the tornado handler
  - repro: macOS: click Show in File Browser while lsof is slow; other requests wait up to 5 s
  - log: 2026-11-13T06:46:37Z @kj added
  - log: 2026-11-13T06:49:45Z @kj rejected: not worth a fix; reason: one short lsof call per click, bounded by the 5 s timeout; no user harmed in ordinary use
