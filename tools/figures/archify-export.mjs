#!/usr/bin/env node
// archify の HTML をヘッドレス Chrome で開き、Export メニューから画像を書き出す。
// 使い方: node archify-export.mjs <html> <出力ディレクトリ> [light|dark] [png|jpeg|webp|svg-light|svg-dark] [--plain] [--css <file>]...
// --plain: 記事やスライドに画像で貼る用。白背景で、グリッドの点・外側の余白・タイトルを入れない（png・jpeg・webp のみ）
// --css: 書き出す直前にページへ差し込む CSS。複数指定できる。archify が画像に取り込むのは svg などで始まるセレクタのルールだけ
// sandbox の中では Chrome がプロファイルを作れないので、sandbox の外で実行する。
import { spawn } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { setTimeout as sleep } from 'node:timers/promises';

const argv = process.argv.slice(2);
let plain = false;
const cssFiles = [];
const positional = [];
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--plain') plain = true;
  else if (argv[i] === '--css') cssFiles.push(argv[++i]);
  else positional.push(argv[i]);
}
const [htmlArg, outArg, theme = 'light', format = 'png'] = positional;
if (!htmlArg || !outArg || cssFiles.includes(undefined)) {
  console.error('usage: archify-export.mjs <html> <out-dir> [light|dark] [png|jpeg|webp|svg-light|svg-dark] [--plain] [--css <file>]...');
  process.exit(2);
}
const extraCss = cssFiles.map((f) => readFileSync(resolve(f), 'utf8')).join('\n');
const rasterMime = { png: 'image/png', jpeg: 'image/jpeg', webp: 'image/webp' }[format];
if (plain && !rasterMime) {
  console.error('--plain は png・jpeg・webp でだけ使える');
  process.exit(2);
}
const outDir = resolve(outArg);
mkdirSync(outDir, { recursive: true });
const url = new URL(pathToFileURL(resolve(htmlArg)));
url.searchParams.set('theme', theme);

const chromePath = process.env.CHROME_PATH ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const profile = mkdtempSync(join(tmpdir(), 'archify-export-'));
const chrome = spawn(chromePath, [
  '--headless=new', '--disable-gpu', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, '--window-size=1440,1000', 'about:blank',
], { stdio: 'ignore' });

let exitCode = 1;
try {
  const port = await waitForPort(profile);
  const version = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json();
  const page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === 'page');
  const browser = await connect(version.webSocketDebuggerUrl);
  await browser.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: outDir });
  const tab = await connect(page.webSocketDebuggerUrl);
  await tab.send('Page.enable');
  const loaded = tab.once('Page.loadEventFired');
  await tab.send('Page.navigate', { url: url.href });
  await loaded;
  await sleep(1500);

  if (extraCss) {
    await tab.send('Runtime.evaluate', {
      expression: `(() => {
        const style = document.createElement('style');
        style.textContent = ${JSON.stringify(extraCss)};
        document.head.appendChild(style);
      })()`,
    });
  }

  // archify は書き出す時点の --bg、カードの点の背景、h1 から背景・グリッド・タイトルを描く
  if (plain) {
    await tab.send('Runtime.evaluate', {
      expression: `(() => {
        const root = document.documentElement;
        root.style.setProperty('--bg', '#ffffff');
        root.style.setProperty('--panel-border', 'transparent');
        const card = document.querySelector('.diagram-container');
        if (card) card.style.backgroundImage = 'none';
        for (const el of document.querySelectorAll('.header h1, .header .subtitle')) el.textContent = '';
      })()`,
    });
  }

  const before = new Set(readdirSync(outDir));
  const { result } = await tab.send('Runtime.evaluate', {
    userGesture: true,
    returnByValue: true,
    expression: `(() => {
      document.getElementById('btn-export')?.click();
      const item = document.querySelector('.export-menu button[data-format="${format}"]');
      if (!item) return { error: 'export item not found: ${format}' };
      item.click();
      return { theme: document.documentElement.getAttribute('data-theme') };
    })()`,
  });
  if (result.value?.error) throw new Error(result.value.error);

  // ダウンロード完了（.crdownload が消える）まで最大 15 秒待つ
  for (let i = 0; i < 75; i++) {
    const added = readdirSync(outDir).filter((f) => !before.has(f));
    if (added.length > 0 && added.every((f) => !f.endsWith('.crdownload'))) {
      for (const f of added) {
        if (plain) await cropMargin(tab, join(outDir, f), rasterMime);
        console.log(join(outDir, f));
      }
      console.log(`theme=${result.value.theme} format=${format}${plain ? ' plain' : ''}`);
      exitCode = 0;
      break;
    }
    await sleep(200);
  }
  if (exitCode !== 0) console.error('download did not finish within 15s');
} catch (e) {
  console.error(e.message);
} finally {
  chrome.kill();
  await sleep(300);
  rmSync(profile, { recursive: true, force: true });
}
process.exit(exitCode);

// カードの外側の余白と角の丸みの分を切り落とす。
// 28・24・16 は archify の assets/template.html の FIGURE_MARGIN・FIGURE_CARD_PADDING・カードの角の半径。
// archify を更新したら値が変わっていないか確かめる。
async function cropMargin(tab, file, mime) {
  const b64 = readFileSync(file).toString('base64');
  const { result, exceptionDetails } = await tab.send('Runtime.evaluate', {
    awaitPromise: true,
    returnByValue: true,
    expression: `(async () => {
      const img = new Image();
      img.src = 'data:${mime};base64,${b64}';
      await img.decode();
      const vb = document.querySelector('.diagram-container svg').viewBox.baseVal;
      const scale = img.naturalWidth / (vb.width + 2 * 24 + 2 * 28);
      const inset = Math.round((28 + 16) * scale);
      const canvas = document.createElement('canvas');
      canvas.width = img.naturalWidth - 2 * inset;
      canvas.height = img.naturalHeight - 2 * inset;
      canvas.getContext('2d').drawImage(img, inset, inset, canvas.width, canvas.height, 0, 0, canvas.width, canvas.height);
      return canvas.toDataURL('${mime}').split(',')[1];
    })()`,
  });
  if (exceptionDetails || typeof result.value !== 'string') throw new Error(`crop failed: ${JSON.stringify(exceptionDetails ?? result)}`);
  writeFileSync(file, Buffer.from(result.value, 'base64'));
}

async function waitForPort(dir) {
  for (let i = 0; i < 50; i++) {
    try {
      return readFileSync(join(dir, 'DevToolsActivePort'), 'utf8').split('\n')[0];
    } catch {
      await sleep(200);
    }
  }
  throw new Error('Chrome did not start (DevToolsActivePort not found)');
}

function connect(wsUrl) {
  const ws = new WebSocket(wsUrl);
  let id = 0;
  const pending = new Map();
  const waiters = [];
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.id && pending.has(msg.id)) {
      const { res, rej } = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) rej(new Error(JSON.stringify(msg.error)));
      else res(msg.result);
    } else if (msg.method) {
      for (const w of waiters.filter((x) => x.method === msg.method)) {
        waiters.splice(waiters.indexOf(w), 1);
        w.res(msg.params);
      }
    }
  };
  return new Promise((ready) => {
    ws.onopen = () => ready({
      send: (method, params = {}) => new Promise((res, rej) => {
        const i = ++id;
        pending.set(i, { res, rej });
        ws.send(JSON.stringify({ id: i, method, params }));
      }),
      once: (method) => new Promise((res) => waiters.push({ method, res })),
    });
  });
}
