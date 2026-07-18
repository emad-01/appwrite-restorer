#!/usr/bin/env python3
import asyncio
import os
import sys
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL", "").strip()
PASSWORD = os.getenv("APPWRITE_PASSWORD", "").strip()
PROJECT_URL = os.getenv("PROJECT_URL", "").strip()

async def main():
    # بررسی متغیرها
    print(f"📧 Email: {'✅ تنظیم شده' if EMAIL else '❌ خالی'}")
    print(f"🔑 Password: {'✅ تنظیم شده' if PASSWORD else '❌ خالی'}")
    print(f"🔗 Project URL: {PROJECT_URL[:50]}..." if len(PROJECT_URL) > 50 else f"🔗 Project URL: {PROJECT_URL}")
    
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ یک یا چند متغیر محیطی خالی است!")
        sys.exit(1)
    
    if not PROJECT_URL.startswith("http"):
        print(f"❌ URL نامعتبر: {PROJECT_URL}")
        sys.exit(1)

    print(f"\n🚀 شروع بازیابی برای: {EMAIL}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            print("🔐 در حال ورود...")
            await page.goto("https://cloud.appwrite.io/console/login", wait_until="networkidle")

            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)
            
            print("⏳ در حال ارسال فرم...")
            await page.click('button[type="submit"]')

            # انتظار برای تغییر URL
            try:
                await page.wait_for_url("**/console/**", timeout=30000)
                print("✅ ورود موفقیت‌آمیز")
            except:
                current_url = page.url
                print(f"⚠️ URL فعلی: {current_url}")
                await page.screenshot(path="login_error.png")
                raise Exception("ورود ناموفق")

            print(f"📂 در حال باز کردن: {PROJECT_URL}")
            await page.goto(PROJECT_URL, wait_until="networkidle")
            await asyncio.sleep(3)
            await page.screenshot(path="project_page.png")

            print("🔄 جستجوی دکمه Restore...")
            restore_btn = await page.query_selector('button:has-text("Restore project")')

            if restore_btn:
                print("✅ دکمه Restore یافت شد!")
                await restore_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path="after_restore.png")
                print("✅ پروژه بازیابی شد!")
            else:
                active = await page.query_selector('text="Active"')
                if active:
                    print("✅ پروژه قبلاً فعال است")
                else:
                    print("⚠️ دکمه Restore یافت نشد")
                    buttons = await page.query_selector_all('button')
                    for btn in buttons[:5]:
                        text = await btn.text_content()
                        print(f"  - {text.strip()}")

        except Exception as e:
            print(f"❌ خطا: {e}")
            await page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            await browser.close()
            print("🔒 تمام")

if __name__ == "__main__":
    asyncio.run(main())
