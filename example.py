"""
使用示例脚本
演示如何使用各个模块
"""
from main import XiaohongshuAutoPoster
from dotenv import load_dotenv
from check_ollama import check_ollama

load_dotenv()

def example_single_post():
    """示例：单次发布"""
    poster = XiaohongshuAutoPoster()
    
    # 发布一篇关于"serendipity"的帖子
    result = poster.create_and_publish_post(word="serendipity", theme="日常用语")
    
    if result.get('success'):
        print(f"\n✅ 成功发布！")
        print(f"单词: {result['word']}")
        print(f"标题: {result['title']}")
        print(f"图片: {result['image_path']}")
    else:
        print(f"\n❌ 发布失败: {result.get('error')}")


def example_scheduled_posts():
    """示例：定时发布"""
    from trigger_manager import TriggerManager
    
    poster = XiaohongshuAutoPoster()
    
    # 创建触发器，每24小时发布一次
    trigger = TriggerManager(lambda: poster.create_and_publish_post())
    
    # 启动定时任务（会一直运行）
    print("定时任务已启动，按Ctrl+C停止...")
    try:
        trigger.start_scheduler()
    except KeyboardInterrupt:
        print("\n定时任务已停止")


def example_custom_content():
    """示例：自定义内容"""
    from content_generator import ContentGenerator
    from image_generator import ImageGenerator
    
    # 生成自定义主题的文案
    generator = ContentGenerator()
    content = generator.generate_word_content(
        word="resilient",
        theme="商务英语"
    )
    
    print(f"单词: {content['word']}")
    print(f"标题: {content['title']}")
    print(f"\n内容:\n{content['content']}")
    print(f"\n标签: {', '.join(content['tags'])}")
    
    # 生成配图
    img_generator = ImageGenerator()
    image_path = img_generator.generate_word_image(
        word=content['word'],
        meaning="有韧性的",
        image_style="modern"
    )
    print(f"\n图片已生成: {image_path}")


if __name__ == "__main__":
    import sys
    
    # 先检查 Ollama 是否可用，避免在生成阶段才报 ConnectionError
    if not check_ollama():
        sys.exit(1)

    if len(sys.argv) > 1:
        mode = sys.argv[1]
        if mode == "single":
            example_single_post()
        elif mode == "schedule":
            example_scheduled_posts()
        elif mode == "custom":
            example_custom_content()
        else:
            print("用法: python example.py [single|schedule|custom]")
    else:
        print("请选择运行模式:")
        print("  python example.py single    - 单次发布示例")
        print("  python example.py schedule  - 定时发布示例")
        print("  python example.py custom   - 自定义内容示例")
