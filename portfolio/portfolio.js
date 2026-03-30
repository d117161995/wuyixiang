/* ════════════════════════════════════════════
   XD Studio – 影视作品集  |  交互逻辑
   ════════════════════════════════════════════ */
(function () {
  'use strict';

  const DB = window.__PORTFOLIO_DB__;
  if (!DB) {
    document.getElementById('content').innerHTML =
      '<p style="text-align:center;padding:4rem;color:#8892a8;">数据库加载失败，请先运行 <code>node tools/fetch-portfolio.mjs</code></p>';
    return;
  }

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => [...document.querySelectorAll(sel)];

  const isFileProtocol = location.protocol === 'file:';
  const LOCAL_VIDEO_ROOT = 'Y:/作品集合';

  function resolveVideoSrc(localVideoUrl) {
    if (!localVideoUrl) return '';
    if (isFileProtocol) {
      const decoded = decodeURIComponent(localVideoUrl.replace('/local-videos/', ''));
      return `file:///${LOCAL_VIDEO_ROOT}/${decoded}`;
    }
    return localVideoUrl;
  }

  // ─── State ───
  const state = {
    game: null,
    category: null,
    difficulty: null,
    production: null,
    search: '',
    missing: null,
  };

  // ─── Render Stats ───
  function renderStats() {
    const el = $('#topbar-stats');
    el.innerHTML = `
      <span class="stat-item">游戏 <span class="stat-num">6</span></span>
      <span class="stat-item">视频 <span class="stat-num">${DB.projectCount}</span></span>
      <span class="stat-item">更新 <span class="stat-num">${new Date(DB.lastUpdated).toLocaleDateString('zh-CN')}</span></span>
    `;
  }

  // ─── Render Update Log ───
  function renderUpdateLog() {
    const el = $('#update-log');
    if (!el || !DB.updateLogs || !DB.updateLogs.length) return;
    const log = DB.updateLogs[0];
    const t = new Date(log.time);
    const timeStr = `${t.toLocaleDateString('zh-CN')} ${t.toLocaleTimeString('zh-CN', {hour:'2-digit',minute:'2-digit'})}`;

    const TYPE_ICONS = { added: '＋', removed: '－', cover: '🖼', updated: '✎', none: '✓' };
    const TYPE_CLASS = { added: 'log-added', removed: 'log-removed', cover: 'log-cover', updated: 'log-updated', none: 'log-none' };

    const changesHtml = (log.changes || []).map(c => {
      const icon = TYPE_ICONS[c.type] || '•';
      const cls = TYPE_CLASS[c.type] || '';
      const itemsStr = c.items.map(i => `<span class="log-change-item">${i}</span>`).join('');
      return `<div class="log-change-group ${cls}"><span class="log-change-icon">${icon}</span><span class="log-change-label">${c.label}：</span>${itemsStr}</div>`;
    }).join('');

    const copyText = `影视作品集更新（${timeStr}）\n` +
      (log.changes || []).map(c => `${c.label}：${c.items.join('、')}`).join('\n');

    el.innerHTML = `
      <div class="update-log-inner">
        <div class="update-log-header">
          <span class="update-log-label">上次更新</span>
          <span class="update-log-time">${timeStr}</span>
          <button class="update-log-copy" id="btn-copy-log" title="复制更新内容">复制</button>
        </div>
        <div class="update-log-changes">${changesHtml}</div>
      </div>
    `;

    $('#btn-copy-log').addEventListener('click', () => {
      navigator.clipboard.writeText(copyText).then(() => {
        const btn = $('#btn-copy-log');
        btn.textContent = '已复制';
        btn.classList.add('copied');
        setTimeout(() => { btn.textContent = '复制'; btn.classList.remove('copied'); }, 1500);
      });
    });
  }

  // ─── Render Filters ───
  function renderFilters() {
    renderChips('filter-game', DB.games.map(g => g.name), 'game');
    renderChips('filter-category', DB.stats.categories, 'category');
    renderChips('filter-difficulty', DB.stats.difficulties, 'difficulty');
    renderChips('filter-production', DB.stats.productions, 'production');
    renderSelect('select-game', DB.games.map(g => g.name), 'game', '全部游戏');
    renderSelect('select-category', DB.stats.categories, 'category', '全部类别');
    renderSelect('select-production', DB.stats.productions, 'production', '全部方式');
  }

  function renderSelect(selectId, values, filterKey, defaultLabel) {
    const sel = document.getElementById(selectId);
    if (!sel) return;
    sel.innerHTML = `<option value="">${defaultLabel}</option>` +
      values.map(v => `<option value="${v}">${v}</option>`).join('');
    sel.addEventListener('change', () => {
      const val = sel.value;
      state[filterKey] = val || null;
      const chipsEl = document.getElementById('filter-' + filterKey);
      if (chipsEl) {
        chipsEl.querySelectorAll('.chip').forEach(c => {
          c.classList.toggle('active', c.dataset.value === val);
        });
      }
      applyFilters();
    });
  }

  const HIGHLIGHT_CHIPS = ['游戏衍生动画', '半自动AI', '全自动AI'];

  function renderChips(containerId, values, filterKey) {
    const el = document.getElementById(containerId);
    el.innerHTML = values.map(v => {
      const extra = HIGHLIGHT_CHIPS.includes(v) ? ' chip--highlight' : '';
      return `<button class="chip${extra}" data-filter="${filterKey}" data-value="${v}">${v}</button>`;
    }).join('');

    el.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      const val = chip.dataset.value;
      if (state[filterKey] === val) {
        state[filterKey] = null;
        chip.classList.remove('active');
      } else {
        el.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
        state[filterKey] = val;
        chip.classList.add('active');
      }
      applyFilters();
    });
  }

  // ─── Search ───
  const searchInput = $('#search-input');
  let searchTimer;
  searchInput.addEventListener('input', () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.search = searchInput.value.trim().toLowerCase();
      applyFilters();
    }, 200);
  });

  // ─── Check Dropdown ───
  const checkToggle = $('#check-toggle');
  const checkPanel = $('#check-panel');

  function countMissing() {
    const counts = { video: 0, cover: 0, category: 0, difficulty: 0 };
    DB.games.forEach(g => g.projects.forEach(p => {
      if (!p.localVideo && !p.video) counts.video++;
      if (!p.cover) counts.cover++;
      if (!p.categories || !p.categories.length) counts.category++;
      if (!p.difficulty || !p.difficulty.length) counts.difficulty++;
    }));
    return counts;
  }

  function updateMissingLabels() {
    const counts = countMissing();
    const total = counts.video + counts.cover + counts.category + counts.difficulty;
    if (!state.missing) {
      checkToggle.innerHTML = total > 0 ? `资源检查 (${total}) ▾` : '资源检查 <span class="check-ok">✓</span> ▾';
    }
    missingContainer.querySelectorAll('.chip').forEach(chip => {
      const key = chip.dataset.missing;
      const n = counts[key] || 0;
      const labels = { video: '缺视频', cover: '缺封面', category: '缺分类', difficulty: '缺难度' };
      chip.innerHTML = n > 0 ? `${labels[key]} (${n})` : `${labels[key]} <span class="check-ok">✓</span>`;
    });
  }

  const missingContainer = document.getElementById('filter-missing');
  checkToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    const isOpen = checkPanel.classList.toggle('open');
    checkToggle.classList.toggle('open', isOpen);
  });
  document.addEventListener('click', (e) => {
    if (!e.target.closest('.check-dropdown')) {
      checkPanel.classList.remove('open');
      checkToggle.classList.remove('open');
    }
  });
  missingContainer.addEventListener('click', (e) => {
    const chip = e.target.closest('.chip');
    if (!chip) return;
    const val = chip.dataset.missing;
    if (state.missing === val) {
      state.missing = null;
      chip.classList.remove('active');
      updateMissingLabels();
    } else {
      missingContainer.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      state.missing = val;
      chip.classList.add('active');
      checkToggle.textContent = '检查: ' + chip.textContent + ' ✕';
    }
    applyFilters();
  });

  // ─── Render Cards ───
  function getDifficultyBadge(project) {
    const d = project.difficulty?.[0];
    if (!d) return '';
    const cls = d.startsWith('引擎') ? 'UE' : d;
    return `<span class="card-badge badge-${cls}">${d}</span>`;
  }

  function renderContent() {
    const content = $('#content');
    content.innerHTML = '';

    DB.games.forEach((game, gi) => {
      const section = document.createElement('section');
      section.className = 'game-section';
      section.dataset.game = game.name;
      section.dataset.index = gi % 8;

      const header = document.createElement('div');
      header.className = 'game-header';
      header.innerHTML = `
        <div class="game-indicator"></div>
        <h2 class="game-name">${game.name}</h2>
        <span class="game-count">${game.projects.length} 视频</span>
      `;
      section.appendChild(header);

      const grid = document.createElement('div');
      grid.className = 'card-grid';

      game.projects.forEach((p) => {
        const card = document.createElement('div');
        card.className = 'card';
        card.dataset.recordId = p.recordId;
        card.dataset.game = game.name;
        card.dataset.categories = (p.categories || []).join(',');
        card.dataset.difficulty = (p.difficulty || []).join(',');
        card.dataset.production = (p.production || []).join(',');
        card.dataset.project = (p.project || '').toLowerCase();
        const missingList = [];
        if (!p.localVideo && !p.video) missingList.push('video');
        if (!p.cover) missingList.push('cover');
        if (!p.categories || !p.categories.length) missingList.push('category');
        if (!p.difficulty || !p.difficulty.length) missingList.push('difficulty');
        card.dataset.missing = missingList.join(',');

        const thumbContent = p.cover
          ? `<img src="${p.cover}" alt="${p.project}" loading="lazy" />`
          : `<div class="card-thumb--empty">暂无封面</div>`;

        const hasVideo = !!(p.localVideo || p.video || p.bilibiliUrl || p.youtubeUrl);
        const playIcon = hasVideo ? '<div class="card-play-icon"></div>' : '';

        const categoryTags = (p.categories || []).map(c =>
          `<span class="card-tag">${c}</span>`
        ).join('');

        card.innerHTML = `
          <div class="card-thumb">
            ${thumbContent}
            ${playIcon}
          </div>
          <div class="card-info">
            <div class="card-title" title="${p.project}">${p.project}</div>
            <div class="card-sub">
              ${categoryTags}
              ${p.duration ? `<span class="card-duration">${p.duration}</span>` : ''}
            </div>
          </div>
        `;

        const videoSrcForHover = resolveVideoSrc(p.localVideo) || p.video;
        if (videoSrcForHover) {
          let hoverTimer;
          let hoverActive = false;

          card.addEventListener('mouseenter', () => {
            hoverActive = true;
            hoverTimer = setTimeout(() => {
              if (!hoverActive) return;
              const thumb = card.querySelector('.card-thumb');
              const img = thumb.querySelector('img');
              if (img) img.style.display = 'none';

              const vid = document.createElement('video');
              vid.className = 'card-hover-video';
              vid.muted = true;
              vid.loop = true;
              vid.playsInline = true;
              vid.src = videoSrcForHover;
              thumb.appendChild(vid);
              vid.play().catch(() => {});
            }, 400);
          });

          card.addEventListener('mouseleave', () => {
            hoverActive = false;
            clearTimeout(hoverTimer);
            const thumb = card.querySelector('.card-thumb');
            const vid = thumb.querySelector('.card-hover-video');
            if (vid) {
              vid.pause();
              vid.src = '';
              vid.remove();
            }
            const img = thumb.querySelector('img');
            if (img) img.style.display = '';
          });
        }

        card.addEventListener('click', () => openModal(p));
        grid.appendChild(card);
      });

      section.appendChild(grid);
      content.appendChild(section);
    });
  }

  // ─── Apply Filters ───
  function applyFilters() {
    $$('.game-section').forEach(section => {
      const gameName = section.dataset.game;
      if (state.game && gameName !== state.game) {
        section.classList.add('hidden');
        return;
      }
      section.classList.remove('hidden');

      const cards = section.querySelectorAll('.card');
      let visibleCount = 0;

      cards.forEach(card => {
        let show = true;

        if (state.category) {
          const cats = card.dataset.categories.split(',');
          if (!cats.includes(state.category)) show = false;
        }
        if (state.difficulty) {
          const diffs = card.dataset.difficulty.split(',');
          if (!diffs.includes(state.difficulty)) show = false;
        }
        if (state.production) {
          const prods = card.dataset.production.split(',');
          if (!prods.includes(state.production)) show = false;
        }
        if (state.search) {
          if (!card.dataset.project.includes(state.search)) show = false;
        }
        if (state.missing) {
          const m = card.dataset.missing || '';
          if (!m.split(',').includes(state.missing)) show = false;
        }

        card.classList.toggle('hidden', !show);
        if (show) visibleCount++;
      });

      const countEl = section.querySelector('.game-count');
      if (countEl) countEl.textContent = `${visibleCount} 视频`;

      if (visibleCount === 0 && !state.game) {
        section.classList.add('hidden');
      }
    });
  }

  // ─── Modal ───
  const overlay = $('#modal-overlay');
  const modalClose = $('#modal-close');

  function openModal(project) {
    const mediaEl = $('#modal-media');
    const videoSrc = resolveVideoSrc(project.localVideo) || project.video;
    const modal = $('#modal');
    modal.classList.remove('modal--portrait');

    if (videoSrc) {
      mediaEl.innerHTML = `<video controls playsinline preload="auto" poster="${project.cover || ''}"><source src="${videoSrc}" type="video/mp4"></video>`;
      const vid = mediaEl.querySelector('video');
      vid.addEventListener('loadedmetadata', () => {
        if (vid.videoHeight > vid.videoWidth) {
          modal.classList.add('modal--portrait');
        }
      });
      vid.play().catch(() => {});
    } else if (project.cover) {
      mediaEl.innerHTML = `<img src="${project.cover}" alt="${project.project}" />`;
    } else {
      mediaEl.innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#5a6480">暂无媒体</div>';
    }

    $('#modal-title').textContent = project.project;

    const meta = $('#modal-meta');
    const metaItems = [];
    if (project.game) metaItems.push(`<span class="modal-meta-item"><span class="meta-label">游戏</span> ${project.game}</span>`);
    if (project.quarter) metaItems.push(`<span class="modal-meta-item"><span class="meta-label">季度</span> ${project.quarter}</span>`);
    if (project.duration) metaItems.push(`<span class="modal-meta-item"><span class="meta-label">时长</span> ${project.duration}</span>`);
    if (project.cycle) metaItems.push(`<span class="modal-meta-item"><span class="meta-label">周期</span> ${project.cycle}</span>`);
    meta.innerHTML = metaItems.join('');

    const tags = $('#modal-tags');
    const tagHtml = [];
    (project.categories || []).forEach(c => tagHtml.push(`<span class="modal-tag modal-tag--category">${c}</span>`));
    (project.difficulty || []).forEach(d => tagHtml.push(`<span class="modal-tag modal-tag--difficulty">${d}</span>`));
    (project.production || []).forEach(p => tagHtml.push(`<span class="modal-tag modal-tag--production">${p}</span>`));
    tags.innerHTML = tagHtml.join('');

    const links = $('#modal-links');
    const linkHtml = [];
    if (project.bilibiliUrl) linkHtml.push(`<a class="modal-link modal-link--bilibili" href="${project.bilibiliUrl}" target="_blank" rel="noopener">B站观看</a>`);
    if (project.youtubeUrl) linkHtml.push(`<a class="modal-link modal-link--youtube" href="${project.youtubeUrl}" target="_blank" rel="noopener">YouTube</a>`);
    links.innerHTML = linkHtml.join('');

    const details = $('#modal-details');
    const detailItems = [];
    if (project.deliveryDate) detailItems.push(`<div class="detail-item"><span class="detail-label">交付时间</span><span class="detail-value">${project.deliveryDate}</span></div>`);
    details.innerHTML = detailItems.join('');

    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function closeModal() {
    overlay.classList.remove('open');
    document.body.style.overflow = '';
    const video = overlay.querySelector('video');
    if (video) video.pause();
  }

  modalClose.addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // ─── Back to Top ───
  const btt = $('#back-to-top');
  window.addEventListener('scroll', () => {
    btt.classList.toggle('visible', window.scrollY > 400);
  }, { passive: true });
  btt.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // ─── Init ───
  renderStats();
  renderUpdateLog();
  renderFilters();
  renderContent();
  updateMissingLabels();
})();
