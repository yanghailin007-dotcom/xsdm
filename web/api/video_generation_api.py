"""
多类型视频生成API接口 - 支持三种视频模式

支持的视频类型：
1. short_film - 短片/动画电影（5-30分钟）
2. long_series - 长篇剧集（20-40分钟/集）
3. short_video - 短视频系列（1-3分钟）
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from typing import Dict, List
import os
import sys
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

# 创建蓝图
video_api = Blueprint('video_api', __name__)

# 初始化日志记录器
logger = get_logger(__name__)

# 导入管理器
try:
    from web.managers.novel_manager import NovelGenerationManager
    manager = NovelGenerationManager()
except Exception as e:
    logger.error(f"无法初始化NovelGenerationManager: {e}")
    manager = None


# API登录装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'logged_in' not in session:
            return jsonify({"success": False, "error": "需要登录", "code": "AUTH_REQUIRED"}), 401
        return f(*args, **kwargs)
    return decorated_function


@video_api.route('/video/novels', methods=['GET'])
@login_required
def get_eligible_novels():
    """
    获取可用于视频生成的小说列表
    只返回已完成第一阶段的小说
    """
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取所有小说项目
        all_projects = manager.get_novel_projects()
        
        # 筛选符合条件的小说
        eligible_novels = []
        for project in all_projects:
            title = project.get("title", "")
            # 获取完整的小说数据以检查是否具备视频生成条件
            novel_detail = manager.get_novel_detail(title)
            
            if novel_detail and _is_eligible_for_video_generation(novel_detail):
                novel_detail["video_ready"] = True
                novel_detail["total_medium_events"] = _count_medium_events(novel_detail)
                novel_detail["estimated_episodes"] = novel_detail["total_medium_events"]
                novel_detail["total_duration_minutes"] = round(novel_detail["total_medium_events"] * 3.5, 1)
                eligible_novels.append(novel_detail)
        
        logger.info(f"✅ [VIDEO] 筛选完成：{len(eligible_novels)}/{len(all_projects)} 个小说可用")
        
        return jsonify({
            "success": True,
            "novels": eligible_novels,
            "total": len(eligible_novels)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 获取小说列表失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _is_eligible_for_video_generation(novel_data: Dict) -> bool:
    """
    检查小说是否具备视频生成条件
    使用与小说列表页面相同的判断标准：必须完成所有7个产物
    """
    try:
        title = novel_data.get("title") or novel_data.get("novel_title", "")
        if not title:
            return False
        
        # 使用ProductLoader来检查所有7个产物
        from web.api.phase_generation_api import ProductLoader
        loader = ProductLoader(title, logger)
        products = loader.load_all_products()
        
        # 必须完成所有7个产物
        required_categories = ['worldview', 'factions', 'characters', 'growth', 'writing', 'storyline', 'market']
        completed_required = 7
        
        # 计算关键产物的完成数量
        key_products_count = 0
        for category in required_categories:
            if products.get(category, {}).get('complete', False):
                key_products_count += 1
        
        is_eligible = key_products_count >= completed_required
        
        if is_eligible:
            logger.info(f"✅ [VIDEO] {title} 具备视频生成条件：{key_products_count}/{completed_required} 个产物已完成")
        else:
            logger.info(f"⚠️ [VIDEO] {title} 不具备视频生成条件：仅 {key_products_count}/{completed_required} 个产物已完成")
        
        return is_eligible
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 检查视频生成条件失败: {e}")
        return False


def _count_medium_events(novel_data: Dict) -> int:
    """统计小说中的中级事件总数"""
    total_count = 0
    
    stage_plans = novel_data.get("stage_writing_plans", {})
    for stage_data in stage_plans.values():
        plan = stage_data.get("stage_writing_plan", {})
        events = plan.get("event_system", {}).get("major_events", [])
        
        for event in events:
            composition = event.get("composition", {})
            for stage_events in composition.values():
                total_count += len(stage_events)
    
    return total_count


@video_api.route('/video/types', methods=['GET'])
def get_video_types():
    """
    获取支持的视频类型列表
    
    返回所有可用的视频类型及其配置
    """
    video_types = {
        "short_film": {
            "name": "短片/动画电影",
            "description": "3-10分钟的完整故事，适合动画电影或短片制作",
            "duration_range": "3-10分钟",
            "characteristics": [
                "精简情节，聚焦主线",
                "节奏紧凑，无冗余",
                "视觉表现力强",
                "艺术化镜头语言"
            ],
            "use_cases": ["动画短片", "电影预告片", "剧情短片", "独立动画"]
        },
        "long_series": {
            "name": "长篇剧集",
            "description": "1-5分钟/集的连续剧集，适合网络动画或短视频剧",
            "duration_range": "1-5分钟/集",
            "characteristics": [
                "多集连续，每集完整但有关联",
                "保留丰富的支线剧情",
                "节奏张弛有度",
                "注重角色发展",
                "支持200集长篇连载"
            ],
            "use_cases": ["网络动画", "短视频剧", "连续剧", "番剧"]
        },
        "short_video": {
            "name": "短视频系列",
            "description": "30秒-1分钟的竖屏短视频，适合抖音、快手等平台",
            "duration_range": "30秒-1分钟",
            "characteristics": [
                "极度精炼，只保留高光时刻",
                "节奏极快，3秒一钩子",
                "视觉冲击力强",
                "竖屏构图",
                "即时满足感"
            ],
            "use_cases": ["抖音", "快手", "视频号", "B站短视频", "YouTube Shorts"]
        }
    }
    
    return jsonify({
        "success": True,
        "video_types": video_types
    })


@video_api.route('/video/novel-content', methods=['GET'])
@login_required
def get_novel_content():
    """
    获取小说的事件和角色内容
    
    查询参数：
    - title: 小说标题
    """
    try:
        title = request.args.get('title')
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        logger.info(f"📊 [VIDEO] 获取小说内容: {title}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 🔥 使用通用事件提取器提取事件和角色
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        
        # 提取事件 - 返回层级结构
        all_events = event_extractor.extract_all_major_events(novel_detail)
        logger.info(f"📊 [VIDEO] 提取到 {len(all_events)} 个重大事件")
        
        # 格式化事件数据 - 层级结构（重大事件包含中级事件）
        events = []
        
        for idx, major_event in enumerate(all_events):
            # 获取重大事件信息
            event_name = major_event.get("name", major_event.get("title", f"事件 {idx + 1}"))
            description = major_event.get("description", "")
            chapter_range = major_event.get("chapter_range", "")
            
            # 提取中级事件
            composition = major_event.get("composition", {})
            medium_events_list = []
            
            if composition:
                # 使用正确的阶段名称（与故事线一致）
                stage_order = ["起", "承", "转", "合"]
                for stage in stage_order:
                    medium_events = composition.get(stage, [])
                    if isinstance(medium_events, list) and medium_events:
                        for medium_event in medium_events:
                            # 🔥 优先级尝试多个字段名来获取标题
                            event_title = (
                                medium_event.get("title") or
                                medium_event.get("name") or
                                medium_event.get("event") or
                                medium_event.get("main_goal") or
                                medium_event.get("role_in_stage_arc") or
                                f"中级事件 {len(medium_events_list) + 1}"
                            )
                            
                            medium_events_list.append({
                                "id": f"event_{len(events)}_{len(medium_events_list)}",
                                "title": event_title,
                                "description": medium_event.get("description", ""),
                                "stage": stage,
                                "characters": medium_event.get("characters", ""),
                                "location": medium_event.get("location", ""),
                                "emotion": medium_event.get("emotion", "")
                            })
            
            # 创建重大事件（包含子事件）
            events.append({
                "id": f"major_event_{idx}",
                "title": event_name,
                "description": description,
                "chapter_range": chapter_range,
                "type": "major",  # 标记为重大事件
                "has_children": len(medium_events_list) > 0,
                "children_count": len(medium_events_list),
                "children": medium_events_list,
                "characters": major_event.get("characters", ""),
                "location": major_event.get("location", ""),
                "emotion": major_event.get("emotion", "")
            })
        
        logger.info(f"📊 [VIDEO] 格式化后共有 {len(events)} 个重大事件，包含 {sum(e['children_count'] for e in events)} 个中级事件")
        
        # 提取角色
        characters = event_extractor.extract_character_designs(novel_detail)
        logger.info(f"👥 [VIDEO] 提取到 {len(characters)} 个角色设计")
        
        # 格式化角色数据
        formatted_characters = []
        for idx, character in enumerate(characters):
            formatted_characters.append({
                "id": f"character_{idx}",
                "name": character.get("name", f"角色 {idx + 1}"),
                "role": character.get("role", ""),
                "description": character.get("description", "")[:200]
            })
        
        return jsonify({
            "success": True,
            "events": events,
            "characters": formatted_characters,
            "total_events": len(events),
            "total_characters": len(formatted_characters)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 获取小说内容失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/generate-prompt', methods=['POST'])
@login_required
def generate_prompt():
    """
    生成视频生成提示词（基于选中的事件和角色）
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",
        "selected_events": [
            {"id": "event_0", "title": "...", "stage": "起因", ...}
        ],
        "selected_characters": [
            {"id": "character_0", "name": "...", ...}
        ]
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        selected_events = data.get('selected_events', [])
        selected_characters = data.get('selected_characters', [])
        
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        logger.info(f"🎬 [VIDEO] 生成提示词: {title} - {video_type}")
        logger.info(f"📊 [VIDEO] 选中事件: {len(selected_events)}个, 角色: {len(selected_characters)}个")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 检查是否已完成第一阶段
        has_phase_one = bool(novel_detail.get("quality_data")) or bool(novel_detail.get("core_worldview"))
        if not has_phase_one:
            return jsonify({"success": False, "error": "小说尚未完成第一阶段设定"}), 400
        
        # 🔥 使用新的视频场景提示词生成器
        from src.prompts.VideoScenePrompts import get_video_scene_prompts
        scene_prompt_generator = get_video_scene_prompts()
        
        # 🔥 将重大事件展开为中级事件
        expanded_events = []
        
        # 首先获取所有重大事件（用于查找）
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        all_major_events = event_extractor.extract_all_major_events(novel_detail)
        
        # 创建重大事件索引（按ID或名称查找）
        # 🔥 修复：同时支持 event_X 和 major_event_X 两种ID格式
        major_events_map = {}
        for idx, major_event in enumerate(all_major_events):
            event_id = f"event_{idx}"
            major_event_id = f"major_event_{idx}"
            event_name = major_event.get("name", major_event.get("title", ""))
            major_events_map[event_id] = major_event
            major_events_map[major_event_id] = major_event
            major_events_map[event_name] = major_event
        
        if not selected_events:
            # 如果没有选中事件，提取所有重大事件并展开
            for major_event in all_major_events:
                composition = major_event.get("composition", {})
                # 🔥 修复：使用EventExtractor的extract_medium_events方法
                # 它会自动处理新旧两种格式（"起承转合"和"起因发展高潮结局"）
                medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
                for medium_event in medium_events_from_extractor:
                    medium_event_copy = dict(medium_event)
                    medium_event_copy["parent_major"] = major_event.get("name")
                    expanded_events.append(medium_event_copy)
            
            logger.info(f"📊 [VIDEO] 未指定事件，自动提取所有中级事件: {len(expanded_events)}个")
        else:
            # 用户选中的是重大事件，需要展开为中级事件
            for selected_event in selected_events:
                # 处理不同格式的输入
                if isinstance(selected_event, str):
                    # 🔥 新增：处理复合ID格式（major_event_X_event_Y_Z）
                    if '_event_' in selected_event and selected_event.startswith('major_event_'):
                        # 这是中级事件的复合ID（格式：major_event_X_event_Y_Z）
                        # 从右边分割，找到最后一个 _event_
                        parts = selected_event.rsplit('_event_', 1)
                        parent_id = parts[0]
                        
                        # 从父事件中查找对应的子事件
                        major_event = major_events_map.get(parent_id)
                        if major_event:
                            composition = major_event.get("composition", {})
                            # 子事件ID格式：event_Y_Z，其中Y是重大事件索引，Z是子事件索引
                            child_id_suffix = selected_event.replace(f'{parent_id}_', '')
                            
                            # 遍历所有阶段查找子事件
                            found = False
                            for stage in ["起", "承", "转", "合"]:
                                medium_events = composition.get(stage, [])
                                for idx, medium_event in enumerate(medium_events):
                                    # 🔥 修复：生成完整的子事件ID（包含父索引）
                                    # child_id_suffix 格式：event_0_0 (第一个0是父事件索引，第二个0是子事件索引)
                                    # 需要从 parent_id 中提取父事件索引
                                    parent_idx = parent_id.replace("major_event_", "")
                                    full_child_id = f"event_{parent_idx}_{idx}"
                                    
                                    # 检查子事件ID是否匹配
                                    if child_id_suffix == full_child_id:
                                        medium_event_copy = dict(medium_event)
                                        medium_event_copy["parent_major"] = major_event.get("name", major_event.get("title", ""))
                                        medium_event_copy["stage"] = stage
                                        expanded_events.append(medium_event_copy)
                                        found = True
                                        logger.info(f"📊 [VIDEO] 通过复合ID '{selected_event}' 找到子事件 (stage={stage}, idx={idx})")
                                        break
                                if found:
                                    break
                            
                            if not found:
                                logger.warn(f"⚠️ [VIDEO] 无法在复合ID '{selected_event}' 中找到子事件")
                        else:
                            logger.warn(f"⚠️ [VIDEO] 无法在复合ID '{selected_event}' 中找到父事件 '{parent_id}'")
                    
                    # 🔥 原有逻辑：尝试从重大事件映射中查找
                    else:
                        major_event = major_events_map.get(selected_event)
                        if major_event:
                            # 找到了重大事件，展开它的中级事件
                            # 🔥 修复：使用EventExtractor的extract_medium_events方法
                            # 它会自动处理新旧两种格式
                            medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
                            for medium_event in medium_events_from_extractor:
                                medium_event_copy = dict(medium_event)
                                medium_event_copy["parent_major"] = major_event.get("name", major_event.get("title", ""))
                                expanded_events.append(medium_event_copy)
                            
                            logger.info(f"📊 [VIDEO] 通过ID '{selected_event}' 展开重大事件 '{major_event.get('name')}' 为 {len([e for e in expanded_events if e.get('parent_major') == major_event.get('name')])} 个中级事件")
                        else:
                            logger.warn(f"⚠️ [VIDEO] 未找到ID为 '{selected_event}' 的事件")
                
                elif isinstance(selected_event, dict):
                    # 如果是字典，检查是否是重大事件（有composition字段）
                    if selected_event.get("composition"):
                        # 这是重大事件，展开其中的中级事件
                        # 🔥 修复：使用EventExtractor的extract_medium_events方法
                        # 它会自动处理新旧两种格式
                        medium_events_from_extractor = event_extractor.extract_medium_events(selected_event)
                        for medium_event in medium_events_from_extractor:
                            medium_event_copy = dict(medium_event)
                            medium_event_copy["parent_major"] = selected_event.get("name", selected_event.get("title", ""))
                            expanded_events.append(medium_event_copy)
                        
                        logger.info(f"📊 [VIDEO] 展开重大事件 '{selected_event.get('name')}' 为 {len([e for e in expanded_events if e.get('parent_major') == selected_event.get('name')])} 个中级事件")
                    
                    elif selected_event.get("stage") in ["起因", "发展", "高潮", "结局"]:
                        # 这已经是中级事件，直接使用
                        expanded_events.append(selected_event)
                    
                    else:
                        logger.warn(f"⚠️ [VIDEO] 未知的事件格式: {selected_event}")
                
                else:
                    logger.warn(f"⚠️ [VIDEO] 跳过不支持的事件类型: {type(selected_event)}")
        
        # 使用展开后的中级事件
        selected_events = expanded_events
        
        if not selected_events:
            return jsonify({"success": False, "error": "未能从选中的事件中提取到任何中级事件"}), 400
        
        logger.info(f"✅ [VIDEO] 最终使用 {len(selected_events)} 个中级事件生成提示词")
        
        # 如果没有选中角色，提取主要角色
        if not selected_characters:
            from src.managers.EventExtractor import get_event_extractor
            event_extractor = get_event_extractor(logger)
            all_characters = event_extractor.extract_character_designs(novel_detail)
            
            # 只选择主角和重要配角
            selected_characters = [
                char for char in all_characters
                if char.get("role", "") in ["主角", "重要配角", "配角"]
            ][:5]  # 最多5个角色
            
            logger.info(f"👥 [VIDEO] 未指定角色，自动提取主要角色: {len(selected_characters)}个")
        
        # 生成详细的场景级提示词
        prompt = scene_prompt_generator.generate_video_type_prompt(
            selected_events=selected_events,
            selected_characters=selected_characters,
            video_type=video_type,
            novel_data=novel_detail
        )
        
        # 统计信息
        total_shots_estimate = _estimate_total_shots(selected_events, video_type)
        total_duration_estimate = _estimate_total_duration(selected_events, video_type)
        
        logger.info(f"✅ [VIDEO] 提示词生成成功")
        logger.info(f"📊 [VIDEO] 预计镜头数: {total_shots_estimate}, 预计时长: {total_duration_estimate}分钟")
        
        return jsonify({
            "success": True,
            "prompt": prompt,
            "metadata": {
                "selected_events_count": len(selected_events),
                "selected_characters_count": len(selected_characters),
                "estimated_shots": total_shots_estimate,
                "estimated_duration_minutes": total_duration_estimate,
                "video_type": video_type
            }
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 生成提示词失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _estimate_total_shots(events: List[Dict], video_type: str) -> int:
    """估算总镜头数"""
    if video_type == "long_series":
        # 长剧集：每个中级事件根据阶段不同有不同镜头数
        shots_map = {"起因": 5, "发展": 8, "高潮": 15, "结局": 4}
        return sum(shots_map.get(e.get("stage", "发展"), 8) for e in events)
    elif video_type == "short_film":
        # 短片：每个重大事件5-7个镜头
        return len(events) * 6
    else:  # short_video
        # 短视频：每个事件5-7个镜头
        return len(events) * 6


def _estimate_total_duration(events: List[Dict], video_type: str) -> float:
    """估算总时长（分钟）"""
    if video_type == "long_series":
        # 长剧集：根据阶段不同时长不同
        duration_map = {"起因": 2.0, "发展": 3.5, "高潮": 7.5, "结局": 1.8}
        return sum(duration_map.get(e.get("stage", "发展"), 3.5) for e in events)
    elif video_type == "short_film":
        # 短片：每个重大事件3-4分钟
        return len(events) * 3.5
    else:  # short_video
        # 短视频：每个事件约1分钟
        return len(events) * 1.0


@video_api.route('/video/generate-storyboard', methods=['POST'])
@login_required
def generate_storyboard():
    """
    生成分镜头脚本（包含角色设计提取）
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series"
    }
    
    工作流程：
    1. 提取重大事件
    2. 提取角色设计
    3. 生成分镜头脚本
    4. 生成角色剧照生成提示词
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        logger.info(f"🎬 [VIDEO] 生成分镜头: {title} - {video_type}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 🔥 新增：使用通用事件提取器提取事件和角色
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        
        # 提取事件
        all_events = event_extractor.extract_all_major_events(novel_detail)
        logger.info(f"📊 [VIDEO] 提取到 {len(all_events)} 个重大事件")
        
        # 提取角色
        characters = event_extractor.extract_character_designs(novel_detail)
        character_prompts = event_extractor.generate_character_prompts(characters)
        logger.info(f"👥 [VIDEO] 提取到 {len(characters)} 个角色设计")
        
        # 使用视频适配器进行转换
        from src.managers.VideoAdapterManager import VideoAdapterManager
        
        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None
        
        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)
        
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type
        )
        
        # 提取所有镜头
        units = video_result.get("units", [])
        shots = []
        
        for unit in units:
            storyboard = unit.get("storyboard", {})
            scenes = storyboard.get("scenes", [])
            
            for scene in scenes:
                shot_sequence = scene.get("shot_sequence", [])
                for shot in shot_sequence:
                    shots.append({
                        "shot_index": len(shots),
                        "unit_number": unit.get("unit_number"),
                        "scene_number": scene.get("scene_number"),
                        "scene_description": scene.get("scene_description", ""),
                        "shot_number": shot.get("shot_number"),
                        "shot_type": shot.get("shot_type", "中景"),
                        "camera_movement": shot.get("camera_movement", "固定"),
                        "duration_seconds": shot.get("duration_seconds", 5),
                        "description": shot.get("description", ""),
                        "audio_cue": shot.get("audio_note", shot.get("tiktok_note", "")),
                        "generation_prompt": f"""{shot.get('description', '')}
景别：{shot.get('shot_type', '中景')}
运镜：{shot.get('camera_movement', '固定')}
时长：{shot.get('duration_seconds', 5)}秒""",
                        "status": "pending",
                        "visual_style": video_result.get("visual_style_guide", {}).get("overall_style", "写实")
                    })
        
        return jsonify({
            "success": True,
            "storyboard": video_result,
            "shots": shots,
            "total_shots": len(shots)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 生成分镜头失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/generate-storyboard-custom', methods=['POST'])
@login_required
def generate_storyboard_custom():
    """
    基于自定义提示词生成分镜头脚本
    
    请求参数：
    {
        "prompt": "自定义提示词",
        "video_type": "long_series"
    }
    """
    try:
        data = request.json or {}
        prompt = data.get('prompt', '')
        video_type = data.get('video_type', 'long_series')
        
        if not prompt:
            return jsonify({"success": False, "error": "提示词不能为空"}), 400
        
        logger.info(f"🎬 [VIDEO] 自定义模式生成分镜头: {video_type}")
        logger.info(f"📝 [VIDEO] 提示词长度: {len(prompt)} 字符")
        
        # 根据视频类型生成默认分镜头结构
        type_configs = {
            "short_film": {
                "name": "短片/动画电影",
                "default_units": 1,
                "shots_per_unit": 15,
                "avg_duration": 5
            },
            "long_series": {
                "name": "长篇剧集",
                "default_units": 3,
                "shots_per_unit": 10,
                "avg_duration": 4
            },
            "short_video": {
                "name": "短视频系列",
                "default_units": 5,
                "shots_per_unit": 5,
                "avg_duration": 3
            }
        }
        
        config = type_configs.get(video_type, type_configs["long_series"])
        
        # 构建视频结果结构
        video_result = {
            "video_type": video_type,
            "video_type_name": config["name"],
            "mode": "custom",
            "custom_prompt": prompt,
            "series_info": {
                "title": "自定义视频项目",
                "total_units": config["default_units"],
                "video_format": video_type
            },
            "visual_style_guide": {
                "overall_style": "自定义",
                "color_palette": "根据提示词自动适配",
                "atmosphere": "根据提示词自动生成"
            },
            "pacing_guidelines": {
                "tempo": "根据视频类型自动调整",
                "transitions": "平滑过渡"
            },
            "units": []
        }
        
        # 生成分镜头单元
        shots = []
        for unit_idx in range(config["default_units"]):
            unit_number = unit_idx + 1
            unit_type = "自定义单元"
            
            # 创建场景
            scenes = [{
                "scene_number": 1,
                "scene_title": f"场景 {unit_number}",
                "scene_description": f"基于自定义提示词的场景：{prompt[:100]}...",
                "estimated_duration_minutes": round(config["shots_per_unit"] * config["avg_duration"] / 60, 1),
                "shot_sequence": [],
                "visual_notes": {
                    "color_palette": "根据提示词适配",
                    "lighting": "标准",
                    "composition_style": "电影级"
                }
            }]
            
            # 生成镜头序列
            for shot_idx in range(config["shots_per_unit"]):
                shot_number = shot_idx + 1
                shot = {
                    "shot_number": shot_number,
                    "shot_type": _get_default_shot_type(shot_idx, config["shots_per_unit"]),
                    "camera_movement": _get_default_camera_movement(shot_idx),
                    "duration_seconds": config["avg_duration"],
                    "description": f"基于提示词的第{shot_number}个镜头：{prompt[:50]}...",
                    "audio_note": _get_default_audio_note(shot_idx, video_type),
                    "tiktok_note": _get_default_tiktok_note(video_type)
                }
                
                scenes[0]["shot_sequence"].append(shot)
                
                # 添加到shots列表
                shots.append({
                    "shot_index": len(shots),
                    "unit_number": unit_number,
                    "scene_number": 1,
                    "scene_description": scenes[0]["scene_description"],
                    "shot_number": shot_number,
                    "shot_type": shot["shot_type"],
                    "camera_movement": shot["camera_movement"],
                    "duration_seconds": shot["duration_seconds"],
                    "description": shot["description"],
                    "audio_cue": shot["audio_note"],
                    "generation_prompt": f"""自定义提示词：{prompt}

镜头 #{shot_number}：
{shot["description"]}
景别：{shot["shot_type"]}
运镜：{shot["camera_movement"]}
时长：{shot["duration_seconds"]}秒
音频：{shot["audio_note"]}""",
                    "status": "pending",
                    "visual_style": "自定义"
                })
            
            # 计算场景总时长
            total_duration = sum(
                shot["duration_seconds"] for shot in scenes[0]["shot_sequence"]
            )
            
            video_result["units"].append({
                "unit_number": unit_number,
                "unit_type": unit_type,
                "title": f"自定义视频 - 第{unit_number}部分",
                "storyboard": {
                    "scenes": scenes,
                    "total_shots": len(scenes[0]["shot_sequence"]),
                    "total_duration_minutes": round(total_duration / 60, 1)
                }
            })
        
        logger.info(f"✅ [VIDEO] 自定义模式生成分镜头成功: {len(shots)} 个镜头")
        
        return jsonify({
            "success": True,
            "storyboard": video_result,
            "shots": shots,
            "total_shots": len(shots),
            "message": f"已生成 {len(shots)} 个分镜头"
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 自定义模式生成分镜头失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _get_default_shot_type(index, total_shots):
    """根据镜头位置返回默认景别"""
    if index == 0:
        return "大远景"  # 开场
    elif index == total_shots - 1:
        return "全景"  # 结尾
    elif index % 3 == 0:
        return "中景"
    elif index % 3 == 1:
        return "近景"
    else:
        return "特写"


def _get_default_camera_movement(index):
    """根据镜头位置返回默认运镜"""
    movements = ["固定", "缓慢推", "缓慢拉", "平移", "跟随", "环绕", "升降", "固定"]
    return movements[index % len(movements)]


def _get_default_audio_note(index, video_type):
    """返回默认音频提示"""
    if video_type == "short_video":
        notes = ["节奏感强的音乐", "音效强调", "背景音乐渐强", "高潮音效"]
    else:
        notes = ["环境音", "背景音乐", "角色音效", "过渡音效", "氛围音乐"]
    return notes[index % len(notes)]


def _get_default_tiktok_note(video_type):
    """返回TikTok风格提示"""
    if video_type == "short_video":
        return "快速剪辑，节奏紧凑"
    return "标准视频节奏"


@video_api.route('/video/generate-shot', methods=['POST'])
@login_required
def generate_shot():
    """
    生成单个镜头视频
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",
        "shot_index": 0,
        "shot_data": {...}
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        shot_index = data.get('shot_index')
        shot_data = data.get('shot_data')
        
        if shot_index is None or not shot_data:
            return jsonify({"success": False, "error": "缺少镜头参数"}), 400
        
        logger.info(f"🎬 [VIDEO] 生成镜头 #{shot_index}: {title}")
        
        # 这里应该调用实际的视频生成API
        # 目前返回模拟数据
        logger.info(f"📝 镜头提示词: {shot_data.get('generation_prompt', '')}")
        
        # 模拟生成过程
        import time
        time.sleep(1)  # 模拟处理时间
        
        # 返回模拟结果
        return jsonify({
            "success": True,
            "shot_index": shot_index,
            "status": "completed",
            "video_path": f"/static/generated_videos/{title}/shot_{shot_index}.mp4",
            "thumbnail_path": f"/static/generated_videos/{title}/shot_{shot_index}_thumb.jpg",
            "message": f"镜头 #{shot_index} 生成成功（模拟）"
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 生成镜头失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/export-storyboard', methods=['POST'])
@login_required
def export_storyboard():
    """
    导出分镜头脚本
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series"
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        logger.info(f"📄 [VIDEO] 导出分镜头: {title} - {video_type}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 使用现有的转换API
        from src.managers.VideoAdapterManager import VideoAdapterManager
        
        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None
        
        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)
        
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type
        )
        
        # 保存文件
        video_projects_dir = Path("视频项目")
        safe_title = str(title).replace('/', '_').replace('\\', '_').replace(':', '_')
        project_dir = video_projects_dir / safe_title
        project_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_suffix = {
            "short_film": "短片",
            "long_series": "剧集",
            "short_video": "短视频"
        }[video_type]
        
        output_file = project_dir / f"{safe_title}_{type_suffix}分镜头_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_result, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            "success": True,
            "output_file": str(output_file),
            "message": "分镜头脚本导出成功"
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 导出失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/convert', methods=['POST'])
@login_required
def convert_novel_to_video():
    """
    将已生成的小说转换为视频分镜头脚本（支持三种类型）
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",  // short_film | long_series | short_video
        "total_units": null,          // 可选，集数/视频数
        "output_format": "detailed"   // simple | detailed
    }
    """
    try:
        data = request.json or {}
        
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        total_units = data.get('total_units')
        output_format = data.get('output_format', 'detailed')
        
        # 参数验证
        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400
        
        if video_type not in ['short_film', 'long_series', 'short_video']:
            return jsonify({
                "success": False, 
                "error": f"不支持的视频类型: {video_type}",
                "supported_types": ["short_film", "long_series", "short_video"]
            }), 400
        
        logger.info(f"🎬 [VIDEO] 开始将小说转换为【{video_type}】: {title}")
        logger.info(f"📊 [VIDEO] 参数: type={video_type}, format={output_format}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 1. 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 2. 检查是否已完成第一阶段
        quality_data = novel_detail.get("quality_data", {})
        has_phase_one = bool(quality_data) or bool(novel_detail.get("core_worldview"))
        
        if not has_phase_one:
            return jsonify({
                "success": False,
                "error": "小说尚未完成第一阶段设定，请先生成完整的小说设定"
            }), 400
        
        # 3. 导入视频适配器
        try:
            from src.managers.VideoAdapterManager import VideoAdapterManager
        except ImportError as e:
            logger.error(f"无法导入VideoAdapterManager: {e}")
            return jsonify({"success": False, "error": "视频适配器模块不可用"}), 500
        
        # 4. 创建适配器并执行转换
        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None
        
        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)
        
        logger.info(f"🔄 [VIDEO] 开始转换...")
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type,
            total_units=total_units
        )
        
        # 5. 保存结果
        video_projects_dir = Path("视频项目")
        video_projects_dir.mkdir(exist_ok=True)
        
        safe_title = title.replace('/', '_').replace('\\', '_').replace(':', '_')
        project_dir = video_projects_dir / safe_title
        project_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_suffix = {
            "short_film": "短片",
            "long_series": "剧集",
            "short_video": "短视频"
        }[video_type]
        
        output_file = project_dir / f"{safe_title}_{type_suffix}分镜头_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(video_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ [VIDEO] 分镜头脚本已保存: {output_file}")
        
        # 6. 根据输出格式返回结果
        if output_format == 'simple':
            # 简化格式
            units = video_result.get("units", [])
            total_duration = sum(
                unit.get("storyboard", {}).get("total_duration_minutes", 0)
                for unit in units
            )
            
            result = {
                "success": True,
                "series_info": video_result.get("series_info"),
                "video_type": video_type,
                "video_type_name": video_result.get("video_type_name"),
                "total_units": len(units),
                "total_duration_minutes": round(total_duration, 1),
                "output_file": str(output_file)
            }
        else:
            # 详细格式
            result = {
                "success": True,
                "data": video_result,
                "output_file": str(output_file)
            }
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 转换失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/preview/<title>/<video_type>/<int:unit_num>', methods=['GET'])
@login_required
def preview_video_unit(title, video_type, unit_num):
    """
    预览单个单元（集/视频）的分镜头脚本
    
    参数：
    - title: 小说标题
    - video_type: 视频类型
    - unit_num: 单元编号（集数/视频序号）
    """
    try:
        logger.info(f"🎬 [VIDEO] 预览 {video_type} 第{unit_num}个单元: {title}")
        
        if video_type not in ['short_film', 'long_series', 'short_video']:
            return jsonify({"success": False, "error": "无效的视频类型"}), 400
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据并转换
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 导入并转换
        try:
            from src.managers.VideoAdapterManager import VideoAdapterManager
        except ImportError as e:
            return jsonify({"success": False, "error": "视频适配器模块不可用"}), 500
        
        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None
        
        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)
        
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type
        )
        
        # 提取指定单元
        units = video_result.get("units", [])
        target_unit = None
        
        for unit in units:
            if unit.get("unit_number") == unit_num:
                target_unit = unit
                break
        
        if not target_unit:
            return jsonify({
                "success": False,
                "error": f"第{unit_num}个单元不存在",
                "available_units": [unit.get("unit_number") for unit in units]
            }), 404
        
        return jsonify({
            "success": True,
            "unit": target_unit,
            "series_info": video_result.get("series_info"),
            "visual_style_guide": video_result.get("visual_style_guide"),
            "pacing_guidelines": video_result.get("pacing_guidelines")
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 预览失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/export/<title>/<video_type>/<int:unit_num>', methods=['GET'])
@login_required
def export_video_unit(title, video_type, unit_num):
    """
    导出单个单元的分镜头脚本为Markdown格式
    
    参数：
    - title: 小说标题
    - video_type: 视频类型
    - unit_num: 单元编号
    """
    try:
        logger.info(f"📄 [VIDEO] 导出 {video_type} 第{unit_num}个单元Markdown: {title}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据并转换
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        try:
            from src.managers.VideoAdapterManager import VideoAdapterManager
        except ImportError as e:
            return jsonify({"success": False, "error": "视频适配器模块不可用"}), 500
        
        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None
        
        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)
        
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type
        )
        
        # 提取指定单元
        units = video_result.get("units", [])
        target_unit = None
        
        for unit in units:
            if unit.get("unit_number") == unit_num:
                target_unit = unit
                break
        
        if not target_unit:
            return jsonify({"success": False, "error": f"第{unit_num}个单元不存在"}), 404
        
        # 生成Markdown
        markdown_content = _generate_unit_markdown(
            target_unit,
            video_result.get("series_info", {}),
            video_result.get("visual_style_guide", {}),
            video_result.get("pacing_guidelines", {}),
            video_type
        )
        
        # 保存文件
        video_projects_dir = Path("视频项目")
        safe_title = title.replace('/', '_').replace('\\', '_').replace(':', '_')
        project_dir = video_projects_dir / safe_title
        project_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        type_suffix = {
            "short_film": "短片",
            "long_series": "剧集",
            "short_video": "短视频"
        }[video_type]
        
        markdown_file = project_dir / f"{type_suffix}_{unit_num}_分镜头脚本_{timestamp}.md"
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        return jsonify({
            "success": True,
            "markdown_file": str(markdown_file),
            "content_preview": markdown_content[:500] + "..." if len(markdown_content) > 500 else markdown_content
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 导出失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _generate_unit_markdown(unit, series_info, style_guide, pacing, video_type):
    """生成单元的Markdown格式分镜头脚本"""
    
    series_title = series_info.get("title", "未命名")
    unit_num = unit.get("unit_number", 1)
    unit_type = unit.get("unit_type", "未知")
    
    storyboard = unit.get("storyboard", {})
    scenes = storyboard.get("scenes", [])
    total_duration = storyboard.get("total_duration_minutes", 0)
    
    # 根据视频类型选择标题格式
    if video_type == "short_film":
        title_line = f"# {series_title} - 短片分镜头脚本"
    elif video_type == "short_video":
        title_line = f"# {series_title} - 第{unit_num}个短视频"
    else:
        title_line = f"# {series_title} - 第{unit_num}集分镜头脚本"
    
    md = f"""{title_line}

## 基本信息
- **类型**: {unit_type}
- **编号**: {unit_num}
- **预估时长**: {total_duration}分钟
- **场景数量**: {len(scenes)}场

---

"""
    
    # 添加节奏指导
    if pacing:
        md += "## 节奏指导\n\n"
        for key, value in pacing.items():
            md += f"- **{key}**: {value}\n"
        md += "\n---\n\n"
    
    # 添加每个场景
    for scene in scenes:
        scene_num = scene.get("scene_number", 1)
        scene_title = scene.get("scene_title", "未命名场景")
        scene_desc = scene.get("scene_description", "")
        scene_duration = scene.get("estimated_duration_minutes", 0)
        
        md += f"## 场景 {scene_num}: {scene_title}\n\n"
        md += f"**时长**: {scene_duration}分钟  \n"
        md += f"**描述**: {scene_desc}  \n\n"
        
        # 添加镜头序列
        shots = scene.get("shot_sequence", [])
        if shots:
            md += "### 镜头序列\n\n"
            md += "| 镜头号 | 景别 | 运镜 | 时长 | 描述 | 音频 |\n"
            md += "|--------|------|------|------|------|------|\n"
            
            for shot in shots:
                shot_num = shot.get("shot_number", "-")
                shot_type = shot.get("shot_type", "-")
                movement = shot.get("camera_movement", "-")
                duration = shot.get("duration_seconds", "-")
                desc = shot.get("description", "-")
                audio = shot.get("audio_note", shot.get("tiktok_note", "-"))
                
                md += f"| {shot_num} | {shot_type} | {movement} | {duration}秒 | {desc} | {audio} |\n"
            
            md += "\n"
        
        # 添加视觉备注
        visual_notes = scene.get("visual_notes", {})
        if visual_notes:
            md += "### 视觉设计\n\n"
            md += f"- **色彩**: {visual_notes.get('color_palette', '-')}\n"
            md += f"- **灯光**: {visual_notes.get('lighting', '-')}\n"
            md += f"- **构图**: {visual_notes.get('composition_style', '-')}\n\n"
        
        md += "---\n\n"
    
    return md


@video_api.route('/video/generate-character-portrait', methods=['POST'])
@login_required
def generate_character_portrait():
    """
    生成角色剧照
    
    请求参数：
    {
        "title": "小说标题",
        "character_id": "character_0",
        "character_data": {...},  // 完整的角色数据
        "aspect_ratio": "16:9",    // 可选，默认16:9
        "image_size": "4K"         // 可选，默认4K
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        character_id = data.get('character_id')
        character_data = data.get('character_data', {})
        aspect_ratio = data.get('aspect_ratio', '9:16')  # 默认竖屏，适合角色展示
        image_size = data.get('image_size', '4K')
        
        logger.info(f"🎨 [VIDEO] ===== 开始生成角色剧照 =====")
        logger.info(f"📝 [VIDEO] 请求参数:")
        logger.info(f"  - 小说标题: {title}")
        logger.info(f"  - 角色ID: {character_id}")
        logger.info(f"  - 角色名称: {character_data.get('name', 'Unknown')}")
        logger.info(f"  - 角色定位: {character_data.get('role', 'Unknown')}")
        logger.info(f"  - 图片比例: {aspect_ratio}")
        logger.info(f"  - 图片质量: {image_size}")
        
        if not title or not character_id:
            logger.error(f"❌ [VIDEO] 缺少必需参数: title={title}, character_id={character_id}")
            return jsonify({"success": False, "error": "缺少必需参数: title 或 character_id"}), 400
        
        logger.info(f"🎨 [VIDEO] 生成角色剧照: {title} - {character_id}")
        
        # 使用EventExtractor生成剧照提示词
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        
        logger.info(f"🔧 [VIDEO] 开始生成角色提示词...")
        # 生成剧照提示词
        character_prompts = event_extractor.generate_character_prompts([character_data])
        
        if not character_prompts:
            logger.error(f"❌ [VIDEO] 生成角色提示词失败: character_prompts为空")
            return jsonify({"success": False, "error": "生成角色提示词失败"}), 500
        
        prompt = character_prompts[0].get('generation_prompt', '')
        logger.info(f"✅ [VIDEO] 角色提示词生成成功")
        logger.info(f"📝 [VIDEO] 提示词长度: {len(prompt)} 字符")
        logger.info(f"📝 [VIDEO] 提示词预览: {prompt[:200]}...")
        
        # 调用NanoBanana服务生成图像
        from web.services.nanobanana_service import NanoBananaService
        nanobanana_service = NanoBananaService()
        
        logger.info(f"🎨 [VIDEO] 准备调用NanoBanana服务...")
        # 生成文件名
        character_name = character_data.get('name', 'unknown')
        safe_name = character_name.replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{title}_{safe_name}_portrait_{timestamp}"
        logger.info(f"💾 [VIDEO] 生成文件名: {filename}")
        
        # 生成图像
        logger.info(f"🚀 [VIDEO] 调用NanoBanana.generate_image()...")
        logger.info(f"📤 [VIDEO] 请求参数:")
        logger.info(f"  - prompt长度: {len(prompt)}")
        logger.info(f"  - aspect_ratio: {aspect_ratio}")
        logger.info(f"  - image_size: {image_size}")
        logger.info(f"  - filename: {filename}")
        
        result = nanobanana_service.generate_image({
            'prompt': prompt,
            'aspect_ratio': aspect_ratio,
            'image_size': image_size,
            'save_filename': filename
        })
        
        logger.info(f"📥 [VIDEO] NanoBanana返回结果:")
        logger.info(f"  - success: {result.get('success')}")
        logger.info(f"  - local_path: {result.get('local_path', 'N/A')}")
        logger.info(f"  - url: {result.get('url', 'N/A')}")
        logger.info(f"  - file_size: {result.get('file_size', 'N/A')}")
        logger.info(f"  - error: {result.get('error', 'N/A')}")
        
        # 验证文件是否存在
        if result.get('success') and result.get('local_path'):
            import os
            if os.path.exists(result['local_path']):
                file_size = os.path.getsize(result['local_path'])
                logger.info(f"✅ [VIDEO] 文件验证成功: {result['local_path']} ({file_size} bytes)")
            else:
                logger.error(f"❌ [VIDEO] 文件不存在: {result['local_path']}")
        
        if result.get('success'):
            logger.info(f"✅ [VIDEO] 角色剧照生成成功: {result.get('local_path')}")
            # 构建HTTP访问路径（浏览器可访问）
            import urllib.parse
            image_filename = os.path.basename(result.get('local_path', ''))
            # URL编码文件名，处理中文和特殊字符
            encoded_filename = urllib.parse.quote(image_filename)
            image_url = f"/generated_images/{encoded_filename}"
            logger.info(f"🌐 [VIDEO] 图片访问URL: {image_url}")
            logger.info(f"🌐 [VIDEO] 原始文件名: {image_filename}")
            logger.info(f"🌐 [VIDEO] 编码后文件名: {encoded_filename}")
            
            return jsonify({
                "success": True,
                "image_path": result.get('local_path'),  # 本地路径（用于下载）
                "image_url": image_url,  # HTTP URL（用于浏览器显示）
                "prompt": prompt,
                "character_name": character_name,
                "message": f"角色 {character_name} 的剧照生成成功"
            })
        else:
            logger.error(f"❌ [VIDEO] 角色剧照生成失败: {result.get('error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"❌ [VIDEO] 生成角色剧照失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/character-details', methods=['GET'])
@login_required
def get_character_details():
    """
    获取角色详细信息（从选中事件中自动提取）
    
    查询参数：
    - title: 小说标题
    - character_id: 角色ID
    - selected_events: 选中的事件ID列表（可选）
    """
    try:
        title = request.args.get('title')
        character_id = request.args.get('character_id')
        
        if not title or not character_id:
            return jsonify({"success": False, "error": "缺少必需参数"}), 400
        
        logger.info(f"👤 [VIDEO] 获取角色详情: {title} - {character_id}")
        
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500
        
        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404
        
        # 提取角色设计
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)
        
        characters = event_extractor.extract_character_designs(novel_detail)
        
        # 查找指定角色
        target_character = None
        for char in characters:
            if char.get('name') == character_id or f"character_{characters.index(char)}" == character_id:
                target_character = char
                break
        
        if not target_character:
            return jsonify({"success": False, "error": "角色不存在"}), 404
        
        # 提取该角色参与的章节/事件
        character_events = []
        all_major_events = event_extractor.extract_all_major_events(novel_detail)
        
        for major_event in all_major_events:
            event_characters = major_event.get('characters', '')
            if target_character.get('name') in event_characters:
                character_events.append({
                    "event_name": major_event.get('name', major_event.get('title', '未命名')),
                    "chapter_range": major_event.get('chapter_range', ''),
                    "description": major_event.get('description', '')[:200]
                })
        
        # 生成剧照提示词
        character_prompts = event_extractor.generate_character_prompts([target_character])
        
        return jsonify({
            "success": True,
            "character": target_character,
            "related_events": character_events[:10],  # 最多返回10个相关事件
            "generation_prompt": character_prompts[0].get('generation_prompt', '') if character_prompts else '',
            "total_events": len(character_events)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 获取角色详情失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def register_video_routes(app):
    """注册视频生成API路由"""
    app.register_blueprint(video_api, url_prefix='/api')
    
    logger.info("=" * 60)
    logger.info("📋 已注册的视频生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'video' in rule.rule:
            logger.info(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.info("=" * 60)
    logger.info("视频生成API路由注册完成")