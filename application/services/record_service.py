# -*- coding: utf-8 -*-
"""借阅记录微服务(端口 8003)。
契约:
  GET /records/reader/{reader_id} -> 该读者的所有借阅记录 | 404
  POST /records/borrow            -> 创建借阅记录"""
import json
import sys
import os
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from infrastructure.data import BORROW_RECORDS, BOOKS, READERS

PORT = 8003


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
        m = re.match(r"/records/reader/(\w+)$", self.path)
        if m:
            reader_id = m.group(1)
            records = [r for r in BORROW_RECORDS.values() if r.get("reader_id") == reader_id]
            if records:
                return self._send(200, records)
            return self._send(404, {"error": "该读者无借阅记录"})
        self._send(404, {"error": "未知路径"})

    def do_POST(self):
        if self.path == "/records/borrow":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))
                reader_id = data.get("reader_id")
                book_id = data.get("book_id")

                if not reader_id or not book_id:
                    return self._send(400, {"error": "缺少 reader_id 或 book_id"})

                reader = READERS.get(reader_id)
                if not reader:
                    return self._send(404, {"error": "读者不存在"})

                if not reader.get("is_valid", True):
                    return self._send(400, {"error": "读者不可借（可能欠费或已超限）"})

                book = BOOKS.get(book_id)
                if not book:
                    return self._send(404, {"error": "书籍不存在"})

                if book.get("status") != "在馆":
                    return self._send(400, {"error": "书籍不在馆，无法借阅"})

                record_id = f"BR{len(BORROW_RECORDS) + 1:03d}"
                borrow_date = datetime.now().strftime("%Y-%m-%d")
                due_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

                new_record = {
                    "record_id": record_id,
                    "reader_id": reader_id,
                    "book_id": book_id,
                    "borrow_date": borrow_date,
                    "due_date": due_date,
                    "return_date": None,
                    "status": "借出中"
                }
                BORROW_RECORDS[record_id] = new_record

                reader["borrowed_count"] = reader.get("borrowed_count", 0) + 1
                book["status"] = "已借出"

                return self._send(200, {
                    "record_id": record_id,
                    "status": "借出中",
                    "msg": "借阅记录创建成功"
                })

            except json.JSONDecodeError:
                return self._send(400, {"error": "无效的 JSON 数据"})

        self._send(404, {"error": "未知路径"})


if __name__ == "__main__":
    print(f"[record-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()