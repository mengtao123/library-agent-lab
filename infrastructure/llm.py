# -*- coding: utf-8 -*-
"""
统一的大模型客户端。

设计要点(重要):
- 对外暴露与 OpenAI 完全一致的接口:client.chat.completions.create(model, messages, tools, ...)
  返回对象 .choices[0].message,message 有 .content 与 .tool_calls。
- 若环境变量里配置了 OPENAI_API_KEY,则使用真实的 OpenAI 兼容大模型(openai SDK)。
- 否则回退到 MockLLM —— 一个确定性的"教学桩",用规则模拟大模型的"意图判断/工具选择/
  生成回复",让整套系统在【无密钥、无网络】的情况下也能完整跑通、输出可复现。
  学生在自己电脑上 `export OPENAI_API_KEY=...` 后,同一套代码即调用真实模型,无需改动。

这正是工程上的"接口隔离":上层 Agent/编排逻辑只依赖接口,不关心背后是真模型还是桩。
"""
import os, re, json, uuid


def _load_dotenv():
    """无依赖加载同目录下的 .env(每行 KEY=VALUE),已存在的环境变量不覆盖。
    这就是配置大模型 API Key 的地方:把 .env.example 复制成 .env 并填入 key。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip('"').strip("'")
        if v:  # 空值不设置,避免空字符串误判为"已配置"
            os.environ.setdefault(k.strip(), v)


_load_dotenv()

CHAT_MODEL = os.getenv("CHAT_MODEL", "mock-llm")


# ----------------------------------------------------------------------
# 模拟 OpenAI 返回对象的最小数据结构
# ----------------------------------------------------------------------
class _Fn:
    def __init__(self, name, arguments): self.name = name; self.arguments = arguments


class _ToolCall:
    def __init__(self, name, args):
        self.id = "call_" + uuid.uuid4().hex[:8];
        self.type = "function"
        self.function = _Fn(name, json.dumps(args, ensure_ascii=False))


class _Msg:
    def __init__(self, content=None, tool_calls=None, role="assistant"):
        self.content = content;
        self.tool_calls = tool_calls or None;
        self.role = role

    def model_dump(self):
        d = {"role": self.role, "content": self.content or ""}
        if self.tool_calls:
            d["tool_calls"] = [{"id": tc.id, "type": "function",
                                "function": {"name": tc.function.name,
                                             "arguments": tc.function.arguments}}
                               for tc in self.tool_calls]
        return d


class _Choice:
    def __init__(self, m): self.message = m


class _Resp:
    def __init__(self, m): self.choices = [_Choice(m)]


def _norm(messages):
    """把 messages 里可能混入的对象统一成 dict,便于桩解析。"""
    out = []
    for m in messages:
        if isinstance(m, dict):
            out.append(m)
        elif hasattr(m, "model_dump"):
            out.append(m.model_dump())
        else:
            out.append({"role": getattr(m, "role", "assistant"),
                        "content": getattr(m, "content", "")})
    return out


# ----------------------------------------------------------------------
# MockLLM:确定性教学桩（图书馆版本）
# ----------------------------------------------------------------------
class _MockCompletions:
    def create(self, model=None, messages=None, tools=None,
               temperature=0, response_format=None, **kw):
        msgs = _norm(messages)
        sys_txt = " ".join(m.get("content", "") or "" for m in msgs if m.get("role") == "system")
        user_txt = " ".join(m.get("content", "") or "" for m in msgs if m.get("role") == "user")

        # 1) 路由:system 要求"只回一个词"
        if "只回一个词" in sys_txt or "只回复一个词" in sys_txt:
            return _Resp(_Msg(content=self._route(user_txt)))

        # 2) 摘要压缩:system/user 要求"压缩成要点"
        if "压缩成要点" in sys_txt + user_txt or "压缩成" in user_txt:
            return _Resp(_Msg(content=self._summarize(user_txt)))

        # 3) 评测打分:judge,要求输出 {"pass": ...}
        if response_format and '"pass"' in (sys_txt + user_txt):
            return _Resp(_Msg(content=self._judge(user_txt)))

        # 4) 意图识别:要求输出 {"intent": ...}（图书馆版）
        if response_format and ("意图" in sys_txt or '"intent"' in sys_txt):
            return _Resp(_Msg(content=self._intent_library(user_txt)))

        # 5) 工具调用 / ReAct:提供了 tools（图书馆版）
        if tools:
            last_user = next((m.get("content", "") for m in reversed(msgs)
                              if m.get("role") == "user"), user_txt)
            return self._tool_step_library(msgs, tools, last_user)

        # 6) 兜底:普通生成
        return _Resp(_Msg(content=self._final_answer_library(msgs, user_txt)))

    # ---- 路由（只回一个词，粗粒度） ----
    def _route(self, t):
        if re.search(r"借|借书|借阅|还|还书|续|续借", t):
            return "借还书"
        if re.search(r"查|查询|有没有|在馆|在吗|在哪|记录|借了|借过", t):
            return "查询"
        return "其他"

    # ---- 摘要（图书馆版） ----
    def _summarize(self, t):
        rid = "、".join(set(re.findall(r"R\d{3}", t)))
        bid = "、".join(set(re.findall(r"B\d{3}", t)))
        parts = []
        if rid: parts.append(f"涉及读者 {rid}")
        if bid: parts.append(f"涉及书籍 {bid}")
        return ";".join(parts) if parts else "用户进行了若干轮咨询。"

    # ---- 评测 ----
    def _judge(self, t):
        m_must = re.search(r"要点[:：]\s*(\[[^\]]*\])", t)
        m_ans = re.search(r"回答[:：]\s*(.+)", t, re.S)
        must, ans = [], ""
        if m_must:
            try:
                must = json.loads(m_must.group(1).replace("'", '"'))
            except Exception:
                must = re.findall(r"[\"']([^\"']+)[\"']", m_must.group(1))
        if m_ans: ans = m_ans.group(1)
        ok = all(str(x) in ans for x in must) if must else True
        return json.dumps({"pass": bool(ok)}, ensure_ascii=False)

    # ---- 意图识别（输出 JSON，细粒度） ----
    def _intent_library(self, t):
        # 优先级：先判断"记录" → "询问是否能借" → "借书" → "还书" → "查书" → "查读者"
        if re.search(r"记录|借了|借过|借阅记录", t):
            intent = "查借阅记录"
        elif re.search(r"能借|可以借|可借|能不能借|能借书", t):
            intent = "查读者"
        elif re.search(r"借|借书", t):
            intent = "借书"
        elif re.search(r"还|还书", t):
            intent = "还书"
        elif re.search(r"查|查询|有没有|在馆|在吗|在哪", t):
            intent = "查书"
        elif re.search(r"读者|R\d{3}", t):
            intent = "查读者"
        else:
            intent = "其他"

        ent = {}
        rid = re.findall(r"R\d{3}", t)
        if rid:
            ent["reader_id"] = rid[0]
        bid = re.findall(r"B\d{3}", t)
        if bid:
            ent["book_id"] = bid[0]
        for name in ["三体", "百年孤独", "算法导论", "人类简史"]:
            if name in t:
                ent["book_name"] = name
        for name in ["张三", "李四", "王五"]:
            if name in t:
                ent["reader_name"] = name

        return json.dumps({"intent": intent, "entities": ent}, ensure_ascii=False)

    def _called_tools(self, msgs):
        names = []
        for m in msgs:
            if m.get("role") == "assistant" and m.get("tool_calls"):
                names += [tc["function"]["name"] for tc in m["tool_calls"]]
        return names

    def _observations(self, msgs):
        obs = []
        for m in msgs:
            if m.get("role") == "tool":
                try:
                    obs.append(json.loads(m["content"]))
                except Exception:
                    obs.append(m["content"])
        return obs

    # ---- ★ 图书馆工具步骤（替换原来的 _tool_step） ----
    def _tool_step_library(self, msgs, tools, user_txt):
        """ReAct 决策:返回工具调用指令,让 react_agent 真正执行"""
        from tools import FUNCS

        avail = {t["function"]["name"] for t in tools}
        called = self._called_tools(msgs)

        rid_list = re.findall(r"R\d{3}", user_txt)
        bid_list = re.findall(r"B\d{3}", user_txt)
        reader_id = rid_list[0] if rid_list else None
        book_id = bid_list[0] if bid_list else None

        # 如果已经调用过工具了，检查是否还需要更多工具
        if called:
            # 检查已调用的工具
            has_reader = "get_reader" in called
            has_book = "get_book" in called
            has_records = "get_records" in called

            # 判断用户想做什么
            wants_book = bool(re.search(r"书|B\d{3}|三体|百年孤独|算法导论|人类简史|在吗|有没有", user_txt))
            wants_records = bool(re.search(r"记录|借了|借过|借阅记录", user_txt))
            wants_borrow = bool(re.search(r"借|借书", user_txt))
            is_asking_can_borrow = bool(re.search(r"能借|可以借|能不能借", user_txt))

            # 如果查了读者，还需要查书（借书或查书场景）
            if has_reader and wants_book and not has_book and "get_book" in avail:
                # 通过书名找ID
                if not book_id:
                    for title, bid in [("三体", "B001"), ("百年孤独", "B002"), ("算法导论", "B003"),
                                       ("人类简史", "B004")]:
                        if title in user_txt:
                            book_id = bid
                            break
                if book_id:
                    return _Resp(_Msg(tool_calls=[_ToolCall("get_book", {"book_id": book_id})]))

            # 如果查了读者和书，还需要借书
            if has_reader and has_book and wants_borrow and not is_asking_can_borrow and "borrow_book" in avail:
                if reader_id and book_id:
                    return _Resp(
                        _Msg(tool_calls=[_ToolCall("borrow_book", {"reader_id": reader_id, "book_id": book_id})]))

            # 如果查了读者（能借吗场景），还需要查借阅记录
            if has_reader and wants_records and not has_records and "get_records" in avail:
                if reader_id:
                    return _Resp(_Msg(tool_calls=[_ToolCall("get_records", {"reader_id": reader_id})]))

            # 信息齐全 → 终态回复
            return _Resp(_Msg(content=self._final_answer_library(msgs, user_txt)))

        # ---- 第一步：查读者 ----
        wants_reader = bool(re.search(r"读者|张三|李四|王五|R\d{3}", user_txt))
        is_asking_can_borrow = bool(re.search(r"能借|可以借|能不能借", user_txt))
        wants_book = bool(re.search(r"书|B\d{3}|三体|百年孤独|算法导论|人类简史|在吗|有没有", user_txt))

        if (wants_reader or is_asking_can_borrow) and "get_reader" in avail and "get_reader" not in called:
            if not reader_id:
                for name, rid in [("张三", "R001"), ("李四", "R002"), ("王五", "R003")]:
                    if name in user_txt:
                        reader_id = rid
                        break
            if reader_id:
                return _Resp(_Msg(tool_calls=[_ToolCall("get_reader", {"reader_id": reader_id})]))

        # ---- 第二步：查书 ----
        if wants_book and "get_book" in avail and "get_book" not in called:
            if not book_id:
                for title, bid in [("三体", "B001"), ("百年孤独", "B002"), ("算法导论", "B003"), ("人类简史", "B004")]:
                    if title in user_txt:
                        book_id = bid
                        break
            if book_id:
                return _Resp(_Msg(tool_calls=[_ToolCall("get_book", {"book_id": book_id})]))

        # ---- 第三步：查借阅记录 ----
        wants_records = bool(re.search(r"记录|借了|借过|借阅记录", user_txt))
        if wants_records and "get_records" in avail and "get_records" not in called:
            if not reader_id:
                for name, rid in [("张三", "R001"), ("李四", "R002"), ("王五", "R003")]:
                    if name in user_txt:
                        reader_id = rid
                        break
            if reader_id:
                return _Resp(_Msg(tool_calls=[_ToolCall("get_records", {"reader_id": reader_id})]))

        # ---- 第四步：借书 ----
        wants_borrow = bool(re.search(r"借|借书", user_txt))
        if wants_borrow and not is_asking_can_borrow and "borrow_book" in avail and "borrow_book" not in called:
            if reader_id and book_id:
                return _Resp(_Msg(tool_calls=[_ToolCall("borrow_book", {"reader_id": reader_id, "book_id": book_id})]))

        # ---- 信息齐全 → 终态回复 ----
        return _Resp(_Msg(content=self._final_answer_library(msgs, user_txt)))

    # ---- ★ 图书馆最终答复（替换原来的 _final_answer） ----
    def _final_answer_library(self, msgs, user_txt):
        obs = self._observations(msgs)
        reader = next((o for o in obs if isinstance(o, dict) and "reader_id" in o and "name" in o), None)
        book = next((o for o in obs if isinstance(o, dict) and "book_id" in o and "title" in o), None)
        records = next((o for o in obs if isinstance(o, list) and o and "record_id" in o[0]), None)

        parts = []
        if reader and "error" not in reader:
            status = "可借" if reader.get("is_valid", False) else "不可借（可能欠费或已超限）"
            parts.append(
                f"读者{reader['name']}（{reader['reader_id']}），{reader['department']}，已借{reader.get('borrowed_count', 0)}本，状态：{status}。")

        if book and "error" not in book:
            parts.append(
                f"书籍《{book['title']}》（{book['book_id']}），作者{book['author']}，状态：{book.get('status', '未知')}，位置：{book.get('location', '未知')}。")

        if records and "error" not in records:
            if records:
                titles = []
                for r in records:
                    book_id = r.get("book_id")
                    # 尝试从 BOOKS 中取书名
                    try:
                        from data import BOOKS
                        book_info = BOOKS.get(book_id, {})
                        titles.append(book_info.get("title", book_id))
                    except Exception:
                        titles.append(book_id)
                parts.append(f"该读者共有{len(records)}条借阅记录：{', '.join(titles)}。")

        has_error = any(isinstance(o, dict) and o.get("error") for o in obs)
        if has_error:
            parts.append("抱歉，未能查询到对应信息，请核对后再试。")

        if not parts:
            parts.append("您好，我可以帮您查书、查读者信息、查借阅记录或办理借书。")

        return "".join(parts)


class _MockChat:
    def __init__(self): self.completions = _MockCompletions()


class MockLLM:
    def __init__(self): self.chat = _MockChat()


# ----------------------------------------------------------------------
# 对外:client + chat() 便捷函数(真实/桩 自动切换)
# ----------------------------------------------------------------------
if os.getenv("OPENAI_API_KEY"):
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"),
                    base_url=os.getenv("OPENAI_BASE_URL"))
    BACKEND = "real:" + CHAT_MODEL
else:
    client = MockLLM()
    BACKEND = "mock-llm(教学桩,离线可复现)"


def chat(messages, **kw):
    """无工具的便捷调用,返回 message 对象。"""
    return client.chat.completions.create(model=CHAT_MODEL, messages=messages, **kw).choices[0].message


if __name__ == "__main__":
    print("当前后端:", BACKEND)
    print(chat([{"role": "user", "content": "你好"}]).content)