#!/usr/bin/env python3
import asyncio
import os
import sys
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL", "").strip()
PASSWORD = os.getenv("APPWRITE_PASSWORD", "").strip()
PROJECT_URL = os.getenv("PROJECT_URL", "").strip()
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "unknown")

NOTIFY_EMAIL = "ali94khodaei@gmail.com"
SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_PASS = os.getenv("SMTP_PASS", "").strip()

def send_email_notification(subject, body):
    """ارسال ایمیل اطلاع‌رسانی"""
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ SMTP تنظیم نشده - ایمیل ارسال نمی‌شود")
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = NOTIFY_EMAIL
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ ایمیل ارسال شد به {NOTIFY_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ خطا در ارسال ایمیل: {e}")
        return False

async def main():
    print(f"📧 Email: {'✅' if EMAIL else '❌'}")
    print(f"🔑 Password: {'✅' if PASSWORD else '❌'}")
    print(f"🔗 URL: {PROJECT_URL[:60]}...")
    
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ متغیرها خالی هستند")
        sys.exit(1)

    project_name = "Unknown"
    status = "failed"
    error_msg = ""
    is_paused = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            print("🔐 باز کردن صفحه لاگین...")
            await page.goto("https://cloud.appwrite.io/console/login", wait_until="networkidle")
            await asyncio.sleep(2)

            print("📝 پر کردن فرم...")
            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)

            print("🖱️ کلیک روی Sign in...")
            await page.click('button[type="submit"]')
            
            print("⏳ انتظار برای پاسخ سرور...")
            await asyncio.sleep(5)
            
            max_wait = 30
            waited = 5
            current_url = page.url
            
            while "login" in current_url and waited < max_wait:
                await asyncio.sleep(2)
                waited += 2
                current_url = page.url
                print(f"⏳ منتظر... ({waited}s)")
            
            print(f"📍 URL نهایی: {current_url}")

            if "login" in current_url:
                print("❌ بعد از 30 ثانیه هنوز روی Login هستیم!")
                error_msg = "ورود به Appwrite ناموفق بود"
                sys.exit(1)

            print("✅ ورود موفقیت‌آمیز!")

            print(f"📂 باز کردن پروژه...")
            await page.goto(PROJECT_URL, wait_until="networkidle")
            await asyncio.sleep(3)
            
            current_url = page.url
            print(f"📍 URL پروژه: {current_url}")
            await page.screenshot(path="project_page.png")

            if "login" in current_url:
                print("❌ به Login redirect شدیم!")
                error_msg = "Session منقضی شد"
                sys.exit(1)

            # استخراج نام پروژه
            title_el = await page.query_selector('h1')
            if title_el:
                project_name = await title_el.text_content()
                project_name = project_name.strip()
            else:
                match = re.search(r'project-([a-zA-Z0-9]+)', PROJECT_URL)
                if match:
                    project_name = f"Project-{match.group(1)[:8]}"

            print(f"📋 نام پروژه: {project_name}")

            # بررسی محتوای صفحه برای تشخیص وضعیت
            page_content = await page.content()
            page_text = await page.inner_text('body')

            # بررسی آیا پروژه Paused است
            if "Project paused" in page_content or "paused due to inactivity" in page_content:
                is_paused = True
                print("⏸️ پروژه در حالت Paused است")

                print("🔄 جستجوی دکمه Restore...")
                restore_btn = await page.query_selector('button:has-text("Restore project")')

                if restore_btn:
                    print("✅ دکمه Restore یافت شد!")
                    await restore_btn.click()
                    await asyncio.sleep(5)
                    
                    # بررسی موفقیت
                    new_content = await page.content()
                    if "Project paused" not in new_content:
                        status = "restored"
                        print("✅ پروژه با موفقیت بازیابی شد!")
                    else:
                        status = "failed"
                        error_msg = "بازیابی ناموفق بود"
                        print("❌ بازیابی ناموفق")
                else:
                    status = "failed"
                    error_msg = "دکمه Restore یافت نشد"
                    print("⚠️ دکمه Restore یافت نشد")
            else:
                # پروژه Paused نیست
                is_paused = False
                if "Active" in page_text or "Running" in page_text:
                    status = "already_active"
                    print("✅ پروژه قبلاً فعال است - نیازی به Restore نیست")
                else:
                    status = "already_active"
                    print("ℹ️ پروژه متوقف نیست - وضعیت: فعال")

        except Exception as e:
            error_msg = str(e)
            print(f"❌ خطا: {e}")
        finally:
            await browser.close()
            print("🔒 تمام")

    # ارسال ایمیل
    if status == "restored":
        subject = f"✅ Appwrite: پروژه '{project_name}' بازیابی شد"
        body = f"""سلام،

پروژه '{project_name}' با موفقیت از حالت تعلیق خارج شد.

🔹 اکانت: {EMAIL}
🔹 وضعیت: ✅ بازیابی موفق

با احترام،
Appwrite Auto Restorer
"""
    elif status == "already_active":
        subject = f"ℹ️ Appwrite: پروژه '{project_name}' فعال است"
        body = f"""سلام،

پروژه '{project_name}' نیازی به بازیابی نداشت.

🔹 اکانت: {EMAIL}
🔹 وضعیت: ℹ️ قبلاً فعال/در حال اجرا

با احترام،
Appwrite Auto Restorer
"""
    else:
        subject = f"❌ Appwrite: خطا در '{project_name}'"
        body = f"""سلام،

بازیابی پروژه '{project_name}' با خطا مواجه شد.

🔹 اکانت: {EMAIL}
🔹 خطا: {error_msg}

لطفاً دستی بررسی کنید.

با احترام،
Appwrite Auto Restorer
"""

        # ارسال ایمیل فقط وقتی که پروژه واقعاً بازیابی شد
    if status == "restored":
        send_email_notification(subject, body)
        print("📧 ایمیل ارسال شد - پروژه از حالت Paused خارج شد")
    elif status == "already_active":
        print("ℹ️ پروژه قبلاً فعال بود - نیازی به ایمیل نیست")
    else:
        print("❌ خطا در بازیابی - ایمیل خطا ارسال نمی‌شود")

    # Exit codes
    if status in ["restored", "already_active"]:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
