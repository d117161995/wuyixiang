/**
 * 从 CGTeamwork (proj_eth) 查询 Cha 类型资产的中文名和缩略图
 * 输出: cgtw-asset-names.json + thumbnails/ 文件夹
 */

import fs from "node:fs";
import path from "node:path";
import { pipeline } from "node:stream/promises";
import { Readable } from "node:stream";

process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0";

const CGTW_HOST = "cgt-artstudio.xindong.com";
const BASE_URL = `https://${CGTW_HOST}`;
const API_URL = `${BASE_URL}/api.php`;
const ACCOUNT = "wuyixiang@xd.com";
const PASSWORD = "ares1121qqwq";

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1"));
const THUMB_DIR = path.join(SCRIPT_DIR, "thumbnails");

async function apiCall(controller, method, data = {}, token = "") {
  const payload = { controller, method, app: "api", ...data };
  const formBody = "data=" + encodeURIComponent(JSON.stringify(payload));
  const headers = { "Content-Type": "application/x-www-form-urlencoded" };
  if (token) headers["Cookie"] = `token=${token}`;
  const resp = await fetch(API_URL, { method: "POST", headers, body: formBody });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const result = await resp.json();
  if (result && result.code !== "1") {
    throw new Error(`CGTW error: ${JSON.stringify(result.data || result)}`);
  }
  return result?.data ?? result;
}

async function login() {
  console.log(`登录 ${CGTW_HOST} ...`);
  const data = await apiCall("account", "login", { account: ACCOUNT, password: PASSWORD, machine_key: "" });
  if (!data?.token) throw new Error("登录失败");
  console.log(`登录成功`);
  return data.token;
}

async function downloadImage(url, destPath, token) {
  try {
    const headers = {};
    if (token) headers["Cookie"] = `token=${token}`;
    const resp = await fetch(url, { headers });
    if (!resp.ok || !resp.body) return false;
    await pipeline(Readable.fromWeb(resp.body), fs.createWriteStream(destPath));
    return true;
  } catch { return false; }
}

async function main() {
  const token = await login();

  const DB = "proj_film";
  const MOD = "m_asset";

  console.log(`查询 ${DB}.${MOD} (type=Cha) ...`);
  const assets = await apiCall("info", "get_filter", {
    db: DB, module: MOD,
    sign_array: [`${MOD}.entity`, `${MOD}.cn_name`, `${MOD}.type`, `${MOD}.image`, `${MOD}.notes`, `${MOD}.status`, `${MOD}.first_appear`, `${MOD}.create_time`],
    sign_filter_array: [[`${MOD}.type`, "=", "Cha"]],
    order_sign_array: [`${MOD}.entity`],
    limit: "5000", start_num: "",
  }, token);

  if (!Array.isArray(assets) || !assets.length) {
    console.log("未查到 Cha 资产"); return;
  }
  console.log(`共 ${assets.length} 个 Cha 资产`);

  if (!fs.existsSync(THUMB_DIR)) fs.mkdirSync(THUMB_DIR, { recursive: true });

  const result = [];
  let dlCount = 0;
  for (const a of assets) {
    const entity = a[`${MOD}.entity`] || "";
    const cnName = a[`${MOD}.cn_name`] || "";
    const notesRaw = (a[`${MOD}.notes`] || "").trim();
    const imageRaw = a[`${MOD}.image`] || "";

    const notesParts = notesRaw.split("|").map(s => s.trim());
    const status = (a[`${MOD}.status`] || "").trim();
    const firstAppear = (a[`${MOD}.first_appear`] || "").trim();
    const createTime = (a[`${MOD}.create_time`] || "").trim();
    const entry = {
      entity,
      cn_name: cnName,
      status,
      first_appear: firstAppear,
      create_time: createTime,
      notes: notesRaw,
      notes_episode: notesParts[0] || "",
      notes_cn: notesParts[1] || "",
      notes_en: notesParts[2] || "",
      notes_role: notesParts[3] || "",
      thumbnail: "",
    };

    let imageUrl = "";
    if (imageRaw) {
      try {
        const parsed = JSON.parse(imageRaw);
        if (Array.isArray(parsed) && parsed.length) {
          imageUrl = parsed[0].max || parsed[0].min || "";
        }
      } catch {
        imageUrl = imageRaw;
      }
    }

    if (imageUrl) {
      if (!imageUrl.startsWith("http")) {
        imageUrl = `${BASE_URL}${imageUrl.startsWith("/") ? "" : "/"}${imageUrl}`;
      }
      const ext = path.extname(new URL(imageUrl).pathname) || ".png";
      const thumbName = `${entity}${ext}`;
      const thumbPath = path.join(THUMB_DIR, thumbName);

      if (fs.existsSync(thumbPath)) {
        entry.thumbnail = thumbName;
      } else {
        const ok = await downloadImage(imageUrl, thumbPath, token);
        if (ok) {
          entry.thumbnail = thumbName;
          dlCount++;
          if (dlCount % 20 === 0) console.log(`  已下载 ${dlCount} 张...`);
        }
      }
    }

    result.push(entry);
  }

  const outPath = path.join(SCRIPT_DIR, "cgtw-asset-names.json");
  fs.writeFileSync(outPath, JSON.stringify(result, null, 2), "utf-8");
  console.log(`\n完成: ${result.length} 个 Cha 资产, 下载 ${dlCount} 张缩略图`);
  console.log(`数据: ${outPath}`);
  console.log(`缩略图: ${THUMB_DIR}`);

  const withThumb = result.filter(r => r.thumbnail);
  console.log(`有缩略图: ${withThumb.length} / ${result.length}`);
}

main().catch(e => { console.error("错误:", e.message); process.exit(1); });
