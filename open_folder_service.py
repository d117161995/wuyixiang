import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.parse

class OpenFolderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 允许跨域
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        
        # 解析路径
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'path' in params:
            folder_path = params['path'][0]
            if os.path.exists(folder_path):
                # Windows 下打开资源管理器并选中文件夹
                subprocess.Popen(f'explorer "{folder_path}"')
                self.wfile.write(b"Success")
            else:
                self.wfile.write(b"Path not found")
        else:
            self.wfile.write(b"No path provided")

def run(port=8081):
    server_address = ('', port)
    httpd = HTTPServer(server_address, OpenFolderHandler)
    print(f'本地文件夹打开服务已启动: http://localhost:{port}')
    print('请保持此窗口运行...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
