const path = require('node:path');

const { defineConfig } = require('vite');


const storyDir = path.resolve(__dirname, 'story');
const assetDir = path.resolve(__dirname, 'Asset');
const torchCharDir = path.resolve(__dirname, 'TorchCharLib');

const fs = require('node:fs');

function localFilesPlugin() {
  const MIME_MAP = {
    '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm',
    '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska',
    '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.webp': 'image/webp', '.gif': 'image/gif', '.bmp': 'image/bmp',
    '.tga': 'image/x-tga', '.tif': 'image/tiff', '.tiff': 'image/tiff',
    '.psd': 'image/vnd.adobe.photoshop', '.exr': 'image/x-exr',
    '.fbx': 'application/octet-stream', '.glb': 'model/gltf-binary', '.gltf': 'model/gltf+json',
  };

  return {
    name: 'local-files-server',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const driveMatch = req.url && req.url.match(/^\/([a-z])-drive\//);
        const isLocalFiles = req.url && req.url.startsWith('/local-files/');
        if (!driveMatch && !isLocalFiles) return next();

        let filePath;
        if (driveMatch) {
          const rest = req.url.replace(/^\/[a-z]-drive\//, '').split('?')[0];
          filePath = driveMatch[1].toUpperCase() + ':/' + decodeURIComponent(rest);
        } else {
          const relEncoded = req.url.replace('/local-files/', '').split('?')[0];
          filePath = decodeURIComponent(relEncoded);
        }

        if (!fs.existsSync(filePath)) {
          res.writeHead(404);
          res.end('Not found');
          return;
        }

        const ext = path.extname(filePath).toLowerCase();
        const mime = MIME_MAP[ext] || 'application/octet-stream';
        const stat = fs.statSync(filePath);
        const range = req.headers.range;

        if (range) {
          const parts = range.replace(/bytes=/, '').split('-');
          const start = parseInt(parts[0], 10);
          const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
          res.writeHead(206, {
            'Content-Range': `bytes ${start}-${end}/${stat.size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Content-Type': mime,
          });
          fs.createReadStream(filePath, { start, end }).pipe(res);
        } else {
          res.writeHead(200, {
            'Content-Type': mime,
            'Content-Length': stat.size,
            'Accept-Ranges': 'bytes',
          });
          fs.createReadStream(filePath).pipe(res);
        }
      });
    },
  };
}

// 统一 CORS 头，支持 file:// 和其他域的跨域请求
function setCorsHeaders(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Filename');
}

function seedanceDbPlugin(opts = {}) {
  const prefix = opts.prefix || 'seedance-db';
  const DB_PATH = opts.dbPath || path.resolve(__dirname, 'SeedanceStudio', 'seedance-db.json');
  const apiBase = `/api/${prefix}`;

  function readDb() {
    try {
      if (!fs.existsSync(DB_PATH)) return [];
      return JSON.parse(fs.readFileSync(DB_PATH, 'utf-8'));
    } catch { return []; }
  }

  function writeDb(data) {
    fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2), 'utf-8');
  }

  function parseBody(req) {
    return new Promise((resolve, reject) => {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => {
        try { resolve(JSON.parse(body)); } catch { resolve({}); }
      });
      req.on('error', reject);
    });
  }

  return {
    name: `${prefix}-server`,
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url || !req.url.startsWith(apiBase)) return next();

        setCorsHeaders(res);
        if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

        const urlPath = req.url.split('?')[0];
        res.setHeader('Content-Type', 'application/json');

        if (req.method === 'GET' && urlPath === apiBase) {
          const records = readDb();
          res.writeHead(200);
          res.end(JSON.stringify(records));
          return;
        }

        if (req.method === 'POST' && urlPath === apiBase) {
          const record = await parseBody(req);
          const records = readDb();
          records.unshift(record);
          writeDb(records);
          res.writeHead(201);
          res.end(JSON.stringify({ ok: true }));
          return;
        }

        const idMatch = urlPath.match(new RegExp(`^${apiBase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/(.+)$`));
        if (req.method === 'PATCH' && idMatch) {
          const id = decodeURIComponent(idMatch[1]);
          const updates = await parseBody(req);
          const records = readDb();
          const idx = records.findIndex(r => r.id === id);
          if (idx !== -1) {
            Object.assign(records[idx], updates);
            writeDb(records);
          }
          res.writeHead(200);
          res.end(JSON.stringify({ ok: true }));
          return;
        }

        if (req.method === 'DELETE' && idMatch) {
          const id = decodeURIComponent(idMatch[1]);
          let records = readDb();
          records = records.filter(r => r.id !== id);
          writeDb(records);
          res.writeHead(200);
          res.end(JSON.stringify({ ok: true }));
          return;
        }

        res.writeHead(404);
        res.end(JSON.stringify({ error: 'Not found' }));
      });
    },
  };
}

function seedanceVideoPlugin(opts = {}) {
  const prefix = opts.prefix || 'seedance';
  const VIDEOS_DIR = opts.videosDir || path.resolve(__dirname, 'SeedanceStudio', 'videos');
  const UPLOADS_DIR = opts.uploadsDir || path.resolve(__dirname, 'SeedanceStudio', 'uploads');
  const uploadsRoute = `/${prefix}-uploads`;
  const videosRoute = `/${prefix}-videos`;
  const uploadApi = `/api/${prefix}-upload`;
  const downloadApi = `/api/${prefix}-download`;
  const https = require('node:https');
  const http = require('node:http');

  if (!fs.existsSync(VIDEOS_DIR)) fs.mkdirSync(VIDEOS_DIR, { recursive: true });
  if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });

  function downloadFile(url) {
    return new Promise((resolve, reject) => {
      const client = url.startsWith('https') ? https : http;
      const doRequest = (targetUrl, redirects = 0) => {
        if (redirects > 5) return reject(new Error('Too many redirects'));
        client.get(targetUrl, { headers: { 'User-Agent': 'SeedanceStudio/1.0' } }, (resp) => {
          if (resp.statusCode >= 300 && resp.statusCode < 400 && resp.headers.location) {
            return doRequest(resp.headers.location, redirects + 1);
          }
          if (resp.statusCode !== 200) return reject(new Error(`HTTP ${resp.statusCode}`));
          const chunks = [];
          resp.on('data', c => chunks.push(c));
          resp.on('end', () => resolve(Buffer.concat(chunks)));
          resp.on('error', reject);
        }).on('error', reject);
      };
      doRequest(url);
    });
  }

  function parseBody(req) {
    return new Promise((resolve, reject) => {
      let body = '';
      req.on('data', chunk => { body += chunk; });
      req.on('end', () => { try { resolve(JSON.parse(body)); } catch { resolve({}); } });
      req.on('error', reject);
    });
  }

  return {
    name: `${prefix}-video-server`,
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        if (!req.url) return next();
        const urlPath = req.url.split('?')[0];

        const isMyRoute = urlPath.startsWith(`/api/${prefix}-`) || urlPath.startsWith(videosRoute + '/') || urlPath.startsWith(uploadsRoute + '/');
        if (isMyRoute) {
          setCorsHeaders(res);
          if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }
        }

        if (req.method === 'POST' && urlPath === uploadApi) {
          const chunks = [];
          req.on('data', c => chunks.push(c));
          req.on('end', () => {
            try {
              const buffer = Buffer.concat(chunks);
              const originalName = decodeURIComponent(req.headers['x-filename'] || 'upload');
              const ext = path.extname(originalName) || '';
              const safeName = Date.now() + '-' + Math.random().toString(36).slice(2, 8) + ext;
              const filePath = path.join(UPLOADS_DIR, safeName);
              fs.writeFileSync(filePath, buffer);
              res.writeHead(200, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ ok: true, files: [{ originalName, servedUrl: `${uploadsRoute}/${safeName}`, size: buffer.length }] }));
            } catch (err) {
              res.writeHead(500, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: err.message }));
            }
          });
          return;
        }

        const uploadMatch = urlPath.match(new RegExp(`^${uploadsRoute.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/(.+)$`));
        if (req.method === 'GET' && uploadMatch) {
          const filename = decodeURIComponent(uploadMatch[1]);
          const filePath = path.join(UPLOADS_DIR, filename);
          if (!fs.existsSync(filePath)) {
            res.writeHead(404);
            res.end('Not found');
            return;
          }
          const stat = fs.statSync(filePath);
          const extMap = { '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.webp': 'image/webp', '.mp4': 'video/mp4', '.webm': 'video/webm', '.mov': 'video/quicktime', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.ogg': 'audio/ogg', '.m4a': 'audio/mp4' };
          const ext = path.extname(filename).toLowerCase();
          const mime = extMap[ext] || 'application/octet-stream';

          res.writeHead(200, { 'Content-Type': mime, 'Content-Length': stat.size, 'Cache-Control': 'public, max-age=86400' });
          fs.createReadStream(filePath).pipe(res);
          return;
        }

        if (req.method === 'POST' && urlPath === downloadApi) {
          const { url: videoUrl, taskId } = await parseBody(req);
          res.setHeader('Content-Type', 'application/json');

          if (!videoUrl || !taskId) {
            res.writeHead(400);
            res.end(JSON.stringify({ error: '缺少 url 或 taskId' }));
            return;
          }

          const filename = `${taskId}.mp4`;
          const filePath = path.join(VIDEOS_DIR, filename);

          if (fs.existsSync(filePath)) {
            res.writeHead(200);
            res.end(JSON.stringify({ ok: true, localPath: `${videosRoute}/${filename}`, filename }));
            return;
          }

          try {
            const buffer = await downloadFile(videoUrl);
            fs.writeFileSync(filePath, buffer);
            res.writeHead(200);
            res.end(JSON.stringify({ ok: true, localPath: `${videosRoute}/${filename}`, filename, size: buffer.length }));
          } catch (err) {
            res.writeHead(500);
            res.end(JSON.stringify({ error: err.message }));
          }
          return;
        }

        const videoMatch = urlPath.match(new RegExp(`^${videosRoute.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}/(.+)$`));
        if (req.method === 'GET' && videoMatch) {
          const filename = decodeURIComponent(videoMatch[1]);
          const filePath = path.join(VIDEOS_DIR, filename);

          if (!fs.existsSync(filePath)) {
            res.writeHead(404);
            res.end('Not found');
            return;
          }

          const stat = fs.statSync(filePath);
          const range = req.headers.range;

          if (range) {
            const parts = range.replace(/bytes=/, '').split('-');
            const start = parseInt(parts[0], 10);
            const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
            res.writeHead(206, {
              'Content-Range': `bytes ${start}-${end}/${stat.size}`,
              'Accept-Ranges': 'bytes',
              'Content-Length': end - start + 1,
              'Content-Type': 'video/mp4',
            });
            fs.createReadStream(filePath, { start, end }).pipe(res);
          } else {
            res.writeHead(200, {
              'Content-Type': 'video/mp4',
              'Content-Length': stat.size,
              'Accept-Ranges': 'bytes',
            });
            fs.createReadStream(filePath).pipe(res);
          }
          return;
        }

        next();
      });
    },
  };
}

function localVideoPlugin() {
  const VIDEO_ROOT = 'Y:\\作品集合';
  const MIME = { '.mp4': 'video/mp4', '.mov': 'video/quicktime', '.webm': 'video/webm', '.avi': 'video/x-msvideo', '.mkv': 'video/x-matroska' };

  return {
    name: 'local-video-server',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (!req.url || !req.url.startsWith('/local-videos/')) return next();

        const relEncoded = req.url.replace('/local-videos/', '').split('?')[0];
        const rel = decodeURIComponent(relEncoded);
        const filePath = path.join(VIDEO_ROOT, rel);

        if (!fs.existsSync(filePath)) {
          res.writeHead(404);
          res.end('Not found');
          return;
        }

        const ext = path.extname(filePath).toLowerCase();
        const mime = MIME[ext] || 'application/octet-stream';
        const stat = fs.statSync(filePath);
        const range = req.headers.range;

        if (range) {
          const parts = range.replace(/bytes=/, '').split('-');
          const start = parseInt(parts[0], 10);
          const end = parts[1] ? parseInt(parts[1], 10) : stat.size - 1;
          res.writeHead(206, {
            'Content-Range': `bytes ${start}-${end}/${stat.size}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': end - start + 1,
            'Content-Type': mime,
          });
          fs.createReadStream(filePath, { start, end }).pipe(res);
        } else {
          res.writeHead(200, {
            'Content-Type': mime,
            'Content-Length': stat.size,
            'Accept-Ranges': 'bytes',
          });
          fs.createReadStream(filePath).pipe(res);
        }
      });
    },
  };
}

module.exports = defineConfig({
  server: {
    host: '0.0.0.0',
    port: 8088,
    cors: {
      origin: '*',
      methods: 'GET,POST,PATCH,DELETE,OPTIONS',
      allowedHeaders: ['Content-Type', 'Authorization', 'X-Filename'],
    },
  },
  plugins: [
    localFilesPlugin(),
    localVideoPlugin(),
    seedanceDbPlugin(),
    seedanceVideoPlugin(),
    seedanceDbPlugin({
      prefix: 'sd2-db',
      dbPath: path.resolve('Y:\\tmp\\root\\sd2', 'seedance-db.json'),
    }),
    seedanceVideoPlugin({
      prefix: 'sd2',
      videosDir: path.resolve('Y:\\tmp\\root\\sd2', 'videos'),
      uploadsDir: path.resolve('Y:\\tmp\\root\\sd2', 'uploads'),
    }),
  ],
  build: {
    outDir: path.resolve(__dirname, 'dist'),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        work_index:    path.resolve(__dirname, 'w_work.html'),
        portfolio:     path.resolve(__dirname, 'portfolio', 'index.html'),
        torch_char_lib: path.resolve(torchCharDir, 'index.html'),
      },
    },
  },
});
