#!/usr/bin/env python3
import asyncio
import os
import sys
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL")
PASSWORD = os.getenv("APPWRITE_PASSWORD")
PROJECT_URL = os.getenv("PROJECT_URL")

async def main():
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ متغیرهای محیطی تنظیم نشده‌اند")
        sys.exit(1)

    print(f"🚀 شروع بازیابی برای: {EMAIL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            print("🔐 در حال ورود...")
            await page.goto("https://cloud.appwrite.io/console/login", wait_until="networkidle")

            # پر کردن فرم
            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)
            
            print("⏳ در حال ارسال فرم...")
            await page.click('button[type="submit"]')

            # انتظار برای تغییر URL
            try:
                await page.wait_for_url("**/console/**", timeout=30000)
                print("✅ ورود موفقیت‌آمیز - URL تغییر کرد")
            except:
                # اگر URL تغییر نکرد، بررسی خطا
                current_url = page.url
                print(f"⚠️ URL فعلی: {current_url}")
                
                # بررسی وجود reCAPTCHA
                recaptcha = await page.query_selector('iframe[src*="recaptcha"]')
                if recaptcha:
                    print("🤖 reCAPTCHA شناسایی شد!")
                
                # بررسی پیام خطا
                error_msg = await page.query_selector('.alert, .error, [role="alert"]')
                if error_msg:
                    text = await error_msg.text_content()
                    print(f"❌ پیام خطا: {text}")
                
                await page.screenshot(path="login_error.png")
                raise Exception("ورود ناموفق بود")

            print("📂 در حال باز کردن پروژه...")
            await page.goto(PROJECT_URL, wait_until="networkidle")
            await asyncio.sleep(3)

            # اسکرین‌شات از صفحه پروژه
            await page.screenshot(path="project_page.png")
            print("📸 اسکرین‌شات صفحه پروژه ذخیره شد")

            print("🔄 در حال جستجوی دکمه Restore...")
            restore_btn = await page.query_selector('button:has-text("Restore project")')

            if restore_btn:
                print("✅ دکمه Restore project یافت شد - در حال کلیک...")
                await restore_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path="after_restore.png")
                print("✅ پروژه با موفقیت بازیابی شد!")
            else:
                active = await page.query_selector('text="Active"')
                running = await page.query_selector('text="Running"')
                if active or running:
                    print("✅ پروژه قبلاً فعال است - نیازی به Restore نیست")
                else:
                    print("⚠️ دکمه Restore یافت نشد - وضعیت نامشخص")
                    # لیست همه دکمه‌ها برای دیباگ
                    buttons = await page.query_selector_all('button')
                    for i, btn in enumerate(buttons[:10]):
                        text = await btn.text_content()
                        print(f"  دکمه {i}: {text.strip()}")

        except Exception as e:
            print(f"❌ خطا: {e}")
            await page.screenshot(path="error.png")
            sys.exit(1)

        finally:
            await browser.close()
            print("🔒 تمام")

if __name__ == "__main__":
    asyncio.run(main())
