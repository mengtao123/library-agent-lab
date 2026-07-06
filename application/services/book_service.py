# -*- coding: utf-8 -*-
"""书籍微服务(端口 8002)。
契约:
  GET /books/{book_id}           -> 书籍信息 | 404
  POST /books/{book_id}/borrow   -> 借书（状态改为已借出）"""
import json
import sys
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure.data import BOOKS

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
        m = re.match(r"/books/(\w+)$", self.path)
        if m:
            book = BOOKS.get(m.group(1))
            if book:
                return self._send(200, book)
            return self._send(404, {"error": "书籍不存在"})
        self._send(404, {"error": "未知路径"})

    def do_POST(self):
        m = re.match(r"/books/(\w+)/borrow$", self.path)
        if m:
            book = BOOKS.get(m.group(1))
            if not book:
                return self._send(404, {"error": "书籍不存在"})
            if book.get("status") == "已借出":
                return self._send(400, {"error": "书籍已被借出"})
            book["status"] = "已借出"
            return self._send(200, {
                "book_id": m.group(1),
                "status": "已借出",
                "msg": "借书成功"
            })
        self._send(404, {"error": "未知路径"})


if __name__ == "__main__":
    print(f"[book-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()