// Vite 开发服务器守护进程：自动重启，防止意外退出后 API 断开
// 用法：node start-vite.js
const { spawn } = require('child_process');
const path = require('path');

const RESTART_DELAY = 3000;
const CMD = 'npx vite --config vite.config.js --port 9097 --strictPort';

function ts() {
  return new Date().toLocaleString('zh-CN', { hour12: false });
}

function start() {
  console.log(`[${ts()}] 启动 Vite ...`);

  const child = spawn(CMD, {
    stdio: 'inherit',
    shell: true,
    cwd: __dirname,
    windowsHide: true,
  });

  child.on('exit', (code, signal) => {
    const reason = signal ? `信号 ${signal}` : `退出码 ${code}`;
    console.log(`\n[${ts()}] Vite 已停止 (${reason})，${RESTART_DELAY / 1000}s 后自动重启...`);
    setTimeout(start, RESTART_DELAY);
  });

  child.on('error', (err) => {
    console.error(`[${ts()}] 启动失败:`, err.message);
    setTimeout(start, RESTART_DELAY);
  });
}

start();
