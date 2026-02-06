"""
图片生成模块
支持：1）Stable Diffusion 文生图（本地 API）生成单词卡片；2）本地模板兜底。
"""
import os
import re
import base64
from typing import Optional, Tuple
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

# Stable Diffusion API（本地，如 WebUI）
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")
USE_SD_TXT2IMG = os.getenv("USE_SD_TXT2IMG", "1").strip().lower() in ("1", "true", "yes")


# 稳定版正向 Prompt（中文）- 强烈推荐默认使用
SD_PROMPT_STYLE = """【风格说明】
小红书风格的英语单词学习卡片，
极简设计，干净的白色或浅米色背景，
1:1 正方形构图，
只包含文字，没有任何插画、人物或图形元素，

顶部是一个醒目的英文单词大标题，
下面是较小字号的词性加中文释义，
再下面可以有一行简短的英文例句作为补充，

现代无衬线字体，
排版清晰，有层级感，
留白充足，阅读舒适，
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
    结构化拼接：【风格说明】+【文字内容】。
    减少单词被拆开、中英文混乱、SD 乱编内容。
    """
    lines = [
        SD_PROMPT_STYLE,
        "",
        "【文字内容】",
        f"单词：{word}",
        f"释义：{subtitle}",
    ]
    if example_sentence:
        lines.append(f"例句：{example_sentence}")
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
        """使用模板生成图片（备用方案）"""
        # 创建图片
        width, height = 1080, 1080
        img = Image.new('RGB', (width, height), color='#FF6B9D')  # 小红书风格粉色
        
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体，如果没有则使用默认字体
        try:
            # Windows系统字体路径
            title_font = ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc", 80)
            word_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 60)
            meaning_font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 50)
        except:
            title_font = ImageFont.load_default()
            word_font = ImageFont.load_default()
            meaning_font = ImageFont.load_default()
        
        # 绘制标题
        title = "📚 每日单词"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        title_height = title_bbox[3] - title_bbox[1]
        draw.text(((width - title_width) // 2, 200), title, fill='white', font=title_font)
        
        # 绘制单词
        word_bbox = draw.textbbox((0, 0), word.upper(), font=word_font)
        word_width = word_bbox[2] - word_bbox[0]
        draw.text(((width - word_width) // 2, 400), word.upper(), fill='white', font=word_font)
        
        # 绘制中文释义
        meaning_bbox = draw.textbbox((0, 0), meaning, font=meaning_font)
        meaning_width = meaning_bbox[2] - meaning_bbox[0]
        draw.text(((width - meaning_width) // 2, 550), meaning, fill='white', font=meaning_font)
        
        # 添加装饰性元素
        # 绘制圆形装饰
        draw.ellipse([width//2 - 150, 700, width//2 + 150, 1000], outline='white', width=5)
        
        # 保存图片
        filename = f"generated_images/{word}_template.png"
        img.save(filename)
        return filename
    
    def create_collage(self, images: list, output_path: str) -> str:
        """创建拼图（多张图片组合）"""
        if not images:
            raise ValueError("图片列表不能为空")
        
        # 加载所有图片
        loaded_images = []
        for img_path in images:
            if os.path.exists(img_path):
                loaded_images.append(Image.open(img_path))
        
        if not loaded_images:
            raise ValueError("没有有效的图片")
        
        # 创建拼图（横向排列）
        total_width = sum(img.width for img in loaded_images)
        max_height = max(img.height for img in loaded_images)
        
        collage = Image.new('RGB', (total_width, max_height), color='white')
        
        x_offset = 0
        for img in loaded_images:
            collage.paste(img, (x_offset, 0))
            x_offset += img.width
        
        collage.save(output_path)
        return output_path
