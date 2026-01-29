"""
小红书自动发布系统 - 主程序
整合AI文案生成、图片生成和自动发布功能
"""
import os
import sys
from datetime import datetime
from typing import Optional
from content_generator import ContentGenerator
from image_generator import ImageGenerator
from xiaohongshu_publisher import XiaohongshuPublisher
from trigger_manager import TriggerManager, WebhookTrigger
from data_recorder import DataRecorder
from prompts.word_learning import PROMPT_VERSION

class XiaohongshuAutoPoster:
    """小红书自动发布系统"""
    
    def __init__(self, enable_recording: bool = True):
        self.content_generator = ContentGenerator()
        self.image_generator = ImageGenerator()
        self.publisher = XiaohongshuPublisher()
        self.recorder = DataRecorder() if enable_recording else None
        # 发布模式：local = 只本地保存，不自动发布；auto = 通过 API / Playwright 自动发布
        self.publish_mode = os.getenv("PUBLISH_MODE", "local")
    
    def create_and_publish_post(self, word: str = None, theme: str = None, level: str = "CET-4") -> dict:
        """
        创建并发布一篇小红书帖子
        
        Args:
            word: 指定单词（可选）
            theme: 主题（可选）
        
        Returns:
            发布结果字典
        """
        try:
            print("=" * 50)
            print(f"[{datetime.now()}] 开始创建小红书帖子...")
            print("=" * 50)
            
            # 1. 生成文案（theme=="word" 走新模板 + 结构化解析，否则走老逻辑）
            print("\n📝 步骤1: 生成AI文案...")
            if theme == "word":
                word_for_post = word or "abandon"
                # 数据库级软去重：生成前先判断是否已生成过
                if self.recorder and self.recorder.has_posted(word_for_post, level, PROMPT_VERSION):
                    print(f"跳过已生成过的单词: {word_for_post}")
                    return {
                        "success": True,
                        "skipped": True,
                        "word": word_for_post,
                        "level": level,
                        "prompt_version": PROMPT_VERSION,
                        "message": "已生成过，已跳过",
                    }
                text = self.content_generator.generate_word_post(word_for_post, level=level)
                content_data = self.content_generator.parse_structured_word_post(text, word_for_post)
            else:
                content_data = self.content_generator.generate_word_content(word=word, theme=theme)
            print(f"✓ 单词: {content_data['word']}")
            print(f"✓ 标题: {content_data['title']}")
            print(f"✓ 标签: {', '.join(content_data['tags'])}")
            
            # 提取 prompt_version（从 meta 或使用默认值）
            meta = content_data.get("meta", {})
            prompt_version = meta.get("prompt", PROMPT_VERSION) if meta else PROMPT_VERSION
            
            # 2. 生成图片（明确输入职责：优先用「配图建议」构建 image_prompt，否则用释义兜底）
            print("\n🎨 步骤2: 生成配图...")
            image_suggestion = content_data.get("image_suggestion")
            meaning = self._extract_meaning(content_data["content"]) if not image_suggestion else None
            
            image_path = self.image_generator.generate_word_image(
                word=content_data["word"],
                image_prompt=image_suggestion,  # 明确的配图建议
                meaning=meaning,  # 兜底用
                image_style="modern",
            )
            print(f"✓ 图片已生成: {image_path}")
            
            # 3. 格式化内容
            print("\n📋 步骤3: 格式化内容...")
            formatted_content = self.publisher.format_content_for_xiaohongshu(
                content=content_data['content'],
                tags=content_data['tags']
            )
            
            # 4. 发布到小红书（或本地保存）
            print("\n🚀 步骤4: 发布/保存帖子...")
            if self.publish_mode == "auto":
                # 自动发布（API / Playwright）
                result = self.publisher.publish_post(
                    title=content_data['title'],
                    content=formatted_content,
                    images=[image_path],
                    tags=content_data['tags'],
                )
            else:
                # 仅本地保存，不实际调用小红书
                result = self._save_post_to_local(
                    title=content_data['title'],
                    content=formatted_content,
                    image_path=image_path,
                    word=content_data['word'],
                    tags=content_data['tags'],
                )
            
            if result.get('success'):
                print("\n✅ 发布成功！")
            else:
                print(f"\n❌ 发布失败: {result.get('message')}")
            
            # 5. 记录发帖数据（用于后续分析和优化）
            post_id = None
            if self.recorder:
                try:
                    post_url = result.get('data', {}).get('post_url') if isinstance(result.get('data'), dict) else None
                    post_id = self.recorder.record_post(
                        word=content_data['word'],
                        level=level if theme == "word" else None,
                        prompt_version=prompt_version,
                        title=content_data['title'],
                        tags=content_data['tags'],
                        image_suggestion=content_data.get('image_suggestion'),
                        post_url=post_url,
                    )
                    print(f"✓ 数据已记录（ID: {post_id}）")
                except Exception as e:
                    print(f"⚠️ 数据记录失败: {e}")
            
            return {
                "success": result.get('success', False),
                "word": content_data['word'],
                "title": content_data['title'],
                "image_path": image_path,
                "publish_result": result,
                "post_id": post_id,  # 用于后续更新互动数据
            }
        
        except Exception as e:
            error_msg = f"创建帖子时发生错误: {str(e)}"
            print(f"\n❌ {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
    
    def _extract_meaning(self, content: str) -> str:
        """从内容中提取中文释义（简单实现）"""
        # 尝试查找常见的中文释义格式
        import re
        
        # 查找"释义："、"意思："等关键词后的内容
        patterns = [
            r'释义[：:]\s*([^\n]+)',
            r'意思[：:]\s*([^\n]+)',
            r'含义[：:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                meaning = match.group(1).strip()
                # 清理多余字符
                meaning = re.sub(r'[#*_`]', '', meaning)
                if len(meaning) <= 20:  # 限制长度
                    return meaning
        
        return ""

    def _save_post_to_local(
        self,
        title: str,
        content: str,
        image_path: str,
        word: str,
        tags: Optional[list] = None,
    ) -> dict:
        """
        以本地文件形式保存帖子内容，而不真正发布到小红书。

        返回结构与 publish_post 类似，方便上层统一处理。
        """
        os.makedirs("output", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_word = word.replace(" ", "_") if word else "post"
        text_path = os.path.join("output", f"{safe_word}_{ts}.txt")
        json_path = os.path.join("output", f"{safe_word}_{ts}.json")

        with open(text_path, "w", encoding="utf-8") as f:
            f.write(f"{title}\n\n")
            f.write(content)
            if tags:
                f.write("\n\n")
                f.write(" ".join(f"#{t}#" for t in tags))

        # 同步保存一份 JSON，便于后续二次编辑/批量发布
        post_data = {
            "word": word,
            "title": title,
            "content": content,
            "tags": tags or [],
            "image_path": image_path,
            "created_at": ts,
        }
        try:
            import json

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            # JSON 保存失败不影响主流程（仍然保留 txt + 图片路径）
            print(f"⚠️ JSON 保存失败: {e}")

        print(f"📝 已保存文案到本地: {text_path}")
        print(f"🧾 已保存结构化 JSON: {json_path}")
        print(f"🖼 图片路径: {image_path}")
        print("👉 当前为本地保存模式（PUBLISH_MODE=local），请手动上传到小红书。")

        return {
            "success": True,
            "message": "已保存到本地（未实际发布）",
            "method": "local",
            "text_path": text_path,
            "json_path": json_path,
            "image_path": image_path,
        }
    def update_post_interactions(
        self,
        post_id: int,
        likes: Optional[int] = None,
        favorites: Optional[int] = None,
        comments: Optional[int] = None,
        views: Optional[int] = None,
    ) -> bool:
        """
        更新帖子互动数据（点赞、收藏、评论、浏览量）
        
        Args:
            post_id: 帖子 ID（从 create_and_publish_post 返回）
            likes: 点赞数
            favorites: 收藏数
            comments: 评论数
            views: 浏览量
        
        Returns:
            是否更新成功
        """
        if not self.recorder:
            print("⚠️ 数据记录功能未启用")
            return False
        
        return self.recorder.update_interactions(
            post_id=post_id,
            likes=likes,
            favorites=favorites,
            comments=comments,
            views=views,
        )
    
    def get_analytics(self) -> dict:
        """
        获取数据分析结果
        
        Returns:
            包含各种对比分析的字典
        """
        if not self.recorder:
            return {"error": "数据记录功能未启用"}
        
        return {
            "prompt_versions": self.recorder.compare_prompt_versions(),
            "levels": self.recorder.compare_levels(),
            "recent_posts": self.recorder.get_recent_posts(limit=10),
        }


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='小红书自动发布系统')
    parser.add_argument('--word', type=str, help='指定要学习的单词')
    parser.add_argument('--theme', type=str, help='主题（如：word、日常用语、商务英语等）')
    parser.add_argument('--level', type=str, default='CET-4', help='难度水平（CET-4、CET-6、GRE等），默认CET-4')
    parser.add_argument('--mode', type=str, choices=['once', 'schedule', 'webhook', 'analytics'], 
                       default='once', help='运行模式：once(单次), schedule(定时), webhook(Webhook服务), analytics(数据分析)')
    parser.add_argument('--port', type=int, default=8080, help='Webhook服务端口')
    
    args = parser.parse_args()
    
    # 创建发布系统实例
    poster = XiaohongshuAutoPoster()
    
    if args.mode == 'once':
        # 单次执行
        result = poster.create_and_publish_post(word=args.word, theme=args.theme, level=args.level)
        sys.exit(0 if result.get('success') else 1)
    
    elif args.mode == 'analytics':
        # 数据分析模式
        print("=" * 50)
        print("📊 数据分析")
        print("=" * 50)
        analytics = poster.get_analytics()
        
        if "error" in analytics:
            print(f"❌ {analytics['error']}")
            sys.exit(1)
        
        print("\n🔍 Prompt 版本对比：")
        for item in analytics.get("prompt_versions", []):
            print(f"  {item['prompt_version']}: "
                  f"平均点赞 {item['avg_likes']}, "
                  f"平均收藏 {item['avg_favorites']}, "
                  f"平均评论 {item['avg_comments']} "
                  f"（共 {item['total_posts']} 篇）")
        
        print("\n📚 难度水平对比：")
        for item in analytics.get("levels", []):
            print(f"  {item['level']}: "
                  f"平均点赞 {item['avg_likes']}, "
                  f"平均收藏 {item['avg_favorites']}, "
                  f"平均评论 {item['avg_comments']} "
                  f"（共 {item['total_posts']} 篇）")
        
        print("\n📝 最近发帖：")
        for post in analytics.get("recent_posts", [])[:5]:
            print(f"  [{post['created_at']}] {post['word']} ({post['level']}) - "
                  f"👍{post['likes']} ⭐{post['favorites']} 💬{post['comments']}")
        
        sys.exit(0)
    
    elif args.mode == 'schedule':
        # 定时任务模式
        print("启动定时任务模式...")
        trigger = TriggerManager(lambda: poster.create_and_publish_post())
        try:
            trigger.start_scheduler()
        except KeyboardInterrupt:
            print("\n程序已停止")
    
    elif args.mode == 'webhook':
        # Webhook模式
        print("启动Webhook服务模式...")
        webhook = WebhookTrigger(
            callback=lambda **kwargs: poster.create_and_publish_post(
                word=kwargs.get('word'),
                theme=kwargs.get('theme')
            ),
            port=args.port
        )
        webhook.start_server()


if __name__ == "__main__":
    main()
