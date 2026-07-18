#!/usr/bin/env python3
import asyncio
import os
import sys
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL", "").strip()
PASSWORD = os.getenv("APPWRITE_PASSWORD", "").strip()
PROJECT_URL = os.getenv("PROJECT_URL", "").strip()

async def main():
    print(f"📧 Email: {'✅' if EMAIL else '❌'}")
    print(f"🔑 Password: {'✅' if PASSWORD else '❌'}")
    print(f"🔗 URL: {PROJECT_URL[:60]}...")
    
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ متغیرها خالی هستند")
        sys.exit(1)

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
            await page.screenshot(path="before_login.png")

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
                print(f"⏳ منتظر... ({waited}s) URL: {current_url}")
            
            await page.screenshot(path="after_login.png")
            print(f"📍 URL نهایی: {current_url}")

            if "login" in current_url:
                print("❌ بعد از 30 ثانیه هنوز روی Login هستیم!")
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
                sys.exit(1)

            print("🔄 جستجوی دکمه Restore...")
            restore_btn = await page.query_selector('button:has-text("Restore project")')

            if restore_btn:
                print("✅ دکمه Restore یافت شد!")
                await restore_btn.click()
                await asyncio.sleep(5)
                await page.screenshot(path="after_restore.png")
                print("✅ پروژه بازیابی شد!")
            else:
                page_content = await page.content()
                if "Project paused" in page_content:
                    print("⚠️ پروژه Paused ولی دکمه یافت نشد")
                    await page.screenshot(path="paused_not_found.png", full_page=True)
                elif "Active" in page_content:
                    print("✅ پروژه قبلاً فعال است")
                else:
                    print("⚠️ وضعیت نامشخص")
                    await page.screenshot(path="unknown.png", full_page=True)

        except Exception as e:
            print(f"❌ خطا: {e}")
            await page.screenshot(path="error.png")
            sys.exit(1)
        finally:
            await browser.close()
            print("🔒 تمام")

if __name__ == "__main__":
    asyncio.run(main())
