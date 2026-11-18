// Gera os PNGs de marca/png a partir de marca/pecas.html.
// Uso: node marca/exportar.js   (precisa do Playwright instalado)
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const pecas = [
  'foto-grupo', 'logo-horizontal', 'logo-horizontal-branco', 'post-convite',
  'story-convite', 'card-oferta', 'destaque-cozinha', 'destaque-casa', 'destaque-ofertas',
];

(async () => {
  const saida = path.join(__dirname, 'png');
  fs.mkdirSync(saida, { recursive: true });
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1200, height: 1000 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'pecas.html'));
  await page.evaluate(() => document.fonts.ready);
  await page.addStyleTag({ content: 'body{background:transparent!important}' });
  await page.waitForTimeout(500);
  for (const id of pecas) {
    const el = page.locator('#' + id);
    const transparente = id.startsWith('logo-horizontal');
    await el.screenshot({ path: path.join(saida, id + '.png'), omitBackground: transparente });
    console.log('ok', id);
  }
  await browser.close();
})();
