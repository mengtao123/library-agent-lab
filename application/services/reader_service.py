# -*- coding: utf-8 -*-
"""读者微服务(端口 8001)。"""
import json
import sys
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from infrastructure.data import READERS
from infrastructure.metrics import track_request, get_metrics

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
        start = time.time()

        if self.path == "/metrics":
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(get_metrics())
            return

        m = re.match(r"/readers/(\w+)$", self.path)
        if m:
            reader = READERS.get(m.group(1))
            if reader:
                self._send(200, reader)
            else:
                self._send(404, {"error": "读者不存在"})
        else:
            self._send(404, {"error": "未知路径"})

        duration = time.time() - start
        track_request('reader-service', 'GET', self.path, duration)


if __name__ == "__main__":
    print(f"[reader-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()