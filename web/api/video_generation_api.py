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
import re
from pathlib import Path
from datetime import datetime
import json

# 添加项目根目录到路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(BASE_DIR)

from src.utils.logger import get_logger
from src.core.APIClient import APIClient
from config.config import CONFIG

# 加载视频配置
def load_video_config():
    """加载视频生成配置"""
    try:
        from config.config import CONFIG
        return CONFIG.get("video_generation", {})
    except ImportError:
        # 如果无法导入，使用默认值
        return {
            "default_shot_duration": 8.0,
            "custom_video": {
                "short_film": {"shots_per_unit": 15, "avg_duration": 8.0},
                "long_series": {"shots_per_unit": 10, "avg_duration": 8.0},
                "short_video": {"shots_per_unit": 5, "avg_duration": 8.0}
            }
        }

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

# 初始化AI客户端（用于生成分镜头）
try:
    ai_client = APIClient(CONFIG)
    logger.info("✅ AI客户端初始化成功")
except Exception as e:
    logger.error(f"无法初始化AI客户端: {e}")
    ai_client = None


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
        logger.info(f"📊 [VIDEO] 当前加载的小说项目列表: {list(manager.novel_projects.keys()) if manager else 'N/A'}")

        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        # 获取小说数据 - 先尝试精确匹配
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            # 如果精确匹配失败，尝试模糊匹配
            logger.warn(f"⚠️ [VIDEO] 精确匹配失败，尝试模糊匹配: {title}")
            for available_title in manager.novel_projects.keys():
                if title.strip() == available_title.strip():
                    logger.info(f"✅ [VIDEO] 通过去除空白匹配成功: {available_title}")
                    novel_detail = manager.get_novel_detail(available_title)
                    break
                elif title.lower() == available_title.lower():
                    logger.info(f"✅ [VIDEO] 通过大小写不敏感匹配成功: {available_title}")
                    novel_detail = manager.get_novel_detail(available_title)
                    break
                elif title in available_title or available_title in title:
                    logger.info(f"✅ [VIDEO] 通过部分匹配成功: {available_title}")
                    novel_detail = manager.get_novel_detail(available_title)
                    break

        if not novel_detail:
            logger.error(f"❌ [VIDEO] 小说项目不存在: {title}")
            logger.error(f"❌ [VIDEO] 可用的小说: {list(manager.novel_projects.keys())}")
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

                            # 🔥 修复：生成复合ID，格式为 major_event_X_event_Y_Z
                            # 其中 X 是重大事件索引，Y 是阶段索引（在stage_order中的位置），Z 是该阶段中的子事件索引
                            stage_idx = stage_order.index(stage)
                            # 计算当前阶段中已经有多少个中级事件
                            medium_idx_in_stage = len([me for me in medium_events_list if me.get('stage') == stage])
                            medium_event_id = f"major_event_{idx}_event_{stage_idx}_{medium_idx_in_stage}"

                            medium_events_list.append({
                                "id": medium_event_id,
                                "title": event_title,
                                "description": medium_event.get("description", ""),
                                "stage": stage,
                                "stage_idx": stage_idx,
                                "medium_idx": medium_idx_in_stage,
                                "parent_id": f"major_event_{idx}",
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

        # 格式化角色数据 - 保留完整的角色设计信息用于剧照生成
        formatted_characters = []
        character_names = []  # 用于填充medium events
        for idx, character in enumerate(characters):
            char_name = character.get("name", f"角色 {idx + 1}")

            # 构建完整的角色数据结构
            formatted_char = {
                "id": f"character_{idx}",
                "name": char_name,
                "role": character.get("role", ""),
                # 详细的外形描述
                "description": character.get("description", ""),
                "appearance": character.get("appearance", ""),
                "age": character.get("age", ""),
                "gender": character.get("gender", ""),
                "personality": character.get("personality", ""),
                # 从角色设计文件中提取的详细字段
                "initial_state": character.get("initial_state", {}),
                "living_characteristics": character.get("living_characteristics", {}),
                "soul_matrix": character.get("soul_matrix", []),
                "background": character.get("background", ""),
                "appearing_event": character.get("appearing_event", "")
            }
            formatted_characters.append(formatted_char)
            character_names.append(char_name)

        # 🔥 修复：将角色列表添加到每个medium event，这样前端可以提取
        for event in events:
            if event.get("children"):
                for child in event["children"]:
                    # 如果medium event没有characters字段，添加全局角色列表（用逗号分隔）
                    if not child.get("characters"):
                        child["characters"] = ",".join(character_names)

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
    import re

    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        selected_events = data.get('selected_events', [])
        selected_characters = data.get('selected_characters', [])

        # 🔥 规范化 selected_characters 格式（可能是字符串列表或字典列表）
        normalized_characters = []
        for char in selected_characters:
            if isinstance(char, str):
                normalized_characters.append({"name": char, "role": "选中角色"})
            elif isinstance(char, dict):
                normalized_characters.append(char)
        selected_characters = normalized_characters

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
                    # 🔥 修复：处理复合ID格式（major_event_X_event_Y_Z）
                    # 复合ID应该有格式：major_event_数字_event_数字_数字
                    # 检查是否有两个 _event_ 或者 _event_ 出现在 major_event_ 之后
                    if selected_event.startswith('major_event_') and selected_event.count('_event_') >= 2:
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
                                logger.warn(f"⚠️ [VIDEO] 无法在复合ID '{selected_event}' 中找到子事件，直接使用父事件")
                                # 🔥 修复：如果找不到子事件，展开父事件的所有中级事件
                                medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
                                for medium_event in medium_events_from_extractor:
                                    medium_event_copy = dict(medium_event)
                                    medium_event_copy["parent_major"] = major_event.get("name", major_event.get("title", ""))
                                    expanded_events.append(medium_event_copy)
                        else:
                            logger.warn(f"⚠️ [VIDEO] 无法在复合ID '{selected_event}' 中找到父事件 '{parent_id}'，尝试从索引提取")
                            # 🔥 修复：尝试从parent_id中提取索引直接访问
                            try:
                                parent_idx = int(parent_id.replace("major_event_", ""))
                                if 0 <= parent_idx < len(all_major_events):
                                    major_event = all_major_events[parent_idx]
                                    medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
                                    for medium_event in medium_events_from_extractor:
                                        medium_event_copy = dict(medium_event)
                                        medium_event_copy["parent_major"] = major_event.get("name", major_event.get("title", ""))
                                        expanded_events.append(medium_event_copy)
                                    logger.info(f"📊 [VIDEO] 通过索引 {parent_idx} 成功找到父事件并展开")
                                else:
                                    logger.error(f"❌ [VIDEO] 索引 {parent_idx} 超出范围 [0, {len(all_major_events)})")
                            except (ValueError, IndexError) as e:
                                logger.error(f"❌ [VIDEO] 无法从 '{parent_id}' 提取有效索引: {e}")

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
                            # 🔥 修复：尝试从selected_event中提取索引作为备用方案
                            logger.warn(f"⚠️ [VIDEO] 未找到ID为 '{selected_event}' 的事件，尝试从索引提取")
                            try:
                                # 尝试从 major_event_X 格式中提取索引
                                event_idx = int(selected_event.replace("major_event_", "").replace("event_", ""))
                                if 0 <= event_idx < len(all_major_events):
                                    major_event = all_major_events[event_idx]
                                    medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
                                    for medium_event in medium_events_from_extractor:
                                        medium_event_copy = dict(medium_event)
                                        medium_event_copy["parent_major"] = major_event.get("name", major_event.get("title", ""))
                                        expanded_events.append(medium_event_copy)
                                    logger.info(f"📊 [VIDEO] 通过索引 {event_idx} 成功展开重大事件")
                                else:
                                    logger.error(f"❌ [VIDEO] 索引 {event_idx} 超出范围 [0, {len(all_major_events)})")
                            except (ValueError, IndexError) as e:
                                logger.error(f"❌ [VIDEO] 无法从 '{selected_event}' 提取有效索引: {e}")
                
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
        
        # 🔥 如果没有选中角色，从角色设计和事件中自动提取角色
        if not selected_characters:
            # 第一步：从角色设计中获取所有已知角色
            from src.managers.EventExtractor import get_event_extractor
            event_extractor = get_event_extractor(logger)
            all_character_designs = event_extractor.extract_character_designs(novel_detail)

            logger.info(f"👥 [VIDEO] 从角色设计中提取到 {len(all_character_designs)} 个角色")

            # 第二步：收集事件中的所有文本（用于检查角色是否参与）
            event_text_parts = []
            for event in selected_events:
                for field in ["description", "main_goal", "role_in_stage_arc", "title", "plot_outline"]:
                    field_value = event.get(field, "")
                    if field_value:
                        # 如果是列表，合并所有元素
                        if isinstance(field_value, list):
                            event_text_parts.extend([str(item) for item in field_value])
                        else:
                            event_text_parts.append(str(field_value))

                # 检查 characters 字段
                event_characters = event.get("characters", "")
                if event_characters:
                    event_text_parts.append(str(event_characters))

            # 合并所有文本
            all_text = " ".join(event_text_parts)

            # 第三步：构建角色列表
            # 策略：优先选择在事件文本中出现的角色，然后按角色重要性排序
            character_candidates = []

            for char_design in all_character_designs:
                char_name = char_design.get("name", "")
                if not char_name:
                    continue

                # 检查角色是否在事件文本中出现
                appears_in_events = char_name in all_text

                character_candidates.append({
                    "name": char_name,
                    "role": char_design.get("role_type", char_design.get("role", "角色")),
                    "description": char_design.get("description", char_design.get("background", char_design.get("core_personality", "")))[:200],
                    "appears_in_events": appears_in_events,
                    "full_data": char_design
                })

            # 按优先级排序：
            # 1. 在事件中出现的角色优先
            # 2. 按角色重要性排序（主角 > 重要角色 > 配角）
            role_priority = {
                "主角": 0,
                "核心盟友": 1,
                "核心反派": 2,
                "重要角色": 3,
                "重要配角": 4,
                "配角": 5,
                "角色": 6
            }

            def get_priority(char):
                role = char.get("role", "角色")
                base_priority = role_priority.get(role, 99)
                # 如果在事件中出现，优先级提高
                if char.get("appears_in_events"):
                    base_priority -= 10
                return base_priority

            character_candidates.sort(key=get_priority)

            # 构建最终的角色列表
            for char in character_candidates:
                selected_characters.append({
                    "name": char["name"],
                    "role": char["role"],
                    "description": char["description"]
                })

            # 最多20个角色
            selected_characters = selected_characters[:20]

            # 统计参与角色数量
            active_count = sum(1 for c in character_candidates[:len(selected_characters)] if c.get("appears_in_events"))

            logger.info(f"👥 [VIDEO] 提取到 {len(selected_characters)} 个角色（其中 {active_count} 个在事件中出现）")
            if selected_characters:
                logger.info(f"👥 [VIDEO] 角色列表: {[c['name'] + '(' + c.get('role', '角色') + ')' for c in selected_characters[:8]]}...")
        
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


def _filter_selected_events(all_events: List[Dict], selected_event_ids: List[str], logger) -> List[Dict]:
    """
    过滤出用户选中的事件（支持重大事件和中级事件）
    
    Args:
        all_events: 所有重大事件列表
        selected_event_ids: 选中的事件ID列表（可能包含重大事件ID或中级事件ID）
        logger: 日志记录器
    
    Returns:
        过滤后的事件列表（只包含选中的事件）
    """
    filtered_events = []
    selected_medium_events_map = {}  # 🔥 用map来跟踪每个事件选中的中级事件
    
    logger.debug(f"🔍 开始过滤事件，选中事件ID列表: {selected_event_ids}")
    
    # 第一遍：收集所有选中的中级事件
    for idx, major_event in enumerate(all_events):
        major_event_id = f"major_event_{idx}"
        major_event_id_alt = f"event_{idx}"
        major_event_name = major_event.get("name", major_event.get("title", ""))
        
        logger.debug(f"  检查事件 {idx}: {major_event_name} (ID: {major_event_id}, {major_event_id_alt})")
        
        # 检查是否选中了这个重大事件（通过ID或名称）
        major_selected = (
            major_event_id in selected_event_ids or
            major_event_id_alt in selected_event_ids or
            major_event_name in selected_event_ids
        )
        
        # 检查是否有选中的中级事件
        composition = major_event.get("composition", {})
        event_selected_medium = []
        
        logger.debug(f"    检查composition中的中级事件...")
        
        for stage_idx, stage in enumerate(["起", "承", "转", "合", "起因", "发展", "高潮", "结局"]):
            medium_events = composition.get(stage, [])
            if not isinstance(medium_events, list):
                continue
            
            logger.debug(f"      Stage '{stage}': {len(medium_events)} 个中级事件")
            
            for medium_idx, medium_event in enumerate(medium_events):
                # 生成中级事件的可能ID格式（与前端保持一致）
                # 前端生成格式: major_event_X_event_Y_Z
                # 其中X是父事件索引，Y是阶段索引（在阶段列表中的位置），Z是该阶段中的中级事件索引
                
                # 注意：前端生成ID时使用的阶段索引可能与我们遍历的stage_idx不同
                # 让我们尝试多种可能的格式
                medium_event_id = f"{major_event_id}_event_{stage_idx}_{medium_idx}"
                medium_event_id_alt = f"{major_event_id_alt}_event_{stage_idx}_{medium_idx}"
                medium_event_id_alt2 = f"{major_event_id_alt}_{medium_idx}"
                
                # 检查是否被选中
                if (medium_event_id in selected_event_ids or
                    medium_event_id_alt in selected_event_ids or
                    medium_event_id_alt2 in selected_event_ids):
                    event_selected_medium.append(medium_event)
                    logger.debug(f"  ✅ 选中中级事件: {medium_event.get('name', medium_event.get('title', '未命名'))} (stage={stage}, stage_idx={stage_idx}, medium_idx={medium_idx}, matched_id={medium_event_id})")
        
        # 保存到map中
        if event_selected_medium:
            selected_medium_events_map[idx] = event_selected_medium
            logger.info(f"  📊 事件 {idx} ({major_event_name}): 找到 {len(event_selected_medium)} 个选中的中级事件")
    
    # 第二遍：根据选中的事件构建过滤后的列表
    for idx, major_event in enumerate(all_events):
        major_event_id = f"major_event_{idx}"
        major_event_id_alt = f"event_{idx}"
        major_event_name = major_event.get("name", major_event.get("title", ""))
        
        # 检查是否选中了这个重大事件（通过ID或名称）
        major_selected = (
            major_event_id in selected_event_ids or
            major_event_id_alt in selected_event_ids or
            major_event_name in selected_event_ids
        )
        
        # 如果选中了整个重大事件
        if major_selected:
            filtered_events.append(major_event)
            logger.info(f"  ✅ 选中重大事件: {major_event_name}")
        
        # 如果有选中的中级事件
        elif idx in selected_medium_events_map:
            selected_medium_events = selected_medium_events_map[idx]
            composition = major_event.get("composition", {})
            
            # 创建一个新的重大事件对象，只保留选中的中级事件
            filtered_major = dict(major_event)
            new_composition = {}
            for stage in ["起", "承", "转", "合", "起因", "发展", "高潮", "结局"]:
                medium_events = composition.get(stage, [])
                if isinstance(medium_events, list):
                    # 过滤出选中的中级事件
                    filtered = [e for e in medium_events if e in selected_medium_events]
                    if filtered:
                        new_composition[stage] = filtered
            filtered_major["composition"] = new_composition
            filtered_events.append(filtered_major)
            logger.info(f"  ✅ 部分选中重大事件: {major_event_name} (包含 {len(selected_medium_events)} 个中级事件)")
    
    return filtered_events


@video_api.route('/video/generate-storyboard', methods=['POST'])
@login_required
def generate_storyboard():
    """
    生成分镜头脚本（包含角色设计提取）
    
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",
        "selected_events": ["event_0", "event_1", ...]  // 可选：选中的事件ID列表
    }
    
    工作流程：
    1. 提取重大事件（如果指定了selected_events，只提取选中的事件）
    2. 提取角色设计
    3. 生成分镜头脚本
    4. 生成角色剧照生成提示词
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        selected_events = data.get('selected_events', [])  # 🔥 新增：获取选中事件列表
        
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

        # 🔥 如果指定了选中事件，只处理选中的
        if selected_events:
            logger.info(f"🎯 [VIDEO] 用户选中了 {len(selected_events)} 个事件，过滤中...")
            all_events = _filter_selected_events(all_events, selected_events, logger)

        logger.info(f"📊 [VIDEO] 最终处理 {len(all_events)} 个事件")

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

        # 🔥 传递过滤后的事件列表
        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type,
            filtered_events=all_events  # 🔥 新增参数
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
                    # 🔥 直接使用镜头描述，专注于视频画面本身
                    generation_prompt = shot.get('description', shot.get('veo_prompt', ''))

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
                        "veo_prompt": generation_prompt,  # 🔥 直接使用镜头描述
                        "screen_action": shot.get("description", ""),  # 保留兼容字段
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
    基于自定义提示词生成分镜头脚本（使用AI动态生成）
    
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
        # 从配置文件读取或使用默认值
        video_config = load_video_config()
        custom_config = video_config.get("custom_video", {})
        default_duration = video_config.get("default_shot_duration", 8.0)
        
        type_configs = {
            "short_film": {
                "name": "短片/动画电影",
                "default_units": 1,
                "shots_per_unit": custom_config.get("short_film", {}).get("shots_per_unit", 15),
                "avg_duration": custom_config.get("short_film", {}).get("avg_duration", default_duration)
            },
            "long_series": {
                "name": "长篇剧集",
                "default_units": 3,
                "shots_per_unit": custom_config.get("long_series", {}).get("shots_per_unit", 10),
                "avg_duration": custom_config.get("long_series", {}).get("avg_duration", default_duration)
            },
            "short_video": {
                "name": "短视频系列",
                "default_units": 5,
                "shots_per_unit": custom_config.get("short_video", {}).get("shots_per_unit", 5),
                "avg_duration": custom_config.get("short_video", {}).get("avg_duration", default_duration)
            }
        }
        
        config = type_configs.get(video_type, type_configs["long_series"])
        logger.info(f"📋 [VIDEO] 使用配置的镜头时长: {config['avg_duration']}秒")
        
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
            
            # 🔥 为每个单元单独调用AI生成镜头描述
            logger.info(f"🎬 [VIDEO] 开始生成第{unit_number}个单元的镜头...")
            unit_shot_descriptions = _generate_ai_shot_descriptions(
                prompt,
                config["shots_per_unit"],
                video_type
            )
            
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
            
            # 🔥 使用AI生成的描述创建镜头序列
            for shot_idx in range(config["shots_per_unit"]):
                shot_number = shot_idx + 1
                shot_description = unit_shot_descriptions[shot_idx]  # 🔥 使用AI生成的描述
                
                shot = {
                    "shot_number": shot_number,
                    "shot_type": _get_default_shot_type(shot_idx, config["shots_per_unit"]),
                    "camera_movement": _get_default_camera_movement(shot_idx),
                    "duration_seconds": config["avg_duration"],
                    "description": shot_description,
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
        
        # 🔥 保存分镜头到文件
        from pathlib import Path
        video_projects_dir = Path("视频项目")
        video_projects_dir.mkdir(exist_ok=True)
        
        # 使用时间戳创建项目名称
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c for c in prompt[:20] if c.isalnum() or c in (' ', '-', '_')).strip()
        project_name = f"自定义视频_{safe_prompt}_{timestamp}"
        project_dir = video_projects_dir / project_name
        project_dir.mkdir(exist_ok=True)
        
        # 保存完整的分镜头JSON
        storyboard_file = project_dir / f"分镜头脚本_{timestamp}.json"
        with open(storyboard_file, 'w', encoding='utf-8') as f:
            json.dump(video_result, f, ensure_ascii=False, indent=2)
        
        logger.info(f"💾 [VIDEO] 分镜头已保存: {storyboard_file}")
        
        # 生成Markdown格式的分镜头脚本
        markdown_content = _generate_custom_storyboard_markdown(video_result, prompt, video_type)
        markdown_file = project_dir / f"分镜头脚本_{timestamp}.md"
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"📄 [VIDEO] Markdown分镜头已保存: {markdown_file}")
        
        return jsonify({
            "success": True,
            "storyboard": video_result,
            "shots": shots,
            "total_shots": len(shots),
            "project_dir": str(project_dir),
            "storyboard_file": str(storyboard_file),
            "markdown_file": str(markdown_file),
            "message": f"已生成 {len(shots)} 个分镜头，已保存到 {project_name}"
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


def _generate_ai_shot_descriptions(prompt: str, shot_count: int, video_type: str) -> List[str]:
    """
    使用AI为每个镜头生成独特的描述
    
    🔥 重要：此函数使用专用的视频生成API调用，不使用小说的APIClient
    以避免"番茄小说风格"等不相关的提示词干扰
    
    Args:
        prompt: 用户输入的原始提示词
        shot_count: 需要生成的镜头数量
        video_type: 视频类型
    
    Returns:
        镜头描述列表
    """
    try:
        logger.info(f"🤖 [VIDEO] 调用AI生成{shot_count}个独特的镜头描述...")
        
        # 🔥 使用专用的视频生成API调用，避免小说风格干扰
        try:
            import sys
            import importlib.util
            from pathlib import Path
            
            # 确保项目根目录在路径中
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            # 使用importlib动态导入config.py
            config_path = project_root / "config" / "config.py"
            spec = importlib.util.spec_from_file_location("config_module", config_path)
            if spec is not None and spec.loader is not None:
                config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(config_module)
                api_config = config_module.CONFIG
                logger.info(f"✅ [VIDEO] 配置加载成功，默认提供商: {api_config.get('default_provider', 'unknown')}")
            else:
                raise ImportError("无法创建config模块规格")
            
            # 🔥 关键修复：直接调用底层API，不使用APIClient（它会添加小说风格提示词）
            # 获取API配置
            provider = api_config.get('default_provider', 'gemini')
            provider_config = api_config.get('providers', {}).get(provider, {})
            api_key = provider_config.get('api_key', '')
            api_url = provider_config.get('api_url', '')
            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            
            if not api_key or not api_url:
                raise ValueError("API配置不完整")
            
            logger.info(f"🔧 [VIDEO] 使用配置: provider={provider}, model={model}")
            
            # 🔥 构建专用的视频生成提示词（不包含任何小说风格相关内容）
            type_guide = {
                "short_film": "短片风格：每个镜头应该富有电影感，注重视觉美学和艺术性",
                "long_series": "剧集风格：镜头应该叙事清晰，节奏适中，注重故事连贯性",
                "short_video": "短视频风格：镜头应该节奏快，视觉冲击力强，前3秒必须有钩子"
            }.get(video_type, "标准视频风格")
            
            ai_prompt = f"""你是一位专业的视频导演和分镜头设计师。请基于以下提示词，生成{shot_count}个独特的镜头描述。

【原始提示词】
{prompt}

【关键要求】
1. 🎯 必须生成恰好 {shot_count} 个镜头，不能多也不能少
2. 每个镜头时长：10秒
3. 视频风格：{type_guide}
4. 镜头之间要有连贯性和递进关系
5. 第1个镜头：开场建立场景，使用全景或大远景
6. 第{shot_count}个镜头：结尾收束，使用全景或远景
7. 中间镜头：逐步推进叙事，展示不同角度和细节变化

【输出格式】
请严格按照以下格式输出，每个镜头一行：
镜头1：[详细的视觉描述，包含场景、角度、动作、氛围]
镜头2：[详细的视觉描述，包含场景、角度、动作、氛围]
镜头3：[详细的视觉描述，包含场景、角度、动作、氛围]
镜头4：[详细的视觉描述，包含场景、角度、动作、氛围]
镜头5：[详细的视觉描述，包含场景、角度、动作、氛围]
...
镜头{shot_count}：[详细的视觉描述，包含场景、角度、动作、氛围]

【示例】（假设需要生成10个镜头）
镜头1：赛博朋克风格的未来城市夜景，霓虹灯闪烁的全景镜头，无人机俯瞰视角
镜头2：街道上穿着潮鞋的年轻人脚步特写，踏过积水的水花飞溅慢动作
镜头3：侧面跟拍镜头，霓虹灯光扫过角色的脸部，表情坚毅
镜头4：第一人称主观视角快速切换，展示都市生活的多面性
镜头5：中景镜头，角色与环境的互动，展现城市脉搏
镜头6：近景特写，捕捉关键细节和情感瞬间
镜头7：运镜环绕展示，呈现角色与场景的立体关系
镜头8：动态跟拍镜头，跟随角色行动的节奏变化
镜头9：高角度俯拍，展现城市建筑的几何美感
镜头10：十字路口大远景拉升，角色走向未知的远方

【重要提醒】
⚠️ 必须生成完整的 {shot_count} 个镜头
⚠️ 每个镜头的描述必须独特且具体（至少20个汉字）
⚠️ 描述应该可以直接用于AI视频生成工具
⚠️ 避免重复的词汇和句式
⚠️ 确保视觉叙事的连贯性和递进性"""

            # 🔥 直接调用API（不使用APIClient，避免小说风格干扰）
            logger.info(f"📡 [VIDEO] 发起AI请求（直接API调用，避开小说风格系统）...")
            logger.info(f"📡 [VIDEO] API URL: {api_url}")
            logger.info(f"📡 [VIDEO] Model: {model}")
            
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一位专业的视频导演，擅长创作富有视觉冲击力的分镜头脚本。"
                    },
                    {
                        "role": "user",
                        "content": ai_prompt
                    }
                ],
                "temperature": 0.8,
                "stream": False
            }
            
            logger.info(f"📡 [VIDEO] 请求载荷大小: {len(str(payload))} 字符")
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=120)
            
            if response.status_code == 200:
                result_json = response.json()
                # 提取生成的文本
                if 'choices' in result_json and len(result_json['choices']) > 0:
                    result = result_json['choices'][0].get('message', {}).get('content', '')
                else:
                    result = str(result_json)
                
                logger.info(f"✅ [VIDEO] API响应成功，长度: {len(result)}字符")
                # 解析AI返回的镜头描述
                logger.info(f"✅ [VIDEO] AI响应成功，长度: {len(result)}字符")
                logger.info(f"📋 [VIDEO] 原始响应预览:")
                logger.info(f"{result[:800]}...")  # 显示前800字符
                
                descriptions = []
                
                # 方法1：按行分割解析
                lines = result.split('\n')
                logger.info(f"📊 [VIDEO] 响应被分割为 {len(lines)} 行")
                
                for line_idx, line in enumerate(lines):
                    line = line.strip()
                    if line:  # 跳过空行
                        # 匹配 "镜头1：" 或 "镜头1." 或 "镜头1、" 等格式
                        match = re.match(r'^镜头\s*(\d+)[:：.,、]\s*(.+)', line)
                        if match:
                            shot_num = int(match.group(1))
                            description = match.group(2).strip()
                            if description and len(description) >= 10:  # 至少10个字符
                                # 确保按顺序添加
                                while len(descriptions) < shot_num - 1:
                                    descriptions.append("")  # 填充空位
                                if shot_num - 1 < len(descriptions):
                                    descriptions[shot_num - 1] = description
                                else:
                                    descriptions.append(description)
                                logger.info(f"    ✅ 提取镜头{shot_num}: {description[:40]}...")
                        else:
                            # 尝试其他可能的格式
                            logger.debug(f"    ⚠️ 不匹配标准格式: {line[:60]}...")
                
                # 方法2：如果没有找到标准格式，尝试查找所有包含"镜头"关键词的行
                if len(descriptions) < shot_count:
                    logger.info(f"🔄 [VIDEO] 标准格式只找到{len(descriptions)}个，尝试备用解析...")
                    for line in lines:
                        line = line.strip()
                        if '镜头' in line and len(line) > 20:
                            # 提取冒号后的内容
                            if '：' in line or ':' in line:
                                parts = re.split(r'[:：]', line, 1)
                                if len(parts) == 2 and parts[1].strip():
                                    desc = parts[1].strip()
                                    if desc not in descriptions and len(desc) >= 10:
                                        descriptions.append(desc)
                                        logger.info(f"    ✅ 备用提取: {desc[:40]}...")
                
                # 清理空描述
                descriptions = [d for d in descriptions if d and len(d) >= 10]
                
                logger.info(f"📊 [VIDEO] 最终解析到 {len(descriptions)} 个镜头描述")
                
                # 如果AI生成的数量足够，返回
                if len(descriptions) >= shot_count:
                    logger.info(f"✅ [VIDEO] AI成功生成{len(descriptions)}个镜头描述，使用前{shot_count}个")
                    return descriptions[:shot_count]
                else:
                    logger.info(f"⚠️ [VIDEO] AI只生成了{len(descriptions)}个镜头，需要{shot_count}个，使用备用方案补充")
                    # 使用备用方案补充
                    fallback = _generate_fallback_shot_descriptions(prompt, shot_count - len(descriptions), video_type)
                    # 合并AI生成的和备用生成的
                    return descriptions + fallback
            
        except FileNotFoundError:
            logger.info("⚠️ [VIDEO] 配置文件未找到，使用备用方案")
        except json.JSONDecodeError as e:
            logger.info(f"⚠️ [VIDEO] 配置文件解析失败: {e}，使用备用方案")
        except ImportError as e:
            logger.info(f"⚠️ [VIDEO] 无法导入APIClient: {e}，使用备用方案")
        except Exception as api_error:
            logger.info(f"⚠️ [VIDEO] API调用失败: {api_error}，使用备用方案")
        
        # 使用备用方案
        return _generate_fallback_shot_descriptions(prompt, shot_count, video_type)
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] AI生成失败: {e}，使用备用方案")
        return _generate_fallback_shot_descriptions(prompt, shot_count, video_type)


def _generate_fallback_shot_descriptions(prompt: str, shot_count: int, video_type: str) -> List[str]:
    """
    备用方案：基于规则生成镜头描述
    
    Args:
        prompt: 用户提示词
        shot_count: 镜头数量
        video_type: 视频类型
    
    Returns:
        镜头描述列表
    """
    descriptions = []
    
    for i in range(shot_count):
        if i == 0:
            # 开场
            descriptions.append(f"开场建立场景：{prompt}。使用全景镜头，展示整体环境氛围，为观众建立视觉基础。")
        elif i == shot_count - 1:
            # 结尾
            descriptions.append(f"结尾收束：{prompt}。使用远景或全景镜头，为场景留下余韵，完成视觉叙事。")
        else:
            # 中间镜头：根据位置生成
            position_ratio = i / shot_count
            if position_ratio < 0.3:
                descriptions.append(f"细节展开（镜头{i+1}）：{prompt}。聚焦场景中的关键元素和细节，逐步推进叙事。")
            elif position_ratio < 0.7:
                descriptions.append(f"核心呈现（镜头{i+1}）：{prompt}。展示场景的核心内容和关键动作，推进情节发展。")
            else:
                descriptions.append(f"高潮时刻（镜头{i+1}）：{prompt}。聚焦场景的高光时刻或转折点，营造视觉冲击。")
    
    return descriptions


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


def _generate_custom_storyboard_markdown(video_result: Dict, prompt: str, video_type: str) -> str:
    """
    为自定义视频生成分镜头Markdown脚本
    
    Args:
        video_result: 视频分镜头结果
        prompt: 原始提示词
        video_type: 视频类型
    
    Returns:
        Markdown格式的分镜头脚本
    """
    type_name = {
        "short_film": "短片/动画电影",
        "long_series": "长篇剧集",
        "short_video": "短视频系列"
    }.get(video_type, video_type)
    
    units = video_result.get("units", [])
    total_shots = sum(unit.get("storyboard", {}).get("total_shots", 0) for unit in units)
    
    md = f"""# 自定义视频分镜头脚本

## 基本信息
- **视频类型**: {type_name}
- **原始提示词**: {prompt}
- **单元数量**: {len(units)}
- **总镜头数**: {total_shots}
- **生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 视频风格指南
- **整体风格**: {video_result.get("visual_style_guide", {}).get("overall_style", "自定义")}
- **色彩方案**: {video_result.get("visual_style_guide", {}).get("color_palette", "根据提示词自动适配")}
- **氛围**: {video_result.get("visual_style_guide", {}).get("atmosphere", "根据提示词自动生成")}

## 节奏指导
- **整体节奏**: {video_result.get("pacing_guidelines", {}).get("tempo", "根据视频类型自动调整")}
- **过渡风格**: {video_result.get("pacing_guidelines", {}).get("transitions", "平滑过渡")}

---

"""
    
    # 为每个单元生成分镜头
    for unit in units:
        unit_number = unit.get("unit_number", 1)
        unit_title = unit.get("title", f"第{unit_number}部分")
        storyboard = unit.get("storyboard", {})
        scenes = storyboard.get("scenes", [])
        
        md += f"## 单元 {unit_number}: {unit_title}\n\n"
        
        for scene in scenes:
            scene_number = scene.get("scene_number", 1)
            scene_title = scene.get("scene_title", f"场景{scene_number}")
            scene_desc = scene.get("scene_description", "")
            duration = scene.get("estimated_duration_minutes", 0)
            
            md += f"### 场景 {scene_number}: {scene_title}\n\n"
            md += f"**描述**: {scene_desc}  \n"
            md += f"**预估时长**: {duration}分钟  \n\n"
            
            # 镜头序列
            shots = scene.get("shot_sequence", [])
            if shots:
                md += "#### 镜头序列\n\n"
                md += "| 镜头号 | 景别 | 运镜 | 时长 | 描述 | 音频 |\n"
                md += "|--------|------|------|------|------|------|\n"
                
                for shot in shots:
                    shot_num = shot.get("shot_number", "-")
                    shot_type = shot.get("shot_type", "-")
                    movement = shot.get("camera_movement", "-")
                    duration_sec = shot.get("duration_seconds", "-")
                    desc = shot.get("description", "-")
                    audio = shot.get("audio_note", shot.get("tiktok_note", "-"))
                    
                    # 截断过长的描述
                    if len(desc) > 50:
                        desc = desc[:47] + "..."
                    
                    md += f"| {shot_num} | {shot_type} | {movement} | {duration_sec}秒 | {desc} | {audio} |\n"
                
                md += "\n"
            
            # 视觉备注
            visual_notes = scene.get("visual_notes", {})
            if visual_notes:
                md += "#### 视觉设计\n\n"
                md += f"- **色彩**: {visual_notes.get('color_palette', '-')}\n"
                md += f"- **灯光**: {visual_notes.get('lighting', '-')}\n"
                md += f"- **构图**: {visual_notes.get('composition_style', '-')}\n\n"
        
        md += "---\n\n"
    
    # 添加统计信息
    md += "## 统计信息\n\n"
    md += f"- 总单元数: {len(units)}\n"
    md += f"- 总场景数: {sum(len(unit.get('storyboard', {}).get('scenes', [])) for unit in units)}\n"
    md += f"- 总镜头数: {total_shots}\n"
    md += f"- 总预估时长: {sum(unit.get('storyboard', {}).get('total_duration_minutes', 0) for unit in units):.1f} 分钟\n"
    
    return md


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
        "image_size": "4K",         // 可选，默认4K
        "reference_images": ["/path/to/reference1.jpg", ...]  // 可选，多个参考图像路径数组
        "reference_image": "/path/to/reference.jpg"  // 兼容旧版本，单个参考图像
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        character_id = data.get('character_id')
        character_data = data.get('character_data', {})
        aspect_ratio = data.get('aspect_ratio', '9:16')  # 默认竖屏，适合角色展示
        image_size = data.get('image_size', '4K')
        reference_images = data.get('reference_images', [])  # 🔥 新增：多个参考图像数组
        reference_image = data.get('reference_image')  # 兼容旧版本：单个参考图像
        custom_prompt = data.get('prompt', '')  # 🔥 新增：自定义提示词（用于自定义模式）
        custom_style = data.get('style', '')  # 🔥 新增：自定义风格（用于自定义模式）
        
        # 🔥 兼容处理：将单个参考图像转换为数组
        if reference_image and not reference_images:
            reference_images = [reference_image]
        
        logger.info(f"🎨 [VIDEO] ===== 开始生成角色剧照 =====")
        logger.info(f"📝 [VIDEO] 请求参数:")
        logger.info(f"  - 小说标题: {title or '自定义模式'}")
        logger.info(f"  - 角色ID: {character_id or '自定义模式'}")
        logger.info(f"  - 角色名称: {character_data.get('name', 'Unknown')}")
        logger.info(f"  - 角色定位: {character_data.get('role', 'Unknown')}")
        logger.info(f"  - 图片比例: {aspect_ratio}")
        logger.info(f"  - 图片质量: {image_size}")
        # 🔥 不打印完整的参考图像base64数据
        if reference_images:
            logger.info(f"  - 参考图像数量: {len(reference_images)} 张")
            for idx, ref_img in enumerate(reference_images):
                # 检测是否是base64数据格式
                is_base64 = ref_img.startswith('data:image/')
                ref_type = "Base64数据" if is_base64 else "文件路径"
                preview = ref_img[:50] + "..." if len(ref_img) > 50 else ref_img
                logger.info(f"    参考图{idx+1}: {ref_type} (总长度: {len(ref_img)} 字符, 预览: {preview})")
        else:
            logger.info(f"  - 参考图像: 无")
        logger.info(f"  - 自定义提示词: {custom_prompt[:50] if custom_prompt else '无'}...")
        logger.info(f"  - 自定义风格: {custom_style or '无'}")
        
        # 🔥 修复：支持自定义模式（不需要 title 和 character_id）
        is_custom_mode = bool(custom_prompt)
        
        if not is_custom_mode and (not title or not character_id):
            logger.error(f"❌ [VIDEO] 缺少必需参数: title={title}, character_id={character_id}")
            return jsonify({"success": False, "error": "缺少必需参数: title 或 character_id"}), 400
        
        logger.info(f"🎨 [VIDEO] 生成角色剧照: {title or '自定义模式'} - {character_id or '自定义模式'} (模式: {'自定义' if is_custom_mode else '角色'})")
        
        # 生成剧照提示词
        if is_custom_mode:
            # 🔥 自定义模式：直接使用用户输入的提示词
            prompt = custom_prompt
            
            # 添加风格指导
            if custom_style:
                style_guide = {
                    'xianxia': '仙侠风格，飘逸洒脱，仙气缭绕',
                    'modern': '现代都市，时尚简约，充满活力',
                    'fantasy': '奇幻魔法，神秘华丽，充满魔力',
                    'sci': '科幻未来，科技感强，赛博朋克',
                    'romance': '浪漫唯美，温柔细腻，梦幻氛围'
                }
                if custom_style in style_guide:
                    prompt = f"{prompt}\n\n风格要求：{style_guide[custom_style]}"
            
            logger.info(f"✅ [VIDEO] 使用自定义提示词")
            logger.info(f"📝 [VIDEO] 提示词长度: {len(prompt)} 字符")
            logger.info(f"📝 [VIDEO] 提示词预览: {prompt[:200]}...")
        else:
            # 角色模式：使用EventExtractor生成剧照提示词
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
        
        # 🔥 新增：处理多个参考图像路径（支持文件路径和Base64数据）
        ref_image_paths = []
        if reference_images:
            import os
            import tempfile
            import base64
            
            for idx, reference_image in enumerate(reference_images):
                ref_image_path = None
                
                # 检测是否是base64数据格式
                if reference_image.startswith('data:image/'):
                    try:
                        # 解析base64数据
                        header, data = reference_image.split(',', 1)
                        # 获取MIME类型
                        mime_type = header.split(':')[1].split(';')[0]
                        # 获取文件扩展名
                        ext_map = {
                            'image/png': '.png',
                            'image/jpeg': '.jpg',
                            'image/jpg': '.jpg',
                            'image/gif': '.gif',
                            'image/webp': '.webp'
                        }
                        ext = ext_map.get(mime_type, '.png')
                        
                        # 创建临时目录（如果不存在）
                        temp_dir = os.path.join(BASE_DIR, 'temp_uploads')
                        os.makedirs(temp_dir, exist_ok=True)
                        
                        # 创建临时文件保存base64图像
                        with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=temp_dir) as f:
                            temp_path = f.name
                            f.write(base64.b64decode(data))
                        
                        ref_image_path = temp_path
                        logger.info(f"🖼️ [VIDEO] Base64图像{idx+1}已保存到临时文件: {ref_image_path}")
                    except Exception as e:
                        logger.error(f"❌ [VIDEO] 处理Base64图像{idx+1}失败: {e}")
                        ref_image_path = None
                elif reference_image.startswith('/generated_images/'):
                    # 如果是URL路径，转换为本地路径
                    ref_image_path = os.path.join(BASE_DIR, reference_image.lstrip('/'))
                    logger.info(f"🖼️ [VIDEO] 参考图像{idx+1}路径转换: {reference_image} -> {ref_image_path}")
                else:
                    # 直接使用作为文件路径
                    ref_image_path = reference_image
                
                # 验证文件存在
                if ref_image_path and not os.path.exists(ref_image_path):
                    logger.warn(f"⚠️ [VIDEO] 参考图像{idx+1}不存在，将跳过: {ref_image_path}")
                    ref_image_path = None
                
                if ref_image_path:
                    ref_image_paths.append(ref_image_path)
            
            logger.info(f"✅ [VIDEO] 成功处理 {len(ref_image_paths)} 张参考图像")
        
        # 🔥 直接使用NanoBananaImageGenerator（支持多个参考图像）
        from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
        generator = NanoBananaImageGenerator()
        
        logger.debug(f"🎨 [VIDEO] 准备调用NanoBananaImageGenerator...")
        logger.debug(f"📝 [VIDEO] 提示词长度: {len(prompt)} 字符")
        logger.debug(f"📝 [VIDEO] 提示词预览: {prompt[:100]}...")  # 只显示前100字符
        logger.debug(f"🖼️ [VIDEO] 参考图像数量: {len(ref_image_paths)}")

        # 🔥 生成文件名：项目名+角色+剧集
        if is_custom_mode:
            # 自定义模式：使用通用文件名
            safe_name = 'custom'
            filename = f"{title or 'custom'}_custom_portrait"
        else:
            # 角色模式：使用标准命名 项目名_角色名_剧集
            character_name = character_data.get('name', 'unknown')
            safe_character = character_name.replace(' ', '_').replace('/', '_')

            # 获取剧集信息（如果有）
            episode_info = data.get('episode_info', '')
            if episode_info:
                safe_episode = episode_info.replace(' ', '_').replace('/', '_')
                filename = f"{title}_{safe_character}_{safe_episode}"
            else:
                filename = f"{title}_{safe_character}"

        logger.debug(f"💾 [VIDEO] 生成文件名: {filename}")
        
        # 🔥 生成图像（支持多个参考图像，最多5张）
        logger.debug(f"🚀 [VIDEO] 调用NanoBananaImageGenerator.generate_image()...")
        logger.debug(f"📤 [VIDEO] 请求参数:")
        logger.debug(f"  - prompt长度: {len(prompt)}")
        logger.debug(f"  - aspect_ratio: {aspect_ratio}")
        logger.debug(f"  - image_size: {image_size}")
        logger.debug(f"  - 参考图像数量: {len(ref_image_paths)} 张")
        
        result = generator.generate_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            save_path=None,  # 自动生成路径
            reference_images=ref_image_paths  # 🔥 传递多个参考图像（数组）
        )
        
        logger.info(f"📥 [VIDEO] NanoBananaImageGenerator返回结果:")
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

            # 🔥 复制到视频项目的目录
            import os
            import shutil
            project_file_path = None  # 初始化变量
            project_filename = None
            video_project_dir = None

            # 🔥 获取项目信息（从 character_data 或请求参数中）
            novel_title = None
            episode_info = None

            # 优先从 character_data 获取项目信息
            if character_data:
                novel_title = character_data.get('novel_title') or character_data.get('title')
                episode_info = character_data.get('episode_info') or data.get('episode_info', '')

            # 如果没有，从请求参数获取
            if not novel_title:
                novel_title = data.get('novel_title') or title
            if not episode_info:
                episode_info = data.get('episode_info', '')

            # 🔥 添加调试日志
            logger.info(f"🔍 [VIDEO] 视频项目复制检查:")
            logger.info(f"  - is_custom_mode: {is_custom_mode}")
            logger.info(f"  - title: {title}")
            logger.info(f"  - novel_title: {novel_title}")
            logger.info(f"  - episode_info: {episode_info}")
            logger.info(f"  - 条件满足: {bool(novel_title)}")

            # 🔥 只要有 novel_title 就保存到项目目录
            if novel_title:
                try:
                    # 🔥 路径安全处理：只对文件名进行清理，目录名使用原始值
                    def sanitize_filename(name):
                        """清理文件名，只移除Windows不允许的字符（保留中文标点）"""
                        invalid_chars = ['<', '>', '"', '/', '\\', '|', '?', '*']
                        result = name
                        for char in invalid_chars:
                            result = result.replace(char, '_')
                        return result.strip('_')

                    # 获取角色名
                    character_name = character_data.get('name') if character_data else 'custom'
                    safe_character_name = sanitize_filename(character_name)

                    # 🔥 使用原始的小说名和剧集信息（实际目录已用这些名称创建）
                    safe_episode = episode_info if episode_info else '默认'

                    # 🔥 新目录结构: 视频项目/{小说名}/{分集}/{角色名}.png
                    video_project_base = os.path.join(BASE_DIR, '视频项目', novel_title, safe_episode)

                    logger.info(f"📁 [VIDEO] 视频项目路径构建:")
                    logger.info(f"  - 原始小说标题: {novel_title}")
                    logger.info(f"  - 原始角色名: {character_name}")
                    logger.info(f"  - 清理后角色名: {safe_character_name}")
                    logger.info(f"  - 剧集信息: {episode_info}")
                    logger.info(f"  - 项目目录: {video_project_base}")

                    # 创建视频项目目录（如果不存在）
                    os.makedirs(video_project_base, exist_ok=True)
                    logger.info(f"📁 [VIDEO] 确保/创建视频项目目录: {video_project_base}")

                    # 复制文件到视频项目目录
                    original_file = result.get('local_path')
                    if original_file and os.path.exists(original_file):
                        # 使用角色名作为文件名: {角色名}.png
                        project_filename = f"{safe_character_name}.png"
                        project_file_path = os.path.join(video_project_base, project_filename)

                        # 如果文件已存在，添加序号
                        counter = 1
                        while os.path.exists(project_file_path):
                            project_filename = f"{safe_character_name}_{counter}.png"
                            project_file_path = os.path.join(video_project_base, project_filename)
                            counter += 1

                        shutil.copy2(original_file, project_file_path)
                        logger.info(f"✅ [VIDEO] 剧照已保存到视频项目: {project_file_path}")

                        # 构建项目内的访问URL: /project-files/{小说名}/{分集}/{角色名}.png
                        video_project_dir = f"{novel_title}/{safe_episode}"
                    else:
                        logger.error(f"❌ [VIDEO] 原始文件不存在: {original_file}")
                except Exception as e:
                    logger.error(f"⚠️ [VIDEO] 保存到视频项目失败: {e}")
                    import traceback
                    logger.error(f"错误堆栈: {traceback.format_exc()}")

            # 构建HTTP访问路径（浏览器可访问）
            import urllib.parse

            # 🔥 优先使用视频项目内的URL
            if project_file_path and os.path.exists(project_file_path):
                # 使用项目文件路径
                project_filename_encoded = urllib.parse.quote(project_filename)
                image_url = f"/project-files/{urllib.parse.quote(video_project_dir)}/{project_filename_encoded}"
                logger.info(f"🌐 [VIDEO] 使用视频项目URL: {image_url}")
            else:
                # 回退到generated_images路径
                image_filename = os.path.basename(result.get('local_path', ''))
                encoded_filename = urllib.parse.quote(image_filename)
                image_url = f"/generated_images/{encoded_filename}"
                logger.info(f"🌐 [VIDEO] 使用generated_images URL: {image_url}")
                logger.info(f"🌐 [VIDEO] 原始文件名: {image_filename}")
                logger.info(f"🌐 [VIDEO] 编码后文件名: {encoded_filename}")

            # 构建返回消息
            if is_custom_mode:
                message = f"自定义剧照生成成功" + (f" (使用{len(ref_image_paths)}张参考图)" if ref_image_paths else "")
            else:
                message = f"角色 {character_name} 的剧照生成成功" + (f" (使用{len(ref_image_paths)}张参考图)" if ref_image_paths else "")

            return jsonify({
                "success": True,
                "image_path": result.get('local_path'),  # 本地路径（用于下载）
                "image_url": image_url,  # HTTP URL（用于浏览器显示）
                "project_image_path": project_file_path,  # 🔥 视频项目内的文件路径
                "prompt": prompt,
                "character_name": character_name if not is_custom_mode else '自定义',
                "used_reference_images": len(ref_image_paths),  # 🔥 新增：使用了多少张参考图
                "message": message
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


@video_api.route('/video/discover-portraits', methods=['GET'])
@login_required
def discover_character_portraits():
    """
    扫描视频项目目录，发现已有的角色剧照

    新目录结构: 视频项目/{小说名}/{分集}/{角色名}.png

    返回格式：
    {
        "success": true,
        "portraits": [
            {
                "character_name": "林长生",
                "novel_title": "心声泄露：我成了家族老阴比",
                "episode_info": "第一集",
                "image_url": "/project-files/...",
                "local_path": "视频项目/..."
            }
        ]
    }
    """
    try:
        import os
        from pathlib import Path
        import urllib.parse

        project_base = Path('视频项目')
        if not project_base.exists():
            return jsonify({
                "success": True,
                "portraits": [],
                "message": "视频项目目录不存在"
            })

        portraits = []

        # 🔥 新结构：遍历小说目录
        for novel_dir in project_base.iterdir():
            if not novel_dir.is_dir():
                continue

            novel_title = novel_dir.name
            logger.info(f"🔍 [发现剧照] 扫描小说目录: {novel_title}")

            # 🔥 遍历分集目录
            for episode_dir in novel_dir.iterdir():
                if not episode_dir.is_dir():
                    continue

                episode_info = episode_dir.name
                logger.info(f"  📁 扫描分集: {episode_info}")

                # 查找分集中的图片文件
                image_files = list(episode_dir.glob('*.png')) + list(episode_dir.glob('*.jpg')) + list(episode_dir.glob('*.jpeg'))

                for img_file in image_files:
                    # 从文件名提取角色名（去掉扩展名和序号）
                    character_name = img_file.stem
                    # 处理带序号的文件名，如 "林长生_1" -> "林长生"
                    if '_' in character_name and character_name.split('_')[-1].isdigit():
                        character_name = '_'.join(character_name.split('_')[:-1])

                    # 构建访问URL
                    relative_path = img_file.relative_to(project_base)
                    image_url = f"/project-files/{urllib.parse.quote(str(relative_path), safe='/')}"

                    portrait_info = {
                        "character_name": character_name,
                        "novel_title": novel_title,
                        "episode_info": episode_info,
                        "image_url": image_url,
                        "local_path": str(img_file),
                        "filename": img_file.name
                    }
                    portraits.append(portrait_info)
                    logger.info(f"    ✅ 发现剧照: {character_name} -> {image_url}")

        logger.info(f"📊 [发现剧照] 共发现 {len(portraits)} 个剧照文件")
        return jsonify({
            "success": True,
            "portraits": portraits
        })

    except Exception as e:
        logger.error(f"❌ [发现剧照] 扫描失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/generate-scene-portrait', methods=['POST'])
@login_required
def generate_scene_portrait():
    """
    生成场景/任务剧照
    
    请求参数：
    {
        "title": "小说标题",
        "event_id": "事件ID",
        "event_data": {...},  // 事件数据
        "aspect_ratio": "16:9",    // 可选，默认16:9
        "image_size": "4K",         // 可选，默认4K
        "reference_image": "/path/to/reference.jpg",  // 可选，参考图像路径
        "custom_prompt": "额外提示词"  // 可选
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        event_id = data.get('event_id')
        event_data = data.get('event_data', {})
        aspect_ratio = data.get('aspect_ratio', '16:9')  # 默认横屏，适合场景展示
        image_size = data.get('image_size', '4K')
        reference_image = data.get('reference_image')  # 支持参考图像
        custom_prompt = data.get('custom_prompt', '')
        
        logger.info(f"🎬 [SCENE] ===== 开始生成场景剧照 =====")
        logger.info(f"📝 [SCENE] 请求参数:")
        logger.info(f"  - 小说标题: {title}")
        logger.info(f"  - 事件ID: {event_id}")
        logger.info(f"  - 事件名称: {event_data.get('title', event_data.get('name', 'Unknown'))}")
        logger.info(f"  - 图片比例: {aspect_ratio}")
        logger.info(f"  - 图片质量: {image_size}")
        # 🔥 不打印完整的参考图像base64数据
        if reference_image:
            # 检测是否是base64数据格式
            is_base64 = reference_image.startswith('data:image/')
            ref_type = "Base64数据" if is_base64 else "文件路径"
            preview = reference_image[:50] + "..." if len(reference_image) > 50 else reference_image
            logger.info(f"  - 参考图像: {ref_type} (总长度: {len(reference_image)} 字符, 预览: {preview})")
        else:
            logger.info(f"  - 参考图像: 无")
        logger.info(f"  - 自定义提示词: {custom_prompt[:50] if custom_prompt else '无'}...")
        
        if not title or not event_id:
            logger.error(f"❌ [SCENE] 缺少必需参数: title={title}, event_id={event_id}")
            return jsonify({"success": False, "error": "缺少必需参数: title 或 event_id"}), 400
        
        # 生成场景提示词
        scene_prompt = _generate_scene_prompt(event_data, custom_prompt)
        
        logger.info(f"✅ [SCENE] 场景提示词生成成功")
        logger.info(f"📝 [SCENE] 提示词长度: {len(scene_prompt)} 字符")
        logger.info(f"📝 [SCENE] 提示词预览: {scene_prompt[:200]}...")
        
        # 🔥 处理参考图像路径（支持文件路径和Base64数据）
        ref_image_path = None
        if reference_image:
            import os
            import tempfile
            import base64
            
            # 检测是否是base64数据格式
            if reference_image.startswith('data:image/'):
                try:
                    # 解析base64数据
                    header, data = reference_image.split(',', 1)
                    # 获取MIME类型
                    mime_type = header.split(':')[1].split(';')[0]
                    # 获取文件扩展名
                    ext_map = {
                        'image/png': '.png',
                        'image/jpeg': '.jpg',
                        'image/jpg': '.jpg',
                        'image/gif': '.gif',
                        'image/webp': '.webp'
                    }
                    ext = ext_map.get(mime_type, '.png')
                    
                    # 创建临时目录（如果不存在）
                    temp_dir = os.path.join(BASE_DIR, 'temp_uploads')
                    os.makedirs(temp_dir, exist_ok=True)
                    
                    # 创建临时文件保存base64图像
                    with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=temp_dir) as f:
                        temp_path = f.name
                        f.write(base64.b64decode(data))
                    
                    ref_image_path = temp_path
                    logger.info(f"🖼️ [SCENE] Base64图像已保存到临时文件: {ref_image_path}")
                except Exception as e:
                    logger.error(f"❌ [SCENE] 处理Base64图像失败: {e}")
                    ref_image_path = None
            elif reference_image.startswith('/generated_images/'):
                # 如果是URL路径，转换为本地路径
                ref_image_path = os.path.join(BASE_DIR, reference_image.lstrip('/'))
                logger.info(f"🖼️ [SCENE] 参考图像路径转换: {reference_image} -> {ref_image_path}")
            else:
                # 直接使用作为文件路径
                ref_image_path = reference_image
            
            # 验证文件存在
            if ref_image_path and not os.path.exists(ref_image_path):
                logger.warn(f"⚠️ [SCENE] 参考图像不存在，将使用纯文本模式: {ref_image_path}")
                ref_image_path = None
        
        # 使用NanoBananaImageGenerator生成图像
        from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
        generator = NanoBananaImageGenerator()
        
        # 生成文件名
        event_name = event_data.get('title', event_data.get('name', 'unknown'))
        safe_name = event_name.replace(' ', '_').replace('/', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{title}_{safe_name}_scene_{timestamp}"
        
        # 生成图像
        logger.info(f"🚀 [SCENE] 调用NanoBananaImageGenerator.generate_image()...")
        result = generator.generate_image(
            prompt=scene_prompt,
            aspect_ratio=aspect_ratio,
            image_size=image_size,
            save_path=None,
            reference_image=ref_image_path
        )
        
        logger.info(f"📥 [SCENE] NanoBananaImageGenerator返回结果:")
        logger.info(f"  - success: {result.get('success')}")
        logger.info(f"  - local_path: {result.get('local_path', 'N/A')}")
        
        if result.get('success'):
            logger.info(f"✅ [SCENE] 场景剧照生成成功: {result.get('local_path')}")
            
            # 构建HTTP访问路径
            import urllib.parse
            image_filename = os.path.basename(result.get('local_path', ''))
            encoded_filename = urllib.parse.quote(image_filename)
            image_url = f"/generated_images/{encoded_filename}"
            
            return jsonify({
                "success": True,
                "image_path": result.get('local_path'),
                "image_url": image_url,
                "prompt": scene_prompt,
                "event_name": event_name,
                "used_reference_image": ref_image_path is not None,
                "message": f"场景 {event_name} 的剧照生成成功" + (" (使用参考图像)" if ref_image_path else "")
            })
        else:
            logger.error(f"❌ [SCENE] 场景剧照生成失败: {result.get('error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', '生成失败')
            }), 500
            
    except Exception as e:
        logger.error(f"❌ [SCENE] 生成场景剧照失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _generate_scene_prompt(event_data: Dict, custom_prompt: str = '') -> str:
    """
    生成场景剧照的提示词
    
    Args:
        event_data: 事件数据
        custom_prompt: 自定义提示词
    
    Returns:
        生成的场景提示词
    """
    event_name = event_data.get('title', event_data.get('name', '未知场景'))
    description = event_data.get('description', '')
    location = event_data.get('location', '')
    emotion = event_data.get('emotion', '')
    stage = event_data.get('stage', '')
    characters = event_data.get('characters', '')
    
    # 构建场景提示词
    prompt_parts = []
    
    # 添加场景标题和阶段
    if stage:
        prompt_parts.append(f"[{stage}阶段场景]")
    prompt_parts.append(f"《{event_name}》")
    
    # 添加场景描述
    if description:
        prompt_parts.append(f"\n场景描述：{description}")
    
    # 添加地点信息
    if location:
        prompt_parts.append(f"\n地点：{location}")
    
    # 添加情感氛围
    if emotion:
        prompt_parts.append(f"\n氛围：{emotion}")
    
    # 添加角色信息（如果有）
    if characters:
        prompt_parts.append(f"\n角色：{characters}")
    
    # 添加视觉风格指导
    prompt_parts.append("\n视觉风格要求：")
    prompt_parts.append("- 高质量电影级场景渲染")
    prompt_parts.append("- 丰富的细节和层次感")
    prompt_parts.append("- 恰当的光影效果")
    prompt_parts.append("- 符合场景氛围的色彩搭配")
    
    # 根据阶段添加特定指导
    if stage == '起':
        prompt_parts.append("- 宁静平和的开场氛围")
    elif stage == '承':
        prompt_parts.append("- 逐渐推进的叙事张力")
    elif stage == '转':
        prompt_parts.append("- 强烈的视觉冲击和戏剧性")
    elif stage == '合':
        prompt_parts.append("- 收束和总结性的视觉呈现")
    
    # 添加自定义提示词
    if custom_prompt:
        prompt_parts.append(f"\n额外要求：{custom_prompt}")
    
    return '\n'.join(prompt_parts)


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


@video_api.route('/video/projects', methods=['GET'])
@login_required
def list_video_projects():
    """
    列出所有视频项目（包括自定义项目和小说转换的项目）
    
    返回项目列表，支持点击跳转到详情
    """
    try:
        video_projects_dir = Path("视频项目")
        if not video_projects_dir.exists():
            return jsonify({
                "success": True,
                "projects": [],
                "total": 0
            })
        
        projects = []
        
        # 遍历所有子目录
        for project_path in video_projects_dir.iterdir():
            if not project_path.is_dir():
                continue
            
            # 查找JSON文件
            json_files = list(project_path.glob("*.json"))
            if not json_files:
                continue
            
            # 读取第一个JSON文件获取项目信息
            try:
                with open(json_files[0], 'r', encoding='utf-8') as f:
                    storyboard_data = json.load(f)
                
                # 提取项目信息
                project_info = {
                    "project_name": project_path.name,
                    "project_path": str(project_path),
                    "video_type": storyboard_data.get("video_type", "unknown"),
                    "video_type_name": storyboard_data.get("video_type_name", "未知类型"),
                    "mode": storyboard_data.get("mode", "novel"),  # novel 或 custom
                    "total_units": len(storyboard_data.get("units", [])),
                    "created_time": json_files[0].stat().st_mtime,
                    "json_file": str(json_files[0])
                }
                
                # 如果是自定义模式，添加自定义提示词
                if storyboard_data.get("mode") == "custom":
                    project_info["custom_prompt"] = storyboard_data.get("custom_prompt", "")[:100]
                
                # 计算总镜头数
                total_shots = sum(
                    unit.get("storyboard", {}).get("total_shots", 0)
                    for unit in storyboard_data.get("units", [])
                )
                project_info["total_shots"] = total_shots
                
                projects.append(project_info)
                
            except Exception as e:
                logger.warn(f"⚠️ [VIDEO] 无法读取项目 {project_path.name}: {e}")
                continue
        
        # 按创建时间倒序排序
        projects.sort(key=lambda x: x["created_time"], reverse=True)
        
        logger.info(f"📊 [VIDEO] 找到 {len(projects)} 个视频项目")
        
        return jsonify({
            "success": True,
            "projects": projects,
            "total": len(projects)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 列出视频项目失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/project/<project_name>', methods=['GET'])
@login_required
def get_video_project(project_name):
    """
    获取指定视频项目的详细信息

    参数：
    - project_name: 项目名称
    """
    try:
        video_projects_dir = Path("视频项目")
        project_path = video_projects_dir / project_name

        if not project_path.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404

        # 查找JSON文件
        json_files = list(project_path.glob("*.json"))
        if not json_files:
            return jsonify({"success": False, "error": "项目数据文件不存在"}), 404

        # 读取分镜头数据
        with open(json_files[0], 'r', encoding='utf-8') as f:
            storyboard_data = json.load(f)

        # 提取所有镜头
        units = storyboard_data.get("units", [])
        shots = []

        for unit in units:
            storyboard = unit.get("storyboard", {})
            scenes = storyboard.get("scenes", [])

            for scene in scenes:
                shot_sequence = scene.get("shot_sequence", [])
                for shot in shot_sequence:
                    # 🔥 直接使用镜头描述，专注于视频画面本身
                    generation_prompt = shot.get('description', shot.get('veo_prompt', ''))

                    shots.append({
                        "shot_index": len(shots),
                        "unit_number": unit.get("unit_number"),
                        "scene_number": scene.get("scene_number"),
                        "scene_description": scene.get("scene_description", ""),
                        "shot_number": shot.get("shot_number"),
                        "shot_type": shot.get("shot_type", "中景"),
                        "camera_movement": shot.get("camera_movement", '固定'),
                        "duration_seconds": shot.get("duration_seconds", 5),
                        "description": shot.get("description", ""),
                        "audio_cue": shot.get("audio_note", shot.get("tiktok_note", "")),
                        "veo_prompt": generation_prompt,  # 🔥 使用前端期望的字段名
                        "screen_action": shot.get("description", ""),  # 保留兼容字段
                        "status": "pending",
                        "visual_style": storyboard_data.get("visual_style_guide", {}).get("overall_style", "写实")
                    })

        logger.info(f"📊 [VIDEO] 加载项目 {project_name}: {len(shots)} 个镜头")
        
        return jsonify({
            "success": True,
            "project_name": project_name,
            "storyboard": storyboard_data,
            "shots": shots,
            "total_shots": len(shots),
            "project_path": str(project_path)
        })
        
    except Exception as e:
        logger.error(f"❌ [VIDEO] 获取视频项目失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/generate-portrait-first', methods=['POST'])
@login_required
def generate_portrait_first_workflow():
    """
    优化工作流：先生成人物剧照，再逐镜头生成视频

    工作流程：
    1. 提取重大事件中的角色
    2. 为所有角色生成剧照
    3. 为每个镜头匹配角色剧照作为参考图
    4. 逐镜头生成视频

    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",
        "selected_events": ["event_0", "event_1", ...],  // 可选
        "aspect_ratio": "9:16",  // 照片比例，默认9:16（竖屏）
        "image_size": "4K"       // 照片质量，默认4K
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        video_type = data.get('video_type', 'long_series')
        selected_events = data.get('selected_events', [])
        aspect_ratio = data.get('aspect_ratio', '9:16')
        image_size = data.get('image_size', '4K')

        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400

        logger.info(f"🎬 [PORTRAIT-FIRST] 开始优化工作流: {title}")

        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404

        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)

        # ========== 第一步：提取事件和角色 ==========
        logger.info(f"📋 [步骤1/4] 提取事件和角色...")

        # 提取重大事件
        all_events = event_extractor.extract_all_major_events(novel_detail)
        if selected_events:
            all_events = _filter_selected_events(all_events, selected_events, logger)

        # 提取角色（从事件中识别）
        characters_in_events = _extract_characters_from_events(all_events)
        logger.info(f"  👥 从事件中识别到 {len(characters_in_events)} 个角色")

        # ========== 第二步：生成角色剧照 ==========
        logger.info(f"📸 [步骤2/4] 生成角色剧照...")

        character_portraits = {}
        portrait_results = []

        from src.utils.NanoBananaImageGenerator import get_image_generator
        from pathlib import Path
        import re

        image_gen = get_image_generator()
        safe_title = re.sub(r'[\\/*?:"<>|]', '_', title)
        portraits_dir = Path(f"generated_images/{safe_title}_portraits")
        portraits_dir.mkdir(parents=True, exist_ok=True)

        for char_id, char_info in characters_in_events.items():
            char_name = char_info.get('name', f'角色{char_id}')
            char_appearance = char_info.get('appearance', '')
            char_role = char_info.get('role', '角色')

            # 生成角色剧照prompt
            portrait_prompt = f"""高质量角色剧照，{char_appearance}

角色：{char_name}
身份：{char_role}
风格：精修写真级人物肖像
构图：人物居中，上半身或全身
背景：虚化或纯色背景，突出人物
细节：面部特征清晰，表情生动，光影柔和"""

            try:
                # 生成剧照
                portrait_path = portraits_dir / f"{safe_title}_{char_name}_portrait.png"

                result = image_gen.generate_image(
                    prompt=portrait_prompt,
                    save_path=str(portrait_path),
                    image_size=image_size
                )

                if result.get('success'):
                    portrait_url = f"/generated_images/{safe_title}_portraits/{safe_title}_{char_name}_portrait.png"
                    character_portraits[char_id] = portrait_url

                    portrait_results.append({
                        "character_id": char_id,
                        "character_name": char_name,
                        "portrait_url": portrait_url,
                        "status": "completed"
                    })
                    logger.info(f"  ✅ {char_name} 剧照生成成功")
                else:
                    portrait_results.append({
                        "character_id": char_id,
                        "character_name": char_name,
                        "status": "failed",
                        "error": result.get('error', '未知错误')
                    })
                    logger.warn(f"  ⚠️ {char_name} 剧照生成失败")

            except Exception as e:
                logger.error(f"  ❌ {char_name} 剧照生成异常: {e}")
                portrait_results.append({
                    "character_id": char_id,
                    "character_name": char_name,
                    "status": "error",
                    "error": str(e)
                })

        # ========== 第三步：生成镜头序列，关联角色剧照 ==========
        logger.info(f"🎬 [步骤3/4] 生成镜头序列并关联剧照...")

        from src.managers.VideoAdapterManager import VideoAdapterManager

        class MockGenerator:
            def __init__(self, novel_data):
                self.novel_data = novel_data
                self.api_client = None

        mock_generator = MockGenerator(novel_detail)
        adapter = VideoAdapterManager(mock_generator)

        video_result = adapter.convert_to_video(
            novel_data=novel_detail,
            video_type=video_type,
            filtered_events=all_events
        )

        # 提取镜头并关联角色剧照
        units = video_result.get("units", [])
        shots_with_portraits = []

        for unit in units:
            storyboard = unit.get("storyboard", {})
            scenes = storyboard.get("scenes", [])

            for scene in scenes:
                shot_sequence = scene.get("shot_sequence", [])
                scene_characters = _identify_characters_in_scene(scene, characters_in_events)

                for shot in shot_sequence:
                    # 为这个镜头找到相关的角色剧照
                    shot_portraits = []
                    for char_id in scene_characters:
                        if char_id in character_portraits:
                            shot_portraits.append({
                                "character_id": char_id,
                                "character_name": characters_in_events[char_id].get('name', ''),
                                "portrait_url": character_portraits[char_id]
                            })

                    shots_with_portraits.append({
                        "shot_index": len(shots_with_portraits),
                        "unit_number": unit.get("unit_number"),
                        "unit_name": unit.get("medium_event_name", ""),
                        "scene_number": scene.get("scene_number"),
                        "scene_description": scene.get("scene_description", ""),
                        "shot_number": shot.get("shot_number"),
                        "shot_type": shot.get("shot_type", "中景"),
                        "camera_movement": shot.get("camera_movement", "固定"),
                        "duration_seconds": shot.get("duration_seconds", 8),
                        "description": shot.get("description", ""),
                        "audio_cue": shot.get("audio_note", shot.get("tiktok_note", "")),
                        "generation_prompt": _generate_shot_prompt_with_portraits(shot, shot_portraits),
                        "reference_portraits": shot_portraits,
                        "reference_image_urls": [p["portrait_url"] for p in shot_portraits],
                        "status": "pending"
                    })

        logger.info(f"  📊 共生成 {len(shots_with_portraits)} 个镜头")

        # ========== 第四步：保存项目 ==========
        logger.info(f"💾 [步骤4/4] 保存项目数据...")

        project_name = f"{safe_title}_{video_type}"
        project_dir = Path(f"视频项目/{project_name}")
        project_dir.mkdir(parents=True, exist_ok=True)

        storyboard_data = {
            "project_name": project_name,
            "novel_title": title,
            "video_type": video_type,
            "visual_style_guide": video_result.get("visual_style_guide", {}),
            "units": units,
            "character_portraits": portrait_results,
            "total_episodes": len(units),
            "total_shots": len(shots_with_portraits),
            "creation_time": __import__('datetime').datetime.now().isoformat()
        }

        storyboard_file = project_dir / f"{project_name}_storyboard.json"
        with open(storyboard_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(storyboard, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 项目已保存: {storyboard_file}")

        # 返回结果
        return jsonify({
            "success": True,
            "project_name": project_name,
            "workflow": "portrait_first",
            "character_portraits": portrait_results,
            "total_shots": len(shots_with_portraits),
            "total_episodes": len(units),
            "shots": shots_with_portraits,
            "storyboard": storyboard_data,
            "next_step": "使用 /video/generate-shots 逐镜头生成视频"
        })

    except Exception as e:
        logger.error(f"❌ [PORTRAIT-FIRST] 工作流执行失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/generate-shots', methods=['POST'])
@login_required
def generate_shots_portrait_first():
    """
    逐镜头生成视频（使用角色剧照作为参考）

    请求参数：
    {
        "project_name": "项目名称",
        "shot_indices": [0, 1, 2, ...],  // 要生成的镜头索引，不指定则全部生成
        "orientation": "portrait",  // 视频方向
        "duration": 10  // 单个视频时长（秒）
    }
    """
    try:
        data = request.json or {}
        project_name = data.get('project_name')
        shot_indices = data.get('shot_indices', [])
        orientation = data.get('orientation', 'portrait')
        duration = data.get('duration', 10)

        if not project_name:
            return jsonify({"success": False, "error": "项目名称不能为空"}), 400

        logger.info(f"🎬 [GENERATE-SHOTS] 开始生成镜头: {project_name}")

        # 加载项目数据
        project_dir = Path(f"视频项目/{project_name}")
        storyboard_file = project_dir / f"{project_name}_storyboard.json"

        if not storyboard_file.exists():
            return jsonify({"success": False, "error": "项目不存在"}), 404

        with open(storyboard_file, 'r', encoding='utf-8') as f:
            import json
            storyboard_data = json.load(f)

        # 获取角色剧照
        character_portraits = storyboard_data.get("character_portraits", [])
        portrait_map = {p["character_id"]: p["portrait_url"] for p in character_portraits if p.get("status") == "completed"}

        # 获取镜头序列（从shots字段或重新生成）
        shots = storyboard_data.get("shots", [])
        if not shots:
            return jsonify({"success": False, "error": "项目没有镜头数据"}), 400

        # 过滤要生成的镜头
        shots_to_generate = shots
        if shot_indices:
            shots_to_generate = [s for s in shots if s["shot_index"] in shot_indices]

        logger.info(f"  📊 需要生成 {len(shots_to_generate)} 个镜头")

        # 这里返回任务信息，实际生成由前端调用video API完成
        return jsonify({
            "success": True,
            "project_name": project_name,
            "total_shots": len(shots),
            "shots_to_generate": len(shots_to_generate),
            "shots": shots_to_generate,
            "portrait_map": portrait_map,
            "instruction": "对每个镜头调用 /api/veo/generate，使用 reference_image_urls 作为参考图"
        })

    except Exception as e:
        logger.error(f"❌ [GENERATE-SHOTS] 处理失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _extract_characters_from_events(events: list) -> dict:
    """
    从事件中提取角色信息

    返回: {character_id: {name, appearance, role}}
    """
    characters = {}

    for event in events:
        # 从事件描述中识别角色
        event_name = event.get('name', '')
        event_desc = event.get('description', '')
        composition = event.get('composition', {})

        # 检查composition中的各个阶段
        for stage_key in ['起因', '发展', '高潮', '结局', '起', '承', '转', '合']:
            stage_data = composition.get(stage_key, {})
            if not stage_data:
                continue

            # 提取角色信息
            stage_name = stage_data.get('name', '')
            stage_desc = stage_data.get('description', '')

            # 尝试解析角色名
            import re
            # 匹配中文角色名模式
            char_pattern = r'([一-龥]{2,4})(?:说|道|想|看|听|做|动作|表情|神态|出手|攻击)'
            chars_in_stage = re.findall(char_pattern, stage_name + stage_desc)

            for char_name in set(chars_in_stage):
                char_id = f"char_{hash(char_name) % 10000}"
                if char_id not in characters:
                    # 从事件上下文推断角色特征
                    characters[char_id] = {
                        "id": char_id,
                        "name": char_name,
                        "role": _infer_character_role(char_name, event),
                        "appearance": _infer_character_appearance(char_name, event),
                        "first_appearance": event_name
                    }

    return characters


def _infer_character_role(char_name: str, event: dict) -> str:
    """推断角色身份"""
    event_name = event.get('name', '')
    desc = event.get('description', '')

    if '主角' in desc or '男主' in desc or '女主' in desc:
        return '主角'
    elif '族长' in event_name or '长老' in event_name:
        return '族长/长老'
    elif '退婚' in event_name or '圣女' in event_name:
        return '外来者'
    elif '子孙' in event_name or '弟子' in event_name:
        return '家族成员'
    else:
        return '角色'


def _infer_character_appearance(char_name: str, event: dict) -> str:
    """推断角色外貌"""
    desc = event.get('description', '')

    # 基础外貌描述
    if '主角' in desc or '男主' in desc:
        return '年轻男性，面容英俊，眼神坚毅，气质不凡'
    elif '女主' in desc or '圣女' in desc or '少女' in desc:
        return '年轻女性，容貌绝美，气质出尘'
    elif '族长' in event.get('name', ''):
        return '中年男性，威严庄重，须发灰白，气场强大'
    else:
        return '古装人物，细节精致，表情生动'


def _identify_characters_in_scene(scene: dict, all_characters: dict) -> list:
    """
    识别场景中出现的角色

    返回: [character_id1, character_id2, ...]
    """
    scene_desc = scene.get('scene_description', '')
    char_ids = []

    for char_id, char_info in all_characters.items():
        char_name = char_info.get('name', '')
        if char_name in scene_desc:
            char_ids.append(char_id)

    return char_ids


def _generate_shot_prompt_with_portraits(shot: dict, portraits: list) -> str:
    """
    生成包含角色剧照参考的镜头prompt

    Args:
        shot: 镜头数据
        portraits: 该镜头中的角色剧照列表
    """
    base_prompt = f"""{shot.get('description', '')}
景别：{shot.get('shot_type', '中景')}
运镜：{shot.get('camera_movement', '固定')}
时长：{shot.get('duration_seconds', 8)}秒"""

    if portraits:
        char_names = ', '.join([p['character_name'] for p in portraits])
        base_prompt += f"""
出场角色：{char_names}
人物参考：请保持人物形象与参考剧照一致"""

    return base_prompt


@video_api.route('/video/adapt-to-short-drama', methods=['POST'])
@login_required
def adapt_to_short_drama():
    """
    短剧风格改造API

    将小说的叙事格式改造为短剧专用格式：
    1. 识别每个事件的核心情节点
    2. 添加开场钩子（前3秒抓人）
    3. 设计情绪峰值
    4. 添加结尾悬念
    5. 优化节奏（短剧特有的快节奏）

    请求参数：
    {
        "title": "小说标题",
        "selected_events": ["event_0", "event_1", ...],  // 可选
        "drama_type": "爽文"  // 爽文/悬疑/甜宠
    }
    """
    try:
        data = request.json or {}
        title = data.get('title')
        selected_events = data.get('selected_events', [])
        drama_type = data.get('drama_type', '爽文')

        if not title:
            return jsonify({"success": False, "error": "小说标题不能为空"}), 400

        logger.info(f"🎬 [SHORT_DRAMA] 开始短剧风格改造: {title}, 类型: {drama_type}")

        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({"success": False, "error": "小说项目不存在"}), 404

        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)

        # 提取原始事件
        all_events = event_extractor.extract_all_major_events(novel_detail)
        if selected_events:
            all_events = _filter_selected_events(all_events, selected_events, logger)

        logger.info(f"  📊 待改造事件: {len(all_events)} 个")

        # 进行短剧风格改造
        adapted_events = []
        for event in all_events:
            adapted = _adapt_event_to_short_drama(event, drama_type)
            adapted_events.append(adapted)
            logger.info(f"  ✅ 改造完成: {adapted['name']}")

        # 生成改造报告
        adaptation_report = {
            "original_events": len(all_events),
            "drama_type": drama_type,
            "adaptation_summary": _generate_adaptation_summary(adapted_events),
            "next_steps": [
                "1. 查看改造后的事件结构",
                "2. 确认情节点设计",
                "3. 继续生成剧照和视频"
            ]
        }

        return jsonify({
            "success": True,
            "title": title,
            "drama_type": drama_type,
            "original_events": len(all_events),
            "adapted_events": adapted_events,
            "report": adaptation_report
        })

    except Exception as e:
        logger.error(f"❌ [SHORT_DRAMA] 改造失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


def _adapt_event_to_short_drama(event: dict, drama_type: str) -> dict:
    """
    将单个事件改造为短剧格式

    短剧必需元素：
    - hook: 开场钩子（前3秒）
    - conflict_core: 核心冲突
    - emotional_beats: 情节点序列
    - climax: 高潮时刻
    - cliffhanger: 结尾悬念
    """
    event_name = event.get('name', '')
    event_desc = event.get('description', '')
    composition = event.get('composition', {})

    # 识别叙事阶段
    stages = ['起因', '发展', '高潮', '结局']
    if not any(composition.get(s) for s in stages):
        stages = ['起', '承', '转', '合']

    # 构建短剧格式
    adapted = {
        "original_name": event_name,
        "original_description": event_desc,
        "drama_type": drama_type,
        "chapter_range": event.get('chapter_range', ''),

        # 短剧核心元素
        "hook": _generate_hook(event, composition, drama_type),
        "conflict_core": _extract_conflict_core(event, composition),
        "emotional_beats": _generate_emotional_beats(event, composition, drama_type),
        "climax": _extract_climax(event, composition),
        "cliffhanger": _generate_cliffhanger(event, composition),

        # 保留原始composition结构，但添加短剧标记
        "composition": _enhance_composition_with_drama_tags(composition, drama_type)
    }

    # 生成短剧专用的事件名
    adapted['name'] = _generate_short_drama_event_name(event, drama_type)

    return adapted


def _generate_hook(event: dict, composition: dict, drama_type: str) -> dict:
    """生成开场钩子（前3秒抓人）"""
    event_name = event.get('name', '')
    event_desc = event.get('description', '')

    # 根据事件类型生成钩子
    if '退婚' in event_name:
        hook = {
            "visual": "高堂之上，圣女居高临下，一纸退婚书扔在案前",
            "text": "退婚？好！今日之耻，我记下了！",
            "duration": 3,
            "purpose": "立即建立冲突，激发观众期待"
        }
    elif '穿越' in event_name or '牌位' in event_name:
        hook = {
            "visual": "黑暗的祠堂，牌位发出金光，周围族人跪地瑟瑟发抖",
            "text": "我穿越成了家族牌位？而且家族今晚就要被灭门？",
            "duration": 3,
            "purpose": "抛出绝境设定，制造悬念"
        }
    elif '心声' in event_name:
        hook = {
            "visual": "金色文字环绕族长，所有族人惊恐跪地",
            "text": "这是...先祖显灵？族长的心声竟然能被听到！",
            "duration": 3,
            "purpose": "揭示金手指，爽感释放"
        }
    else:
        # 通用钩子
        hook = {
            "visual": _extract_visual_key_moment(event_desc),
            "text": _generate_hook_text(event_name, drama_type),
            "duration": 3,
            "purpose": "快速抓人"
        }

    return hook


def _generate_hook_text(event_name: str, drama_type: str) -> str:
    """生成钩子文案"""
    hooks = {
        '爽文': [
            "三十年河东，三十年河西，莫欺少年穷！",
            "今日之辱，来日百倍奉还！",
            "既然你们不仁，就休怪我不义！"
        ],
        '悬疑': [
            "这一切，都在我的算计之中...",
            "你以为这是巧合？不，这是命运的安排。",
            "真相，往往隐藏在最不起眼的地方。"
        ],
        '甜宠': [
            "这一眼，便是一眼万年。",
            "原来你一直都在这里。",
            "所有的相遇，都是久别重逢。"
        ]
    }

    import random
    type_hooks = hooks.get(drama_type, hooks['爽文'])
    return random.choice(type_hooks)


def _extract_visual_key_moment(description: str) -> str:
    """从描述中提取视觉关键时刻"""
    if '祠堂' in description:
        return "破旧祠堂，香火摇曳，气氛压抑"
    elif '大殿' in description or '退婚' in description:
        return "宏伟大殿，气氛紧张，众目睽睽"
    elif '战场' in description:
        return "战场硝烟，刀光剑影，生死一线"
    else:
        return "关键时刻来临"


def _extract_conflict_core(event: dict, composition: dict) -> dict:
    """提取核心冲突"""
    event_name = event.get('name', '')

    if '退婚' in event_name:
        return {
            "sides": ["主角（被退婚）", "女方（圣女/大宗门）"],
            "contradiction": "实力悬殊，身份不平等",
            "escalation": "从受辱到反击的转变"
        }
    elif '心声' in event_name:
        return {
            "sides": ["主角（心声泄露）", "族人（从怀疑到跪拜）"],
            "contradiction": "认知错位，真相惊人",
            "escalation": "从被误解到被膜拜"
        }
    else:
        # 通用冲突提取
        return {
            "sides": ["主角方", "对手方"],
            "contradiction": "利益冲突/理念冲突",
            "escalation": "冲突逐步升级"
        }


def _generate_emotional_beats(event: dict, composition: dict, drama_type: str) -> list:
    """生成情节点序列"""
    event_name = event.get('name', '')

    # 根据事件类型生成不同的情节点
    if '退婚' in event_name:
        beats = [
            {"beat": "压抑", "content": "圣女居高临下，家族低头哈腰", "duration": 15},
            {"beat": "羞辱", "content": "退婚书扔出，全族震怒", "duration": 10},
            {"beat": "转折", "content": "主角淡然接受，反而道谢", "duration": 10},
            {"beat": "铺垫", "content": "族长不解，气氛微妙", "duration": 10}
        ]
    elif '心声' in event_name:
        beats = [
            {"beat": "质疑", "content": "族长突然说话，族人惊恐", "duration": 10},
            {"beat": "泄露", "content": "心声说出众人秘密", "duration": 15},
            {"beat": "震撼", "content": "金色文字环绕，族人跪拜", "duration": 15},
            {"beat": "敬畏", "content": "先祖显灵，地位确立", "duration": 10}
        ]
    else:
        # 通用情节点（4幕结构）
        beats = [
            {"beat": "起", "content": "冲突建立，局势紧张", "duration": 15},
            {"beat": "承", "content": "矛盾升级，信息密集", "duration": 20},
            {"beat": "转", "content": "意外发生，局势逆转", "duration": 20},
            {"beat": "合", "content": "结果揭晓，情绪释放", "duration": 10}
        ]

    return beats


def _extract_climax(event: dict, composition: dict) -> dict:
    """提取高潮时刻"""
    event_name = event.get('name', '')

    if '退婚' in event_name:
        return {
            "moment": "主角道谢时，全场哗然，众人不解其意",
            "visual": "主角淡然一笑，转身离去，圣女若有所思",
            "emotional_peak": "爽感释放 - 以退为进，格局打开"
        }
    elif '心声' in event_name:
        return {
            "moment": "金色文字环绕族长，所有族人跪地膜拜",
            "visual": "神圣景象，金光璀璨，震撼视觉",
            "emotional_peak": "身份揭晓 - 从牌位到先祖"
        }
    else:
        return {
            "moment": "关键时刻来临",
            "visual": "高光时刻，情绪达到顶点",
            "emotional_peak": "情绪爆发"
        }


def _generate_cliffhanger(event: dict, composition: dict) -> dict:
    """生成结尾悬念"""
    event_name = event.get('name', '')
    event_desc = event.get('description', '')

    # 根据事件类型生成悬念
    if '退婚' in event_name:
        return {
            "text": "圣女看着主角离去的背影，若有所思...",
            "next_hook": "三日后，太乙圣地的人会再来...",
            "purpose": "为后续剧情埋下伏笔"
        }
    elif '心声' in event_name:
        return {
            "text": "然而，被灭门的危机倒计时仍在继续...",
            "next_hook": "仇敌今夜就会到来，家族能否逃过此劫？",
            "purpose": "制造紧迫感，吸引看下集"
        }
    else:
        return {
            "text": "更大的风暴即将来临...",
            "next_hook": "下一集，新的挑战等待着你",
            "purpose": "保持观众观看欲望"
        }


def _enhance_composition_with_drama_tags(composition: dict, drama_type: str) -> dict:
    """为composition添加短剧标签"""
    enhanced = {}

    stage_mapping = {
        '起因': 'hook',
        '发展': 'buildup',
        '高潮': 'climax',
        '结局': 'cliffhanger',
        '起': 'hook',
        '承': 'buildup',
        '转': 'climax',
        '合': 'cliffhanger'
    }

    for stage_key, stage_data in composition.items():
        if stage_data:
            stage_data['short_drama_role'] = stage_mapping.get(stage_key, 'buildup')
            stage_data['drama_type'] = drama_type
            enhanced[stage_key] = stage_data

    return enhanced


def _generate_short_drama_event_name(event: dict, drama_type: str) -> str:
    """生成短剧风格的事件名"""
    original_name = event.get('name', '')

    # 短剧风格的事件名需要更吸引人
    name_map = {
        '地狱开局': "【开场】穿越成牌位，死期倒计时",
        '神级反转': "【高潮】退婚现场，主角道谢谢全场",
        '祠堂惊变': "【爆点】心声泄露，全族当场吓跪"
    }

    # 如果有直接映射，使用映射
    for key, value in name_map.items():
        if key in original_name:
            return value

    # 否则添加短剧标签
    drama_tags = {
        '爽文': '【爽点】',
        '悬疑': '【谜题】',
        '甜宠': '【糖点】'
    }

    tag = drama_tags.get(drama_type, '【精彩】')
    return f"{tag} {original_name}"


def _generate_adaptation_summary(events: list) -> str:
    """生成改造摘要"""
    total_hooks = len([e for e in events if e.get('hook')])
    total_cliffhangers = len([e for e in events if e.get('cliffhanger')])

    return f"""改造完成！共{len(events)}个事件已转换为短剧格式：

✅ 开场钩子: {total_hooks}个（确保前3秒抓人）
✅ 情节点: 总计{sum(len(e.get('emotional_beats', [])) for e in events)}个
✅ 高潮时刻: {len(events)}个
✅ 结尾悬念: {total_cliffhangers}个（确保看下集）

格式特点：
- 节奏紧凑，无冗余信息
- 情绪递进，爽点/悬念密集
- 每集独立完整，但有关联
- 适配8-10秒短视频格式"""


@video_api.route('/video/style-conversion', methods=['POST'])
@login_required
def style_conversion():
    """
    统一工作流 - 步骤1：风格转换

    将小说内容转换为选定视频风格的格式

    请求参数：
    {
        "title": "小说标题",
        "video_type": "视频类型",
        "selected_events": ["event1", "event2"],
        "selected_characters": ["char1", "char2"]
    }
    """
    try:
        data = request.get_json()
        title = data.get('title')
        video_type = data.get('video_type')
        selected_events = data.get('selected_events', [])

        if not title:
            return jsonify({'success': False, 'error': '缺少小说标题'}), 400

        if not manager:
            return jsonify({'success': False, 'error': '管理器未初始化'}), 500

        logger.info(f"🎨 [风格转换] 开始转换: {title} -> {video_type}")

        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({'success': False, 'error': f'找不到小说: {title}'}), 404

        # 获取事件提取器
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)

        # 提取角色数据（用于统计）
        characters = event_extractor.extract_character_designs(novel_detail)

        # 生成风格转换预览
        type_names = {
            'short_film': '短片/动画电影',
            'long_series': '长篇剧集',
            'short_video': '短视频系列'
        }

        converted_preview = f"""【风格转换完成】

原始小说：{title}
目标类型：{type_names.get(video_type, video_type)}

转换说明：
- ✓ 内容已适配{type_names.get(video_type, video_type)}的叙事节奏
- ✓ 选中{len(selected_events)}个事件进行转换
- ✓ 共{len(characters)}个角色将参与视频制作

下一步：生成角色剧照以固定角色形象
"""

        return jsonify({
            'success': True,
            'video_type': video_type,
            'event_count': len(selected_events),
            'character_count': len(characters),
            'converted_preview': converted_preview
        })

    except Exception as e:
        logger.error(f"风格转换失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@video_api.route('/video/generate-batch-portraits', methods=['POST'])
@login_required
def generate_batch_portraits():
    """
    统一工作流 - 步骤2：批量生成角色剧照

    为多个角色批量生成剧照

    请求参数：
    {
        "title": "小说标题",
        "characters": [
            {"id": "char1", "name": "张三", "role": "主角", "appearance": "..."},
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        title = data.get('title')
        characters = data.get('characters', [])

        if not title:
            return jsonify({'success': False, 'error': '缺少小说标题'}), 400

        if not manager:
            return jsonify({'success': False, 'error': '管理器未初始化'}), 500

        logger.info(f"📸 [批量剧照] 开始生成 {len(characters)} 个角色的剧照")

        # 获取小说数据
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({'success': False, 'error': f'找不到小说: {title}'}), 404

        # 获取事件提取器
        from src.managers.EventExtractor import get_event_extractor
        event_extractor = get_event_extractor(logger)

        # 提取角色数据
        all_characters = event_extractor.extract_character_designs(novel_detail)

        # 限制最多生成3个角色（避免超时）
        characters_to_generate = characters[:3]
        logger.info(f"📸 [批量剧照] 将生成 {len(characters_to_generate)} 个角色剧照")

        portraits = []
        from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
        generator = NanoBananaImageGenerator()
        import os
        import urllib.parse

        for idx, char in enumerate(characters_to_generate):
            char_name = char.get('name')
            char_id = char.get('id')
            char_role = char.get('role', '角色')

            logger.info(f"📸 [批量剧照] 正在生成角色 {idx+1}/{len(characters_to_generate)}: {char_name}")

            # 从完整角色列表中查找详细信息
            char_detail = None
            for c in all_characters:
                if c.get('name') == char_name or c.get('id') == char_id:
                    char_detail = c
                    break

            if not char_detail:
                logger.warn(f"⚠️ [批量剧照] 找不到角色详情: {char_name}")
                continue

            # 生成角色提示词
            character_prompts = event_extractor.generate_character_prompts([char_detail])
            if not character_prompts:
                logger.warn(f"⚠️ [批量剧照] 生成角色提示词失败: {char_name}")
                continue

            prompt = character_prompts[0].get('generation_prompt', '')

            # 生成文件名
            safe_name = char_name.replace(' ', '_').replace('/', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{title}_{safe_name}_portrait_{timestamp}"

            # 调用图像生成器
            try:
                result = generator.generate_image(
                    prompt=prompt,
                    aspect_ratio='9:16',  # 竖屏适合角色展示
                    image_size='4K',
                    save_path=None,
                    reference_images=[]
                )

                if result.get('success'):
                    # 构建HTTP访问路径
                    image_filename = os.path.basename(result.get('local_path', ''))
                    encoded_filename = urllib.parse.quote(image_filename)
                    image_url = f"/generated_images/{encoded_filename}"

                    logger.info(f"✅ [批量剧照] {char_name} 剧照生成成功: {image_url}")

                    portraits.append({
                        'characterId': char_id,
                        'characterName': char_name,
                        'characterRole': char_role,
                        'imageUrl': image_url,
                        'localPath': result.get('local_path'),
                        'prompt': prompt
                    })
                else:
                    logger.error(f"❌ [批量剧照] {char_name} 生成失败: {result.get('error')}")
                    # 添加失败的条目，标记为失败
                    portraits.append({
                        'characterId': char_id,
                        'characterName': char_name,
                        'characterRole': char_role,
                        'imageUrl': None,
                        'error': result.get('error', '生成失败'),
                        'status': 'failed'
                    })
            except Exception as e:
                logger.error(f"❌ [批量剧照] {char_name} 生成异常: {str(e)}")
                portraits.append({
                    'characterId': char_id,
                    'characterName': char_name,
                    'characterRole': char_role,
                    'imageUrl': None,
                    'error': str(e),
                    'status': 'error'
                })

        return jsonify({
            'success': True,
            'portraits': portraits,
            'total': len(portraits),
            'successful': len([p for p in portraits if p.get('imageUrl')]),
            'failed': len([p for p in portraits if not p.get('imageUrl')])
        })

    except Exception as e:
        logger.error(f"批量剧照生成失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@video_api.route('/projects', methods=['GET'])
@login_required
def get_video_projects():
    """
    获取视频项目列表

    返回所有创建的视频制作项目
    """
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        projects = []

        # 从tasks/video_tasks目录读取项目信息
        tasks_dir = os.path.join(BASE_DIR, 'tasks', 'video_tasks')
        if os.path.exists(tasks_dir):
            for task_file in os.listdir(tasks_dir):
                if task_file.endswith('.json'):
                    try:
                        with open(os.path.join(tasks_dir, task_file), 'r', encoding='utf-8') as f:
                            task_data = json.load(f)

                        projects.append({
                            'id': task_file.replace('.json', ''),
                            'title': task_data.get('project_name', task_file.replace('.json', '')),
                            'novel_title': task_data.get('novel_title', ''),
                            'status': task_data.get('status', 'pending'),
                            'total_episodes': task_data.get('total_shots', 0),
                            'character_count': len(task_data.get('characters', [])),
                            'portrait_count': task_data.get('portrait_count', 0),
                            'created_at': task_data.get('created_at', ''),
                            'progress': calculate_progress(task_data)
                        })
                    except Exception as e:
                        logger.warn(f"读取项目文件 {task_file} 失败: {e}")

        # 同时也检查直接创建的项目文件
        projects_dir = os.path.join(BASE_DIR, 'video_projects')
        if os.path.exists(projects_dir):
            for proj_file in os.listdir(projects_dir):
                if proj_file.endswith('.json'):
                    try:
                        with open(os.path.join(projects_dir, proj_file), 'r', encoding='utf-8') as f:
                            proj_data = json.load(f)

                        # 检查是否已经在列表中
                        existing = next((p for p in projects if p['id'] == proj_file.replace('.json', '')), None)
                        if existing:
                            continue

                        projects.append({
                            'id': proj_file.replace('.json', ''),
                            'title': proj_data.get('title', proj_file.replace('.json', '')),
                            'novel_title': proj_data.get('novel_title', ''),
                            'status': proj_data.get('status', 'draft'),
                            'total_episodes': proj_data.get('total_episodes', 0),
                            'character_count': len(proj_data.get('characters', [])),
                            'portrait_count': len(proj_data.get('portraits', {})),
                            'created_at': proj_data.get('created_at', ''),
                            'progress': 0
                        })
                    except Exception as e:
                        logger.warn(f"读取项目文件 {proj_file} 失败: {e}")

        return jsonify({
            'success': True,
            'projects': projects,
            'total': len(projects)
        })

    except Exception as e:
        logger.error(f"获取项目列表失败: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


def calculate_progress(task_data):
    """计算项目进度"""
    total_shots = task_data.get('total_shots', 0)
    if total_shots == 0:
        return 0

    completed_shots = task_data.get('completed_shots', 0)
    return (completed_shots / total_shots) * 100


@video_api.route('/stats', methods=['GET'])
@login_required
def get_video_stats():
    """
    获取视频制作统计数据

    返回小说项目数、剧照数、视频数、任务数等统计信息
    """
    try:
        if not manager:
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        stats = {
            'novel_count': 0,
            'portrait_count': 0,
            'video_count': 0,
            'task_count': 0,
            'project_count': 0
        }

        # 获取所有小说项目
        all_projects = manager.get_novel_projects()
        stats['novel_count'] = len(all_projects)

        # 统计剧照数量（检查generated_images目录）
        try:
            images_dir = os.path.join(BASE_DIR, 'generated_images')
            if os.path.exists(images_dir):
                portrait_files = [f for f in os.listdir(images_dir) if f.endswith('.png') or f.endswith('.jpg')]
                stats['portrait_count'] = len(portrait_files)
        except Exception as e:
            logger.warn(f"统计剧照失败: {e}")

        # 统计视频数量（检查generated_videos目录）
        try:
            videos_dir = os.path.join(BASE_DIR, 'generated_videos')
            if os.path.exists(videos_dir):
                video_files = [f for f in os.listdir(videos_dir) if f.endswith('.mp4')]
                stats['video_count'] = len(video_files)
        except Exception as e:
            logger.warn(f"统计视频失败: {e}")

        # 统计任务数量（检查tasks目录）
        try:
            tasks_dir = os.path.join(BASE_DIR, 'tasks', 'video_tasks')
            if os.path.exists(tasks_dir):
                task_files = [f for f in os.listdir(tasks_dir) if f.endswith('.json')]
                stats['task_count'] = len(task_files)
        except Exception as e:
            logger.warn(f"统计任务失败: {e}")

        return jsonify({
            'success': True,
            **stats
        })

    except Exception as e:
        logger.error(f"获取统计数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@video_api.route('/video/convert-to-short-drama', methods=['POST'])
@login_required
def convert_to_short_drama():
    """
    将小说转换为短剧风格

    请求参数:
    {
        "novel_title": "小说标题"
    }

    返回:
    {
        "success": true,
        "sample_original": "原始内容示例",
        "sample_converted": "短剧风格内容示例",
        "stats": {...}
    }
    """
    try:
        logger.info("=" * 60)
        logger.info("🎭 [短剧转换] 收到转换请求")

        if not manager:
            logger.error("❌ [短剧转换] 管理器未初始化")
            return jsonify({"success": False, "error": "管理器未初始化"}), 500

        data = request.get_json()
        logger.info(f"📦 [短剧转换] 请求数据: {data}")

        novel_title = data.get('novel_title')
        if not novel_title:
            logger.error("❌ [短剧转换] 缺少小说标题")
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        logger.info(f"📚 [短剧转换] 小说标题: {novel_title}")

        # 获取小说详情
        novel_detail = manager.get_novel_detail(novel_title)
        if not novel_detail:
            logger.error(f"❌ [短剧转换] 找不到小说: {novel_title}")
            return jsonify({"success": False, "error": f"找不到该小说: {novel_title}"}), 404

        logger.info(f"✅ [短剧转换] 找到小说，keys: {list(novel_detail.keys())[:10]}")

        # 尝试多种方式获取事件数据
        events = novel_detail.get('events', [])
        if not events:
            events = novel_detail.get('major_events', [])
        if not events:
            events = novel_detail.get('medium_events', [])
        if not events:
            # 尝试从storyline获取
            storyline = novel_detail.get('storyline', {})
            if isinstance(storyline, dict):
                events = storyline.get('events', [])
            elif isinstance(storyline, list):
                events = storyline

        logger.info(f"📊 [短剧转换] 找到事件数量: {len(events) if events else 0}")

        # 获取角色信息
        characters = novel_detail.get('characters', [])
        if not characters:
            characters = novel_detail.get('character_profiles', [])

        # 获取小说描述
        description = novel_detail.get('description', '')
        premise = novel_detail.get('premise', '')
        summary = novel_detail.get('summary', '')

        # 选择一个事件作为示例，如果没有事件则使用小说描述
        if events and len(events) > 0:
            sample_event = events[0]
            if isinstance(sample_event, dict):
                event_title = sample_event.get('title', sample_event.get('name', '未知事件'))
                event_description = sample_event.get('description', sample_event.get('content', sample_event.get('summary', '')))
            else:
                event_title = "事件"
                event_description = str(sample_event)
        else:
            # 没有事件时使用小说描述
            event_title = novel_title
            event_description = description or premise or summary or f"《{novel_title}》是一部精彩的作品"

        # 确保描述不为空
        if not event_description or len(event_description) < 10:
            event_description = f"这是《{novel_title}》的故事内容，讲述了精彩的情节和动人的故事。"

        logger.info(f"📝 [短剧转换] 事件标题: {event_title}, 描述长度: {len(event_description)}")

        # 构建原始内容
        original_content = f"""【事件标题】{event_title}

【原始内容】
{event_description}"""

        # 构建短剧风格内容（添加钩子、悬念等）
        preview_text = event_description[:80] + "..." if len(event_description) > 80 else event_description

        converted_content = f"""🎬 【短剧脚本】{event_title}

【开场钩子】
（3秒黄金开场 - 紧抓观众注意力）
{preview_text}

【悬念设置】
（5秒处抛出悬念）
真相到底是什么？让我们一起来看...

【剧情推进】
{event_description}

【卡点留白】
（结尾悬念 - 引导继续观看）
接下来会发生什么？点击下方继续观看..."""

        # 统计信息
        stats = {
            'total_events': len(events) if events else 0,
            'total_characters': len(characters) if characters else 0,
            'estimated_episodes': len(events) if events else 10,
            'novel_title': novel_title
        }

        logger.info(f"✅ [短剧转换] 转换完成! 事件数: {stats['total_events']}, 角色数: {stats['total_characters']}")
        logger.info("=" * 60)

        return jsonify({
            "success": True,
            "sample_original": original_content,
            "sample_converted": converted_content,
            "stats": stats,
            "novel_data": {
                "title": novel_title,
                "events": (events or [])[:10],
                "characters": (characters or [])[:20]
            }
        })

    except Exception as e:
        logger.error(f"❌ [短剧转换] 转换失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/episode-workflow/check-storyboards', methods=['POST'])
@login_required
def check_episode_storyboards():
    """
    检查分镜头文件是否已存在

    请求参数:
    {
        "novel_title": "小说标题",
        "episodes": [
            {"id": "major_event_0_event_0_0", "title": "诈尸惊魂..."}
        ]
    }

    响应:
    {
        "success": true,
        "existing_storyboards": {
            "major_event_0_event_0_0": {"title": "...", "path": "..."},
            ...
        },
        "missing_episodes": ["major_event_0_event_1_0", ...]
    }
    """
    try:
        data = request.json or {}
        novel_title = data.get('novel_title', '')
        episodes = data.get('episodes', [])

        logger.info(f"🔍 [检查分镜头] 检查 {len(episodes)} 集的分镜头文件")

        existing_storyboards = {}
        missing_episodes = []

        for episode in episodes:
            episode_id = episode.get('id', '')
            episode_title = episode.get('title', '')

            # 尝试加载分镜头文件
            storyboard_data = _load_storyboard_file(novel_title, episode_title, episode_id)

            if storyboard_data:
                existing_storyboards[episode_id] = {
                    'title': storyboard_data.get('video_title', episode_title),
                    'episode_title': episode_title,
                    'shots_count': len(storyboard_data.get('shots', [])),
                    'data': storyboard_data
                }
                logger.info(f"  ✅ 找到分镜头: {episode_title}")
            else:
                missing_episodes.append(episode_id)
                logger.info(f"  ❌ 未找到分镜头: {episode_title}")

        return jsonify({
            "success": True,
            "existing_storyboards": existing_storyboards,
            "missing_episodes": missing_episodes,
            "total_checked": len(episodes),
            "existing_count": len(existing_storyboards),
            "missing_count": len(missing_episodes)
        })

    except Exception as e:
        logger.error(f"❌ [检查分镜头] 检查失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@video_api.route('/video/episode-workflow/generate-storyboard', methods=['POST'])
@login_required
def generate_episode_storyboard():
    """
    按集制作工作流 - 为选中的集数生成分镜头脚本

    请求参数:
    {
        "novel_title": "小说标题",
        "episodes": [
            {
                "id": "major_event_16_event_0_0",
                "title": "天道成了看门狗",
                "stage": "起",
                "major_event": "这界太小，准备搬家"
            },
            ...
        ]
    }

    返回:
    {
        "success": true,
        "storyboards": {
            "major_event_16_event_0_0": {
                "title": "天道成了看门狗",
                "scenes": [...]
            },
            ...
        }
    }
    """
    try:
        data = request.get_json()
        novel_title = data.get('novel_title')
        episodes = data.get('episodes', [])

        if not novel_title:
            return jsonify({"success": False, "error": "缺少小说标题"}), 400

        if not episodes:
            return jsonify({"success": False, "error": "没有选中任何集数"}), 400

        logger.info(f"🎬 [按集制作] 开始为 {len(episodes)} 集生成分镜头脚本")
        logger.info(f"📚 [按集制作] 小说: {novel_title}")

        # 获取小说详情
        novel_detail = manager.get_novel_detail(novel_title)
        if not novel_detail:
            return jsonify({"success": False, "error": f"找不到小说: {novel_title}"}), 404

        # 获取角色信息用于生成分镜头
        characters = novel_detail.get('characters', [])
        character_profiles = []
        for char in characters:
            if isinstance(char, dict):
                char_name = char.get('name', '')
                char_desc = char.get('description', char.get('appearance', ''))
                if char_name:
                    character_profiles.append(f"{char_name}: {char_desc}")
            elif isinstance(char, str):
                character_profiles.append(char)

        # 🔥 使用AI生成分镜头
        storyboards = {}

        for episode in episodes:
            episode_id = episode.get('id')
            episode_title = episode.get('title', '未知标题')
            episode_stage = episode.get('stage', '')

            logger.info(f"  📺 [按集制作] 使用AI生成分镜头: {episode_title} ({episode_stage})")

            # 🔥 调用AI生成分镜头（传递小说标题和剧集信息）
            storyboard_result = _generate_storyboard_with_ai(novel_title, episode)

            if storyboard_result:
                # AI生成成功，使用AI结果
                shots = storyboard_result.get('shots', [])

                # 🔥 修复：转换为正确的场景格式
                # 前端期望每个场景有 shot_sequence 数组
                scenes = []
                for shot in shots:
                    # 将每个镜头包装为一个场景
                    scene_title = shot.get('screen_action', '')[:50] if shot.get('screen_action') else f"镜头{shot.get('shot_number', 1)}"

                    # 🔥 新格式支持：提取角色信息
                    shot_characters = shot.get('characters', [])

                    scenes.append({
                        'scene_number': shot.get('shot_number', 1),
                        'scene_title': scene_title,
                        'location': shot.get('location', '场景'),
                        'estimated_duration_seconds': shot.get('duration', 8),
                        'shot_sequence': [{  # 🔥 关键：将镜头包装在 shot_sequence 数组中
                            'shot_number': shot.get('shot_number', 1),
                            'shot_type': shot.get('shot_type', '中景'),
                            'camera_movement': shot.get('shot_type', '中景'),
                            'duration': shot.get('duration', 8),
                            'description': shot.get('screen_action', shot.get('description', '')),
                            'dialogue': shot.get('dialogue', ''),
                            'audio_note': shot.get('audio', shot.get('audio_note', '背景音乐')),
                            'veo_prompt': shot.get('veo_prompt', ''),
                            'plot_points': [shot.get('plot_content', '')] if shot.get('plot_content') else shot.get('plot_points', []),
                            # 🔥 新增：角色信息（用于视频生成时匹配参考图）
                            'characters': shot_characters
                        }]
                    })

                # 🔥 新增：提取角色参考图映射
                character_images = storyboard_result.get('character_images', [])

                storyboards[episode_id] = {
                    'title': storyboard_result.get('video_title', episode_title),
                    'stage': episode_stage,
                    'scenes': scenes,
                    'total_duration': sum(s['estimated_duration_seconds'] for s in scenes),
                    'hook': storyboard_result.get('hook', ''),
                    'ending_hook': storyboard_result.get('ending_hook', ''),
                    'ai_generated': True,
                    # 🔥 新增：角色参考图映射（用于前端显示和视频生成）
                    'character_images': character_images
                }

                logger.info(f"  ✅ [按集制作] AI生成分镜头成功: {len(scenes)} 个场景, {len(character_images)} 个角色")
            else:
                # AI生成失败，回退到原有逻辑
                logger.warn(f"  ⚠️ [按集制作] AI生成失败，使用备用方案")

                # 根据剧集的阶段调整内容风格
                stage_descriptions = {
                    '起': '开篇引入，设定悬念',
                    '承': '情节推进，矛盾升级',
                    '转': '剧情转折，意外发生',
                    '合': '高潮结局，收尾呼应'
                }

                stage_note = stage_descriptions.get(episode_stage, '')

                # 提取事件数据和角色信息用于生成详细提示语
                event_content = episode.get('content', [])
                if isinstance(event_content, list) and event_content:
                    event_description = '，'.join(event_content[:3])
                else:
                    event_description = episode.get('description', episode.get('plot_outline', ''))

                event_data = {
                    'description': event_description,
                    'content': event_content,
                    'location': episode.get('location', ''),
                    'characters': episode.get('characters', [])
                }

                # 使用原有逻辑生成分镜头场景
                scenes = _generate_episode_scenes(
                    episode_title,
                    episode_stage,
                    stage_note,
                    novel_title,
                    character_profiles,
                    event_data
                )

                storyboards[episode_id] = {
                    'title': episode_title,
                    'stage': episode_stage,
                    'scenes': scenes,
                    'ai_generated': False
                }

        logger.info(f"✅ [按集制作] 分镜头生成完成，共 {len(storyboards)} 集")

        return jsonify({
            "success": True,
            "storyboards": storyboards,
            "total_episodes": len(storyboards),
            "message": f"已为 {len(storyboards)} 集生成分镜头脚本"
        })

    except Exception as e:
        logger.error(f"❌ [按集制作] 分镜头生成失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


def _generate_episode_scenes(episode_title: str, stage: str, stage_note: str,
                              novel_title: str, character_profiles: list,
                              event_data: dict = None) -> list:
    """
    为单个剧集生成场景分镜头

    Args:
        episode_title: 剧集标题
        stage: 剧集阶段（起承转合）
        stage_note: 阶段说明
        novel_title: 小说标题
        character_profiles: 角色档案列表
        event_data: 事件数据（包含描述、地点、角色等）

    Returns:
        场景列表
    """
    event_data = event_data or {}

    # 根据不同阶段生成不同数量的场景
    scene_counts = {
        '起': 4,
        '承': 5,
        '转': 4,
        '合': 5
    }

    num_scenes = scene_counts.get(stage, 4)
    scenes = []

    # 提取事件中的角色列表
    event_characters = event_data.get('characters', [])
    if isinstance(event_characters, str):
        # 如果是字符串，尝试解析
        event_characters = [c.strip() for c in event_characters.split(',') if c.strip()]

    for i in range(num_scenes):
        scene_num = i + 1

        # 生成场景标题
        scene_templates = {
            '起': ['开篇亮相', '悬念引入', '事件发生', '埋下伏笔'],
            '承': ['情节展开', '矛盾升级', '多方博弈', '局势变化', '推向高潮'],
            '转': ['意外转折', '真相揭露', '危机爆发', '峰回路转'],
            '合': ['终极对决', '高潮爆发', '尘埃落定', '余韵悠长', '新的开始']
        }

        templates = scene_templates.get(stage, ['场景一', '场景二', '场景三', '场景四'])
        scene_title = templates[i] if i < len(templates) else f'场景{scene_num}'

        # 🔥 生成分镜头（传递事件数据和角色信息）
        shots = _generate_scene_shots(
            scene_title, episode_title, stage, scene_num,
            event_data, character_profiles
        )

        scene = {
            'scene_number': scene_num,
            'scene_title': scene_title,
            'shot_sequence': shots,
            'estimated_duration_seconds': sum(s.get('duration', 8) for s in shots),
            'location': _generate_location_description(stage, scene_num),
            'characters_involved': _select_characters_for_scene(character_profiles, min(3, len(character_profiles)))
        }

        scenes.append(scene)

    return scenes


def _generate_scene_shots(scene_title: str, episode_title: str, stage: str, scene_num: int,
                           event_data: dict = None, characters: list = None) -> list:
    """
    为场景生成分镜头序列（包含Veo 3 AI提示语）

    🔥 新逻辑：每个情节点(content)对应一个独立的分镜头

    Args:
        scene_title: 场景标题
        episode_title: 剧集标题
        stage: 剧集阶段
        scene_num: 场景编号
        event_data: 事件数据（包含情节点）
        characters: 参与角色列表

    Returns:
        分镜头列表（每个镜头包含veo_prompt用于AI视频生成）
    """
    characters = characters or []
    event_data = event_data or {}

    # 🔥 提取事件信息 - 优先使用 content 字段
    event_content = event_data.get('content', [])

    # 如果 content 不是数组或为空，回退到旧逻辑
    if not isinstance(event_content, list) or len(event_content) == 0:
        event_description = event_data.get('description', event_data.get('plot_outline', ''))
        # 使用默认镜头类型
        shot_types_data = ['全景', '中景', '特写', '固定']
        shots = []
        for i, shot_type in enumerate(shot_types_data):
            veo_prompt = _generate_veo_prompt(
                shot_type=shot_type,
                scene_title=scene_title,
                episode_title=episode_title,
                stage=stage,
                event_description=event_description,
                event_location=event_data.get('location', ''),
                characters=characters,
                main_characters=event_data.get('characters', []),
                shot_index=i,
                total_shots=len(shot_types_data)
            )
            shots.append({
                'shot_number': i + 1,
                'shot_type': shot_type,
                'camera_movement': shot_type,
                'duration': 8,
                'description': _generate_shot_description(shot_type, episode_title, scene_title),
                'audio_note': _generate_audio_note(stage, shot_type),
                'veo_prompt': veo_prompt
            })
        return shots

    # 🔥 新逻辑：每个情节点对应一个镜头
    # 为每个情节点分配合适的镜头类型
    shot_type_sequence = _generate_shot_type_sequence(len(event_content), stage)

    shots = []
    for i, plot_point in enumerate(event_content):
        shot_type = shot_type_sequence[i] if i < len(shot_type_sequence) else '中景'

        # 🔥 为每个情节点生成独立的提示语
        veo_prompt = _generate_veo_prompt(
            shot_type=shot_type,
            scene_title=scene_title,
            episode_title=episode_title,
            stage=stage,
            event_description=plot_point,  # 🔥 使用单个情节点，不是全部
            event_location=event_data.get('location', ''),
            characters=characters,
            main_characters=event_data.get('characters', []),
            shot_index=i,
            total_shots=len(event_content),
            plot_point=plot_point  # 🔥 传递情节点用于生成更具体的描述
        )

        shots.append({
            'shot_number': i + 1,
            'shot_type': shot_type,
            'camera_movement': shot_type,
            'duration': 8,
            'description': f'{plot_point}（{shot_type}）',
            'audio_note': _generate_audio_note(stage, shot_type),
            'veo_prompt': veo_prompt
        })

    return shots


def _generate_shot_type_sequence(num_plots: int, stage: str) -> list:
    """
    根据情节点数量和阶段，生成合适的镜头类型序列

    Args:
        num_plots: 情节点数量
        stage: 剧集阶段（起承转合）

    Returns:
        镜头类型列表
    """
    # 不同阶段的镜头类型优先级
    stage_shot_priority = {
        '起': ['全景', '中景', '特写', '中景', '特写', '跟拍', '全景'],
        '承': ['中景', '全景', '跟拍', '特写', '中景', '拉远', '推镜头'],
        '转': ['特写', '急推', '中景', '晃动', '全景', '仰拍', '甩镜头'],
        '合': ['全景', '仰拍', '特写', '慢动作', '拉远', '全景', '固定']
    }

    priority = stage_shot_priority.get(stage, ['全景', '中景', '特写', '中景'])

    # 扩展到需要的数量
    sequence = []
    for i in range(num_plots):
        sequence.append(priority[i % len(priority)])

    return sequence


def _generate_veo_prompt(shot_type: str, scene_title: str, episode_title: str, stage: str,
                          event_description: str, event_location: str,
                          characters: list, main_characters: list,
                          shot_index: int = 0, total_shots: int = 1,
                          plot_point: str = None) -> str:
    """
    生成Veo 3专用的AI视频提示语（中文版）

    Args:
        shot_type: 镜头类型
        scene_title: 场景标题
        episode_title: 剧集标题
        stage: 剧集阶段
        event_description: 事件描述
        event_location: 事件地点
        characters: 所有角色列表
        main_characters: 主要参与角色

    Returns:
        Veo 3提示语字符串（中文）
    """
    # 基础镜头提示语模板（中文）- 针对短剧优化
    shot_prompts = {
        '全景': '{location}全景镜头。{atmosphere}。电影级灯光，专业色彩分级，展现空间层次感。仙侠修真风格，飘渺仙气，古风建筑，飘逸长袍，灵气流转的视觉效果。',
        '中景': '{characters}中景镜头，腰部以上构图。{action}。专业电影灯光，浅景深，人物动作清晰自然。',
        '特写': '人物面部特写，{emotion}。戏剧性侧光照明，高对比度，超细节纹理捕捉，电影级人像质感。',
        '拉远': '拉远镜头展现{location}全貌。景深扩大，空间环境层次分明，专业运镜配合大气透视效果。',
        '推镜头': '缓慢推进镜头聚焦{subject}。浅景深效果，电影级推轨移动，边缘渐晕虚化突出主体。',
        '跟拍': '跟随{character}移动的跟拍镜头。稳定器防抖，动态运镜，自然运动模糊，环境信息丰富。',
        '摇镜头': '{location}横摇扫描镜头。平滑水平移动展现场景细节，大气深度感，专业空间感知。',
        '升降': '{location}升降镜头展现垂直层次。垂直运镜展示空间关系和尺度感，电影级视觉效果。',
        '仰拍': '仰视{character}的低角度镜头。强化威严感和力量感，戏剧性天空背景，镜头光晕特效。',
        '固定': '固定机位拍摄{scene}。三脚架稳定构图，自然光照明，专业色彩还原。',
        '慢镜头': '{emotion}慢动作镜头。高帧率捕捉，平滑运动，戏剧性时间延展，情感张力十足。',
        '淡出': '{scene}淡出转场。渐进式亮度降低，平滑结束场景，专业色彩时间调校。',
        '急推': '急速推进{subject}。快速推轨移动制造冲击力，焦点变换，戏剧性张力爆发。',
        '甩镜头': '急速甩摇展现{scene}。快速水平运动模糊，动态能量，戏剧性视觉效果。',
        '晃动': '手持晃动镜头表现{action}。纪录片风格混乱感，自然运动模糊，紧张氛围营造。',
        '快速切换': '快速剪辑展现{action}。快节奏编辑，动态角度，高能量运动，专业动作摄影。',
        '主观视角': '{scene}第一人称视角。沉浸式体验，自然头部运动，深度感和临场感。',
        '爆炸': '{location}爆炸特效。高冲击力视觉特效，戏剧性灯光，粒子效果和冲击波细节。',
        '拉镜头': '拉远镜头展现{location}。构图扩展展示环境，深度层次分明，空间关系清晰。',
        '慢动作': '{action}慢动作特写。高FPS捕捉，细节运动保留，戏剧性时间控制。'
    }

    # 氛围描述（根据阶段）- 中文，针对短剧开局优化
    atmosphere_by_stage = {
        '起': '{location}场景开篇。{action}。清晨光线，神秘氛围，悬念丛生。古风建筑，烟雾缭绕，仙侠修真风格',
        '承': '{location}场景。{action}。情节推进，张力渐增。自然光配合微妙阴影，戏剧性光影',
        '转': '{location}场景。{action}。戏剧转折，情感强烈。激烈灯光，强烈对比冲击',
        '合': '{location}场景。{action}。高潮收尾，史诗级宏大场面。震撼灯光，视觉冲击力强大'
    }

    # 角色描述（如果有）
    # 🔥 修复：characters 可能是字符串列表或字典列表
    char_desc = ''
    if characters:
        # 提取角色名称列表
        char_names = []
        for c in characters[:3]:
            if isinstance(c, dict):
                name = c.get('name', '')
                if name:
                    char_names.append(name)
            elif isinstance(c, str):
                # 从 "角色名: 描述" 格式中提取名称
                if ':' in c:
                    name = c.split(':')[0].strip()
                else:
                    name = c.strip()
                if name:
                    char_names.append(name)

        if char_names:
            char_desc = f"{', '.join(char_names)}等角色"

    if not char_desc:
        char_desc = '角色身着古装'

    # 场景动作描述（基于事件内容）
    if event_description:
        action_desc = event_description
    else:
        # 🔥 根据事件标题生成场景描述
        # 例如："诈尸惊魂：开局就在火葬场" → "主角在火葬场突然醒来，周围人惊慌失措"
        if '火葬场' in episode_title or '灵堂' in episode_title or '葬礼' in episode_title:
            action_desc = '主角躺在灵堂/火葬场突然醒来，周围守灵的人惊慌失措，误以为诈尸'
        elif '重生' in episode_title or '穿越' in episode_title:
            action_desc = '主角重生/穿越醒来，发现自己回到过去，观察陌生又熟悉的环境'
        elif '战斗' in episode_title or '对决' in episode_title or '激战' in episode_title:
            action_desc = '双方激烈战斗，刀光剑影，能量碰撞，场面震撼'
        elif '修炼' in episode_title or '突破' in episode_title or '升级' in episode_title:
            action_desc = '主角闭关修炼，周身灵气涌动，突破境界，天地异象'
        elif '退婚' in episode_title or '羞辱' in episode_title:
            action_desc = '主角面对众人的羞辱和退婚，神色平静，眼神坚定'
        else:
            # 通用描述：根据场景类型生成
            action_desc = f'{episode_title.replace("：", "").replace(":", "")}的关键场景展现'

    # 🔥 改进地点映射 - 根据事件标题智能推断地点
    location_map = {
        '庭院': '古色古香的庭院',
        '书房': '古典书房',
        '大殿': '庄严大殿',
        '演武场': '宗门演武场',
        '密室': '幽静密室',
        '山林': '云雾缭绕的山林',
        '主厅': '宽敞主厅',
        '门口': '府邸大门',
        '洞府': '修仙洞府',
        '广场': '宗门广场',
        '天际': '天际云端',
        '战场': '激战战场',
        '虚空': '神秘虚空',
        '巅峰': '绝顶山峰',
        '灵堂': '肃穆灵堂，白布挽联，香烛缭绕',
        '火葬场': '火葬场灵堂，棺木陈列，守灵人群',
        '墓地': '阴森墓地，石碑林立，雾气弥漫'
    }

    # 🔥 智能推断地点
    if not event_location:
        if '火葬场' in episode_title or '灵堂' in episode_title or '葬礼' in episode_title or '诈尸' in episode_title:
            location_cn = '肃穆灵堂，白布挽联，香烛缭绕，守灵人群在旁'
        elif '重生' in episode_title or '醒来' in episode_title:
            location_cn = '古朴卧房，纱帐轻拂，晨光透过窗棂'
        else:
            location_cn = '古风场景'
    else:
        # 转换地点为中文描述
        location_cn = location_map.get(event_location, event_location)

    # 获取主要角色名（用于跟拍等需要角色名的镜头）
    character_name = ''
    if main_characters:
        character_name = main_characters[0]
    elif characters and len(characters) > 0:
        first_char = characters[0]
        if isinstance(first_char, dict):
            character_name = first_char.get('name', '')
        elif isinstance(first_char, str):
            character_name = first_char.split(':')[0] if ':' in first_char else first_char

    if not character_name:
        character_name = '角色'

    # 🔥 获取镜头模板并替换占位符
    prompt_template = shot_prompts.get(shot_type, shot_prompts['中景'])

    # 🔥 先替换氛围描述中的占位符
    atmosphere_with_placeholders = atmosphere_by_stage.get(stage, '电影氛围，专业灯光')
    atmosphere = atmosphere_with_placeholders.format(
        characters=char_desc,
        action=action_desc[:30] if action_desc else '剧情展开'
    )

    # 根据不同的镜头类型，使用不同的模板
    if shot_type in ['全景', '拉远', '摇镜头', '升降', '爆炸', '拉镜头']:
        # 这些镜头需要 location
        veo_prompt = prompt_template.format(
            location=location_cn,
            atmosphere=atmosphere
        )
    elif shot_type in ['中景', '晃动', '快速切换', '慢动作']:
        # 这些镜头需要 characters 和 action
        veo_prompt = prompt_template.format(
            characters=char_desc,
            action=action_desc[:50] if action_desc else '戏剧性互动'
        )
    elif shot_type in ['特写', '慢镜头']:
        # 这些镜头需要 emotion
        veo_prompt = prompt_template.format(
            emotion='强烈情感表达' if stage in ['转', '合'] else '细腻情感'
        )
    elif shot_type in ['推镜头', '急推']:
        # 这些镜头需要 subject
        veo_prompt = prompt_template.format(
            subject='主要人物' if main_characters else '场景主体'
        )
    elif shot_type in ['跟拍', '仰拍']:
        # 这些镜头需要 character
        veo_prompt = prompt_template.format(
            character=character_name
        )
    elif shot_type in ['固定', '淡出', '甩镜头', '主观视角']:
        # 这些镜头需要 scene
        veo_prompt = prompt_template.format(
            scene=scene_title
        )
    else:
        # 默认使用中景模板
        default_template = shot_prompts['中景']
        veo_prompt = default_template.format(
            characters=char_desc,
            action=action_desc[:50] if action_desc else '戏剧性互动'
        )

    # 添加风格后缀（中文）
    style_suffix = _get_style_suffix(stage)
    veo_prompt = f"{veo_prompt} {style_suffix}"

    return veo_prompt


def _get_style_suffix(stage: str) -> str:
    """根据阶段返回视觉风格后缀（中文）"""
    styles = {
        '起': '仙侠修真风格，飘渺仙气，古风建筑，飘逸长袍，灵气流转的视觉效果。',
        '承': '中国古风美学，精致古装，自然柔和灯光，细腻阴影层次。',
        '转': '戏剧性中国奇幻风格，激烈灯光，神秘特效，强大视觉冲击力。',
        '合': '史诗级仙侠高潮风格，宏大场面，天庭特效，庄严电影级摄影。'
    }
    return styles.get(stage, styles['起'])


def _generate_shot_description(shot_type: str, episode_title: str, scene_title: str) -> str:
    """生成长头描述"""
    descriptions = {
        '全景': f'展现{episode_title}的整体场景',
        '中景': f'展示{scene_title}中的人物交流',
        '特写': f'突出人物表情和情感细节',
        '拉远': f'拉大景深，展现{episode_title}的环境氛围',
        '推镜头': f'推近主体，引导观众视线',
        '跟拍': f'跟随人物动作，增强代入感',
        '摇镜头': f'扫描场景，展示{scene_title}的环境',
        '升降': f'垂直运镜，展现场景层次',
        '仰拍': f'仰拍镜头，增强视觉冲击力',
        '固定': f'固定镜头，稳定观察场景',
        '慢镜头': f'慢动作处理，强化重要时刻',
        '淡出': f'画面淡出，完成场景过渡',
        '急推': f'急速推镜头，制造紧张感',
        '甩镜头': f'甩镜头特效，表现戏剧性',
        '晃动': f'镜头晃动，表现不稳定状态',
        '快速切换': f'快速切换镜头，加快叙事节奏',
        '主观视角': f'主观视角拍摄，增强代入感',
        '爆炸': f'视觉冲击特效',
        '拉镜头': f'拉镜头扩大视野',
        '慢动作': f'慢动作突出重点'
    }
    return descriptions.get(shot_type, f'{shot_type}镜头展示{scene_title}')


def _generate_audio_note(stage: str, shot_type: str) -> str:
    """生成音频备注"""
    audio_notes = {
        '起': ['轻快背景音乐', '音效点缀', '环境音'],
        '承': ['节奏加快', '紧张音乐渐强', '音效密集'],
        '转': ['音效突出', '音乐转折', '静音对比'],
        '合': ['高潮音乐', '宏大配乐', '音效丰富']
    }

    stage_notes = audio_notes.get(stage, ['背景音乐'])
    return stage_notes[0] if stage_notes else '背景音乐'


def _generate_location_description(stage: str, scene_num: int) -> str:
    """生成场景地点描述"""
    locations = {
        '起': ['主厅', '庭院', '书房', '门口'],
        '承': ['大殿', '演武场', '密室', '山林'],
        '转': ['战场', '禁地', '洞府', '天际'],
        '合': ['巅峰', '广场', '仙宫', '虚空']
    }

    loc_list = locations.get(stage, ['场景'])
    return loc_list[scene_num % len(loc_list)] if loc_list else '场景'


def _select_characters_for_scene(character_profiles: list, max_chars: int) -> list:
    """为场景选择角色"""
    if not character_profiles:
        return ['主角']

    # 简单选择：取前 max_chars 个角色
    selected = []
    for i in range(min(max_chars, len(character_profiles))):
        char_str = character_profiles[i]
        if isinstance(char_str, str):
            # 提取角色名称
            char_name = char_str.split(':')[0].strip()
            selected.append(char_name)
        elif isinstance(char_str, dict):
            char_name = char_str.get('name', '角色')
            selected.append(char_name)

    return selected


# ==================== AI驱动的分镜头生成 ====================

def _load_writing_plan_file(novel_title: str, episode_id: str = None) -> dict:
    """
    直接从文件系统加载写作计划JSON文件

    Args:
        novel_title: 小说标题
        episode_id: 剧集ID，用于确定加载哪个阶段的写作计划

    Returns:
        写作计划数据字典，如果文件不存在返回空字典
    """
    try:
        from pathlib import Path
        import re

        novel_dir = Path('小说项目') / novel_title
        plans_dir = novel_dir / 'plans'

        if not plans_dir.exists():
            logger.warn(f"⚠️ plans目录不存在: {plans_dir}")
            return {}

        # 查找所有写作计划文件
        plan_files = list(plans_dir.glob('*writing_plan.json'))

        if not plan_files:
            logger.warn(f"⚠️ 未找到写作计划文件: {plans_dir}/*writing_plan.json")
            return {}

        # 🔥 根据episode_id确定应该加载哪个阶段的文件
        target_stage = None
        if episode_id:
            # 解析major_idx
            match = re.search(r'major_event_(\d+)', episode_id)
            if match:
                major_idx = int(match.group(1))

                # 根据major_idx判断阶段
                # opening_stage: major_event 0-2 (前3个事件)
                # development_stage: major_event 3-7
                # conflict_stage: major_event 8-12
                # climax_stage: major_event 13+
                if major_idx <= 2:
                    target_stage = 'opening'
                elif major_idx <= 7:
                    target_stage = 'development'
                elif major_idx <= 12:
                    target_stage = 'conflict'
                else:
                    target_stage = 'climax'

                logger.info(f"🎯 根据major_idx={major_idx}，目标阶段: {target_stage}")

        # 如果确定了目标阶段，优先加载对应的文件
        if target_stage:
            for plan_file in plan_files:
                if target_stage in plan_file.name.lower():
                    logger.info(f"📂 读取写作计划文件: {plan_file}")
                    with open(plan_file, 'r', encoding='utf-8') as f:
                        plan_data = json.load(f)
                    logger.info(f"✅ 写作计划文件加载成功: {plan_file.name}")
                    return plan_data

        # 回退：使用第一个找到的文件
        plan_file = plan_files[0]
        logger.info(f"📂 读取写作计划文件（默认）: {plan_file}")

        with open(plan_file, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        logger.info(f"✅ 写作计划文件加载成功")
        return plan_data

    except Exception as e:
        logger.error(f"❌ 加载写作计划文件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def _find_event_in_writing_plan(writing_plan: dict, episode_id: str, episode_stage: str) -> dict:
    """
    从写作计划中查找对应的事件数据

    Args:
        writing_plan: 写作计划数据
        episode_id: 剧集ID，格式如: major_event_0_event_2_0
        episode_stage: 剧集阶段（起承转合）

    Returns:
        包含情节点的事件数据，如果找不到返回默认数据
    """
    try:
        # 解析episode_id，格式: major_event_{major_idx}_event_{stage_idx}_{sub_idx}
        # 例如: major_event_0_event_2_0 → major_idx=0, stage_idx=2, sub_idx=0
        import re

        # 使用正则提取所有数字
        numbers = re.findall(r'\d+', episode_id)
        if len(numbers) >= 3:
            major_idx = int(numbers[0])  # 第一个数字是major_idx
            stage_idx = int(numbers[1])  # 第二个数字是stage_idx
            sub_idx = int(numbers[2]) if len(numbers) > 2 else 0  # 第三个数字是该阶段内的索引
        else:
            # 回退方案
            major_idx = 0
            stage_idx = 0
            sub_idx = 0

        # 根据stage_idx确定阶段名称
        stage_names = ['起', '承', '转', '合']
        if stage_idx < len(stage_names):
            stage_from_id = stage_names[stage_idx]
        else:
            stage_from_id = '起'

        logger.info(f"🔍 解析episode_id: major_idx={major_idx}, stage_idx={stage_idx}({stage_from_id}), sub_idx={sub_idx}")

        # 从写作计划中提取事件系统
        stage_plan = writing_plan.get('stage_writing_plan', {})
        event_system = stage_plan.get('event_system', {})
        major_events = event_system.get('major_events', [])

        if not major_events or major_idx >= len(major_events):
            logger.warn(f"⚠️ 未找到major_event[{major_idx}]，总数: {len(major_events)}")
            return {}

        major_event = major_events[major_idx]
        composition = major_event.get('composition', {})

        # 使用解析出的stage名称，而不是传入的episode_stage
        target_stage = stage_from_id
        stage_events = composition.get(target_stage, [])

        if not stage_events:
            logger.warn(f"⚠️ 未找到{target_stage}阶段的事件，可用阶段: {list(composition.keys())}")
            return {}

        # 使用sub_idx作为该阶段内的事件索引
        if sub_idx >= len(stage_events):
            logger.warn(f"⚠️ 未找到{target_stage}阶段的第{sub_idx}个事件，总数: {len(stage_events)}")
            # 如果超出范围，使用第一个事件
            sub_idx = 0

        medium_event = stage_events[sub_idx]

        # 提取情节点（plot_outline）
        plot_outline = medium_event.get('plot_outline', [])
        description = medium_event.get('description', '')
        name = medium_event.get('name', '')

        logger.info(f"✅ 找到事件: {name}, 情节点数: {len(plot_outline)}")

        return {
            'name': name,
            'description': description,
            'plot_outline': plot_outline,
            'major_event_name': major_event.get('name', ''),
            'emotional_derivation': medium_event.get('emotional_derivation', {})
        }

    except Exception as e:
        logger.error(f"❌ 查找事件失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {}


def _generate_storyboard_with_ai(novel_title: str, episode: dict) -> dict:
    """
    使用AI（gemini-2.5-pro）生成分镜头脚本

    AI会综合考虑以下因素：
    - 世界观设定
    - 角色信息
    - 写作计划
    - 市场分析
    - 事件情节点（将2-3个情节合并为一个镜头）

    Args:
        novel_title: 小说标题
        episode: 单个剧集信息（包含id、标题、阶段等）

    Returns:
        分镜头数据字典
    """
    if not ai_client:
        logger.error("❌ AI客户端未初始化，无法使用AI生成分镜头")
        return None

    episode_id = episode.get('id', '')
    episode_title = episode.get('title', '未知标题')
    episode_stage = episode.get('stage', '起')

    logger.info(f"🤖 [AI分镜头] 开始为剧集生成AI分镜头: {episode_title}")
    logger.info(f"   小说: {novel_title}")
    logger.info(f"   阶段: {episode_stage}")
    logger.info(f"   episode_id: {episode_id}")

    # 🔥 加载角色设计文件
    character_data = _load_character_design_file(novel_title)

    # 🔥 直接从写作计划文件加载数据（根据episode_id智能选择正确的阶段文件）
    writing_plan = _load_writing_plan_file(novel_title, episode_id)

    if not writing_plan:
        logger.error("❌ 无法加载写作计划文件")
        return None

    # 🔥 从写作计划中查找对应的事件数据
    event_data = _find_event_in_writing_plan(writing_plan, episode_id, episode_stage)

    # 提取情节点和事件信息
    if event_data:
        # 从写作计划成功获取数据
        plot_outline = event_data.get('plot_outline', [])
        event_name = event_data.get('name', episode_title)
        major_event_name = event_data.get('major_event_name', '')
        event_description = event_data.get('description', '')
        plot_points = plot_outline if plot_outline else [event_description]
    else:
        # 🔥 回退方案：使用 episode 参数中传递的数据
        logger.warn(f"⚠️ [AI分镜头] 写作计划中未找到对应事件，使用 episode 参数数据")

        event_name = episode.get('title', episode_title)
        major_event_name = episode.get('major_event', '')
        event_description = episode.get('description', '')

        # 尝试获取 content 字段
        event_content = episode.get('content', [])
        if isinstance(event_content, list) and event_content:
            plot_points = event_content
        else:
            plot_points = [event_description] if event_description else [event_name]

    logger.info(f"   事件名称: {event_name}")
    logger.info(f"   所属重大事件: {major_event_name}")
    logger.info(f"   情节点数量: {len(plot_points)}")
    logger.info(f"   角色数据: {len(character_data)} 个角色")

    # 🔥 构建角色参考图映射信息
    character_reference_info = _build_character_reference_info(character_data)

    # 构建系统提示词 - 全新的短视频格式
    system_prompt = """你是一位专业的短视频/短剧分镜头脚本设计师，擅长将小说情节转化为高吸引力的短视频分镜头。

【核心任务】
根据提供的小说信息、事件情节点和角色信息，设计出适合竖屏短视频（9:16）的高质量分镜头脚本。

【角色-参考图绑定机制】
⚠️ 重要：AI视频生成时会根据角色名自动查找对应的参考图。
- 在镜头的 veo_prompt 中，直接使用角色姓名即可
- 参考图使用格式：「{角色名}，{详细外貌描述}，{动作描述}，{场景环境}」
- 系统会自动根据角色名匹配项目中的角色参考图

【短视频分镜头原则】
1. **黄金前3秒**: 开头必须抓人眼球，用强烈的视觉冲突或悬念
2. **快节奏**: 每2-3秒一个新画面，避免拖沓
3. **爽点密集**: 情绪快速递进，反转要有冲击力
4. **竖屏构图**: 一切为手机竖屏优化，人物居中或偏上
5. **音乐配合**: 每个镜头标注合适的音效/背景音乐
6. **角色一致性**: 使用角色名确保同一角色在不同镜头中形象一致
7. **统一时长**: 所有镜头必须严格为8秒

【输出格式】
严格按以下JSON格式输出，不要包含任何其他文字：
```json
{
  "video_title": "视频标题（吸引眼球的，15字内）",
  "hook": "开头3秒钩子描述",
  "total_duration": 预计总时长（秒）,
  "scenes": [
    {
      "scene_number": 1,
      "duration": 8,
      "visual": {
        "shot_type": "镜头类型（特写/中景/全景/推近/拉远/跟拍/摇镜头/主观视角/俯拍/仰拍）",
        "description": "画面动作描述（具体、可拍摄）",
        "veo_prompt": "AI视频生成提示词（直接使用角色名，如：林战，身穿兽皮战甲，面容震撼，站在画面中央，背景是祠堂）"
      },
      "dialogue": {
        "speaker": "说话角色名（无台词填'无'）",
        "lines": "角色台词内容（无台词填空字符串''）",
        "tone": "语气描述（如：愤怒、温柔、紧张等）",
        "audio_note": "音效/BGM描述"
      },
      "plot_content": "对应的情节点内容"
    }
  ],
  "ending_hook": "结尾悬念或爽点"
}
```

**⚠️ 对话场景特殊格式**：
当场景是角色之间的对话时，使用以下格式：
```json
{
  "scene_number": 3,
  "duration": 16,
  "visual": {...},
  "dialogues": [
    {"speaker": "林战", "lines": "你还是离开林家吧。", "tone": "严肃", "audio_note": "..."},
    {"speaker": "叶凡", "lines": "我偏不。", "tone": "坚定", "audio_note": "..."},
    {"speaker": "林战", "lines": "那就别怪我。", "tone": "冷漠", "audio_note": "..."}
  ],
  "plot_content": "情节点描述"
}
```

注意：
- 对话场景使用 `dialogues`（复数）而不是 `dialogue`（单数）
- 同一镜头中的多句台词，画面保持不变，只显示不同角色说话
- 音频文件命名规则：`{镜头号}_{事件名}_对话{序号}_{角色}.mp3`

【veo_prompt编写规范】
1. 直接使用角色名，系统会自动匹配对应的参考图
2. 格式：「{角色名}，{详细外貌描述}，{动作描述}，{场景环境}，{光影氛围}」
3. 多角色场景：「{角色A}站在左侧，{角色B}站在右侧，{场景描述}」
4. 无角色场景：直接描述场景、环境、氛围

【台词设计要求】
1. 台词要简洁有力，符合短剧快节奏特点
2. 每句台词控制在3-10字内
3. speaker填写角色名，旁白填写"旁白"，内心独白填写"主角内心混响"
4. 无台词镜头：speaker填"无"，lines填空字符串""
"""

    # 构建用户提示词 - 传递完整上下文（从写作计划文件中提取）
    user_prompt = f"""请为以下剧集设计分镜头脚本：

【剧集信息】
- 剧集标题: {event_name}
- 所属重大事件: {major_event_name}
- 剧集阶段: {episode_stage}

【情节点列表】（详细情节描述）
"""

    # 添加情节点
    for i, point in enumerate(plot_points, 1):
        user_prompt += f"{i}. {point}\n"

    # 🔥 从写作计划中提取核心设定和世界观
    novel_metadata = writing_plan.get('stage_writing_plan', {}).get('novel_metadata', {})
    creative_seed = novel_metadata.get('creative_seed', {})

    # 添加核心设定
    core_setting = creative_seed.get('coreSetting', '')
    if core_setting:
        user_prompt += f"""

【核心设定】
{core_setting}
"""

    # 添加简介
    synopsis = creative_seed.get('synopsis', '')
    if synopsis:
        user_prompt += f"""

【故事简介】
{synopsis}
"""

    # 🔥 添加市场定位参考
    core_selling_points = creative_seed.get('coreSellingPoints', '')
    if core_selling_points:
        user_prompt += f"""

【核心卖点】
{core_selling_points}
"""

    # 🔥 添加角色参考图信息
    if character_reference_info:
        user_prompt += f"""

【角色参考图映射】
以下是本镜头涉及的角色（系统会根据角色名自动匹配参考图）：
"""
        for char_info in character_reference_info:
            user_prompt += f"- 参考图{char_info['reference_index']}: {char_info['character_name']} - {char_info['appearance_brief']}\n"
        user_prompt += "\n⚠️ 在编写veo_prompt时，直接使用角色名即可，系统会自动匹配对应的参考图。\n"

    user_prompt += f"""

【设计要求】
1. 根据情节点内容，设计3-6个镜头（每个镜头对应一个scene）
2. **每个镜头时长必须严格为8秒**
3. veo_prompt必须直接包含角色名，格式：「{角色名}，外貌描述，动作，场景环境」
4. 多角色场景：「{角色A}站在左侧，{角色B}站在右侧，{场景描述}」
5. 镜头类型要多样化（特写、中景、全景、推拉摇移等）
6. 视频方向为竖屏（9:16），适合手机观看
7. **对话场景处理**：
   - 如果场景是角色之间的对话交流，使用 `dialogues` 数组格式
   - 将多句对话放在同一个镜头中，画面保持不变
   - 每句台词标注对应的角色和语气
   - 对话场景的时长可以设为16秒（包含2-3句对话）
8. **独白/旁白场景**：
   - 使用 `dialogue` 对象格式
   - 单句台词，镜头时长8秒
9. **无台词镜头**：speaker填"无"，lines填空字符串""

请直接输出JSON格式的分镜头脚本。"""

    # 🔥 优先检查是否已有保存的分镜头文件
    existing_storyboard = _load_storyboard_file(novel_title, event_name, episode_id)
    if existing_storyboard:
        logger.info(f"✅ [AI分镜头] 使用已保存的分镜头，跳过AI生成")
        return existing_storyboard

    # 调用AI生成
    try:
        logger.info(f"🚀 [AI分镜头] 调用AI生成，使用模型: gemini-2.5-pro")
        result = ai_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            purpose="AI分镜头生成",
            provider="gemini",
            model_name="gemini-2.5-pro"
        )

        if not result:
            logger.error("❌ [AI分镜头] AI调用失败，未返回结果")
            return None

        # 解析JSON结果
        storyboard_data = ai_client.parse_json_response(result)
        if not storyboard_data:
            logger.error("❌ [AI分镜头] JSON解析失败")
            logger.error(f"原始结果: {result[:500]}...")
            return None

        # 🔥 验证新格式
        if 'scenes' not in storyboard_data:
            logger.error("❌ [AI分镜头] AI未返回新格式（缺少scenes字段），请检查系统提示词")
            logger.error(f"返回的字段: {list(storyboard_data.keys())}")
            return None

        logger.info(f"✅ [AI分镜头] AI生成成功，场景数: {len(storyboard_data.get('scenes', []))}")

        # 保存生成的分镜头到文件（按重大事件组织目录）
        _save_storyboard_to_file(novel_title, event_name, episode_id, storyboard_data, major_event_name)

        return storyboard_data

    except Exception as e:
        logger.error(f"❌ [AI分镜头] AI生成异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None


def _load_character_design_file(novel_title: str) -> dict:
    """
    加载角色设计文件

    Args:
        novel_title: 小说标题

    Returns:
        角色数据字典，包含main_character和important_characters
    """
    try:
        from pathlib import Path

        # 查找角色设计文件
        novel_dir = Path('小说项目') / novel_title
        character_file = novel_dir / 'characters' / f'{novel_title}_角色设计.json'

        if not character_file.exists():
            logger.warn(f"⚠️ [角色加载] 未找到角色设计文件: {character_file}")
            return {}

        with open(character_file, 'r', encoding='utf-8') as f:
            character_data = json.load(f)

        logger.info(f"✅ [角色加载] 成功加载角色设计文件: {len(character_data.get('important_characters', []))} 个重要角色")
        return character_data

    except Exception as e:
        logger.error(f"❌ [角色加载] 加载角色设计文件失败: {e}")
        return {}


def _build_character_reference_info(character_data: dict) -> list:
    """
    构建角色参考图映射信息

    Args:
        character_data: 角色数据字典

    Returns:
        角色参考图信息列表，每个元素包含：
        - character_name: 角色名
        - reference_index: 参考图序号
        - appearance_brief: 外貌简述
    """
    reference_info = []
    index = 1

    # 首先添加主角
    main_char = character_data.get('main_character', {})
    if main_char:
        appearance = _extract_appearance_brief(main_char)
        reference_info.append({
            'character_name': main_char.get('name', '主角'),
            'reference_index': index,
            'appearance_brief': appearance
        })
        index += 1

    # 然后添加重要角色（最多10个）
    important_chars = character_data.get('important_characters', [])
    for char in important_chars[:10]:
        appearance = _extract_appearance_brief(char)
        reference_info.append({
            'character_name': char.get('name', '未命名'),
            'reference_index': index,
            'appearance_brief': appearance
        })
        index += 1

    return reference_info


def _extract_appearance_brief(character: dict) -> str:
    """
    提取角色外貌简述

    Args:
        character: 角色数据

    Returns:
        外貌简述字符串
    """
    # 尝试从不同字段提取外貌信息
    living_chars = character.get('living_characteristics', {})
    physical = living_chars.get('physical_presence', '')

    initial_state = character.get('initial_state', {})
    description = initial_state.get('description', '')

    # 优先使用 physical_presence，其次使用 description
    if physical:
        return physical[:100]  # 限制长度
    elif description:
        return description[:100]
    else:
        return character.get('name', '角色')  # 回退到角色名


def _save_storyboard_to_file(novel_title: str, event_name: str, episode_id: str, storyboard_data: dict, major_event_name: str = ''):
    """
    保存分镜头数据到文件

    Args:
        novel_title: 小说标题
        event_name: 事件名称（如：诈尸惊魂：开局就在火葬场）
        episode_id: 剧集ID（如：major_event_0_event_0_0）
        storyboard_data: 分镜头数据
        major_event_name: 重大事件名称（用于创建子目录）
    """
    try:
        import re

        # 🔥 根据episode_id确定重大事件序号，用于组织目录结构
        # episode_id格式: major_event_0_event_0_0
        major_idx = 0
        if episode_id:
            numbers = re.findall(r'\d+', episode_id)
            if len(numbers) >= 1:
                major_idx = int(numbers[0])

        # 🔥 创建子目录：第一集、第二集等，或使用重大事件名称
        if major_event_name:
            # 使用重大事件名称作为子目录
            safe_major_name = re.sub(r'[<>:"/\\|?*]', '_', major_event_name[:30])  # 限制长度
            sub_dir_name = f"{major_idx + 1}集_{safe_major_name}"
        else:
            sub_dir_name = f"{major_idx + 1}集"

        # 创建保存目录：视频项目/小说名/X集_重大事件名/storyboards/
        save_dir = Path('视频项目') / novel_title / sub_dir_name / 'storyboards'
        save_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名：{事件名称}.json（不带时间戳）
        safe_event_name = re.sub(r'[<>:"/\\|?*]', '_', event_name)
        filename = f"{safe_event_name}.json"
        filepath = save_dir / filename

        # 保存数据
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 [AI分镜头] 分镜头已保存到: {filepath}")

    except Exception as e:
        logger.error(f"❌ [AI分镜头] 保存分镜头文件失败: {e}")


def _load_storyboard_file(novel_title: str, event_name: str, episode_id: str = '') -> dict:
    """
    加载已保存的分镜头文件

    Args:
        novel_title: 小说标题（可能是清理过的，也可能是原始的）
        event_name: 事件名称
        episode_id: 剧集ID（可选，用于确定子目录）

    Returns:
        分镜头数据字典，如果文件不存在返回None
    """
    try:
        import re

        # 🔥 获取实际存在的小说目录（优先选择带冒号的正确目录）
        project_base = Path('视频项目')
        actual_novel_dir = None
        normalize_name = lambda name: re.sub(r'[<>:"/\\|?*：：、＿_]', '', name)

        # 尝试多种方式找到实际的小说目录
        if project_base.exists():
            # 先收集所有匹配的目录
            matching_dirs = []
            for novel_dir in project_base.iterdir():
                if not novel_dir.is_dir():
                    continue

                # 精确匹配
                if novel_dir.name == novel_title:
                    matching_dirs.insert(0, novel_dir)  # 精确匹配优先
                    break

                # 模糊匹配：移除特殊字符后比较
                # 心声泄露：我成了家族老阴比 vs 心声泄露_我成了家族老阴比
                if normalize_name(novel_dir.name) == normalize_name(novel_title):
                    matching_dirs.append(novel_dir)

            # 优先选择包含中文冒号的目录（正确的格式）
            for novel_dir in matching_dirs:
                if '：' in novel_dir.name:
                    actual_novel_dir = novel_dir
                    break

            # 如果没有找到带冒号的，使用第一个匹配的
            if not actual_novel_dir and matching_dirs:
                actual_novel_dir = matching_dirs[0]

        if not actual_novel_dir:
            logger.info(f"📂 [AI分镜头] 未找到小说目录: {novel_title}")
            return None

        logger.info(f"📂 [AI分镜头] 使用实际目录: {actual_novel_dir.name}")

        # 🔥 尝试多个可能的路径
        possible_paths = []

        # 路径1：新的组织方式（按重大事件组织）
        if episode_id:
            numbers = re.findall(r'\d+', episode_id)
            if len(numbers) >= 1:
                major_idx = int(numbers[0])
                # 尝试在所有 "X集*" 子目录下查找
                for episode_dir in actual_novel_dir.iterdir():
                    if not episode_dir.is_dir():
                        continue

                    # 匹配目录名模式：数字集_... 或 数字集
                    dir_name = episode_dir.name
                    if re.match(r'^\d+集', dir_name):
                        # 检查是否是正确的重大事件序号
                        dir_major_idx = int(re.findall(r'^(\d+)集', dir_name)[0]) - 1
                        if dir_major_idx == major_idx:
                            storyboards_path = episode_dir / 'storyboards'
                            if storyboards_path.exists():
                                possible_paths.append(storyboards_path)
                                logger.info(f"📂 [AI分镜头] 找到匹配的剧集目录: {dir_name}")

        # 路径2：旧的扁平结构（向后兼容）
        path2 = actual_novel_dir / 'storyboards'
        if path2.exists():
            possible_paths.append(path2)

        # 查找匹配的文件
        safe_event_name = re.sub(r'[<>:"/\\|?*]', '_', event_name)
        filename = f"{safe_event_name}.json"

        for search_dir in possible_paths:
            filepath = search_dir / filename
            if filepath.exists():
                logger.info(f"📂 [AI分镜头] 找到已保存的分镜头: {filepath}")

                with open(filepath, 'r', encoding='utf-8') as f:
                    storyboard_data = json.load(f)

                # 检查是否有角色参考图信息
                character_images = storyboard_data.get('character_images', [])
                if character_images:
                    logger.info(f"✅ [AI分镜头] 已加载现有分镜头 (包含{len(character_images)}个角色)")
                else:
                    logger.info(f"✅ [AI分镜头] 已加载现有分镜头 (旧格式)")

                return storyboard_data

        logger.info(f"📂 [AI分镜头] 未找到已保存的分镜头: {filename}")
        return None

    except Exception as e:
        logger.error(f"❌ [AI分镜头] 加载分镜头文件失败: {e}")
        return None


def register_video_routes(app):
    """注册视频生成API路由"""
    app.register_blueprint(video_api, url_prefix='/api')

    logger.debug("=" * 60)
    logger.debug("📋 已注册的视频生成API路由:")
    for rule in app.url_map.iter_rules():
        if 'video' in rule.rule:
            logger.debug(f"  - {rule.methods} {rule.rule} -> {rule.endpoint}")
    logger.debug("=" * 60)
    logger.debug("视频生成API路由注册完成")