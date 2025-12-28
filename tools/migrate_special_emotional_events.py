#!/usr/bin/env python
"""
特殊情感事件数据迁移脚本

将旧格式的特殊情感事件（在重大事件级别或有chapter_range）
迁移到新格式（附着在中型事件上，只指定target_chapter）

使用方法:
    python tools/migrate_special_emotional_events.py <项目名称>

示例:
    python tools/migrate_special_emotional_events.py "吞噬万界：从一把生锈铁剑开始"
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger

logger = get_logger("SpecialEventsMigration")


class SpecialEmotionalEventsMigrator:
    """特殊情感事件数据迁移器"""
    
    def __init__(self, project_title: str):
        self.project_title = project_title
        self.safe_title = self._sanitize_title(project_title)
        self.project_dir = Path("小说项目") / self.project_title
        
        if not self.project_dir.exists():
            self.project_dir = Path("小说项目") / self.safe_title
        
        logger.info(f"初始化迁移器: 项目={project_title}")
        logger.info(f"项目目录: {self.project_dir}")
    
    def _sanitize_title(self, title: str) -> str:
        """清理标题中的特殊字符"""
        import re
        return re.sub(r'[\\/*?"<>|]', "_", title)
    
    def find_stage_plan_files(self) -> List[Path]:
        """查找所有阶段计划文件"""
        plans_dir = self.project_dir / "plans"
        
        if not plans_dir.exists():
            logger.error(f"plans目录不存在: {plans_dir}")
            return []
        
        stage_files = list(plans_dir.glob("*_writing_plan.json"))
        logger.info(f"找到 {len(stage_files)} 个阶段计划文件")
        
        return sorted(stage_files)
    
    def migrate_stage_file(self, stage_file: Path) -> bool:
        """迁移单个阶段文件"""
        logger.info(f"\n处理文件: {stage_file.name}")
        
        try:
            with open(stage_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取stage_writing_plan
            stage_writing_plan = data.get('stage_writing_plan', {})
            if not stage_writing_plan:
                logger.info(f"  ⚠️ 文件中没有stage_writing_plan，跳过")
                return False
            
            event_system = stage_writing_plan.get('event_system', {})
            if not event_system:
                logger.info(f"  ⚠️ event_system为空，跳过")
                return False
            
            # 检查是否有旧格式的特殊情感事件
            old_special_events = event_system.get('special_emotional_events', [])
            if not old_special_events:
                logger.info(f"  ✅ 没有旧格式的特殊情感事件，无需迁移")
                return False
            
            logger.info(f"  📋 发现 {len(old_special_events)} 个旧格式特殊情感事件")
            
            # 获取重大事件
            major_events = event_system.get('major_events', [])
            if not major_events:
                logger.info(f"  ⚠️ 没有重大事件，无法迁移")
                return False
            
            # 执行迁移
            migration_count = self._migrate_special_events(
                old_special_events, 
                major_events, 
                stage_writing_plan.get('chapter_range', '')
            )
            
            if migration_count > 0:
                # 保存修改后的数据
                with open(stage_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"  ✅ 迁移完成: {migration_count} 个特殊情感事件")
                return True
            else:
                logger.info(f"  ⚠️ 没有需要迁移的特殊情感事件")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ 迁移文件失败: {e}")
            return False
    
    def _migrate_special_events(self, old_special_events: List[Dict], 
                               major_events: List[Dict],
                               stage_range: str) -> int:
        """
        迁移特殊情感事件
        
        策略：
        1. 对于有chapter_range的特殊事件，尝试找到对应的中型事件
        2. 如果有target_chapter，直接使用
        3. 否则根据chapter_range的中间章节计算target_chapter
        4. 将特殊事件附加到对应的中型事件上
        """
        migrated_count = 0
        
        for se in old_special_events:
            logger.info(f"\n  处理特殊事件: {se.get('name', '未命名')}")
            
            # 检查是否已经是新格式（有target_chapter）
            if 'target_chapter' in se:
                logger.info(f"    ✅ 已经是新格式，跳过")
                continue
            
            # 确定目标章节
            target_chapter = None
            
            if 'target_chapter' in se:
                # 新格式，直接使用
                target_chapter = se['target_chapter']
            elif 'chapter_range' in se:
                # 旧格式，取中间章节
                chapter_range = se['chapter_range']
                try:
                    from src.managers.StagePlanUtils import parse_chapter_range
                    start, end = parse_chapter_range(chapter_range)
                    target_chapter = (start + end) // 2
                    logger.info(f"    📍 从chapter_range计算: {chapter_range} -> 第{target_chapter}章")
                except:
                    logger.info(f"    ⚠️ 无法解析chapter_range: {chapter_range}")
                    continue
            elif 'chapter' in se:
                # 旧格式，直接使用
                target_chapter = se['chapter']
            else:
                logger.info(f"    ⚠️ 无法确定目标章节，跳过")
                continue
            
            # 查找对应的中型事件
            found_medium_event = self._find_medium_event_for_chapter(
                major_events, target_chapter, se
            )
            
            if found_medium_event:
                # 附加到中型事件
                if 'special_emotional_events' not in found_medium_event:
                    found_medium_event['special_emotional_events'] = []
                
                # 转换为新格式
                new_se = self._convert_to_new_format(se, target_chapter)
                found_medium_event['special_emotional_events'].append(new_se)
                
                logger.info(f"    ✅ 已附加到中型事件: {found_medium_event.get('name')}")
                migrated_count += 1
            else:
                logger.info(f"    ⚠️ 未找到对应的中型事件，跳过")
        
        return migrated_count
    
    def _find_medium_event_for_chapter(self, major_events: List[Dict], 
                                       target_chapter: int,
                                       special_event: Dict) -> Dict:
        """
        查找包含目标章节的中型事件
        
        优先级：
        1. 查找chapter_range包含目标章节的中型事件
        2. 如果有多个，选择最接近中间的
        """
        candidates = []
        
        for major_event in major_events:
            composition = major_event.get('composition', {})
            if not composition:
                continue
            
            for phase_name, phase_events in composition.items():
                if not isinstance(phase_events, list):
                    continue
                
                for medium_event in phase_events:
                    chapter_range = medium_event.get('chapter_range', '')
                    if not chapter_range:
                        continue
                    
                    try:
                        from src.managers.StagePlanUtils import parse_chapter_range
                        start, end = parse_chapter_range(chapter_range)
                        
                        if start <= target_chapter <= end:
                            # 计算距离中间章节的距离
                            midpoint = (start + end) / 2
                            distance = abs(target_chapter - midpoint)
                            
                            candidates.append({
                                'event': medium_event,
                                'distance': distance
                            })
                    except:
                        continue
        
        if candidates:
            # 按距离排序，选择最接近中间的
            candidates.sort(key=lambda x: x['distance'])
            return candidates[0]['event']
        
        return None
    
    def _convert_to_new_format(self, old_event: Dict, target_chapter: int) -> Dict:
        """将旧格式转换为新格式"""
        return {
            'name': old_event.get('name', old_event.get('event_subtype', '特殊事件')),
            'target_chapter': target_chapter,
            'purpose': old_event.get('purpose', old_event.get('significance', '')),
            'emotional_tone': old_event.get('emotional_tone', '温馨'),
            'key_elements': old_event.get('key_elements', []),
            'context_hint': old_event.get('context_hint', old_event.get('placement_hint', ''))
        }
    
    def migrate_project(self) -> bool:
        """迁移整个项目"""
        logger.info(f"\n{'='*60}")
        logger.info(f"开始迁移项目: {self.project_title}")
        logger.info(f"{'='*60}\n")
        
        stage_files = self.find_stage_plan_files()
        
        if not stage_files:
            logger.error("没有找到任何阶段计划文件，迁移终止")
            return False
        
        success_count = 0
        for stage_file in stage_files:
            if self.migrate_stage_file(stage_file):
                success_count += 1
        
        logger.info(f"\n{'='*60}")
        logger.info(f"迁移完成!")
        logger.info(f"  成功迁移: {success_count}/{len(stage_files)} 个阶段文件")
        logger.info(f"{'='*60}\n")
        
        return success_count > 0


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  python tools/migrate_special_emotional_events.py <项目名称>")
        print("\n示例:")
        print("  python tools/migrate_special_emotional_events.py \"吞噬万界：从一把生锈铁剑开始\"")
        print("\n可用的项目列表:")
        
        # 列出可用的项目
        projects_dir = Path("小说项目")
        if projects_dir.exists():
            projects = [d for d in projects_dir.iterdir() if d.is_dir()]
            for i, project in enumerate(projects, 1):
                print(f"  {i}. {project.name}")
        
        sys.exit(1)
    
    project_title = sys.argv[1]
    
    migrator = SpecialEmotionalEventsMigrator(project_title)
    success = migrator.migrate_project()
    
    if success:
        print("\n✅ 迁移成功!")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败或无需迁移")
        sys.exit(1)


if __name__ == '__main__':
    main()