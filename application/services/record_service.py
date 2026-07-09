# -*- coding: utf-8 -*-
"""借阅记录微服务(端口 8003)。"""
import json
import sys
import os
import re
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from infrastructure.data import BORROW_RECORDS, BOOKS, READERS
from infrastructure.metrics import track_request, get_metrics

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
        start = time.time()

        if self.path == "/metrics":
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(get_metrics())
            return

        m = re.match(r"/records/reader/(\w+)$", self.path)
        if m:
            reader_id = m.group(1)
            records = [r for r in BORROW_RECORDS.values() if r.get("reader_id") == reader_id]
            if records:
                self._send(200, records)
            else:
                self._send(404, {"error": "该读者无借阅记录"})
        else:
            self._send(404, {"error": "未知路径"})

        duration = time.time() - start
        track_request('record-service', 'GET', self.path, duration)

    def do_POST(self):
        start = time.time()

        if self.path == "/records/borrow":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode("utf-8"))
                reader_id = data.get("reader_id")
                book_id = data.get("book_id")

                if not reader_id or not book_id:
                    self._send(400, {"error": "缺少 reader_id 或 book_id"})
                else:
                    reader = READERS.get(reader_id)
                    if not reader:
                        self._send(404, {"error": "读者不存在"})
                    elif not reader.get("is_valid", True):
                        self._send(400, {"error": "读者不可借（可能欠费或已超限）"})
                    else:
                        book = BOOKS.get(book_id)
                        if not book:
                            self._send(404, {"error": "书籍不存在"})
                        elif book.get("status") != "在馆":
                            self._send(400, {"error": "书籍不在馆，无法借阅"})
                        else:
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

                            self._send(200, {
                                "record_id": record_id,
                                "status": "借出中",
                                "msg": "借阅记录创建成功"
                            })
            except json.JSONDecodeError:
                self._send(400, {"error": "无效的 JSON 数据"})
        else:
            self._send(404, {"error": "未知路径"})

        duration = time.time() - start
        track_request('record-service', 'POST', self.path, duration)


if __name__ == "__main__":
    print(f"[record-service] 启动于 http://localhost:{PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()