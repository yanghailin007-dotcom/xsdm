#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理遗留文件脚本
清理仍在旧路径下的文件，确保所有内容都已迁移到新的统一结构
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime

from src.config.path_config import path_config
from src.utils.path_manager import path_manager


class LegacyFileCleaner:
    """遗留文件清理器"""
    
    def __init__(self):
        self.cleaned_files = []
        self.error_files = []
        self.base_dir = Path("小说项目")
        self.quality_data_dir = Path("quality_data")
        
    def scan_legacy_files(self) -> Dict[str, List[str]]:
        """扫描所有遗留文件"""
        legacy_files = {
            "project_info": [],
            "chapters": [],
            "overviews": [],
            "style_guides": [],
            "timing_plans": [],
            "element_introductions": [],
            "root_files": []
        }
        
        # 扫描小说项目目录下的旧格式文件
        if self.base_dir.exists():
            for item in self.base_dir.iterdir():
                if item.is_file():
                    filename = item.name
                    if filename.endswith("_项目信息.json"):
                        legacy_files["project_info"].append(str(item))
                    elif filename.endswith("_章节总览.json"):
                        legacy_files["overviews"].append(str(item)))
                    elif filename.endswith("_写作风格指南.json"):
                        legacy_files["style_guides"].append(str(item)))
                    elif filename.endswith("_元素登场时机.json"):
                        legacy_files["timing_plans"].append(str(item)))
                    elif filename.endswith("_元素引入计划.json"):
                        legacy_files["element_introductions"].append(str(item)))
                    elif filename.endswith("_Refined_AI_Brief.txt"):
                        legacy_files["root_files"].append(str(item)))
        
        # 扫扫描章节目录
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.endswith("_章节"):
                legacy_files["chapters"].append(str(item)))
        
        # 扫描quality_data目录
        if self.quality_data_dir.exists():
            for pattern in ["*.json"]:
                for file_path in self.quality_data_dir.glob(pattern):
                    if "凡人" in file_path.name or "写作计划" in file_path.name or "元素" in file_path.name:
                        legacy_files["root_files"].append(str(file_path))
        
        # 扫描根目录的特殊文件
        for pattern in ["*_写作风格指南.json", "*_元素*.json"]:
            for file_path in Path(".").glob(pattern):
                if file_path.is_file():
                    legacy_files["root_files"].append(str(file_path))
        
        return legacy_files
    
    def get_safe_novel_title(self, file_path: str) -> Optional[str]:
        """从文件路径中提取小说标题"""
        filename = Path(file_path).stem
        
        # 尝试不同的模式
        patterns = [
            r"(.+)_项目信息\.json$",
            r"(.+)_章节总览\.json$",
            r"(.+)_写作风格指南\.json$",
            r"(.+)_元素.*\.json$"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    def clean_file(self, file_path: str, novel_title: str = None) -> bool:
        """清理单个文件"""
        try:
            full_path = Path(file_path)
            
            # 获取文件信息
            if not full_path.exists():
                self.logger.info(f"  ⚠️ 文件不存在: {file_path}")
                return False
            
            # 如果是目录，递归删除
            if full_path.is_dir():
                shutil.rmtree(full_path)
                self.logger.info(f"  🗑️ 删除目录: {file_path}")
                self.cleaned_files.append(file_path)
                return True
            
            # 获取文件大小
            file_size = full_path.stat().st_size
            if file_size == 0:
                # 空文件，直接删除
                full_path.unlink()
                self.logger.info(f"  🗑️ 删除空文件: {file_path}")
                self.cleaned_files.append(file_path)
                return True
            
            # 对于非空文件，先备份再删除
            backup_path = full_path.with_suffix(".bak")
            shutil.move(str(full_path), str(backup_path))
            
            # 删除原文件
            full_path.unlink()
            
            self.logger.info(f"  ✅ 已备份并删除: {file_path} -> {backup_path}")
            self.cleaned_files.append(file_path)
            return True
            
        except Exception as e:
            self.logger.error(f"  ❌ 清理文件失败: {file_path} - {e}")
            self.error_files.append(file_path)
            return False
    
    def migrate_file_to_new_structure(self, file_path: str) -> bool:
        """将文件迁移到新的统一结构"""
        try:
            full_path = Path(file_path)
            
            # 从文件路径提取小说标题
            novel_title = self.get_safe_novel_title(file_path)
            if not novel_title:
                self.logger.info(f"  ⚠️ 无法从路径提取小说标题: {file_path}")
                return False
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 确定文件类型并保存到新位置
            if "写作风格指南" in file_path or "writing_style" in file_path:
                # 使用路径管理器保存
                success = path_manager.save_writing_style_guide(novel_title, content)
                if success:
                    os.remove(full_path)
                    self.logger.info(f"  ✅ 迁移写作风格指南: {file_path}")
                    self.cleaned_files.append(file_path)
                    return True
            
            elif "项目信息" in file_path:
                # 使用路径管理器保存
                try:
                    data = json.load(full_path)
                    success = path_manager.save_project_info(novel_title, data)
                    if success:
                        os.remove(full_path)
                        self.logger.info(f"  ✅ 迁移项目信息: {file_path}")
                        self.cleaned_files.append(file_path)
                        return True
                except Exception as e:
                    self.logger.error(f"  ❌ 迁移项目信息失败: {e}")
            
            elif "章节总览" in file_path:
                # 使用路径管理器保存
                try:
                    data = json.load(full_path)
                    success = path_manager.save_novel_overview(novel_title, data)
                    if success:
                        os.remove(full_path)
                        self.logger.info(f"  ✅ 迁移章节总览: {file_path}")
                        self.cleaned_files.append(file_path)
                        return True
                except Exception as e:
                    self.logger.error(f"  ❌ 迁移章节总览失败: {e}")
            
            else:
                # 对于其他文件，尝试识别类型并迁移
                try:
                    data = json.load(full_path)
                    file_type = self._identify_file_type(file_path, data)
                    
                    if file_type:
                        success = path_manager.save_material_data(novel_title, file_type, data)
                        if success:
                            os.remove(full_path)
                            self.logger.info(f"  ✅ 迁移材料文件: {file_path} -> {file_type}")
                            self.cleaned_files.append(file_path)
                            return True
                except Exception as e:
                    self.logger.warning(f"  ⚠️ 未知文件类型，保留文件: {file_path}")
            
            return False
            
        except Exception as e:
            self.logger.error(f"  ❌ 迁移文件失败: {file_path} - {e}")
            return False
    
    def _identify_file_type(self, file_path: str, data: Dict) -> Optional[str]:
        """识别文件类型"""
        filename = Path(file_path).stem.lower()
        
        # 根据内容和文件名识别类型
        if "世界观" in filename or "worldview" in filename:
            return "worldview"
        elif "角色" in filename or "character" in filename:
            return "characters"
        elif "市场" in filename or "market" in filename:
            return "market_analysis"
        elif "写作风格" in filename or "style" in filename:
            return "writing_style_guide"
        elif "项目信息" in filename or "project_info" in filename:
            return "project_info"
        elif "总览" in filename or "overview" in filename:
            return "novel_overview"
        elif "元素" in filename and ("时机" in filename or "timing" in filename or "introduction" in filename):
            return "element_timing"
        
        return None
    
    def generate_cleanup_report(self) -> Dict:
        """生成清理报告"""
        report = {
            "cleanup_time": datetime.now().isoformat(),
            "total_cleaned_files": len(self.cleaned_files),
            "total_error_files": len(self.error_files),
            "cleaned_files": self.cleaned_files,
            "error_files": self.error_files,
            "recommendations": []
        }
        
        # 添加建议
        if self.error_files:
            report["recommendations"].append("手动检查失败的文件并进行修复")
        
        if not self.cleaned_files and not self.error_files:
            report["recommendations"].append("没有发现需要清理的遗留文件")
        elif self.cleaned_files:
            report["recommendations"].append("建议检查新目录结构确保文件已正确迁移")
        
        return report
    
    def cleanup_all_legacy_files(self, dry_run: bool = False) -> Dict:
        """清理所有遗留文件"""
        print("🔍 开始扫描遗留文件...")
        
        if dry_run:
            print("[DRY RUN] 只扫描，不执行删除操作")
        
        # 扫描所有遗留文件
        legacy_files = self.scan_legacy_files()
        total_files = sum(len(files) for files in legacy_files.values())
        
        if total_files == 0:
            print("✅ 没有发现需要清理的遗留文件")
            return self.generate_cleanup_report()
        
        print(f"\n📊 发现 {total_files} 个遗留文件需要处理")
        
        for category, files in legacy_files.items():
            print(f"\n📂 处理类别: {category} ({len(files)} 个文件)")
            
            for file_path in files:
                print(f"  📁 {file_path}")
                
                if not dry_run:
                    success = self.clean_file(file_path)
                    if success:
                        print(f"    ✅ 已清理: {file_path}")
                    else:
                        print(f"    ❌ 清理失败: {file_path}")
        
        # 生成报告
        report = self.generate_cleanup_report()
        
        print(f"\n" + "="*60)
        print("📊 遗留文件清理报告")
        print("="*60)
        
        print(f"✅ 成功清理: {len(self.cleaned_files)} 个文件")
        print(f"❌ 清理失败: {len(self.error_files)} 个文件")
        
        if report["recommendations"]:
            print(f"\n💡 建议:")
            for rec in report["recommendations"]:
                print(f"  - {rec}")
        
        # 保存报告
        import json
        report_file = f"legacy_files_cleanup_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 清理报告已保存: {report_file}")
        
        return report


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="清理遗留文件脚本")
    parser.add_argument("--dry-run", action="store_true", help="试运行模式，不实际删除文件")
    parser.add_argument("--category", type=str, help="只清理指定类别的文件")
    
    args = parser.parse_args()
    
    cleaner = LegacyFileCleaner()
    
    if args.category:
        # 只清理指定类别
        legacy_files = cleaner.scan_legacy_files()
        if args.category in legacy_files:
            print(f"\n🎯 只清理类别: {args.category}")
            
            for file_path in legacy_files[args.category]:
                print(f"  📁 {file_path}")
                
                if not args.dry_run:
                    success = cleaner.clean_file(file_path)
                    if success:
                        print(f"    ✅ 已清理: {file_path}")
                    else:
                        print(f"    ❌ 清理失败: {file_path}")
        else:
            print(f"❌ 未找到类别 '{args.category}' 的文件")
    else:
        # 清理所有遗留文件
        success = cleaner.cleanup_all_legacy_files(args.dry_run)
        
        if not args.dry_run:
            print("\n🎉 遗留文件清理完成！")
        else:
            print("\n🔍 试运行完成，未执行实际删除操作")


if __name__ == "__main__":
    main()