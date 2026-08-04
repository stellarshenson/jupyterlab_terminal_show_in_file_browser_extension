"""
API handlers for terminal cwd retrieval.
"""
import json
import os
import subprocess
import sys

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado


class TerminalCwdHandler(APIHandler):
    """Handler for getting terminal current working directory."""

    @tornado.web.authenticated
    async def get(self, terminal_name: str):
        """Get the cwd for a terminal by name.

        Args:
            terminal_name: The name of the terminal (e.g., "1", "2")
        """
        try:
            # Get the terminal manager from the server app
            terminal_manager = self.settings.get("terminal_manager")

            if terminal_manager is None:
                self.set_status(503)
                self.finish(json.dumps({
                    "error": "Terminal service not available"
                }))
                return

            # Get the terminal instance
            terminal = terminal_manager.get_terminal(terminal_name)

            if terminal is None:
                self.set_status(404)
                self.finish(json.dumps({
                    "error": f"Terminal '{terminal_name}' not found"
                }))
                return

            # Get the pty process
            ptyproc = getattr(terminal, "ptyproc", None)

            if ptyproc is None:
                self.set_status(500)
                self.finish(json.dumps({
                    "error": "Could not access terminal process"
                }))
                return

            pid = ptyproc.pid
            cwd = self._get_process_cwd(pid)

            if cwd is None:
                self.set_status(500)
                self.finish(json.dumps({
                    "error": "Could not determine terminal cwd"
                }))
                return

            self.finish(json.dumps({
                "terminal_name": terminal_name,
                "cwd": cwd
            }))

        except Exception as e:
            self.log.error(f"Error getting terminal cwd: {e}")
            self.set_status(500)
            self.finish(json.dumps({
                "error": "Internal error determining terminal cwd"
            }))

    def _get_process_cwd(self, pid: int) -> str | None:
        """Get the current working directory for a terminal's shell process.

        Resolves the cwd via the pty's foreground process group (tpgid) - the
        process currently in the foreground of the controlling terminal, which
        is what the user is interacting with. Read from the pty shell's own
        /proc/{pid}/stat, this signal:
          - follows the active foreground program (e.g. mc, whose own process
            tracks the current panel directory),
          - excludes other terminals' sessions that a shared daemon may have
            spawned into this process subtree - they live on a different pty and
            can never be this terminal's foreground group.

        Falls back to the pty process's own cwd. Pseudo-filesystem paths
        (/proc, /sys, /dev) and non-directories are rejected via _is_valid_cwd.

        Args:
            pid: The pty process ID

        Returns:
            The cwd path or None if it couldn't be determined
        """
        # Primary: the foreground process group of the controlling terminal.
        tpgid = self._get_foreground_pgid(pid)
        if tpgid and tpgid > 0:
            cwd = self._try_get_cwd(tpgid)
            if cwd and self._is_valid_cwd(cwd):
                return cwd

        # Fallback: the pty process's own cwd (the terminal's shell).
        cwd = self._try_get_cwd(pid)
        if cwd and self._is_valid_cwd(cwd):
            return cwd

        return None

    def _get_foreground_pgid(self, pid: int) -> int | None:
        """Get the foreground process group id of a process's controlling
        terminal (Linux), from field 8 (tpgid) of /proc/{pid}/stat.

        This is the process group currently in the foreground of the pty - the
        program the user is interacting with.

        Args:
            pid: Process ID (the pty shell)

        Returns:
            The tpgid integer, or None if unavailable (e.g. non-Linux, or the
            process has no controlling terminal)
        """
        try:
            with open(f"/proc/{pid}/stat") as f:
                data = f.read()
            # Field 2 (comm) is wrapped in parentheses and may itself contain
            # spaces or ')'; split the remainder after the final ')'. The
            # tokens then begin at field 3 (state), so tpgid (field 8) is
            # index 5.
            fields = data[data.rindex(")") + 2:].split()
            return int(fields[5])
        except (OSError, ValueError, IndexError):
            return None

    def _is_valid_cwd(self, path: str) -> bool:
        """Check whether a cwd path is a real filesystem directory.

        Filters out pseudo-filesystem paths (e.g. /proc/*/fdinfo,
        /sys/*) that appear on sandboxed processes like Chrome.

        Args:
            path: Absolute path to validate

        Returns:
            True if the path is a usable real directory
        """
        if not path or not path.startswith('/'):
            return False
        # Reject kernel pseudo-filesystems
        if path.startswith(('/proc/', '/sys/', '/dev/')):
            return False
        return os.path.isdir(path)

    def _try_get_cwd(self, pid: int) -> str | None:
        """Try to get cwd for a specific process.

        Args:
            pid: Process ID

        Returns:
            The cwd path or None
        """
        if sys.platform == "darwin":
            return self._get_cwd_macos(pid)
        # Linux (and any other platform exposing /proc); returns None where
        # /proc is absent.
        return self._get_cwd_linux(pid)

    def _get_cwd_linux(self, pid: int) -> str | None:
        """Get process cwd on Linux using /proc filesystem.

        Args:
            pid: Process ID

        Returns:
            The cwd path or None
        """
        try:
            cwd_link = f"/proc/{pid}/cwd"
            if os.path.exists(cwd_link):
                return os.readlink(cwd_link)
        except (OSError, PermissionError):
            pass
        return None

    def _get_cwd_macos(self, pid: int) -> str | None:
        """Get process cwd on macOS using lsof.

        Args:
            pid: Process ID

        Returns:
            The cwd path or None
        """
        try:
            result = subprocess.run(
                ["lsof", "-a", "-p", str(pid), "-d", "cwd", "-Fn"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("n"):
                        return line[1:]  # Remove the 'n' prefix
        except Exception:
            pass
        return None


def setup_handlers(web_app):
    """Setup the API handlers.

    Args:
        web_app: The Jupyter server web application
    """
    host_pattern = ".*$"
    base_url = web_app.settings["base_url"]

    # Route pattern for terminal cwd endpoint
    route_pattern = url_path_join(
        base_url,
        "api",
        "terminal-cwd",
        "([^/]+)"  # terminal_name parameter
    )

    handlers = [(route_pattern, TerminalCwdHandler)]
    web_app.add_handlers(host_pattern, handlers)
