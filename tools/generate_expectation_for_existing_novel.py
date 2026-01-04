"""
为现有项目生成期待感映射的临时脚本
用于解决之前生成项目时缺少期待感映射的问题
"""

import sys
import os
import json
from pathlib import Path

# 设置UTF-8编码输出（解决Windows控制台问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator, ExpectationType
from src.managers.StagePlanUtils import parse_chapter_range
from src.utils.logger import get_logger

logger = get_logger("GenerateExpectation")


def generate_expectation_for_novel(novel_title: str):
    """
    为指定小说生成期待感映射
    
    Args:
        novel_title: 小说标题
    """
    logger.info(f"🎯 开始为《{novel_title}》生成期待感映射...")
    
    # 1. 查找项目目录
    project_dir = Path("小说项目") / novel_title
    if not project_dir.exists():
        # 尝试使用安全文件名
        import re
        safe_title = re.sub(r'[\\/*?"<>|]', "_", novel_title)
        project_dir = Path("小说项目") / safe_title
    
    if not project_dir.exists():
        logger.error(f"❌ 未找到项目目录: {project_dir}")
        logger.info(f"请确保项目目录存在，目录应为：小说项目/{novel_title}")
        return False
    
    logger.info(f"✅ 找到项目目录: {project_dir}")
    
    # 2. 加载所有阶段的写作计划
    # 尝试多个可能的目录
    possible_dirs = [
        project_dir / "plans",
        project_dir / "planning",
        project_dir / "stage_writing_plans"
    ]
    
    plans_dir = None
    stage_files = []
    
    for dir_path in possible_dirs:
        if dir_path.exists():
            files = list(dir_path.glob("*_writing_plan.json"))
            if files:
                plans_dir = dir_path
                stage_files = files
                logger.info(f"✅ 找到写作计划目录: {dir_path}")
                break
    
    if not plans_dir:
        logger.error(f"❌ 未找到写作计划目录")
        logger.info(f"尝试的目录: {[str(d) for d in possible_dirs]}")
        return False
    
    if not stage_files:
        logger.error(f"❌ 未找到任何写作计划文件")
        return False
    
    logger.info(f"✅ 找到 {len(stage_files)} 个写作计划文件")
    
    # 3. 初始化期待感管理器
    expectation_manager = ExpectationManager()
    
    # 4. 为每个阶段生成期待感映射
    total_tagged = 0
    
    for stage_file in sorted(stage_files):
        logger.info(f"\n{'='*60}")
        logger.info(f"处理阶段文件: {stage_file.name}")
        
        # 从文件名提取阶段名称
        import re
        match = re.search(r'_([^_]+_stage)_writing_plan$', stage_file.name)
        if match:
            stage_name = match.group(1)
        else:
            logger.warn(f"  ⚠️ 无法从文件名提取阶段名称，跳过")
            continue
        
        logger.info(f"  阶段名称: {stage_name}")
        
        # 读取写作计划
        try:
            with open(stage_file, 'r', encoding='utf-8') as f:
                stage_data = json.load(f)
        except Exception as e:
            logger.error(f"  ❌ 读取文件失败: {e}")
            continue
        
        # 提取重大事件
        stage_plan = stage_data.get('stage_writing_plan', {})
        event_system = stage_plan.get('event_system', {})
        major_events = event_system.get('major_events', [])
        
        if not major_events:
            logger.info(f"  ℹ️ 该阶段没有重大事件，跳过")
            continue
        
        logger.info(f"  找到 {len(major_events)} 个重大事件")
        
        # 为该阶段生成期待感映射
        logger.info(f"  开始为事件添加期待感标签...")
        
        for event in major_events:
            event_name = event.get('name', '未命名事件')
            
            # 使用规则匹配选择期待类型
            exp_type = _select_expectation_type(event)
            
            # 计算种植和目标章节
            chapter_range = event.get('chapter_range', '1-10')
            try:
                start_ch, end_ch = parse_chapter_range(chapter_range)
                target_ch = max(start_ch + 3, end_ch)
            except:
                target_ch = end_ch if chapter_range else 10
                start_ch = 1
            
            # 种植期待
            exp_id = expectation_manager.tag_event_with_expectation(
                event_id=event_name,
                expectation_type=exp_type,
                planting_chapter=start_ch,
                description=f"{event_name}: {event.get('main_goal', '')[:80]}...",
                target_chapter=target_ch
            )
            
            total_tagged += 1
            logger.info(f"    ✓ 为事件 '{event_name}' 添加期待: {exp_type.value}")
        
        logger.info(f"  ✅ 该阶段完成，共添加 {len(major_events)} 个期待标签")
    
    # 5. 导出期待感映射
    expectation_map = expectation_manager.export_expectation_map()
    
    # 6. 保存到项目目录
    expectation_map_file = project_dir / "expectation_map.json"
    with open(expectation_map_file, 'w', encoding='utf-8') as f:
        json.dump({
            'novel_title': novel_title,
            'expectation_map': expectation_map,
            'total_tagged': total_tagged,
            'generated_at': __import__('datetime').datetime.now().isoformat(),
            'generation_method': 'rules_based'  # 标记为规则匹配生成
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"✅ 期待感映射生成完成！")
    logger.info(f"  总计: {total_tagged} 个事件")
    logger.info(f"  保存路径: {expectation_map_file}")
    logger.info(f"{'='*60}")
    
    return True


def _select_expectation_type(event):
    """
    根据事件特征选择期待类型（规则匹配）
    
    Args:
        event: 事件字典
        
    Returns:
        ExpectationType
    """
    main_goal = event.get('main_goal', '').lower()
    emotional_focus = event.get('emotional_focus', '').lower()
    name = event.get('name', '').lower()
    description = event.get('description', '').lower()
    role_in_stage_arc = event.get('role_in_stage_arc', '').lower()
    
    # 组合所有文本用于分析
    all_text = f"{main_goal} {emotional_focus} {name} {description} {role_in_stage_arc}"
    
    # 决策树：根据事件特征选择期待类型
    scores = {
        ExpectationType.SUPPRESSION_RELEASE: 0,
        ExpectationType.SHOWCASE: 0,
        ExpectationType.MYSTERY_FORESHADOW: 0,
        ExpectationType.EMOTIONAL_HOOK: 0,
        ExpectationType.POWER_GAP: 0,
        ExpectationType.NESTED_DOLL: 0
    }
    
    # 压抑释放类型关键词
    suppression_keywords = ['击败', '战胜', '复仇', '反击', '雪耻', '逆袭', '反杀', '报仇',
                           '报复', '反击战', '翻盘', '逆转', '反攻', '压制']
    for kw in suppression_keywords:
        if kw in all_text:
            scores[ExpectationType.SUPPRESSION_RELEASE] += 3
    
    # 展示橱窗类型关键词
    showcase_keywords = ['获得', '得到', '炼成', '夺取', '收获', '宝物', '神器',
                         '功法', '秘籍', '法宝', '装备', '宝藏', '发现', '解锁']
    for kw in showcase_keywords:
        if kw in all_text:
            scores[ExpectationType.SHOWCASE] += 3
    
    # 伏笔揭秘类型关键词
    mystery_keywords = ['揭秘', '真相', '发现', '秘密', '身世', '阴谋', '计谋', '背后',
                        '来历', '身份', '真实', '隐藏', '揭开', '曝光']
    for kw in mystery_keywords:
        if kw in all_text:
            scores[ExpectationType.MYSTERY_FORESHADOW] += 3
    
    # 情绪钩子类型关键词
    emotion_keywords = ['误解', '轻视', '震惊', '打脸', '羞辱', '嘲讽', '看不起',
                        '不屑', '挑衅', '羞耻', '愤怒', '爆发']
    for kw in emotion_keywords:
        if kw in all_text:
            scores[ExpectationType.EMOTIONAL_HOOK] += 3
    
    # 实力差距类型关键词
    power_keywords = ['展示', '学习', '修炼', '提升', '突破', '成长', '进阶', '升级',
                      '功法', '实力', '境界']
    for kw in power_keywords:
        if kw in all_text:
            scores[ExpectationType.POWER_GAP] += 2
    
    # 套娃期待类型关键词（默认类型）
    nested_keywords = ['挑战', '任务', '试炼', '考验', '闯关', '冒险', '探索',
                       '旅程', '征程', '历练']
    for kw in nested_keywords:
        if kw in all_text:
            scores[ExpectationType.NESTED_DOLL] += 2
    
    # 选择得分最高的类型
    final_type = max(scores.items(), key=lambda x: x[1])[0]
    
    return final_type


if __name__ == "__main__":
    # 使用示例
    novel_title = "重生成剑：宿主祭天，法力无边"
    
    print("="*60)
    print("为现有项目生成期待感映射")
    print("="*60)
    print(f"小说标题: {novel_title}")
    print("="*60)
    
    success = generate_expectation_for_novel(novel_title)
    
    if success:
        print("\n✅ 期待感映射生成成功！")
        print("\n下一步：")
        print("1. 刷新故事线页面，应该能看到期待感标签了")
        print("2. 新生成的项目会自动包含期待感映射")
    else:
        print("\n❌ 期待感映射生成失败")
        print("请检查：")
        print("1. 项目目录是否存在")
        print("2. plans 目录中是否有写作计划文件")