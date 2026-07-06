# -*- coding: utf-8 -*-
"""
Agent 层：意图识别 + ReAct 多步 Agent
- detect_intent: 自然语言 → 结构化意图
- react_agent: 多步推理 + 工具调用
"""
import json
import re
from infrastructure.llm import client, chat, CHAT_MODEL
from infrastructure.tools import TOOLS, FUNCS


# ============================================================
# 意图识别
# ============================================================

INTENT_SYSTEM = """你是图书馆智能服务助手。判断用户意图，只输出 JSON。

intent 取值：借书 / 查书 / 查读者 / 查借阅记录 / 其他

示例：
用户："R001想借B001"
→ {"intent": "借书", "entities": {"reader_id": "R001", "book_id": "B001"}}

用户："三体在吗？"
→ {"intent": "查书", "entities": {"book_name": "三体"}}

用户："张三的借阅记录"
→ {"intent": "查借阅记录", "entities": {"reader_name": "张三"}}

不要输出多余文字，只输出 JSON。"""


def detect_intent(text: str) -> dict:
    """意图识别：自然语言 → 结构化 JSON"""
    try:
        msg = chat([
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": text}
        ], temperature=0, response_format={"type": "json_object"})
        return json.loads(msg.content)
    except Exception:
        return {"intent": "其他", "entities": {}}


# ============================================================
# 实体提取辅助函数
# ============================================================

def extract_ids(text: str) -> dict:
    """从文本中提取读者ID和书籍ID"""
    reader_id = None
    book_id = None

    r_match = re.search(r'R\d{3}', text)
    if r_match:
        reader_id = r_match.group()

    b_match = re.search(r'B\d{3}', text)
    if b_match:
        book_id = b_match.group()

    return {"reader_id": reader_id, "book_id": book_id}


# ============================================================
# Step 6: ReAct Agent
# ============================================================

PLAN_SYSTEM = """你是图书馆智能服务助理。帮助用户查书、查读者信息、查借阅记录、借书。

规则：
1. 先拆成多个步骤，每次只调用一个最必要的工具
2. 拿到结果后再判断下一步
3. 信息齐全后才综合回答
4. 不要编造未查到的信息

可用工具：
- get_reader: 查读者信息（姓名、院系、可借数量、是否有效）
- get_book: 查书籍信息（书名、作者、状态：在馆/已借出、位置）
- get_records: 查某读者的借阅记录
- borrow_book: 借书（需要 reader_id 和 book_id）

遇到模糊信息时，先查清再操作。"""


def react_agent(user_text: str, max_steps: int = 6, verbose: bool = True) -> str:
    """ReAct 多步 Agent：自主规划、调用工具、综合回答"""
    msgs = [{"role": "system", "content": PLAN_SYSTEM}]
    msgs.append({"role": "user", "content": user_text})

    for step in range(1, max_steps + 1):
        # 调用大模型
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=msgs,
            tools=TOOLS
        )
        choice = resp.choices[0]
        msg = choice.message

        # 打印大模型返回的原始消息（调试用）
        if verbose:
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    print(f"  [第{step}步] 模型决定调用 {tc.function.name}({tc.function.arguments})")
            else:
                print(f"  [第{step}步] 模型决定直接回答")

        # 将助手消息加入对话历史
        msgs.append(msg.model_dump() if hasattr(msg, "model_dump") else msg)

        # 如果没有工具调用，说明已生成最终回答
        if not msg.tool_calls:
            if verbose:
                print(f"  [第{step}步] 思考→信息已齐全，生成最终答复")
            return msg.content or ""

        # 执行工具调用
        for tc in msg.tool_calls:
            func_name = tc.function.name
            args = json.loads(tc.function.arguments)

            if verbose:
                print(f"  [第{step}步] 执行→调用 {func_name}({args})")

            # 调用工具函数（真正调微服务）
            result = FUNCS[func_name](**args)

            if verbose:
                print(f"           观察← {json.dumps(result, ensure_ascii=False)[:100]}")

            # 将工具结果加入对话历史
            msgs.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False)
            })

    return "(已达最大步数，请缩小问题范围)"


# ============================================================
# 实验三：多 Agent 编排（路由 + 专家）
# ============================================================

def router(text: str) -> str:
    """路由 Agent：判断用户意图，返回专家名称"""
    text_lower = text.lower()

    # ---- 优先级从高到低 ----

    # 1. 政策/规则相关（最高优先级）
    if re.search(r"规则|政策|逾期|丢失|赔偿|预约|能借几本|能借多少|最多借|可以借几本|借阅规则", text_lower):
        return "政策专家"

    # 2. 借阅记录相关
    if re.search(r"记录|借了|借过|借阅记录|借书记录", text_lower):
        return "记录专家"

    # 3. 询问能否借书 → 读者专家（不是真的要借书）
    if re.search(r"能借书|可以借书|能不能借书|可借", text_lower):
        return "读者专家"

    # 4. 借书相关（明确要借书）
    if re.search(r"想借|要借|帮我借|借一下|借书", text_lower):
        return "借书专家"

    # 5. 查书相关
    if re.search(r"查|查询|有没有|在馆|在吗|找|搜索|书|B\d{3}", text_lower):
        return "查书专家"

    # 6. 读者相关
    if re.search(r"读者|R\d{3}|张三|李四|王五", text_lower):
        return "读者专家"

    return "通用专家"


# ---- 专家实现 ----

def expert_borrow(text: str, ctx=None, verbose=False) -> str:
    """借书专家：处理借书请求（走 BPMN 流程）"""
    # 提取读者ID和书籍ID
    ids = extract_ids(text)
    reader_id = ids.get("reader_id")
    book_id = ids.get("book_id")

    # 如果没有ID，尝试从文本中提取姓名/书名
    if not reader_id:
        for name, rid in [("张三", "R001"), ("李四", "R002"), ("王五", "R003")]:
            if name in text:
                reader_id = rid
                break

    if not book_id:
        for title, bid in [("三体", "B001"), ("百年孤独", "B002"), ("算法导论", "B003"), ("人类简史", "B004")]:
            if title in text:
                book_id = bid
                break

    # 如果同时有读者ID和书籍ID → 走 BPMN 流程
    if reader_id and book_id:
        from domain.bpmn.bpmn_handlers import run_borrow_process
        final, trace = run_borrow_process(reader_id, book_id)
        if verbose:
            for line in trace:
                print("  " + line)
        return "【借书专家·BPMN流程】" + final

    # 如果只有读者ID，查读者信息
    if reader_id:
        from infrastructure.tools import get_reader
        result = get_reader(reader_id)
        if "error" in result:
            return f"【借书专家】❌ {result['error']}"
        status = "可借" if result.get("is_valid", False) else "不可借（可能欠费或已超限）"
        return f"【借书专家】👤 {result['name']}（{reader_id}），{result['department']}，已借{result.get('borrowed_count', 0)}本，状态：{status}，欠费：{result.get('fees', 0)}元。"

    # 如果只有书籍ID，查书籍信息
    if book_id:
        from infrastructure.tools import get_book
        result = get_book(book_id)
        if "error" in result:
            return f"【借书专家】❌ {result['error']}"
        return f"【借书专家】📖 {result['title']}（{book_id}），作者{result['author']}，状态：{result.get('status', '未知')}，位置：{result.get('location', '未知')}。"

    return "【借书专家】请提供读者ID和书籍ID，例如：R001想借B001，或提供姓名和书名，例如：张三想借三体"


def expert_query_book(text: str, ctx=None, verbose=False) -> str:
    """查书专家：查询书籍信息"""
    ids = extract_ids(text)
    book_id = ids.get("book_id")

    if not book_id:
        for title, bid in [("三体", "B001"), ("百年孤独", "B002"), ("算法导论", "B003"), ("人类简史", "B004")]:
            if title in text:
                book_id = bid
                break

    if book_id:
        from infrastructure.tools import get_book
        book = get_book(book_id)
        if "error" in book:
            return f"【查书专家】❌ {book['error']}"
        return f"【查书专家】📖 {book['title']}（{book_id}），作者{book['author']}，状态：{book.get('status', '未知')}，位置：{book.get('location', '未知')}。"

    return "【查书专家】请提供书名或书籍ID，例如：三体在吗？"


def expert_reader(text: str, ctx=None, verbose=False) -> str:
    """读者专家：查询读者信息"""
    ids = extract_ids(text)
    reader_id = ids.get("reader_id")

    if not reader_id:
        for name, rid in [("张三", "R001"), ("李四", "R002"), ("王五", "R003")]:
            if name in text:
                reader_id = rid
                break

    if reader_id:
        from infrastructure.tools import get_reader
        reader = get_reader(reader_id)
        if "error" in reader:
            return f"【读者专家】❌ {reader['error']}"
        status = "可借" if reader.get("is_valid", False) else "不可借（可能欠费或已超限）"
        return f"【读者专家】👤 {reader['name']}（{reader_id}），{reader['department']}，已借{reader.get('borrowed_count', 0)}本，状态：{status}，欠费：{reader.get('fees', 0)}元。"

    return "【读者专家】请提供读者姓名或ID，例如：查一下张三"


def expert_policy(text: str, ctx=None, verbose=False) -> str:
    """政策专家：检索图书馆规则政策"""
    from domain.rag.rag import retrieve
    results = retrieve(text, k=2)
    if results:
        return "【政策专家】📋 " + "；".join(results)
    return "【政策专家】未找到相关政策信息"


def expert_records(text: str, ctx=None, verbose=False) -> str:
    """记录专家：查询借阅记录"""
    ids = extract_ids(text)
    reader_id = ids.get("reader_id")

    if not reader_id:
        for name, rid in [("张三", "R001"), ("李四", "R002"), ("王五", "R003")]:
            if name in text:
                reader_id = rid
                break

    if reader_id:
        from infrastructure.tools import get_records
        records = get_records(reader_id)
        if "error" in records:
            return f"【记录专家】❌ {records['error']}"
        if not records:
            return f"【记录专家】📋 读者{reader_id}暂无借阅记录。"
        titles = []
        for r in records:
            book_id = r.get("book_id")
            from infrastructure.data import BOOKS
            book_info = BOOKS.get(book_id, {})
            titles.append(f"《{book_info.get('title', book_id)}》{r.get('status', '')}")
        return f"【记录专家】📋 共{len(records)}条记录：{'；'.join(titles)}。"

    return "【记录专家】请提供读者ID"


def expert_general(text: str, ctx=None, verbose=False) -> str:
    """通用专家：兜底"""
    return f"【通用专家】您好，我可以帮您查书、查读者、查借阅记录、借书或查询图书馆政策。您说：{text}"


# ---- 专家注册表 ----
EXPERTS = {
    "借书专家": expert_borrow,
    "查书专家": expert_query_book,
    "读者专家": expert_reader,
    "政策专家": expert_policy,
    "记录专家": expert_records,
    "通用专家": expert_general,
}


def orchestrate(text: str, memory=None, verbose: bool = True) -> dict:
    """编排：路由 → 分派专家"""
    if verbose:
        print(f"  [路由] 收到: {text}")

    # 路由判断
    expert_name = router(text)
    if verbose:
        print(f"  [路由] 分派给: {expert_name}")

    # 获取专家并执行
    expert = EXPERTS.get(expert_name, expert_general)
    answer = expert(text, verbose=verbose)

    return {"intent": expert_name, "answer": answer}