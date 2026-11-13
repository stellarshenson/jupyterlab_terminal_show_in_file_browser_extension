import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { IDefaultFileBrowser } from '@jupyterlab/filebrowser';
import { ITerminalTracker } from '@jupyterlab/terminal';
import { showErrorMessage } from '@jupyterlab/apputils';
import { ServerConnection } from '@jupyterlab/services';
import { URLExt } from '@jupyterlab/coreutils';
import { ITranslator, nullTranslator } from '@jupyterlab/translation';
import { folderIcon } from '@jupyterlab/ui-components';

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
  root: string;
  error?: string;
}

/**
 * Fetch the current working directory for a terminal from the server.
 *
 * @param terminalName - The name of the terminal
 * @returns Promise resolving to the cwd and the server root, both absolute,
 * or null if not available
 */
async function fetchTerminalCwd(
  terminalName: string
): Promise<ITerminalCwdResponse | null> {
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

    return (await response.json()) as ITerminalCwdResponse;
  } catch (error) {
    console.error('Error fetching terminal cwd:', error);
    return null;
  }
}

/**
 * Convert an absolute filesystem path to a path relative to the server root.
 *
 * @param absolutePath - The absolute filesystem path
 * @param serverRoot - The server's root directory, absolute
 * @returns The relative path for the file browser, or null if outside server root
 */
function toRelativePath(
  absolutePath: string,
  serverRoot: string
): string | null {
  // Normalize cwd - ensure no trailing slashes
  const normalizedCwd = absolutePath.replace(/\/+$/, '');

  const normalizedRoot = serverRoot.replace(/\/+$/, '');

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
 * Initialization data for the @stellarshenson/jupyterlab-terminal-show-in-file-browser-extension extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: '@stellarshenson/jupyterlab-terminal-show-in-file-browser-extension:plugin',
  description:
    'JupyterLab extension to add context menu item to the terminal tab to navigate file browser to the pwd path of the terminal',
  autoStart: true,
  requires: [IDefaultFileBrowser, ITerminalTracker],
  optional: [ITranslator],
  activate: (
    app: JupyterFrontEnd,
    fileBrowser: IDefaultFileBrowser,
    terminalTracker: ITerminalTracker,
    translator: ITranslator | null
  ) => {
    console.log(
      'JupyterLab extension @stellarshenson/jupyterlab-terminal-show-in-file-browser-extension is activated!'
    );

    const { commands } = app;
    const trans = (translator ?? nullTranslator).load(
      'jupyterlab_terminal_show_in_file_browser_extension'
    );

    // The tab selector in schema/plugin.json matches every main-area tab, and
    // a tab carries no mark of its widget's kind. Whether the context menu was
    // opened on a terminal - on its tab or inside it - is decided here: a tab
    // holds its widget's id in data-id. On any other tab the item is hidden,
    // so a document tab keeps JupyterLab's own "Show in File Browser" alone.
    const contextMenuTerminal = () => {
      const node = app.contextMenuHitTest(
        node =>
          node.classList.contains('lm-TabBar-tab') ||
          node.classList.contains('jp-Terminal')
      );
      return node === undefined
        ? undefined
        : terminalTracker.find(
            widget =>
              widget.id === node.dataset.id || widget.content.node === node
          );
    };

    const openedOnTerminal = (): boolean => contextMenuTerminal() !== undefined;

    // Add the command
    commands.addCommand(COMMAND_ID, {
      label: trans.__('Show in File Browser'),
      icon: folderIcon,
      caption: trans.__('Navigate file browser to terminal current directory'),
      describedBy: { args: { type: 'object', properties: {} } },
      isVisible: openedOnTerminal,
      isEnabled: () => {
        const widget = terminalTracker.currentWidget;
        return widget !== null;
      },
      execute: async () => {
        const widget = contextMenuTerminal() ?? terminalTracker.currentWidget;
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
        const data = await fetchTerminalCwd(terminalName);

        if (!data?.cwd) {
          await showErrorMessage(
            'CWD Not Available',
            'Could not determine terminal current directory. ' +
              'This may happen if the terminal process is not accessible.'
          );
          return;
        }

        // Convert absolute path to relative path for file browser
        const relativePath = toRelativePath(data.cwd, data.root);

        // If outside workspace, fallback to workspace root
        const targetPath = relativePath === null ? '' : relativePath;

        try {
          // Navigate using absolute path from root
          // Use '/' prefix to ensure navigation from workspace root, not current directory
          const absolutePath = targetPath === '' ? '/' : '/' + targetPath;

          await fileBrowser.model.cd(absolutePath);
          // Show the file browser: the sidebar may be collapsed or on
          // another panel.
          app.shell.activateById(fileBrowser.id);
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
  }
};

export default plugin;
