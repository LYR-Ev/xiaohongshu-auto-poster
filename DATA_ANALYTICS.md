# 数据记录与分析使用指南

系统会自动记录每次发帖的元数据，并支持后续补充互动数据，用于分析和优化内容策略。

## 📊 数据记录内容

每次发帖会自动记录：

- **prompt_version**: Prompt 版本（如 `word_learning_v1`）
- **word**: 单词
- **level**: 难度水平（CET-4、CET-6、GRE 等）
- **title**: 标题
- **tags**: 标签列表
- **image_suggestion**: 配图建议
- **created_at**: 生成时间
- **published_at**: 发布时间

## 🔄 更新互动数据

### 方式1：命令行工具

```bash
# 更新帖子 ID 为 1 的互动数据
python update_interactions.py 1 --likes 10 --favorites 5 --comments 2 --views 100
```

### 方式2：Python API

```python
from main import XiaohongshuAutoPoster

poster = XiaohongshuAutoPoster()

# 发布帖子
result = poster.create_and_publish_post(word="abandon", theme="word", level="CET-4")
post_id = result.get("post_id")

# 后续更新互动数据
poster.update_post_interactions(
    post_id=post_id,
    likes=10,
    favorites=5,
    comments=2,
    views=100
)
```

### 方式3：直接使用 DataRecorder

```python
from data_recorder import DataRecorder

recorder = DataRecorder()
recorder.update_interactions(
    post_id=1,
    likes=10,
    favorites=5,
    comments=2
)
```

## 📈 数据分析

### 查看分析报告

```bash
python main.py --mode analytics
```

输出示例：

```
🔍 Prompt 版本对比：
  word_learning_v1: 平均点赞 15.5, 平均收藏 8.2, 平均评论 3.1 （共 20 篇）

📚 难度水平对比：
  CET-4: 平均点赞 18.3, 平均收藏 9.5, 平均评论 4.2 （共 15 篇）
  CET-6: 平均点赞 12.1, 平均收藏 6.8, 平均评论 2.5 （共 10 篇）

📝 最近发帖：
  [2026-01-23 10:30:00] abandon (CET-4) - 👍10 ⭐5 💬2
```

### Python API 查询

```python
from main import XiaohongshuAutoPoster

poster = XiaohongshuAutoPoster()
analytics = poster.get_analytics()

# 对比不同 Prompt 版本
for version in analytics["prompt_versions"]:
    print(f"{version['prompt_version']}: {version['avg_likes']} 平均点赞")

# 对比不同难度
for level in analytics["levels"]:
    print(f"{level['level']}: {level['avg_likes']} 平均点赞")
```

### 自定义查询

```python
from data_recorder import DataRecorder

recorder = DataRecorder()

# 获取特定条件的统计
stats = recorder.get_post_stats(
    prompt_version="word_learning_v1",
    level="CET-4"
)
print(f"总发帖数: {stats['total_posts']}")
print(f"平均点赞: {stats['avg_likes']}")

# 获取最近发帖
recent = recorder.get_recent_posts(limit=10)
for post in recent:
    print(f"{post['word']}: 👍{post['likes']} ⭐{post['favorites']}")
```

## 🎯 使用场景

### 1. 对比不同 Prompt 版本

```python
# 发布时使用不同版本（通过修改 prompts/word_learning.py 中的 PROMPT_VERSION）
# 然后查看对比
analytics = poster.get_analytics()
versions = analytics["prompt_versions"]
best_version = max(versions, key=lambda x: x["avg_likes"])
print(f"最佳版本: {best_version['prompt_version']}")
```

### 2. 对比不同难度水平

```python
# 分别发布 CET-4 和 CET-6 的内容
poster.create_and_publish_post(word="abandon", theme="word", level="CET-4")
poster.create_and_publish_post(word="serendipity", theme="word", level="CET-6")

# 查看对比
levels = poster.get_analytics()["levels"]
for level in levels:
    print(f"{level['level']}: {level['avg_likes']} 平均点赞")
```

### 3. A/B 测试不同互动钩子

在 Prompt 中尝试不同的结尾互动方式：

- 版本 A: "记得点赞收藏哦～"
- 版本 B: "评论区说说你的记忆方法吧！"
- 版本 C: "关注我，每天学一个单词"

通过 `prompt_version` 区分，然后对比平均互动数据。

## 💾 数据库位置

数据存储在 `posts_data.db`（SQLite 数据库），可以使用 SQLite 工具直接查询：

```bash
sqlite3 posts_data.db

# 查看所有帖子
SELECT * FROM posts;

# 查看互动数据
SELECT p.word, p.level, i.likes, i.favorites 
FROM posts p 
JOIN interactions i ON p.id = i.post_id 
ORDER BY i.likes DESC;
```

## 🔧 高级用法

### 导出为 CSV

```python
import csv
from data_recorder import DataRecorder

recorder = DataRecorder()
posts = recorder.get_recent_posts(limit=1000)

with open("posts_export.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=["word", "level", "prompt_version", "likes", "favorites", "comments"])
    writer.writeheader()
    for post in posts:
        writer.writerow({
            "word": post["word"],
            "level": post["level"],
            "prompt_version": post["prompt_version"],
            "likes": post["likes"],
            "favorites": post["favorites"],
            "comments": post["comments"],
        })
```

### 禁用数据记录

如果不需要记录数据：

```python
poster = XiaohongshuAutoPoster(enable_recording=False)
```

## 📝 注意事项

1. **数据记录是自动的**：每次调用 `create_and_publish_post` 都会自动记录
2. **互动数据需要手动更新**：系统不会自动抓取小红书数据，需要手动或通过接口补充
3. **数据库文件**：`posts_data.db` 会在首次运行时自动创建
4. **数据持久化**：所有数据保存在本地 SQLite 数据库，不会丢失
