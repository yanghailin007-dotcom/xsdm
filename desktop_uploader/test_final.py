#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整测试：真实小说内容(>1000字) + 定时发布
"""

import time
import sys
from playwright.sync_api import sync_playwright

def get_real_content() -> str:
    """使用真实小说内容 - 确保超过1000字"""
    content = """第一章 血色崛起

陆玄缓缓睁开眼睛，入目是一片陌生的景象。简陋的茅草屋，破旧的木床，空气中弥漫着一股淡淡的药草味。

"这是哪里？我明明正在熬夜看《凡人修仙传》，怎么突然..."

脑海中一阵剧痛，无数记忆碎片如潮水般涌来。片刻后，陆玄终于理清了现状——他穿越了，穿越到了《凡人修仙传》的世界，成为了越国边境小宗门"黄枫谷"的一名外门弟子。

原主也叫陆玄，天赋平庸，四灵根资质，入门三年才勉强达到炼气三层。在这个弱肉强食的修仙界，这样的资质注定只能成为炮灰。

"叮！杀戮进化系统激活中..."

一道冰冷的机械声在脑海中响起，陆玄瞳孔骤缩。

"系统？"

"系统激活完成！宿主：陆玄。功能：击杀拥有灵气的生灵，可掠夺对方修为、灵根、功法、寿元等一切！"

陆玄倒吸一口凉气。这个系统，简直是逆天！不需要苦修，只需要杀戮就能变强！

就在这时，门外传来一阵脚步声。

"陆师弟，该去执事殿领取这个月的丹药了。"

来人是同门的赵师兄，炼气五层的修为，平日里没少欺负原主。但此刻，陆玄看向他的目光却变得不一样。

因为在他的视野中，赵师兄头顶浮现出一行血色文字：

【目标：赵无极】
【修为：炼气五层】
【可掠夺：修为进度、土灵根资质、低级功法《厚土诀》】

"赵师兄，请进。"陆玄嘴角勾起一抹不易察觉的冷笑。

赵无极推门而入，正准备像往常一样嘲讽几句，却见陆玄已经站在门后，手中握着一柄匕首。

"你——"

"噗嗤！"

匕首直插心脏！赵无极瞪大双眼，难以置信地看着胸口的血洞。

"为...为什么..."

"因为，你太弱了。"

【叮！击杀炼气五层修士，获得修为+200，土灵根+3，《厚土诀》感悟！】

一股热流涌入体内，陆玄的修为瞬间突破，从炼气三层直接飙升至炼气五层！

感受着体内澎湃的灵力，陆玄眼中闪过一丝嗜血的光芒。

"杀戮，从现在开始！"

三日后，血色禁地开启。

这是越国七大派共同掌控的试炼之地，里面妖兽横行，但也天材地宝无数。对于普通弟子来说，这是九死一生的险地，但对于拥有杀戮系统的陆玄来说，这是最佳的猎场！

禁地深处，一头二阶妖兽"铁背苍狼"正在啃食一具尸体。突然，它浑身毛发炸起，感受到了致命的危险。

"吼！"

一道血色剑光闪过，苍狼的头颅高高飞起！

【叮！击杀二阶妖兽，获得修为+500，妖兽精血+10！】

陆玄的身影从阴影中走出，身后是堆积如山的妖兽尸体。进入禁地短短半日，他已经击杀了三十余头妖兽，修为暴涨至炼气八层！

"还不够...我需要更多的杀戮！"

就在这时，前方传来一阵打斗声。陆玄隐匿身形，悄然靠近。

只见三名掩月宗弟子正在围攻一名黄枫谷的女修，那女修已经身受重伤，岌岌可危。

"嘿嘿，黄枫谷的小娘子，乖乖交出储物袋，或许还能留你全尸！"

"你们...卑鄙！"

陆玄冷眼旁观，并没有出手的打算。但就在此时，其中一名掩月宗弟子似乎察觉到了什么，猛地转头。

"谁在那里！"

三人的目光同时锁定陆玄。

"黄枫谷的废物？正好，一起解决了！"

三人放弃女修，朝陆玄包围而来。他们都是炼气七层的修为，联手之下，寻常炼气八层根本不是对手。

但陆玄，可不是寻常修士！

"既然你们找死，那就成全你们。"

"狂妄！"

三人同时出手，法器呼啸而至。但陆玄的身影却如鬼魅般消失，下一瞬已经出现在一人身后。

"噗！"

【叮！击杀炼气七层修士...】

"什么！"

另外两人大惊失色，但已经晚了。陆玄如死神般收割着生命，眨眼间，三具尸体倒地。

【叮！累计击杀三名炼气七层修士，获得修为+1200，水灵根+5，金灵根+3...】

"轰！"

体内瓶颈破碎，陆玄正式踏入炼气九层！

远处，那名黄枫谷女修已经看呆了。这个同门师弟，怎么会如此恐怖？

陆玄转身，目光落在她身上。

女修心中一颤，颤声道："多...多谢师弟相救..."

"把你的储物袋交出来。"

"什...什么？"

"我说，储物袋。"陆玄眼中毫无感情，"或者，死。"

一刻钟后，陆玄提着满满的储物袋，消失在禁地深处。身后，女修瘫坐在地，劫后余生。

七日后，血色禁地关闭。

七大派弟子伤亡惨重，但其中最震撼的消息是——黄枫谷一名外门弟子，在禁地中击杀了掩月宗、清虚门等派数十名精英弟子，被七大派联合通缉！

而那名弟子的名字，叫做陆玄。

"血剑魔尊"之名，从此在越国修仙界传开。"""
    
    print(f"内容长度: {len(content)} 字")
    return content

def test_flow(port: int = 10002):
    cdp_url = f"http://127.0.0.1:{port}"
    
    with sync_playwright() as p:
        print("[连接] 连接 Chrome...")
        browser = p.chromium.connect_over_cdp(cdp_url)
        page = browser.contexts[0].pages[0]
        print(f"[页面] {page.url}")
        
        # 1. 填写章节号
        print("\n[1] 填写章节号...")
        page.locator('.serial-editor-title-left input').first.fill("1001")
        print("  [OK] 1001")
        
        # 2. 填写标题
        print("[2] 填写标题...")
        page.locator('.serial-editor-title-right input').first.fill("定时发布测试-第一章")
        print("  [OK]")
        
        # 3. 填写内容
        print("[3] 填写内容...")
        content = get_real_content()
        page.locator('.ProseMirror').first.fill(content)
        length = page.evaluate('() => document.querySelector(".ProseMirror").innerText.length')
        print(f"  [OK] 实际: {length}字")
        
        # 4. 点击下一步
        print("[4] 点击下一步...")
        page.locator('button:has-text("下一步")').first.click()
        print("  [OK]")
        
        # 5. 处理模态框
        print("\n[5] 等待模态框...")
        for i in range(10):
            time.sleep(0.5)
            
            card = page.locator('.publish-confirm-card').first
            if card.count() > 0:
                print("  [OK] 找到模态框")
                
                # AI 选"是"
                try:
                    labels = card.locator('label.arco-radio').all()
                    if len(labels) >= 1:
                        labels[0].click()
                        print("  [OK] AI: 是")
                except Exception as e:
                    print(f"  [WARN] AI: {e}")
                
                time.sleep(0.3)
                
                # 定时发布
                print("\n[6] 开启定时发布...")
                try:
                    switch = page.locator('button[role="switch"]').first
                    if switch.count() > 0:
                        is_on = switch.get_attribute('aria-checked') == 'true'
                        print(f"    当前: {'开' if is_on else '关'}")
                        
                        if not is_on:
                            switch.click()
                            print("    [OK] 开启")
                            time.sleep(0.8)
                            
                            # 选时间
                            picker = page.locator('.arco-picker-input input').first
                            if picker.count() > 0:
                                picker.click()
                                time.sleep(0.3)
                                # 选第一个时间
                                cell = page.locator('.arco-timepicker-cell').first
                                if cell.count() > 0:
                                    cell.click()
                                    print("    [OK] 选时间")
                except Exception as e:
                    print(f"    [ERR] {e}")
                
                time.sleep(0.3)
                
                # 确认发布
                print("\n[7] 确认发布...")
                try:
                    footer = page.locator('.arco-modal-footer').first
                    footer.locator('button.arco-btn-primary').first.click()
                    print("  [OK]")
                except Exception as e:
                    print(f"  [ERR] {e}")
                
                break
        
        # 6. 风险检测
        print("\n[8] 风险检测...")
        for i in range(5):
            time.sleep(0.5)
            risk = page.locator('.arco-modal:has-text("风险检测")').first
            if risk.count() > 0 and risk.is_visible():
                print("  [发现]")
                risk.locator('button.arco-btn-primary').first.click()
                print("  [OK] 确定")
                break
            if '/manage' in page.url:
                print("  [OK] 返回管理页")
                break
        
        print(f"\n[结果] {page.url}")
        print("[完成]")
        input("按回车...")
        browser.close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 10002
    test_flow(port)
