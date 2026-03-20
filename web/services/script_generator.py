"""
上传脚本生成器服务
生成包含小说数据和配置的上传脚本包
"""
import os
import json
import zipfile
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 路径配置
BASE_DIR = Path(__file__).parent.parent.parent
TEMPLATE_PATH = BASE_DIR / 'tools' / 'upload_script_template.py'


class ScriptGenerator:
    """脚本生成器"""
    
    def __init__(self, api_base_url: str = "http://localhost:5000"):
        self.api_base_url = api_base_url
        self.template = None
        self._load_template()
    
    def _load_template(self):
        """加载脚本模板"""
        if TEMPLATE_PATH.exists():
            with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
                self.template = f.read()
        else:
            raise FileNotFoundError(f"脚本模板不存在: {TEMPLATE_PATH}")
    
    def generate_script(self, task_id: str, user_token: str, novel_info: Dict,
                       chapters: List[Dict], platform: str = 'fanqie') -> str:
        """
        生成上传脚本内容
        
        Args:
            task_id: 任务ID
            user_token: 用户认证token
            novel_info: 小说信息
            chapters: 章节列表
            platform: 上传平台
            
        Returns:
            生成的脚本内容
        """
        # 替换模板变量
        script = self.template
        
        # 基础配置
        script = script.replace('{{API_BASE_URL}}', self.api_base_url)
        script = script.replace('{{TASK_ID}}', task_id)
        script = script.replace('{{USER_TOKEN}}', user_token)
        script = script.replace('{{NOVEL_TITLE}}', novel_info.get('title', ''))
        script = script.replace('{{NOVEL_ID}}', novel_info.get('id', ''))
        script = script.replace('{{PLATFORM}}', platform)
        
        return script
    
    def create_upload_package(self, task_id: str, user_token: str, 
                             novel_info: Dict, chapters: List[Dict],
                             platform: str = 'fanqie') -> Dict:
        """
        创建上传脚本包（ZIP）
        
        Returns:
            {
                'success': bool,
                'package_path': str,  # ZIP文件路径
                'files': List[str]    # 包内文件列表
            }
        """
        try:
            # 创建临时目录
            temp_dir = Path(tempfile.mkdtemp(prefix=f'upload_{task_id}_'))
            
            # 生成脚本
            script_content = self.generate_script(
                task_id=task_id,
                user_token=user_token,
                novel_info=novel_info,
                chapters=chapters,
                platform=platform
            )
            
            # 保存脚本文件
            script_name = f"upload_{novel_info.get('title', 'novel').replace(' ', '_')}.py"
            script_path = temp_dir / script_name
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
            
            # 保存章节数据
            chapters_data = []
            for i, ch in enumerate(chapters, 1):
                chapters_data.append({
                    'number': ch.get('number', i),
                    'title': ch.get('title', f'第{i}章'),
                    'content': ch.get('content', ''),
                    'word_count': len(ch.get('content', ''))
                })
            
            chapters_path = temp_dir / 'chapters.json'
            with open(chapters_path, 'w', encoding='utf-8') as f:
                json.dump(chapters_data, f, ensure_ascii=False, indent=2)
            
            # 创建README
            readme_content = self._generate_readme(novel_info, len(chapters))
            readme_path = temp_dir / 'README.txt'
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            
            # 创建ZIP包
            zip_name = f"upload_package_{task_id}.zip"
            zip_path = temp_dir.parent / zip_name
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(script_path, script_name)
                zf.write(chapters_path, 'chapters.json')
                zf.write(readme_path, 'README.txt')
            
            # 清理临时文件
            script_path.unlink()
            chapters_path.unlink()
            readme_path.unlink()
            temp_dir.rmdir()
            
            return {
                'success': True,
                'package_path': str(zip_path),
                'files': [script_name, 'chapters.json', 'README.txt']
            }
            
        except Exception as e:
            print(f"[ScriptGenerator] 创建上传包失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def _generate_readme(self, novel_info: Dict, chapter_count: int) -> str:
        """生成README内容"""
        return f"""═══════════════════════════════════════════════════════════
  大文娱创作平台 - 本地上传脚本包
═══════════════════════════════════════════════════════════

小说信息:
  标题: {novel_info.get('title', '未知')}
  章节数: {chapter_count} 章
  生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

文件说明:
  1. upload_xxx.py - 上传脚本（双击运行）
  2. chapters.json - 章节数据
  3. README.txt - 本说明文件

使用方法:
  1. 确保已下载并解压 Chrome 启动器
  2. 运行 "一键启动.bat" 启动 Chrome
  3. 在 Chrome 中登录番茄小说作者账号
  4. 双击运行 upload_xxx.py 开始上传
  5. 在网页查看上传进度

注意事项:
  • 请勿关闭 Chrome 浏览器
  • 请勿修改 chapters.json 文件
  • 上传过程中请保持网络连接
  • 如遇上传失败，可多次重试

技术支持:
  官网: {self.api_base_url}
  文档: {self.api_base_url}/help

═══════════════════════════════════════════════════════════
"""


def generate_simple_script(novel_title: str, chapters: List[Dict], 
                          output_path: str) -> bool:
    """
    生成简单的独立上传脚本（不含上报功能）
    用于快速测试或离线使用
    """
    try:
        script_content = f'''#!/usr/bin/env python3
"""
大文娱创作平台 - 简易上传脚本
小说: {novel_title}
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

import json
import time
from pathlib import Path

# 章节数据
CHAPTERS = {json.dumps(chapters, ensure_ascii=False, indent=2)}

def main():
    print("=" * 60)
    print("大文娱创作平台 - 简易上传脚本")
    print("=" * 60)
    print(f"小说: {novel_title}")
    print(f"章节: {{len(CHAPTERS)}} 章")
    print("=" * 60)
    
    # TODO: 实现实际上传逻辑
    for i, ch in enumerate(CHAPTERS, 1):
        print(f"\\n[{i}/{{len(CHAPTERS)}}] 第{{ch['number']}}章: {{ch['title']}}")
        print("  模拟上传...")
        time.sleep(1)
        print("  ✓ 完成")
    
    print("\\n" + "=" * 60)
    print("上传完成！")
    print("=" * 60)
    input("\\n请按回车键退出...")

if __name__ == "__main__":
    main()
'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        return True
        
    except Exception as e:
        print(f"[ScriptGenerator] 生成简易脚本失败: {e}")
        return False
