"""
图片生成模块
支持：1）Stable Diffusion 文生图（本地 API）生成单词卡片；2）本地模板兜底。
"""
import os
import re
import base64
from pathlib import Path
from typing import Optional, Tuple
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

# Stable Diffusion API（本地，如 WebUI）
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")
USE_SD_TXT2IMG = os.getenv("USE_SD_TXT2IMG", "1").strip().lower() in ("1", "true", "yes")


# 稳定版正向 Prompt（中文）- 封面仅小写单词，无释义无多余符号
SD_PROMPT_STYLE = """【风格说明】
小红书风格的英语单词学习卡片，
极简设计，干净的白色或浅米色背景，
1:1 正方形构图，
只包含一个英文单词，没有任何插画、人物或图形元素，无中文释义，无例句，无标点等多余符号，

顶部居中显示一个醒目的英文单词，使用小写字母，

现代无衬线字体，
排版清晰，留白充足，阅读舒适，
整体像一个真实的小红书英语学习账号截图，
安静、克制、适合收藏"""

# 稳定版负向 Prompt（中文）
SD_NEGATIVE_PROMPT = """人物，真人，卡通，动漫，插画，
图标，emoji，符号，
彩色背景，渐变背景，纹理背景，
复杂排版，海报风，设计感过强，
手写字体，书法字体，
模糊，低清晰度，变形，
水印，logo"""


def _build_sd_prompt(word: str, subtitle: str, example_sentence: Optional[str]) -> str:
    """
    封面仅显示小写单词，无中文释义、无例句、无多余符号。
    结构化拼接：【风格说明】+【文字内容】。
    """
    word_lower = word.strip().lower() if word else "word"
    lines = [
        SD_PROMPT_STYLE,
        "",
        "【文字内容】",
        word_lower,
    ]
    return "\n".join(lines)


def _extract_subtitle_and_example(content: str) -> Tuple[str, Optional[str]]:
    """从正文中抽取「词性+释义」作副标题、以及一条英文例句。"""
    if not content or not content.strip():
        return "", None
    subtitle = ""
    example_sentence = None
    lines = [ln.strip() for ln in content.replace("\r", "\n").split("\n") if ln.strip()]
    # 副标题：优先匹配 n. / v. / adj. 等 + 中文
    pos_pattern = re.compile(r"^(n\.|v\.|adj\.|adv\.|prep\.|conj\.)\s*.+")
    for line in lines:
        if pos_pattern.match(line) and any("\u4e00" <= c <= "\u9fff" for c in line):
            subtitle = line
            break
    # 例句：取第一条「以大写开头、以.结尾、主要为英文」的行
    for line in lines:
        if len(line) < 15:
            continue
        if not line.endswith("."):
            continue
        ascii_ratio = sum(1 for c in line if ord(c) < 128) / max(len(line), 1)
        if ascii_ratio >= 0.7 and line[0].isupper():
            example_sentence = line
            break
    return subtitle, example_sentence


class ImageGenerator:
    """图片生成器：优先文生图（SD），失败则本地模板兜底。"""
    
    def __init__(self):
        self.sd_api_url = SD_API_URL.rstrip("/")
    
    def generate_word_image(
        self, 
        word: str, 
        image_prompt: Optional[str] = None,
        meaning: Optional[str] = None, 
        image_style: str = "modern",
        content: Optional[str] = None,
    ) -> str:
        """
        生成单词配图：优先调用本地 Stable Diffusion 文生图，失败则用本地模板。
        
        Args:
            word: 单词
            image_prompt: 配图建议（文生图时未用，保留兼容）
            meaning: 中文释义（模板兜底用；文生图时用于补全副标题）
            image_style: 图片风格（保留参数以兼容接口）
            content: 正文/单词卡内容，用于抽取副标题和例句以填入文生图 prompt
        
        Returns:
            图片文件路径
        """
        os.makedirs("generated_images", exist_ok=True)
        
        subtitle = meaning or "学习单词"
        example_sentence = None
        if content:
            _sub, _ex = _extract_subtitle_and_example(content)
            if _sub:
                subtitle = _sub
            example_sentence = _ex
        
        if USE_SD_TXT2IMG:
            try:
                return self._generate_sd_word_card(word, subtitle, example_sentence)
            except Exception as e:
                # 文生图失败时静默回退到模板，不打断主流程
                pass  # 下方用模板继续
        
        return self._generate_template_image(word, subtitle or meaning or "学习单词")
    
    def _generate_sd_word_card(
        self, word: str, subtitle: str, example_sentence: Optional[str]
    ) -> str:
        """调用本地 Stable Diffusion txt2img API 生成单词卡片图。"""
        import requests
        
        prompt = _build_sd_prompt(word, subtitle, example_sentence)
        payload = {
            "prompt": prompt,
            "negative_prompt": SD_NEGATIVE_PROMPT,
            "steps": int(os.getenv("SD_STEPS", "25")),
            "width": int(os.getenv("SD_WIDTH", "1024")),
            "height": int(os.getenv("SD_HEIGHT", "1024")),
        }
        url = f"{self.sd_api_url}/sdapi/v1/txt2img"
        resp = requests.post(url, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        images_b64 = data.get("images")
        if not images_b64:
            raise ValueError("SD API returned no images")
        img_data = base64.b64decode(images_b64[0])
        safe_word = word.replace(" ", "_").strip() or "word"
        path = os.path.join("generated_images", f"{safe_word}_sd.png")
        with open(path, "wb") as f:
            f.write(img_data)
        return path
    
    def _generate_template_image(self, word: str, meaning: str) -> str:
        """使用模板生成图片（备用方案）：根目录 bg1.jpg 为背景（保持原尺寸），仅显示小写英文单词。"""
        bg_path = Path(__file__).resolve().parent / "bg1.jpg"
        if bg_path.exists():
            img = Image.open(bg_path).convert("RGB")
            width, height = img.size
        else:
            width, height = 1080, 1080
            img = Image.new('RGB', (width, height), color='#C97B84')
        draw = ImageDraw.Draw(img)

        try:
            word_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 72)
        except Exception:
            word_font = ImageFont.load_default()

        # 仅显示小写英文单词，黑色字体，适中大小、居中（参照笔记纸风格，字体不过大）
        word_display = (word or "word").strip().lower()
        word_bbox = draw.textbbox((0, 0), word_display, font=word_font)
        word_width = word_bbox[2] - word_bbox[0]
        word_height = word_bbox[3] - word_bbox[1]
        x = (width - word_width) // 2
        y = (height - word_height) // 2
        draw.text((x, y), word_display, fill='black', font=word_font)

        safe_word = (word or "word").replace(" ", "_").strip()
        filename = f"generated_images/{safe_word}_template.png"
        img.save(filename)
        return filename
