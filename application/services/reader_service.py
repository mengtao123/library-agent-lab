# -*- coding: utf-8 -*-
"""读者微服务(端口 8001)。
契约:
  GET /readers/{reader_id} -> 读者信息 | 404"""
import json
import sys
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure.data import READERS

PORT = 8001


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        m = re.match(r"/readers/(\w+)$", self.path)
        if m:
            reader = READERS.get(m.group(1))
            if reader:
                return self._send(200, reader)
            return self._send(404, {"error": "读者不存在"})
        self._send(404, {"error": "未知路径"})


if __name__ == "__main__":
    print(f"[reader-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()