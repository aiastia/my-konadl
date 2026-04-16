"""Telegram Bot API 相关函数"""
import requests
import time
import os
from config import BOT_TOKEN, CHAT_ID, MAX_FILE_SIZE

# TG API 基础 URL
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# 速率限制：每次发送间隔（秒）
SEND_DELAY = 3
# Telegram photo 接口最大 10MB
TG_PHOTO_MAX_SIZE = 10 * 1024 * 1024


def tg_request(method, data=None, files=None, max_retries=3):
    """带速率限制和 429 重试的 Telegram API 请求"""
    url = f"{TG_API}/{method}"
    for attempt in range(max_retries):
        try:
            r = requests.post(url, data=data, files=files, timeout=120)
            if r.status_code == 200:
                return r
            resp = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            # 429: Too Many Requests → 等待后重试
            if r.status_code == 429:
                retry_after = resp.get("parameters", {}).get("retry_after", 5)
                print(f"  ⏳ 速率限制，等待 {retry_after} 秒后重试...")
                time.sleep(retry_after + 1)
                continue
            # 非重试错误，直接返回
            return r
        except Exception as e:
            print(f"  ❌ 请求异常: {e}")
            if attempt < max_retries - 1:
                time.sleep(3)
    return r


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


def tg_send_message(text):
    """发送纯文本消息到 Telegram"""
    try:
        r = tg_request("sendMessage", data={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        })
        if r.status_code == 200:
            print(f"✅ 消息发送成功")
            return True
        else:
            print(f"❌ 消息发送失败: {r.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ 消息发送异常: {e}")
        return False


def tg_send_photo(image_url, caption="", download_fn=None):
    """下载预览图并发送到 Telegram（超过10MB则转为文件发送）

    Args:
        image_url: 图片 URL
        caption: 图片说明
        download_fn: 下载函数，从 utils 传入以避免循环依赖
    """
    print(f"  ⬇️  下载预览图...")
    file_path = download_fn(image_url) if download_fn else None
    if not file_path:
        print(f"  ❌ 预览图下载失败")
        return False

    actual_size = os.path.getsize(file_path)
    try:
        if actual_size > TG_PHOTO_MAX_SIZE:
            print(f"  ⚠️  预览图过大 ({actual_size / 1024 / 1024:.1f} MB)，转为文件发送")
            with open(file_path, "rb") as f:
                r = tg_request("sendDocument", data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                }, files={"document": f})
            if r.status_code == 200:
                print(f"  ✅ 预览图（文件方式）发送成功")
                return True
            else:
                print(f"  ❌ 预览图（文件方式）发送失败: {r.text[:200]}")
                return False
        else:
            with open(file_path, "rb") as f:
                r = tg_request("sendPhoto", data={
                    "chat_id": CHAT_ID,
                    "caption": caption,
                    "parse_mode": "HTML"
                }, files={"photo": f})
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


def tg_send_file(image_url, caption="", download_fn=None):
    """下载原图并发送到 Telegram"""
    print(f"  ⬇️  下载原图...")
    file_path = download_fn(image_url) if download_fn else None
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
            r = tg_request("sendDocument", data={
                "chat_id": CHAT_ID,
                "caption": caption,
                "parse_mode": "HTML"
            }, files={"document": f})
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