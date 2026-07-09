# -*- coding: utf-8 -*-
"""书籍微服务(端口 8002)。"""
import json
import sys
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from infrastructure.data import BOOKS
from infrastructure.metrics import track_request, get_metrics

PORT = 8002


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

        m = re.match(r"/books/(\w+)$", self.path)
        if m:
            book = BOOKS.get(m.group(1))
            if book:
                self._send(200, book)
            else:
                self._send(404, {"error": "书籍不存在"})
        else:
            self._send(404, {"error": "未知路径"})

        duration = time.time() - start
        track_request('book-service', 'GET', self.path, duration)

    def do_POST(self):
        start = time.time()

        m = re.match(r"/books/(\w+)/borrow$", self.path)
        if m:
            book = BOOKS.get(m.group(1))
            if not book:
                self._send(404, {"error": "书籍不存在"})
            elif book.get("status") == "已借出":
                self._send(400, {"error": "书籍已被借出"})
            else:
                book["status"] = "已借出"
                self._send(200, {
                    "book_id": m.group(1),
                    "status": "已借出",
                    "msg": "借书成功"
                })
        else:
            self._send(404, {"error": "未知路径"})

        duration = time.time() - start
        track_request('book-service', 'POST', self.path, duration)


if __name__ == "__main__":
    print(f"[book-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()