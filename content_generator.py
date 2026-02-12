"""
AI文案生成模块
支持本地 Ollama 生成记单词文案，唯一 Prompt 入口为 prompts.word_learning.build_word_learning_prompt。
"""
import re
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dotenv import load_dotenv

from llm_client import generate_text
from prompts.word_learning import build_word_learning_prompt, PROMPT_VERSION
from structured_parser import StructuredPostParser
from renderers.xhs_word_renderer import render_xhs_word_post, WordPost

load_dotenv()

# level -> 单词库文件路径（一行一个单词）
LEVEL_WORD_FILES: Dict[str, str] = {
    "CET-4": "data/CET4.txt",
    "CET-6": "data/CET6.txt",
    "考研": "data/考研.txt",
    "CET4": "data/CET4.txt",
    "CET6": "data/CET6.txt",
    "cet-4": "data/CET4.txt",
    "cet-6": "data/CET6.txt",
    "cet4": "data/CET4.txt",
    "cet6": "data/CET6.txt",
}


class AllWordsUsedError(Exception):
    """该 level 下单词库中的词均已出现在 posts 表中，无法再选未发词。"""
    def __init__(self, level: str):
        self.level = level
        super().__init__(f"该级别单词已全部使用完毕: {level}（word + level + prompt_version 均在 posts 中已有记录）")

# 分段兜底正则：任意命中即视为该段开始，避免模型换说法（例句/Examples/实用例子）导致拆段失败
EXAMPLE_SPLIT_PATTERNS = [
    r"实用例句\s*[：:]",
    r"例句\s*[：:]",
    r"Examples?\s*[：:]",
    r"实用例子\s*[：:]",
    r"【例句】",
]
RELATED_SPLIT_PATTERNS = [
    r"相关词汇扩展\s*[：:]",
    r"相关词汇\s*[：:]",
    r"扩展\s*[：:]",
    r"Related\s*[：:]",
    r"【相关词汇】",
]


def _find_first_match(text: str, patterns: List[str]) -> tuple:
    """返回 (位置, 匹配到的正则在 text 中的结束位置)。未命中返回 (-1, -1)。"""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.start(), m.end()
    return -1, -1


def _parse_body_into_word_post(正文: str) -> tuple:
    """
    从【正文】中拆出 memory_story、examples、related。
    分段用兜底正则，任意命中即视为例句/扩展段开始；memory_story 只取第一个空行前的自然段。
    """
    memory_story = ""
    examples: List[str] = []
    related: List[str] = []
    if not 正文 or not 正文.strip():
        return memory_story, examples, related

    text = 正文.strip()
    # 例句段：用正则找任意分界
    ex_pos, ex_end = _find_first_match(text, EXAMPLE_SPLIT_PATTERNS)
    if ex_pos == -1:
        # memory_story 只取「第一个空行之前」的完整故事块，避免释义重复、故事被截断
        memory_story = text.split("\n\n")[0].strip()
        return memory_story, examples, related

    before_ex = text[:ex_pos].strip()
    memory_story = before_ex.split("\n\n")[0].strip()
    rest = text[ex_end:].strip()

    # 扩展段：用正则找任意分界
    rel_pos, rel_end = _find_first_match(rest, RELATED_SPLIT_PATTERNS)
    if rel_pos >= 0:
        examples_block = rest[:rel_pos].strip()
        related_block = rest[rel_end:].strip()
        for line in related_block.split("\n"):
            line = line.strip()
            if line.startswith("-") or line.startswith("•"):
                line = line.lstrip("-•").strip()
                if line:
                    related.append(line)
    else:
        examples_block = rest

    for line in examples_block.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("-") or line.startswith("•"):
            examples.append(line.lstrip("-•").strip())
        elif re.match(r"^\d+[\.．]\s*", line):
            examples.append(re.sub(r"^\d+[\.．]\s*", "", line))
        elif "英语：" in line or "英文：" in line:
            examples.append(line)

    return memory_story, examples, related


def build_word_post_from_sections(word: str, 单词卡: str, 正文: str) -> WordPost:
    """
    将 Parser 拆出的字段转为唯一结构 WordPost。
    不决定格式，只做字段提取与映射。
    """
    definitions = (单词卡 or "").strip()
    memory_story, examples, related = _parse_body_into_word_post(正文 or "")
    return {
        "word": word,
        "definitions": definitions,
        "memory_story": memory_story,
        "examples": examples,
        "related": related,
    }


class WordLearningParser(StructuredPostParser):
    """单词学习帖解析器（继承基类）"""
    
    sections = ("【标题】", "【单词卡】", "【配图建议】", "【正文】", "【标签】", "【meta】")
    
    def _post_process(self, sections: Dict[str, str], word: str) -> Dict[str, Any]:
        """将解析出的段落转换为业务格式"""
        title = sections.get("【标题】", "").strip() or f"📚 今天学单词：{word}"
        单词卡 = sections.get("【单词卡】", "").strip()
        配图建议 = sections.get("【配图建议】", "").strip()
        正文 = sections.get("【正文】", "").strip()
        标签_raw = sections.get("【标签】", "").strip()
        meta_raw = sections.get("【meta】", "").strip()
        
        tags = self.extract_tags(标签_raw)
        if not tags:
            tags = ["英语学习", "记单词", "英语词汇", "学习打卡", "英语干货"]
        
        meta = self.extract_meta(meta_raw)
        
        # Parser 只拆字段，不拼文案；content 由 main 经唯一 Renderer 生成
        return {
            "word": word,
            "title": title,
            "单词卡": 单词卡,
            "正文": 正文,
            "tags": tags[:8],
            "image_suggestion": 配图建议 or None,
            "meta": meta,
        }


class ContentGenerator:
    """AI文案生成器"""
    
    def __init__(self):
        self.word_parser = WordLearningParser()
    
    def generate_word_post(self, word: str, level: str = "CET-6") -> str:
        """
        使用独立 Prompt 模板生成英语单词学习帖文案。
        内部调用 llm_client.generate_text，不写死 Prompt。

        Args:
            word: 要学习的英语单词
            level: 难度水平，默认 "CET-6"

        Returns:
            LLM 生成的文案原文（字符串）
        """
        prompt = build_word_learning_prompt(word=word, level=level)
        return generate_text(prompt)

    def parse_structured_word_post(self, text: str, word: str) -> dict:
        """
        解析「六段式」结构化输出（含【meta】），只拆字段，不拼文案。
        Returns 含 word, title, 单词卡, 正文, tags, image_suggestion, meta；
        content 由调用方通过唯一 Renderer 生成。
        """
        return self.word_parser.parse(text, word=word)

    def render_word_post_content(self, parsed: Dict[str, Any]) -> str:
        """
        唯一出口：将解析结果转为 WordPost 后交给 Renderer 生成最终正文。
        main 禁止拼文案，只允许调用此方法。
        """
        word_post = build_word_post_from_sections(
            word=parsed["word"],
            单词卡=parsed.get("单词卡") or "",
            正文=parsed.get("正文") or "",
        )
        return render_xhs_word_post(word_post)

    def get_words_for_level(self, level: str) -> List[str]:
        """
        按 level 读取单词库文件，返回单词列表（一行一个，去空、去首尾空白）。

        Args:
            level: 难度级别，如 "CET-4"、"CET-6"、"考研"、"CET4"、"CET6" "cet-4"、"cet-6"、"cet4"、"cet6"

        Returns:
            该级别单词库中的全部单词列表

        Raises:
            ValueError: 不支持的 level
            FileNotFoundError: 对应单词库文件不存在
        """
        path_str = LEVEL_WORD_FILES.get(level)
        if not path_str:
            raise ValueError(f"不支持的 level（单词库未配置）: {level}，可选: {list(LEVEL_WORD_FILES.keys())}")
        path = Path(path_str)
        if not path.exists():
            raise FileNotFoundError(f"单词库文件不存在: {path.absolute()}")
        with path.open("r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]
        return words

    def pick_unused_word(
        self,
        level: str,
        has_posted: Callable[[str, str, str], bool],
    ) -> str:
        """
        从指定 level 的单词库中，选出一个「未在 posts 表中出现过（word + level + PROMPT_VERSION）」的单词。

        Args:
            level: 难度级别
            has_posted: 判断是否已发过，签名 (word, level, prompt_version) -> bool

        Returns:
            一个未发过的单词

        Raises:
            AllWordsUsedError: 该 level 下所有单词均已发过
        """
        words = self.get_words_for_level(level)
        unused = [
            w for w in words
            if not has_posted(w.strip(), level, PROMPT_VERSION)
        ]
        if not unused:
            raise AllWordsUsedError(level)
        return random.choice(unused).strip()

    def generate_word_content(
        self,
        word: Optional[str] = None,
        theme: Optional[str] = None,
        level: Optional[str] = None,
    ) -> dict:
        """
        生成记单词文案。唯一 Prompt 来源：build_word_learning_prompt。
        不拼写 Prompt 字符串；与 theme==word 同协议、同解析、同 Renderer。
        """
        level = level or (theme if theme and theme in LEVEL_WORD_FILES else "CET-4")
        if not word or not word.strip():
            word = self._get_random_word(level)
        else:
            word = word.strip()
        prompt = build_word_learning_prompt(word=word, level=level)
        text = generate_text(prompt)
        content_data = self.parse_structured_word_post(text, word)
        content_data["content"] = self.render_word_post_content(content_data)
        return content_data
    
    def _get_random_word(self, level: str) -> str:
        """从指定 level 单词库中随机取一词（不查 posts，用于 generate_word_content）。"""
        words = self.get_words_for_level(level)
        return random.choice(words).strip()
