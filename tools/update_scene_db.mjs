/**
 * 扫描 Sence 目录，生成 scene-db.json 图片数据库
 * 数据库包含：items（图片列表）、favorites（收藏）、trash（回收站）
 * 若已有 db 文件则保留其中的 favorites 和 trash
 */
import fs from 'node:fs/promises';
import path from 'node:path';

const IMAGE_EXTS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif']);

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function relPathToServerUrl(relPosix) {
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
    console.error('Usage: node tools/update_scene_db.mjs --src "<sceneDir>" --out "<outJson>"');
    process.exit(1);
  }
  return args;
}

const { src, out } = parseArgs(process.argv.slice(2));

// 读取已有 db，保留 favorites/trash，且已存在图片完整保留原 item
let oldFavorites = [];
let oldTrash = [];
let oldItemMap = new Map(); // abs -> old item

try {
  const raw = await fs.readFile(out, 'utf8');
  const old = JSON.parse(raw);
  if (Array.isArray(old.favorites)) oldFavorites = old.favorites;
  if (Array.isArray(old.trash)) oldTrash = old.trash;
  if (Array.isArray(old.items)) {
    old.items.forEach((it) => {
      if (it && typeof it.abs === 'string' && it.abs) {
        oldItemMap.set(it.abs, it);
      }
    });
  }
} catch {
  // ignore
}

const files = await walk(src);
files.sort((a, b) => a.localeCompare(b, 'zh-CN'));

const allAbsSet = new Set(files);
const items = files.map((absPath) => {
  // 已存在图片：完整保留原 item（天气、分类、标签等都不更新）
  const oldItem = oldItemMap.get(absPath);
  if (oldItem) {
    return { ...oldItem };
  }

  const rel = path.relative(src, absPath);
  const parts = rel.split(path.sep).filter(Boolean);
  let category = parts.length >= 2 ? parts[0] : '未分区';
  const relPosix = toPosix(rel);
  
  const item = {
    category,
    name: path.basename(absPath),
    rel: relPosix,
    abs: absPath,
    url: relPathToServerUrl(relPosix),
  };

  return item;
});

const fixedCategories = await listTopLevelCategories(src);
const hasUncategorized = items.some((i) => i.category === '未分区');
const itemCategories = [...new Set(items.map((i) => i.category).filter(Boolean))];
const categories = [
  ...new Set([
    ...fixedCategories,
    ...itemCategories,
    ...(hasUncategorized ? ['未分区'] : []),
  ]),
];

// 只保留仍存在的路径
const favorites = oldFavorites.filter((p) => allAbsSet.has(p));
const trash = oldTrash.filter((p) => allAbsSet.has(p));

const payload = {
  version: 1,
  generatedAt: new Date().toISOString(),
  sourceDir: src,
  total: items.length,
  categories,
  items,
  favorites,
  trash,
};

await fs.mkdir(path.dirname(out), { recursive: true });
await fs.writeFile(out, JSON.stringify(payload, null, 2), 'utf8');

// 同时输出 .data.js 供 file:// 使用
const outJs = out.replace(/\.json$/i, '.data.js');
const jsContent = `// Auto-generated. Do not edit.\nwindow.__SCENE_DB__ = ${JSON.stringify(payload)};\n`;
await fs.writeFile(outJs, jsContent, 'utf8');

console.log(`Wrote ${items.length} items, ${favorites.length} favorites, ${trash.length} trash to ${out}`);
