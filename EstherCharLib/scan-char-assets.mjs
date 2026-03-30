#!/usr/bin/env node
/**
 * Node.js 版本的角色资产扫描脚本
 * 扫描 X:\projects2024\ETH\Asset\Cha 下所有角色目录
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CHA_ROOT = "X:\\projects2024\\ETH\\Asset\\Cha";
const OUTPUT_JSON = path.join(__dirname, "esther-char-db.json");
const OUTPUT_JS = path.join(__dirname, "esther-char-db.data.js");
const CGTW_NAMES_FILE = path.join(__dirname, "cgtw-asset-names.json");

const IMAGE_EXT = new Set([".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tga", ".tif", ".tiff", ".psd", ".exr"]);
const VIDEO_EXT = new Set([".mp4", ".mov", ".avi", ".wmv", ".webm", ".mkv", ".flv"]);
const MAYA_EXT = new Set([".ma", ".mb"]);
const FBX_EXT = new Set([".fbx"]);
const EXCLUDE_DIRS = new Set(["history", "metadata", "backup"]);

function walkDir(dir) {
  const results = [];
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return results;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (EXCLUDE_DIRS.has(entry.name.toLowerCase())) continue;
      results.push(...walkDir(fullPath));
    } else if (entry.isFile()) {
      results.push(fullPath);
    }
  }
  return results.sort();
}

function collectMedia(folder, extensions) {
  return walkDir(folder)
    .filter(f => extensions.has(path.extname(f).toLowerCase()))
    .map(f => f.replace(/\\/g, "/"));
}

function collectMayaFiles(folder) {
  return collectMedia(folder, MAYA_EXT);
}

function findMainMaya(folder, charId, suffix) {
  const files = collectMayaFiles(folder);
  if (files.length === 0) return "";
  const target = `${charId}_${suffix}.ma`.toLowerCase();
  for (const f of files) {
    if (path.basename(f).toLowerCase() === target) return f;
  }
  return files[0];
}

function scanCharacter(charDir) {
  const charId = path.basename(charDir);

  const prodesignGameImages = collectMedia(path.join(charDir, "Prodesign", "work"), IMAGE_EXT);
  const prodesignFilmImages = collectMedia(path.join(charDir, "Prodesign", "approved"), IMAGE_EXT);
  let lookdevVideos = collectMedia(path.join(charDir, "LookDev", "approved"), VIDEO_EXT);
  if (lookdevVideos.length > 1) {
    let latest = lookdevVideos[0];
    let latestMtime = fs.statSync(lookdevVideos[0].replace(/\//g, path.sep)).mtimeMs;
    for (let i = 1; i < lookdevVideos.length; i++) {
      const mt = fs.statSync(lookdevVideos[i].replace(/\//g, path.sep)).mtimeMs;
      if (mt > latestMtime) { latestMtime = mt; latest = lookdevVideos[i]; }
    }
    lookdevVideos = [latest];
  }
  const lookdevImages = collectMedia(path.join(charDir, "LookDev", "approved"), IMAGE_EXT);

  const modPath = findMainMaya(path.join(charDir, "MOD", "work"), charId, "mod");
  const texPath = findMainMaya(path.join(charDir, "TEX", "publish", "maya"), charId, "tex");
  const rigPath = findMainMaya(path.join(charDir, "RIG", "publish"), charId, "rig");

  const allFbxCandidates = [
    ...walkDir(path.join(charDir, "MOD", "work")),
    ...walkDir(path.join(charDir, "RIG", "work")),
  ].filter(f => FBX_EXT.has(path.extname(f).toLowerCase()));

  let allFbx = [];
  if (allFbxCandidates.length > 0) {
    let latest = allFbxCandidates[0];
    let latestMtime = fs.statSync(allFbxCandidates[0]).mtimeMs;
    for (let i = 1; i < allFbxCandidates.length; i++) {
      const mt = fs.statSync(allFbxCandidates[i]).mtimeMs;
      if (mt > latestMtime) { latestMtime = mt; latest = allFbxCandidates[i]; }
    }
    allFbx = [latest.replace(/\\/g, "/")];
  }

  return {
    id: charId,
    name: charId,
    basePath: charDir.replace(/\\/g, "/"),
    prodesign_game: { label: "2D游戏设计", images: prodesignGameImages },
    prodesign_film: { label: "2D影视设计", images: prodesignFilmImages },
    lookdev: { label: "3D影视设计（LookDev）", videos: lookdevVideos, images: lookdevImages },
    mod: { label: "模型", path: modPath, fbxFiles: allFbx },
    tex: { label: "材质", path: texPath },
    rig: { label: "绑定", path: rigPath },
  };
}

function loadCgtwNames() {
  if (!fs.existsSync(CGTW_NAMES_FILE)) return new Map();
  const data = JSON.parse(fs.readFileSync(CGTW_NAMES_FILE, "utf-8"));
  const map = new Map();
  for (const item of data) {
    map.set(item.entity, item);
  }
  return map;
}

function main() {
  if (!fs.existsSync(CHA_ROOT)) {
    console.log(`根目录不存在: ${CHA_ROOT}`);
    return;
  }

  const cgtwMap = loadCgtwNames();
  console.log(`CGTW 名称数据: ${cgtwMap.size} 条`);

  const charDirs = fs.readdirSync(CHA_ROOT, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => path.join(CHA_ROOT, d.name))
    .sort();

  console.log(`扫描到 ${charDirs.length} 个角色目录`);

  const characters = [];
  for (const charDir of charDirs) {
    const charId = path.basename(charDir);
    process.stdout.write(`  扫描: ${charId} ...`);
    const charData = scanCharacter(charDir);

    const cgtw = cgtwMap.get(charId);
    if (!cgtw || !cgtw.notes) {
      console.log(` [跳过 - 无自定义备注]`);
      continue;
    }

    charData.cn_name = cgtw.cn_name || "";
    charData.first_appear = cgtw.first_appear || "";
    charData.create_time = cgtw.create_time || "";
    charData.notes_episode = cgtw.notes_episode || "";
    charData.notes_cn = cgtw.notes_cn || "";
    charData.notes_en = cgtw.notes_en || "";
    charData.notes_role = cgtw.notes_role || "";

    characters.push(charData);

    const counts = [];
    const pg = charData.prodesign_game.images.length;
    const pf = charData.prodesign_film.images.length;
    const lv = charData.lookdev.videos.length;
    const li = charData.lookdev.images.length;
    const fbx = (charData.mod.fbxFiles || []).length;
    if (pg) counts.push(`2D游戏:${pg}`);
    if (pf) counts.push(`2D影视:${pf}`);
    if (lv) counts.push(`LookDev视频:${lv}`);
    if (li) counts.push(`LookDev图:${li}`);
    if (charData.mod.path) counts.push("MOD");
    if (fbx) counts.push(`FBX:${fbx}`);
    if (charData.tex.path) counts.push("TEX");
    if (charData.rig.path) counts.push("RIG");
    console.log(` [${counts.length ? counts.join(", ") : "暂无资源"}]`);
  }

  const db = {
    version: "1.0.0",
    project: "伊瑟 ETH",
    source: CHA_ROOT.replace(/\\/g, "/"),
    generatedAt: new Date().toISOString(),
    totalCharacters: characters.length,
    characters,
  };

  fs.writeFileSync(OUTPUT_JSON, JSON.stringify(db, null, 2), "utf-8");
  fs.writeFileSync(OUTPUT_JS, "window.__ESTHER_CHAR_DB__ = " + JSON.stringify(db, null, 2) + ";\n", "utf-8");

  console.log(`\n完成！共 ${characters.length} 个角色`);
  console.log(`JSON 数据库: ${OUTPUT_JSON}`);
  console.log(`JS 数据库:   ${OUTPUT_JS}`);
}

main();
