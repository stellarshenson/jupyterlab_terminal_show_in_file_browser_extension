# Acceptance Criteria - jupyterlab_terminal_show_in_file_browser_extension

A context-menu action on terminal tabs and inside terminals that moves the file browser to the terminal's current working directory.

## Authors

- `@kj` Konrad Jelen

## Context Menu `MENU`

Placement and appearance of the Show in File Browser context-menu item

- log: 2026-11-04T20:16:32Z @kj category created

- [x] `ACC-MENU-1-ICON` **Menu item icon** - MEDIUM; the Show in File Browser item shows an icon on a terminal tab and inside a terminal
  - evidence: Galata 4 passed, 0 failed in bubblewrap: 'a terminal tab shows the item, and it opens the folder of the terminal' saw the visible item with terminal:show-in-file-browser and exactly one .lm-Menu-itemIcon svg
  - test: Galata: open the terminal tab context menu, assert the item holds an svg icon
  - test-tags: E2E
  - mechanism: 2026-11-04T20:16:32Z @kj command terminal:show-in-file-browser sets icon to folderIcon from @jupyterlab/ui-components, which JupyterLab renders in context menus
  - log: 2026-11-04T20:16:32Z @kj added
  - log: 2026-11-04T20:19:25Z @kj icon set to folderIcon in src/index.ts; Galata assertion added; build, lint, jest and pytest pass; awaiting the Galata run
  - log: 2026-11-04T20:25:43Z @kj closed: Galata run 2026-11-04 green
- [x] `ACC-MENU-2-DOC-ONLY` **Document tab keeps JupyterLab's item** - HIGH; a document tab shows only JupyterLab's own Show in File Browser, not this extension's
  - evidence: Galata 4 passed, 0 failed on 2026-11-04: 'a document tab shows only the item of JupyterLab' saw exactly one visible item, data-command docmanager:show-in-file-browser
  - test: Galata: open a note.txt tab while a terminal is open, assert one visible item with data-command docmanager:show-in-file-browser
  - test-tags: E2E
  - log: 2026-11-04T20:24:02Z @kj added
  - log: 2026-11-04T20:25:43Z @kj closed: Galata run 2026-11-04 green
- [x] `ACC-MENU-3-TAB-SHOW` **Item on a terminal tab** - HIGH; a terminal tab context menu shows the item
  - evidence: Galata 4 passed, 0 failed on 2026-11-04: 'a terminal tab shows the item...' saw exactly one visible item with data-command terminal:show-in-file-browser
  - test: Galata: right-click the terminal tab, assert one visible item with data-command terminal:show-in-file-browser
  - test-tags: E2E
  - log: 2026-11-04T20:24:02Z @kj added
  - log: 2026-11-04T20:25:43Z @kj closed: Galata run 2026-11-04 green
- [x] `ACC-MENU-4-INSIDE` **Item inside a terminal** - MEDIUM; right-clicking inside a terminal shows the item
  - evidence: Galata 4 passed, 0 failed on 2026-11-04: 'the menu inside a terminal shows the item' saw the item with data-command terminal:show-in-file-browser
  - test: Galata: right-click the terminal area, assert the item with data-command terminal:show-in-file-browser
  - test-tags: E2E
  - log: 2026-11-04T20:24:02Z @kj added
  - log: 2026-11-04T20:25:43Z @kj closed: Galata run 2026-11-04 green
- [x] `ACC-MENU-5-NAVIGATE` **File browser follows the terminal** - HIGH; clicking the item moves the file browser to the terminal's cwd
  - evidence: Galata 4 passed, 0 failed on 2026-11-04: after the click the test polled the file browser path to <tmp>/sub, the terminal's cwd
  - test: Galata: terminal in tmpPath/sub, click the item, assert the browser path is tmpPath/sub
  - test-tags: E2E
  - log: 2026-11-04T20:24:03Z @kj added
  - log: 2026-11-04T20:25:44Z @kj closed: Galata run 2026-11-04 green

## Working Directory `CWD`

How the server resolves the terminal's working directory

- log: 2026-11-04T20:24:03Z @kj category created

- [x] `ACC-CWD-6-FOREGROUND` **Foreground group cwd** - HIGH; the cwd comes from the pty shell's foreground process group, never from a process another terminal started
  - evidence: pytest 26 passed on 2026-11-04 (logs/pytest-icon-menu.log), including TestGetProcessCwd resolving via tpgid and ignoring a foreign session
  - test: pytest: TestGetProcessCwd resolves via tpgid and ignores a foreign session
  - test-tags: UNIT
  - log: 2026-11-04T20:24:03Z @kj added
  - log: 2026-11-04T20:25:44Z @kj closed: pytest 26 passed 2026-11-04
- [x] `ACC-CWD-7-DELETED` **Deleted cwd recovery** - MEDIUM; when the terminal's directory was deleted, the nearest existing ancestor is used
  - evidence: pytest 26 passed on 2026-11-04 (logs/pytest-icon-menu.log), including test_recovers_ancestor_when_cwd_deleted returning the nearest existing ancestor
  - test: pytest: test_recovers_ancestor_when_cwd_deleted returns the nearest existing directory
  - test-tags: UNIT
  - log: 2026-11-04T20:24:03Z @kj added
  - log: 2026-11-04T20:25:44Z @kj closed: pytest 26 passed 2026-11-04
