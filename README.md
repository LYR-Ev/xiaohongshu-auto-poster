# Xiaohongshu Auto Poster

本项目用于：
- 使用本地 Ollama（qwen2.5）生成小红书文案
- 自动生成配图（本地模板）
- 支持本地保存 / Playwright 自动发布（可开关）

## 环境要求

- Python >= 3.9
- Ollama >= 0.15
- 已下载模型：qwen2.5:3b

## 本地运行步骤

### 1. 克隆仓库
```bash
git clone https://github.com/你的用户名/仓库名.git
cd 仓库名
2. 创建虚拟环境
python -m venv venv

Windows
venv\Scripts\Activate

macOS / Linux
source venv/bin/activate

3. 安装依赖
pip install -r requirements.txt

4. 配置环境变量
cp .env.example .env


（按需修改）

5. 启动 Ollama
ollama run qwen2.5:3b

6. 运行示例
python example.py single

发布模式说明

PUBLISH_MODE=local：仅保存到本地

PUBLISH_MODE=auto：使用 Playwright 自动发布


---

## 🧠 三、初始化 Git 仓库（本机）

在项目根目录：

```bash
git init
git status


确认：

✅ .env 不在列表

✅ venv/ 不在列表

然后：

git add .
git commit -m "init: local ollama based xiaohongshu poster"