/**
 * 从飞书多维表格拉取「小镇_寻鲸季过场动画」任务数据，写入 TaskBoard/taskboard-db.json
 *
 * 用法：
 *   node tools/build_taskboard.mjs
 *
 * 需要环境变量：
 *   FEISHU_APP_ID      飞书应用 App ID
 *   FEISHU_APP_SECRET  飞书应用 App Secret
 *
 * 也可以直接在脚本顶部硬编码（仅内网使用）。
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// ── 飞书配置 ──────────────────────────────────────────────
const APP_TOKEN = 'SFpqbX6Zda0cRssqqLEcp7Ranmh';
const TABLE_ID  = 'tblTUjW19PAj3OtA';
const PROJECT   = '小镇_寻鲸季过场动画';
const BASE_URL  = 'https://open.feishu.cn/open-apis';

const APP_ID     = process.env.FEISHU_APP_ID     || '';
const APP_SECRET = process.env.FEISHU_APP_SECRET || '';

// ── 获取 Tenant Access Token ──────────────────────────────
async function getTenantToken() {
  const res = await fetch(`${BASE_URL}/auth/v3/tenant_access_token/internal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ app_id: APP_ID, app_secret: APP_SECRET }),
  });
  const data = await res.json();
  if (data.code !== 0) throw new Error(`获取 token 失败: ${data.msg}`);
  return data.tenant_access_token;
}

// ── 搜索记录 ──────────────────────────────────────────────
async function searchRecords(token) {
  const url = `${BASE_URL}/bitable/v1/apps/${APP_TOKEN}/tables/${TABLE_ID}/records/search?page_size=100`;
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      filter: {
        conjunction: 'and',
        conditions: [
          { field_name: '重要紧急程度', operator: 'is', value: [PROJECT] },
        ],
      },
    }),
  });
  const data = await res.json();
  if (data.code !== 0) throw new Error(`搜索记录失败: ${data.msg}`);
  return data.data.items || [];
}

// ── 日期格式化 ────────────────────────────────────────────
function msToDate(ms) {
  if (!ms) return null;
  return new Date(ms).toISOString().slice(0, 10);
}

function extractText(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  if (Array.isArray(field)) return field.map(f => f.text || '').join('');
  return String(field);
}

// ── 转换为本地数据结构 ────────────────────────────────────
function transformRecords(items) {
  return items.map(item => {
    const f = item.fields;
    const assigneeInfo = Array.isArray(f['任务执行人']) ? f['任务执行人'][0] : null;
    const parentLinks = f['父记录']?.link_record_ids;

    return {
      id: item.record_id,
      title: extractText(f['任务描述']),
      assignee: assigneeInfo?.name || '',
      email: assigneeInfo?.email || '',
      status: f['进展'] || '',
      startDate: msToDate(f['开始日期']),
      dueDate: msToDate(f['预计完成日期']),
      completedDate: msToDate(f['实际完成日期']),
      isDelayed: extractText(f['是否延期']?.value).includes('延期'),
      parentId: parentLinks?.length ? parentLinks[0] : null,
    };
  });
}

// ── 补充 children 字段 ────────────────────────────────────
function buildTree(tasks) {
  const map = new Map(tasks.map(t => [t.id, t]));
  for (const t of tasks) {
    if (!t.parentId) t.children = [];
  }
  for (const t of tasks) {
    if (t.parentId && map.has(t.parentId)) {
      const parent = map.get(t.parentId);
      if (!parent.children) parent.children = [];
      parent.children.push(t.id);
    }
  }
  return tasks;
}

// ── 主流程 ────────────────────────────────────────────────
async function main() {
  console.log('🔑 获取飞书 Tenant Access Token …');
  const token = await getTenantToken();

  console.log('📥 拉取任务记录 …');
  const rawItems = await searchRecords(token);
  console.log(`   共 ${rawItems.length} 条记录`);

  const tasks = buildTree(transformRecords(rawItems));

  const payload = {
    meta: {
      project: PROJECT,
      source: '飞书多维表格',
      sourceUrl: `https://xd.feishu.cn/base/${APP_TOKEN}?table=${TABLE_ID}`,
      appToken: APP_TOKEN,
      tableId: TABLE_ID,
      generatedAt: new Date().toISOString(),
      totalTasks: tasks.length,
    },
    tasks,
  };

  const outPath = path.resolve(__dirname, '..', 'TaskBoard', 'taskboard-db.json');
  await fs.mkdir(path.dirname(outPath), { recursive: true });
  await fs.writeFile(outPath, JSON.stringify(payload, null, 2), 'utf8');

  // 同时输出 JS 版本，方便 file:// 协议直接加载
  const jsPath = outPath.replace(/\.json$/i, '.data.js');
  const jsContent = `// 自动生成，请勿手动编辑\nwindow.__TASKBOARD_DB__ = ${JSON.stringify(payload)};\n`;
  await fs.writeFile(jsPath, jsContent, 'utf8');

  console.log(`✅ 写入完成：${outPath}`);
  console.log(`✅ JS 版本：${jsPath}`);
}

main().catch(err => {
  console.error('❌ 构建失败:', err.message);
  process.exit(1);
});
