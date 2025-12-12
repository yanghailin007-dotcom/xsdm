#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量更新路径管理使用脚本
更新所有核心文件以使用新的统一路径管理系统
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Set

class PathManagementUpdater:
    """路径管理使用更新器"""
    
    def __init__(self):
        self.updated_files = []
        self.error_files = []
        self.src_dir = Path("src")
        
        # 需要更新的文件模式
        self.update_patterns = [
            # 需要添加path_manager导入的文件
            {
                "pattern": r"from src\.utils\.path_manager import path_manager",
                "files_to_check": [
                    "src/core/NovelGenerator.py",
                    "src/managers/EventManager.py",
                    "src/managers/ForeshadowingManager.py",
                    "src/managers/RomancePatternManager.py",
                    "src/managers/WritingGuidanceManager.py"
                ]
            },
            # 需要更新保存方法的文件
            {
                "pattern": r"self\.project_manager\.save_",
                "replacement": "self.path_manager.save_",
                "files_to_check": [
                    "src/managers/ElementTimingPlanner.py",
                    "src/core/NovelGenerator.py"
                ]
            },
            # 需要更新加载方法的文件
            {
                "pattern": r"self\.project_manager\.load_",
                "replacement": "self.path_manager.load_",
                "files_to_check": [
                    "src/managers/ElementTimingPlanner.py",
                    "src/core/NovelGenerator.py"
                ]
            },
            # 需要添加path_manager初始化的文件
            {
                "pattern": r"self\.project_manager = manager",
                "add_after": [
                    "from src.utils.path_manager import path_manager",
                    "self.path_manager = path_manager"
                ],
                "files_to_check": [
                    "src/managers/ElementTimingPlanner.py"
                ]
            }
        ]
    
    def find_files_to_update(self) -> Dict[str, List[str]]:
        """查找需要更新的文件"""
        files_to_update = {}
        
        for pattern_config in self.update_patterns:
            files_to_update[pattern_config["pattern"]] = []
            
            # 检查指定的文件
            for file_path in pattern_config["files_to_check"]:
                full_path = self.src_dir / file_path
                if full_path.exists():
                    files_to_update[pattern_config["pattern"]].append(file_path)
                    print(f"✓ 找到文件: {file_path}")
                else:
                    print(f"⚠️ 文件不存在: {file_path}")
        
        return files_to_update
    
    def update_file(self, file_path: str, pattern_config: Dict) -> bool:
        """更新单个文件"""
        try:
            full_path = self.src_dir / file_path
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modified = False
            
            # 应用替换模式
            if "replacement" in pattern_config:
                pattern = pattern_config["pattern"]
                replacement = pattern_config["replacement"]
                
                if re.search(pattern, content):
                    content = re.sub(pattern, replacement, content)
                    modified = True
                    print(f"  🔄 替换: {pattern} -> {replacement}")
            
            # 添加导入
            if "add_after" in pattern_config:
                # 查找导入部分
                import_lines = pattern_config["add_after"]
                
                # 检查是否已经存在这些导入
                existing_imports = []
                for import_line in import_lines:
                    if import_line in content:
                        existing_imports.append(import_line)
                
                for import_line in import_lines:
                    if import_line not in existing_imports:
                        # 在文件开头的导入部分添加
                        lines = content.split('\n')
                        
                        # 找到最后一个import语句
                        last_import_idx = -1
                        for i, line in enumerate(lines):
                            if line.strip().startswith('from ') or line.strip().startswith('import '):
                                last_import_idx = i
                        
                        if last_import_idx >= 0:
                            lines.insert(last_import_idx + 1, import_line)
                            content = '\n'.join(lines)
                            modified = True
                            print(f"  ➕ 添加导入: {import_line}")
                        else:
                            # 如果没有import语句，在文件开头添加
                            content = import_line + '\n' + content
                            modified = True
                            print(f"  ➕ 添加导入到开头: {import_line}")
            
            # 保存修改后的文件
            if modified:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                print(f"✅ 已更新: {file_path}")
                self.updated_files.append(file_path)
                return True
            else:
                print(f"  ⚪️ 无需更新: {file_path}")
                return True
                
        except Exception as e:
            print(f"❌ 更新文件失败 {file_path}: {e}")
            self.error_files.append(file_path)
            return False
    
    def update_all_files(self):
        """更新所有文件"""
        print("🔍 查找需要更新的文件...")
        files_to_update = self.find_files_to_update()
        
        if not files_to_update:
            print("✅ 没有找到需要更新的文件")
            return
        
        print(f"\n📝 找到 {sum(len(files) for files in files_to_update.values())} 个文件需要更新")
        
        print("\n🔄 开始更新文件...")
        for pattern, files in files_to_update.items():
            print(f"\n📋 处理模式: {pattern}")
            
            for file_path in files:
                success = self.update_file(file_path, {
                    "pattern": pattern,
                    "replacement": pattern_config.get("replacement", ""),
                    "add_after": pattern_config.get("add_after", [])
                })
                
                if not success:
                    print(f"  ❌ 更新失败: {file_path}")
        
        # 生成更新报告
        self.generate_update_report()
    
    def generate_update_report(self):
        """生成更新报告"""
        print("\n" + "="*60)
        print("📊 路径管理使用更新报告")
        print("="*60)
        
        print(f"✅ 成功更新文件数: {len(self.updated_files)}")
        print(f"❌ 更新失败文件数: {len(self.error_files)}")
        
        if self.updated_files:
            print("\n📋 已更新的文件:")
            for file_path in self.updated_files:
                print(f"  ✅ {file_path}")
        
        if self.error_files:
            print("\n❌ 更新失败的文件:")
            for file_path in self.error_files:
                print(f"  ❌ {file_path}")
        
        # 保存报告到文件
        report_data = {
            "update_time": "2025-12-12",
            "updated_files": self.updated_files,
            "error_files": self.error_files,
            "total_updated": len(self.updated_files),
            "total_errors": len(self.error_files)
        }
        
        import json
        report_file = "path_management_update_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n📄 更新报告已保存: {report_file}")
        
        return len(self.error_files) == 0
    
    def verify_updates(self):
        """验证更新结果"""
        print("\n🔍 验证更新结果...")
        
        verification_results = {}
        
        # 检查关键文件是否包含新的导入
        key_files = [
            "src/managers/StagePlanManager.py",
            "src/managers/ElementTimingPlanner.py",
            "src/core/NovelGenerator.py"
        ]
        
        for file_path in key_files:
            full_path = self.src_dir / file_path
            if full_path.exists():
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 检查是否有path_manager相关代码
                has_path_manager_import = "path_manager" in content
                has_path_manager_usage = re.search(r"path_manager\.", content)
                
                verification_results[file_path] = {
                    "exists": True,
                    "has_import": has_path_manager_import,
                    "has_usage": has_path_manager_usage is not None,
                    "verified": has_path_manager_import and has_path_manager_usage
                }
                
                status = "✅" if verification_results[file_path]["verified"] else "❌"
                print(f"  {status} {file_path}: 导入={has_path_manager_import}, 使用={has_path_manager_usage is not None}")
            else:
                verification_results[file_path] = {
                    "exists": False,
                    "verified": False
                }
                print(f"  ❌ {file_path}: 文件不存在")
        
        # 保存验证结果
        import json
        verification_file = "path_management_verification_report.json"
        with open(verification_file, 'w', encoding='utf-8') as f:
            json.dump(verification_results, f, ensure_ascii=False, indent=2)
        
        verified_count = sum(1 for result in verification_results.values() if result["verified"])
        total_count = len(verification_results)
        
        print(f"\n📊 验证结果:")
        print(f"✅ 验证通过: {verified_count}/{total_count}")
        print(f"📄 验证报告已保存: {verification_file}")
        
        return verified_count == total_count


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="批量更新路径管理使用")
    parser.add_argument("--verify", action="store_true", help="只验证更新结果，不执行更新")
    parser.add_argument("--pattern", type=str, help="只更新匹配特定模式的文件")
    
    args = parser.parse_args()
    
    updater = PathManagementUpdater()
    
    if args.verify:
        print("🔍 验证模式：只检查更新结果")
        updater.verify_updates()
    else:
        print("🔄 更新模式：更新所有相关文件")
        success = updater.update_all_files()
        
        if success:
            print("\n[SUCCESS] 所有文件更新完成！")
            print("\n[INFO] 现在运行验证检查...")
            updater.verify_updates()
        else:
            print("\n[WARNING] 部分文件更新失败，请检查错误日志")
            print("\n[INFO] 建议：手动检查失败文件并进行修复")


if __name__ == "__main__":
    main()