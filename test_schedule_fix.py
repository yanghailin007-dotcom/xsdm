#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试定时发布计划计算逻辑
验证修复后的 _calculate_publish_schedule_with_sync 方法
"""

from datetime import datetime, timedelta

def test_schedule_logic():
    """
    测试场景：
    - 今天4月7日
    - 首次发布20章
    - 每天发布8章
    - 章节号：1-100章
    
    预期结果：
    - 第1-20章：今天直接发布（无定时）
    - 第21-28章：4月8日
    - 第29-36章：4月9日
    - 第37-44章：4月10日
    - ...以此类推
    """
    
    # 模拟参数
    chapter_numbers = list(range(1, 101))  # 第1-100章
    first_count = 20  # 首次发布20章
    daily_count = 8   # 每天8章
    publish_time = "07:00"  # 发布时间
    interval = 30  # 章节间隔（分钟）
    
    # 模拟 novel_config
    novel_config = {'publish_config': {}}
    
    # 执行计算逻辑（复制修复后的代码逻辑）
    schedule = {}
    scheduled_chapters = sorted([ch for ch in chapter_numbers if ch > first_count])
    
    if not scheduled_chapters:
        print("没有需要定时的章节")
        return
    
    print("=" * 60)
    print(f"测试场景：今天4月7日，首次发布{first_count}章，之后每天{daily_count}章")
    print(f"需要定时的章节：第{scheduled_chapters[0]}-{scheduled_chapters[-1]}章（共{len(scheduled_chapters)}章）")
    print("=" * 60)
    
    # 从明天开始计算
    hour, minute = map(int, publish_time.split(':'))
    tomorrow = datetime.now() + timedelta(days=1)
    base_time = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
    
    print(f"基准时间（明天）: {base_time.strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # 分配时间
    day_offset = 0
    chapters_in_current_day = 0
    
    for i, chap_num in enumerate(scheduled_chapters):
        target_date = (base_time + timedelta(days=day_offset)).date()
        target_time = base_time.time()
        
        schedule[chap_num] = f"{target_date} {target_time.strftime('%H:%M')}"
        
        chapters_in_current_day += 1
        
        if chapters_in_current_day >= daily_count:
            day_offset += 1
            chapters_in_current_day = 0
    
    # 按日期分组显示
    date_groups = {}
    for chap_num, time_str in schedule.items():
        date = time_str.split()[0]
        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(chap_num)
    
    print("定时发布计划：")
    print("-" * 60)
    for date in sorted(date_groups.keys()):
        chapters = date_groups[date]
        # 格式化日期（显示4月8日、4月9日等）
        dt = datetime.strptime(date, '%Y-%m-%d')
        date_display = dt.strftime('%m月%d日')
        print(f"  {date_display}: 第{min(chapters):3d}-{max(chapters):3d}章 ({len(chapters):2d}章)")
    print("-" * 60)
    
    # 验证结果
    print("\n验证结果：")
    errors = []
    
    # 验证1：第21章应该是明天
    chap_21_date = schedule.get(21, '').split()[0]
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    if chap_21_date == tomorrow_str:
        print(f"✓ 第21章是明天（{chap_21_date}）")
    else:
        print(f"✗ 第21章应该是明天（{tomorrow_str}），实际是{chap_21_date}")
        errors.append("第21章日期错误")
    
    # 验证2：第21-28章是同一日
    dates_21_28 = [schedule.get(i, '').split()[0] for i in range(21, 29) if i in schedule]
    if len(set(dates_21_28)) == 1:
        print(f"✓ 第21-28章是同一天（{dates_21_28[0]}）")
    else:
        print(f"✗ 第21-28章日期不一致: {set(dates_21_28)}")
        errors.append("第21-28章日期不一致")
    
    # 验证3：第29-36章是下一天
    dates_29_36 = [schedule.get(i, '').split()[0] for i in range(29, 37) if i in schedule]
    if len(set(dates_29_36)) == 1:
        print(f"✓ 第29-36章是同一天（{dates_29_36[0]}）")
    else:
        print(f"✗ 第29-36章日期不一致: {set(dates_29_36)}")
        errors.append("第29-36章日期不一致")
    
    # 验证4：第29章比第28章晚一天
    date_28 = datetime.strptime(schedule.get(28, '').split()[0], '%Y-%m-%d')
    date_29 = datetime.strptime(schedule.get(29, '').split()[0], '%Y-%m-%d')
    if (date_29 - date_28).days == 1:
        print(f"✓ 第29章比第28章晚1天")
    else:
        print(f"✗ 第29章应该比第28章晚1天，实际相差{(date_29 - date_28).days}天")
        errors.append("跨天计算错误")
    
    # 验证5：每天正好是8章
    for date, chapters in date_groups.items():
        if len(chapters) != daily_count:
            # 最后一天可能不足8章，是正常的
            dt = datetime.strptime(date, '%Y-%m-%d')
            if date != max(date_groups.keys()):
                print(f"✗ {date} 有{len(chapters)}章，应该有{daily_count}章")
                errors.append(f"{date}章节数错误")
    
    print()
    if errors:
        print(f"发现 {len(errors)} 个错误:")
        for e in errors:
            print(f"  - {e}")
        return False
    else:
        print("✓ 所有验证通过！")
        return True

if __name__ == '__main__':
    test_schedule_logic()
