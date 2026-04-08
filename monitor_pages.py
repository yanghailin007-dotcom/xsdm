#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
页面健康监控脚本 - 长期运行
定期检查所有关键页面入口是否正常
"""

import asyncio
import sys
import time
from datetime import datetime
from pathlib import Path

# 配置
BASE_URL = "http://localhost:5000"
CHECK_INTERVAL = 300  # 每5分钟检查一次
LOG_FILE = Path("logs/page_monitor.log")

# 页面列表
PAGES = [
    ("home", "/"),
    ("login", "/login"),
    ("market-driven-create", "/market-driven-create"),
    ("short-drama", "/short-drama"),
    ("creative-workshop", "/creative-workshop"),
    ("video-generation", "/video-generation"),
]

async def check_page(page, name: str, url: str) -> bool:
    """检查单个页面"""
    try:
        response = await page.goto(url, wait_until="domcontentloaded", timeout=10000)
        if response and response.status >= 400:
            return False
        await page.wait_for_selector("body", timeout=5000)
        return True
    except:
        return False

async def run_check():
    """运行一次检查"""
    from playwright.async_api import async_playwright
    
    results = []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        
        for name, path in PAGES:
            page = await context.new_page()
            try:
                success = await check_page(page, name, f"{BASE_URL}{path}")
                results.append((name, success))
            finally:
                await page.close()
        
        await browser.close()
    
    return results

async def main():
    """主循环 - 持续监控"""
    # 确保日志目录存在
    LOG_FILE.parent.mkdir(exist_ok=True)
    
    print(f"[{datetime.now()}] Page monitor started")
    print(f"Monitoring {len(PAGES)} pages every {CHECK_INTERVAL} seconds")
    print(f"Log file: {LOG_FILE}")
    
    fail_count = {name: 0 for name, _ in PAGES}
    
    while True:
        try:
            results = await run_check()
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_lines = [f"[{timestamp}] Page Check Results:"]
            
            all_passed = True
            for name, success in results:
                status = "OK" if success else "FAIL"
                log_lines.append(f"  [{status}] {name}")
                
                if not success:
                    all_passed = False
                    fail_count[name] += 1
                else:
                    fail_count[name] = 0
            
            # 记录到文件
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write("\n".join(log_lines) + "\n")
            
            # 打印到控制台
            print("\n" + "=" * 60)
            print(f"[{timestamp}] Check complete: {'ALL PASS' if all_passed else 'SOME FAIL'}")
            for name, success in results:
                icon = "OK" if success else f"FAIL({fail_count[name]})"
                print(f"  [{icon}] {name}")
            
            # 如果有页面连续失败3次，发送警告
            for name, count in fail_count.items():
                if count >= 3:
                    print(f"  [ALERT] {name} failed {count} times in a row!")
            
        except Exception as e:
            print(f"[{datetime.now()}] Error during check: {e}")
        
        # 等待下一次检查
        await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{datetime.now()}] Monitor stopped by user")
        sys.exit(0)
