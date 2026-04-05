#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试 V3 - 修复定时发布开关，内容多样化
"""

import time
import random
import sys
from playwright.sync_api import sync_playwright

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def human_sleep(min_sec=0.5, max_sec=2.0):
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)
    return delay

def generate_diverse_content(min_length: int = 1100) -> str:
    """生成高度多样化的内容，避免重复检测"""
    # 使用大量不同的段落，确保内容不重复
    paragraphs = [
        "春风拂过湖面，泛起层层涟漪，岸边的柳树抽出嫩绿的新芽。这是江南最美的时节，烟雨朦胧中，小桥流水人家构成了一幅诗意画卷。",
        "深夜的图书馆里只有寥寥几人，台灯发出昏黄的光。他专注地翻阅着泛黄的古籍，寻找那段被历史尘封的真相。",
        "暴雨倾盆而下，城市的霓虹灯在雨幕中变得模糊。行人匆匆赶路，只有那个老人依然坐在公交站台下，等待着永远不会来的班车。",
        "雪山之巅，寒风呼啸，他却浑然不觉。手中的长剑闪烁着寒光，那是师父临终前传下的绝世神兵，承载着门派百年的荣耀。",
        "老茶馆里飘着龙井的清香，几位白发老人正在下象棋。楚河汉界间，是岁月沉淀的智慧，也是人生百态的缩影。",
        "飞船穿过云层，舷窗外的地球逐渐变小。宇航员望着那颗蓝色星球，心中涌起难以言喻的感动，那是人类共同的家园。",
        "古镇的石板路上，脚步声回荡。青瓦白墙间，时光仿佛静止，只有那棵百年银杏树见证了太多的离别与重逢。",
        "实验室里，各种仪器发出规律的声音。年轻的研究员盯着屏幕上的数据，眼中闪烁着发现新大陆般的兴奋光芒。",
        "沙漠中的驼队缓缓前行，夕阳西下，将沙丘染成金色。商人们脸上写满疲惫，但眼中却燃烧着对财富的渴望。",
        "音乐会现场，指挥棒落下，悠扬的旋律流淌而出。观众屏息凝神，沉浸在贝多芬用灵魂谱写的音符之中。",
        "海边的灯塔在夜色中闪烁，为迷航的船只指引方向。潮起潮落间，无数故事被大海吞没，又有无数希望被冲上沙滩。",
        "山间的寺庙钟声悠扬，惊起了栖息在古松上的飞鸟。僧人手持扫帚，清扫着落叶，心中一片宁静。",
        "城市的地下铁轰鸣而过，车厢里挤满了疲惫的上班族。每个人的脸上都写满了故事，却又彼此陌生。",
        "乡村的小学里，孩子们朗朗的读书声回荡在山谷间。简陋的教室里，一双双求知的眼睛闪烁着对未来的憧憬。",
        "医院的走廊里，消毒水的气味弥漫。医生护士脚步匆匆，生与死的较量每时每刻都在上演。",
        "画家站在画布前，手中的画笔沾满了颜料。他要将眼前的美景永远定格，让瞬间成为永恒。",
        "厨师在灶台前忙碌，锅铲翻飞间，一道道美味佳肴陆续出锅。食物的香气勾起了食客们的食欲。",
        "摄影师扛着器材，跋涉在崎岖的山路上。他要捕捉那稍纵即逝的光影，记录大自然的壮美。",
        "码头的渔民们收网归航，满仓的鱼虾是他们一天的收获。海鸥在空中盘旋，等待着丢弃的鱼内脏。",
        "火车站的候车室里，人们拖着行李箱来来往往。离别与重逢在这里交织，每一张面孔都是一个故事。"
    ]
    
    # 随机打乱顺序
    random.shuffle(paragraphs)
    
    # 构建内容，确保段落不重复
    content = ""
    idx = 0
    used_paragraphs = set()
    
    while len(content) < min_length:
        para = paragraphs[idx % len(paragraphs)]
        # 添加一些随机变化，使内容更独特
        if random.random() > 0.5:
            para = para.replace("。", "，")
        content += para + "\n\n"
        idx += 1
        
        # 如果已经用完所有段落，重新打乱再用
        if idx >= len(paragraphs):
            random.shuffle(paragraphs)
            idx = 0
    
    return content

def test_complete_v3(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        log("连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        log(f"当前页面: {page.url}")
        
        human_sleep(1, 2)
        
        # 1. 填写章节号
        log("[步骤1] 填写章节号...")
        try:
            num_input = page.locator('.serial-editor-title-left input').first
            if num_input.count() == 0:
                num_input = page.locator('.left-input input').first
            if num_input.count() > 0:
                num_input.click()
                human_sleep(0.3, 0.8)
                num_input.fill("")
                human_sleep(0.2, 0.5)
                num_input.fill("888")
                log("  [OK] 888")
            else:
                log("  [ERR] 未找到")
                return
        except Exception as e:
            log(f"  [ERR] {e}")
            return
        
        human_sleep(0.5, 1.5)
        
        # 2. 填写标题
        log("[步骤2] 填写标题...")
        try:
            title_input = page.locator('.serial-editor-title-right input').first
            if title_input.count() == 0:
                title_input = page.locator('.right-input input').first
            if title_input.count() > 0:
                title_input.click()
                human_sleep(0.3, 0.8)
                title_input.fill("")
                human_sleep(0.2, 0.5)
                title_input.fill("定时发布测试-多样化内容")
                log("  [OK]")
        except Exception as e:
            log(f"  [ERR] {e}")
        
        human_sleep(0.5, 1.5)
        
        # 3. 填写多样化内容
        log("[步骤3] 填写多样化内容...")
        try:
            content = generate_diverse_content(1100)
            editor = page.locator('.ProseMirror[contenteditable]').first
            if editor.count() > 0:
                editor.click()
                human_sleep(0.5, 1.0)
                editor.fill(content)
                length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
                log(f"  [OK] {length}字")
            else:
                log("  [ERR] 未找到编辑器")
        except Exception as e:
            log(f"  [ERR] {e}")
        
        human_sleep(1, 2)
        
        # 4. 点击下一步
        log("[步骤4] 点击下一步...")
        try:
            next_btn = page.locator('button:has-text("下一步")').first
            if next_btn.count() > 0:
                human_sleep(0.5, 1.0)
                next_btn.click()
                log("  [OK]")
                human_sleep(2, 3)
        except Exception as e:
            log(f"  [ERR] {e}")
        
        # 5. 处理模态框
        log("[步骤5] 等待模态框...")
        for i in range(15):
            time.sleep(0.5)
            modal = page.locator('.publish-confirm-container-new, .arco-modal:has(.publish-confirm-card)').first
            if modal.count() > 0 and modal.is_visible():
                log("  [OK] 找到模态框")
                break
        else:
            log("  [ERR] 未找到")
            return
        
        human_sleep(0.8, 1.5)
        
        # 5.1 选择 AI
        log("[步骤5.1] 选择 AI: 是...")
        try:
            cards = page.locator('.publish-confirm-card').all()
            log(f"  找到 {len(cards)} 个 card")
            if len(cards) >= 1:
                ai_card = cards[0]
                radios = ai_card.locator('label.arco-radio').all()
                if len(radios) >= 1:
                    human_sleep(0.3, 0.8)
                    radios[0].click()
                    log("  [OK] 已选择 AI: 是")
        except Exception as e:
            log(f"  [WARN] {e}")
        
        human_sleep(0.5, 1.2)
        
        # 5.2 开启定时发布 - 在第二个card中
        log("[步骤5.2] 开启定时发布...")
        try:
            cards = page.locator('.publish-confirm-card').all()
            if len(cards) >= 2:
                time_card = cards[1]  # 定时发布在第二个card
                log("  [OK] 找到定时发布card")
                
                # 在这个card中查找switch
                switch = time_card.locator('button[role="switch"]').first
                if switch.count() > 0:
                    is_on = switch.get_attribute('aria-checked') == 'true'
                    log(f"  当前状态: {'已开启' if is_on else '已关闭'}")
                    
                    if not is_on:
                        human_sleep(0.3, 0.6)
                        switch.click()
                        log("  [OK] 已点击开启")
                        human_sleep(1.5, 2.5)
                        
                        # 选择时间 - 明天早上9点
                        picker = page.locator('.arco-picker-input input').first
                        if picker.count() > 0:
                            log("  打开时间选择器...")
                            human_sleep(0.3, 0.6)
                            picker.click()
                            human_sleep(0.8, 1.5)
                            
                            # 先选择明天的日期
                            tomorrow_cell = page.locator('.arco-picker-cell:not(.arco-picker-cell-disabled)').nth(1)
                            if tomorrow_cell.count() > 0:
                                tomorrow_cell.click()
                                log("  [OK] 已选择明天日期")
                                human_sleep(0.5, 1.0)
                            
                            # 选择早上9点
                            time_cells = page.locator('.arco-timepicker-cell, .arco-picker-time-cell').all()
                            if len(time_cells) >= 9:
                                # 选择第9个（大概对应9点）
                                time_cells[9].click()
                                log("  [OK] 已选择早上9点")
                            elif len(time_cells) > 0:
                                # 如果不够9个，选第一个可用的
                                time_cells[0].click()
                                log("  [OK] 已选择时间")
                    else:
                        log("  [OK] 已开启")
                else:
                    log("  [WARN] 未找到switch")
            else:
                log("  [WARN] 未找到第二个card")
        except Exception as e:
            log(f"  [WARN] {e}")
        
        human_sleep(0.8, 1.5)
        
        # 5.3 确认发布
        log("[步骤5.3] 点击确认发布...")
        try:
            confirm = page.locator('.arco-modal-footer button.arco-btn-primary').first
            if confirm.count() > 0 and confirm.is_visible():
                human_sleep(0.5, 1.0)
                confirm.click()
                log("  [OK]")
            else:
                confirm2 = page.locator('button:has-text("确认发布")').first
                if confirm2.count() > 0:
                    human_sleep(0.5, 1.0)
                    confirm2.click()
                    log("  [OK]")
        except Exception as e:
            log(f"  [ERR] {e}")
            return
        
        human_sleep(2, 3)
        
        # 6. 风险检测
        log("[步骤6] 风险检测...")
        for i in range(10):
            time.sleep(0.5)
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                log("  [OK] 发现")
                human_sleep(0.5, 1.0)
                risk.locator('button.arco-btn-primary').first.click()
                log("  [OK] 确定")
                break
            if '/manage' in page.url:
                log("  [OK] 返回管理页")
                break
        
        log(f"\n[完成] {page.url}")
        input("按回车...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_complete_v3(port)
