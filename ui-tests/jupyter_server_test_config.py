"""Server configuration for integration tests.

!! Never use this configuration in production because it
opens the server to the world and provide access to JupyterLab
JavaScript objects through the global window variable.
"""
import os
from tempfile import mkdtemp

from jupyterlab.galata import configure_jupyter_server

configure_jupyter_server(c)

# Galata pins port 8888 with no retries. JUPYTER_TEST_PORT moves the server when
# 8888 is taken; `or` rather than a get() default, so an exported-but-empty
# value falls back like JavaScript's `||` in playwright.config.js does.
c.ServerApp.port = int(os.environ.get("JUPYTER_TEST_PORT") or "8888")

# Settings written during a test land in a fresh folder, never in the
# developer's own ~/.jupyter/lab/user-settings.
c.LabApp.user_settings_dir = mkdtemp(prefix="galata-settings-")

# A startup tab other than the Launcher hangs galata's readiness wait. Ignored
# where the extension is not installed, as in CI.
c.GalaxaHubMotd.open_on_start = False

# Uncomment to set server log level to debug level
# c.ServerApp.log_level = "DEBUG"
