import { expect, IJupyterLabPageFixture, test } from '@jupyterlab/galata';

const LABEL = 'Show in File Browser';

// The shown menu items with the label. A hidden item stays in the DOM, so
// only visible ones count.
const shownItems = (page: IJupyterLabPageFixture) =>
  page.locator('.lm-Menu-item:visible', { hasText: LABEL });

const tab = (page: IJupyterLabPageFixture, text: string) =>
  page.locator('.lm-DockPanel-tabBar .lm-TabBar-tab', { hasText: text });

const openTerminal = async (
  page: IJupyterLabPageFixture,
  cwd: string
): Promise<void> => {
  await page.evaluate(async cwd => {
    await (window as any).jupyterapp.commands.execute('terminal:create-new', {
      cwd
    });
  }, cwd);
  await page.locator('.jp-Terminal').waitFor();
};

const browserPath = (page: IJupyterLabPageFixture): Promise<string> =>
  page.evaluate(async () => {
    const browser = await (window as any).galata.getPlugin(
      '@jupyterlab/filebrowser-extension:default-file-browser'
    );
    return browser.model.path;
  });

test.describe('Show in File Browser menu item', () => {
  // The item's tab selector matches every main-area tab. On a document tab
  // JupyterLab has its own item with the same label, so this extension's item
  // must stay hidden there, also while a terminal is open.
  test('a document tab shows only the item of JupyterLab', async ({
    page,
    tmpPath
  }) => {
    await page.contents.uploadContent('hello', 'text', `${tmpPath}/note.txt`);
    await openTerminal(page, tmpPath);
    await page.filebrowser.open(`${tmpPath}/note.txt`);
    await tab(page, 'note.txt').click({ button: 'right' });
    await expect(page.locator('.lm-Menu')).toBeVisible();
    await expect(shownItems(page)).toHaveCount(1);
    await expect(shownItems(page)).toHaveAttribute(
      'data-command',
      'docmanager:show-in-file-browser'
    );
  });

  test('a terminal tab shows the item, and it opens the folder of the terminal', async ({
    page,
    tmpPath
  }) => {
    const folder = `${tmpPath}/sub`;
    await page.contents.uploadContent('hello', 'text', `${folder}/note.txt`);
    await page.filebrowser.openDirectory(tmpPath);
    await openTerminal(page, folder);
    expect(await browserPath(page)).toBe(tmpPath);

    await tab(page, 'Terminal').click({ button: 'right' });
    await expect(page.locator('.lm-Menu')).toBeVisible();
    await expect(shownItems(page)).toHaveCount(1);
    await expect(shownItems(page)).toHaveAttribute(
      'data-command',
      'terminal:show-in-file-browser'
    );
    await shownItems(page).click();
    await expect.poll(() => browserPath(page)).toBe(folder);
  });

  test('the menu inside a terminal shows the item', async ({
    page,
    tmpPath
  }) => {
    await openTerminal(page, tmpPath);
    await page.locator('.jp-Terminal').click({ button: 'right' });
    await expect(page.locator('.lm-Menu')).toBeVisible();
    await expect(shownItems(page)).toHaveCount(1);
    await expect(shownItems(page)).toHaveAttribute(
      'data-command',
      'terminal:show-in-file-browser'
    );
  });
});
