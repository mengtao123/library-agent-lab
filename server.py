# -*- coding: utf-8 -*-
"""
Web 后端(端口 8000)。一条命令启动整套可视化系统:
    python3 server.py
然后浏览器打开 http://localhost:8000 即可对话。

它做三件事:
  1) 在后台线程启动三个业务微服务(8001/8002/8003);
  2) GET  /            返回前端页面 web/index.html;
  3) POST /api/chat    接收 {message,user_id},调用 Agent,返回 {reply,intent,trace}。
零依赖:仅用 Python 标准库。
"""
import os
import sys
import json
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ---- 1. 后台启动业务微服务（图书馆版） ----
import application.services.reader_service as s_reader
import application.services.book_service as s_book
import application.services.record_service as s_record


def _start(mod):
    srv = HTTPServer(("127.0.0.1", mod.PORT), mod.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

print(">>> 正在启动微服务...")
for m in (s_reader, s_book, s_record):
    _start(m)
time.sleep(1.0)
print(">>> 微服务已就绪: 读者(8001) 书籍(8002) 借阅记录(8003)")

# ---- 2. 业务依赖(在微服务起来后再导入) ----
from application.app import serve_struct
from domain.memory.memory import Memory
from infrastructure.metrics import get_metrics

SESSIONS = {}  # user_id -> Memory(每个用户一份会话记忆)

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "interface", "web")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        data = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        start = time.time()
        
        # /metrics 路由
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(get_metrics())
            return

        path = "index.html" if self.path in ("/", "") else self.path.lstrip("/")
        fp = os.path.join(WEB_DIR, os.path.basename(path))
        if os.path.isfile(fp):
            ctype = "text/html; charset=utf-8" if fp.endswith(".html") else "text/plain; charset=utf-8"
            with open(fp, "rb") as f:
                self._send(200, f.read(), ctype)
        else:
            self._send(404, {"error": "not found"})
        
        duration = time.time() - start
        from infrastructure.metrics import track_request
        track_request('app', 'GET', self.path, duration)

    def do_POST(self):
        start = time.time()
        
        if self.path != "/api/chat":
            duration = time.time() - start
            from infrastructure.metrics import track_request
            track_request('app', 'POST', self.path, duration)
            return self._send(404, {"error": "unknown api"})
        
        n = int(self.headers.get("Content-Length", 0))
        try:
            req = json.loads(self.rfile.read(n) or "{}")
        except Exception:
            duration = time.time() - start
            from infrastructure.metrics import track_request
            track_request('app', 'POST', self.path, duration)
            return self._send(400, {"error": "bad json"})

        uid = req.get("user_id", "u001")
        msg = (req.get("message") or "").strip()
        if not msg:
            duration = time.time() - start
            from infrastructure.metrics import track_request
            track_request('app', 'POST', self.path, duration)
            return self._send(400, {"error": "empty message"})

        mem = SESSIONS.setdefault(uid, Memory())
        result = serve_struct(uid, msg, memory=mem)
        
        duration = time.time() - start
        from infrastructure.metrics import track_request
        track_request('app', 'POST', self.path, duration)
        
        self._send(200, result)


if __name__ == "__main__":
    print("=" * 56)
    print("  智能服务助理 已启动")
    print("  业务微服务: 8001 / 8002 / 8003 (后台)")
    print("  请用浏览器打开:  http://localhost:8000")
    print("  按 Ctrl+C 退出")
    print("=" * 56)
    HTTPServer(("0.0.0.0", 8000), Handler).serve_forever()