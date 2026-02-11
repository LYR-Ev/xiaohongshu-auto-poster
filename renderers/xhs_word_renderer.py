"""
小红书单词帖 · 唯一发帖模板（不可漂）
只有本 Renderer 能决定最终发帖格式；Prompt 只负责内容素材，Parser 只负责拆字段。
"""
import hashlib
import random
from typing import List, TypedDict


class WordPost(TypedDict, total=False):
    """唯一结构数据模型：不管用什么 Prompt，最终都要被解析成这一份。"""
    word: str
    definitions: str       # 词性 + 中文释义，如 n. xxx; v. xxx
    memory_story: str     # 记忆技巧 / 故事段落
    examples: List[str]   # 例句（已中英对照）
    related: List[str]    # 扩展词汇


DEFAULT_HEADERS = [
    "📘 今天一起轻松记一个高频单词👍 点赞支持这个英语学习帖吧~ 📊 收藏可以随时回顾单词讲解哦",
    "📚 每天一个单词，慢慢把英语捡回来～👍 点赞 + 收藏更好吸收",
]

DEFAULT_FOOTERS = [
    "👍 点赞是对我最大的支持，收藏起来反复看～",
    "📌 建议收藏，下次刷到还能复习这个单词",
]


def render_xhs_word_post(data: WordPost) -> str:
    """
    唯一出口：将 WordPost 渲染为小红书正文。
    不允许 main.py / Prompt 决定结构，只有此处能决定格式。
    同一单词固定同一头尾（seed 由 word 决定），便于重发/回放/对账/A/B 可复现。
    """
    word = (data.get("word") or "word").strip()
    seed = int(hashlib.md5(word.encode()).hexdigest()[:8], 16)
    random.seed(seed)
    header = random.choice(DEFAULT_HEADERS)
    footer = random.choice(DEFAULT_FOOTERS)

    lines = []

    # 开头
    lines.append(header)
    lines.append("")

    # 单词
    lines.append(data["word"])
    lines.append("")
    lines.append(data.get("definitions") or "")
    lines.append("")

    # 记忆故事
    lines.append(data.get("memory_story") or "")
    lines.append("")

    # 例句
    lines.append("实用例句：")
    for ex in data.get("examples") or []:
        lines.append(f"- {ex}")
    lines.append("")

    # 扩展
    if data.get("related"):
        lines.append("相关词汇扩展：")
        for r in data["related"]:
            lines.append(f"- {r}")
        lines.append("")

    # 结尾
    lines.append(footer)

    return "\n".join(lines).strip()
