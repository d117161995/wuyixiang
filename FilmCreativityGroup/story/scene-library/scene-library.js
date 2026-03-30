const DB_URL = './scene-db.json';
const API_BASE = '';

const qs = (s, el = document) => el.querySelector(s);
const qsa = (s, el = document) => Array.from(el.querySelectorAll(s));

const state = {
  data: null,
  category: '全部',
  timeFilter: '全部', // '全部' | '白天' | '黄昏' | '晚上' | '未标记'
  visibleItems: [],
  warmedThumbs: new Set(),
  thumbWarmQueue: [],
  thumbWarmRunning: false,
};

const LS_KEY = 'sceneLibraryState_v2'; // upgrade key
const LS_SCROLL_KEY = 'sceneLibraryScroll_v1';
const LS_FAV_KEY = 'sceneLibraryFav_v1';
const LS_TRASH_KEY = 'sceneLibraryTrash_v1';

function loadLocalFavorites() {
  try {
    const raw = localStorage.getItem(LS_FAV_KEY);
    if (raw) {
      const arr = JSON.parse(raw);
      return new Set(Array.isArray(arr) ? arr : []);
    }
  } catch { /* ignore */ }
  return new Set();
}

function saveLocalFavorites(set) {
  try {
    localStorage.setItem(LS_FAV_KEY, JSON.stringify([...set]));
  } catch { /* ignore */ }
}

function loadLocalTrash() {
  try {
    const raw = localStorage.getItem(LS_TRASH_KEY);
    if (raw) {
      const arr = JSON.parse(raw);
      return new Set(Array.isArray(arr) ? arr : []);
    }
  } catch { /* ignore */ }
  return new Set();
}

function saveLocalTrash(set) {
  try {
    localStorage.setItem(LS_TRASH_KEY, JSON.stringify([...set]));
  } catch { /* ignore */ }
}

function getFavoritesSet() {
  if (isUsingServer() && state.data) {
    const fav = state.data.favorites;
    return new Set(Array.isArray(fav) ? fav : []);
  }
  return loadLocalFavorites();
}

function getTrashSet() {
  if (isUsingServer() && state.data) {
    const tr = state.data.trash;
    return new Set(Array.isArray(tr) ? tr : []);
  }
  return loadLocalTrash();
}

function isUsingServer() {
  return window.location.protocol !== 'file:';
}

async function apiToggleFav(abs) {
  if (!isUsingServer()) return null;
  try {
    const res = await fetch(`${API_BASE}/api/db/toggle-fav`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abs }),
    });
    const json = await res.json();
    if (json.ok && state.data) {
      state.data.favorites = json.favorites ?? state.data.favorites;
    }
    return json;
  } catch (e) {
    return { ok: false, error: String(e?.message || e) };
  }
}

async function apiDelete(abs) {
  if (!isUsingServer()) return null;
  try {
    const res = await fetch(`${API_BASE}/api/db/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abs }),
    });
    const json = await res.json();
    if (json.ok && state.data) {
      state.data.trash = json.trash ?? state.data.trash;
    }
    return json;
  } catch (e) {
    return { ok: false, error: String(e?.message || e) };
  }
}

async function apiRestore(abs) {
  if (!isUsingServer()) return null;
  try {
    const res = await fetch(`${API_BASE}/api/db/restore`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ abs }),
    });
    const json = await res.json();
    if (json.ok && state.data) {
      state.data.trash = json.trash ?? state.data.trash;
    }
    return json;
  } catch (e) {
    return { ok: false, error: String(e?.message || e) };
  }
}

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function pathToFileUrl(pathStr) {
  const p = String(pathStr || '').trim();
  if (!p) return '';
  const normalized = p.replaceAll('\\', '/');

  // Mac/Unix 绝对路径：不编码，Safari file:// 对 SMB 挂载要求原始 UTF-8 路径
  if (normalized.startsWith('/')) {
    return 'file://' + normalized;
  }

  // Windows 路径：编码特殊字符
  const segs = normalized.split('/').filter(Boolean);
  const encoded = segs
    .map((seg, i) => (i === 0 && /:$/.test(seg) ? seg : encodeURIComponent(seg)))
    .join('/');
  return `file:///${encoded}`;
}

function absPathToFileUrlCandidates(p) {
  try {
    const absRaw = String(p || '').trim();
    if (!absRaw) return [];

    // 仅在 file: 协议下启用 Mac 路径修正
    if (window.location.protocol !== 'file:') {
       return [pathToFileUrl(absRaw)].filter(Boolean);
    }

    const isMacDesktop =
      /Macintosh|Mac OS X/i.test(navigator.userAgent) && !/iPhone|iPad|iPod/i.test(navigator.userAgent);
    const norm = absRaw.replaceAll('\\', '/');

    if (!isMacDesktop) {
      return [pathToFileUrl(norm)].filter(Boolean);
    }

    const candidates = [];
    const pushCandidate = (pathStr) => {
      const u = pathToFileUrl(pathStr);
      if (u && !candidates.includes(u)) candidates.push(u);
    };

    const mDrive = norm.match(/^([a-zA-Z]):\/(.*)$/);
    const mUnc = norm.match(/^\/\/([^/]+)\/([^/]+)\/(.*)$/);

    if (mDrive) {
      const drive = mDrive[1].toLowerCase();
      const rest = mDrive[2] || '';

      // 兼容两种常见挂载：
      // 1) /Volumes/<host>/<rest>    (你当前 Asset 路径这种)
      // 2) /Volumes/<host>/y/<rest>  (按 share 挂载)
      if (drive === 'y') {
        pushCandidate(`/Volumes/172.27.109.10/${rest}`);
        pushCandidate(`/Volumes/172.27.109.10/y/${rest}`);
      }
      pushCandidate(`/Volumes/${drive.toUpperCase()}/${rest}`);
      pushCandidate(norm);
      return candidates;
    }

    if (mUnc) {
      const host = mUnc[1];
      const share = mUnc[2];
      const rest = mUnc[3] || '';
      pushCandidate(`/Volumes/${host}/${rest}`);
      pushCandidate(`/Volumes/${host}/${share}/${rest}`);
      pushCandidate(norm);
      return candidates;
    }

    pushCandidate(norm);
    return candidates;
  } catch {
    return [];
  }
}

function absPathToFileUrl(p) {
  return absPathToFileUrlCandidates(p)[0] || '';
}

function toAbsoluteUrl(u) {
  if (!u) return '';
  // /sence/... -> http://localhost:5173/sence/...
  if (u.startsWith('/')) return `${window.location.origin}${u}`;
  return u;
}

function toThumbUrl(u, width = 640, quality = 72) {
  if (!u) return '';
  // 相对地址：/sence/... -> /thumb/...
  if (u.startsWith('/sence/')) {
    const rel = u.slice('/sence/'.length);
    return `/thumb/${rel}?w=${width}&q=${quality}`;
  }
  // 绝对地址：http://x/sence/... -> http://x/thumb/...
  if (/^https?:\/\//i.test(u)) {
    try {
      const p = new URL(u);
      if (p.pathname.startsWith('/sence/')) {
        p.pathname = `/thumb/${p.pathname.slice('/sence/'.length)}`;
        p.searchParams.set('w', String(width));
        p.searchParams.set('q', String(quality));
        return p.toString();
      }
    } catch {
      // ignore
    }
  }
  return u;
}

function enqueueThumbWarmup(items) {
  if (!isUsingServer() || !Array.isArray(items) || !items.length) return;
  const MAX_CANDIDATES = 64;
  const urls = items
    .slice(0, MAX_CANDIDATES)
    .map((it) => toThumbUrl(it.url, 480, 70))
    .filter(Boolean);

  for (const u of urls) {
    if (state.warmedThumbs.has(u)) continue;
    state.warmedThumbs.add(u);
    state.thumbWarmQueue.push(u);
  }
  startThumbWarmWorkers();
}

function startThumbWarmWorkers() {
  if (state.thumbWarmRunning) return;
  if (!state.thumbWarmQueue.length) return;
  state.thumbWarmRunning = true;

  const CONCURRENCY = 8;
  let cursor = 0;
  const queue = state.thumbWarmQueue.slice();
  state.thumbWarmQueue.length = 0;

  const worker = async () => {
    while (cursor < queue.length) {
      const idx = cursor++;
      const url = queue[idx];
      try {
        await fetch(url, { cache: 'force-cache' });
      } catch {
        // ignore preload errors
      }
    }
  };

  Promise.allSettled(Array.from({ length: Math.min(CONCURRENCY, queue.length) }, () => worker()))
    .finally(() => {
      state.thumbWarmRunning = false;
      if (state.thumbWarmQueue.length) {
        startThumbWarmWorkers();
      }
    });
}

function guessMimeByName(name) {
  const lower = String(name || '').toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.gif')) return 'image/gif';
  return 'application/octet-stream';
}

function setUrlParams() {
  const url = new URL(window.location.href);
  if (state.category && state.category !== '全部') url.searchParams.set('cat', state.category);
  else url.searchParams.delete('cat');

  if (state.timeFilter && state.timeFilter !== '全部') url.searchParams.set('time', state.timeFilter);
  else url.searchParams.delete('time');

  history.replaceState(null, '', url.toString());

  try {
    localStorage.setItem(LS_KEY, JSON.stringify({ cat: state.category, time: state.timeFilter }));
  } catch {
    // ignore
  }
}

function readUrlParams() {
  const url = new URL(window.location.href);
  const cat = url.searchParams.get('cat');
  const time = url.searchParams.get('time');

  if (cat !== null || time !== null) {
    state.category = cat || '全部';
    state.timeFilter = time || '全部';
    return;
  }

  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const obj = JSON.parse(raw);
      state.category = obj?.cat || '全部';
      state.timeFilter = obj?.time || '全部';
      return;
    }
  } catch {
    // ignore
  }

  state.category = '全部';
  state.timeFilter = '全部';
}

function filterItems() {
  const items = state.data?.items || [];
  const trashSet = getTrashSet();
  const favoritesSet = getFavoritesSet();

  // 1. 回收站模式：只看回收站，忽略其他筛选
  if (state.category === '回收站') {
    return items.filter((it) => trashSet.has(it.abs));
  }

  // 2. 正常模式：过滤掉回收站的
  let filtered = items.filter((it) => !trashSet.has(it.abs));

  // 3. 收藏夹筛选
  if (state.category === '收藏夹') {
    filtered = filtered.filter((it) => favoritesSet.has(it.abs));
  }
  // 4. 分类筛选
  else if (state.category !== '全部') {
    filtered = filtered.filter((it) => it.category === state.category);
  }

  // 5. 时间筛选
  if (state.timeFilter === '未标记') {
    filtered = filtered.filter((it) => !it.timeOfDay);
  } else if (state.timeFilter === '白天') {
    filtered = filtered.filter((it) => it.timeOfDay === 'day');
  } else if (state.timeFilter === '黄昏') {
    filtered = filtered.filter((it) => it.timeOfDay === 'dusk');
  } else if (state.timeFilter === '晚上') {
    filtered = filtered.filter((it) => it.timeOfDay === 'night');
  } else if (state.timeFilter === '室内') {
    filtered = filtered.filter((it) => it.timeOfDay === 'indoor');
  }

  return filtered;
}

function renderMeta(items) {
  const meta = qs('#sceneMeta');
  if (!meta) return;
  const total = state.data?.total ?? 0;

  const isFile = window.location.protocol === 'file:';
  const isSecure = window.isSecureContext;
  const hasClipboardWrite = !!navigator.clipboard?.write;
  const hasClipboardItem = !!window.ClipboardItem;
  const canCopyImage = !isFile && isSecure && hasClipboardWrite && hasClipboardItem;

  const hint =
    isFile
      ? `<span class="meta-pill" style="border-color: rgba(239,68,68,0.35); color: #b91c1c;">
          提示：你正在用 file:// 打开（只能看图），复制图片会失败；请运行 <strong>start.cmd</strong> 用 http://localhost 打开
        </span>`
      : `<span class="meta-pill" style="border-color: rgba(99,102,241,0.25);">
          复制图片：<strong style="color:${canCopyImage ? '#16a34a' : '#b91c1c'}">${canCopyImage ? '可用' : '不可用'}</strong>
          <span style="opacity:.8;">（secure=${isSecure ? 'yes' : 'no'} / clipboardWrite=${hasClipboardWrite ? 'yes' : 'no'} / ClipboardItem=${hasClipboardItem ? 'yes' : 'no'}）</span>
        </span>`;
  meta.innerHTML = `
    <span class="meta-pill">总数：<strong>${total}</strong></span>
    <span class="meta-pill">当前显示：<strong>${items.length}</strong></span>
    <span class="meta-pill">分区：<strong>${escapeHtml(state.category)}</strong></span>
    ${hint}
  `;
}

function computeCountMap() {
  const countMap = new Map();
  const trashSet = getTrashSet();
  for (const it of state.data?.items || []) {
    if (trashSet.has(it.abs)) continue;
    countMap.set(it.category, (countMap.get(it.category) || 0) + 1);
  }
  return countMap;
}

function renderCategoryChips(countMap) {
  const wrap = qs('#categoryChips');
  if (!wrap || !state.data) return;
  const trashSet = getTrashSet();
  const favoritesSet = getFavoritesSet();
  const totalNonTrash = (state.data?.items || []).filter((it) => !trashSet.has(it.abs)).length;
  const favCount = (state.data?.items || []).filter(
    (it) => favoritesSet.has(it.abs) && !trashSet.has(it.abs)
  ).length;
  const trashCount = trashSet.size;

  const leftCats = ['全部', ...state.data.categories];
  const rightCats = ['收藏夹', '回收站'];

  const chipHtml = (c) => {
    const active = c === state.category ? 'is-active' : '';
    const count =
      c === '全部' ? totalNonTrash : c === '收藏夹' ? favCount : c === '回收站' ? trashCount : countMap.get(c) || 0;
    return `<button class="chip ${active}" type="button" data-cat="${escapeHtml(
      c
    )}">${escapeHtml(c)} <span class="chip-count">${count}</span></button>`;
  };

  // 时间筛选器
  const timeOpts = [
    { val: '全部', label: '全部时间' },
    { val: '白天', label: '☀️ 白天' },
    { val: '黄昏', label: '🌆 黄昏' },
    { val: '晚上', label: '🌙 晚上' },
    { val: '室内', label: '🏠 室内' },
    { val: '未标记', label: '❓ 未标记' },
  ];
  const timeSelectHtml = `
    <div class="time-filter-wrap">
      <select id="timeFilterSelect" class="time-select">
        ${timeOpts
          .map(
            (o) =>
              `<option value="${o.val}" ${state.timeFilter === o.val ? 'selected' : ''}>${o.label}</option>`
          )
          .join('')}
      </select>
      <button id="btnAutoTag" class="btn-auto-tag" type="button" title="自动识别未标记图片的时间">✨ 自动识别</button>
    </div>
  `;

  wrap.innerHTML = `
    <div class="chips-row">
      <div class="chips-left">${leftCats.map(chipHtml).join('')}</div>
      <div class="chips-spacer"></div>
      <div class="chips-right">${rightCats.map(chipHtml).join('')}</div>
    </div>
    <div class="filters-row">
      ${timeSelectHtml}
    </div>
  `;

  qsa('.chip', wrap).forEach((btn) => {
    btn.addEventListener('click', () => {
      state.category = btn.getAttribute('data-cat') || '全部';
      setUrlParams();
      renderAll();
    });
  });

  const sel = qs('#timeFilterSelect');
  if (sel) {
    sel.addEventListener('change', () => {
      state.timeFilter = sel.value;
      setUrlParams();
      renderAll();
    });
  }

  const btnTag = qs('#btnAutoTag');
  if (btnTag) {
    btnTag.addEventListener('click', () => runAutoTagging(false));
  }
}

// Settings Modal Logic
const settingsModal = qs('#settingsModal');
const settingsCat = qs('#settingsCat');
const settingsTime = qs('#settingsTime');
const settingsFav = qs('#settingsFav');
const settingsTrash = qs('#settingsTrash');
const settingsPreviewImg = qs('#settingsPreviewImg');
const btnSaveSettings = qs('#btnSaveSettings');
let currentSettingsAbs = null;

function openSettingsModal(abs, category, timeOfDay, url) {
  if (!settingsModal) return;
  currentSettingsAbs = abs;
  
  // Populate categories
  if (settingsCat && state.data) {
    settingsCat.innerHTML = state.data.categories
      .map(c => `<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`)
      .join('');
    settingsCat.value = category || '未分区';
  }
  
  if (settingsTime) {
    settingsTime.value = timeOfDay || '';
  }

  // Populate checks
  const favSet = getFavoritesSet();
  const trashSet = getTrashSet();
  if (settingsFav) settingsFav.checked = favSet.has(abs);
  if (settingsTrash) settingsTrash.checked = trashSet.has(abs);

  // Preview Image
  if (settingsPreviewImg) {
    settingsPreviewImg.src = url || '';
  }

  settingsModal.classList.add('is-open');
  settingsModal.setAttribute('aria-hidden', 'false');
}

function closeSettingsModal() {
  if (!settingsModal) return;
  settingsModal.classList.remove('is-open');
  settingsModal.setAttribute('aria-hidden', 'true');
  currentSettingsAbs = null;
  if (settingsPreviewImg) settingsPreviewImg.src = '';
}

if (settingsModal) {
  settingsModal.addEventListener('click', (e) => {
    if (e.target.hasAttribute('data-close-settings')) closeSettingsModal();
  });
  
  btnSaveSettings?.addEventListener('click', async () => {
    if (!currentSettingsAbs) return;
    
    const cat = settingsCat.value;
    const time = settingsTime.value;
    const isFav = settingsFav?.checked ?? false;
    const isTrash = settingsTrash?.checked ?? false;
    
    // UI Feedback
    btnSaveSettings.disabled = true;
    btnSaveSettings.textContent = '保存中...';

    try {
      // 1. Update Item Props (Category, Time)
      const updates = [{
        abs: currentSettingsAbs,
        changes: {
          category: cat,
          timeOfDay: time || null
        }
      }];
      
      const res = await fetch(`${API_BASE}/api/db/update-items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates }),
      });
      const json = await res.json();
      
      if (!json.ok) throw new Error(json.error);

      // 2. Update Favorites
      const favSet = getFavoritesSet();
      const wasFav = favSet.has(currentSettingsAbs);
      if (isFav !== wasFav) {
        if (isUsingServer()) await apiToggleFav(currentSettingsAbs);
        else {
          if (isFav) favSet.add(currentSettingsAbs); else favSet.delete(currentSettingsAbs);
          saveLocalFavorites(favSet);
        }
      }

      // 3. Update Trash
      const trashSet = getTrashSet();
      const wasTrash = trashSet.has(currentSettingsAbs);
      if (isTrash !== wasTrash) {
        if (isUsingServer()) {
          if (isTrash) await apiDelete(currentSettingsAbs);
          else await apiRestore(currentSettingsAbs);
        } else {
          if (isTrash) trashSet.add(currentSettingsAbs); else trashSet.delete(currentSettingsAbs);
          saveLocalTrash(trashSet);
        }
      }

      // Update local state & UI
      const item = state.data.items.find(it => it.abs === currentSettingsAbs);
      if (item) {
        item.category = cat;
        item.timeOfDay = time || null;
      }
      // Re-fetch fav/trash state from server if possible, or assume success
      if (isUsingServer() && state.data) {
         // Manually update local cache of fav/trash arrays to reflect changes immediately
         // (Real sync happens on re-fetch or next action, but for UI responsiveness)
         if (isFav && !state.data.favorites.includes(currentSettingsAbs)) state.data.favorites.push(currentSettingsAbs);
         if (!isFav) state.data.favorites = state.data.favorites.filter(x => x !== currentSettingsAbs);
         
         if (isTrash && !state.data.trash.includes(currentSettingsAbs)) state.data.trash.push(currentSettingsAbs);
         if (!isTrash) state.data.trash = state.data.trash.filter(x => x !== currentSettingsAbs);
      }

      renderAll();
      closeSettingsModal();

    } catch (e) {
      alert('保存失败: ' + e.message);
    } finally {
      btnSaveSettings.disabled = false;
      btnSaveSettings.textContent = '保存';
    }
  });
}

function renderSections(items) {
  const sections = qs('#sceneSections');
  const empty = qs('#sceneEmpty');
  if (!sections) return;
  if (empty) empty.style.display = items.length ? 'none' : 'block';

  const favoritesSet = getFavoritesSet();
  const isTrashView = state.category === '回收站';

  // 合并显示为一个大 Grid，不再按 Category 分组
  sections.innerHTML = `
    <section class="cat-section">
      <div class="scene-grid">
        ${items
          .map((it, idx) => {
            const title = `${it.category}/${it.name}`;
            const fav = favoritesSet.has(it.abs);
            const actionBtn = isTrashView
              ? `<button class="restore-btn" type="button" data-action="restore" aria-label="恢复" title="恢复">↩</button>`
              : `<button class="delete-btn" type="button" data-action="delete" aria-label="移到回收站" title="移到回收站">🗑</button>`;
            
            let timeIcon = '';
            if (it.timeOfDay === 'day') timeIcon = '☀️';
            else if (it.timeOfDay === 'night') timeIcon = '🌙';
            else if (it.timeOfDay === 'dusk') timeIcon = '🌆';
            else if (it.timeOfDay === 'indoor') timeIcon = '🏠';

            const timeBadge = timeIcon ? `<span class="time-badge" title="${it.timeOfDay}">${timeIcon}</span>` : '';
            const thumb480 = toThumbUrl(it.url, 480, 70);
            const thumb720 = toThumbUrl(it.url, 720, 72);

            return `
              <div class="scene-card" role="button" tabindex="0"
                data-url="${escapeHtml(it.url)}"
                data-title="${escapeHtml(title)}"
                data-path="${escapeHtml(it.abs)}"
                data-cat="${escapeHtml(it.category)}"
                data-time="${escapeHtml(it.timeOfDay || '')}">
                ${actionBtn}
                <button class="settings-btn" type="button" data-action="settings" aria-label="设置" title="设置">⚙</button>
                ${timeBadge}
                <button class="fav-btn ${fav ? 'is-fav' : ''}" type="button" data-action="fav" aria-label="${fav ? '取消收藏' : '收藏'}" title="${fav ? '已收藏' : '收藏'}">${fav ? '★' : '☆'}</button>
                
                <div class="scene-overlay">
                  <button class="drag-btn" type="button" draggable="true" data-action="drag" aria-label="拖拽到其他网页">⠿</button>
                  <button class="zoom-btn" type="button" data-action="zoom" aria-label="放大预览">⤢</button>
                </div>
                <div class="scene-thumb">
                  <img loading="${idx < 24 ? 'eager' : 'lazy'}" decoding="async" fetchpriority="${idx < 8 ? 'high' : 'low'}"
                    src="${escapeHtml(thumb480)}"
                    srcset="${escapeHtml(thumb480)} 480w, ${escapeHtml(thumb720)} 720w"
                    sizes="(max-width: 900px) 100vw, (max-width: 1400px) 33vw, 25vw"
                    alt="${escapeHtml(
              title
            )}">
                </div>
              </div>
            `;
          })
          .join('')}
      </div>
    </section>
  `;

  // bind events (same as before)
  qsa('.scene-card', sections).forEach((card) => {
    const getAbs = () => card.getAttribute('data-path') || '';
    const getUrl = () => card.getAttribute('data-url') || '';

    const copyThis = async () => {
      const url = getUrl();
      const { ok, reason } = await copyImageOnly(url);
      flashCardCopied(card, ok ? '已复制图片' : `复制失败：${reason}`);
    };

    // 单击：复制当前图片（仅复制图片本体）
    card.addEventListener('click', copyThis);
    card.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        copyThis();
      }
    });

    // 设置按钮
    qsa('[data-action="settings"]', card).forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const abs = card.getAttribute('data-path');
        const cat = card.getAttribute('data-cat');
        const time = card.getAttribute('data-time');
        const url = card.getAttribute('data-url');
        openSettingsModal(abs, cat, time, url);
      });
    });

    // 左下角收藏：点击切换收藏状态

    // 收藏：切换收藏状态（优先 API，file:// 用 localStorage）
    qsa('[data-action="fav"]', card).forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const abs = card.getAttribute('data-path') || '';
        if (!abs) return;
        if (isUsingServer()) {
          const json = await apiToggleFav(abs);
          if (!json?.ok) {
            console.warn('toggle-fav failed', json);
          }
        } else {
          const fav = loadLocalFavorites();
          if (fav.has(abs)) fav.delete(abs);
          else fav.add(abs);
          saveLocalFavorites(fav);
        }
        setUrlParams();
        renderAll();
      });
    });

    // 删除：移到回收站
    qsa('[data-action="delete"]', card).forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const abs = card.getAttribute('data-path') || '';
        if (!abs) return;
        if (isUsingServer()) {
          const json = await apiDelete(abs);
          if (!json?.ok) {
            console.warn('delete failed', json);
            return;
          }
        } else {
          const tr = loadLocalTrash();
          tr.add(abs);
          saveLocalTrash(tr);
        }
        setUrlParams();
        renderAll();
      });
    });

    // 恢复：从回收站恢复
    qsa('[data-action="restore"]', card).forEach((btn) => {
      btn.addEventListener('click', async (e) => {
        e.stopPropagation();
        e.preventDefault();
        const abs = card.getAttribute('data-path') || '';
        if (!abs) return;
        if (isUsingServer()) {
          const json = await apiRestore(abs);
          if (!json?.ok) {
            console.warn('restore failed', json);
            return;
          }
        } else {
          const tr = loadLocalTrash();
          tr.delete(abs);
          saveLocalTrash(tr);
        }
        setUrlParams();
        renderAll();
      });
    });

    // 右下角拖拽手柄：给别的网页提供可识别的数据（URL/HTML/DownloadURL）
    qsa('[data-action="drag"]', card).forEach((btn) => {
      btn.addEventListener('click', (e) => e.stopPropagation());
      btn.addEventListener('dragstart', (e) => {
        e.stopPropagation();
        const abs = card.getAttribute('data-path') || '';
        const url = toAbsoluteUrl(card.getAttribute('data-url') || '');
        const title = card.getAttribute('data-title') || '';
        const filename = (title.split('/').pop() || 'image.png').replace(/[\\/:*?"<>|]/g, '_');
        const mime = guessMimeByName(filename);

        const dt = e.dataTransfer;
        if (!dt) return;
        dt.effectAllowed = 'copy';
        // 常见可识别格式
        dt.setData('text/uri-list', url);
        dt.setData('text/plain', url);
        dt.setData('text/html', `<img src="${url}" alt="${escapeHtml(title)}">`);
        // Chrome/Edge：拖到桌面/部分应用可生成文件
        dt.setData('DownloadURL', `${mime}:${filename}:${url}`);

        // 额外信息（便于调试/某些站点识别）
        if (abs) dt.setData('application/x-local-abs-path', abs);
      });
    });

    // 右下角放大按钮：打开预览
    qsa('[data-action="zoom"]', card).forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        openLightbox(card.getAttribute('data-url'), card.getAttribute('data-title'), card.getAttribute('data-path'));
      });
    });
  });

  // file:// + mac 下：图片加载失败时按候选路径自动重试
  if (window.location.protocol === 'file:') {
    qsa('.scene-card', sections).forEach((card) => {
      const imgEl = qs('.scene-thumb img', card);
      if (!imgEl) return;
      const abs = card.getAttribute('data-path') || '';
      const item = state.visibleItems.find((it) => it.abs === abs);
      const candidates = Array.isArray(item?._urlCandidates) ? item._urlCandidates : [];
      if (candidates.length <= 1) return;

      let idx = 0;
      imgEl.addEventListener('error', () => {
        idx += 1;
        if (idx >= candidates.length) return;
        const nextUrl = candidates[idx];
        card.setAttribute('data-url', nextUrl);
        imgEl.srcset = '';
        imgEl.src = nextUrl;
      });
    });
  }
}

function renderAll() {
  const items = filterItems();
  state.visibleItems = items;
  const countMap = computeCountMap();
  renderCategoryChips(countMap);
  renderMeta(items);
  renderSections(items);
  enqueueThumbWarmup(items);
}

// Lightbox
const lightbox = qs('#imageLightbox');
const lightboxImage = qs('#lightboxImage');
const lightboxTitle = qs('#lightboxTitle');
const lightboxPrev = qs('#lightboxPrev');
const lightboxNext = qs('#lightboxNext');
let current = { url: '', title: '', path: '' };
let currentIndex = -1;

function clampIndex(i) {
  const n = state.visibleItems.length;
  if (!n) return -1;
  return Math.max(0, Math.min(n - 1, i));
}

function updateNavButtons() {
  const n = state.visibleItems.length;
  const has = n > 0 && currentIndex >= 0;
  if (lightboxPrev) lightboxPrev.disabled = !has || currentIndex <= 0;
  if (lightboxNext) lightboxNext.disabled = !has || currentIndex >= n - 1;
}

function showAtIndex(i) {
  const idx = clampIndex(i);
  if (idx < 0) return;
  const it = state.visibleItems[idx];
  currentIndex = idx;
  current = {
    url: it?.url || '',
    title: `${it?.category || ''}/${it?.name || ''}`.replace(/^\/|\/$/g, ''),
    path: it?.abs || '',
  };
  if (lightboxTitle) lightboxTitle.textContent = current.title || '—';
  if (lightboxImage) lightboxImage.src = current.url;
  updateNavButtons();
}

function findIndexByAbs(absPath) {
  if (!absPath) return -1;
  return state.visibleItems.findIndex((it) => it.abs === absPath);
}

function openLightbox(url, title, absPath) {
  if (!lightbox || !lightboxImage) return;
  const idx = findIndexByAbs(absPath);
  if (idx >= 0) {
    showAtIndex(idx);
  } else {
    // fallback：不在当前筛选列表里时，仍可预览（但不提供前后切换）
    currentIndex = -1;
    current = { url: url || '', title: title || '', path: absPath || '' };
    if (lightboxTitle) lightboxTitle.textContent = current.title || '—';
    lightboxImage.src = current.url;
    updateNavButtons();
  }
  lightbox.classList.add('is-open');
  lightbox.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
}

function closeLightbox() {
  if (!lightbox) return;
  lightbox.classList.remove('is-open');
  lightbox.setAttribute('aria-hidden', 'true');
  if (lightboxImage) lightboxImage.src = '';
  document.body.style.overflow = '';
  currentIndex = -1;
  updateNavButtons();
}

function buildCopyText(type) {
  if (type === 'md') return `![](${current.url})`;
  if (type === 'html') return `<img src="${current.url}" alt="${current.title}">`;
  return current.path || current.url;
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    ta.remove();
    return true;
  }
}

function imageFromUrlToPngBlob(url) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext('2d');
        if (!ctx) return reject(new Error('no_canvas_ctx'));
        ctx.drawImage(img, 0, 0);
        canvas.toBlob((blob) => {
          if (blob) resolve(blob);
          else reject(new Error('toBlob_failed'));
        }, 'image/png');
      } catch (e) {
        reject(e);
      }
    };
    img.onerror = () => reject(new Error('img_load_failed'));
    img.src = url;
  });
}

function explainCopyImageUnavailable() {
  if (window.location.protocol === 'file:') return '请用 start.cmd（http://localhost）打开';
  if (!window.isSecureContext) return '需要安全环境（https 或 localhost）';
  if (!navigator.clipboard?.write) return '浏览器不支持 clipboard.write';
  if (!window.ClipboardItem) return '浏览器不支持 ClipboardItem';
  return '';
}

async function copyImageOnly(url) {
  // 只复制图片本体；不做“复制路径”的兜底
  if (!url) return { ok: false, reason: 'url 为空' };

  const pre = explainCopyImageUnavailable();
  if (pre) return { ok: false, reason: pre };

  try {
    // 优先 fetch 拿 blob（在 https/localhost 更稳定；file:// 可能失败）
    const res = await fetch(url, { cache: 'force-cache' });
    const blob = await res.blob();
    const mime = blob.type || 'image/png';
    await navigator.clipboard.write([new ClipboardItem({ [mime]: blob })]);
    return { ok: true, reason: '' };
  } catch (e) {
    // fallback：img + canvas 转 blob（部分环境 fetch file:// 会失败）
    try {
      const pngBlob = await imageFromUrlToPngBlob(url);
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': pngBlob })]);
      return { ok: true, reason: '' };
    } catch (e2) {
      const name = (e2 && typeof e2 === 'object' && 'name' in e2 && e2.name) ? e2.name : '';
      const msg = (e2 && typeof e2 === 'object' && 'message' in e2 && e2.message) ? e2.message : '';
      // 常见：NotAllowedError / SecurityError / NotFoundError
      return { ok: false, reason: name || msg || '未知原因（可能被浏览器/系统策略拦截）' };
    }
  }
}

function flashCardCopied(card, text) {
  if (!card) return;
  const old = card.getAttribute('data-flash') || '';
  card.setAttribute('data-flash', text || '已复制');
  card.classList.add('is-copied');
  setTimeout(() => {
    card.classList.remove('is-copied');
    if (old) card.setAttribute('data-flash', old);
    else card.removeAttribute('data-flash');
  }, 650);
}

if (lightbox) {
  lightbox.addEventListener('click', (e) => {
    const target = e.target;
    if (target && target.hasAttribute('data-lightbox-close')) closeLightbox();
  });
}

lightboxPrev?.addEventListener('click', () => {
  if (currentIndex > 0) showAtIndex(currentIndex - 1);
});

lightboxNext?.addEventListener('click', () => {
  const n = state.visibleItems.length;
  if (currentIndex >= 0 && currentIndex < n - 1) showAtIndex(currentIndex + 1);
});

document.addEventListener('keydown', (e) => {
  const isOpen = lightbox?.classList.contains('is-open');
  if (e.key === 'Escape' && isOpen) closeLightbox();
  if (!isOpen) return;
  if (e.key === 'ArrowLeft') {
    if (currentIndex > 0) showAtIndex(currentIndex - 1);
  }
  if (e.key === 'ArrowRight') {
    const n = state.visibleItems.length;
    if (currentIndex >= 0 && currentIndex < n - 1) showAtIndex(currentIndex + 1);
  }
});

// Copy page link
const btnCopyPageLink = qs('#btnCopyPageLink');
btnCopyPageLink?.addEventListener('click', async () => {
  const url = window.location.href;
  await copyToClipboard(url);
  const old = btnCopyPageLink.textContent;
  btnCopyPageLink.textContent = '已复制';
  setTimeout(() => (btnCopyPageLink.textContent = old), 900);
});

// Refresh index (re-scan new images)
const btnRefreshIndex = qs('#btnRefreshIndex');
btnRefreshIndex?.addEventListener('click', async () => {
  if (window.location.protocol === 'file:') {
    alert('请运行 start.cmd 用 http://localhost 打开后再刷新索引。');
    return;
  }
  const oldTitle = btnRefreshIndex.getAttribute('title') || '';
  btnRefreshIndex.disabled = true;
  btnRefreshIndex.classList.add('is-loading');
  btnRefreshIndex.setAttribute('title', '刷新中...');
  try {
    const res = await fetch('/api/reindex', { method: 'POST' });
    if (!res.ok) throw new Error(`reindex_failed_${res.status}`);
    
    // 刷新成功后，自动触发一次“自动识别”
    // 为了不阻塞 UI，先 reload 页面，然后在 init 里检查是否需要自动识别？
    // 或者直接在这里调用 runAutoTagging？
    // 由于 reindex 可能会增加新图片，reload 是最稳妥的，但 reload 后无法自动触发 tag。
    // 我们可以加一个 URL 参数 ?autoTag=1
    
    const url = new URL(window.location.href);
    url.searchParams.set('_', String(Date.now()));
    url.searchParams.set('autoTag', '1'); // 标记需要自动识别
    window.location.href = url.toString();
  } catch (e) {
    console.error(e);
    alert('刷新失败：请确认你是用 start.cmd 启动的本地服务，并且服务窗口没有报错。');
    btnRefreshIndex.disabled = false;
    btnRefreshIndex.classList.remove('is-loading');
    btnRefreshIndex.setAttribute('title', oldTitle || '刷新并更新图片');
  }
});

// 记住滚动位置（避免每次打开都回到顶部）
window.addEventListener('beforeunload', () => {
  try {
    localStorage.setItem(LS_SCROLL_KEY, String(window.scrollY || 0));
  } catch {
    // ignore
  }
});

// --- Auto Tagging Logic ---

async function analyzeImageTime(item) {
  // 1. 优先判断文件夹：只有“室内”文件夹才标记为室内
  if (item.category && item.category.includes('室内')) {
    return 'indoor';
  }

  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.src = item.url;
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        const w = 50, h = 50;
        canvas.width = w;
        canvas.height = h;
        const ctx = canvas.getContext('2d');
        if (!ctx) return resolve(null);
        ctx.drawImage(img, 0, 0, w, h);
        
        // 只分析顶部 35% (天空区域)
        const skyH = Math.floor(h * 0.35);
        const data = ctx.getImageData(0, 0, w, skyH).data;
        
        let rSum = 0, gSum = 0, bSum = 0, lSum = 0;
        const pixelCount = w * skyH;

        for (let i = 0; i < data.length; i += 4) {
          const r = data[i];
          const g = data[i + 1];
          const b = data[i + 2];
          const l = 0.299 * r + 0.587 * g + 0.114 * b;
          rSum += r;
          gSum += g;
          bSum += b;
          lSum += l;
        }

        const avgL = lSum / pixelCount;
        const avgR = rSum / pixelCount;
        const avgG = gSum / pixelCount;
        const avgB = bSum / pixelCount;

        // 1. 晚上 (Night): 深蓝色或极暗
        if (avgL < 50) return resolve('night');
        if (avgL < 100 && avgB > avgR * 1.2 && avgB > avgG * 1.1) return resolve('night');

        // 2. 黄昏 (Dusk): 橘色/红色/粉色/紫色
        const isWarm = avgR > avgB; // 偏红/橙
        const isPurple = avgR > avgG * 1.1 && avgB > avgG * 1.1; // 偏紫
        
        if (isWarm || isPurple) {
           const max = Math.max(avgR, avgG, avgB);
           const min = Math.min(avgR, avgG, avgB);
           if (max - min > 15) { 
             return resolve('dusk');
           }
        }

        // 3. 其他情况默认为白天 (Day)
        return resolve('day');
      } catch (e) {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
  });
}

async function runAutoTagging(isAuto = false) {
  if (!isUsingServer()) {
    if (!isAuto) alert('请在本地服务器环境下运行 (start.cmd)');
    return;
  }
  const btn = qs('#btnAutoTag');
  
  // 询问是否覆盖 (仅当手动点击时)
  let overwrite = false;
  if (!isAuto) {
    overwrite = confirm('是否重新分析所有图片？\n点击“确定”将重新识别所有图片（包括已标记的）。\n点击“取消”仅识别未标记的新图片。');
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = '分析中...';
  }

  const items = state.data?.items || [];
  const targets = overwrite ? items : items.filter(it => !it.timeOfDay);
  
  if (targets.length === 0) {
    if (!isAuto) alert('所有图片都已标记');
    if (btn) {
      btn.disabled = false;
      btn.textContent = '✨ 自动识别';
    }
    return;
  }

  let changed = [];
  const batchSize = 10;
  
  // 分批处理避免卡顿
  for (let i = 0; i < targets.length; i += batchSize) {
    const batch = targets.slice(i, i + batchSize);
    const promises = batch.map(async (it) => {
      const time = await analyzeImageTime(it);
      if (time) {
        return { abs: it.abs, changes: { timeOfDay: time } };
      }
      return null;
    });
    
    const results = await Promise.all(promises);
    changed.push(...results.filter(Boolean));
    
    if (btn) btn.textContent = `分析中 (${Math.min(i + batchSize, targets.length)}/${targets.length})`;
  }

  if (changed.length > 0) {
    try {
      const res = await fetch(`${API_BASE}/api/db/update-items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates: changed }),
      });
      const json = await res.json();
      if (json.ok) {
        // 更新本地状态
        const itemMap = new Map();
        state.data.items.forEach((it, idx) => itemMap.set(it.abs, idx));
        for (const ch of changed) {
          const idx = itemMap.get(ch.abs);
          if (idx !== undefined) {
            state.data.items[idx] = { ...state.data.items[idx], ...ch.changes };
          }
        }
        renderAll();
        if (!isAuto) alert(`已更新 ${changed.length} 张图片的标签`);
        else console.log(`[AutoTag] Updated ${changed.length} items`);
      } else {
        console.error('Save failed', json);
        if (!isAuto) alert('保存失败: ' + json.error);
      }
    } catch (e) {
      console.error('Save error', e);
      if (!isAuto) alert('保存失败: ' + e.message);
    }
  } else {
    if (!isAuto) alert('未能识别出任何新标签');
  }

  if (btn) {
    btn.disabled = false;
    btn.textContent = '✨ 自动识别';
  }
}

// Boot
(async function init() {
  readUrlParams();
  let data = window.__SCENE_DB__;
  if (!data) {
    try {
      const res = await fetch(DB_URL);
      data = await res.json();
    } catch (e) {
      console.error('Failed to load scene db.', e);
      const empty = qs('#sceneEmpty');
      if (empty) {
        empty.style.display = 'block';
        empty.textContent = '数据库加载失败：请运行 start.cmd 启动服务，或确保 scene-db.data.js 存在。';
      }
      return;
    }
  }

  state.data = data;

  // 如果是直接双击打开（file://），/sence/... 不存在，会导致图片全挂。
  // 这里做一个“仅用于展示”的兜底：把 url 临时改回 file:///absPath，让缩略图能显示。
  // 注意：file:// 下浏览器通常不允许“复制图片到剪贴板”，请用 start.cmd 在 http://localhost 下打开。
  if (window.location.protocol === 'file:' && state.data?.items?.length) {
    state.data.items = state.data.items.map((it) => ({
      ...it,
      _urlCandidates: absPathToFileUrlCandidates(it.abs),
      url: absPathToFileUrl(it.abs),
    }));
  }

  const validCats = ['全部', ...(data.categories || []), '收藏夹', '回收站'];
  if (state.category && !validCats.includes(state.category)) {
    state.category = '全部';
  }
  renderAll();

  // 恢复滚动位置（仅在没有明确 hash/定位时）
  try {
    const raw = localStorage.getItem(LS_SCROLL_KEY);
    const y = raw ? Number(raw) : 0;
    if (Number.isFinite(y) && y > 0) {
      setTimeout(() => window.scrollTo({ top: y, behavior: 'instant' }), 0);
    }
  } catch {
    // ignore
  }

  // 检查是否需要自动运行 Auto Tag (来自刷新按钮的 reload)
  const url = new URL(window.location.href);
  if (url.searchParams.get('autoTag') === '1') {
    // 清除参数，避免下次刷新还触发
    url.searchParams.delete('autoTag');
    history.replaceState(null, '', url.toString());
    // 稍微延迟一下等待渲染
    setTimeout(() => {
        runAutoTagging(true);
    }, 500);
  }
})();

