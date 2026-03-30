const net = require('net');
const http = require('http');
const fs = require('fs');
const path = require('path');
const { WebSocketServer } = require('ws');

const MAYA_HOST = '127.0.0.1';
const MAYA_PORT = 12345;
const HTTP_PORT = 7890;

// ── HTTP 静态文件服务 ──
const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
};

const httpServer = http.createServer((req, res) => {
    let filePath = req.url === '/' ? '/index.html' : req.url;
    filePath = path.join(__dirname, 'public', filePath);

    const ext = path.extname(filePath);
    const contentType = MIME[ext] || 'application/octet-stream';

    fs.readFile(filePath, (err, data) => {
        if (err) {
            res.writeHead(404);
            res.end('Not Found');
            return;
        }
        res.writeHead(200, { 'Content-Type': contentType });
        res.end(data);
    });
});

// ── WebSocket 服务 ──
const wss = new WebSocketServer({ server: httpServer });

let mayaConnected = false;

function sendToMaya(pythonCode) {
    return new Promise((resolve, reject) => {
        const client = new net.Socket();
        let result = '';

        client.connect(MAYA_PORT, MAYA_HOST, () => {
            mayaConnected = true;
            client.write(pythonCode + '\n');
        });

        client.on('data', data => {
            result += data.toString();
        });

        client.on('end', () => {
            resolve(result.trim());
        });

        client.on('error', err => {
            mayaConnected = false;
            reject(err);
        });

        client.on('close', () => {
            client.destroy();
        });

        setTimeout(() => {
            client.destroy();
            resolve(result.trim() || '(timeout - no response)');
        }, 5000);
    });
}

function broadcastStatus(data) {
    const msg = JSON.stringify(data);
    wss.clients.forEach(ws => {
        if (ws.readyState === 1) ws.send(msg);
    });
}

wss.on('connection', ws => {
    console.log('[WS] 浏览器已连接');
    ws.send(JSON.stringify({ type: 'status', connected: mayaConnected }));

    ws.on('message', async raw => {
        let msg;
        try {
            msg = JSON.parse(raw.toString());
        } catch {
            ws.send(JSON.stringify({ type: 'error', error: '无效的 JSON' }));
            return;
        }

        if (msg.type === 'exec') {
            try {
                const result = await sendToMaya(msg.code);
                ws.send(JSON.stringify({ type: 'result', id: msg.id, result }));
                mayaConnected = true;
                broadcastStatus({ type: 'status', connected: true });
            } catch (err) {
                mayaConnected = false;
                ws.send(JSON.stringify({ type: 'error', id: msg.id, error: err.message }));
                broadcastStatus({ type: 'status', connected: false });
            }
        }

        if (msg.type === 'ping') {
            try {
                await sendToMaya('print("pong")');
                mayaConnected = true;
                ws.send(JSON.stringify({ type: 'status', connected: true }));
            } catch {
                mayaConnected = false;
                ws.send(JSON.stringify({ type: 'status', connected: false }));
            }
        }
    });

    ws.on('close', () => console.log('[WS] 浏览器断开'));
});

// ── 启动 ──
httpServer.listen(HTTP_PORT, () => {
    console.log(`\n  Maya Bridge 已启动`);
    console.log(`  ─────────────────────────────────`);
    console.log(`  网页面板:  http://localhost:${HTTP_PORT}`);
    console.log(`  Maya 端口: ${MAYA_HOST}:${MAYA_PORT}`);
    console.log(`  ─────────────────────────────────\n`);
});
