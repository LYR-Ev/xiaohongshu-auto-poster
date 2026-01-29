"""
小红书发布模块
支持通过API或自动化工具发布小红书帖子
"""
import os
import time
import json
import requests
from typing import Dict, List, Optional
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, Page

load_dotenv()


class XiaohongshuPublisher:
    """小红书发布器"""
    
    def __init__(self):
        self.app_id = os.getenv("XIAOHONGSHU_APP_ID")
        self.app_secret = os.getenv("XIAOHONGSHU_APP_SECRET")
        self.access_token = os.getenv("XIAOHONGSHU_ACCESS_TOKEN")
        self.use_api = bool(self.app_id and self.app_secret)
    
    def publish_post(self, title: str, content: str, images: List[str], tags: List[str] = None) -> Dict:
        """
        发布小红书帖子
        
        Args:
            title: 标题
            content: 正文内容
            images: 图片路径列表
            tags: 标签列表
        
        Returns:
            发布结果字典
        """
        if self.use_api:
            return self._publish_via_api(title, content, images, tags)
        else:
            return self._publish_via_automation(title, content, images, tags)
    
    def _publish_via_api(self, title: str, content: str, images: List[str], tags: List[str]) -> Dict:
        """通过官方API发布（需要申请开放平台权限）"""
        # 注意：小红书官方API需要申请开放平台权限
        # 这里提供示例代码结构
        
        # 1. 上传图片获取图片ID
        image_ids = []
        for img_path in images:
            if os.path.exists(img_path):
                image_id = self._upload_image(img_path)
                if image_id:
                    image_ids.append(image_id)
        
        # 2. 构建发布内容
        # 添加标签到内容中
        full_content = content
        if tags:
            tag_text = " ".join([f"#{tag}#" for tag in tags])
            full_content = f"{content}\n\n{tag_text}"
        
        # 3. 调用发布接口
        url = "https://open.xiaohongshu.com/api/sns/web/v1/note"  # 示例URL，实际需要查看官方文档
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "title": title,
            "content": full_content,
            "image_ids": image_ids,
            "type": "normal"
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                return {
                    "success": True,
                    "message": "发布成功",
                    "data": response.json()
                }
            else:
                return {
                    "success": False,
                    "message": f"发布失败: {response.text}",
                    "error": response.status_code
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"发布异常: {str(e)}"
            }
    
    def _upload_image(self, image_path: str) -> Optional[str]:
        """上传图片获取图片ID"""
        # 这里需要调用小红书图片上传接口
        # 示例代码结构
        upload_url = "https://open.xiaohongshu.com/api/sns/web/v1/upload/image"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        try:
            with open(image_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(upload_url, headers=headers, files=files)
                if response.status_code == 200:
                    data = response.json()
                    return data.get('image_id')
        except Exception as e:
            print(f"图片上传失败: {e}")
        
        return None
    
    def _publish_via_automation(self, title: str, content: str, images: List[str], tags: List[str]) -> Dict:
        """
        通过自动化工具发布（使用Playwright）
        注意：这种方式需要登录账号，可能存在风险，建议使用官方API
        """
        try:
            with sync_playwright() as p:
                # 启动浏览器
                browser = p.chromium.launch(headless=False)  # headless=False方便调试
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                # 访问小红书发布页面
                page.goto("https://creator.xiaohongshu.com/publish/publish")
                time.sleep(3)
                
                # 这里需要手动登录或使用cookie
                # 注意：自动化登录可能违反服务条款，建议使用官方API
                
                # 填写标题
                title_input = page.locator('input[placeholder*="标题"]').first
                if title_input.is_visible():
                    title_input.fill(title)
                
                # 填写内容
                content_area = page.locator('textarea[placeholder*="内容"]').first
                if content_area.is_visible():
                    # 添加标签到内容
                    full_content = content
                    if tags:
                        tag_text = " ".join([f"#{tag}#" for tag in tags])
                        full_content = f"{content}\n\n{tag_text}"
                    content_area.fill(full_content)
                
                # 上传图片
                for img_path in images:
                    if os.path.exists(img_path):
                        file_input = page.locator('input[type="file"]').first
                        if file_input.is_visible():
                            file_input.set_input_files(img_path)
                            time.sleep(2)  # 等待上传完成
                
                # 点击发布按钮
                publish_button = page.locator('button:has-text("发布")').first
                if publish_button.is_visible():
                    # 注意：这里不实际点击，避免误发布
                    # publish_button.click()
                    print("准备发布，请手动确认...")
                    time.sleep(5)  # 给用户时间确认
                
                browser.close()
                
                return {
                    "success": True,
                    "message": "自动化发布流程完成（需要手动确认）",
                    "method": "automation"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"自动化发布失败: {str(e)}",
                "method": "automation"
            }
    
    def format_content_for_xiaohongshu(self, content: str, tags: List[str]) -> str:
        """格式化内容为小红书风格"""
        # 确保每段之间有适当间距
        formatted = content.replace('\n\n', '\n').replace('\n', '\n\n')
        
        # 添加标签
        if tags:
            tag_line = "\n\n" + " ".join([f"#{tag}#" for tag in tags])
            formatted += tag_line
        
        return formatted
