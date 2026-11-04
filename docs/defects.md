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
