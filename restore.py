#!/usr/bin/env python3
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright

EMAIL = os.getenv("APPWRITE_EMAIL", "").strip()
PASSWORD = os.getenv("APPWRITE_PASSWORD", "").strip()
PROJECT_URL = os.getenv("PROJECT_URL", "").strip()

COOKIES_FILE = "appwrite_cookies.json"

async def save_cookies(context):
    """ذخیره کوکی‌ها"""
    cookies = await context.cookies()
    with open(COOKIES_FILE, "w") as f:
        json.dump(cookies, f)
    print("🍪 کوکی‌ها ذخیره شدند")

async def load_cookies(context):
    """بارگذاری کوکی‌ها"""
    try:
        with open(COOKIES_FILE, "r") as f:
            cookies = json.load(f)
        await context.add_cookies(cookies)
        print("🍪 کوکی‌ها بارگذاری شدند")
        return True
    except FileNotFoundError:
        return False

async def main():
    print(f"📧 Email: {'✅' if EMAIL else '❌'}")
    print(f"🔑 Password: {'✅' if PASSWORD else '❌'}")
    print(f"🔗 URL: {PROJECT_URL[:60]}...")
    
    if not all([EMAIL, PASSWORD, PROJECT_URL]):
        print("❌ متغیرها خالی هستند")
        sys.exit(1)

    async with async_playwright() as p:
        # Launch با args ضد-detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )
        
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Europe/Berlin",
        )

        # حذف webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # تلاش برای بارگذاری کوکی
        cookies_loaded = await load_cookies(context)

        if cookies_loaded:
            print("🔍 بررسی اعتبار کوکی‌ها...")
            await page.goto("https://cloud.appwrite.io/console", wait_until="networkidle")
            if "login" not in page.url:
                print("✅ کوکی‌ها معتبر هستند")
                logged_in = True
            else:
                print("🔄 کوکی‌ها منقضی شدند")
                logged_in = False
        else:
            logged_in = False

        if not logged_in:
            print("🔐 در حال ورود با ایمیل و پسورد...")
            await page.goto("https://cloud.appwrite.io/console/login", wait_until="networkidle")
            await asyncio.sleep(2)

            # پر کردن فرم
            await page.fill('input[type="email"]', EMAIL)
            await page.fill('input[type="password"]', PASSWORD)
            
            # اسکرین‌شات قبل از کلیک
            await page.screenshot(path="before_login.png")
            
            print("⏳ ارسال فرم...")
            await page.click('button[type="submit"]')
            
            # انتظار برای navigation
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
                await asyncio.sleep(3)
            except:
                pass

            # بررسی URL
            current_url = page.url
            print(f"📍 URL بعد از Login: {current_url}")
            await page.screenshot(path="after_login.png")

            if "login" in current_url:
                print("❌ هنوز روی صفحه Login هستیم!")
                
                # بررسی reCAPTCHA
                recaptcha = await page.query_selector('iframe[src*="recaptcha"], .g-recaptcha')
                if recaptcha:
                    print("🤖 reCAPTCHA شناسایی شد!")
                
                # بررسی پیام خطا
                error_selectors = [
                    '.alert', '.error', '[role="alert"]',
                    'text="Invalid credentials"',
                    'text="Wrong email or password"',
                ]
                for sel in error_selectors:
                    el = await page.query_selector(sel)
                    if el:
                        text = await el.text_content()
                        print(f"❌ پیام خطا: {text.strip()}")
                
                sys.exit(1)

            print("✅ ورود موفقیت‌آمیز!")
            await save_cookies(context)

        # رفتن به صفحه پروژه
        print(f"📂 باز کردن پروژه...")
        await page.goto(PROJECT_URL, wait_until="networkidle")
        await asyncio.sleep(3)
        
        current_url = page.url
        print(f"📍 URL فعلی: {current_url}")
        await page.screenshot(path="project_page.png")

        # بررسی آیا redirect به login شده
        if "login" in current_url:
            print("❌ به صفحه Login redirect شدیم!")
            sys.exit(1)

        # جستجوی دکمه Restore
        print("🔄 جستجوی دکمه Restore...")
        
        # چند selector مختلف را امتحان می‌کنیم
        restore_selectors = [
            'button:has-text("Restore project")',
            'button:has-text("Restore")',
            'text="Restore project"',
            '[data-testid="restore-project"]',
            'button >> nth=1',  # دکمه دوم در دیالوگ
        ]
        
        restore_btn = None
        for sel in restore_selectors:
            restore_btn = await page.query_selector(sel)
            if restore_btn:
                print(f"✅ دکمه با selector یافت شد: {sel}")
                break

        if restore_btn:
            # بررسی visible بودن
            is_visible = await restore_btn.is_visible()
            print(f"👁️ دکمه visible: {is_visible}")
            
            if is_visible:
                await restore_btn.click()
                print("🖱️ کلیک روی Restore project")
                await asyncio.sleep(5)
                await page.screenshot(path="after_restore.png")
                print("✅ پروژه بازیابی شد!")
            else:
                print("⚠️ دکمه یافت شد ولی visible نیست")
        else:
            # بررسی وضعیت پروژه
            page_content = await page.content()
            
            if "Project paused" in page_content:
                print("⚠️ پروژه Paused است ولی دکمه Restore یافت نشد")
                # اسکرین‌شات کامل
                await page.screenshot(path="paused_not_found.png", full_page=True)
            elif "Active" in page_content or "Running" in page_content:
                print("✅ پروژه قبلاً فعال است")
            else:
                print("⚠️ وضعیت نامشخص")
                await page.screenshot(path="unknown_state.png", full_page=True)

        await browser.close()
        print("🔒 تمام")

if __name__ == "__main__":
    asyncio.run(main())
