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
                "error": str(e)
            }))

    def _get_process_cwd(self, pid: int) -> str | None:
        """Get the current working directory of a process.

        Tries multiple methods:
        1. Read /proc/{pid}/cwd symlink (Linux)
        2. Read PWD from /proc/{pid}/environ (Linux)
        3. Use lsof (macOS)

        Args:
            pid: Process ID

        Returns:
            The cwd path or None if it couldn't be determined
        """
        # First, try to get the child process (the actual shell)
        # The pty process spawns a shell, we want the shell's cwd
        child_pid = self._get_child_pid(pid)
        target_pid = child_pid if child_pid else pid

        cwd = None

        if sys.platform == "linux":
            # Try /proc/pid/cwd first
            cwd = self._get_cwd_linux(target_pid)

            # Fallback to PWD from environment
            if cwd is None:
                cwd = self._get_pwd_from_environ(target_pid)

        elif sys.platform == "darwin":
            cwd = self._get_cwd_macos(target_pid)
        else:
            # Windows or other - try Linux methods
            cwd = self._get_cwd_linux(target_pid)
            if cwd is None:
                cwd = self._get_pwd_from_environ(target_pid)

        return cwd

    def _get_child_pid(self, parent_pid: int) -> int | None:
        """Get the first child process PID.

        Args:
            parent_pid: Parent process ID

        Returns:
            Child PID or None
        """
        try:
            if sys.platform == "linux":
                # Read children from /proc
                children_file = f"/proc/{parent_pid}/task/{parent_pid}/children"
                if os.path.exists(children_file):
                    with open(children_file, "r") as f:
                        children = f.read().strip().split()
                        if children:
                            return int(children[0])

            # Fallback: use pgrep
            result = subprocess.run(
                ["pgrep", "-P", str(parent_pid)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                if pids:
                    return int(pids[0])
        except Exception:
            pass

        return None

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

    def _get_pwd_from_environ(self, pid: int) -> str | None:
        """Get PWD environment variable from process environment.

        Args:
            pid: Process ID

        Returns:
            The PWD value or None
        """
        try:
            environ_file = f"/proc/{pid}/environ"
            if os.path.exists(environ_file):
                with open(environ_file, "rb") as f:
                    environ_data = f.read()
                    # Environment variables are null-separated
                    for entry in environ_data.split(b"\x00"):
                        if entry.startswith(b"PWD="):
                            return entry[4:].decode("utf-8", errors="replace")
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
