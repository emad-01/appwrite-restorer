#!/usr/bin/env python3
"""
Appwrite Auto Restorer - ساده و قابل اعتماد
"""

import asyncio
import os
import sys
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL")
PASSWORD = os.getenv("APPWRITE_PASSWORD")
PROJECT_URL = os.getenv("PROJECT_URL")

async def main():
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ لطفاً متغیرهای محیطی را تنظیم کنید")
        sys.exit(1)

    print(f"🚀 شروع بازیابی برای: {EMAIL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )

        # حذف علائم automation
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            # ۱. ورود به Appwrite
            print("🔐 در حال ورود...")
            await page.goto("https://cloud.appwrite.io/console/login", wait_until="networkidle")

            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)
            await page.click('button[type="submit"]')

            # انتظار برای ورود موفق
            await page.wait_for_url("**/console/**", timeout=30000)
            print("✅ ورود موفقیت‌آمیز")

            # ۲. رفتن به صفحه پروژه
            print("📂 در حال باز کردن پروژه...")
            await page.goto(PROJECT_URL, wait_until="networkidle")
            await asyncio.sleep(3)

            # ۳. کلیک روی Restore project
            print("🔄 در حال جستجوی دکمه Restore...")
            restore_btn = await page.query_selector('button:has-text("Restore project")')

            if restore_btn:
                await restore_btn.click()
                await asyncio.sleep(5)
                print("✅ پروژه با موفقیت بازیابی شد!")
            else:
                # بررسی آیا قبلاً فعال است
                active = await page.query_selector('text="Active"')
                if active:
                    print("✅ پروژه قبلاً فعال است")
                else:
                    print("⚠️ دکمه Restore یافت نشد - اسکرین‌شات ذخیره شد")
                    await page.screenshot(path="screenshot.png")

        except Exception as e:
            print(f"❌ خطا: {e}")
            await page.screenshot(path="error.png")
            sys.exit(1)

        finally:
            await browser.close()
            print("🔒 تمام")

if __name__ == "__main__":
    asyncio.run(main())
