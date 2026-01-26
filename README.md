# jupyterlab_terminal_show_in_file_browser_extension

[![GitHub Actions](https://github.com/stellarshenson/jupyterlab_terminal_show_in_file_browser_extension/actions/workflows/build.yml/badge.svg)](https://github.com/stellarshenson/jupyterlab_terminal_show_in_file_browser_extension/actions/workflows/build.yml)
[![npm version](https://img.shields.io/npm/v/jupyterlab_terminal_show_in_file_browser_extension.svg)](https://www.npmjs.com/package/jupyterlab_terminal_show_in_file_browser_extension)
[![PyPI version](https://img.shields.io/pypi/v/jupyterlab-terminal-show-in-file-browser-extension.svg)](https://pypi.org/project/jupyterlab-terminal-show-in-file-browser-extension/)
[![Total PyPI downloads](https://static.pepy.tech/badge/jupyterlab-terminal-show-in-file-browser-extension)](https://pepy.tech/project/jupyterlab-terminal-show-in-file-browser-extension)
[![JupyterLab 4](https://img.shields.io/badge/JupyterLab-4-orange.svg)](https://jupyterlab.readthedocs.io/en/stable/)
[![Brought To You By KOLOMOLO](https://img.shields.io/badge/Brought%20To%20You%20By-KOLOMOLO-00ffff?style=flat)](https://kolomolo.com)

> [!TIP]
> This extension is part of the [stellars_jupyterlab_extensions](https://github.com/stellarshenson/stellars_jupyterlab_extensions) metapackage. Install all Stellars extensions at once: `pip install stellars_jupyterlab_extensions`

Navigate the file browser to your terminal's current working directory with a single click. Right-click on any terminal tab and select "Show in File Browser" to instantly jump to the directory where your terminal session is working.

**Full disclosure:** This extension does exactly one thing. It's not revolutionary, it won't change your life, and it definitely won't impress anyone at parties. But every time you `cd` somewhere and wonder "where am I again?" - it'll be there for you. Quietly. Unremarkably. Like a good friend who never asks for credit.

![Show in File Browser](.resources/screenshot.png)

## Features

- **Context menu on terminal tabs** - Right-click any terminal tab to reveal "Show in File Browser" option
- **Context menu in terminal area** - Also available when right-clicking inside the terminal
- **Server-side cwd detection** - Accurately determines terminal's working directory via process inspection
- **Cross-platform support** - Works on Linux (via /proc) and macOS (via lsof)
- **Graceful fallback** - Navigates to workspace root if terminal is outside the Jupyter workspace

## Installation

Requires JupyterLab 4.0.0 or higher.

```bash
pip install jupyterlab_terminal_show_in_file_browser_extension
```
