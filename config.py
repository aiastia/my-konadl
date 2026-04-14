import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID", "@your_channel")

TAGS = "rating:s -nude -sex"
LIMIT = 20          # 每页数量
MAX_PAGES = 3       # 最多翻几页

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB