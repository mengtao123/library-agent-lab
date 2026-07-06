# -*- coding: utf-8 -*-
"""会话记忆与上下文工程：由简到繁 —— ①滑动窗口 ②摘要压缩 ③长期画像。"""
import re
from infrastructure.llm import chat


class Memory:
    def __init__(self, window=6):
        self.window = window      # ① 滑动窗口：只保留最近 window 条原始对话
        self.history = []
        self.summary = ""
        self.profile = {}         # ③ 长期画像

    def add(self, role, content):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.window:            # ② 超窗口 → 摘要压缩
            old = self.history[:-self.window]
            self.history = self.history[-self.window:]
            self.summary = self._summarize(old)

    def _summarize(self, msgs):
        text = "\n".join(f"{m['role']}: {m['content']}" for m in msgs)
        prompt = "把以下对话压缩成要点，务必保留读者ID/书籍ID/借阅诉求:\n" + \
                 ((self.summary + "\n") if self.summary else "") + text
        return chat([{"role": "user", "content": prompt}]).content

    def remember(self, key, value):
        """记住用户长期画像信息"""
        self.profile[key] = value

    def build(self, system=""):
        """构建带记忆的 messages"""
        msgs = []
        if system:
            msgs.append({"role": "system", "content": system})
        if self.profile:
            msgs.append({"role": "system", "content": "用户画像:" + str(self.profile)})
        if self.summary:
            msgs.append({"role": "system", "content": "历史摘要:" + self.summary})
        return msgs + self.history

    def recall_reader_id(self):
        """从近期对话/摘要中回忆最近提到的读者ID"""
        for m in reversed(self.history):
            ids = re.findall(r"R\d{3}", m.get("content", ""))
            if ids:
                return ids[-1]
        ids = re.findall(r"R\d{3}", self.summary)
        return ids[-1] if ids else None

    def recall_book_id(self):
        """从近期对话/摘要中回忆最近提到的书籍ID"""
        for m in reversed(self.history):
            ids = re.findall(r"B\d{3}", m.get("content", ""))
            if ids:
                return ids[-1]
        ids = re.findall(r"B\d{3}", self.summary)
        return ids[-1] if ids else None

    def recall_reader_name(self):
        """从近期对话/摘要中回忆最近提到的读者姓名"""
        for m in reversed(self.history):
            for name in ["张三", "李四", "王五"]:
                if name in m.get("content", ""):
                    return name
        for name in ["张三", "李四", "王五"]:
            if name in self.summary:
                return name
        return None

    def recall_book_name(self):
        """从近期对话/摘要中回忆最近提到的书名"""
        for m in reversed(self.history):
            for name in ["三体", "百年孤独", "算法导论", "人类简史"]:
                if name in m.get("content", ""):
                    return name
        for name in ["三体", "百年孤独", "算法导论", "人类简史"]:
            if name in self.summary:
                return name
        return None