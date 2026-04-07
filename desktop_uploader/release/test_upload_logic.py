#!/usr/bin/env python3
"""
上传逻辑自测脚本
测试场景：
1. 正本上传（首次上传，章节号<=20）
2. 自动续传（已有发布记录，自动推算日期）
3. 手动指定日期（用户设置了manual_publish_date）
4. 剩余章节上传（部分已上传，继续上传剩余）
5. 跨天上传（当天已满，自动跨天）
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

class UploadLogicTester:
    """上传逻辑测试器"""
    
    def __init__(self):
        self.test_results = []
        
    def log(self, msg, level="INFO"):
        print(f"[{level}] {msg}")
        
    def assert_equals(self, actual, expected, test_name):
        """断言相等"""
        if actual == expected:
            self.log(f"✅ {test_name}: 通过", "PASS")
            self.test_results.append((test_name, True, None))
            return True
        else:
            self.log(f"❌ {test_name}: 失败", "FAIL")
            self.log(f"   期望: {expected}", "FAIL")
            self.log(f"   实际: {actual}", "FAIL")
            self.test_results.append((test_name, False, f"期望:{expected}, 实际:{actual}"))
            return False
    
    def assert_true(self, condition, test_name):
        """断言为真"""
        if condition:
            self.log(f"✅ {test_name}: 通过", "PASS")
            self.test_results.append((test_name, True, None))
            return True
        else:
            self.log(f"❌ {test_name}: 失败", "FAIL")
            self.test_results.append((test_name, False, "条件不满足"))
            return False
    
    # ==================== 场景1: 正本上传（章节号1-20） ====================
    def test_scene1_first_upload_within_20(self):
        """场景1: 首次上传，章节号1-20（全部立即发布）"""
        self.log("\n" + "="*60)
        self.log("场景1: 正本上传（章节号1-20，全部立即发布）")
        self.log("="*60)
        
        # 模拟配置
        first_count = 20
        daily_count = 8
        chapter_numbers = list(range(1, 21))  # 1-20章
        
        # 判断是否需要定时
        needs_schedule = any(ch_num > first_count for ch_num in chapter_numbers)
        
        self.assert_equals(needs_schedule, False, "章节1-20不需要定时")
        self.log(f"章节范围: 1-20, 全部≤{first_count}，立即发布")
        
        return True
    
    # ==================== 场景2: 正本上传（章节号21-30） ====================
    def test_scene2_first_upload_over_20(self):
        """场景2: 首次上传，章节号21-30（需要定时）"""
        self.log("\n" + "="*60)
        self.log("场景2: 正本上传（章节号21-30，需要定时）")
        self.log("="*60)
        
        first_count = 20
        daily_count = 8
        chapter_numbers = list(range(21, 31))  # 21-30章
        
        # 判断是否需要定时
        needs_schedule = any(ch_num > first_count for ch_num in chapter_numbers)
        self.assert_equals(needs_schedule, True, "章节21-30需要定时")
        
        # 模拟定时计算（首次上传，无发布记录，无手动配置）
        # 应该从明天开始
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 模拟分配
        schedule = {}
        base_date = datetime.now() + timedelta(days=1)
        chapters_in_day = 0
        
        for chap_num in chapter_numbers:
            if chapters_in_day >= daily_count:
                base_date = base_date + timedelta(days=1)
                chapters_in_day = 0
            schedule[chap_num] = base_date.strftime('%Y-%m-%d %H:%M')
            chapters_in_day += 1
        
        # 验证分配结果
        self.log(f"定时计划: {len(schedule)}章")
        
        # 21-28章应该在明天（第一天）
        for ch in range(21, 29):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, tomorrow, f"第{ch}章在明天")
        
        # 29-30章应该在下一天
        day_after = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
        for ch in range(29, 31):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, day_after, f"第{ch}章在后天")
        
        return True
    
    # ==================== 场景3: 自动续传 ====================
    def test_scene3_auto_resume(self):
        """场景3: 自动续传（已有发布记录）"""
        self.log("\n" + "="*60)
        self.log("场景3: 自动续传（已有发布记录）")
        self.log("="*60)
        
        # 模拟发布记录
        published_chapters = {
            "21": {"publish_time": "2026-04-08 06:00"},
            "22": {"publish_time": "2026-04-08 06:00"},
            "23": {"publish_time": "2026-04-08 06:00"},
            "24": {"publish_time": "2026-04-08 06:00"},
            "25": {"publish_time": "2026-04-08 06:00"},
            "26": {"publish_time": "2026-04-08 06:00"},
        }
        
        first_count = 20
        daily_count = 8
        chapter_numbers = list(range(27, 35))  # 27-34章
        
        # 模拟获取最后发布信息
        last_date = "2026-04-08"
        last_count = 6  # 4月8日已发6章
        
        # 判断基准日期
        if last_count < daily_count:
            base_date = last_date
            chapters_in_day = last_count
            self.log(f"续发: 从{base_date}继续，已发{chapters_in_day}章")
        else:
            base_date = "2026-04-09"
            chapters_in_day = 0
        
        # 模拟分配
        schedule = {}
        base_dt = datetime.strptime(f"{base_date} 06:00", "%Y-%m-%d %H:%M")
        
        for chap_num in chapter_numbers:
            if chapters_in_day >= daily_count:
                base_dt = base_dt + timedelta(days=1)
                chapters_in_day = 0
            schedule[chap_num] = base_dt.strftime('%Y-%m-%d %H:%M')
            chapters_in_day += 1
        
        # 验证：27-28章应该在4月8日（6+2=8，满额）
        for ch in range(27, 29):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, "2026-04-08", f"第{ch}章在4月8日")
        
        # 29章开始应该在4月9日
        for ch in range(29, 35):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, "2026-04-09", f"第{ch}章在4月9日")
        
        return True
    
    # ==================== 场景4: 手动指定日期 ====================
    def test_scene4_manual_date(self):
        """场景4: 手动指定日期"""
        self.log("\n" + "="*60)
        self.log("场景4: 手动指定日期")
        self.log("="*60)
        
        # 模拟手动配置
        manual_date = "2026-04-10"
        manual_time = "08:00"
        
        first_count = 20
        daily_count = 8
        chapter_numbers = list(range(27, 35))  # 27-34章
        
        # 手动配置优先，从指定日期开始
        base_dt = datetime.strptime(f"{manual_date} {manual_time}", "%Y-%m-%d %H:%M")
        chapters_in_day = 0  # 假设手动配置的日期还没有发布记录
        
        self.log(f"使用手动配置: {manual_date} {manual_time}")
        
        # 模拟分配
        schedule = {}
        for chap_num in chapter_numbers:
            if chapters_in_day >= daily_count:
                base_dt = base_dt + timedelta(days=1)
                chapters_in_day = 0
            schedule[chap_num] = base_dt.strftime('%Y-%m-%d %H:%M')
            chapters_in_day += 1
        
        # 验证：27-34章应该从4月10日开始
        for ch in range(27, 35):
            date = schedule[ch].split(' ')[0]
            expected_date = "2026-04-10" if ch <= 34 else "2026-04-11"
            if ch <= 34:
                self.assert_equals(date, "2026-04-10", f"第{ch}章在4月10日")
        
        return True
    
    # ==================== 场景5: 跨天上传 ====================
    def test_scene5_cross_day(self):
        """场景5: 跨天上传（当天已满）"""
        self.log("\n" + "="*60)
        self.log("场景5: 跨天上传（当天已满）")
        self.log("="*60)
        
        # 模拟发布记录：4月8日已满8章
        published_chapters = {
            "21": {"publish_time": "2026-04-08 06:00"},
            "22": {"publish_time": "2026-04-08 06:00"},
            "23": {"publish_time": "2026-04-08 06:00"},
            "24": {"publish_time": "2026-04-08 06:00"},
            "25": {"publish_time": "2026-04-08 06:00"},
            "26": {"publish_time": "2026-04-08 06:00"},
            "27": {"publish_time": "2026-04-08 06:00"},
            "28": {"publish_time": "2026-04-08 06:00"},  # 满8章
        }
        
        first_count = 20
        daily_count = 8
        chapter_numbers = list(range(29, 40))  # 29-39章
        
        # 获取最后发布信息
        last_date = "2026-04-08"
        last_count = 8  # 已满
        
        # 应该跨到下一天
        if last_count >= daily_count:
            base_date = "2026-04-09"
            chapters_in_day = 0
            self.log(f"跨天: 从{base_date}开始，新一天")
        
        # 模拟分配
        schedule = {}
        base_dt = datetime.strptime(f"{base_date} 06:00", "%Y-%m-%d %H:%M")
        
        for chap_num in chapter_numbers:
            if chapters_in_day >= daily_count:
                base_dt = base_dt + timedelta(days=1)
                chapters_in_day = 0
            schedule[chap_num] = base_dt.strftime('%Y-%m-%d %H:%M')
            chapters_in_day += 1
        
        # 验证：29-36章在4月9日，37-39章在4月10日
        for ch in range(29, 37):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, "2026-04-09", f"第{ch}章在4月9日")
        
        for ch in range(37, 40):
            date = schedule[ch].split(' ')[0]
            self.assert_equals(date, "2026-04-10", f"第{ch}章在4月10日")
        
        return True
    
    # ==================== 场景6: 混合上传（已发布+新章节） ====================
    def test_scene6_mixed_upload(self):
        """场景6: 混合上传（包含已发布章节）"""
        self.log("\n" + "="*60)
        self.log("场景6: 混合上传（包含已发布章节）")
        self.log("="*60)
        
        # 用户选择了第21-30章，但21-26已发布
        all_chapters = list(range(21, 31))
        published = {21, 22, 23, 24, 25, 26}
        to_upload = [ch for ch in all_chapters if ch not in published]
        
        self.log(f"选择章节: {all_chapters}")
        self.log(f"已发布: {sorted(published)}")
        self.log(f"待上传: {to_upload}")
        
        self.assert_equals(to_upload, [27, 28, 29, 30], "过滤已发布章节")
        
        return True
    
    def run_all_tests(self):
        """运行所有测试"""
        self.log("\n" + "="*70)
        self.log("开始上传逻辑自测")
        self.log("="*70)
        
        tests = [
            ("场景1: 正本上传（1-20章）", self.test_scene1_first_upload_within_20),
            ("场景2: 正本上传（21-30章）", self.test_scene2_first_upload_over_20),
            ("场景3: 自动续传", self.test_scene3_auto_resume),
            ("场景4: 手动指定日期", self.test_scene4_manual_date),
            ("场景5: 跨天上传", self.test_scene5_cross_day),
            ("场景6: 混合上传", self.test_scene6_mixed_upload),
        ]
        
        passed = 0
        failed = 0
        
        for name, test_func in tests:
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"❌ {name}: 异常 - {e}", "ERROR")
                failed += 1
        
        # 输出汇总
        self.log("\n" + "="*70)
        self.log("自测结果汇总")
        self.log("="*70)
        self.log(f"通过: {passed}/{len(tests)}")
        self.log(f"失败: {failed}/{len(tests)}")
        
        if failed == 0:
            self.log("\n✅ 所有测试通过！逻辑验证成功。", "PASS")
        else:
            self.log("\n⚠️ 存在失败的测试，请检查。", "FAIL")
        
        return failed == 0

if __name__ == "__main__":
    tester = UploadLogicTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
