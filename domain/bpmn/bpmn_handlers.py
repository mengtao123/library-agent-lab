# -*- coding: utf-8 -*-
"""把 borrow_book.bpmn 里的每个"任务"节点绑定到真实动作(调微服务 / RAG)。
这就是 BPMN 与系统的"接线":流程图的节点 id ←→ 这里的处理器函数。"""
import os
from infrastructure.tools import get_reader, get_book, borrow_book, get_records
from domain.rag.rag import retrieve

BPMN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "flows", "borrow_book.bpmn")


# ============================================================
# 处理器函数：每个函数对应 BPMN 图里的一个节点
# ============================================================

def h_get_reader(ctx):
    """Task_GetReader：查询读者信息"""
    reader_id = ctx.get("reader_id", "R001")
    result = get_reader(reader_id)
    if "error" in result:
        ctx["reader_error"] = result["error"]
        ctx["reader_valid"] = False
        return f"❌ 查询读者失败：{result['error']}"
    ctx["reader"] = result
    ctx["reader_valid"] = result.get("is_valid", False)
    ctx["reader_name"] = result.get("name", "")
    ctx["borrowed_count"] = result.get("borrowed_count", 0)
    ctx["max_borrow"] = result.get("max_borrow", 5)
    ctx["fees"] = result.get("fees", 0)
    return f"✅ {result['name']}（{reader_id}），已借{result.get('borrowed_count', 0)}本，状态：{'可借' if result.get('is_valid') else '不可借'}"


def h_get_book(ctx):
    """Task_GetBook：查询书籍状态"""
    book_id = ctx.get("book_id", "B001")
    result = get_book(book_id)
    if "error" in result:
        ctx["book_error"] = result["error"]
        ctx["available"] = False
        return f"❌ 查询书籍失败：{result['error']}"
    ctx["book"] = result
    ctx["available"] = (result.get("status") == "在馆")
    ctx["book_title"] = result.get("title", "")
    ctx["book_status"] = result.get("status", "未知")
    ctx["location"] = result.get("location", "")
    return f"✅ 《{result['title']}》（{book_id}），状态：{result.get('status', '未知')}，位置：{result.get('location', '未知')}"


def h_notify_denied(ctx):
    """Task_NotifyDenied：通知读者不可借"""
    name = ctx.get("reader_name", "该读者")
    fees = ctx.get("fees", 0)
    borrowed = ctx.get("borrowed_count", 0)
    max_borrow = ctx.get("max_borrow", 5)

    if fees > 10:
        reason = f"欠费{fees}元"
    elif borrowed >= max_borrow:
        reason = f"已借{borrowed}本，达到上限{max_borrow}本"
    else:
        reason = "读者状态异常"

    ctx["final"] = f"❌ {name}不可借书，原因：{reason}。请处理后再试。"
    return ctx["final"]


def h_borrow_book(ctx):
    """Task_BorrowBook：执行借书"""
    reader_id = ctx.get("reader_id", "R001")
    book_id = ctx.get("book_id", "B001")
    result = borrow_book(reader_id, book_id)
    if "error" in result:
        ctx["final"] = f"❌ 借书失败：{result['error']}"
        return ctx["final"]
    ctx["record_id"] = result.get("record_id")
    ctx["final"] = f"✅ 借书成功！记录ID：{result.get('record_id')}"
    return ctx["final"]


def h_notify_wait(ctx):
    """Task_NotifyWait：通知读者等待/预约"""
    title = ctx.get("book_title", "该书")
    ctx["final"] = f"📋 《{title}》目前不在馆，已为您登记预约，到馆后将通知您。"
    return ctx["final"]


# ============================================================
# 处理器注册表：key = 节点上的 delegateExpression 名字
# ============================================================

HANDLERS = {
    "h_get_reader": h_get_reader,
    "h_get_book": h_get_book,
    "h_notify_denied": h_notify_denied,
    "h_borrow_book": h_borrow_book,
    "h_notify_wait": h_notify_wait,
}


# ============================================================
# 运行 BPMN 流程
# ============================================================

def run_borrow_process(reader_id, book_id, user_id="u001"):
    """执行借书 BPMN 流程，返回 (最终答复, 执行轨迹列表)"""
    from domain.bpmn.bpmn_engine import run_bpmn

    trace = []
    ctx = {
        "reader_id": reader_id,
        "book_id": book_id,
        "user_id": user_id
    }

    run_bpmn(
        BPMN_FILE,
        HANDLERS,
        ctx,
        log=lambda s: trace.append("[BPMN] " + s)
    )

    return ctx.get("final", "(流程未产生结果)"), trace