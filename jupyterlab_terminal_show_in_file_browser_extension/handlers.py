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

        Traverses the entire process tree recursively to find the deepest
        shell process. This handles cases like mc (Midnight Commander) which
        spawns a subshell - we want the subshell's cwd, not the parent shell.

        Priority order:
        1. Deepest shell process in the tree (e.g., mc's subshell)
        2. Any shell process found in the tree
        3. Direct pty process as fallback

        Args:
            pid: Process ID

        Returns:
            The cwd path or None if it couldn't be determined
        """
        known_shells = {'bash', 'zsh', 'fish', 'sh', 'dash', 'ksh', 'tcsh', 'csh'}

        # Build complete process tree with depth information
        # List of (pid, depth, is_shell, comm)
        all_processes = []
        self._collect_process_tree(pid, 0, all_processes, known_shells)

        # Sort by depth descending, shells first at each depth
        # This ensures we try the deepest shell first (mc's subshell)
        all_processes.sort(key=lambda x: (-x[1], not x[2]))

        # Try each process, deepest shells first
        for target_pid, depth, is_shell, comm in all_processes:
            cwd = self._try_get_cwd(target_pid)
            if cwd:
                return cwd

        # Fallback: try the original pid directly
        return self._try_get_cwd(pid)

    def _collect_process_tree(
        self,
        pid: int,
        depth: int,
        results: list,
        known_shells: set
    ) -> None:
        """Recursively collect all processes in the tree with depth info.

        Args:
            pid: Process ID to start from
            depth: Current depth in the tree
            results: List to append (pid, depth, is_shell, comm) tuples
            known_shells: Set of known shell command names
        """
        # Get process command name
        comm = self._get_process_comm(pid)
        is_shell = comm in known_shells if comm else False

        results.append((pid, depth, is_shell, comm))

        # Get direct children and recurse
        children = self._get_direct_children(pid)
        for child_pid in children:
            self._collect_process_tree(child_pid, depth + 1, results, known_shells)

    def _get_process_comm(self, pid: int) -> str | None:
        """Get the command name for a process.

        Args:
            pid: Process ID

        Returns:
            Command name or None
        """
        try:
            if sys.platform == "linux":
                comm_file = f"/proc/{pid}/comm"
                if os.path.exists(comm_file):
                    with open(comm_file, "r") as f:
                        return f.read().strip()
            else:
                # macOS/other: use ps
                result = subprocess.run(
                    ["ps", "-p", str(pid), "-o", "comm="],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    # ps may return full path, extract basename
                    return os.path.basename(result.stdout.strip())
        except Exception:
            pass
        return None

    def _get_direct_children(self, parent_pid: int) -> list[int]:
        """Get direct child PIDs of a process.

        Args:
            parent_pid: Parent process ID

        Returns:
            List of child PIDs
        """
        children = []
        try:
            if sys.platform == "linux":
                children_file = f"/proc/{parent_pid}/task/{parent_pid}/children"
                if os.path.exists(children_file):
                    with open(children_file, "r") as f:
                        for child in f.read().strip().split():
                            try:
                                children.append(int(child))
                            except ValueError:
                                pass

            # Fallback: use pgrep
            if not children:
                result = subprocess.run(
                    ["pgrep", "-P", str(parent_pid)],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0 and result.stdout.strip():
                    for pid_str in result.stdout.strip().split("\n"):
                        try:
                            children.append(int(pid_str))
                        except ValueError:
                            pass
        except Exception:
            pass
        return children

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
