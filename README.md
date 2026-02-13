# 小红书自动发帖 · 单词学习

使用本地 Ollama 生成英语单词学习文案，配合 Stable Diffusion 文生图或本地模板生成配图，支持本地保存或自动发布，并记录发帖数据便于分析。

## 环境要求

- Python >= 3.9
- Ollama（已拉取模型，如 `qwen2.5:3b`）
- 可选：Stable Diffusion WebUI（`http://127.0.0.1:7860`）用于文生图，不启用则用本地模板出图

## 快速开始

```bash
# 1. 克隆并进入项目
git clone <你的仓库地址>
cd xiaohongshu-auto-poster

# 2. 虚拟环境
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量
cp .env.example .env
# 按需修改 .env（Ollama 地址、发布模式、SD 地址等）

# 5. 启动 Ollama（另开终端）
ollama run qwen2.5:3b
```

---

## 命令一览

### 主程序 `main.py`

| 命令 | 作用 |
|------|------|
| `python main.py --help` | 查看所有参数说明 |
| `python main.py --word <单词> --theme word [--level CET-4]` | **单次**：生成并保存/发布一篇「单词学习」帖（默认 level=CET-4） |
| `python main.py --theme word` | 单次：随机选一个单词（未指定 `--word` 时用默认词）生成一篇帖 |
| `python main.py --word <单词> --theme <主题>` | 单次：按指定主题生成（如 `--theme 日常用语`），走通用文案模板 |
| `python main.py --mode schedule` | **定时**：按内置间隔循环发帖，Ctrl+C 停止 |
| `python main.py --mode webhook [--port 8080]` | **Webhook 服务**：启动 HTTP 服务，通过请求触发发帖（可传 `word`、`theme` 等） |
| `python main.py --mode analytics` | **数据分析**：从本地数据库统计 Prompt 版本对比、难度对比、最近发帖与互动数据 |

**常用示例：**

```bash
# 发一篇「serendipity」单词帖（CET-4）
python main.py --word serendipity --theme word

# 发一篇六级难度单词帖
python main.py --word abandon --theme word --level CET-6

python main.py --theme word --level CET-6

# 只看数据分析（不发帖）
python main.py --mode analytics

# 定时自动发帖
python main.py --mode schedule

# Webhook 模式，端口 9000
python main.py --mode webhook --port 9000
```


---

### 示例脚本 `example.py`

在运行前会先检查 Ollama 是否可用。

| 命令 | 作用 |
|------|------|
| `python example.py single` | 单次发布示例：发一篇「serendipity」主题为「日常用语」的帖子 |
| `python example.py schedule` | 定时发布示例：启动定时任务，按间隔发帖（Ctrl+C 停止） |
| `python example.py custom` | 自定义内容示例：仅演示文案生成 + 配图（不涉及完整发帖流程） |

---

### 工具脚本

| 命令 | 作用 |
|------|------|
| `python check_ollama.py` | 检查本地 Ollama 是否在运行（默认 `http://localhost:11434`），开发/调试时建议先跑 |
| `python update_interactions.py <post_id> --likes N [--favorites N] [--comments N] [--views N]` | 根据帖子 ID 更新数据库中的互动数据（点赞、收藏、评论、浏览量），用于后续数据分析 |

**示例：**

```bash
python check_ollama.py

python update_interactions.py 1 --likes 10 --favorites 5 --comments 2
```

---

## 发布模式（环境变量）

在 `.env` 中设置 `PUBLISH_MODE`：

- **`local`**（默认）：只把文案和图片保存到本地 `output/` 和 `generated_images/`，不调用小红书发布接口。
- **`auto`**：通过配置的 API 或 Playwright 自动发布到小红书。

---

## 其他说明

- **配图**：默认优先用本地 Stable Diffusion（`USE_SD_TXT2IMG=1`，`SD_API_URL` 指向 WebUI）。若未开 SD 或请求失败，会自动回退到本地模板出图；图片生成失败也不会影响文案保存。
- **去重**：`theme=word` 时，会先查数据库是否已有「同一单词 + level + prompt_version」的记录，若已发过则跳过生成并提示。
- **数据与分析**：发帖会写入本地 SQLite（`posts_data.db`）。`--mode analytics` 与 `DATA_ANALYTICS.md` 用于查看统计与对比。

更细的数据分析用法见 [DATA_ANALYTICS.md](DATA_ANALYTICS.md)。
