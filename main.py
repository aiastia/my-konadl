import requests
import cloudscraper
import json
import os
from datetime import datetime, timezone, timedelta
from config import *

# 优先 Konachan，Yande.re 作为备选
SITES = [
    "https://konachan.com/post.json",
    "https://yande.re/post.json"
]

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


def load_db():
    """加载已发送 ID 数据库"""
    if not os.path.exists("db.json"):
        return set()
    with open("db.json", "r") as f:
        return set(json.load(f))


def save_db(db):
    """保存已发送 ID 数据库"""
    with open("db.json", "w") as f:
        json.dump(list(db), f, indent=2)


def tg_send_photo(url, caption=""):
    """发送预览图到 Telegram"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
            data={
                "chat_id": CHAT_ID,
                "photo": url,
                "caption": caption,
                "parse_mode": "HTML"
            },
            timeout=30
        )
        if r.status_code == 200:
            print(f"  ✅ 预览图发送成功")
        else:
            print(f"  ❌ 预览图发送失败: {r.text}")
        return r
    except Exception as e:
        print(f"  ❌ 预览图发送异常: {e}")
        return None


def tg_send_file(url, caption=""):
    """发送原图文件到 Telegram"""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument",
            data={
                "chat_id": CHAT_ID,
                "document": url,
                "caption": caption,
                "parse_mode": "HTML"
            },
            timeout=60
        )
        if r.status_code == 200:
            print(f"  ✅ 原图发送成功")
        else:
            print(f"  ❌ 原图发送失败: {r.text}")
        return r
    except Exception as e:
        print(f"  ❌ 原图发送异常: {e}")
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


def fetch_page(site_url, tags_with_date, page):
    """抓取单页数据"""
    params = {
        "tags": tags_with_date,
        "limit": LIMIT,
        "page": page
    }
    r = safe_get(site_url, params=params)
    if r is None:
        return None
    try:
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except:
        return []


def main():
    today = datetime.now(TZ).strftime("%Y-%m-%d")
    print(f"📅 当天日期: {today}")
    print(f"🏷️  标签: {TAGS}")

    # 拼接日期过滤标签
    tags_with_date = f"{TAGS} date:{today}"
    print(f"🔍 查询标签: {tags_with_date}")

    db = load_db()
    print(f"💾 已有记录: {len(db)} 条")

    total_sent = 0
    site_succeeded = False

    for site in SITES:
        if site_succeeded:
            break

        print(f"\n🌐 尝试站点: {site}")

        for page in range(1, MAX_PAGES + 1):
            print(f"\n📄 第 {page} 页")
            posts = fetch_page(site, tags_with_date, page)

            if posts is None:
                print(f"❌ 请求失败，切换备选站点")
                break

            if len(posts) == 0:
                print(f"📭 本页无数据，停止翻页")
                site_succeeded = True
                break

            print(f"📬 获取到 {len(posts)} 条结果")

            for p in posts:
                pid = str(p.get("id", ""))

                if not pid:
                    continue

                if pid in db:
                    print(f"  ⏭️  跳过已发送: {pid}")
                    continue

                preview = p.get("preview_url")
                original = p.get("file_url")

                if not preview or not original:
                    continue

                # 构建消息
                tags = p.get("tags", "").strip()
                source = p.get("source", "")
                score = p.get("score", 0)

                caption_lines = [
                    f"🖼 <b>ID</b>: <code>{pid}</code>",
                    f"⭐ <b>Score</b>: {score}",
                    f"📅 <b>Date</b>: {today}",
                ]

                if tags:
                    # 截断过长的 tags
                    tag_display = tags[:200] + "..." if len(tags) > 200 else tags
                    caption_lines.append(f"🏷 <b>Tags</b>: {tag_display}")

                if source:
                    caption_lines.append(f"🔗 <a href=\"{source}\">Source</a>")

                caption_lines.append(f"🌐 <a href=\"{original}\">Original</a>")

                caption = "\n".join(caption_lines)

                print(f"  📤 发送: {pid}")

                # 发送预览图
                tg_send_photo(preview, caption)

                # 检查原图大小
                size = get_file_size(original)
                print(f"  📦 原图大小: {size / 1024 / 1024:.1f} MB")

                if 0 < size <= MAX_FILE_SIZE:
                    tg_send_file(original, caption)
                else:
                    if size > MAX_FILE_SIZE:
                        print(f"  ⚠️  原图过大 ({size / 1024 / 1024:.1f} MB)，跳过")
                    else:
                        print(f"  ⚠️  无法获取文件大小，跳过原图")

                db.add(pid)
                total_sent += 1

            # 页间保存，防止中途失败丢数据
            save_db(db)

        site_succeeded = True

    save_db(db)
    print(f"\n🎉 完成！共发送 {total_sent} 条新内容")
    print(f"💾 数据库现有 {len(db)} 条记录")


if __name__ == "__main__":
    main()