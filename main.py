"""KonaDL 主程序：从 Konachan/Yande.re 抓取图片发送到 Telegram"""
import sys
import time
from datetime import datetime, timedelta, timezone

from config import TAGS, LIMIT, MAX_PAGES, DAYS_BACK, MAX_FILE_SIZE
from utils import TZ, safe_get, download_file, get_file_size, load_db, save_db, is_within_range
from telegram import check_bot_token, tg_send_message, tg_send_photo, tg_send_file, SEND_DELAY

# 优先 Konachan，Yande.re 作为备选
SITES = [
    "https://konachan.com/post.json",
    "https://yande.re/post.json"
]


def fetch_page(site_url, page):
    """抓取单页数据"""
    params = {"tags": TAGS, "limit": LIMIT, "page": page}
    r = safe_get(site_url, params=params)
    if r is None:
        return None
    try:
        data = r.json()
        return data if isinstance(data, list) else []
    except:
        return []


def build_caption(pid, tags, source, score, rating, today, original):
    """构建 Telegram 消息 caption"""
    lines = [
        f"🖼 <b>ID</b>: <code>{pid}</code>",
        f"⭐ <b>Score</b>: {score}",
        f"🔒 <b>Rating</b>: {rating}",
        f"📅 <b>Date</b>: {today}",
    ]
    if tags:
        tag_display = tags[:200] + "..." if len(tags) > 200 else tags
        lines.append(f"🏷 <b>Tags</b>: {tag_display}")
    if source:
        lines.append(f"🔗 <a href=\"{source}\">Source</a>")
    lines.append(f"🌐 <a href=\"{original}\">Original</a>")
    return "\n".join(lines)


def process_post(p, db, today):
    """处理单条帖子：发送预览图和原图，返回 True 表示成功发送"""
    pid = str(p.get("id", ""))
    jpeg = p.get("jpeg_url") or p.get("sample_url") or p.get("preview_url")
    original = p.get("file_url")

    if not jpeg or not original:
        return False

    tags = p.get("tags", "").strip()
    source = p.get("source", "")
    score = p.get("score", 0)
    rating = p.get("rating", "?")

    caption = build_caption(pid, tags, source, score, rating, today, original)
    print(f"  📤 发送: {pid} (rating:{rating})")

    # 发送预览图
    tg_send_photo(jpeg, caption, download_fn=download_file)
    time.sleep(SEND_DELAY)

    # 检查原始文件大小
    file_size = get_file_size(original)
    print(f"  📦 原始文件大小: {file_size / 1024 / 1024:.1f} MB")

    if 0 < file_size <= MAX_FILE_SIZE:
        tg_send_file(original, caption, download_fn=download_file)
        time.sleep(SEND_DELAY)
    elif file_size > MAX_FILE_SIZE:
        print(f"  ⚠️  原始文件过大 ({file_size / 1024 / 1024:.1f} MB)，跳过")
    else:
        print(f"  ⚠️  无法获取文件大小，跳过原图")

    return True


def main():
    if not check_bot_token():
        print("⛔ 请检查 config.py 中的 BOT_TOKEN 是否正确！")
        sys.exit(1)

    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    start_date = (now - timedelta(days=DAYS_BACK)).strftime("%Y-%m-%d")

    print(f"📅 当前日期: {today}")
    print(f"📅 回溯到: {start_date} (最近 {DAYS_BACK} 天)")
    print(f"🏷️  标签: {TAGS}")

    db = load_db()
    print(f"💾 已有记录: {len(db)} 条")

    # 发送启动通知
    tg_send_message(
        f"🚀 <b>KonaDL 启动</b>\n"
        f"📅 <b>时间</b>: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )

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

            in_range_count = 0
            old_count = 0
            consecutive_old = 0
            consecutive_dup = 0
            should_stop = False

            for p in posts:
                pid = str(p.get("id", ""))
                created_at = p.get("created_at", 0)

                if not pid:
                    continue

                # 检查时间范围
                if not is_within_range(created_at):
                    created_str = datetime.fromtimestamp(created_at, tz=TZ).strftime("%Y-%m-%d %H:%M")
                    print(f"  ⏭️  超出范围: {pid} (创建于 {created_str})")
                    old_count += 1
                    consecutive_old += 1
                    if consecutive_old >= 5:
                        print(f"  🛑 连续 {consecutive_old} 个超出范围，停止翻页")
                        should_stop = True
                    continue

                in_range_count += 1
                consecutive_old = 0

                # 检查是否已发送
                if pid in db:
                    print(f"  ⏭️  跳过已发送: {pid}")
                    consecutive_dup += 1
                    if consecutive_dup >= 5:
                        print(f"  🛑 连续 {consecutive_dup} 个已发送，停止翻页")
                        should_stop = True
                    continue

                consecutive_dup = 0

                # 处理发送
                if process_post(p, db, today):
                    db.add(pid)
                    total_sent += 1

                if should_stop:
                    break

            if should_stop:
                save_db(db)
                print(f"\n🎉 完成！共发送 {total_sent} 条新内容")
                print(f"💾 数据库现有 {len(db)} 条记录")
                return

            print(f"  📊 本页统计: 范围内 {in_range_count} 条, 超出范围 {old_count} 条")

            if in_range_count == 0 and old_count > 0:
                print(f"📭 本页无范围内内容，停止翻页")
                site_succeeded = True
                break

            save_db(db)

        if not site_succeeded:
            site_succeeded = True

    save_db(db)
    print(f"\n🎉 完成！共发送 {total_sent} 条新内容")
    print(f"💾 数据库现有 {len(db)} 条记录")


if __name__ == "__main__":
    main()