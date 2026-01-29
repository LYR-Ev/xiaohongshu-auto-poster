# 快速开始指南

## 第一步：安装依赖

```bash
pip install -r requirements.txt
```

如果使用自动化发布功能，还需要安装浏览器：

```bash
playwright install chromium
```

## 第二步：配置API密钥

1. 复制配置文件：
```bash
copy .env.example .env
```

2. 默认使用本地 Ollama（无需 key），无需配置 OpenAI/Claude。

   可选：如果你希望启用 Claude 作为远程兜底：

   ```bash
   pip install anthropic
   ```

   并在 `.env` 中配置：

   - `ANTHROPIC_API_KEY` - Anthropic API密钥（可选：仅在需要 Claude 远程兜底时配置）

## 第三步：测试运行

### 方式1：单次发布测试

```bash
python main.py --mode once --word "serendipity"
```

这会：
1. 生成关于"serendipity"的AI文案
2. 生成配图
3. 尝试发布到小红书（如果没有配置API，会显示自动化流程）

### 方式2：使用示例脚本

```bash
python example.py single
```

## 第四步：配置小红书发布

### 选项A：使用官方API（推荐）

1. 申请小红书开放平台权限
2. 获取 App ID 和 App Secret
3. 在 `.env` 中配置：
   ```
   XIAOHONGSHU_APP_ID=your_app_id
   XIAOHONGSHU_APP_SECRET=your_app_secret
   XIAOHONGSHU_ACCESS_TOKEN=your_access_token
   ```

### 选项B：使用自动化方式（需谨慎）

- 系统会使用浏览器自动化工具
- 需要手动登录小红书账号
- 可能存在违反服务条款的风险

## 第五步：启动定时任务

配置好所有参数后，启动定时自动发布：

```bash
python main.py --mode schedule
```

系统会按照 `.env` 中配置的 `POST_INTERVAL_HOURS` 间隔自动发布。

## 常见问题

### Q: 没有API密钥怎么办？
A: 默认走本地 Ollama（无需 key）。如果你要启用 Claude 远程兜底，才需要配置 `ANTHROPIC_API_KEY`。

### Q: 如何修改文案风格？
A: 编辑 `content_generator.py` 中的 `_build_prompt` 方法，修改提示词。

### Q: 如何调整图片风格？
A: 在调用 `generate_word_image` 时修改 `image_style` 参数，或编辑 `image_generator.py` 中的生成逻辑。

### Q: 定时任务如何停止？
A: 按 `Ctrl+C` 停止程序。

## 下一步

- 查看 `README.md` 了解详细功能
- 查看 `example.py` 了解更多使用示例
- 根据需要自定义各个模块的功能
