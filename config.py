import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "@your_channel")

TAGS = "rating:s -nude -sex"
LIMIT = 20          # 每页数量
MAX_PAGES = 10      # 最多翻几页
DAYS_BACK = 1       # 回溯天数（0=只今天, 1=今天+昨天）

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# 数据库最大保留 ID 数量（超过时自动清理旧记录）
# 程序每次运行最多处理 MAX_PAGES * LIMIT = 200 条，保留 500 足够去重
DB_MAX_IDS = 300
