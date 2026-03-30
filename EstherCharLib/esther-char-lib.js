const DB_URL = "./esther-char-db.json";
const qs = (s, root = document) => root.querySelector(s);

const state = {
  characters: [],
  selected: "",
  keyword: "",
};

function escapeHtml(t) {
  return String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

function showToast(msg, duration = 1800) {
  const el = qs("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.remove("show"), duration);
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.cssText = "position:fixed;left:-9999px";
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  showToast("已复制: " + text);
}

function resolveFileUrl(absPath) {
  if (!absPath) return "";
  const normalized = absPath.replace(/\\/g, "/");
  if (/^(https?:)?\/\//.test(normalized) || normalized.startsWith("data:") || normalized.startsWith("blob:")) {
    return normalized;
  }
  if (normalized.startsWith("./") || normalized.startsWith("../")) {
    return normalized;
  }
  if (window.location.protocol === "file:") {
    const segs = normalized.split("/").filter(Boolean);
    const encoded = segs.map((s, i) => (i === 0 && /:$/.test(s) ? s : encodeURIComponent(s))).join("/");
    return "file:///" + encoded;
  }
  const driveMatch = normalized.match(/^([A-Za-z]):\//);
  if (driveMatch) {
    const drive = driveMatch[1].toLowerCase();
    const rest = normalized.slice(3);
    const segs = rest.split("/").filter(Boolean);
    const encoded = segs.map(s => encodeURIComponent(s)).join("/");
    return "/" + drive + "-drive/" + encoded;
  }
  const segs = normalized.split("/").filter(Boolean);
  const encoded = segs.map(s => encodeURIComponent(s)).join("/");
  return "/local-files/" + encoded;
}

function charHasContent(char) {
  return (
    char.prodesign_game.images.length > 0 ||
    char.prodesign_film.images.length > 0 ||
    char.lookdev.videos.length > 0 ||
    char.lookdev.images.length > 0 ||
    !!char.mod.path ||
    (char.mod.fbxFiles && char.mod.fbxFiles.length > 0) ||
    !!char.tex.path ||
    !!char.rig.path
  );
}

function renderSidebar() {
  const list = qs("#charList");
  const kw = state.keyword.toLowerCase();
  const filtered = state.characters.filter(c =>
    !kw || c.id.toLowerCase().includes(kw) || c.name.toLowerCase().includes(kw)
    || (c.cn_name || "").toLowerCase().includes(kw)
    || (c.notes_episode || "").toLowerCase().includes(kw)
    || (c.notes_cn || "").toLowerCase().includes(kw)
    || (c.notes_en || "").toLowerCase().includes(kw)
  );

  function parseFA(fa) {
    if (!fa) return 0;
    const m = fa.match(/^(?:ss|pv)(\d+)(?:_(\d+))?/);
    return m ? parseInt(m[1]) * 100 + (m[2] ? parseInt(m[2]) : 0) : 0;
  }
  function getPrefix(id) {
    const m = id.match(/^c\d+_([A-Za-z_]+)/);
    if (!m) return id.toLowerCase();
    const parts = m[1].split(/(?=[A-Z])|_/).filter(Boolean);
    return parts[0].toLowerCase();
  }
  function advSort(list) {
    const byEp = new Map();
    for (const c of list) {
      const k = c.first_appear || "";
      if (!byEp.has(k)) byEp.set(k, []);
      byEp.get(k).push(c);
    }
    const epKeys = [...byEp.keys()].sort((a, b) => parseFA(b) - parseFA(a));
    const out = [];
    for (const ek of epKeys) {
      const g = byEp.get(ek);
      g.sort((a, b) => (b.create_time || "").localeCompare(a.create_time || ""));
      const result = [], inserted = new Set(), pfxMap = new Map();
      for (const c of g) {
        const pfx = getPrefix(c.id);
        if (!pfxMap.has(pfx)) pfxMap.set(pfx, []);
        pfxMap.get(pfx).push(c);
      }
      for (const c of g) {
        const pfx = getPrefix(c.id);
        if (inserted.has(pfx)) continue;
        inserted.add(pfx);
        for (const m of pfxMap.get(pfx)) result.push(m);
      }
      for (const c of result) out.push(c);
    }
    return out;
  }
  const groupA = advSort(filtered.filter(c => c.notes_role === "主角"));
  const groupB = advSort(filtered.filter(c => c.notes_role !== "主角"));

  function renderItem(c) {
    const active = c.id === state.selected ? "active" : "";
    const has = charHasContent(c);
    const cn = c.notes_cn ? `<span class="cn-name">${escapeHtml(c.notes_cn)}</span>` : "";
    const label = cn || escapeHtml(c.id);
    return `<div class="char-item ${active}" data-id="${escapeHtml(c.id)}"><span class="dot ${has ? "" : "empty"}"></span>${label}</div>`;
  }

  function renderGroup(label, items, groupKey) {
    if (!items.length) return "";
    const collapsed = state.collapsed && state.collapsed[groupKey];
    return `
      <div class="char-group">
        <div class="char-group-header${collapsed ? " collapsed" : ""}" data-group="${groupKey}">
          <span>${escapeHtml(label)} (${items.length})</span>
          <span class="group-arrow">▼</span>
        </div>
        <div class="char-group-body${collapsed ? " collapsed" : ""}">
          ${items.map(renderItem).join("")}
        </div>
      </div>`;
  }

  list.innerHTML = renderGroup("主角", groupA, "lead") + renderGroup("配角", groupB, "support");

  list.querySelectorAll(".char-group-header").forEach(hdr => {
    hdr.addEventListener("click", () => {
      const key = hdr.dataset.group;
      if (!state.collapsed) state.collapsed = {};
      state.collapsed[key] = !state.collapsed[key];
      hdr.classList.toggle("collapsed");
      hdr.nextElementSibling.classList.toggle("collapsed");
    });
  });

  list.querySelectorAll(".char-item").forEach(el => {
    el.addEventListener("click", () => {
      state.selected = el.dataset.id;
      renderSidebar();
      renderMain();
    });
  });

  qs("#charCount").textContent = state.characters.length + "个";
}

function renderVisualCard(title, images, isVideo = false, videos = []) {
  const mediaCount = images.length + videos.length;
  const countText = mediaCount > 0 ? `${mediaCount} 个` : "";

  let bodyHtml = "";
  if (videos.length === 0 && images.length === 0) {
    bodyHtml = `<div class="visual-card-body empty-body"><span class="empty-text">暂无资源</span></div>`;
  } else {
    let items = "";
    for (const v of videos) {
      const ext = v.split(".").pop().toLowerCase();
      if (ext === "mov") {
        items += `<div class="video-item"><div class="video-unsupported">
          <div class="icon">🎬</div>
          <div class="msg">浏览器不支持 .mov 格式，请用本地播放器打开</div>
          <div class="path">${escapeHtml(v)}</div>
          <button class="btn-copy-path" type="button" data-path="${escapeHtml(v)}">复制路径</button>
        </div></div>`;
      } else {
        const src = resolveFileUrl(v);
        items += `<div class="video-item"><video src="${escapeHtml(src)}#t=0.001" controls muted preload="auto"></video></div>`;
      }
    }
    const imgCount = images.length;
    const noVid = videos.length === 0;
    let sizeClass = "";
    if (imgCount === 1 && noVid) sizeClass = " single";
    else if (imgCount === 2 && noVid) sizeClass = " dual";
    for (const img of images) {
      const src = resolveFileUrl(img);
      items += `<div class="thumb-item${sizeClass}" data-src="${escapeHtml(src)}"><img src="${escapeHtml(src)}" loading="lazy" alt=""></div>`;
    }
    bodyHtml = `<div class="visual-card-body">${items}</div>`;
  }

  return `
    <div class="visual-card">
      <div class="visual-card-header">
        <span class="visual-card-title">${escapeHtml(title)}</span>
      </div>
      ${bodyHtml}
    </div>
  `;
}

function renderPathCard(title, filePath, fileTag) {
  const hasPath = !!filePath;
  const display = hasPath ? filePath : "暂无资源";
  const tagHtml = fileTag ? `<span class="file-tag">${escapeHtml(fileTag)}</span>` : "";
  return `
    <div class="file-card">
      <div class="file-card-title">${escapeHtml(title)}</div>
      <div class="file-path-row">
        ${tagHtml}
        <div class="file-path ${hasPath ? "" : "no-path"}" title="${escapeHtml(display)}">${escapeHtml(display)}</div>
        <button class="btn-copy" type="button" data-path="${escapeHtml(filePath || "")}" ${hasPath ? "" : "disabled"}>复制</button>
      </div>
    </div>`;
}

function renderModPathCard(title, filePath, fbxFiles) {
  const hasPath = !!filePath;
  const maDisplay = hasPath ? filePath : "暂无资源";
  const fbxList = Array.isArray(fbxFiles) ? fbxFiles : (fbxFiles ? [fbxFiles] : []);
  const fbxRowsHtml = fbxList.length
    ? fbxList.map(function (fp, i) {
        const fname = fp.split("/").pop();
        return `
          <div class="file-path-row" style="margin-bottom:4px">
            <span class="file-tag file-tag-fbx">FBX</span>
            <div class="file-path" title="${escapeHtml(fp)}">${escapeHtml(fname)}</div>
            <button class="btn-copy" type="button" data-path="${escapeHtml(fp)}">复制</button>
            <button class="btn-3d" type="button" data-fbx="${escapeHtml(fp)}" data-idx="${i}">查看</button>
          </div>`;
      }).join("")
    : `<div class="file-path-row"><span class="file-tag file-tag-fbx">FBX</span><div class="file-path no-path">暂无资源</div></div>`;

  return `
    <div class="file-card">
      <div class="file-card-title">${escapeHtml(title)}</div>
      <div class="file-path-row" style="margin-bottom:6px">
        <span class="file-tag">MA</span>
        <div class="file-path ${hasPath ? "" : "no-path"}" title="${escapeHtml(maDisplay)}">${escapeHtml(maDisplay)}</div>
        <button class="btn-copy" type="button" data-path="${escapeHtml(filePath || "")}" ${hasPath ? "" : "disabled"}>复制</button>
      </div>
      ${fbxRowsHtml}
    </div>`;
}

function renderViewer3D(fbxFiles) {
  const fbxList = Array.isArray(fbxFiles) ? fbxFiles : (fbxFiles ? [fbxFiles] : []);
  return `
    <div class="viewer-panel">
      <div class="inline-viewer" id="inlineViewer">
        <div class="inline-viewer-idle" id="inlineViewerIdle">
          ${fbxList.length ? "点击「查看」加载 3D 模型" : "暂无 FBX 模型"}
        </div>
        <div class="inline-viewer-progress" id="inlineViewerProgress" style="display:none">
          <div class="progress-bar"><div class="progress-fill" id="progressFill"></div></div>
          <span class="progress-text" id="progressText">0%</span>
        </div>
        <div class="inline-viewer-hint" style="display:none">左键旋转 · 滚轮缩放 · 右键平移</div>
      </div>
    </div>`;
}

function renderMain() {
  const main = qs("#mainContent");
  const char = state.characters.find(c => c.id === state.selected);

  if (!char) {
    main.innerHTML = `<div class="main-empty" id="emptyState"><div class="icon">📦</div><div class="text">请从左侧选择一个角色</div></div>`;
    return;
  }

  const titleParts = [];
  if (char.notes_cn) titleParts.push(char.notes_cn);
  if (char.notes_en) titleParts.push(char.notes_en);
  const titleText = titleParts.join(" - ");
  const roleTag = char.notes_role ? ` (${char.notes_role})` : "";
  const displayTitle = titleText ? `<span class="char-cn-name">${escapeHtml(titleText)}</span><span class="char-role-tag">${escapeHtml(roleTag)}</span>` : escapeHtml(char.id);
  main.innerHTML = `
    <div class="top-bar">
      <div class="char-title">${displayTitle}</div>
      <div class="char-base-path" title="点击复制根路径" data-copy="${escapeHtml(char.basePath)}">${escapeHtml(char.basePath)}</div>
    </div>

    <div class="visual-grid">
      <div class="visual-left">
        ${renderVisualCard(char.prodesign_game.label, char.prodesign_game.images)}
        ${renderVisualCard(char.prodesign_film.label, char.prodesign_film.images)}
      </div>
      <div class="visual-right">
        ${renderVisualCard(char.lookdev.label, [], true, char.lookdev.videos)}
      </div>
    </div>

    <div class="bottom-section">
      <div class="bottom-left">
        ${renderModPathCard(char.mod.label, char.mod.path, char.mod.fbxFiles)}
        ${renderPathCard(char.tex.label, char.tex.path, "MA")}
        ${renderPathCard(char.rig.label, char.rig.path, "MA")}
      </div>
      <div class="bottom-right">
        ${renderViewer3D(char.mod.fbxFiles)}
      </div>
    </div>
  `;

  main.querySelector(".char-base-path")?.addEventListener("click", () => {
    copyText(char.basePath);
  });

  main.querySelectorAll(".btn-copy").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = btn.dataset.path;
      if (!p) return;
      copyText(p);
      btn.classList.add("copied");
      btn.textContent = "已复制";
      setTimeout(() => { btn.classList.remove("copied"); btn.textContent = "复制"; }, 1500);
    });
  });

  main.querySelectorAll(".btn-3d").forEach(btn => {
    btn.addEventListener("click", async () => {
      const fbx = btn.dataset.fbx;
      const viewer = main.querySelector("#inlineViewer");
      if (!fbx || !viewer) return;

      main.querySelectorAll(".btn-3d").forEach(b => {
        b.disabled = false;
        b.textContent = "查看";
      });

      const idle = viewer.querySelector("#inlineViewerIdle");
      const progress = viewer.querySelector("#inlineViewerProgress");
      const hint = viewer.querySelector(".inline-viewer-hint");
      const progressFill = viewer.querySelector("#progressFill");
      if (idle) idle.style.display = "none";
      if (progress) progress.style.display = "flex";
      if (progressFill) { progressFill.style.width = "0%"; progressFill.style.background = ""; }
      if (hint) hint.style.display = "none";
      btn.disabled = true;
      btn.textContent = "加载中";

      let waited = 0;
      while (!window.__initInlineViewer && waited < 5000) {
        await new Promise(r => setTimeout(r, 100));
        waited += 100;
      }
      if (!window.__initInlineViewer) {
        btn.textContent = "加载失败";
        if (progress) { const t = progress.querySelector(".progress-text"); if (t) t.textContent = "模块加载失败"; }
        return;
      }
      window.__initInlineViewer(viewer, fbx, () => {
        btn.textContent = "已加载";
        if (hint) hint.style.display = "";
      });
    });
  });

  main.querySelectorAll(".btn-copy-path").forEach(btn => {
    btn.addEventListener("click", () => {
      const p = btn.dataset.path;
      if (!p) return;
      copyText(p);
      btn.textContent = "已复制";
      setTimeout(() => { btn.textContent = "复制路径"; }, 1500);
    });
  });

  main.querySelectorAll(".thumb-item").forEach(el => {
    el.addEventListener("click", () => openLightbox(el.dataset.src));
  });
}

function openLightbox(src) {
  const box = qs("#lightbox");
  const img = qs("#lightboxImg");
  if (!box || !img || !src) return;
  img.src = src;
  box.classList.add("show");
}

function closeLightbox() {
  const box = qs("#lightbox");
  const img = qs("#lightboxImg");
  box.classList.remove("show");
  img.src = "";
}

function applyDb(raw) {
  state.characters = Array.isArray(raw?.characters) ? raw.characters : [];
  const fuqiu = state.characters.find(c => c.id === "c051_Fuqiu");
  state.selected = fuqiu?.id || state.characters[0]?.id || "";
  renderSidebar();
  renderMain();
}

async function loadDatabase() {
  try {
    const res = await fetch(DB_URL + "?t=" + Date.now(), { cache: "no-store" });
    if (!res.ok) throw new Error(`${res.status}`);
    applyDb(await res.json());
    return;
  } catch {}
  if (window.__ESTHER_CHAR_DB__ && Array.isArray(window.__ESTHER_CHAR_DB__.characters)) {
    applyDb(window.__ESTHER_CHAR_DB__);
    return;
  }
  qs("#mainContent").innerHTML = `<div class="main-empty"><div class="icon">⚠️</div><div class="text">数据库加载失败</div></div>`;
}

(function init() {
  qs("#searchInput").addEventListener("input", e => {
    state.keyword = e.target.value.trim();
    renderSidebar();
  });

  qs("#lightboxClose").addEventListener("click", closeLightbox);
  qs("#lightbox").addEventListener("click", e => { if (e.target === qs("#lightbox")) closeLightbox(); });

  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeLightbox();
  });

  qs("#btnRefresh")?.addEventListener("click", async () => {
    const btn = qs("#btnRefresh");
    btn.disabled = true;
    btn.textContent = "⟳ 刷新中...";
    try {
      const res = await fetch(DB_URL + "?t=" + Date.now(), { cache: "no-store" });
      if (!res.ok) throw new Error(`${res.status}`);
      const raw = await res.json();
      const prevId = state.selected;
      applyDb(raw);
      if (prevId && state.characters.some(c => c.id === prevId)) {
        state.selected = prevId;
        renderSidebar();
        renderMain();
      }
      showToast("数据库已刷新，共 " + state.characters.length + " 个角色");
    } catch (e) {
      showToast("刷新失败: " + e.message, 3000);
    }
    btn.disabled = false;
    btn.textContent = "⟳ 刷新数据库";
  });

  document.addEventListener("volumechange", e => {
    if (e.target.tagName === "VIDEO" && !e.target.muted) {
      e.target.muted = true;
    }
  }, true);

  loadDatabase();
})();
