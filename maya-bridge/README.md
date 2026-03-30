# Maya Bridge - 网页控制 Maya

通过浏览器远程控制 Maya，发送 Python 命令并实时查看结果。

## 架构

```
浏览器 ←─ WebSocket ─→ Node.js 服务 ←─ TCP ─→ Maya commandPort
```

## 快速开始

### 1. 安装依赖

```bash
cd maya-bridge
npm install
```

### 2. 在 Maya 中开启 commandPort

打开 Maya → Script Editor，粘贴运行 `maya_setup.py` 中的内容，或者直接执行：

```python
import maya.cmds as cmds
cmds.commandPort(name=':12345', sourceType='python')
```

### 3. 启动 Node.js 服务

```bash
npm start
```

### 4. 打开浏览器

访问 http://localhost:7890

## 文件结构

```
maya-bridge/
├── server.js          # Node.js 中间层（HTTP + WebSocket + TCP）
├── maya_setup.py      # Maya 端 commandPort 启动脚本
├── package.json
├── README.md
└── public/
    └── index.html     # 网页控制面板
```

## 配置

| 参数 | 默认值 | 文件 | 说明 |
|------|--------|------|------|
| `MAYA_PORT` | 12345 | server.js / maya_setup.py | Maya commandPort 端口 |
| `HTTP_PORT` | 7890 | server.js | 网页服务端口 |
| `MAYA_HOST` | 127.0.0.1 | server.js | Maya 主机地址 |

## 功能

- **代码编辑器**: 输入任意 Maya Python 代码，Ctrl+Enter 执行
- **快捷命令**: 一键创建对象、列出场景、保存文件等
- **场景信息**: 实时查看当前文件、对象数、帧范围、FPS
- **历史记录**: 点击可快速复用之前的命令
- **连接状态**: 实时显示 Maya 连接状态，自动重连

## 注意事项

- Maya 和 Node.js 服务需要在同一台机器上（或可互通网络）
- 修改端口后需要同时更新 `server.js` 和 `maya_setup.py`
- 如需跨机器使用，将 `MAYA_HOST` 改为 Maya 所在机器的 IP
