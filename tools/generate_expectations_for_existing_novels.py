"""
为现有小说生成期待感标签的工具脚本

用法：
python tools/generate_expectations_for_existing_novels.py --title "小说标题"
"""

import sys
import json
import os
from pathlib import Path
from typing import Dict, List

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.managers.ExpectationManager import ExpectationManager, ExpectationIntegrator, ExpectationType


class ExpectationGenerator:
    """为现有小说生成期待感标签"""
    
    def __init__(self):
        self.logger = self._get_logger()
        self.manager = ExpectationManager()
        self.integrator = ExpectationIntegrator(self.manager)
    
    def _get_logger(self):
        """获取日志记录器"""
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)
    
    def find_project_dir(self, title: str) -> Path | None:
        """查找项目目录"""
        self.logger.info(f"正在查找项目目录: {title}")
        
        # 清理标题中的特殊字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        
        # 可能的目录路径
        possible_paths = [
            Path("小说项目") / title,
            Path("小说项目") / safe_title
        ]
        
        # 额外：扫描所有子目录进行模糊匹配
        project_base = Path("小说项目")
        if project_base.exists():
            self.logger.info(f"扫描 {project_base} 目录...")
            for item in project_base.iterdir():
                if item.is_dir():
                    # 检查目录名是否包含标题的关键部分
                    dir_name = item.name.lower()
                    title_lower = title.lower().replace(':', '').replace('：', '')
                    if title_lower in dir_name or dir_name in title_lower:
                        self.logger.info(f"✓ 通过模糊匹配找到项目目录: {item}")
                        return item
        
        for path in possible_paths:
            if path.exists():
                self.logger.info(f"✓ 找到项目目录: {path}")
                return path
        
        self.logger.error(f"✗ 未找到项目目录: {title}")
        self.logger.info(f"  尝试的路径: {possible_paths}")
        return None
    
    def load_stage_plan(self, project_dir: Path) -> Dict | None:
        """加载阶段计划"""
        plans_dir = project_dir / "plans"
        if not plans_dir.exists():
            plans_dir = project_dir / "planning"
        
        # 查找所有写作计划文件
        plan_files = list(plans_dir.glob("*_writing_plan.json"))
        
        if not plan_files:
            self.logger.error(f"✗ 未找到写作计划文件")
            return {}
        
        self.logger.info(f"✓ 找到 {len(plan_files)} 个写作计划文件")
        
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
                
                self.logger.info(f"  - 加载阶段: {stage_name}")
                
            except Exception as e:
                self.logger.error(f"✗ 加载 {plan_file} 失败: {e}")
        
        return merged_plan
    
    def generate_expectations_for_stage(self, stage_name: str, stage_plan: Dict) -> int:
        """为单个阶段生成期待感标签"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"处理阶段: {stage_name}")
        self.logger.info(f"{'='*60}")
        
        stage_writing_plan = stage_plan.get('stage_writing_plan', {})
        event_system = stage_writing_plan.get('event_system', {})
        major_events = event_system.get('major_events', [])
        
        if not major_events:
            self.logger.warning(f"  ⚠️ 该阶段没有重大事件")
            return 0
        
        self.logger.info(f"  - 找到 {len(major_events)} 个重大事件")
        
        # 使用集成器自动分析和标记事件
        result = self.integrator.analyze_and_tag_events(
            major_events=major_events,
            stage_name=stage_name
        )
        
        self.logger.info(f"  ✓ 为 {result['tagged_count']} 个事件添加了期待标签")
        
        return result['tagged_count']
    
    def generate_expectations_for_novel(self, title: str) -> bool:
        """为整本小说生成期待感标签"""
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"开始为小说《{title}》生成期待感标签")
        self.logger.info(f"{'='*80}\n")
        
        # 1. 查找项目目录
        project_dir = self.find_project_dir(title)
        if not project_dir:
            return False
        
        # 2. 加载阶段计划
        stage_plan = self.load_stage_plan(project_dir)
        if not stage_plan:
            return False
        
        # 3. 为每个阶段生成期待感标签
        total_tagged = 0
        for stage_name in stage_plan['stage_names']:
            stage_data = stage_plan['stages'][stage_name]
            count = self.generate_expectations_for_stage(stage_name, stage_data)
            total_tagged += count
        
        # 4. 生成期待感报告
        self.logger.info(f"\n{'='*80}")
        self.logger.info(f"期待感生成完成")
        self.logger.info(f"{'='*80}")
        self.logger.info(f"总计: 为 {total_tagged} 个事件添加了期待标签")
        
        # 5. 生成期待感报告
        report = self.manager.generate_expectation_report()
        self.print_expectation_report(report)
        
        # 6. 保存期待感映射到文件
        expectation_map = self.manager.export_expectation_map()
        self.save_expectation_map(project_dir, expectation_map, title)
        
        self.logger.info(f"\n✅ 期待感标签已保存到项目目录")
        self.logger.info(f"   文件位置: {project_dir}/expectation_map.json")
        
        return True
    
    def print_expectation_report(self, report: Dict):
        """打印期待感报告"""
        self.logger.info(f"\n📊 期待感统计:")
        self.logger.info(f"   总期待数: {report['total_expectations']}")
        self.logger.info(f"   已释放: {report['released_expectations']}")
        self.logger.info(f"   待处理: {report['pending_expectations']}")
        self.logger.info(f"   满足率: {report['satisfaction_rate']}%")
        
        if report.get('expectation_type_stats'):
            self.logger.info(f"\n📈 期待类型分布:")
            for exp_type, stats in report['expectation_type_stats'].items():
                self.logger.info(f"   - {exp_type}: {stats['total']}个 (已释放{stats['released']}个)")
    
    def save_expectation_map(self, project_dir: Path, expectation_map: Dict, title: str):
        """保存期待感映射到文件"""
        expectation_file = project_dir / "expectation_map.json"
        
        try:
            with open(expectation_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': title,
                    'generated_at': __import__('datetime').datetime.now().isoformat(),
                    'expectation_map': expectation_map
                }, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✓ 期待感映射已保存: {expectation_file}")
            
        except Exception as e:
            self.logger.error(f"✗ 保存期待感映射失败: {e}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='为现有小说生成期待感标签')
    parser.add_argument('--title', type=str, help='小说标题（不指定则列出所有项目）')
    parser.add_argument('--list', action='store_true', help='列出所有可用项目')
    
    args = parser.parse_args()
    
    generator = ExpectationGenerator()
    
    if args.list or not args.title:
        # 列出所有项目
        generator.logger.info("正在扫描项目目录...")
        project_base = Path("小说项目")
        if project_base.exists():
            projects = []
            for item in project_base.iterdir():
                if item.is_dir():
                    projects.append(item.name)
            
            if projects:
                print(f"\n找到 {len(projects)} 个项目:")
                for i, project in enumerate(projects, 1):
                    print(f"  {i}. {project}")
                print(f"\n使用方法:")
                print(f"  python tools/generate_expectations_for_existing_novels.py --title \"项目名称\"")
                return
            else:
                generator.logger.warning("未找到任何项目目录")
                return
    
    # 生成期待感标签
    success = generator.generate_expectations_for_novel(args.title)
    
    if success:
        print(f"\n{'='*60}")
        print(f"[OK] 成功为《{args.title}》生成期待感标签！")
        print(f"{'='*60}")
        print(f"\n下一步:")
        print(f"1. 刷新故事线页面，查看期待感标签")
        print(f"2. 点击事件查看详细的期待感信息")
        print(f"3. 期待感数据已保存在项目目录的 expectation_map.json 文件中")
    else:
        print(f"\n{'='*60}")
        print(f"[ERROR] 生成失败")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()