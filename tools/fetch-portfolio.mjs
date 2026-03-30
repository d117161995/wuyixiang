/**
 * 飞书多维表格 → 本地 portfolio-db.json 抓取工具
 * 读取"影视作品集"表格全部记录，下载封面图和成片视频，生成 JSON 数据库
 *
 * 用法: node tools/fetch-portfolio.mjs [--skip-video] [--skip-cover]
 *   --skip-video  跳过视频下载（仅更新 JSON 和封面图）
 *   --skip-cover  跳过封面图下载
 */
import fs from 'node:fs/promises';
import { createWriteStream, existsSync, statSync } from 'node:fs';
import path from 'node:path';
import { pipeline } from 'node:stream/promises';
import { fileURLToPath } from 'node:url';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileAsync = promisify(execFile);

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'portfolio');
const COVERS_DIR = path.join(OUT_DIR, 'covers');
const VIDEOS_DIR = path.join(OUT_DIR, 'videos');
const DB_PATH = path.join(OUT_DIR, 'portfolio-db.json');
const DB_JS_PATH = path.join(OUT_DIR, 'portfolio-db.data.js');

const APP_ID = 'cli_a90ca9e6fa78dbcc';
const APP_SECRET = 'Y2zIAXZWWOfGot3LgeuTshNtS6I2WR78';
const APP_TOKEN = 'AwKnbJh4saEcnVsnAsYcbQPlnUc';
const TABLE_ID = 'tblsjmQUm9eE8IU8';

const FLAGS = {
  skipVideo: process.argv.includes('--skip-video'),
  skipCover: process.argv.includes('--skip-cover'),
};

// ─── Feishu Auth ───

let tenantToken = '';

async function getTenantToken() {
  const res = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: APP_ID, app_secret: APP_SECRET }),
  });
  const data = await res.json();
  if (data.code !== 0) throw new Error(`Auth failed: ${data.msg}`);
  tenantToken = data.tenant_access_token;
  console.log('[auth] tenant token obtained');
}

async function feishuGet(url) {
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${tenantToken}` },
  });
  return res.json();
}

async function feishuPost(url, body) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${tenantToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });
  return res.json();
}

// ─── Fetch All Records ───

async function fetchAllRecords() {
  const records = [];
  let pageToken = '';
  let page = 1;

  while (true) {
    console.log(`[fetch] page ${page}...`);
    const url = new URL(`https://open.feishu.cn/open-apis/bitable/v1/apps/${APP_TOKEN}/tables/${TABLE_ID}/records`);
    if (pageToken) url.searchParams.set('page_token', pageToken);
    url.searchParams.set('page_size', '100');

    const res = await fetch(url.toString(), {
      headers: { Authorization: `Bearer ${tenantToken}` },
    });
    const data = await res.json();
    if (data.code !== 0) throw new Error(`Fetch records failed: ${data.msg}`);

    const items = data.data?.items || [];
    records.push(...items);
    console.log(`[fetch] got ${items.length} records (total: ${records.length})`);

    if (!data.data?.has_more) break;
    pageToken = data.data.page_token;
    page++;
  }

  return records;
}

// ─── Download Helpers ───

function sanitizeFilename(name) {
  return name.replace(/[<>:"/\\|?*\x00-\x1f]/g, '_').replace(/\s+/g, '_');
}

async function downloadFile(fileToken, destPath, fileName, force = false) {
  if (!force && existsSync(destPath)) {
    console.log(`  [skip] ${fileName} (already exists)`);
    return true;
  }

  try {
    const tmpUrl = `https://open.feishu.cn/open-apis/drive/v1/medias/batch_get_tmp_download_url?file_tokens=${fileToken}`;
    const urlData = await feishuGet(tmpUrl);
    const downloadUrl = urlData?.data?.tmp_download_urls?.[0]?.tmp_download_url;
    if (!downloadUrl) {
      console.log(`  [warn] no download URL for ${fileName}`);
      return false;
    }

    console.log(`  [download] ${fileName}...`);
    const res = await fetch(downloadUrl);
    if (!res.ok) {
      console.log(`  [error] HTTP ${res.status} for ${fileName}`);
      return false;
    }

    await pipeline(res.body, createWriteStream(destPath));
    console.log(`  [done] ${fileName}`);
    return true;
  } catch (err) {
    console.log(`  [error] ${fileName}: ${err.message}`);
    return false;
  }
}

// ─── Parse Record ───

function extractText(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  if (Array.isArray(field)) {
    return field.map(item => {
      if (typeof item === 'string') return item;
      if (item?.text) return item.text;
      return '';
    }).filter(Boolean).join('');
  }
  if (field?.text) return field.text;
  return '';
}

function extractMultiSelect(field) {
  if (!field) return [];
  if (Array.isArray(field)) return field.filter(v => typeof v === 'string');
  return [];
}

function extractUrl(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  if (field?.link) return field.link;
  if (field?.text) return field.text;
  return '';
}

function extractAttachments(field) {
  if (!field || !Array.isArray(field)) return [];
  return field.map(att => ({
    fileToken: att.file_token || '',
    name: att.name || '',
    size: att.size || 0,
    type: att.type || '',
  }));
}

function parseRecord(record) {
  const f = record.fields || {};
  return {
    recordId: record.record_id,
    project: extractText(f['项目']),
    game: extractText(f['游戏']),
    categories: extractMultiSelect(f['类别']),
    difficulty: extractMultiSelect(f['难度等级']),
    production: extractMultiSelect(f['生产方式']),
    participation: extractMultiSelect(f['参与环节']),
    quarter: extractText(f['交付季度']),
    deliveryDate: extractText(f['交付时间']),
    cycle: extractText(f['制作周期']),
    duration: extractText(f['视频时长']),
    productionStart: f['制作启动'] || null,
    productionEnd: f['制作结束'] || null,
    coverAttachments: extractAttachments(f['封面图']),
    videoAttachments: extractAttachments(f['成片']),
    bilibiliUrl: extractUrl(f['国内视频链接']),
    youtubeUrl: extractUrl(f['海外视频链接']),
    assetSheet: extractUrl(f['时间资产表']),
    parentRecordId: f['父记录']?.[0] || f['父记录'] || '',
    cover: '',
    video: '',
  };
}

// ─── Game Name Merge Map ───
const GAME_MERGE = {
  '麦芬-SAGA': '出发吧麦芬-SAGA',
};

function normalizeGameName(name) {
  return GAME_MERGE[name] || name;
}

// ─── Build Tree Structure ───

function buildGameTree(records) {
  for (const r of records) {
    if (r.game) r.game = normalizeGameName(r.game);
  }

  const parentRecords = [];
  const childRecords = [];

  for (const r of records) {
    if (!r.game && !r.categories.length && !r.difficulty.length) {
      parentRecords.push(r);
    } else {
      childRecords.push(r);
    }
  }

  const games = [];
  const gameMap = new Map();

  for (const p of parentRecords) {
    const rawName = p.project;
    const mergedName = normalizeGameName(rawName);
    const existing = games.find(g => g.name === mergedName);
    if (existing) {
      if (!existing.cover && p.cover) existing.cover = p.cover;
      gameMap.set(p.recordId, existing);
      continue;
    }
    const game = {
      name: mergedName,
      cover: p.cover,
      recordId: p.recordId,
      projects: [],
    };
    games.push(game);
    gameMap.set(p.recordId, game);
  }

  for (const c of childRecords) {
    const gameName = c.game;
    let game = games.find(g => g.name === gameName);
    if (!game) {
      game = { name: gameName || '未分类', cover: '', recordId: '', projects: [] };
      games.push(game);
      if (gameName) gameMap.set(gameName, game);
    }
    game.projects.push(c);
  }

  const KNOWN_GAMES = new Set([
    '火炬之光-TLI',
    '出发吧麦芬-SAGA',
    '香肠派对-SSG',
    '心动小镇-XDT',
    '伊瑟-ETH',
    'RO',
    '仙境传说-RO',
  ]);

  for (const g of games) {
    if (g.name === 'RO') g.name = '仙境传说-RO';
    for (const p of g.projects) {
      if (p.game === 'RO') p.game = '仙境传说-RO';
      p.production = (p.production || []).map(v => v === '实录' ? '游戏实录' : v === '离线' ? '传统离线' : v);
    }
    if (!g.name || !KNOWN_GAMES.has(g.name)) g.name = '其他';
  }

  const merged = [];
  for (const g of games) {
    if (g.projects.length === 0) continue;
    const existing = merged.find(m => m.name === g.name);
    if (existing) {
      existing.projects.push(...g.projects);
      if (!existing.cover && g.cover) existing.cover = g.cover;
    } else {
      merged.push(g);
    }
  }

  const GAME_ORDER = [
    '火炬之光-TLI',
    '心动小镇-XDT',
    '伊瑟-ETH',
    '香肠派对-SSG',
    '出发吧麦芬-SAGA',
    '仙境传说-RO',
    '其他',
  ];
  merged.sort((a, b) => {
    const ia = GAME_ORDER.indexOf(a.name);
    const ib = GAME_ORDER.indexOf(b.name);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });
  return merged;
}

// ─── Match Local Videos from Y:\作品集合 ───

const LOCAL_VIDEO_ROOT = 'Y:\\作品集合';
const VIDEO_EXTS = new Set(['.mp4', '.mov', '.avi', '.mkv', '.webm']);

function normalize(s) {
  return s.replace(/[\s_\-]+/g, '').toLowerCase();
}

const VIDEO_NAME_MAP = {
  '香肠2026春节': '香肠2026新年cg',
  '香肠2025八周年': '香肠八周年cg',
  '香肠ss21遗迹探险01': '香肠ss21遗迹探险ep01',
  '香肠ss21遗迹探险02': '香肠ss21遗迹探险ep02',
  '香肠ss21遗迹探险03': '香肠ss21遗迹探险ep03',
  '香肠遗迹探险动画01': '香肠ss21遗迹探险ep01',
  '香肠遗迹探险动画02': '香肠ss21遗迹探险ep02',
  '香肠遗迹探险动画03': '香肠ss21遗迹探险ep03',
  '香肠黄油小熊联动': '香肠黄油小熊联名pv',
  '香肠奶龙联动': '香肠奶龙联名',
  '香肠超时空赛季01': '香肠超时空赛季动画01',
  '香肠超时空赛季02': '香肠超时空赛季动画02',
  '香肠超时空赛季03': '香肠超时空赛季动画03',
  '香肠2022五周年': '香肠五周年',
  '香肠2023情人节': '香肠情人节宣传',
  '香肠2023春节': '香肠2023除夕夜倒计时',
  '香肠2021四周年': '香肠2021年四周年',
  '香肠2021春节': '香肠2021年新年cg',
  '香肠2021跨年双旦': '香肠双旦cg',
  '香肠航海王赛季玩法': '香肠航海王引擎动画',
  '香肠军武赛季玩法': '香肠ss18军武赛季玩法',
  '麦芬香格里拉联动预告': '麦芬香格里拉联动15s',
  '麦芬eva联动预告': '麦芬eva联动（30s）',
  '小镇泡面番·露营食记ep01': '小镇泡面番ep01',
  '小镇泡面番·露营食记ep02': '小镇泡面番ep02',
  '小镇泡面番·露营食记ep03': '小镇泡面番ep03',
  '小镇动物新邻季bp': '小镇动物季bp',
  '小镇动物新邻季玩法pv': '小镇动物季（玩法片）pv',
  '小镇动物新邻季开幕式timeline': '小镇动物季开幕式timeline',
  '小镇动物新邻季闭幕式timeline': '小镇动物季闭幕式timeline',
  '小镇新春季bp': '小镇新春bp',
  '小镇新春季玩法pv': '小镇新春（玩法片）pv',
  '小镇新春季卡池pv': '小镇新春（大卡池）pv',
  '小镇新春季年夜饭timeline': '小镇新春年夜饭timeline',
  '小镇沙滩乐园季bp': '小镇沙滩潮流季bp',
  '小镇沙滩乐园季玩法pv': '小镇沙滩潮流季pv',
  '小镇奇灵夜季bp': '小镇万圣节bp',
  '伊瑟琳提尔（女生版)': '伊瑟琳提尔（女主)',
  '伊瑟琳提尔（男生版）': '伊瑟琳提尔（男主）',
  '伊瑟坠楼(女生版）': '伊瑟坠楼(女主)',
  '伊瑟坠楼(男生版）': '伊瑟坠楼(男主)',
};

async function getVideoDuration(filePath) {
  try {
    const { stdout } = await execFileAsync('ffprobe', [
      '-v', 'quiet',
      '-print_format', 'json',
      '-show_format',
      filePath,
    ], { timeout: 15000 });
    const info = JSON.parse(stdout);
    const secs = parseFloat(info.format?.duration);
    if (!secs || isNaN(secs)) return '';
    const m = Math.floor(secs / 60);
    const s = Math.round(secs % 60);
    if (m > 0) return `${m}分${s.toString().padStart(2, '0')}秒`;
    return `${Math.round(secs)}秒`;
  } catch {
    return '';
  }
}

async function matchLocalVideos(games) {
  let totalMatched = 0;
  let totalUnmatched = 0;

  try {
    await fs.access(LOCAL_VIDEO_ROOT);
  } catch {
    console.log('\n[local-video] Y:\\作品集合 not accessible, skipping');
    return { totalMatched: 0, totalUnmatched: 0 };
  }

  console.log('\n--- Scanning local videos (Y:\\作品集合) ---');

  const topDirs = await fs.readdir(LOCAL_VIDEO_ROOT, { withFileTypes: true });
  const videoIndex = new Map();

  const EXT_PRIORITY = ['.mp4', '.webm', '.mov', '.avi', '.mkv'];

  for (const dir of topDirs) {
    if (!dir.isDirectory()) continue;
    const dirPath = path.join(LOCAL_VIDEO_ROOT, dir.name);
    const files = await fs.readdir(dirPath);
    for (const file of files) {
      const ext = path.extname(file).toLowerCase();
      if (!VIDEO_EXTS.has(ext)) continue;
      const stem = path.basename(file, ext);
      const fullPath = path.join(dirPath, file);
      const key = normalize(stem);
      const existing = videoIndex.get(key);
      if (existing) {
        const curPri = EXT_PRIORITY.indexOf(ext);
        const oldExt = path.extname(existing).toLowerCase();
        const oldPri = EXT_PRIORITY.indexOf(oldExt);
        if (curPri >= 0 && (oldPri < 0 || curPri < oldPri)) {
          videoIndex.set(key, fullPath);
        }
      } else {
        videoIndex.set(key, fullPath);
      }
    }
  }

  // Also scan "其它" folder
  console.log(`  [index] ${videoIndex.size} local video files indexed`);

  for (const game of games) {
    for (const project of game.projects) {
      const projName = project.project || '';
      const key = normalize(projName);

      let matched = videoIndex.get(key);

      // Fallback: try manual name mapping
      if (!matched && VIDEO_NAME_MAP[key]) {
        matched = videoIndex.get(VIDEO_NAME_MAP[key]);
      }

      // Fallback: try partial matching
      if (!matched) {
        for (const [k, v] of videoIndex) {
          if (k.includes(key) || key.includes(k)) {
            matched = v;
            break;
          }
        }
      }

      if (matched) {
        const rel = path.relative(LOCAL_VIDEO_ROOT, matched).split(path.sep).map(encodeURIComponent).join('/');
        project.localVideo = `/local-videos/${rel}`;
        project._localPath = matched;
        totalMatched++;
      }
    }
  }

  totalUnmatched = games.reduce((s, g) => s + g.projects.filter(p => !p.localVideo).length, 0);
  console.log(`  [match] ${totalMatched} matched, ${totalUnmatched} unmatched`);

  return { totalMatched, totalUnmatched };

  console.log('\n--- Reading video durations (ffprobe) ---');
  let durCount = 0;
  for (const game of games) {
    for (const project of game.projects) {
      if (!project._localPath) continue;
      const dur = await getVideoDuration(project._localPath);
      if (dur) {
        project.duration = dur;
        durCount++;
      }
      delete project._localPath;
    }
  }
  console.log(`  [duration] ${durCount} durations updated from actual video files`);
}

async function main() {
  console.log('=== 影视作品集数据抓取工具 ===\n');

  await fs.mkdir(COVERS_DIR, { recursive: true });
  await fs.mkdir(VIDEOS_DIR, { recursive: true });

  await getTenantToken();
  const rawRecords = await fetchAllRecords();
  const records = rawRecords.map(parseRecord);

  console.log(`\n[process] ${records.length} records parsed`);

  const newCovers = [];
  const updatedCovers = [];

  // Load previous cover tokens for change detection
  let prevCoverTokens = {};
  try {
    const prevDb = JSON.parse(await fs.readFile(DB_PATH, 'utf8'));
    prevCoverTokens = prevDb._coverTokens || {};
  } catch {}
  const curCoverTokens = {};

  // Download covers
  if (!FLAGS.skipCover) {
    console.log('\n--- Downloading covers ---');
    for (const r of records) {
      for (const att of r.coverAttachments) {
        const ext = path.extname(att.name) || '.png';
        const safeName = sanitizeFilename(r.project || r.recordId) + ext;
        const destPath = path.join(COVERS_DIR, safeName);
        const prevToken = prevCoverTokens[safeName];
        const tokenChanged = prevToken && prevToken !== att.fileToken;
        const localExists = existsSync(destPath);
        const isNew = !localExists;
        let sizeChanged = false;
        if (localExists && att.size > 0) {
          try {
            const localSize = statSync(destPath).size;
            if (localSize !== att.size) {
              sizeChanged = true;
            }
          } catch {}
        }
        const force = tokenChanged || sizeChanged;
        if (tokenChanged) console.log(`  [update] ${safeName} (token changed on Feishu)`);
        if (sizeChanged) console.log(`  [update] ${safeName} (size changed: local=${statSync(destPath).size} vs feishu=${att.size})`);
        const ok = await downloadFile(att.fileToken, destPath, safeName, force);
        if (ok) {
          r.cover = `covers/${safeName}`;
          curCoverTokens[safeName] = att.fileToken;
          if (isNew) newCovers.push(r.project || safeName);
          else if (tokenChanged || sizeChanged) updatedCovers.push(r.project || safeName);
        }
      }
    }
  } else {
    console.log('\n[skip] cover download');
    for (const r of records) {
      for (const att of r.coverAttachments) {
        const ext = path.extname(att.name) || '.png';
        const safeName = sanitizeFilename(r.project || r.recordId) + ext;
        if (existsSync(path.join(COVERS_DIR, safeName))) {
          r.cover = `covers/${safeName}`;
        }
        curCoverTokens[safeName] = att.fileToken;
      }
    }
  }

  // Download videos
  if (!FLAGS.skipVideo) {
    console.log('\n--- Downloading videos ---');
    for (const r of records) {
      for (const att of r.videoAttachments) {
        const ext = path.extname(att.name) || '.mp4';
        const safeName = sanitizeFilename(r.project || r.recordId) + ext;
        const destPath = path.join(VIDEOS_DIR, safeName);
        const ok = await downloadFile(att.fileToken, destPath, safeName);
        if (ok) r.video = `videos/${safeName}`;
      }
    }
  } else {
    console.log('\n[skip] video download');
    for (const r of records) {
      for (const att of r.videoAttachments) {
        const ext = path.extname(att.name) || '.mp4';
        const safeName = sanitizeFilename(r.project || r.recordId) + ext;
        if (existsSync(path.join(VIDEOS_DIR, safeName))) {
          r.video = `videos/${safeName}`;
        }
      }
    }
  }

  // Build game tree
  const games = buildGameTree(records);

  // Scan local video directory Y:\作品集合
  const videoStats = await matchLocalVideos(games) || { totalMatched: 0, totalUnmatched: 0 };

  // Compute stats
  const allProjects = games.flatMap(g => g.projects);
  const CATEGORY_ORDER = ['启宣CG', '赛季版本', '剧情动画', '过场动画', '开场动画', '联动动画', '玩法动画', '活动宣传'];
  const PRODUCTION_ORDER = ['传统离线', '引擎UE', '引擎Unity', '游戏实录', '二维手绘', '半自动AI', '全自动AI'];
  const rawCategories = [...new Set(allProjects.flatMap(p => p.categories))];
  const allCategories = [...CATEGORY_ORDER.filter(c => rawCategories.includes(c)), ...rawCategories.filter(c => !CATEGORY_ORDER.includes(c))];
  const allDifficulties = [...new Set(allProjects.flatMap(p => p.difficulty))].sort();
  const rawProductions = [...new Set(allProjects.flatMap(p => p.production))];
  const allProductions = [...PRODUCTION_ORDER.filter(p => rawProductions.includes(p)), ...rawProductions.filter(p => !PRODUCTION_ORDER.includes(p))];
  const allQuarters = [...new Set(allProjects.map(p => p.quarter).filter(Boolean))].sort();

  // Load previous DB for diff
  let prevDb = null;
  let prevLogs = [];
  try {
    prevDb = JSON.parse(await fs.readFile(DB_PATH, 'utf8'));
    prevLogs = prevDb.updateLogs || [];
  } catch {}

  // Diff: compare with previous data to find concrete changes
  const diffDetails = [];
  const prevProjects = new Map();
  if (prevDb && prevDb.games) {
    for (const g of prevDb.games) {
      for (const p of g.projects) {
        prevProjects.set(p.recordId, { ...p, _game: g.name });
      }
    }
  }
  const curProjects = new Map();
  for (const g of games) {
    for (const p of g.projects) {
      curProjects.set(p.recordId, { ...p, _game: g.name });
    }
  }

  // New projects
  const addedProjects = [];
  for (const [id, p] of curProjects) {
    if (!prevProjects.has(id)) {
      addedProjects.push({ name: p.project, game: p._game });
    }
  }
  if (addedProjects.length) {
    diffDetails.push({ type: 'added', label: '新增项目', items: addedProjects.map(p => `${p.game} - ${p.name}`) });
  }

  // Removed projects
  const removedProjects = [];
  for (const [id, p] of prevProjects) {
    if (!curProjects.has(id)) {
      removedProjects.push({ name: p.project, game: p._game });
    }
  }
  if (removedProjects.length) {
    diffDetails.push({ type: 'removed', label: '移除项目', items: removedProjects.map(p => `${p.game} - ${p.name}`) });
  }

  // New covers
  if (newCovers.length) {
    diffDetails.push({ type: 'cover', label: '新增封面', items: newCovers });
  }

  // Updated covers (file changed on Feishu)
  if (updatedCovers.length) {
    diffDetails.push({ type: 'cover', label: '更新封面', items: updatedCovers });
  }

  // Field changes on existing projects
  const COMPARE_FIELDS = ['project', 'categories', 'difficulty', 'production', 'quarter', 'deliveryDate', 'cycle', 'duration', 'bilibiliUrl', 'youtubeUrl'];
  const updatedProjects = [];
  for (const [id, cur] of curProjects) {
    const prev = prevProjects.get(id);
    if (!prev) continue;
    const changes = [];
    for (const f of COMPARE_FIELDS) {
      const cv = JSON.stringify(cur[f] || '');
      const pv = JSON.stringify(prev[f] || '');
      if (cv !== pv) changes.push(f);
    }
    if (changes.length) {
      updatedProjects.push({ name: cur.project, game: cur._game, fields: changes });
    }
  }
  if (updatedProjects.length) {
    diffDetails.push({ type: 'updated', label: '字段变更', items: updatedProjects.map(p => `${p.game} - ${p.name}（${p.fields.join(', ')}）`) });
  }

  // Video match changes
  const videoMatchTotal = videoStats.totalMatched + videoStats.totalUnmatched;

  // Build update log entry
  const updateEntry = {
    time: new Date().toISOString(),
    totalRecords: records.length,
    projectCount: allProjects.length,
    gameCount: games.length,
    newCovers: newCovers.length,
    newCoverNames: newCovers,
    videoMatched: videoStats.totalMatched,
    videoTotal: videoMatchTotal,
    videoUnmatched: videoStats.totalUnmatched,
    changes: diffDetails,
  };

  if (diffDetails.length === 0) {
    updateEntry.changes = [{ type: 'none', label: '无变更', items: ['数据与上次一致'] }];
  }

  const updateLogs = [updateEntry, ...prevLogs].slice(0, 20);

  const db = {
    lastUpdated: new Date().toISOString(),
    total: records.length,
    projectCount: allProjects.length,
    stats: {
      categories: allCategories,
      difficulties: allDifficulties,
      productions: allProductions,
      quarters: allQuarters,
      gameCount: games.length,
    },
    updateLogs,
    _coverTokens: curCoverTokens,
    games,
  };

  // Remove attachment raw data from output to keep JSON clean
  for (const g of db.games) {
    for (const p of g.projects) {
      delete p.coverAttachments;
      delete p.videoAttachments;
      delete p.parentRecordId;
    }
  }

  await fs.writeFile(DB_PATH, JSON.stringify(db, null, 2), 'utf8');
  const jsContent = `// Auto-generated by fetch-portfolio.mjs\nwindow.__PORTFOLIO_DB__ = ${JSON.stringify(db)};\n`;
  await fs.writeFile(DB_JS_PATH, jsContent, 'utf8');

  console.log(`\n=== Done ===`);
  console.log(`Games: ${games.length}`);
  console.log(`Projects: ${allProjects.length}`);
  console.log(`Total records: ${records.length}`);
  console.log(`Output: ${DB_PATH}`);
}

main().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
