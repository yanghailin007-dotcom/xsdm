"""
短剧工作台 API
处理项目、角色、分镜头、视频生成等操作
"""

from flask import Blueprint, request, jsonify, send_from_directory
from pathlib import Path
import json
import re
import uuid
import os
import shutil
import sys
from datetime import datetime
from urllib.parse import unquote

from src.utils.logger import get_logger
from src.core.APIClient import APIClient
from config.config import CONFIG

logger = get_logger(__name__)

# 初始化AI客户端
try:
    api_client = APIClient(CONFIG)
    logger.info("✅ [短剧API] AI客户端初始化成功")
except Exception as e:
    logger.warning(f"⚠️ [短剧API] AI客户端初始化失败: {e}")
    api_client = None

short_drama_api = Blueprint('short_drama_api', __name__, url_prefix='/api/short-drama')

# 项目存储目录 - 使用视频项目目录
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
VIDEO_PROJECTS_DIR = BASE_DIR / '视频项目'
VIDEO_PROJECTS_DIR.mkdir(exist_ok=True)

# 小说项目目录
NOVEL_PROJECTS_DIR = BASE_DIR / '小说项目'
NOVEL_PROJECTS_DIR.mkdir(exist_ok=True)


def get_project_dir(novel_title: str) -> Path:
    """获取小说项目目录"""
    return VIDEO_PROJECTS_DIR / novel_title


def get_project_file(novel_title: str) -> Path:
    """获取项目信息文件路径"""
    return get_project_dir(novel_title) / '项目信息.json'


class ShortDramaProject:
    """短剧项目管理"""

    def __init__(self, project_id=None, title=None):
        self.id = project_id or str(uuid.uuid4())[:8]
        self.title = title or '未命名项目'
        self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()
        self.status = 'draft'  # draft, in_progress, completed
        self.episodes = []
        self.characters = []
        self.settings = {
            'aspect_ratio': '9:16',
            'quality': '4K',
            'model': 'veo_3_1-fast'
        }

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'status': self.status,
            'episodes_count': len(self.episodes) if isinstance(self.episodes, list) else 0,
            'characters_count': len(self.characters) if isinstance(self.characters, list) else 0,
            'total_shots': 0,  # TODO: 从episodes数据计算
            'videos_count': 0,  # TODO: 从episodes数据计算
            'progress': self._calculate_progress(),
            'episodes': self.episodes,
            'characters': self.characters,
            'settings': self.settings
        }

    def _calculate_progress(self):
        """计算项目进度"""
        # 如果episodes是字符串ID列表，返回0
        if not self.episodes or not isinstance(self.episodes, list):
            return 0

        # 如果episodes是字典列表且有shots字段
        if self.episodes and isinstance(self.episodes[0], dict):
            total_shots = sum(len(ep.get('shots', [])) for ep in self.episodes)
            if total_shots == 0:
                return 0

            completed_shots = sum(
                len([s for s in ep.get('shots', []) if s.get('status') == 'completed'])
                for ep in self.episodes
            )

            return int((completed_shots / total_shots) * 100)

        return 0

    def save(self):
        """保存项目到文件"""
        project_dir = get_project_dir(self.title)
        project_dir.mkdir(parents=True, exist_ok=True)

        # 🔥 创建场景道具目录
        scene_props_dir = project_dir / '场景道具'
        scene_props_dir.mkdir(exist_ok=True)

        project_file = project_dir / '项目信息.json'
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f'✅ 项目已保存: {project_file}')

    @staticmethod
    def load(project_id):
        """从文件加载项目"""
        # 遍历所有项目目录查找
        for project_dir in VIDEO_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                project_file = project_dir / '项目信息.json'
                if project_file.exists():
                    with open(project_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('id') == project_id:
                            project = ShortDramaProject(project_id, data['title'])
                            project.created_at = data.get('created_at', project.created_at)
                            project.updated_at = data.get('updated_at', project.updated_at)
                            project.status = data.get('status', 'draft')
                            project.episodes = data.get('episodes', [])
                            project.characters = data.get('characters', [])
                            project.settings = data.get('settings', project.settings)
                            return project
        return None

    @staticmethod
    def load_by_title(title):
        """根据小说标题加载项目"""
        project_file = get_project_file(title)
        if not project_file.exists():
            return None

        with open(project_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        project = ShortDramaProject(data.get('id'), title)
        project.created_at = data.get('created_at', project.created_at)
        project.updated_at = data.get('updated_at', project.updated_at)
        project.status = data.get('status', 'draft')
        project.episodes = data.get('episodes', [])
        project.characters = data.get('characters', [])
        project.settings = data.get('settings', project.settings)

        return project

    @staticmethod
    def list_all():
        """列出所有项目"""
        projects = []
        for project_dir in VIDEO_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                project_file = project_dir / '项目信息.json'
                if project_file.exists():
                    try:
                        with open(project_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            projects.append(data)
                    except Exception as e:
                        logger.error(f'加载项目失败 {project_dir}: {e}')

        # 按更新时间排序
        projects.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return projects


# ==================== 项目管理 API ====================

@short_drama_api.route('/projects', methods=['GET'])
def list_projects():
    """获取项目列表"""
    try:
        projects = ShortDramaProject.list_all()
        return jsonify({
            'success': True,
            'projects': projects
        }), 200
    except Exception as e:
        logger.error(f'获取项目列表失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    try:
        data = request.json or {}
        title = data.get('title', '未命名项目')

        project = ShortDramaProject(title=title)
        project.save()

        logger.info(f'✅ 创建项目: {project.id} - {title}')

        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 201
    except Exception as e:
        logger.error(f'创建项目失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/<project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情"""
    try:
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': '项目不存在'
            }), 404

        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 200
    except Exception as e:
        logger.error(f'获取项目失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/<project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    try:
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': '项目不存在'
            }), 404

        data = request.json or {}
        project.title = data.get('title', project.title)
        project.status = data.get('status', project.status)
        project.episodes = data.get('episodes', project.episodes)
        project.characters = data.get('characters', project.characters)
        project.settings = data.get('settings', project.settings)
        project.updated_at = datetime.now().isoformat()

        project.save()

        logger.info(f'✅ 更新项目: {project_id}')

        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 200
    except Exception as e:
        logger.error(f'更新项目失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    try:
        # 查找项目目录
        project = ShortDramaProject.load(project_id)
        if project:
            project_dir = get_project_dir(project.title)
            # 删除整个项目目录
            import shutil
            if project_dir.exists():
                shutil.rmtree(project_dir)
                logger.info(f'✅ 删除项目: {project_id} - {project.title}')
        else:
            logger.warning(f'⚠️ 项目不存在: {project_id}')

        return jsonify({
            'success': True,
            'message': '项目已删除'
        }), 200
    except Exception as e:
        logger.error(f'删除项目失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/<project_id>/data', methods=['GET'])
def get_project_data(project_id):
    """获取项目完整数据"""
    try:
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({
                'success': False,
                'error': '项目不存在'
            }), 404

        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 200
    except Exception as e:
        logger.error(f'获取项目数据失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/from-novel', methods=['POST'])
def create_from_novel():
    """从小说创建项目"""
    try:
        data = request.json or {}
        novel_id = data.get('novel_id')

        if not novel_id:
            return jsonify({
                'success': False,
                'error': '缺少小说ID'
            }), 400

        # 这里可以从小说数据中提取信息
        # 暂时创建一个空项目
        project = ShortDramaProject(title=f'短剧项目_{novel_id}')
        project.save()

        logger.info(f'✅ 从小说创建项目: {project.id}')

        return jsonify({
            'success': True,
            'project': project.to_dict()
        }), 201
    except Exception as e:
        logger.error(f'从小说创建项目失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/create-from-idea', methods=['POST'])
def create_from_idea():
    """从创意直接创建项目并生成分镜头"""
    try:
        data = request.json or {}
        title = data.get('title', '').strip()
        episode = data.get('episode', 1)
        description = data.get('description', '').strip()
        style = data.get('style', '通用')
        shot_count = data.get('shot_count', 3)
        shot_duration = data.get('shot_duration', 8)

        # 验证必填字段
        if not title:
            return jsonify({
                'success': False,
                'error': '请输入剧集名称'
            }), 400
        if not description:
            return jsonify({
                'success': False,
                'error': '请输入创意描述'
            }), 400

        # 限制参数范围
        episode = max(1, min(999, int(episode)))
        shot_count = max(1, min(10, int(shot_count)))
        shot_duration = max(4, min(15, int(shot_duration)))

        logger.info(f'📝 [创意导入] 标题: {title}, 第{episode}集, 风格: {style}, 镜头数: {shot_count}')

        # 1. 创建项目目录
        project_dir = VIDEO_PROJECTS_DIR / title
        project_dir.mkdir(exist_ok=True)

        episode_name = f'{episode}集_创意导入'
        episode_dir = project_dir / episode_name
        episode_dir.mkdir(exist_ok=True)

        storyboard_dir = episode_dir / 'storyboards'
        storyboard_dir.mkdir(exist_ok=True)

        # 2. 调用AI生成分镜头
        storyboard_data = generate_storyboard_from_idea(
            title=f"{title} 第{episode}集",
            description=description,
            style=style,
            shot_count=shot_count,
            shot_duration=shot_duration
        )

        # 3. 保存分镜头JSON
        storyboard_filename = f"{clean_filename(title)}_第{episode}集_创意分镜头.json"
        storyboard_file = storyboard_dir / storyboard_filename

        with open(storyboard_file, 'w', encoding='utf-8') as f:
            json.dump(storyboard_data, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ [创意导入] 分镜头已保存: {storyboard_file}')

        # 4. 创建/更新项目
        project = ShortDramaProject(title=title)
        project.episodes = [episode_name]
        project.save()

        return jsonify({
            'success': True,
            'project': project.to_dict(),
            'storyboard': storyboard_data,
            'message': f'成功生成 {shot_count} 个分镜头'
        }), 201

    except Exception as e:
        logger.error(f'❌ [创意导入] 创建失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_storyboard_from_idea(title: str, description: str, style: str,
                                   shot_count: int, shot_duration: int) -> dict:
    """
    根据创意描述生成分镜头数据

    Args:
        title: 剧集标题
        description: 创意描述
        style: 风格
        shot_count: 镜头数量
        shot_duration: 每镜头时长

    Returns:
        分镜头数据字典
    """
    try:
        # 构建生成提示词
        system_prompt = """你是一位专业的影视分镜头设计师。根据用户提供的创意描述，生成详细的分镜头脚本。

每个镜头需要包含：
1. shot_number: 镜头编号（从1开始）
2. shot_type: 镜头类型（特写/主观视角/近景/中景/全景/远景）
3. veo_prompt: 画面描述（静态画面）
   - 描述在这个镜头范围内看到什么（人物状态、表情、服装、环境、光线、质感、色彩）
   - 用姿态词表达空间关系：站立/坐下/跪地/悬空/倒地/扑向/后退/侧身
   - 不要描述动作过程，只描述画面定格时的样子
   - 示例："林启面部特写，满脸汗水与血污，双眼布满血丝，牙关紧咬，双手抓起锋利废铁片对准背部，废铁片反射幽冷金属光泽，绝望中的决绝表情。"
4. visual.description: 动作序列（动态过程）
   - 描述镜头中发生的动作变化，用箭头 → 连接
   - 格式：状态A → 状态B → 状态C
   - 示例："挥下废铁片 → 咬牙切开背部皮肉 → 鲜血碎肉飞溅 → 露出白森森脊柱"
5. dialogue: 对话信息（可选，如果无对话则speaker为"无"，lines为""，tone为"无"）
   - speaker: 说话者
   - lines: 台词（中文）
   - lines_en: 台词（英文）
   - tone: 语气（中文）
   - tone_en: 语气（英文）
   - audio_note: 音效描述（中文）
   - audio_note_en: 音效描述（英文）
6. duration_seconds: 镜头时长（秒）

【完整示例参考】
{
  "shot_number": 1,
  "shot_type": "特写",
  "veo_prompt": "林启面部特写，面部扭曲痛苦表情，双眼紧闭，汗珠与污泥混杂，下半身浸泡在冒泡的酸液中，周围是腐烂尸体残骸，昏暗光线，恐怖氛围。",
  "dialogue": {
    "speaker": "林启",
    "lines": "啊——！",
    "lines_en": "Ah—!",
    "tone": "撕心裂肺的痛苦",
    "tone_en": "heart-wrenching pain",
    "audio_note": "刺耳的尖叫，酸液腐蚀血肉的滋滋声",
    "audio_note_en": "piercing scream, sizzling sound of acid corroding flesh"
  },
  "visual": {
    "description": "猛然睁眼 → 瞳孔放大 → 剧烈挣扎 → 下半身被酸液腐蚀"
  },
  "duration_seconds": 8
}

【重要规则】
- veo_prompt只描述静态画面，不包含动作变化
- visual.description只描述动态过程，用箭头连接
- shot_type已定义构图范围，veo_prompt不需要重复说明"特写"等词汇
- 如果没有对话，dialogue的speaker设为"无"，lines为空字符串""，tone为"无"

请以JSON格式返回，结构如下：
{
    "video_title": "视频标题",
    "hook": "开篇钩子（一句话吸引眼球）",
    "total_duration": 总时长,
    "scenes": [
        {
            "scene_number": 场景号,
            "scene_title": "场景标题",
            "shot_sequence": [镜头列表]
        }
    ],
    "ending_hook": "结尾钩子"
}

【JSON格式要求】
- 严格遵守JSON规范
- 不要在最后一个属性后添加逗号
- 确保所有引号正确闭合
- 数字类型不要加引号"""

        user_prompt = f"""请根据以下创意生成分镜头脚本：

剧集标题：{title}
风格：{style}
创意描述：{description}

要求：
- 生成 {shot_count} 个镜头，每个镜头一个独立场景（scene_number从1开始）
- 每个镜头约 {shot_duration} 秒
- 风格要符合{style}特色
- 保持画面连贯性和节奏感
- 确保视觉冲击力
- veo_prompt要详细描述画面中的视觉元素（人物、环境、光线、质感）
- visual.description要用箭头→描述动作过程

请直接返回JSON格式的分镜头数据，不要包含其他说明文字。"""

        # 🔥 使用通用的APIClient调用AI
        if api_client is None:
            logger.error("❌ [AI生成] AI客户端未初始化")
            raise Exception("AI客户端未初始化")

        logger.info(f"🚀 [AI生成] 开始调用AI生成分镜头...")
        logger.info(f"   - 剧集标题: {title}")
        logger.info(f"   - 风格: {style}")
        logger.info(f"   - 镜头数: {shot_count}")

        # 使用APIClient调用AI（不使用流式，需要JSON格式）
        response_text = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            purpose="创意分镜头生成"
        )

        if not response_text:
            raise Exception("AI返回空响应")

        # 解析JSON响应
        try:
            # 尝试提取JSON（可能被```json包裹）
            json_text = response_text.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            elif json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()

            # 🔥 清理JSON中的常见问题
            import re
            # 移除对象/数组末尾的多余逗号
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)

            storyboard_data = json.loads(json_text)
            logger.info(f'✅ [AI生成] 分镜头生成成功，共 {len(storyboard_data.get("scenes", []))} 个场景')
            return storyboard_data
        except json.JSONDecodeError as e:
            logger.error(f'❌ [AI生成] JSON解析失败: {e}')
            logger.error(f'   AI响应: {response_text[:500]}...')
            raise Exception(f"AI返回的不是有效的JSON格式: {e}")

    except Exception as e:
        logger.error(f'❌ [AI生成] 分镜头生成失败: {e}')
        # 返回一个基础模板作为兜底
        return _get_default_storyboard(title, description, shot_count, shot_duration)


def _get_default_storyboard(title: str, description: str, shot_count: int, shot_duration: int) -> dict:
    """生成默认分镜头模板（AI失败时的兜底方案）"""
    shots = []
    for i in range(1, shot_count + 1):
        shots.append({
            'shot_number': i,
            'shot_type': ['主观视角', '特写', '中景', '全景'][i % 4],
            'veo_prompt': f'{title} - 镜头{i}：{description[:50]}...',
            'dialogue': {
                'speaker': '无',
                'lines': '',
                'tone': ''
            },
            'visual': {
                'description': f'镜头{i}的动作描述'
            },
            'duration_seconds': shot_duration
        })

    return {
        'video_title': title,
        'hook': description[:50] + '...',
        'total_duration': shot_count * shot_duration,
        'scenes': [
            {
                'scene_number': 1,
                'scene_title': '创意场景',
                'shot_sequence': shots
            }
        ],
        'ending_hook': '敬请期待'
    }


def clean_filename(name: str) -> str:
    """清理文件名，移除非法字符"""
    # 移除或替换Windows文件名中的非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    cleaned = re.sub(illegal_chars, '_', name)
    return cleaned.strip()


# ==================== 角色管理 API ====================

@short_drama_api.route('/storyboards', methods=['GET'])
def get_storyboards():
    """获取指定剧集的分镜头列表"""
    try:
        novel_title = request.args.get('novel')
        episode_name = request.args.get('episode')

        if not novel_title or not episode_name:
            return jsonify({
                'success': False,
                'error': '缺少参数'
            }), 400

        # 构建分镜头目录路径
        storyboard_dir = VIDEO_PROJECTS_DIR / novel_title / episode_name / 'storyboards'

        if not storyboard_dir.exists():
            return jsonify({
                'success': True,
                'storyboards': {}
            })

        # 🔥 尝试从 plan 文件中获取事件顺序
        medium_event_order = {}
        plan_file = NOVEL_PROJECTS_DIR / novel_title / 'plans' / f'{novel_title}_opening_stage_writing_plan.json'

        if plan_file.exists():
            try:
                with open(plan_file, 'r', encoding='utf-8') as f:
                    plan_data = json.load(f)

                event_system = plan_data.get('stage_writing_plan', {}).get('event_system', {})
                major_events = event_system.get('major_events', [])

                # 遍历所有重大事件和中型事件，建立顺序映射
                event_index = 0
                for major_event in major_events:
                    composition = major_event.get('composition', {})
                    for stage in ['起', '承', '转', '合']:
                        medium_events = composition.get(stage, [])
                        for medium_event in medium_events:
                            event_name = medium_event.get('name')
                            if event_name:
                                medium_event_order[event_name] = event_index
                                event_index += 1
                                logger.info(f"📋 [Plan] 事件 {event_index}: {event_name} ({stage})")

                logger.info(f'✅ [Plan] 从 plan 文件加载了 {len(medium_event_order)} 个事件顺序')
            except Exception as e:
                logger.error(f'读取 plan 文件失败: {e}')

        # 扫描分镜头文件
        storyboard_files = list(storyboard_dir.glob('*.json'))

        # 🔥 根据 plan 文件的顺序来排序 storyboards
        def get_event_order(filepath):
            """获取事件在 plan 中的顺序"""
            stem = filepath.stem
            # 去掉后缀 (_[1-3章][起] 等) 来匹配 plan 中的事件名
            event_name = stem
            import re
            # 去掉 _[1-3章][起承转合] 这样的后缀
            stage_match = re.search(r'\[([起承转合])\]$', event_name)
            if stage_match:
                event_name = event_name[:event_name.rfind('[')]
            chapter_match = re.search(r'\[\d+(?:-\d+)?章\]$', event_name)
            if chapter_match:
                event_name = event_name[:event_name.rfind('[')]
            event_name = event_name.rstrip('_')

            logger.info(f"🔍 [排序] 文件名: {stem} -> 提取的事件名: {event_name}")

            # 在 plan 中查找
            if event_name in medium_event_order:
                order = medium_event_order[event_name]
                logger.info(f"  ✅ 匹配成功: order={order}")
                return order
            # 如果不在 plan 中，返回一个大数字（排在最后）
            logger.info(f"  ❌ 未匹配，使用默认值 999999")
            return 999999

        # 按事件顺序排序文件
        storyboard_files.sort(key=get_event_order)

        logger.info(f"📂 [排序后文件顺序]:")
        for idx, f in enumerate(storyboard_files):
            logger.info(f"  [{idx}] {f.name}")

        # 按顺序加载分镜头，使用列表保持顺序
        storyboards_list = []
        for json_file in storyboard_files:
            try:
                order = get_event_order(json_file)
                logger.info(f"📂 文件: {json_file.name} -> 顺序: {order}")

                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 使用文件名（不含扩展名）作为 key
                    key = json_file.stem
                    # 提取显示名称
                    display_name = key
                    stage_match = re.search(r'\[([起承转合])\]$', display_name)
                    if stage_match:
                        display_name = display_name[:display_name.rfind('[')]
                    chapter_match = re.search(r'\[\d+(?:-\d+)?章\]$', display_name)
                    if chapter_match:
                        display_name = display_name[:display_name.rfind('[')]
                    display_name = display_name.rstrip('_')

                    # 在数据中添加显示名称和顺序字段
                    data['_display_name'] = display_name
                    data['_order'] = order
                    data['_key'] = key  # 保留原始key
                    # 将数据添加到列表中（保持顺序）
                    storyboards_list.append(data)
                    logger.info(f"📋 [加载] key={key}, display_name={display_name}, _order={order}")
            except Exception as e:
                logger.error(f'读取分镜头文件失败 {json_file}: {e}')

        logger.info(f'📜 [分镜头] 加载了 {len(storyboards_list)} 个分镜头文件')
        logger.info(f'📜 [返回的 storyboards 列表顺序]:')
        for idx, data in enumerate(storyboards_list):
            key = data.get('_key', 'N/A')
            display_name = data.get('_display_name', 'N/A')
            order = data.get('_order', 'N/A')
            logger.info(f"  [{idx}] _key={key}, _display_name={display_name}, _order={order}")

        return jsonify({
            'success': True,
            'storyboards': storyboards_list  # 返回列表而不是字典
        }), 200

    except Exception as e:
        logger.error(f'获取分镜头列表失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/portraits', methods=['GET'])
def get_portraits():
    """获取指定剧集的剧照列表"""
    try:
        from urllib.parse import quote

        novel_title = request.args.get('novel')
        episode_name = request.args.get('episode')

        if not novel_title or not episode_name:
            return jsonify({
                'success': False,
                'error': '缺少参数'
            }), 400

        # 构建剧集目录路径
        episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_name
        # 🔥 同时扫描父项目目录（用于角色参考图）
        project_dir = VIDEO_PROJECTS_DIR / novel_title

        logger.info(f'📸 [剧照] 扫描目录: {episode_dir}')
        logger.info(f'📸 [剧照] 同时扫描项目目录: {project_dir}')

        # 扫描剧照文件
        portraits = {}
        portrait_files = []

        # 剧集目录中的所有剧照
        if episode_dir.exists():
            portrait_files.extend(list(episode_dir.glob('*.png')) + list(episode_dir.glob('*.jpg')))

        # 🔥 项目目录中的角色参考图（包括 _三视图 和普通角色图）
        if project_dir.exists():
            # 扫描 _三视图 文件（最高优先级）
            three_view_files = [f for f in project_dir.glob('*_三视图.*')]
            portrait_files.extend(three_view_files)
            logger.info(f'📸 [剧照] 发现三视图文件: {[f.name for f in three_view_files]}')

            # 🔥 扫描项目目录中的其他角色参考图（排除三视图，已添加）
            # 获取所有图片文件
            all_project_images = list(project_dir.glob('*.png')) + list(project_dir.glob('*.jpg'))
            # 筛选出角色名图片（格式：角色名.png 或 角色名_数字.png）
            for img in all_project_images:
                stem = img.stem
                # 跳过已处理的 _三视图 文件
                if stem.endswith('_三视图'):
                    continue
                # 跳过明显不是角色图的文件（包含特殊字符的）
                if any(x in stem for x in ['_', '-']) and not stem.split('_')[-1].isdigit():
                    # 如果有下划线但最后一部分不是数字，可能是其他图片
                    continue
                portrait_files.append(img)

            logger.info(f'📸 [剧照] 项目目录图片文件数量: {len(all_project_images)}')
            logger.info(f'📸 [剧照] 添加的角色参考图: {[f.name for f in portrait_files if f.parent == project_dir and not f.name.endswith("_三视图")]}')

        for file_path in portrait_files:
            # 文件名格式: 角色名.png 或 角色名_1.png 或 角色名_三视图.png
            stem = file_path.stem  # 不含扩展名
            ext = file_path.suffix

            # 🔥 特殊处理后缀：_三视图 (最高优先级)
            is_three_view = stem.endswith('_三视图')
            if is_three_view:
                char_name = stem[:-4]  # 移除 '_三视图' 后缀
                number = 999  # 三视图优先级最高
                is_priority = True  # 标记为优先剧照
            else:
                # 解析角色名和编号
                is_priority = False
                if '_' in stem:
                    # 角色名_编号 格式
                    char_name, number_str = stem.rsplit('_', 1)
                    try:
                        number = int(number_str)
                    except ValueError:
                        char_name = stem
                        number = 0
                else:
                    char_name = stem
                    number = 0

            # 获取文件修改时间
            mtime = file_path.stat().st_mtime

            # 🔥 构建URL路径 - 根据文件位置决定URL
            # 项目目录的 _三视图 文件使用不同路径
            rel_path = file_path.relative_to(VIDEO_PROJECTS_DIR)
            url = f"/api/short-drama/projects/{rel_path.as_posix()}"

            if char_name not in portraits:
                portraits[char_name] = []

            portraits[char_name].append({
                'name': file_path.name,
                'number': number,
                'url': url,
                'mtime': mtime,
                'path': str(file_path),
                'isPriority': is_priority  # 🔥 标记是否为优先剧照
            })

        # 对每个角色的剧照按优先级、编号和修改时间排序
        # 优先级: 三视图 > 编号 > 修改时间
        result = []
        for char_name, char_portraits in portraits.items():
            char_portraits.sort(key=lambda x: (
                x['isPriority'],  # False < True, so True comes first when reverse=True
                x['number'],
                x['mtime']
            ), reverse=True)

            result.append({
                'character': char_name,
                'portraits': char_portraits,
                'mainPortrait': char_portraits[0]  # 最新的作为主图
            })

        logger.info(f'📸 [剧照] 扫描到 {len(result)} 个角色的剧照')

        return jsonify({
            'success': True,
            'portraits': result
        }), 200

    except Exception as e:
        logger.error(f'获取剧照列表失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/reference-images', methods=['GET'])
def get_reference_images():
    """获取项目的参考图片列表（reference_images目录）"""
    try:
        from urllib.parse import quote
        import os

        novel_title = request.args.get('novel', '')
        episode_title = request.args.get('episode', '')

        if not novel_title or not episode_title:
            return jsonify({
                'success': False,
                'error': '缺少小说标题或分集标题'
            }), 400

        # 构建参考图片目录路径
        ref_images_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'reference_images'

        if not ref_images_dir.exists():
            return jsonify({
                'success': True,
                'images': []
            }), 200

        images = []
        for file_path in ref_images_dir.glob('*.png'):
            # 获取文件修改时间
            mtime = file_path.stat().st_mtime

            # 构建URL路径
            url = f"/api/short-drama/projects/{quote(novel_title)}/{quote(episode_title)}/reference_images/{quote(file_path.name)}"

            images.append({
                'name': file_path.name,
                'url': url,
                'mtime': mtime,
                'size': file_path.stat().st_size
            })

        # 按修改时间排序，最新的在前
        images.sort(key=lambda x: x['mtime'], reverse=True)

        logger.info(f'📸 [参考图] 找到 {len(images)} 张参考图')

        return jsonify({
            'success': True,
            'images': images
        }), 200

    except Exception as e:
        logger.error(f'获取参考图列表失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/scene-props', methods=['GET'])
def get_scene_props():
    """获取项目的场景道具参考图片列表（场景道具目录）"""
    try:
        from urllib.parse import quote
        import os

        novel_title = request.args.get('novel', '')

        if not novel_title:
            return jsonify({
                'success': False,
                'error': '缺少小说标题'
            }), 400

        # 🔥 构建场景道具目录路径（项目级别，与episode同级）
        scene_props_dir = VIDEO_PROJECTS_DIR / novel_title / '场景道具'

        logger.info(f'🎬 [场景道具] 扫描目录: {scene_props_dir}')

        if not scene_props_dir.exists():
            logger.info(f'🎬 [场景道具] 目录不存在: {scene_props_dir}')
            return jsonify({
                'success': True,
                'images': []
            }), 200

        images = []
        # 支持常见图片格式
        for pattern in ['*.png', '*.jpg', '*.jpeg', '*.webp', '*.gif']:
            for file_path in scene_props_dir.glob(pattern):
                # 获取文件修改时间
                mtime = file_path.stat().st_mtime

                # 构建URL路径
                rel_path = file_path.relative_to(VIDEO_PROJECTS_DIR)
                url = f"/api/short-drama/projects/{rel_path.as_posix()}"

                images.append({
                    'name': file_path.name,
                    'url': url,
                    'mtime': mtime,
                    'size': file_path.stat().st_size,
                    'type': 'scene-prop'
                })

        # 按修改时间排序，最新的在前
        images.sort(key=lambda x: x['mtime'], reverse=True)

        logger.info(f'🎬 [场景道具] 找到 {len(images)} 张场景道具参考图')

        return jsonify({
            'success': True,
            'images': images
        }), 200

    except Exception as e:
        logger.error(f'获取场景道具列表失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/projects/<path:filepath>', methods=['GET'])
def serve_project_file(filepath):
    """提供项目文件访问（剧照、视频等）"""
    try:
        # filepath 是 URL 编码的路径，需要解码
        from urllib.parse import unquote

        # 解码路径
        decoded_path = unquote(filepath)

        file_path = VIDEO_PROJECTS_DIR / decoded_path

        if file_path.exists() and file_path.is_file():
            # 正常情况不打印日志
            return send_from_directory(str(file_path.parent), file_path.name)
        else:
            logger.error(f'📸 [剧照] 文件不存在: {file_path}')
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        logger.error(f'提供文件访问失败: {e}')
        return jsonify({'error': str(e)}), 500


@short_drama_api.route('/check-video', methods=['GET'])
def check_video():
    """检查视频文件是否存在"""
    try:
        from urllib.parse import unquote

        video_path = request.args.get('path')
        if not video_path:
            return jsonify({'exists': False}), 400

        # 解码路径
        decoded_path = unquote(video_path)

        logger.info(f'🎬 [视频检查] 检查文件: {decoded_path}')

        file_path = VIDEO_PROJECTS_DIR / decoded_path

        if file_path.exists() and file_path.is_file():
            # 返回相对路径用于API访问
            rel_path = file_path.relative_to(VIDEO_PROJECTS_DIR)
            url = f"/api/short-drama/projects/{rel_path.as_posix()}"

            logger.info(f'🎬 [视频检查] 文件存在: {file_path}')
            return jsonify({
                'exists': True,
                'path': str(file_path),
                'url': url
            })
        else:
            logger.info(f'🎬 [视频检查] 文件不存在: {file_path}')
            return jsonify({'exists': False})
    except Exception as e:
        logger.error(f'检查视频失败: {e}')
        return jsonify({'exists': False, 'error': str(e)}), 500


@short_drama_api.route('/list-videos', methods=['GET'])
def list_videos():
    """列出指定目录的视频文件"""
    try:
        from urllib.parse import unquote

        episode = request.args.get('episode')
        novel = request.args.get('novel')

        if not episode or not novel:
            return jsonify({'videos': []}), 400

        # 构建视频目录路径
        video_dir = VIDEO_PROJECTS_DIR / novel / episode / 'videos'

        logger.info(f'🎬 [视频列表] 扫描目录: {video_dir}')

        if not video_dir.exists():
            return jsonify({'videos': []})

        videos = []
        for video_file in video_dir.glob('*.mp4'):
            # 新文件名格式: "001_01_诈尸惊魂_对话01_中景_特写_001.mp4"
            # 格式: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话{对话序号:02d}_{镜头类型}_{句子序号:03d}
            name = video_file.stem  # 不含扩展名
            import re

            # 🔥 优先尝试匹配对话场景格式（有"对话"前缀）
            dialogue_match = re.match(r'^(\d+)_(\d+)_(.+)_对话(\d+)_(.+?)_(\d+)$', name)
            if dialogue_match:
                episode_num = int(dialogue_match.group(1))
                scene_num = int(dialogue_match.group(2))
                episode_name = dialogue_match.group(3)
                dialogue_idx = int(dialogue_match.group(4))
                shot_type = dialogue_match.group(5)
                sentence_num = int(dialogue_match.group(6))

                videos.append({
                    'sequence': episode_num,
                    'scene_number': scene_num,
                    'episode_name': episode_name,
                    'dialogue_index': dialogue_idx,
                    'shot_type': shot_type,
                    'sentence_num': sentence_num,
                    'is_dialogue_scene': True,
                    'name': name,
                    'filename': video_file.name,
                    'storyboard_key': episode_name,
                    'path': str(video_file.relative_to(VIDEO_PROJECTS_DIR)),
                    'url': f"/api/short-drama/projects/{video_file.relative_to(VIDEO_PROJECTS_DIR).as_posix()}"
                })
                continue

            # 🔥 尝试匹配普通场景格式（无"对话"前缀）
            # 格式: {章节序号:03d}_{场景序号:02d}_{事件名}_{镜头类型}_{句子序号:03d}
            normal_match = re.match(r'^(\d+)_(\d+)_(.+)_(.+?)_(\d+)$', name)
            if normal_match:
                episode_num = int(normal_match.group(1))
                scene_num = int(normal_match.group(2))
                episode_name = normal_match.group(3)
                shot_type = normal_match.group(4)
                sentence_num = int(normal_match.group(5))

                videos.append({
                    'sequence': episode_num,
                    'scene_number': scene_num,
                    'episode_name': episode_name,
                    'dialogue_index': None,
                    'shot_type': shot_type,
                    'sentence_num': sentence_num,
                    'is_dialogue_scene': False,
                    'name': name,
                    'filename': video_file.name,
                    'storyboard_key': episode_name,
                    'path': str(video_file.relative_to(VIDEO_PROJECTS_DIR)),
                    'url': f"/api/short-drama/projects/{video_file.relative_to(VIDEO_PROJECTS_DIR).as_posix()}"
                })
                continue

            # 尝试匹配旧格式: {镜头号}_{事件名}_{镜头类型}
            old_match = re.match(r'^(\d+)_(.+)', name)
            if old_match:
                seq_num = int(old_match.group(1))
                rest_of_name = old_match.group(2)

                videos.append({
                    'sequence': seq_num,
                    'name': name,
                    'filename': video_file.name,
                    'storyboard_key': rest_of_name,
                    'path': str(video_file.relative_to(VIDEO_PROJECTS_DIR)),
                    'url': f"/api/short-drama/projects/{video_file.relative_to(VIDEO_PROJECTS_DIR).as_posix()}"
                })

        # 按序号排序
        videos.sort(key=lambda v: v['sequence'])

        logger.info(f'🎬 [视频列表] 找到 {len(videos)} 个视频文件')
        return jsonify({'videos': videos})

    except Exception as e:
        logger.error(f'列出视频失败: {e}')
        return jsonify({'videos': [], 'error': str(e)}), 500


@short_drama_api.route('/characters/<character_id>/portrait', methods=['POST'])
def generate_character_portrait(character_id):
    """生成角色剧照"""
    try:
        data = request.json or {}
        project_id = data.get('project_id')

        logger.info(f'🎨 生成角色剧照: {character_id}')

        # 这里调用剧照生成API
        # 暂时返回成功

        return jsonify({
            'success': True,
            'message': '剧照生成任务已提交'
        }), 202
    except Exception as e:
        logger.error(f'生成剧照失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 分镜头管理 API ====================

@short_drama_api.route('/shots/<shot_id>/video', methods=['POST'])
def generate_shot_video(shot_id):
    """生成镜头视频"""
    try:
        data = request.json or {}
        project_id = data.get('project_id')

        logger.info(f'🎬 生成镜头视频: {shot_id}')

        # 这里调用视频生成API
        # 暂时返回成功

        return jsonify({
            'success': True,
            'message': '视频生成任务已提交',
            'task_id': f'task_{uuid.uuid4().hex[:8]}'
        }), 202
    except Exception as e:
        logger.error(f'生成视频失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots/<shot_id>/status', methods=['GET'])
def get_shot_status(shot_id):
    """获取镜头生成状态"""
    try:
        # 这里查询视频生成状态
        # 暂时返回处理中

        return jsonify({
            'success': True,
            'status': 'processing',
            'progress': 50
        }), 200
    except Exception as e:
        logger.error(f'获取镜头状态失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 文件备份与还原 API ====================

@short_drama_api.route('/backup', methods=['POST'])
def backup_file():
    """
    备份文件（用于重新生成前备份原文件）

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "file_type": "video" | "audio",
        "shot_number": 1,
        "file_path": "原文件相对路径"
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        file_type = data.get('file_type', 'video')
        shot_number = data.get('shot_number')
        file_path = data.get('file_path')

        if not all([novel_title, episode_title, shot_number]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 构建备份目录
        backup_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / '.backups' / file_type
        backup_dir.mkdir(parents=True, exist_ok=True)

        # 原文件路径
        if file_path:
            # 如果提供了完整路径
            if file_path.startswith('/'):
                # URL路径，需要解码
                original_file = VIDEO_PROJECTS_DIR / unquote(file_path.lstrip('/'))
            else:
                original_file = VIDEO_PROJECTS_DIR / file_path
        else:
            # 根据类型和镜头号构建路径
            if file_type == 'video':
                file_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'videos'
                pattern = f"*_{shot_number}_*.mp4"
            else:  # audio
                file_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'
                pattern = f"{shot_number}_*.mp3"

            files = list(file_dir.glob(pattern))
            if not files:
                return jsonify({'success': False, 'error': '未找到原文件'}), 404
            original_file = files[0]

        if not original_file.exists():
            return jsonify({'success': False, 'error': f'原文件不存在: {original_file}'}), 404

        # 生成备份文件名（带时间戳）
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"{original_file.stem}_{timestamp}{original_file.suffix}"
        backup_path = backup_dir / backup_filename

        # 复制文件到备份目录
        shutil.copy2(original_file, backup_path)

        logger.info(f'💾 文件已备份: {original_file} -> {backup_path}')

        return jsonify({
            'success': True,
            'backup_path': str(backup_path.relative_to(VIDEO_PROJECTS_DIR)),
            'backup_filename': backup_filename,
            'timestamp': timestamp
        })
    except Exception as e:
        logger.error(f'备份文件失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/backups', methods=['GET'])
def list_backups():
    """
    列出某个镜头的所有备份

    参数：
        novel_title: 小说名
        episode_title: 集数名
        file_type: video | audio
        shot_number: 镜头号
    """
    try:
        novel_title = request.args.get('novel')
        episode_title = request.args.get('episode')
        file_type = request.args.get('file_type', 'video')
        shot_number = request.args.get('shot_number')

        if not all([novel_title, episode_title, shot_number]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        backup_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / '.backups' / file_type

        if not backup_dir.exists():
            return jsonify({'success': True, 'backups': []})

        # 查找该镜头的所有备份
        backups = []
        pattern = f"*_{shot_number}_*"
        for backup_file in backup_dir.glob(pattern):
            # 解析时间戳
            parts = backup_file.stem.split('_')
            if len(parts) >= 2:
                timestamp_str = parts[-1]
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    timestamp_formatted = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                except:
                    timestamp_formatted = timestamp_str
            else:
                timestamp_formatted = 'Unknown'

            backups.append({
                'filename': backup_file.name,
                'path': str(backup_file.relative_to(VIDEO_PROJECTS_DIR)),
                'timestamp': timestamp_formatted,
                'size': backup_file.stat().st_size
            })

        # 按时间倒序排列
        backups.sort(key=lambda x: x['timestamp'], reverse=True)

        return jsonify({
            'success': True,
            'backups': backups
        })
    except Exception as e:
        logger.error(f'列出备份失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/restore', methods=['POST'])
def restore_backup():
    """
    从备份还原文件

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "backup_path": "备份文件相对路径",
        "backup_current": true  # 是否先备份当前文件
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        backup_path = data.get('backup_path')
        backup_current = data.get('backup_current', True)

        if not all([novel_title, episode_title, backup_path]):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        # 备份文件完整路径
        backup_file = VIDEO_PROJECTS_DIR / backup_path

        if not backup_file.exists():
            return jsonify({'success': False, 'error': '备份文件不存在'}), 404

        # 确定目标文件路径
        if backup_path.startswith('.backups/video/'):
            # 视频文件
            target_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'videos'
        elif backup_path.startswith('.backups/audio/'):
            # 音频文件
            target_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'
        else:
            return jsonify({'success': False, 'error': '无法确定目标目录'}), 400

        # 从备份文件名提取原始文件名（去掉时间戳）
        backup_filename = backup_file.name
        # 格式: original_name_timestamp.ext
        parts = backup_filename.rsplit('_', 2)
        if len(parts) >= 3:
            original_filename = '_'.join(parts[:-2]) + backup_file.suffix
        else:
            original_filename = backup_filename

        target_file = target_dir / original_filename

        # 如果要求，先备份当前文件
        if backup_current and target_file.exists():
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            current_backup = target_dir.parent / '.backups' / backup_path.split('/')[2] / f"{target_file.stem}_current_{timestamp}{target_file.suffix}"
            current_backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_file, current_backup)
            logger.info(f'💾 当前文件已备份: {current_backup}')

        # 还原文件
        shutil.copy2(backup_file, target_file)

        logger.info(f'♻️ 文件已还原: {backup_file} -> {target_file}')

        return jsonify({
            'success': True,
            'restored_file': str(target_file.relative_to(VIDEO_PROJECTS_DIR)),
            'original_filename': original_filename
        })
    except Exception as e:
        logger.error(f'还原备份失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/backup/delete', methods=['POST'])
def delete_backup():
    """
    删除备份文件

    请求体：
    {
        "backup_path": "备份文件相对路径"
    }
    """
    try:
        data = request.json
        backup_path = data.get('backup_path')

        if not backup_path:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400

        backup_file = VIDEO_PROJECTS_DIR / backup_path

        if not backup_file.exists():
            return jsonify({'success': False, 'error': '备份文件不存在'}), 404

        backup_file.unlink()

        logger.info(f'🗑️ 备份已删除: {backup_path}')

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f'删除备份失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


def register_short_drama_routes(app):
    """注册短剧工作台路由"""
    app.register_blueprint(short_drama_api)
    logger.info('✅ 短剧工作台 API 已注册')
