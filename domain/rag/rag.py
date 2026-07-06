# -*- coding: utf-8 -*-
"""
极简 RAG 检索：用 numpy 实现字符级 n-gram 的 TF 向量 + 余弦相似度。
- 零依赖(只用 numpy)，离线可跑
- 生产中把 _vectorize 换成嵌入模型即可
"""
import numpy as np
from infrastructure.data import POLICIES


def _ngrams(text, n=(1, 2)):
    """提取字符 n-gram"""
    text = text.replace(" ", "")
    grams = []
    for k in n:
        grams += [text[i:i+k] for i in range(len(text)-k+1)]
    return grams


class VectorStore:
    def __init__(self, docs: dict):
        self.ids = list(docs.keys())
        self.texts = list(docs.values())

        # 建词表
        vocab = {}
        for t in self.texts:
            for g in _ngrams(t):
                vocab.setdefault(g, len(vocab))
        self.vocab = vocab

        # 文档向量矩阵 (n_docs, vocab_size)
        self.M = np.zeros((len(self.texts), len(vocab)), dtype=np.float32)
        for i, t in enumerate(self.texts):
            for g in _ngrams(t):
                self.M[i, vocab[g]] += 1.0
        self._norm = np.linalg.norm(self.M, axis=1) + 1e-8

    def _vectorize(self, q):
        v = np.zeros(len(self.vocab), dtype=np.float32)
        for g in _ngrams(q):
            if g in self.vocab:
                v[self.vocab[g]] += 1.0
        return v

    def search(self, query, k=2):
        v = self._vectorize(query)
        sims = (self.M @ v) / (self._norm * (np.linalg.norm(v) + 1e-8))
        order = np.argsort(-sims)[:k]
        return [(self.ids[i], self.texts[i], float(sims[i])) for i in order if sims[i] > 0]


# ---- 图书馆政策知识库 ----
POLICIES = {
    "借阅规则": "每位读者最多可借5本书，借阅期限为14天，可续借1次（续借7天）。",
    "逾期政策": "图书逾期未还将按每本每天0.5元收取逾期费，超过30天未还将暂停借阅资格。",
    "丢失赔偿": "图书丢失需按原价赔偿，若图书已绝版则按原价3倍赔偿。",
    "借阅资格": "读者需持有效校园卡方可借书，欠费超过10元或逾期图书超过2本将暂停借阅资格。",
    "预约规则": "当图书全部借出时，读者可在线预约，预约成功后图书归还时优先通知。",
}

# 全局知识库
KB = VectorStore(POLICIES)


def retrieve(query, k=2):
    """返回最相关的 k 段政策文本（纯文本列表）"""
    return [t for _id, t, s in KB.search(query, k)]


def retrieve_scored(query, k=3):
    """返回 (标题, 文本, 相似度)，用于演示检索排序"""
    return KB.search(query, k)


if __name__ == "__main__":
    print("=" * 60)
    print("图书馆 RAG 知识库检索测试")
    print("=" * 60)

    test_queries = [
        "能借几本书？",
        "逾期了怎么办？",
        "书丢了要赔多少？",
        "怎么预约图书？"
    ]

    for q in test_queries:
        print(f"\n问: {q}")
        for _id, txt, s in retrieve_scored(q, 2):
            print(f"  [{s:.3f}] {_id}: {txt}")