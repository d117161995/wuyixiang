import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawn } from 'node:child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// 约定：
// - /            -> story 目录（项目根目录）
// - /sence/...   -> 外部图片目录（本机路径）
const PORT = Number(process.env.PORT || 5173);
const HOST = process.env.HOST || '127.0.0.1';
const SCENE_DIR = __dirname;
const STORY_DIR = path.resolve(SCENE_DIR, '..'); // story 目录作为 Web 根目录
const DIST_DIR = path.resolve(path.resolve(SCENE_DIR, '..', '..'), 'dist');
const USE_DIST = String(process.env.SERVE_DIST || '').trim() === '1';
const STATIC_ROOT = USE_DIST ? DIST_DIR : STORY_DIR;
const SENCE_DIR = process.env.SENCE_DIR || 'Y:\\tmp\\WuYiXiang\\XXD_AI\\Asset\\Sence';
const PROJECT_ROOT = path.resolve(SCENE_DIR, '..', '..');
const DB_UPDATE_SCRIPT = path.join(PROJECT_ROOT, 'tools', 'update_scene_db.mjs');
const DB_FILE = path.join(SCENE_DIR, 'scene-db.json');
const THUMB_CACHE_DIR = path.join(PROJECT_ROOT, '.cache', 'scene-thumbs');
let sharpModPromise = null;

const MIME = new Map([
  ['.html', 'text/html; charset=utf-8'],
  ['.css', 'text/css; charset=utf-8'],
  ['.js', 'text/javascript; charset=utf-8'],
  ['.json', 'application/json; charset=utf-8'],
  ['.png', 'image/png'],
  ['.jpg', 'image/jpeg'],
  ['.jpeg', 'image/jpeg'],
  ['.webp', 'image/webp'],
  ['.gif', 'image/gif'],
  ['.svg', 'image/svg+xml; charset=utf-8'],
  ['.ico', 'image/x-icon'],
]);

function safeJoin(base, relPath) {
  const full = path.resolve(base, '.' + path.sep + relPath);
  const baseResolved = path.resolve(base);
  if (!full.startsWith(baseResolved + path.sep) && full !== baseResolved) {
    return null;
  }
  return full;
}

async function statOrNull(p) {
  try {
    return await fs.stat(p);
  } catch {
    return null;
  }
}

async function getSharpOrNull() {
  if (!sharpModPromise) {
    sharpModPromise = import('sharp')
      .then((m) => m.default || m)
      .catch(() => null);
  }
  return sharpModPromise;
}

function clampInt(v, min, max, fallback) {
  const n = Number.parseInt(String(v ?? ''), 10);
  if (Number.isNaN(n)) return fallback;
  return Math.max(min, Math.min(max, n));
}

function getCacheControlByExt(ext) {
  // HTML/索引：不缓存，避免改动看不到
  if (ext === '.html' || ext === '.json') return 'no-cache';
  // 代码：短缓存（刷新可更新）
  if (ext === '.js' || ext === '.css') return 'no-cache';
  // 图片：长缓存（避免每次打开都重新请求/闪烁）
  if (['.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg', '.ico'].includes(ext)) {
    return 'public, max-age=31536000, immutable';
  }
  return 'no-cache';
}

function toHttpDate(d) {
  return new Date(d).toUTCString();
}

async function sendFile(req, res, filePath, st) {
  const ext = path.extname(filePath).toLowerCase();
  res.setHeader('Content-Type', MIME.get(ext) || 'application/octet-stream');
  res.setHeader('Cache-Control', getCacheControlByExt(ext));
  if (st?.mtimeMs) res.setHeader('Last-Modified', toHttpDate(st.mtimeMs));

  // 简单 304：If-Modified-Since
  const ims = req.headers['if-modified-since'];
  if (ims && st?.mtimeMs) {
    const t = Date.parse(String(ims));
    if (!Number.isNaN(t) && st.mtimeMs <= t + 1000) {
      res.statusCode = 304;
      res.end();
      return;
    }
  }

  const buf = await fs.readFile(filePath);
  res.statusCode = 200;
  res.end(buf);
}

async function ensureThumb(srcPath, srcStat, width, quality) {
  const sharp = await getSharpOrNull();
  if (!sharp) return null;

  const keyBase = `${srcPath}|${srcStat.mtimeMs}|${srcStat.size}|w=${width}|q=${quality}|v=1`;
  const key = crypto.createHash('sha1').update(keyBase).digest('hex');
  const outPath = path.join(THUMB_CACHE_DIR, `${key}.webp`);
  const existed = await statOrNull(outPath);
  if (existed?.isFile()) return outPath;

  await fs.mkdir(THUMB_CACHE_DIR, { recursive: true });
  const tmpPath = `${outPath}.tmp-${process.pid}-${Date.now()}`;
  try {
    await sharp(srcPath, { failOn: 'none' })
      .rotate()
      .resize({ width, fit: 'inside', withoutEnlargement: true })
      .webp({ quality, effort: 4 })
      .toFile(tmpPath);
    await fs.rename(tmpPath, outPath);
  } catch {
    await fs.unlink(tmpPath).catch(() => {});
    return null;
  }
  return outPath;
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', 'http://localhost');
    let pathname = decodeURIComponent(url.pathname || '/');

    if (pathname === '/') {
      // 默认跳转到工作展示页
      res.statusCode = 302;
      res.setHeader('Location', '/w_work.html');
      res.end();
      return;
    }

    // allow clipboard/image usage
    res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
    res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');

    // Reindex API: 运行 update_scene_db 重建数据库
    if (pathname === '/api/reindex') {
      if ((req.method || 'GET').toUpperCase() !== 'POST') {
        res.statusCode = 405;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'method_not_allowed' }));
        return;
      }

      const host = String(req.headers.host || '');
      if (!host.startsWith('localhost') && !host.startsWith('127.0.0.1')) {
        res.statusCode = 403;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'forbidden' }));
        return;
      }

      const args = [DB_UPDATE_SCRIPT, '--src', SENCE_DIR, '--out', DB_FILE];
      const child = spawn(process.execPath, args, { cwd: PROJECT_ROOT, windowsHide: true });
      let out = '';
      let err = '';
      child.stdout.on('data', (d) => (out += String(d)));
      child.stderr.on('data', (d) => (err += String(d)));
      const code = await new Promise((resolve) => child.on('close', resolve));

      if (code === 0) {
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: true, stdout: out.trim() }));
        return;
      }

      res.statusCode = 500;
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.end(JSON.stringify({ ok: false, exitCode: code, stdout: out.trim(), stderr: err.trim() }));
      return;
    }

    // 数据库 API：批量更新 items 属性 (如 timeOfDay)
    // 使用 startsWith 避免末尾斜杠问题
    if (pathname.startsWith('/api/db/update-items')) {
      console.log('-> Handling update-items API');
      if ((req.method || 'GET').toUpperCase() !== 'POST') {
        res.statusCode = 405;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'method_not_allowed' }));
        return;
      }

      let body = '';
      for await (const chunk of req) body += chunk;
      let json = {};
      try {
        json = JSON.parse(body || '{}');
      } catch {
        res.statusCode = 400;
        res.end(JSON.stringify({ ok: false, error: 'invalid_json' }));
        return;
      }

      const updates = json.updates; // Array<{ abs: string, changes: object }>
      if (!Array.isArray(updates)) {
        res.statusCode = 400;
        res.end(JSON.stringify({ ok: false, error: 'updates_array_required' }));
        return;
      }

      try {
        const raw = await fs.readFile(DB_FILE, 'utf8');
        const db = JSON.parse(raw);
        if (!Array.isArray(db.items)) db.items = [];

        let changedCount = 0;
        const itemMap = new Map();
        db.items.forEach((it, i) => itemMap.set(it.abs, i));

        for (const up of updates) {
          const idx = itemMap.get(up.abs);
          if (idx !== undefined) {
            db.items[idx] = { ...db.items[idx], ...up.changes };
            changedCount++;
          }
        }

        if (changedCount > 0) {
          await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2), 'utf8');
          const outJs = DB_FILE.replace(/\.json$/i, '.data.js');
          await fs.writeFile(outJs, `// Auto-generated\nwindow.__SCENE_DB__ = ${JSON.stringify(db)};\n`, 'utf8');
        }

        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: true, changed: changedCount }));
      } catch (e) {
        res.statusCode = 500;
        res.end(JSON.stringify({ ok: false, error: 'db_write_failed', message: String(e) }));
      }
      return;
    }

    // 数据库 API：收藏 / 删除 / 恢复（修改 scene-db.json）
    const dbApiMatch = pathname.match(/^\/api\/db\/(toggle-fav|delete|restore)$/);
    if (dbApiMatch) {
      const action = dbApiMatch[1];
      if ((req.method || 'GET').toUpperCase() !== 'POST') {
        res.statusCode = 405;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'method_not_allowed' }));
        return;
      }

      const host = String(req.headers.host || '');
      if (!host.startsWith('localhost') && !host.startsWith('127.0.0.1')) {
        res.statusCode = 403;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'forbidden' }));
        return;
      }

      let body = '';
      for await (const chunk of req) body += chunk;
      let json = {};
      try {
        json = JSON.parse(body || '{}');
      } catch {
        res.statusCode = 400;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'invalid_json' }));
        return;
      }
      const abs = String(json.abs ?? '').trim();
      if (!abs) {
        res.statusCode = 400;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'abs_required' }));
        return;
      }

      try {
        const raw = await fs.readFile(DB_FILE, 'utf8');
        const db = JSON.parse(raw);
        if (!Array.isArray(db.favorites)) db.favorites = [];
        if (!Array.isArray(db.trash)) db.trash = [];

        if (action === 'toggle-fav') {
          const idx = db.favorites.indexOf(abs);
          if (idx >= 0) db.favorites.splice(idx, 1);
          else db.favorites.push(abs);
        } else if (action === 'delete') {
          if (!db.trash.includes(abs)) db.trash.push(abs);
        } else if (action === 'restore') {
          const idx = db.trash.indexOf(abs);
          if (idx >= 0) db.trash.splice(idx, 1);
        }

        await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2), 'utf8');
        // 同步更新 .data.js
        const outJs = DB_FILE.replace(/\.json$/i, '.data.js');
        await fs.writeFile(outJs, `// Auto-generated\nwindow.__SCENE_DB__ = ${JSON.stringify(db)};\n`, 'utf8');

        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: true, favorites: db.favorites, trash: db.trash }));
      } catch (e) {
        res.statusCode = 500;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({ ok: false, error: 'db_write_failed', message: String(e?.message || e) }));
      }
      return;
    }

    if (pathname.startsWith('/thumb/')) {
      const rel = pathname.slice('/thumb/'.length);
      const fp = safeJoin(SENCE_DIR, rel);
      if (!fp) {
        res.statusCode = 400;
        res.end('Bad path');
        return;
      }

      const srcStat = await statOrNull(fp);
      if (!srcStat || !srcStat.isFile()) {
        res.statusCode = 404;
        res.end('Not found');
        return;
      }

      const width = clampInt(url.searchParams.get('w'), 240, 1280, 640);
      const quality = clampInt(url.searchParams.get('q'), 50, 90, 72);
      const thumbPath = await ensureThumb(fp, srcStat, width, quality);
      if (thumbPath) {
        const st = await statOrNull(thumbPath);
        if (st?.isFile()) {
          await sendFile(req, res, thumbPath, st);
          return;
        }
      }
      // sharp 不可用或缩略图生成失败时，回退原图
      await sendFile(req, res, fp, srcStat);
      return;
    }

    if (pathname.startsWith('/sence/')) {
      const rel = pathname.slice('/sence/'.length);
      const fp = safeJoin(SENCE_DIR, rel);
      if (!fp) {
        res.statusCode = 400;
        res.end('Bad path');
        return;
      }
      const st = await statOrNull(fp);
      if (!st || !st.isFile()) {
        res.statusCode = 404;
        res.end('Not found');
        return;
      }
      await sendFile(req, res, fp, st);
      return;
    }

    // 静态文件：默认 story；发布时可切换为 dist（找不到时回退 story）
    const rel = pathname.replace(/^\//, '');
    const primary = safeJoin(STATIC_ROOT, rel);
    const fallback = safeJoin(STORY_DIR, rel);

    if (!primary && !fallback) {
      res.statusCode = 400;
      res.end('Bad path');
      return;
    }

    const primaryStat = primary ? await statOrNull(primary) : null;
    const fallbackStat = fallback ? await statOrNull(fallback) : null;
    const usePrimary = Boolean(primaryStat && primaryStat.isFile());
    const fp = usePrimary ? primary : fallback;
    const st = usePrimary ? primaryStat : fallbackStat;
    if (!fp || !st || !st.isFile()) {
      res.statusCode = 404;
      res.end('Not found');
      return;
    }
    
    await sendFile(req, res, fp, st);
  } catch (e) {
    res.statusCode = 500;
    res.end('Server error');
  }
});

server.listen(PORT, HOST, () => {
  console.log(`[scene-library] static root: ${STATIC_ROOT}`);
  console.log(`[scene-library] http://localhost:${PORT}/index.html`);
  console.log(`[scene-library] serving images: /sence/* -> ${SENCE_DIR}`);
});

