"""工具函数：HTTP 请求、文件下载、数据库、文件大小等"""
import requests
import cloudscraper
import json
import os
import tempfile
from datetime import datetime, timezone, timedelta
from config import DAYS_BACK

# 时区：Asia/Shanghai (UTC+8)
TZ = timezone(timedelta(hours=8))

scraper = cloudscraper.create_scraper()


def safe_get(url, params=None):
    """先尝试 requests，失败后 fallback 到 cloudscraper"""
    try:
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            print(f"[requests] 成功: {r.url}")
            return r
    except Exception as e:
        print(f"[requests] 失败: {e}")

    print(f"[cloudscraper] fallback: {url}")
    try:
        r = scraper.get(url, params=params, timeout=15)
        if r.status_code == 200:
            print(f"[cloudscraper] 成功: {r.url}")
            return r
    except Exception as e:
        print(f"[cloudscraper] 也失败了: {e}")

    return None


def download_file(url):
    """下载文件到临时路径，返回文件路径"""
    try:
        r = requests.get(url, timeout=30, stream=True)
        if r.status_code == 200:
            ext = url.split(".")[-1][:4]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            for chunk in r.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp.close()
            return tmp.name
    except:
        pass

    try:
        r = scraper.get(url, timeout=30, stream=True)
        if r.status_code == 200:
            ext = url.split(".")[-1][:4]
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}")
            for chunk in r.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp.close()
            return tmp.name
    except:
        pass

    return None


def get_file_size(url):
    """获取文件大小"""
    try:
        r = requests.head(url, timeout=10, allow_redirects=True)
        if "Content-Length" in r.headers:
            return int(r.headers["Content-Length"])
    except:
        pass

    try:
        r = scraper.head(url, timeout=15, allow_redirects=True)
        return int(r.headers.get("Content-Length", 0))
    except:
        return 0


def load_db():
    """加载已发送 ID 数据库"""
    if not os.path.exists("db.json"):
        return set()
    with open("db.json", "r") as f:
        data = json.load(f)
    if isinstance(data, dict):
        return set(data.get("ids", []))
    if isinstance(data, list):
        return set(data)
    return set()


def save_db(db):
    """保存已发送 ID 数据库"""
    with open("db.json", "w") as f:
        json.dump({"ids": list(db)}, f, indent=2)


def is_within_range(timestamp):
    """检查 Unix 时间戳是否在最近 N 天内（UTC+8）"""
    dt = datetime.fromtimestamp(timestamp, tz=TZ)
    now = datetime.now(TZ)
    start = (now - timedelta(days=DAYS_BACK)).replace(hour=0, minute=0, second=0)
    return dt >= start