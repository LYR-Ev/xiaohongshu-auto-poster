"""
更新互动数据的工具脚本
用于手动或通过接口更新帖子的点赞、收藏、评论数
"""
import sys
from data_recorder import DataRecorder


def update_interactions_cli():
    """命令行工具：更新互动数据"""
    if len(sys.argv) < 3:
        print("用法: python update_interactions.py <post_id> [--likes N] [--favorites N] [--comments N] [--views N]")
        print("\n示例:")
        print("  python update_interactions.py 1 --likes 10 --favorites 5 --comments 2")
        sys.exit(1)
    
    try:
        post_id = int(sys.argv[1])
    except ValueError:
        print(f"❌ 无效的 post_id: {sys.argv[1]}")
        sys.exit(1)
    
    # 解析参数
    likes = None
    favorites = None
    comments = None
    views = None
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--likes" and i + 1 < len(sys.argv):
            likes = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--favorites" and i + 1 < len(sys.argv):
            favorites = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--comments" and i + 1 < len(sys.argv):
            comments = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--views" and i + 1 < len(sys.argv):
            views = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1
    
    # 更新数据
    recorder = DataRecorder()
    success = recorder.update_interactions(
        post_id=post_id,
        likes=likes,
        favorites=favorites,
        comments=comments,
        views=views,
    )
    
    if success:
        print(f"✅ 已更新帖子 {post_id} 的互动数据")
    else:
        print(f"❌ 更新失败（可能 post_id 不存在）")


if __name__ == "__main__":
    update_interactions_cli()
