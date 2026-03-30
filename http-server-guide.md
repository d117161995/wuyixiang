# 使用 Nginx 解决 Mac 访问兼容性问题

通过 Nginx 将本地文件和网络共享资源发布为 HTTP 服务，彻底解决 `file://` 协议带来的权限限制（视频无法播放、路径无法跳转、跨盘图片不显示）。

## 1. 准备工作

1.  **下载 Nginx**:
    *   下载 Windows 版 Nginx: [http://nginx.org/en/download.html](http://nginx.org/en/download.html)
    *   解压到任意目录（例如 `C:\nginx`）。

2.  **应用配置文件**:
    *   将本项目根目录下的 `nginx.conf` 文件复制到 Nginx 的 `conf` 目录下，替换默认的 `nginx.conf`。
    *   **注意**: 确保 `nginx.conf` 里的路径 `Y:/tmp/WuYiXiang/...` 与你实际的挂载盘符一致。

## 2. 启动服务

1.  双击运行 `nginx.exe`。
2.  如果不确定是否启动，可以在任务管理器查看是否有 `nginx` 进程。

## 3. 访问地址

现在，所有人（包括 Mac 用户）都可以通过浏览器访问，无需挂载 Y 盘，也无需特殊配置：

*   **策划展示页**:  
    `http://<服务器IP>:8080/story/noodle-anime-plan.html`

*   **场景库**:  
    `http://<服务器IP>:8080/story/scene-library/index.html`

## 4. 优势

*   ✅ **视频播放**: HTTP 协议原生支持流式播放，Mac Safari 也能正常看视频。
*   ✅ **资产库跳转**: 相对路径链接在 HTTP 下完美工作，点击直接跳转。
*   ✅ **图片显示**: Nginx 负责读取 Y 盘文件并发送给浏览器，Mac 端无需挂载 SMB 共享，直接看图。
