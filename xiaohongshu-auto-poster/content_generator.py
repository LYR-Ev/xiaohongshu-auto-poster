"""
AI文案生成模块
支持本地 Ollama / Anthropic 等生成记单词文案
"""
import os
import re
from typing import Optional, Dict, Any
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

# 结构化输出中的段落标记，用于解析（包含【meta】）
_STRUCTURED_SECTIONS = ("【标题】", "【单词卡】", "【配图建议】", "【正文】", "【标签】", "【meta】")


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
        
        content = (单词卡 + "\n\n" + 正文).strip() if 单词卡 else 正文
        
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
    
    def generate_word_post(self, word: str, level: str = "CET-4") -> str:
        """
        使用独立 Prompt 模板生成英语单词学习帖文案。
        内部调用 llm_client.generate_text，不写死 Prompt。

        Args:
            word: 要学习的英语单词
            level: 难度水平，默认 "CET-4"

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

        level = theme or "cet4"  # 默认 CET4

        file_map = {
            "cet4": "data/cet4.txt",
            "cet6": "data/cet6.txt",
           
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
   - 单词的发音（音标）
   - 中文释义
   - 记忆技巧（可以是联想、词根词缀、故事等）
   - 实用例句（中英文对照，2-3个）
   - 相关词汇扩展
3. 使用小红书风格：轻松活泼、有互动感、使用emoji
4. 添加5-8个相关话题标签（格式：#话题#）
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
            "tags": tags[:8],  # 限制最多8个标签
            "full_text": content
        }
