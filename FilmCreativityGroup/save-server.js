const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 9099;
const SAVE_PATH = path.join(__dirname, "ai-era-data.json");

const server = http.createServer((req, res) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") {
    res.writeHead(204);
    return res.end();
  }

  if (req.method === "POST" && req.url === "/save") {
    let body = "";
    req.on("data", chunk => body += chunk);
    req.on("end", () => {
      try {
        JSON.parse(body);
        fs.writeFileSync(SAVE_PATH, body, "utf-8");
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
        console.log(`[${new Date().toLocaleTimeString()}] 已保存 ai-era-data.json`);
      } catch (e) {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: e.message }));
      }
    });
    return;
  }

  res.writeHead(404);
  res.end("Not Found");
});

server.listen(PORT, () => {
  console.log(`保存服务已启动: http://localhost:${PORT}`);
  console.log(`文件保存到: ${SAVE_PATH}`);
  console.log("在 ai-era.html 本地页面点击「同步到HTTP」即可自动保存");
  console.log("按 Ctrl+C 停止服务");
});
