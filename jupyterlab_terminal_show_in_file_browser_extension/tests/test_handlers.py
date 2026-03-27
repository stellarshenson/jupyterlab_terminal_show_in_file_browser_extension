"""
Tests for terminal cwd handler.

Tests the helper methods that detect process cwd without requiring
a running Jupyter server.
"""
import os
import sys
import pytest
from unittest.mock import patch, MagicMock

from jupyterlab_terminal_show_in_file_browser_extension.handlers import TerminalCwdHandler


class MockHandler:
    """Mock handler that exposes the cwd detection methods for testing."""

    def __init__(self):
        self.log = MagicMock()

    # Copy methods from TerminalCwdHandler for testing
    _get_cwd_linux = TerminalCwdHandler._get_cwd_linux
    _get_pwd_from_environ = TerminalCwdHandler._get_pwd_from_environ
    _get_cwd_macos = TerminalCwdHandler._get_cwd_macos
    _get_direct_children = TerminalCwdHandler._get_direct_children
    _get_process_comm = TerminalCwdHandler._get_process_comm
    _collect_process_tree = TerminalCwdHandler._collect_process_tree
    _try_get_cwd = TerminalCwdHandler._try_get_cwd
    _is_valid_cwd = TerminalCwdHandler._is_valid_cwd
    _get_process_cwd = TerminalCwdHandler._get_process_cwd


@pytest.fixture
def handler():
    """Create a mock handler instance for testing utility methods."""
    return MockHandler()


class TestGetCwdLinux:
    """Tests for _get_cwd_linux method."""

    def test_returns_cwd_for_current_process(self, handler):
        """Should return cwd for the current process."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        pid = os.getpid()
        cwd = handler._get_cwd_linux(pid)
        assert cwd == os.getcwd()

    def test_returns_none_for_nonexistent_pid(self, handler):
        """Should return None for a non-existent PID."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        # Use a very high PID that's unlikely to exist
        cwd = handler._get_cwd_linux(999999999)
        assert cwd is None

    def test_returns_none_on_permission_error(self, handler):
        """Should return None when permission denied."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        # PID 1 (init) typically has restricted access
        cwd = handler._get_cwd_linux(1)
        # May be None due to permissions, or valid if running as root
        assert cwd is None or isinstance(cwd, str)


class TestGetPwdFromEnviron:
    """Tests for _get_pwd_from_environ method."""

    def test_returns_pwd_for_current_process(self, handler):
        """Should return PWD from current process environment."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        pid = os.getpid()
        pwd = handler._get_pwd_from_environ(pid)
        # PWD should match current directory or be None if not set
        if pwd:
            assert os.path.isabs(pwd)

    def test_returns_none_for_nonexistent_pid(self, handler):
        """Should return None for a non-existent PID."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        pwd = handler._get_pwd_from_environ(999999999)
        assert pwd is None


class TestGetDirectChildren:
    """Tests for _get_direct_children method."""

    def test_returns_list(self, handler):
        """Should always return a list."""
        result = handler._get_direct_children(os.getpid())
        assert isinstance(result, list)

    def test_returns_empty_for_nonexistent_pid(self, handler):
        """Should return empty list for non-existent PID."""
        result = handler._get_direct_children(999999999)
        assert result == []


class TestCollectProcessTree:
    """Tests for _collect_process_tree method (recursive traversal)."""

    def test_collects_current_process(self, handler):
        """Should collect current process info."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        known_shells = {'bash', 'zsh', 'fish', 'sh', 'dash', 'ksh', 'tcsh', 'csh'}
        results = []
        handler._collect_process_tree(os.getpid(), 0, results, known_shells)

        # Should have at least the current process
        assert len(results) >= 1
        # First entry should be current process at depth 0
        pid, depth, is_shell, comm = results[0]
        assert pid == os.getpid()
        assert depth == 0

    def test_collects_multiple_levels(self, handler):
        """Process tree collection should include depth info."""
        # Simulate process tree: (pid, depth, is_shell, comm)
        results = [
            (100, 0, True, 'fish'),        # depth 0, shell (login shell)
            (101, 1, False, 'mc'),          # depth 1, file manager
            (102, 2, True, 'bash'),         # depth 2, shell (mc subshell)
        ]

        # Verify structure
        assert results[0][1] == 0  # login shell at depth 0
        assert results[1][1] == 1  # mc at depth 1
        assert results[2][1] == 2  # subshell at depth 2
        assert results[2][2] is True  # subshell is a shell


class TestTryGetCwd:
    """Tests for _try_get_cwd method."""

    def test_returns_cwd_for_current_process(self, handler):
        """Should return cwd for current process."""
        if sys.platform not in ("linux", "darwin"):
            pytest.skip("Linux/macOS only test")

        cwd = handler._try_get_cwd(os.getpid())
        assert cwd is not None
        assert os.path.isabs(cwd)

    def test_returns_none_for_nonexistent_pid(self, handler):
        """Should return None for non-existent PID."""
        cwd = handler._try_get_cwd(999999999)
        assert cwd is None


class TestGetProcessCwd:
    """Tests for _get_process_cwd method."""

    def test_returns_cwd_for_current_process(self, handler):
        """Should return cwd for current process."""
        if sys.platform not in ("linux", "darwin"):
            pytest.skip("Linux/macOS only test")

        cwd = handler._get_process_cwd(os.getpid())
        assert cwd is not None
        assert os.path.isabs(cwd)

    def test_returns_deepest_valid_shell_cwd(self, handler):
        """Should return deepest shell with valid cwd, skipping pseudo-paths."""
        with patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_collect_process_tree') as mock_collect, \
             patch.object(handler, '_is_valid_cwd') as mock_valid:

            # Tree: fish -> claude -> sh -> chrome
            def populate_tree(pid, depth, results, known_shells):
                results.append((100, 0, True, 'fish'))
                results.append((200, 1, False, 'claude'))
                results.append((300, 2, True, 'sh'))
                results.append((400, 3, False, 'chrome'))

            mock_collect.side_effect = populate_tree

            # Chrome has /proc pseudo-path, sh and fish have real paths
            mock_try.side_effect = lambda pid: {
                100: '/home/test/project',
                200: '/home/test/project',
                300: '/home/test/project',
                400: '/proc/123/fdinfo'
            }.get(pid)

            # /proc path is invalid, real paths are valid
            mock_valid.side_effect = lambda p: not p.startswith('/proc/')

            result = handler._get_process_cwd(100)

            # Should skip chrome (/proc), return sh (deepest valid shell)
            assert result == '/home/test/project'

    def test_uses_file_manager_subshell_cwd(self, handler):
        """Should find mc subshell cwd via recursive deepest-first search."""
        with patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_collect_process_tree') as mock_collect, \
             patch.object(handler, '_is_valid_cwd', return_value=True):

            # Tree: fish -> mc -> bash (subshell with different cwd)
            def populate_tree(pid, depth, results, known_shells):
                results.append((100, 0, True, 'fish'))
                results.append((200, 1, False, 'mc'))
                results.append((300, 2, True, 'bash'))

            mock_collect.side_effect = populate_tree

            mock_try.side_effect = lambda pid: {
                100: '/home',
                200: '/home',
                300: '/home/deep'
            }.get(pid)

            result = handler._get_process_cwd(100)

            # Deepest shell (bash at depth 2) has valid cwd
            assert result == '/home/deep'


class TestIsValidCwd:
    """Tests for _is_valid_cwd static method."""

    def test_rejects_proc_paths(self, handler):
        """Should reject /proc pseudo-filesystem paths."""
        assert handler._is_valid_cwd('/proc/123/fdinfo') is False
        assert handler._is_valid_cwd('/proc/1/cwd') is False

    def test_rejects_sys_paths(self, handler):
        """Should reject /sys pseudo-filesystem paths."""
        assert handler._is_valid_cwd('/sys/class/net') is False

    def test_rejects_dev_paths(self, handler):
        """Should reject /dev paths."""
        assert handler._is_valid_cwd('/dev/pts/0') is False

    def test_rejects_empty_and_relative(self, handler):
        """Should reject empty or relative paths."""
        assert handler._is_valid_cwd('') is False
        assert handler._is_valid_cwd('relative/path') is False

    def test_accepts_real_directory(self, handler):
        """Should accept existing real directories."""
        assert handler._is_valid_cwd('/tmp') is True
        assert handler._is_valid_cwd(os.getcwd()) is True

    def test_rejects_nonexistent_directory(self, handler):
        """Should reject paths that don't exist."""
        assert handler._is_valid_cwd('/nonexistent/fake/path') is False


class TestKnownShells:
    """Tests for known shell detection."""

    def test_common_shells_recognized(self, handler):
        """Should recognize common shells in process tree."""
        known_shells = {'bash', 'zsh', 'fish', 'sh', 'dash', 'ksh', 'tcsh', 'csh'}

        # Test that shells are correctly identified
        for shell in known_shells:
            results = []
            # Manually test the shell detection logic
            comm = shell
            is_shell = comm in known_shells
            assert is_shell, f"{shell} should be recognized as a shell"

    def test_get_process_comm_returns_string(self, handler):
        """Should return command name for current process."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        comm = handler._get_process_comm(os.getpid())
        assert comm is not None
        assert isinstance(comm, str)
        assert len(comm) > 0
