import requests
import cloudscraper
import json
import os
import sys
import tempfile
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

# TG API 基础 URL
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def check_bot_token():
    """验证 Bot Token 是否有效"""
    print("🔐 验证 Bot Token...")
    try:
        r = requests.get(f"{TG_API}/getMe", timeout=10)
        data = r.json()
        if data.get("ok"):
            bot_name = data["result"].get("username", "unknown")
            print(f"✅ Bot 验证成功: @{bot_name}")
            return True
        else:
            print(f"❌ Bot Token 无效: {data.get('description', '未知错误')}")
            return False
    except Exception as e:
        print(f"❌ 无法连接 Telegram API: {e}")
        return False


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


def tg_send_photo(image_url, caption=""):
    """下载预览图并发送到 Telegram"""
    print(f"  ⬇️  下载预览图...")
    file_path = download_file(image_url)
    if not file_path:
        print(f"  ❌ 预览图下载失败")
        return False

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{TG_API}/sendPhoto",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                },
                files={"photo": f},
                timeout=60
            )
        if r.status_code == 200:
            print(f"  ✅ 预览图发送成功")
            return True
        else:
            print(f"  ❌ 预览图发送失败: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ 预览图发送异常: {e}")
        return False
    finally:
        try:
            os.unlink(file_path)
        except:
            pass


def tg_send_file(image_url, caption=""):
    """下载原图并发送到 Telegram"""
    print(f"  ⬇️  下载原图...")
    file_path = download_file(image_url)
    if not file_path:
        print(f"  ❌ 原图下载失败")
        return False

    actual_size = os.path.getsize(file_path)
    if actual_size > MAX_FILE_SIZE:
        print(f"  ⚠️  下载后文件过大 ({actual_size / 1024 / 1024:.1f} MB)，跳过")
        os.unlink(file_path)
        return False

    try:
        with open(file_path, "rb") as f:
            r = requests.post(
                f"{TG_API}/sendDocument",
                data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                },
                files={"document": f},
                timeout=120
            )
        if r.status_code == 200:
            print(f"  ✅ 原图发送成功")
            return True
        else:
            print(f"  ❌ 原图发送失败: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"  ❌ 原图发送异常: {e}")
        return False
    finally:
        try:
            os.unlink(file_path)
        except:
            pass


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


def is_today(timestamp):
    """检查 Unix 时间戳是否是今天（UTC+8）"""
    dt = datetime.fromtimestamp(timestamp, tz=TZ)
    today = datetime.now(TZ)
    return dt.date() == today.date()


def fetch_page(site_url, page):
    """抓取单页数据（不带日期过滤，在代码中过滤）"""
    params = {
        "tags": TAGS,
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
    # 验证 Bot Token
    if not check_bot_token():
        print("⛔ 请检查 config.py 中的 BOT_TOKEN 是否正确！")
        sys.exit(1)

    today = datetime.now(TZ).strftime("%Y-%m-%d")
    print(f"📅 当天日期: {today}")
    print(f"🏷️  标签: {TAGS}")

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
            posts = fetch_page(site, page)

            if posts is None:
                print(f"❌ 请求失败，切换备选站点")
                break

            if len(posts) == 0:
                print(f"📭 本页无数据，停止翻页")
                site_succeeded = True
                break

            print(f"📬 获取到 {len(posts)} 条结果")

            today_count = 0
            old_count = 0

            for p in posts:
                pid = str(p.get("id", ""))
                created_at = p.get("created_at", 0)

                if not pid:
                    continue

                # 检查是否是今天的内容
                if not is_today(created_at):
                    created_str = datetime.fromtimestamp(created_at, tz=TZ).strftime("%Y-%m-%d %H:%M")
                    print(f"  ⏭️  非当天内容: {pid} (创建于 {created_str})")
                    old_count += 1
                    continue

                today_count += 1

                if pid in db:
                    print(f"  ⏭️  跳过已发送: {pid}")
                    continue

                # sample_url: 中等质量示例图，比 preview 清晰
                sample = p.get("sample_url") or p.get("preview_url")
                # jpeg_url: JPEG 版原图，比 file_url (PNG) 小很多
                jpeg = p.get("jpeg_url") or p.get("file_url")
                # file_url: 原始文件（备用）
                original = p.get("file_url")

                if not sample or not original:
                    continue

                # 构建消息
                tags = p.get("tags", "").strip()
                source = p.get("source", "")
                score = p.get("score", 0)
                rating = p.get("rating", "?")

                caption_lines = [
                    f"🖼 <b>ID</b>: <code>{pid}</code>",
                    f"⭐ <b>Score</b>: {score}",
                    f"🔒 <b>Rating</b>: {rating}",
                    f"📅 <b>Date</b>: {today}",
                ]

                if tags:
                    tag_display = tags[:200] + "..." if len(tags) > 200 else tags
                    caption_lines.append(f"🏷 <b>Tags</b>: {tag_display}")

                if source:
                    caption_lines.append(f"🔗 <a href=\"{source}\">Source</a>")

                caption_lines.append(f"🌐 <a href=\"{original}\">Original</a>")

                caption = "\n".join(caption_lines)

                print(f"  📤 发送: {pid} (rating:{rating})")

                # 发送示例图作为预览（比 preview_url 更清晰）
                tg_send_photo(sample, caption)

                # 检查 JPEG 原图大小（比 PNG file_url 小很多）
                jpeg_size = get_file_size(jpeg)
                print(f"  📦 JPEG 大小: {jpeg_size / 1024 / 1024:.1f} MB")

                if 0 < jpeg_size <= MAX_FILE_SIZE:
                    tg_send_file(jpeg, caption)
                else:
                    if jpeg_size > MAX_FILE_SIZE:
                        print(f"  ⚠️  JPEG 过大 ({jpeg_size / 1024 / 1024:.1f} MB)，跳过")
                    else:
                        print(f"  ⚠️  无法获取文件大小，跳过原图")

                db.add(pid)
                total_sent += 1

            print(f"  📊 本页统计: 当天 {today_count} 条, 非当天 {old_count} 条")

            # 如果本页没有当天内容，说明已经超出今天的范围，停止翻页
            if today_count == 0 and old_count > 0:
                print(f"📭 本页无当天内容，停止翻页")
                site_succeeded = True
                break

            # 页间保存，防止中途失败丢数据
            save_db(db)

        if not site_succeeded:
            site_succeeded = True

    save_db(db)
    print(f"\n🎉 完成！共发送 {total_sent} 条新内容")
    print(f"💾 数据库现有 {len(db)} 条记录")


if __name__ == "__main__":
    main()