"""
世界观可视化API接口
提供世界观数据的加载、保存和管理功能
"""

from flask import Blueprint, request, jsonify
import json
from pathlib import Path
import re
from datetime import datetime
from functools import wraps

# 创建蓝图
worldview_api = Blueprint('worldview_api', __name__)

# 导入日志记录器
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

# 初始化日志记录器
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


# ==================== 辅助类 ====================

class WorldviewDataManager:
    """世界观数据管理器"""
    
    def __init__(self, project_title):
        self.project_title = project_title
        self.safe_title = re.sub(r'[\\/*?"<>|]', "_", project_title)
        self.project_dir = Path("小说项目") / self.project_title
        if not self.project_dir.exists():
            self.project_dir = Path("小说项目") / self.safe_title
        
        self.worldview_file = self.project_dir / "worldview_data.json"
    
    def load_worldview(self):
        """加载世界观数据"""
        # 首先从项目目录加载
        if self.worldview_file.exists():
            try:
                with open(self.worldview_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"从项目目录加载世界观数据: {self.worldview_file}")
                    return data
            except Exception as e:
                logger.error(f"加载世界观数据失败: {e}")
        
        # 尝试从产物文件加载
        worldview_dir = self.project_dir / "worldview"
        if worldview_dir.exists():
            worldview_files = list(worldview_dir.glob("*.json"))
            if worldview_files:
                try:
                    with open(worldview_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        logger.info(f"从产物文件加载世界观: {worldview_files[0]}")
                        return self._convert_to_viewer_format(data)
                except Exception as e:
                    logger.error(f"加载世界观产物失败: {e}")
        
        # 返回默认数据
        logger.info("使用默认世界观数据")
        return self._get_default_data()
    
    def save_worldview(self, data):
        """保存世界观数据"""
        try:
            self.worldview_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 添加时间戳
            data['updated_at'] = datetime.now().isoformat()
            
            with open(self.worldview_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"世界观数据已保存: {self.worldview_file}")
            return True
        except Exception as e:
            logger.error(f"保存世界观数据失败: {e}")
            return False
    
    def _convert_to_viewer_format(self, data):
        """将产物格式转换为可视化格式"""
        # 这里可以根据实际的数据格式进行转换
        return {
            'worldName': data.get('title', self.project_title),
            'worldDescription': data.get('description', ''),
            'factions': self._extract_factions(data),
            'locations': self._extract_locations(data),
            'timeline': self._extract_timeline(data),
            'powerSystem': self._format_power_system(data),
            'magicSystem': self._format_magic_system(data),
            'socialSystem': self._format_social_system(data),
            'worldRules': self._format_world_rules(data)
        }
    
    def _extract_factions(self, data):
        """从数据中提取势力信息"""
        factions = data.get('factions', data.get('powers', []))
        if not factions:
            # 返回默认势力
            return [
                {
                    'id': 1,
                    'name': '正道盟',
                    'description': '以修仙正道自居，维护世间秩序',
                    'color': '#667eea',
                    'icon': '⚔️',
                    'power': 90,
                    'territories': ['天南大陆'],
                    'relations': {}
                }
            ]
        
        return factions
    
    def _extract_locations(self, data):
        """从数据中提取地点信息"""
        locations = data.get('locations', data.get('places', []))
        if not locations:
            return []
        return locations
    
    def _extract_timeline(self, data):
        """从数据中提取时间轴信息"""
        timeline = data.get('timeline', data.get('history', []))
        if not timeline:
            return []
        return timeline
    
    def _format_power_system(self, data):
        """格式化修炼体系"""
        power_system = data.get('power_system', data.get('cultivation_system', {}))
        if isinstance(power_system, dict):
            html = "<h4>修炼等级</h4><ul>"
            for level, desc in power_system.items():
                html += f"<li><strong>{level}</strong>：{desc}</li>"
            html += "</ul>"
            return html
        return str(power_system) if power_system else "<p>暂无修炼体系设定</p>"
    
    def _format_magic_system(self, data):
        """格式化法术系统"""
        magic_system = data.get('magic_system', data.get('spell_system', {}))
        if isinstance(magic_system, dict):
            html = "<h4>法术分类</h4><ul>"
            for category, desc in magic_system.items():
                html += f"<li><strong>{category}</strong>：{desc}</li>"
            html += "</ul>"
            return html
        return str(magic_system) if magic_system else "<p>暂无法术系统设定</p>"
    
    def _format_social_system(self, data):
        """格式化社会制度"""
        social_system = data.get('social_system', data.get('society', {}))
        if isinstance(social_system, dict):
            html = "<h4>势力等级</h4><ul>"
            for level, desc in social_system.items():
                html += f"<li><strong>{level}</strong>：{desc}</li>"
            html += "</ul>"
            return html
        return str(social_system) if social_system else "<p>暂无社会制度设定</p>"
    
    def _format_world_rules(self, data):
        """格式化世界规则"""
        world_rules = data.get('world_rules', data.get('rules', {}))
        if isinstance(world_rules, dict):
            html = "<h4>基本规则</h4><ul>"
            for rule, desc in world_rules.items():
                html += f"<li><strong>{rule}</strong>：{desc}</li>"
            html += "</ul>"
            return html
        return str(world_rules) if world_rules else "<p>暂无世界规则设定</p>"
    
    def _get_default_data(self):
        """获取默认世界观数据"""
        return {
            'worldName': self.project_title,
            'worldDescription': '请编辑世界观描述',
            'factions': [
                {
                    'id': 1,
                    'name': '势力1',
                    'description': '势力描述',
                    'color': '#667eea',
                    'icon': '🏰',
                    'power': 50,
                    'territories': [],
                    'relations': {}
                }
            ],
            'locations': [],
            'timeline': [],
            'powerSystem': '<p>暂无修炼体系设定</p>',
            'magicSystem': '<p>暂无法术系统设定</p>',
            'socialSystem': '<p>暂无社会制度设定</p>',
            'worldRules': '<p>暂无世界规则设定</p>'
        }


# ==================== API路由 ====================

@worldview_api.route('/worldview/<project_title>', methods=['GET'])
@login_required
def get_worldview(project_title):
    """获取项目的世界观数据"""
    try:
        manager = WorldviewDataManager(project_title)
        data = manager.load_worldview()
        
        return jsonify({
            'success': True,
            'worldview': data
        })
    except Exception as e:
        logger.error(f"获取世界观数据失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@worldview_api.route('/worldview/<project_title>', methods=['POST'])
@login_required
def save_worldview_data(project_title):
    """保存项目的世界观数据"""
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': '数据不能为空'
            }), 400
        
        manager = WorldviewDataManager(project_title)
        success = manager.save_worldview(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': '世界观保存成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '保存失败'
            }), 500
            
    except Exception as e:
        logger.error(f"保存世界观数据失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@worldview_api.route('/worldview/<project_title>/export', methods=['GET'])
@login_required
def export_worldview(project_title):
    """导出世界观数据为JSON文件"""
    try:
        manager = WorldviewDataManager(project_title)
        data = manager.load_worldview()
        
        # 返回JSON数据，前端可以下载
        from flask import Response
        response = Response(
            json.dumps(data, ensure_ascii=False, indent=2),
            mimetype='application/json',
            headers={
                'Content-Disposition': f'attachment; filename={project_title}_worldview.json'
            }
        )
        
        return response
    except Exception as e:
        logger.error(f"导出世界观数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@worldview_api.route('/worldview/<project_title>/import', methods=['POST'])
@login_required
def import_worldview(project_title):
    """导入世界观数据"""
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': '没有上传文件'
            }), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({
                'success': False,
                'error': '文件名为空'
            }), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({
                'success': False,
                'error': '只支持JSON格式文件'
            }), 400
        
        # 读取文件内容
        data = json.load(file.stream)
        
        # 保存到项目
        manager = WorldviewDataManager(project_title)
        success = manager.save_worldview(data)
        
        if success:
            return jsonify({
                'success': True,
                'message': '导入成功'
            })
        else:
            return jsonify({
                'success': False,
                'error': '导入失败'
            }), 500
            
    except Exception as e:
        logger.error(f"导入世界观数据失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 路由注册函数 ====================

def register_worldview_routes(app):
    """注册世界观API路由"""
    app.register_blueprint(worldview_api, url_prefix='/api')
    logger.debug("✅ 世界观API路由已注册")