import fs from 'node:fs/promises';
import path from 'node:path';

const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif']);

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function relPathToServerUrl(relPosix) {
  // 由本地 server.mjs 提供：/sence/<encoded rel path>
  const encoded = relPosix
    .split('/')
    .map((seg) => encodeURIComponent(seg))
    .join('/');
  return `/sence/${encoded}`;
}

async function walk(dir) {
  const out = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });
  for (const ent of entries) {
    const full = path.join(dir, ent.name);
    if (ent.isDirectory()) {
      out.push(...(await walk(full)));
    } else if (ent.isFile()) {
      const ext = path.extname(ent.name).toLowerCase();
      if (IMAGE_EXTS.has(ext)) out.push(full);
    }
  }
  return out;
}

async function listTopLevelCategories(srcDir) {
  const entries = await fs.readdir(srcDir, { withFileTypes: true });
  // 固定分区：只取一级文件夹名；保留读取顺序（不排序）
  return entries.filter((e) => e.isDirectory()).map((e) => e.name);
}

function parseArgs(argv) {
  const args = { src: '', out: '' };
  const rest = [...argv];
  while (rest.length) {
    const a = rest.shift();
    if (a === '--src') args.src = rest.shift() ?? '';
    else if (a === '--out') args.out = rest.shift() ?? '';
  }
  if (!args.src || !args.out) {
    console.error('Usage: node tools/build_scene_index.mjs --src "<sceneDir>" --out "<outJson>"');
    process.exit(1);
  }
  return args;
}

const { src, out } = parseArgs(process.argv.slice(2));

const fixedCategories = await listTopLevelCategories(src);

const files = await walk(src);
files.sort((a, b) => a.localeCompare(b, 'zh-CN'));

const items = files.map((absPath) => {
  const rel = path.relative(src, absPath);
  const parts = rel.split(path.sep).filter(Boolean);
  const category = parts.length >= 2 ? parts[0] : '未分区';
  const relPosix = toPosix(rel);
  return {
    category,
    name: path.basename(absPath),
    rel: relPosix,
    abs: absPath,
    url: relPathToServerUrl(relPosix),
  };
});

const hasUncategorized = items.some((i) => i.category === '未分区');
const categories = [...fixedCategories, ...(hasUncategorized ? ['未分区'] : [])];

const payload = {
  generatedAt: new Date().toISOString(),
  sourceDir: src,
  total: items.length,
  categories,
  items,
};

await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, JSON.stringify(payload, null, 2), 'utf8');

// 同时输出 JS 版本，避免 file:// 下 fetch JSON 被浏览器拦截
const outJs = out.replace(/\.json$/i, '.data.js');
const jsContent = `// Auto-generated. Do not edit.\nwindow.__SCENE_INDEX__ = ${JSON.stringify(
  payload
)};\n`;
await fs.writeFile(outJs, jsContent, 'utf8');

console.log(`Wrote ${items.length} items to ${out}`);

