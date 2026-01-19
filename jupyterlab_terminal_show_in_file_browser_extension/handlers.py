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

        Tries multiple methods and process candidates:
        1. Try the direct pid first (terminado spawns shell directly)
        2. Try child processes, preferring known shells
        3. For each candidate, try /proc/cwd, PWD environ, or lsof

        Args:
            pid: Process ID

        Returns:
            The cwd path or None if it couldn't be determined
        """
        # Build list of candidate PIDs to try
        # Start with the direct pid (terminado spawns shell as direct child)
        candidates = [pid]

        # Add all child processes
        child_pids = self._get_all_child_pids(pid)
        candidates.extend(child_pids)

        # Try each candidate until we find a valid cwd
        for target_pid in candidates:
            cwd = self._try_get_cwd(target_pid)
            if cwd:
                return cwd

        return None

    def _try_get_cwd(self, pid: int) -> str | None:
        """Try to get cwd for a specific process.

        Args:
            pid: Process ID

        Returns:
            The cwd path or None
        """
        cwd = None

        if sys.platform == "linux":
            # Try /proc/pid/cwd first
            cwd = self._get_cwd_linux(pid)

            # Fallback to PWD from environment
            if cwd is None:
                cwd = self._get_pwd_from_environ(pid)

        elif sys.platform == "darwin":
            cwd = self._get_cwd_macos(pid)
        else:
            # Windows or other - try Linux methods
            cwd = self._get_cwd_linux(pid)
            if cwd is None:
                cwd = self._get_pwd_from_environ(pid)

        return cwd

    def _get_all_child_pids(self, parent_pid: int) -> list[int]:
        """Get all child process PIDs, sorted by shell likelihood.

        Args:
            parent_pid: Parent process ID

        Returns:
            List of child PIDs, with known shells first
        """
        child_pids = []
        shell_pids = []
        known_shells = {'bash', 'zsh', 'fish', 'sh', 'dash', 'ksh', 'tcsh', 'csh'}

        try:
            if sys.platform == "linux":
                # Read children from /proc
                children_file = f"/proc/{parent_pid}/task/{parent_pid}/children"
                if os.path.exists(children_file):
                    with open(children_file, "r") as f:
                        children = f.read().strip().split()
                        for child in children:
                            try:
                                pid = int(child)
                                # Check if this is a known shell
                                comm_file = f"/proc/{pid}/comm"
                                if os.path.exists(comm_file):
                                    with open(comm_file, "r") as cf:
                                        comm = cf.read().strip()
                                        if comm in known_shells:
                                            shell_pids.append(pid)
                                        else:
                                            child_pids.append(pid)
                                else:
                                    child_pids.append(pid)
                            except (ValueError, OSError):
                                pass

            # Fallback: use pgrep
            if not child_pids and not shell_pids:
                result = subprocess.run(
                    ["pgrep", "-P", str(parent_pid)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for pid_str in result.stdout.strip().split("\n"):
                        try:
                            pid = int(pid_str)
                            # Check if this is a known shell
                            comm_file = f"/proc/{pid}/comm"
                            if os.path.exists(comm_file):
                                with open(comm_file, "r") as cf:
                                    comm = cf.read().strip()
                                    if comm in known_shells:
                                        shell_pids.append(pid)
                                    else:
                                        child_pids.append(pid)
                            else:
                                child_pids.append(pid)
                        except (ValueError, OSError):
                            pass
        except Exception:
            pass

        # Return shells first, then other children
        return shell_pids + child_pids

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
