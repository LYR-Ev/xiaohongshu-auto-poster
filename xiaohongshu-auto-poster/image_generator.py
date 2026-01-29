"""
图片生成模块
当前版本不再调用 OpenAI / DALL-E，仅使用本地模板生成配图。
"""
import os
from typing import Optional
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

load_dotenv()


class ImageGenerator:
    """图片生成器"""
    
    def __init__(self):
        # 预留扩展位：未来可接本地图片生成模型
        pass
    
    def generate_word_image(
        self, 
        word: str, 
        image_prompt: Optional[str] = None,
        meaning: Optional[str] = None, 
        image_style: str = "modern"
    ) -> str:
        """
        生成单词配图（使用本地模板实现，避免依赖 OpenAI）
        
        Args:
            word: 单词
            image_prompt: 明确的图片生成提示词（当前模板仅用于未来扩展，占位）
            meaning: 中文释义（用于模板展示）
            image_style: 图片风格（保留参数以兼容接口）
        
        Returns:
            图片文件路径
        """
        # 创建输出目录
        os.makedirs("generated_images", exist_ok=True)
        
        # 直接使用模板生成图片
        return self._generate_template_image(word, meaning or "学习单词")
    
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
