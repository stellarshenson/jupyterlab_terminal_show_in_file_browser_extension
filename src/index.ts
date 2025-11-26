import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { IDefaultFileBrowser } from '@jupyterlab/filebrowser';
import { ITerminalTracker } from '@jupyterlab/terminal';
import { showErrorMessage } from '@jupyterlab/apputils';
import { ServerConnection } from '@jupyterlab/services';
import { URLExt, PageConfig } from '@jupyterlab/coreutils';

/**
 * The command ID for showing terminal cwd in file browser.
 */
const COMMAND_ID = 'terminal:show-in-file-browser';

/**
 * Interface for the terminal cwd API response.
 */
interface ITerminalCwdResponse {
  terminal_name: string;
  cwd: string;
  error?: string;
}

/**
 * Fetch the current working directory for a terminal from the server.
 *
 * @param terminalName - The name of the terminal
 * @returns Promise resolving to the cwd path or null if not available
 */
async function fetchTerminalCwd(terminalName: string): Promise<string | null> {
  const settings = ServerConnection.makeSettings();
  const url = URLExt.join(
    settings.baseUrl,
    'api',
    'terminal-cwd',
    terminalName
  );

  try {
    const response = await ServerConnection.makeRequest(url, {}, settings);

    if (!response.ok) {
      const data = (await response.json()) as ITerminalCwdResponse;
      console.warn(`Failed to get terminal cwd: ${data.error}`);
      return null;
    }

    const data = (await response.json()) as ITerminalCwdResponse;
    return data.cwd;
  } catch (error) {
    console.error('Error fetching terminal cwd:', error);
    return null;
  }
}

/**
 * Expand tilde in path using the home directory extracted from absolutePath.
 *
 * @param path - Path that may contain ~
 * @param absolutePath - An absolute path to extract home directory from
 * @returns Path with ~ expanded, or original if expansion not possible
 */
function expandTilde(path: string, absolutePath: string): string {
  if (!path.startsWith('~')) {
    return path;
  }

  // Extract home directory from absolute path
  // Matches /home/username or /Users/username
  const match = absolutePath.match(/^(\/(?:home|Users)\/[^/]+)/);
  if (!match) {
    return path;
  }

  const homedir = match[1];
  if (path === '~') {
    return homedir;
  }
  if (path.startsWith('~/')) {
    return homedir + path.slice(1);
  }
  return path;
}

/**
 * Convert an absolute filesystem path to a path relative to the server root.
 *
 * @param absolutePath - The absolute filesystem path
 * @param serverRoot - The server's root directory (may contain ~)
 * @returns The relative path for the file browser, or null if outside server root
 */
function toRelativePath(
  absolutePath: string,
  serverRoot: string
): string | null {
  // Normalize cwd - ensure no trailing slashes
  const normalizedCwd = absolutePath.replace(/\/+$/, '');

  // Expand tilde in serverRoot and normalize
  let normalizedRoot = expandTilde(serverRoot, absolutePath).replace(/\/+$/, '');

  // Check if cwd is the server root
  if (normalizedCwd === normalizedRoot) {
    return '';
  }

  // Check if cwd is inside the server root
  const rootPrefix = normalizedRoot + '/';
  if (normalizedCwd.startsWith(rootPrefix)) {
    return normalizedCwd.slice(rootPrefix.length);
  }

  // cwd is outside the server root
  return null;
}

/**
 * Initialization data for the jupyterlab_terminal_show_in_file_browser_extension extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'jupyterlab_terminal_show_in_file_browser_extension:plugin',
  description:
    'JupyterLab extension to add context menu item to the terminal tab to navigate file browser to the pwd path of the terminal',
  autoStart: true,
  requires: [IDefaultFileBrowser, ITerminalTracker],
  activate: (
    app: JupyterFrontEnd,
    fileBrowser: IDefaultFileBrowser,
    terminalTracker: ITerminalTracker
  ) => {
    console.log(
      'JupyterLab extension jupyterlab_terminal_show_in_file_browser_extension is activated!'
    );

    const { commands } = app;

    // Get the server root directory from PageConfig
    // This is the notebook_dir where Jupyter server was started
    const serverRoot = PageConfig.getOption('serverRoot');
    console.log(`Server root: ${serverRoot}`);

    // Add the command
    commands.addCommand(COMMAND_ID, {
      label: 'Show in File Browser',
      caption: 'Navigate file browser to terminal current directory',
      isEnabled: () => {
        const widget = terminalTracker.currentWidget;
        return widget !== null;
      },
      execute: async () => {
        const widget = terminalTracker.currentWidget;
        if (!widget) {
          await showErrorMessage('No Terminal', 'No active terminal found.');
          return;
        }

        const session = widget.content.session;
        if (!session || !session.model) {
          await showErrorMessage(
            'Terminal Error',
            'Could not access terminal session.'
          );
          return;
        }

        const terminalName = session.model.name;

        // Fetch cwd from server
        const cwd = await fetchTerminalCwd(terminalName);

        if (!cwd) {
          await showErrorMessage(
            'CWD Not Available',
            'Could not determine terminal current directory. ' +
              'This may happen if the terminal process is not accessible.'
          );
          return;
        }

        console.log(`Terminal cwd: ${cwd}`);
        console.log(`Server root: ${serverRoot}`);

        // Convert absolute path to relative path for file browser
        const relativePath = toRelativePath(cwd, serverRoot);

        // If outside workspace, fallback to workspace root
        const targetPath = relativePath === null ? '' : relativePath;
        if (relativePath === null) {
          console.log(`Terminal cwd outside workspace, navigating to root`);
        }

        console.log(`Relative path: "${targetPath}"`);

        try {
          // Navigate using absolute path from root
          // Use '/' prefix to ensure navigation from workspace root, not current directory
          const absolutePath = targetPath === '' ? '/' : '/' + targetPath;
          console.log(`Navigating to absolute path: "${absolutePath}"`);

          await fileBrowser.model.cd(absolutePath);
          console.log(
            `File browser navigated to: ${targetPath || '(root)'}`
          );
        } catch (error) {
          console.error('Failed to navigate file browser:', error);
          await showErrorMessage(
            'Navigation Error',
            `Failed to navigate to: ${targetPath || '(root)'}\n` +
              `Error: ${error}`
          );
        }
      }
    });

    console.log(`Command registered: ${COMMAND_ID}`);
  }
};

export default plugin;
