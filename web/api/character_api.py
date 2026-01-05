"""
角色数据管理API
提供角色数据的加载、保存和管理功能
"""

from flask import Blueprint, request, jsonify
import json
from pathlib import Path
import re
from datetime import datetime
from functools import wraps

# 创建蓝图
character_api = Blueprint('character_api', __name__)

# 导入日志记录器
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# API登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


class CharacterDataManager:
    """角色数据管理器"""
    
    def __init__(self, project_title):
        self.project_title = project_title
        self.safe_title = re.sub(r'[\\/*?"<>|]', "_", project_title)
        self.project_dir = Path("小说项目") / self.project_title
        if not self.project_dir.exists():
            self.project_dir = Path("小说项目") / self.safe_title
        
        self.characters_file = self.project_dir / "characters_data.json"
    
    def load_characters(self):
        """加载角色数据"""
        # 首先从项目目录加载
        if self.characters_file.exists():
            try:
                with open(self.characters_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"从项目目录加载角色数据: {self.characters_file}")
                    return data
            except Exception as e:
                logger.error(f"加载角色数据失败: {e}")
        
        # 尝试从产物文件加载
        characters_dir = self.project_dir / "characters"
        if characters_dir.exists():
            characters_files = list(characters_dir.glob("*.json"))
            if characters_files:
                try:
                    with open(characters_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"从产物文件加载角色数据: {characters_files[0]}")
                        # 如果是数组，直接返回；如果是对象，提取characters字段
                        if isinstance(data, list):
                            return data
                        elif isinstance(data, dict) and 'characters' in data:
                            return data['characters']
                        return []
                except Exception as e:
                    logger.error(f"加载角色产物失败: {e}")
        
        # 返回空数组
        logger.info("使用空角色数据")
        return []
    
    def save_characters(self, characters):
        """保存角色数据"""
        try:
            self.characters_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加时间戳
            data = {
                'characters': characters,
                'updated_at': datetime.now().isoformat(),
                'project_title': self.project_title
            }
            
            with open(self.characters_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"角色数据已保存: {self.characters_file}")
            return True
        except Exception as e:
            logger.error(f"保存角色数据失败: {e}")
            return False


# ==================== API路由 ====================

@character_api.route('/characters/<project_title>', methods=['GET'])
@login_required
def get_characters(project_title):
    """获取项目的角色数据"""
    try:
        manager = CharacterDataManager(project_title)
        characters = manager.load_characters()
        
        return jsonify({
            'success': True,
            'characters': characters
        })
    except Exception as e:
        logger.error(f"获取角色数据失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@character_api.route('/characters/<project_title>', methods=['POST'])
@login_required
def save_characters_data(project_title):
    """保存项目的角色数据"""
    try:
        data = request.json
        
        if not data or 'characters' not in data:
            return jsonify({
                'success': False,
                'error': '角色数据不能为空'
            }), 400
        
        characters = data['characters']
        
        manager = CharacterDataManager(project_title)
        success = manager.save_characters(characters)
        
        if success:
            return jsonify({
                'success': True,
                'message': '角色数据保存成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '保存失败'
            }), 500
            
    except Exception as e:
        logger.error(f"保存角色数据失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@character_api.route('/characters/<project_title>/export', methods=['GET'])
@login_required
def export_characters(project_title):
    """导出角色数据为JSON文件"""
    try:
        manager = CharacterDataManager(project_title)
        characters = manager.load_characters()
        
        # 返回JSON数据，前端可以下载
        from flask import Response
        response = Response(
            json.dumps(characters, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={project_title}_characters.json'
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"导出角色数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 路由注册函数 ====================

def register_character_routes(app):
    """注册角色API路由"""
    app.register_blueprint(character_api, url_prefix='/api')
    logger.debug("✅ 角色API路由已注册")