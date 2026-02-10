"""
AI文案生成模块
支持本地 Ollama / Anthropic 等生成记单词文案
"""
import os
import re
import random
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dotenv import load_dotenv

# Anthropic 作为可选软依赖：没安装或没配 key 时自动退回本地 Ollama
try:
    from anthropic import Anthropic  # type: ignore
except ImportError:  # 未安装 anthropic 时不报错
    Anthropic = None  # type: ignore

from llm_client import generate_text
from prompts.word_learning import build_word_learning_prompt, PROMPT_VERSION
from structured_parser import StructuredPostParser

load_dotenv()

# level -> 单词库文件路径（一行一个单词）
LEVEL_WORD_FILES: Dict[str, str] = {
    "CET-4": "data/CET4.txt",
    "CET-6": "data/CET6.txt",
    "考研": "data/考研.txt",
    "CET4": "data/CET4.txt",
    "CET6": "data/CET6.txt",
}


class AllWordsUsedError(Exception):
    """该 level 下单词库中的词均已出现在 posts 表中，无法再选未发词。"""
    def __init__(self, level: str):
        self.level = level
        super().__init__(f"该级别单词已全部使用完毕: {level}（word + level + prompt_version 均在 posts 中已有记录）")

# 结构化输出中的段落标记，用于解析（包含【meta】）
_STRUCTURED_SECTIONS = ("【标题】", "【单词卡】", "【配图建议】", "【正文】", "【标签】", "【meta】")


def render_xhs_word_content(word: str, 单词卡: str, 正文: str) -> str:
    """
    将结构化内容渲染为更像小红书的最终正文。
    不影响图片生成，仅影响文案观感。
    """
    parts = []

    # 开头气氛（非常重要）
    parts.append(f"📘 今天一起轻松记一个高频单词：**{word}** ✨\n")

    if 单词卡:
        parts.append("🔑 **核心含义**\n" + 单词卡.strip())

    if 正文:
        parts.append("🧠 **用法 + 记忆技巧**\n" + 正文.strip())

    # 结尾互动
    parts.append("👇 收藏起来慢慢看，下一个单词继续一起攻克～")

    return "\n\n".join(parts)


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
        
        content = render_xhs_word_content(
            word=word,
            单词卡=单词卡,
            正文=正文
        )
        
        meta = self.extract_meta(meta_raw)
        
        return {
            "word": word,
            "title": title,
            "content": content,
            "tags": tags[:8],
            "image_suggestion": 配图建议 or None,
            "meta": meta,  # 包含 prompt version 等信息
        }


class ContentGenerator:
    """AI文案生成器"""
    
    def __init__(self):
        # 仅保留 Anthropic 作为可选远程备份，本地默认走 Ollama
        self.anthropic_client = None
        self.word_parser = WordLearningParser()  # 使用解析器实例

        # 初始化 Anthropic 客户端（软依赖：既要装了包，又要配了 key 才会启用）
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if Anthropic and anthropic_key and anthropic_key != "your_anthropic_api_key_here":  # type: ignore
            self.anthropic_client = Anthropic(api_key=anthropic_key)  # type: ignore
    
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
        解析「六段式」结构化输出（含【meta】），得到标题、正文、标签、配图建议。
        使用 StructuredPostParser 基类，便于扩展 phrase / grammar 等类型。

        Args:
            text: LLM 按【标题】【单词卡】【配图建议】【正文】【标签】【meta】输出的原文
            word: 当前单词（用于兜底标题等）

        Returns:
            dict: word, title, content, tags, image_suggestion, meta
        """
        return self.word_parser.parse(text, word=word)

    def get_words_for_level(self, level: str) -> List[str]:
        """
        按 level 读取单词库文件，返回单词列表（一行一个，去空、去首尾空白）。

        Args:
            level: 难度级别，如 "CET-4"、"CET-6"、"考研"、"CET4"、"CET6"

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

    def generate_word_content(self, word: Optional[str] = None, theme: Optional[str] = None) -> dict:
        """
        生成记单词文案
        
        Args:
            word: 指定单词（可选，如果不提供则随机选择）
            theme: 主题（可选，如"日常用语"、"商务英语"等）
        
        Returns:
            包含标题、正文、标签的字典
        """
        # 如果没有指定单词，生成一个常见单词
        if not word:
            word = self._get_random_word(theme)
        
        # 生成文案提示词
        prompt = self._build_prompt(word, theme)

        # 优先使用 Claude；否则回落到本地 Ollama（llm_client）
        if self.anthropic_client:
            content = self._generate_with_claude(prompt)
        else:
            content = generate_text(prompt)
        
        # 解析生成的内容
        return self._parse_content(content, word)
    
    def _get_random_word(self, theme: Optional[str] = None) -> str:
        """获取随机单词"""
        # 这里可以连接单词数据库
        import random
        from pathlib import Path

        level = theme or "CET-6"  # 默认 CET6

        file_map = {
            "CET-4": "data/CET4.txt",
            "CET-6": "data/CET6.txt",
            "考研": "data/考研.txt",
           
        }

        word_file = file_map.get(level)
        if not word_file:
            raise ValueError(f"Unsupported word level: {level}")
        
        path = Path(word_file)
        if not word_file:
            raise ValueError(f"Unsupported word level: {level}")

        path = Path(word_file)
        if not path.exists():
            raise FileNotFoundError(f"Word list not found: {path}")

        with path.open("r", encoding="utf-8") as f:
            words = [line.strip() for line in f if line.strip()]

        if not words:
            raise RuntimeError(f"Word list is empty: {path}")

        return random.choice(words)
    
    def _build_prompt(self, word: str, theme: Optional[str] = None) -> str:
        """构建AI提示词"""
        theme_text = f"主题：{theme}，" if theme else ""
        return f"""请为小红书平台生成一篇关于英语单词"{word}"的记单词文案。

要求：
1. 标题要吸引眼球，使用emoji表情符号，长度15-25字
2. 正文要生动有趣，包含：
   - 开头引导语（ 1～2 句话-，语气活泼、有画面感、能吸引人继续看,适当添加emoji表情符号,不允许为空）
   - 英文单词（不需要发音，只需要单词）
   - 中文释义(只按照词典输出单词的标准释义。
严格规则（只适用于中文释义）：
1. 只输出词性和对应的中文释义
2. 不解释、不举例、不扩展
3. 不使用完整句
4. 不允许任何词性下的释义为空
5. 每个词性至少给出 1 个常见、标准中文释义
6. 如果该词性不存在，则不要输出该词性

输出格式（必须严格一致，只适用于中文释义）：
<单词>
n: 中文释义1；中文释义2
v: 中文释义1；中文释义2
adj: 中文释义1；中文释义2
adv: 中文释义1；中文释义2)
   - 记忆技巧（可以是场景记忆，故事等，不要谐音，避免让读者感到云里雾里）
   - 实用例句（中英文对照，2-3个）
   - 相关词汇扩展(英语单词+中文释义，2-3个)
3. 使用小红书风格：轻松活泼、有互动感、使用emoji
4. 添加10个相关话题标签（格式：#话题；必须不能重复,不要出现与英语学习无关的话题）
5. 文案总长度控制在300-500字

{theme_text}请确保内容准确且有趣，能够帮助读者轻松记住这个单词。

请直接输出文案内容，不需要额外说明。"""
    
    def _generate_with_openai(self, prompt: str) -> str:
        """使用OpenAI生成内容"""
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一位专业的小红书内容创作专家，擅长创作有趣、实用的英语学习内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1000
        )
        return response.choices[0].message.content
    
    def _generate_with_claude(self, prompt: str) -> str:
        """使用Claude生成内容"""
        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            temperature=0.8,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return response.content[0].text
    
    def _parse_content(self, content: str, word: str) -> dict:
        """解析生成的内容"""
        lines = content.strip().split('\n')
        
        # 提取标题（第一行）
        title = lines[0].strip() if lines else f"📚 今天学单词：{word}"
        
        # 提取正文（去除标题后的内容）
        body_lines = [line.strip() for line in lines[1:] if line.strip()]
        body = '\n\n'.join(body_lines)
        
        # 提取标签（以#开头的内容）
        tags = []
        for line in body_lines:
            if '#' in line:
                import re
                found_tags = re.findall(r'#([^#]+)#', line)
                tags.extend(found_tags)
        
        # 如果没有找到标签，添加默认标签
        if not tags:
            tags = ["英语学习", "记单词", "英语词汇", "学习打卡", "英语干货"]
        
        return {
            "word": word,
            "title": title,
            "content": body,
            "tags": tags[:10],  # 限制最多10个标签
            "full_text": content
        }
