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
    _get_all_child_pids = TerminalCwdHandler._get_all_child_pids
    _try_get_cwd = TerminalCwdHandler._try_get_cwd
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


class TestGetAllChildPids:
    """Tests for _get_all_child_pids method."""

    def test_returns_list(self, handler):
        """Should always return a list."""
        result = handler._get_all_child_pids(os.getpid())
        assert isinstance(result, list)

    def test_returns_empty_for_nonexistent_pid(self, handler):
        """Should return empty list for non-existent PID."""
        result = handler._get_all_child_pids(999999999)
        assert result == []

    def test_prioritizes_shell_processes(self, handler):
        """Should put known shells first in the list."""
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        # Mock the /proc filesystem reads
        with patch('os.path.exists') as mock_exists, \
             patch('builtins.open', create=True) as mock_open:

            # Setup: parent has children 100 (python), 101 (fish)
            mock_exists.side_effect = lambda p: p in [
                '/proc/1/task/1/children',
                '/proc/100/comm',
                '/proc/101/comm'
            ]

            def open_side_effect(path, *args, **kwargs):
                mock_file = MagicMock()
                if path == '/proc/1/task/1/children':
                    mock_file.read.return_value = '100 101'
                    mock_file.__enter__ = lambda s: mock_file
                    mock_file.__exit__ = MagicMock(return_value=False)
                elif path == '/proc/100/comm':
                    mock_file.read.return_value = 'python'
                    mock_file.__enter__ = lambda s: mock_file
                    mock_file.__exit__ = MagicMock(return_value=False)
                elif path == '/proc/101/comm':
                    mock_file.read.return_value = 'fish'
                    mock_file.__enter__ = lambda s: mock_file
                    mock_file.__exit__ = MagicMock(return_value=False)
                return mock_file

            mock_open.side_effect = open_side_effect

            result = handler._get_all_child_pids(1)

            # Fish should come before python (shells prioritized)
            assert 101 in result
            assert 100 in result
            fish_idx = result.index(101)
            python_idx = result.index(100)
            assert fish_idx < python_idx


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

    def test_tries_multiple_candidates(self, handler):
        """Should try direct pid and children."""
        with patch.object(handler, '_try_get_cwd') as mock_try, \
             patch.object(handler, '_get_all_child_pids') as mock_children:

            # First candidate fails, second succeeds
            mock_try.side_effect = [None, '/home/test']
            mock_children.return_value = [200]

            result = handler._get_process_cwd(100)

            assert result == '/home/test'
            assert mock_try.call_count == 2
            mock_try.assert_any_call(100)  # Direct pid
            mock_try.assert_any_call(200)  # Child pid


class TestKnownShells:
    """Tests for known shell detection."""

    def test_common_shells_recognized(self, handler):
        """Should recognize common shells."""
        known_shells = {'bash', 'zsh', 'fish', 'sh', 'dash', 'ksh', 'tcsh', 'csh'}

        # Verify the handler uses these shells
        # This tests the implementation detail but ensures compatibility
        if sys.platform != "linux":
            pytest.skip("Linux-only test")

        with patch('os.path.exists') as mock_exists, \
             patch('builtins.open', create=True) as mock_open:

            for shell in known_shells:
                mock_exists.return_value = True

                mock_file = MagicMock()
                mock_file.read.side_effect = ['100', shell]
                mock_file.__enter__ = lambda s: mock_file
                mock_file.__exit__ = MagicMock(return_value=False)
                mock_open.return_value = mock_file

                # Just verify no errors for each shell
                handler._get_all_child_pids(1)
