# -*- coding: utf-8 -*-
"""综合入口:护栏 → 编排(多Agent) → 输出脱敏,并打印可观测追踪。
这是把四个实验集成为一个端到端系统的"总闸"。"""
import time
import json
import sys
import io
import contextlib

from infrastructure.guardrails import input_guard, pii_mask
from application.agent import orchestrate
from domain.memory.memory import Memory


def serve(user_id, text, memory=None, verbose=True):
    t0 = time.time()
    ok, msg = input_guard(text)                      # ① 输入护栏
    if not ok:
        _trace(user_id, text, "BLOCKED", t0)
        return msg
    if memory:
        memory.add("user", text)
    result = orchestrate(text, memory=memory, verbose=verbose)  # ② 多Agent编排
    answer = pii_mask(result["answer"])              # ③ 输出脱敏
    if memory:
        memory.add("assistant", answer)
    _trace(user_id, text, result["intent"], t0)      # ④ 可观测追踪
    return answer


def _trace(user_id, text, intent, t0):
    log = {
        "user": user_id,
        "intent": intent,
        "latency_s": round(time.time() - t0, 3),
        "query": text[:30]
    }
    print("  TRACE " + json.dumps(log, ensure_ascii=False))


def serve_struct(user_id, text, memory=None):
    """供 Web 后端调用:返回 {reply, intent, trace, latency}。
    trace 捕获了路由与 ReAct 每一步,用于前端可视化 Agent 的工作过程。"""
    t0 = time.time()
    ok, msg = input_guard(text)
    if not ok:
        return {
            "reply": msg,
            "intent": "BLOCKED",
            "trace": "[输入护栏] 命中提示注入,已拦截",
            "latency": 0.0
        }
    if memory:
        memory.add("user", text)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = orchestrate(text, memory=memory, verbose=True)

    answer = pii_mask(result["answer"])
    if memory:
        memory.add("assistant", answer)

    return {
        "reply": answer,
        "intent": result["intent"],
        "trace": buf.getvalue().strip() or "(无工具调用)",
        "latency": round(time.time() - t0, 3)
    }