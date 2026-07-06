# -*- coding: utf-8 -*-
"""Agent 的工具层：把微服务的 HTTP 接口包装成"工具"，并给出工具契约(schema)。
工具契约 = 服务契约的"面向模型版本"：描述写得越清楚，模型调用越准。"""
import os
import json
import requests

# 服务地址用环境变量配置（本地默认 localhost）
READER_URL = os.getenv("READER_URL", "http://localhost:8001")
BOOK_URL = os.getenv("BOOK_URL", "http://localhost:8002")
RECORD_URL = os.getenv("RECORD_URL", "http://localhost:8003")


# ============================================================
# 工具实现：每个工具调用一个微服务
# ============================================================

def get_reader(reader_id: str) -> dict:
    """查询读者信息"""
    try:
        return requests.get(f"{READER_URL}/readers/{reader_id}", timeout=3).json()
    except Exception as e:
        return {"error": f"读者服务不可用: {e}"}


def get_book(book_id: str) -> dict:
    """查询书籍信息"""
    try:
        return requests.get(f"{BOOK_URL}/books/{book_id}", timeout=3).json()
    except Exception as e:
        return {"error": f"书籍服务不可用: {e}"}


def borrow_book(reader_id: str, book_id: str) -> dict:
    """借书：创建借阅记录"""
    try:
        data = {"reader_id": reader_id, "book_id": book_id}
        return requests.post(
            f"{RECORD_URL}/records/borrow",
            json=data,
            timeout=3
        ).json()
    except Exception as e:
        return {"error": f"借书失败: {e}"}


def get_records(reader_id: str) -> dict:
    """查询某读者的所有借阅记录"""
    try:
        return requests.get(f"{RECORD_URL}/records/reader/{reader_id}", timeout=3).json()
    except Exception as e:
        return {"error": f"借阅记录服务不可用: {e}"}


# ============================================================
# 工具注册表：名字 → 函数
# ============================================================

FUNCS = {
    "get_reader": get_reader,
    "get_book": get_book,
    "borrow_book": borrow_book,
    "get_records": get_records,
}


# ============================================================
# 工具契约（OpenAI tools 规范）
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_reader",
            "description": "根据读者ID查询读者信息，包括姓名、院系、最大借阅数量、当前已借数量、是否有效、欠费金额",
            "parameters": {
                "type": "object",
                "properties": {
                    "reader_id": {
                        "type": "string",
                        "description": "读者ID，格式如 R001"
                    }
                },
                "required": ["reader_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_book",
            "description": "根据书籍ID查询书籍信息，包括书名、作者、ISBN、状态（在馆/已借出）、馆藏位置",
            "parameters": {
                "type": "object",
                "properties": {
                    "book_id": {
                        "type": "string",
                        "description": "书籍ID，格式如 B001"
                    }
                },
                "required": ["book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "borrow_book",
            "description": "借书。创建借阅记录，同时更新书籍状态为已借出，更新读者已借数量。需要读者可借且书籍在馆",
            "parameters": {
                "type": "object",
                "properties": {
                    "reader_id": {
                        "type": "string",
                        "description": "读者ID"
                    },
                    "book_id": {
                        "type": "string",
                        "description": "书籍ID"
                    }
                },
                "required": ["reader_id", "book_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_records",
            "description": "查询某读者的所有借阅记录，包括借阅日期、应还日期、状态（借出中/已逾期/已归还）",
            "parameters": {
                "type": "object",
                "properties": {
                    "reader_id": {
                        "type": "string",
                        "description": "读者ID"
                    }
                },
                "required": ["reader_id"]
            }
        }
    },
]