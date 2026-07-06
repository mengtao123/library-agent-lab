# -*- coding: utf-8 -*-
"""离线评测：固定问题集 + LLM-as-judge 自动打分。"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from infrastructure.llm import chat
from application.agent import orchestrate


EVAL = [
    {"q": "三体在吗？", "must": ["在馆", "三体"]},
    {"q": "张三能借书吗？", "must": ["张三", "可借"]},
    {"q": "能借几本书？", "must": ["5本"]},
    {"q": "李四的借阅记录", "must": ["记录"]},
    {"q": "逾期了怎么办？", "must": ["逾期"]},
]


def judge(answer: str, must: list) -> dict:
    """用 LLM 判断回答是否覆盖了所有要点"""
    prompt = f'''判断以下回答是否覆盖了所有要点。

要点：{must}
回答：{answer}

只输出 JSON：{{"pass": true/false, "reason": "简短原因"}}'''

    try:
        result = chat([
            {"role": "user", "content": prompt}
        ], temperature=0, response_format={"type": "json_object"})
        return json.loads(result.content)
    except Exception:
        return {"pass": False, "reason": "解析失败"}


def run_eval(verbose: bool = True):
    """运行评测，返回通过率和详细结果"""
    passed = 0
    total = len(EVAL)
    results = []

    if verbose:
        print("=" * 60)
        print("📊 离线评测")
        print("=" * 60)

    for i, case in enumerate(EVAL, 1):
        q = case["q"]
        must = case["must"]

        t0 = time.time()
        result = orchestrate(q, verbose=False)
        answer = result.get("answer", "")
        latency = round(time.time() - t0, 3)

        j = judge(answer, must)
        ok = j.get("pass", False)
        if ok:
            passed += 1

        status = "✅ PASS" if ok else "❌ FAIL"
        results.append({"q": q, "pass": ok, "answer": answer, "latency": latency})

        if verbose:
            print(f"\n[{i}/{total}] {status} {q}")
            print(f"  回答: {answer[:80]}...")
            print(f"  要点: {must}")
            print(f"  耗时: {latency}s")

    rate = passed / total * 100
    if verbose:
        print("\n" + "=" * 60)
        print(f"📈 通过率: {passed}/{total} = {rate:.0f}%")
        print("=" * 60)

    return results, rate


def run_eval_with_policy_k(k: int = 3):
    """用指定的 POLICY_K 运行评测"""
    os.environ["POLICY_K"] = str(k)
    return run_eval()