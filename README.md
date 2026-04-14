# 🖼️ Konachan / Yande.re 图片爬虫 + Telegram 推送

自动从 Konachan / Yande.re 抓取当日图片，并通过 Telegram Bot 推送到指定频道。

## ✨ 功能特性

- 🌐 **多站支持**：Konachan 优先，Yande.re 备选
- 🔄 **自动 Fallback**：requests → cloudscraper 双重切换，抗 Cloudflare
- 📅 **当天过滤**：只抓取当天上传的图片
- 📄 **多页抓取**：支持翻页获取更多内容
- 🚫 **自动去重**：基于 db.json 本地去重，不重复发送
- 📱 **TG 推送**：预览图 + 原图文件（超过 50MB 自动跳过）
- 🎨 **美化消息**：HTML 格式 Caption（ID、Score、Tags、Source 链接）
- ⏰ **自动运行**：GitHub Actions 每天北京时间 10:00 自动执行
- 🏷️ **灵活标签**：支持 `rating:s`、`-nude`、`-sex` 等高级过滤

## 📦 项目结构

```
my-konadl/
├── .github/workflows/run.yml   # GitHub Actions 配置
├── .gitignore
├── README.md
├── config.py                   # 配置文件
├── db.json                     # 去重数据库（自动维护）
├── main.py                     # 核心爬虫逻辑
└── requirements.txt            # Python 依赖
```

## ⚙️ 配置说明

编辑 `config.py`：

```python
BOT_TOKEN = "YOUR_BOT_TOKEN"          # Telegram Bot Token
CHAT_ID = "@your_channel"             # 推送目标（频道/群组/个人）

TAGS = "rating:s -nude -sex"          # 搜索标签
LIMIT = 20                            # 每页数量
MAX_PAGES = 3                         # 最多翻页数

MAX_FILE_SIZE = 50 * 1024 * 1024      # 原图最大 50MB
```

### 标签语法（Konachan / Yande.re）

| 语法 | 说明 |
|------|------|
| `rating:s` | Safe 级别 |
| `rating:q` | Questionable 级别 |
| `rating:e` | Explicit 级别 |
| `-tag` | 排除某个标签 |
| `tag1 tag2` | 多标签同时匹配 |

## 🚀 部署步骤

### 1. Fork 或创建仓库

### 2. 修改配置
编辑 `config.py`，填入你的 Bot Token 和频道 ID。

### 3. 推送代码
```bash
git add .
git commit -m "update config"
git push
```

### 4. 启用 GitHub Actions
进入仓库的 **Settings → Actions → General**，允许 Actions 运行。

### 5. 手动测试（可选）
进入 **Actions → crawler → Run workflow** 手动触发一次。

## 🔐 安全建议（推荐）

如果你的仓库是公开的，建议使用 GitHub Secrets：

1. 在 `config.py` 中改为读取环境变量：
```python
import os
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHAT_ID = os.environ.get("CHAT_ID", "")
```

2. 在仓库 **Settings → Secrets and variables → Actions** 中添加：
   - `BOT_TOKEN`
   - `CHAT_ID`

3. 在 `.github/workflows/run.yml` 中添加环境变量：
```yaml
- name: Run crawler
  run: python main.py
  env:
    BOT_TOKEN: ${{ secrets.BOT_TOKEN }}
    CHAT_ID: ${{ secrets.CHAT_ID }}
```

## 📊 运行日志示例

```
📅 当天日期: 2026-04-14
🏷️  标签: rating:s -nude -sex
🔍 查询标签: rating:s -nude -sex date:2026-04-14
💾 已有记录: 42 条

🌐 尝试站点: https://konachan.com/post.json

📄 第 1 页
📬 获取到 20 条结果
  📤 发送: 123456
  ✅ 预览图发送成功
  📦 原图大小: 12.3 MB
  ✅ 原图发送成功

🎉 完成！共发送 5 条新内容
💾 数据库现有 47 条记录
```

## 🔧 自定义

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `TAGS` | `rating:s -nude -sex` | 搜索标签 |
| `LIMIT` | 20 | 每页数量（最大 100） |
| `MAX_PAGES` | 3 | 最大翻页数 |
| `MAX_FILE_SIZE` | 50MB | 原图大小上限 |

## 📄 License

MIT