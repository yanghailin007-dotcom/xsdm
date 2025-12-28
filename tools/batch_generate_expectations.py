"""
批量为所有现有小说生成期待感标签

用法：
python tools/batch_generate_expectations.py
"""

import sys
import json
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator


class BatchExpectationGenerator:
    """批量生成期待感标签"""
    
    def __init__(self):
        self.logger = self._get_logger()
        self.project_base = Path("小说项目")
    
    def _get_logger(self):
        """获取日志记录器"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def scan_projects(self):
        """扫描所有项目目录"""
        if not self.project_base.exists():
            self.logger.error(f"项目目录不存在: {self.project_base}")
            return []
        
        projects = []
        for item in self.project_base.iterdir():
            if item.is_dir():
                # 检查是否包含写作计划
                has_writing_plan = False
                
                # 检查 plans 目录
                plans_dir = item / "plans"
                if plans_dir.exists():
                    plan_files = list(plans_dir.glob("*_writing_plan.json"))
                    if plan_files:
                        has_writing_plan = True
                
                # 检查 planning 目录
                if not has_writing_plan:
                    planning_dir = item / "planning"
                    if planning_dir.exists():
                        plan_files = list(planning_dir.glob("*writing_plan*.json"))
                        if plan_files:
                            has_writing_plan = True
                
                if has_writing_plan:
                    projects.append(item.name)
        
        return projects
    
    def generate_for_project(self, project_name):
        """为单个项目生成期待感标签"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"处理项目: {project_name}")
        self.logger.info(f"{'='*60}")
        
        project_dir = self.project_base / project_name
        
        # 检查是否已有期待感映射
        expectation_file = project_dir / "expectation_map.json"
        if expectation_file.exists():
            self.logger.info(f"  ✓ 项目已有期待感映射文件，跳过")
            return False
        
        # 加载写作计划
        plans_dir = project_dir / "plans"
        if not plans_dir.exists():
            plans_dir = project_dir / "planning"
        
        if not plans_dir.exists():
            self.logger.warning(f"  ⚠️ 未找到写作计划目录")
            return False
        
        # 查找所有写作计划文件
        plan_files = list(plans_dir.glob("*_writing_plan.json"))
        if not plan_files:
            self.logger.warning(f"  ⚠️ 未找到写作计划文件")
            return False
        
        self.logger.info(f"  ✓ 找到 {len(plan_files)} 个写作计划文件")
        
        # 合并所有阶段的计划
        merged_plan = {
            'stage_names': [],
            'stages': {}
        }
        
        for plan_file in sorted(plan_files):
            try:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)
                
                # 从文件名提取阶段名称
                stage_name = plan_file.stem.replace('_writing_plan', '')
                
                # 存储阶段数据
                merged_plan['stage_names'].append(stage_name)
                merged_plan['stages'][stage_name] = plan_data
                
                self.logger.info(f"    - 加载阶段: {stage_name}")
                
            except Exception as e:
                self.logger.error(f"    ✗ 加载 {plan_file} 失败: {e}")
        
        # 生成期待感标签
        self.logger.info(f"\n  🎯 开始生成期待感标签...")
        
        manager = ExpectationManager()
        integrator = ExpectationIntegrator(manager)
        
        total_tagged = 0
        for stage_name in merged_plan['stage_names']:
            stage_data = merged_plan['stages'][stage_name]
            stage_plan = stage_data.get('stage_writing_plan', {})
            major_events = stage_plan.get('event_system', {}).get('major_events', [])
            
            if not major_events:
                continue
            
            self.logger.info(f"\n  处理阶段: {stage_name} ({len(major_events)} 个重大事件)")
            
            # 为每个重大事件添加期待感标签
            for event in major_events:
                event_name = event.get('name', '未命名事件')
                
                # 自动选择期待类型
                exp_type = self._select_expectation_type(event)
                
                # 计算种植和目标章节
                chapter_range = event.get('chapter_range', '1-10')
                try:
                    from src.managers.StagePlanUtils import parse_chapter_range
                    start_ch, end_ch = parse_chapter_range(chapter_range)
                    target_ch = max(start_ch + 3, end_ch)
                except:
                    target_ch = end_ch
                
                # 种植期待
                exp_id = manager.tag_event_with_expectation(
                    event_id=event_name,
                    expectation_type=exp_type,
                    planting_chapter=start_ch,
                    description=f"{event_name}: {event.get('main_goal', '')[:80]}...",
                    target_chapter=target_ch
                )
                
                total_tagged += 1
        
        if total_tagged == 0:
            self.logger.warning(f"  ⚠️ 未找到任何重大事件")
            return False
        
        self.logger.info(f"\n  ✓ 共为 {total_tagged} 个事件添加了期待标签")
        
        # 保存期待感映射
        expectation_map = manager.export_expectation_map()
        
        try:
            with open(expectation_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': project_name,
                    'generated_at': __import__('datetime').datetime.now().isoformat(),
                    'expectation_map': expectation_map
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"  ✓ 期待感映射已保存: {expectation_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"  ✗ 保存期待感映射失败: {e}")
            return False
    
    def _select_expectation_type(self, event):
        """根据事件特征自动选择期待感类型"""
        from src.managers.ExpectationManager import ExpectationType
        
        main_goal = event.get('main_goal', '').lower()
        emotional_focus = event.get('emotional_focus', '').lower()
        name = event.get('name', '').lower()
        
        # 决策树：根据事件特征选择期待类型
        if '击败' in main_goal or '战胜' in main_goal or '复仇' in main_goal:
            return ExpectationType.SUPPRESSION_RELEASE
        elif '获得' in main_goal or '得到' in main_goal or '炼成' in main_goal or '夺取' in main_goal:
            return ExpectationType.SHOWCASE
        elif '揭秘' in main_goal or '真相' in main_goal or '发现' in name:
            return ExpectationType.MYSTERY_FORESHADOW
        elif '误解' in emotional_focus or '轻视' in emotional_focus or '震惊' in main_goal or '打脸' in name:
            return ExpectationType.EMOTIONAL_HOOK
        elif '展示' in main_goal or '学习' in main_goal or '修炼' in main_goal:
            return ExpectationType.POWER_GAP
        else:
            # 默认使用套娃式期待
            return ExpectationType.NESTED_DOLL
    
    def generate_all(self):
        """为所有项目生成期待感标签"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"开始批量生成期待感标签")
        self.logger.info(f"{'='*80}\n")
        
        # 扫描所有项目
        projects = self.scan_projects()
        
        if not projects:
            self.logger.warning(f"未找到任何项目")
            return
        
        self.logger.info(f"找到 {len(projects)} 个项目\n")
        
        # 为每个项目生成期待感标签
        success_count = 0
        skip_count = 0
        fail_count = 0
        
        for project_name in projects:
            result = self.generate_for_project(project_name)
            
            if result is True:
                success_count += 1
            elif result is False:
                fail_count += 1
            else:
                skip_count += 1
        
        # 打印总结
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"批量生成完成")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"成功: {success_count} 个项目")
        self.logger.info(f"跳过: {skip_count} 个项目（已有期待感数据）")
        self.logger.info(f"失败: {fail_count} 个项目")
        self.logger.info(f"{'='*80}\n")
        
        if success_count > 0:
            self.logger.info(f"✅ 期待感标签生成完成！")
            self.logger.info(f"\n下一步:")
            self.logger.info(f"1. 刷新故事线页面")
            self.logger.info(f"2. 点击事件查看详细的期待感信息")
            self.logger.info(f"3. 期待感数据已保存在项目目录的 expectation_map.json 文件中")


def main():
    """主函数"""
    generator = BatchExpectationGenerator()
    generator.generate_all()


if __name__ == "__main__":
    main()