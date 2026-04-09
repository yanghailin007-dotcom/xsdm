# -*- coding: utf-8 -*-
"""
文风系统自检脚本
检查文件、API路由、数据结构是否正确配置
"""

import os
import sys
import json
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

class WritingStyleSelfCheck:
    """文风系统自检类"""
    
    def __init__(self):
        self.checks = []
        self.errors = []
        self.warnings = []
        
    def log(self, message, level="info"):
        """记录日志"""
        if level == "error":
            self.errors.append(message)
            print(f"[ERROR] {message}".encode('utf-8').decode('utf-8'))
        elif level == "warning":
            self.warnings.append(message)
            print(f"[WARN] {message}".encode('utf-8').decode('utf-8'))
        else:
            self.checks.append(message)
            print(f"✅ {message}")
    
    def check_file_structure(self):
        """检查文件结构"""
        print("\n" + "="*60)
        print("检查文件结构")
        print("="*60)
        
        files_to_check = [
            ("web/models/writing_style_model.py", "文风数据模型"),
            ("web/api/writing_style_api.py", "文风API接口"),
            ("web/routes/writing_style_routes.py", "文风页面路由"),
            ("web/templates/components/writing-style-selector.html", "文风选择弹窗组件"),
            ("web/templates/pages/v2/writing-style-library.html", "文风训练库页面"),
        ]
        
        for file_path, desc in files_to_check:
            full_path = project_root / file_path
            if full_path.exists():
                self.log(f"{desc}: {file_path}")
            else:
                self.log(f"{desc} 文件不存在: {file_path}", "error")
    
    def check_data_directory(self):
        """检查数据目录"""
        print("\n" + "="*60)
        print("检查数据目录")
        print("="*60)
        
        data_dir = project_root / "data" / "writing_styles"
        preset_dir = data_dir / "presets"
        user_dir = data_dir / "user_styles"
        
        if data_dir.exists():
            self.log(f"数据目录存在: {data_dir}")
        else:
            self.log(f"数据目录不存在，将自动创建", "warning")
        
        # 检查预设文风
        if preset_dir.exists():
            preset_files = list(preset_dir.glob("*.json"))
            self.log(f"预设文风目录存在，包含 {len(preset_files)} 个文风文件")
            
            # 检查是否有番茄文风
            fanqie_file = preset_dir / "fanqie_light_fast_v1.json"
            if fanqie_file.exists():
                self.log("番茄轻快节奏风预设已创建")
                
                # 验证文件内容
                try:
                    with open(fanqie_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "dna" in data and "system_prompt_addon" in data:
                            self.log("番茄文风配置文件完整")
                        else:
                            self.log("番茄文风配置文件不完整", "warning")
                except Exception as e:
                    self.log(f"番茄文风配置文件读取失败: {e}", "error")
            else:
                self.log("番茄轻快节奏风预设未创建", "warning")
        else:
            self.log("预设文风目录不存在，将自动创建", "warning")
    
    def check_api_routes(self):
        """检查API路由"""
        print("\n" + "="*60)
        print("检查API路由")
        print("="*60)
        
        api_file = project_root / "web" / "api" / "writing_style_api.py"
        if api_file.exists():
            content = api_file.read_text(encoding='utf-8')
            
            routes = [
                ('/presets', '获取预设文风'),
                ('/user-styles', '获取用户文风'),
                ('/detail/', '获取文风详情'),
                ('/recommended', '获取推荐文风'),
                ('/extract', '提取文风'),
                ('/create', '创建文风'),
                ('/apply-to-project', '应用到项目'),
            ]
            
            for route, desc in routes:
                if route in content:
                    self.log(f"API路由存在: {route} ({desc})")
                else:
                    self.log(f"API路由不存在: {route}", "error")
    
    def check_blueprint_registration(self):
        """检查蓝图注册"""
        print("\n" + "="*60)
        print("检查蓝图注册")
        print("="*60)
        
        server_file = project_root / "web" / "web_server_refactored.py"
        if server_file.exists():
            content = server_file.read_text(encoding='utf-8')
            
            if "writing_style_api" in content:
                self.log("文风API蓝图已注册到web_server_refactored.py")
            else:
                self.log("文风API蓝图未注册到web_server_refactored.py", "error")
            
            if "writing_style_routes" in content:
                self.log("文风页面路由已注册到web_server_refactored.py")
            else:
                self.log("文风页面路由未注册到web_server_refactored.py", "error")
    
    def check_model_init(self):
        """检查模型初始化"""
        print("\n" + "="*60)
        print("检查数据模型")
        print("="*60)
        
        try:
            from web.models.writing_style_model import get_writing_style_model
            model = get_writing_style_model()
            self.log("文风数据模型可以正常初始化")
            
            # 检查预设文风
            presets = model.get_all_presets()
            self.log(f"数据模型可以正常获取预设文风，共 {len(presets)} 个")
            
            if presets:
                first_style = presets[0]
                self.log(f"第一个预设文风: {first_style.get('style_name', 'Unknown')}")
                
        except Exception as e:
            self.log(f"数据模型初始化失败: {e}", "error")
    
    def generate_report(self):
        """生成自检报告"""
        print("\n" + "="*60)
        print("自检报告")
        print("="*60)
        
        total = len(self.checks) + len(self.errors) + len(self.warnings)
        
        print(f"\n总计检查: {total} 项")
        print(f"✅ 通过: {len(self.checks)} 项")
        print(f"⚠️ 警告: {len(self.warnings)} 项")
        print(f"❌ 错误: {len(self.errors)} 项")
        
        if self.errors:
            print("\n需要修复的错误:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print("\n需要注意的警告:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        # 保存报告到文件
        report = {
            "total": total,
            "passed": len(self.checks),
            "warnings": len(self.warnings),
            "errors": len(self.errors),
            "error_details": self.errors,
            "warning_details": self.warnings,
            "passed_details": self.checks
        }
        
        report_file = project_root / "tests" / "writing_style_self_check_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n详细报告已保存到: {report_file}")
        
        return len(self.errors) == 0


def main():
    """主函数"""
    print("="*60)
    print("文风系统自检工具")
    print("="*60)
    print(f"项目路径: {project_root}")
    
    checker = WritingStyleSelfCheck()
    
    # 执行检查
    checker.check_file_structure()
    checker.check_data_directory()
    checker.check_api_routes()
    checker.check_blueprint_registration()
    checker.check_model_init()
    
    # 生成报告
    success = checker.generate_report()
    
    print("\n" + "="*60)
    if success:
        print("✅ 自检通过，文风系统配置正确！")
    else:
        print("❌ 自检发现错误，请修复后再试")
    print("="*60)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
