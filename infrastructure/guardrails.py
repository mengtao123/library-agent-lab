# -*- coding: utf-8 -*-
"""护栏：输入(防注入)、授权(防越权)、输出(PII 脱敏)。"""
import re
from infrastructure.data import READERS, BORROW_RECORDS

# ============================================================
# 输入护栏：防提示注入
# ============================================================

INJECTION_KEYWORDS = [
    "忽略以上", "忽略之前", "忽略前面",
    "ignore previous", "ignore above", "ignore all",
    "你现在是", "扮演", "假装你是",
    "系统提示", "system prompt", "你是一个"
]


def input_guard(text: str):
    """输入护栏：拦截明显的提示注入。返回 (是否放行, 提示)。"""
    low = text.lower()
    for keyword in INJECTION_KEYWORDS:
        if keyword.lower() in low:
            return False, f"⚠️ 检测到可疑指令（疑似提示注入），已拦截。"
    return True, ""


# ============================================================
# 授权护栏：防越权
# ============================================================

def authz_guard_reader(user_id: str, reader_id: str):
    """授权护栏：校验读者是否属于当前用户（防越权查他人信息）。"""
    if user_id != reader_id:
        return False, f"⚠️ 无权操作该读者（{reader_id}不属于当前用户），已拒绝。"

    reader = READERS.get(reader_id)
    if not reader:
        return False, "未找到该读者。"
    return True, ""


def authz_guard_record(user_id: str, reader_id: str):
    """授权护栏：校验借阅记录是否属于当前用户。"""
    if user_id != reader_id:
        return False, f"⚠️ 无权查看该读者的借阅记录（{reader_id}不属于当前用户），已拒绝。"

    records = [r for r in BORROW_RECORDS.values() if r.get("reader_id") == reader_id]
    if not records:
        return False, "该读者暂无借阅记录。"
    return True, ""


# ============================================================
# 输出护栏：PII 脱敏
# ============================================================

def pii_mask(text: str) -> str:
    """输出护栏：手机号脱敏。"""
    text = re.sub(r"(1[3-9]\d)\d{4}(\d{4})", r"\1****\2", text or "")
    text = re.sub(r"(\d{6})\d{8}(\d{4})", r"\1********\2", text or "")
    text = re.sub(r"([a-zA-Z0-9._%+-]{2})[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", r"\1***@\2", text or "")
    return text