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
    _get_cwd_macos = TerminalCwdHandler._get_cwd_macos
    _get_foreground_pgid = TerminalCwdHandler._get_foreground_pgid
    _try_get_cwd = TerminalCwdHandler._try_get_cwd
    _is_valid_cwd = TerminalCwdHandler._is_valid_cwd
    _get_recovered_cwd = TerminalCwdHandler._get_recovered_cwd
    _nearest_existing_dir = TerminalCwdHandler._nearest_existing_dir
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


class TestGetForegroundPgid:
    """Tests for _get_foreground_pgid method (tpgid, field 8 of /proc/pid/stat)."""

    def test_returns_int_for_current_process(self, handler):
        """Should return an integer tpgid for the current process."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        tpgid = handler._get_foreground_pgid(os.getpid())
        assert isinstance(tpgid, int)

    def test_returns_none_for_nonexistent_pid(self, handler):
        """Should return None for a non-existent PID."""
        assert handler._get_foreground_pgid(999999999) is None

    def test_parses_comm_with_spaces_and_parens(self, handler):
        """tpgid must parse correctly even when comm contains spaces or ')'.

        The stat line is split after the FINAL ')', so a process command name
        like 'node (v20)' or 'foo) (bar' must not throw off the field offset.
        """
        # pid (comm) state ppid pgrp session tty_nr tpgid ...
        #  1   2      3     4    5     6       7      8
        line = "100 (node (v20)) S 1 100 100 34816 2688654 rest ignored\n"
        with patch("builtins.open") as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = line
            assert handler._get_foreground_pgid(100) == 2688654


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
    """Tests for _get_process_cwd method (tpgid-based resolution)."""

    def test_returns_cwd_for_current_process(self, handler):
        """Should return cwd for current process."""
        if sys.platform not in ("linux", "darwin"):
            pytest.skip("Linux/macOS only test")

        cwd = handler._get_process_cwd(os.getpid())
        assert cwd is not None
        assert os.path.isabs(cwd)

    def test_resolves_via_foreground_process_group(self, handler):
        """Should return the cwd of the pty's foreground process group leader,
        not the pty pid's own cwd."""
        with patch.object(handler, '_get_foreground_pgid', return_value=555), \
             patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_is_valid_cwd', return_value=True):

            mock_try.side_effect = lambda pid: {
                555: '/home/lab/workspace/pmrcorporate/pmr-sales-support',
                100: '/home/lab',  # pty pid - must NOT be used while tpgid valid
            }.get(pid)

            result = handler._get_process_cwd(100)

            assert result == '/home/lab/workspace/pmrcorporate/pmr-sales-support'

    def test_ignores_foreign_session(self, handler):
        """Reproduces the reported bug: a shared claude-code daemon grafted a
        DIFFERENT project's shell into this terminal's process subtree, and the
        old tree-walk resolved that foreign cwd.

        With tpgid we only read this pty's foreground process group, which can
        never be a foreign session on another TTY - so the foreign cwd is never
        consulted. Here the foreground group leader is in the correct project.
        """
        with patch.object(handler, '_get_foreground_pgid', return_value=200), \
             patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_is_valid_cwd', return_value=True):

            # 200 = this pty's foreground group (correct project). A foreign
            # session (pid 900, kolomolo) is simply never read by tpgid.
            mock_try.side_effect = lambda pid: {
                200: '/home/lab/workspace/pmrcorporate/pmr-sales-support',
                900: '/home/lab/workspace/kolomolo/sales/proposals',
            }.get(pid)

            result = handler._get_process_cwd(100)

            assert result == '/home/lab/workspace/pmrcorporate/pmr-sales-support'

    def test_follows_navigating_foreground_program(self, handler):
        """mc-style navigation: the foreground process group leader (mc itself)
        tracks the current directory, so its cwd - not the idle pty login
        shell's - must be returned (entry-10 behaviour kept)."""
        with patch.object(handler, '_get_foreground_pgid', return_value=300), \
             patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_is_valid_cwd', return_value=True):

            mock_try.side_effect = lambda pid: {
                300: '/home/deep',  # foreground program (e.g. mc), navigated dir
                100: '/home',       # pty login shell, unchanged
            }.get(pid)

            result = handler._get_process_cwd(100)

            assert result == '/home/deep'

    def test_falls_back_to_pty_pid_when_no_foreground(self, handler):
        """When there is no foreground group, use the pty process's own cwd."""
        with patch.object(handler, '_get_foreground_pgid', return_value=None), \
             patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_is_valid_cwd', return_value=True):

            mock_try.side_effect = lambda pid: {100: '/home/project'}.get(pid)

            result = handler._get_process_cwd(100)

            assert result == '/home/project'

    def test_falls_back_when_foreground_cwd_invalid(self, handler):
        """A foreground cwd that fails validation (pseudo-path) must be skipped
        in favour of the validated pty-pid fallback."""
        with patch.object(handler, '_get_foreground_pgid', return_value=300), \
             patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_is_valid_cwd',
                          side_effect=lambda p: not p.startswith('/proc/')):

            mock_try.side_effect = lambda pid: {
                300: '/proc/300/fdinfo',  # invalid
                100: '/home/project',     # valid fallback
            }.get(pid)

            result = handler._get_process_cwd(100)

            assert result == '/home/project'

    def test_fallback_validates_cwd(self, handler):
        """The fallback path must also reject pseudo-paths, returning None
        rather than a bogus directory."""
        with patch.object(handler, '_get_foreground_pgid', return_value=None), \
             patch.object(handler, '_try_get_cwd', return_value='/proc/1/fdinfo'), \
             patch.object(handler, '_get_recovered_cwd', return_value=None), \
             patch.object(handler, '_is_valid_cwd',
                          side_effect=lambda p: not p.startswith('/proc/')):

            result = handler._get_process_cwd(100)

            assert result is None

    def test_recovers_ancestor_when_cwd_deleted(self, handler):
        """When the shell's directory has been deleted (both tpgid and pty-pid
        cwds gone), degrade to the nearest existing ancestor rather than fail.

        Reproduces the reported 'CWD Not Available': a terminal whose fish
        login shell sits in a since-deleted directory.
        """
        with patch.object(handler, '_get_foreground_pgid', return_value=None), \
             patch.object(handler, '_try_get_cwd', return_value=None), \
             patch.object(handler, '_get_recovered_cwd',
                          return_value='/home/lab/workspace/private/henryk/court-cases'):

            result = handler._get_process_cwd(100)

            assert result == '/home/lab/workspace/private/henryk/court-cases'


class TestNearestExistingDir:
    """Tests for _nearest_existing_dir method (deleted-cwd recovery)."""

    def test_strips_deleted_suffix_and_walks_up(self, handler):
        """A '<path> (deleted)' cwd should resolve to the nearest ancestor
        that still exists."""
        gone = '/tmp/nonexistent-parent-xyz/gone-child (deleted)'
        assert handler._nearest_existing_dir(gone) == '/tmp'

    def test_returns_existing_dir_unchanged(self, handler):
        """An existing directory should be returned as-is."""
        assert handler._nearest_existing_dir('/tmp') == '/tmp'

    def test_returns_none_for_relative_or_empty(self, handler):
        """Reject non-absolute or empty input."""
        assert handler._nearest_existing_dir('') is None
        assert handler._nearest_existing_dir('relative/path') is None

    def test_returns_none_when_no_ancestor_exists(self, handler):
        """A path with no existing ancestor (below root) yields None."""
        assert handler._nearest_existing_dir('/nonexistent-root-xyz/a/b') is None


class TestIsValidCwd:
    """Tests for _is_valid_cwd method."""

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
