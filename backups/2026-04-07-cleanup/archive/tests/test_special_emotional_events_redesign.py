#!/usr/bin/env python
"""
特殊情感事件重新设计验证脚本

验证特殊情感事件是否：
1. 正确附着在中型事件上
2. 没有章节重叠问题
3. 数据结构符合新格式

使用方法:
    python tests/test_special_emotional_events_redesign.py <项目名称>

示例:
    python tests/test_special_emotional_events_redesign.py "吞噬万界：从一把生锈铁剑开始"
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger("SpecialEventsTest")


class SpecialEventsValidator:
    """特殊情感事件验证器"""
    
    def __init__(self, project_title: str):
        self.project_title = project_title
        self.safe_title = self._sanitize_title(project_title)
        self.project_dir = Path("小说项目") / self.project_title
        
        if not self.project_dir.exists():
            self.project_dir = Path("小说项目") / self.safe_title
        
        logger.info(f"初始化验证器: 项目={project_title}")
    
    def _sanitize_title(self, title: str) -> str:
        """清理标题中的特殊字符"""
        import re
        return re.sub(r'[\\/*?"<>|]', "_", title)
    
    def load_storyline_data(self) -> Dict:
        """加载故事线数据"""
        # 尝试从多个位置加载
        plans_dir = self.project_dir / "plans"
        planning_dir = self.project_dir / "planning"
        
        # 优先从plans目录加载
        if plans_dir.exists():
            stage_files = list(plans_dir.glob("*_writing_plan.json"))
            if stage_files:
                logger.info(f"从plans目录加载: 找到{len(stage_files)}个阶段文件")
                
                all_major_events = []
                stage_info = []
                
                for stage_file in sorted(stage_files):
                    try:
                        with open(stage_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        stage_plan = data.get('stage_writing_plan', {})
                        major_events = stage_plan.get('event_system', {}).get('major_events', [])
                        
                        for event in major_events:
                            all_major_events.append(event)
                        
                        stage_info.append({
                            'file': stage_file.name,
                            'major_events_count': len(major_events)
                        })
                        
                        logger.info(f"  {stage_file.name}: {len(major_events)}个重大事件")
                    except Exception as e:
                        logger.error(f"  读取{stage_file.name}失败: {e}")
                
                return {
                    'major_events': all_major_events,
                    'stage_info': stage_info
                }
        
        logger.error("未找到故事线数据")
        return None
    
    def validate_special_events(self) -> Dict:
        """验证特殊情感事件"""
        logger.info("\n开始验证特殊情感事件...")
        
        storyline = self.load_storyline_data()
        if not storyline:
            return {
                'success': False,
                'error': '无法加载故事线数据'
            }
        
        major_events = storyline['major_events']
        logger.info(f"总共检查 {len(major_events)} 个重大事件")
        
        results = {
            'success': True,
            'total_major_events': len(major_events),
            'events_with_special_events': 0,
            'total_special_events': 0,
            'issues': [],
            'warnings': []
        }
        
        for idx, major_event in enumerate(major_events):
            event_name = major_event.get('name', f'重大事件{idx+1}')
            logger.info(f"\n检查重大事件: {event_name}")
            
            # 检查composition
            composition = major_event.get('composition', {})
            if not composition:
                logger.info(f"  ⚠️ 没有composition字段")
                continue
            
            # 检查每个phase的中型事件
            for phase_name, phase_events in composition.items():
                if not isinstance(phase_events, list):
                    continue
                
                for me_idx, medium_event in enumerate(phase_events):
                    me_name = medium_event.get('name', f'中型事件{me_idx+1}')
                    
                    # 检查特殊情感事件
                    special_events = medium_event.get('special_emotional_events', [])
                    
                    if special_events:
                        results['events_with_special_events'] += 1
                        results['total_special_events'] += len(special_events)
                        logger.info(f"  ✅ 中型事件'{me_name}'包含{len(special_events)}个特殊情感事件")
                        
                        # 验证每个特殊情感事件
                        for se_idx, se in enumerate(special_events):
                            se_name = se.get('name', f'特殊事件{se_idx+1}')
                            
                            # 验证必需字段
                            if 'target_chapter' not in se:
                                results['issues'].append(f"{event_name} > {phase_name} > {me_name} > {se_name}: 缺少target_chapter字段")
                            else:
                                logger.info(f"    ✅ {se_name}: 第{se['target_chapter']}章")
                            
                            # 验证不应该有chapter_range
                            if 'chapter_range' in se:
                                results['issues'].append(f"{event_name} > {phase_name} > {me_name} > {se_name}: 不应该有chapter_range字段")
                            
                            # 验证目的字段
                            if 'purpose' not in se:
                                results['warnings'].append(f"{event_name} > {phase_name} > {me_name} > {se_name}: 缺少purpose字段")
                    else:
                        logger.info(f"  - 中型事件'{me_name}'没有特殊情感事件")
            
            # 检查重大事件级别的特殊情感事件（旧格式）
            old_format_events = major_event.get('special_emotional_events', [])
            if old_format_events:
                results['issues'].append(f"{event_name}: 仍然包含旧格式的special_emotional_events（应该在composition中的中型事件上）")
        
        # 输出验证结果
        logger.info("\n" + "="*60)
        logger.info("验证结果汇总")
        logger.info("="*60)
        logger.info(f"✅ 总重大事件: {results['total_major_events']}")
        logger.info(f"✅ 包含特殊情感事件的重大事件: {results['events_with_special_events']}")
        logger.info(f"✅ 特殊情感事件总数: {results['total_special_events']}")
        
        if results['issues']:
            logger.info(f"\n❌ 发现 {len(results['issues'])} 个问题:")
            for issue in results['issues']:
                logger.info(f"  - {issue}")
        else:
            logger.info("\n✅ 没有发现严重问题")
        
        if results['warnings']:
            logger.info(f"\n⚠️  发现 {len(results['warnings'])} 个警告:")
            for warning in results['warnings']:
                logger.info(f"  - {warning}")
        else:
            logger.info("\n✅ 没有发现警告")
        
        logger.info("="*60)
        
        results['success'] = len(results['issues']) == 0
        
        return results
    
    def check_chapter_overlap(self) -> Dict:
        """检查章节重叠"""
        logger.info("\n检查章节重叠...")
        
        storyline = self.load_storyline_data()
        if not storyline:
            return {
                'success': False,
                'error': '无法加载故事线数据'
            }
        
        major_events = storyline['major_events']
        
        # 收集所有章节分配
        chapter_allocations = {}
        
        for major_event in major_events:
            # 重大事件的章节范围
            me_range = major_event.get('chapter_range', '')
            if me_range:
                try:
                    from src.managers.StagePlanUtils import parse_chapter_range
                    start, end = parse_chapter_range(me_range)
                    for ch in range(start, end + 1):
                        if ch in chapter_allocations:
                            chapter_allocations[ch].append({
                                'type': 'major',
                                'name': major_event.get('name', ''),
                                'source': 'major_event'
                            })
                        else:
                            chapter_allocations[ch] = [{
                                'type': 'major',
                                'name': major_event.get('name', ''),
                                'source': 'major_event'
                            }]
                except:
                    pass
            
            # 中型事件的章节范围
            composition = major_event.get('composition', {})
            if composition:
                for phase_name, phase_events in composition.items():
                    if isinstance(phase_events, list):
                        for medium_event in phase_events:
                            me_range = medium_event.get('chapter_range', '')
                            if me_range:
                                try:
                                    from src.managers.StagePlanUtils import parse_chapter_range
                                    start, end = parse_chapter_range(me_range)
                                    for ch in range(start, end + 1):
                                        if ch in chapter_allocations:
                                            chapter_allocations[ch].append({
                                                'type': 'medium',
                                                'name': medium_event.get('name', ''),
                                                'phase': phase_name,
                                                'source': 'medium_event'
                                            })
                                        else:
                                            chapter_allocations[ch] = [{
                                                'type': 'medium',
                                                'name': medium_event.get('name', ''),
                                                'phase': phase_name,
                                                'source': 'medium_event'
                                            }]
                                except:
                                    pass
            
            # 特殊情感事件的章节（只检查target_chapter）
            if composition:
                for phase_name, phase_events in composition.items():
                    if isinstance(phase_events, list):
                        for medium_event in phase_events:
                            special_events = medium_event.get('special_emotional_events', [])
                            for se in special_events:
                                target_ch = se.get('target_chapter')
                                if target_ch:
                                    if target_ch in chapter_allocations:
                                        chapter_allocations[target_ch].append({
                                            'type': 'special',
                                            'name': se.get('name', ''),
                                            'source': 'special_emotional_event'
                                        })
                                    else:
                                        chapter_allocations[target_ch] = [{
                                            'type': 'special',
                                            'name': se.get('name', ''),
                                            'source': 'special_emotional_event'
                                        }]
        
        # 检查重叠
        overlap_count = 0
        overlaps = []
        
        for chapter, allocations in sorted(chapter_allocations.items()):
            if len(allocations) > 1:
                overlap_count += 1
                overlaps.append({
                    'chapter': chapter,
                    'count': len(allocations),
                    'allocations': allocations
                })
        
        # 输出结果
        logger.info(f"\n章节分配检查结果:")
        logger.info(f"  总章节数: {len(chapter_allocations)}")
        logger.info(f"  有重叠的章节数: {overlap_count}")
        
        if overlaps:
            logger.info(f"\n❌ 发现章节重叠:")
            for overlap in overlaps:
                logger.info(f"  第{overlap['chapter']}章 ({overlap['count']}个分配):")
                for alloc in overlap['allocations']:
                    logger.info(f"    - {alloc['type']}: {alloc['name']} (来自{alloc['source']})")
            
            return {
                'success': False,
                'overlap_count': overlap_count,
                'overlaps': overlaps
            }
        else:
            logger.info("✅ 没有发现章节重叠！")
            return {
                'success': True,
                'overlap_count': 0,
                'overlaps': []
            }
    
    def run_validation(self):
        """运行完整验证"""
        logger.info("\n" + "="*60)
        logger.info("开始验证特殊情感事件重新设计")
        logger.info("="*60)
        
        # 验证1: 特殊情感事件结构
        structure_result = self.validate_special_events()
        
        # 验证2: 章节重叠
        overlap_result = self.check_chapter_overlap()
        
        # 汇总
        logger.info("\n" + "="*60)
        logger.info("验证完成")
        logger.info("="*60)
        
        if structure_result['success'] and overlap_result['success']:
            logger.info("✅ 所有验证通过！")
            return True
        else:
            logger.info("❌ 验证失败，请检查上述问题")
            return False


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python tests/test_special_emotional_events_redesign.py <项目名称>")
        print("\n示例:")
        print("  python tests/test_special_emotional_events_redesign.py \"吞噬万界：从一把生锈铁剑开始\"")
        print("\n可用的项目列表:")
        
        # 列出可用的项目
        projects_dir = Path("小说项目")
        if projects_dir.exists():
            projects = [d for d in projects_dir.iterdir() if d.is_dir()]
            for i, project in enumerate(projects, 1):
                print(f"  {i}. {project.name}")
        
        sys.exit(1)
    
    project_title = sys.argv[1]
    
    validator = SpecialEventsValidator(project_title)
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()