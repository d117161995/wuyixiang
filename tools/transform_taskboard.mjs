/**
 * 将飞书原始数据转换为 TaskBoard 数据库
 * 用法：node tools/transform_taskboard.mjs
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const RAW_PATH = process.argv[2] || path.resolve(__dirname, '..', 'TaskBoard', '_raw_feishu.json');
const OUT_PATH = path.resolve(__dirname, '..', 'TaskBoard', 'taskboard-db.json');

const raw = JSON.parse(await fs.readFile(RAW_PATH, 'utf8'));
const items = raw.items || raw;

function msToDate(ms) {
  if (!ms) return null;
  return new Date(ms).toISOString().slice(0, 10);
}

function extractText(field) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  if (Array.isArray(field)) return field.map(f => f.text || '').join('').trim();
  return String(field);
}

const tasks = items.map(item => {
  const f = item.fields;
  const assigneeInfo = Array.isArray(f['任务执行人']) ? f['任务执行人'][0] : null;
  const parentLinks = f['父记录']?.link_record_ids;
  const delayText = f['是否延期']?.value;

  return {
    id: item.record_id,
    title: extractText(f['任务描述']) || '(无描述)',
    assignee: assigneeInfo?.name || '',
    email: assigneeInfo?.email || '',
    project: f['重要紧急程度'] || '未分类',
    status: f['进展'] || '未知',
    startDate: msToDate(f['开始日期']),
    dueDate: msToDate(f['预计完成日期']),
    completedDate: msToDate(f['实际完成日期']),
    isDelayed: extractText(delayText).includes('延期'),
    parentId: parentLinks?.length ? parentLinks[0] : null,
    reason: extractText(f['原因']),
  };
});

// 统计所有项目
const projectSet = new Set(tasks.map(t => t.project));
const projects = [...projectSet].sort();

const payload = {
  meta: {
    source: '飞书多维表格',
    sourceUrl: 'https://xd.feishu.cn/base/SFpqbX6Zda0cRssqqLEcp7Ranmh?table=tblTUjW19PAj3OtA',
    appToken: 'SFpqbX6Zda0cRssqqLEcp7Ranmh',
    tableId: 'tblTUjW19PAj3OtA',
    generatedAt: new Date().toISOString(),
    totalTasks: tasks.length,
    totalProjects: projects.length,
    projects,
  },
  tasks,
};

await fs.writeFile(OUT_PATH, JSON.stringify(payload, null, 2), 'utf8');

const jsPath = OUT_PATH.replace(/\.json$/i, '.data.js');
const jsContent = `// 自动生成，请勿手动编辑\nwindow.__TASKBOARD_DB__ = ${JSON.stringify(payload)};\n`;
await fs.writeFile(jsPath, jsContent, 'utf8');

console.log(`✅ 共 ${tasks.length} 条任务，${projects.length} 个项目`);
console.log(`   项目：${projects.join('、')}`);
console.log(`   输出：${OUT_PATH}`);
