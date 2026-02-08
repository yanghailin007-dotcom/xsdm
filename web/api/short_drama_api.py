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


def _translate_to_chinese_sync(text: str) -> str:
    """同步翻译英文到中文（内部使用）"""
    try:
        if not api_client:
            logger.warning('AI客户端未初始化，跳过翻译')
            return text

        system_prompt = """你是一个专业的视频提示词翻译专家。
请将英文视频生成提示词翻译成流畅的中文，保持专业术语的准确性。
注意：
- 保持技术术语的准确性（如 cinematic, photorealistic, 8k 等可以保留或翻译为"电影级"、"写实风格"、"8K超清"）
- 翻译要自然流畅，符合中文表达习惯
- 保持原文的结构和重点
- 只返回翻译结果，不要添加任何解释"""

        # 使用正确的 API 方法
        response = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=f"请翻译以下视频提示词：\n\n{text}",
            json_mode=False
        )

        if response:
            return response.strip()
        return text
    except Exception as e:
        logger.error(f'翻译失败: {e}')
        return text  # 翻译失败返回原文


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
        self.storyBeats = None  # 故事节拍数据
        self.settings = {
            'aspect_ratio': '9:16',
            'quality': '4K',
            'model': 'veo_3_1-fast',
            'use_first_last_frame': True  # 🔥 默认开启首尾帧模式
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
            'storyBeats': self.storyBeats,
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
        logger.info(f"[ShortDramaProject.load] 查找项目: {project_id}")
        # 遍历所有项目目录查找
        for project_dir in VIDEO_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                project_file = project_dir / '项目信息.json'
                if project_file.exists():
                    with open(project_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if data.get('id') == project_id:
                            logger.info(f"[ShortDramaProject.load] 找到项目文件: {project_file}")
                            logger.info(f"[ShortDramaProject.load] 文件中的storyBeats: {'storyBeats' in data}")
                            project = ShortDramaProject(project_id, data['title'])
                            project.created_at = data.get('created_at', project.created_at)
                            project.updated_at = data.get('updated_at', project.updated_at)
                            project.status = data.get('status', 'draft')
                            project.episodes = data.get('episodes', [])
                            project.characters = data.get('characters', [])
                            project.storyBeats = data.get('storyBeats')
                            project.settings = data.get('settings', project.settings)
                            logger.info(f"[ShortDramaProject.load] 加载后storyBeats: {project.storyBeats is not None}")

                            # 🔥 加载每个episode的storyboard数据
                            project._load_episode_storyboards(project_dir)

                            return project
        logger.warning(f"[ShortDramaProject.load] 未找到项目: {project_id}")
        return None

    def _load_episode_storyboards(self, project_dir):
        """加载每个episode的storyboard数据并转换为shots数组"""
        if not isinstance(self.episodes, list):
            return

        enriched_episodes = []
        for episode_name in self.episodes:
            # 如果已经是字典对象（有shots），直接使用
            if isinstance(episode_name, dict):
                enriched_episodes.append(episode_name)
                continue

            # 构建episode目录路径
            episode_dir = project_dir / episode_name
            storyboard_dir = episode_dir / 'storyboards'

            # 创建episode对象
            episode_obj = {
                'title': episode_name,
                'shots': []
            }

            # 如果storyboard目录存在，加载storyboard文件
            if storyboard_dir.exists() and storyboard_dir.is_dir():
                storyboard_files = list(storyboard_dir.glob('*.json'))

                shot_id_counter = 1
                for json_file in storyboard_files:
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            storyboard_data = json.load(f)

                            # 从scenes中提取shot_sequence
                            scenes = storyboard_data.get('scenes', [])
                            for scene in scenes:
                                shot_sequence = scene.get('shot_sequence', [])
                                scene_title = scene.get('scene_title', '')
                                scene_number = scene.get('scene_number', 1)

                                for shot in shot_sequence:
                                    # 🔥 兼容新旧数据结构：优先使用新模式，否则使用旧模式
                                    veo_prompt_standard = shot.get('veo_prompt_standard') or shot.get('veo_prompt', '')
                                    veo_prompt_reference = shot.get('veo_prompt_reference') or shot.get('veo_prompt', '')
                                    veo_prompt_frames = shot.get('veo_prompt_frames') or shot.get('veo_prompt', '')
                                    
                                    visual_standard = shot.get('visual_description_standard') or shot.get('visual_description', '') or shot.get('veo_prompt', '')
                                    visual_reference = shot.get('visual_description_reference') or shot.get('visual_description', '') or shot.get('veo_prompt', '')
                                    visual_frames = shot.get('visual_description_frames') or shot.get('visual_description', '') or shot.get('veo_prompt', '')
                                    
                                    # 转换为frontend期望的格式
                                    shot_obj = {
                                        'id': f"shot_{shot_id_counter}",
                                        'shot_number': shot.get('shot_number', 1),
                                        'scene_number': scene_number,
                                        'scene_title': scene_title,
                                        'shot_type': shot.get('shot_type', ''),
                                        'duration': shot.get('duration_seconds', shot.get('duration', 8)),
                                        # 三种模式的英文提示词
                                        'veo_prompt_standard': veo_prompt_standard,
                                        'veo_prompt_reference': veo_prompt_reference,
                                        'veo_prompt_frames': veo_prompt_frames,
                                        # 三种模式的中文描述
                                        'visual_description_standard': visual_standard,
                                        'visual_description_reference': visual_reference,
                                        'visual_description_frames': visual_frames,
                                        # 兼容旧模式
                                        'veo_prompt': shot.get('veo_prompt', ''),
                                        'visual_description': shot.get('visual_description', ''),
                                        'preferred_mode': shot.get('preferred_mode', 'standard'),
                                        'dialogue': shot.get('dialogue', {}),
                                        'visual': shot.get('visual', {}),
                                        'status': 'pending'
                                    }
                                    episode_obj['shots'].append(shot_obj)
                                    shot_id_counter += 1

                    except Exception as e:
                        logger.error(f'加载storyboard文件失败 {json_file}: {e}')

                logger.info(f'📋 [Episode] {episode_name}: 加载了 {len(episode_obj["shots"])} 个镜头')

            enriched_episodes.append(episode_obj)

        # 更新episodes为enriched版本
        self.episodes = enriched_episodes


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
        project.storyBeats = data.get('storyBeats')
        project.settings = data.get('settings', project.settings)

        # 🔥 加载每个episode的storyboard数据
        project_dir = project_file.parent
        project._load_episode_storyboards(project_dir)

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
        logger.info(f"[项目数据] 加载项目: {project_id}")
        project = ShortDramaProject.load(project_id)
        if not project:
            logger.warning(f"[项目数据] 项目不存在: {project_id}")
            return jsonify({
                'success': False,
                'error': '项目不存在'
            }), 404

        result = project.to_dict()
        logger.info(f"[项目数据] 返回数据: storyBeats exists = {'storyBeats' in result and result['storyBeats'] is not None}")
        if 'storyBeats' in result and result['storyBeats']:
            logger.info(f"[项目数据] 返回数据: scenes count = {len(result['storyBeats'].get('scenes', []))}")

        return jsonify({
            'success': True,
            'project': result
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
    """从创意创建项目，先生成故事节拍（Step 3）"""
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
        
        # 计算总时长
        total_duration = shot_count * shot_duration

        logger.info(f'📝 [创意导入] 标题: {title}, 第{episode}集, 风格: {style}, 预计{shot_count}个镜头, 总时长{total_duration}秒')

        # 1. 创建项目目录
        project_dir = VIDEO_PROJECTS_DIR / title
        project_dir.mkdir(exist_ok=True)

        episode_name = f'{episode}集_创意导入'
        episode_dir = project_dir / episode_name
        episode_dir.mkdir(exist_ok=True)

        # 2. 调用AI生成故事节拍 (Step 3)
        logger.info(f'[创意导入] 开始生成故事节拍...')
        story_beats = generate_story_beats_from_idea(
            title=f"{title} 第{episode}集",
            description=description,
            style=style,
            total_duration=total_duration
        )

        # 3. 基于故事节拍生成专业分镜头（全英文）(Step 4)
        logger.info(f'[创意导入] 基于故事节拍生成分镜头（全英文）...')
        shots_en = generate_shots_from_storybeats(
            title=title,
            story_beats=story_beats,
            style=style,
            shot_duration=shot_duration
        )

        # 4. 保存英文版 shots_v2.json
        shots_v2_data = {
            'version': '2.0',
            'generated_at': datetime.now().isoformat(),
            'language': 'en',
            'title': title,
            'episode': episode,
            'total_shots': len(shots_en),
            'shots': shots_en
        }
        shots_v2_file = episode_dir / 'shots_v2.json'
        with open(shots_v2_file, 'w', encoding='utf-8') as f:
            json.dump(shots_v2_data, f, ensure_ascii=False, indent=2)
        logger.info(f'✅ [创意导入] 英文分镜头已保存: {shots_v2_file}')

        # 5. 调用AI将分镜头翻译成中文 (Step 5)
        logger.info(f'[创意导入] 调用AI翻译分镜头为中文...')
        shots_cn = translate_shots_to_chinese(shots_en)

        # 6. 保存中文版 shots_v2_cn.json
        shots_v2_cn_data = {
            'version': '2.0',
            'generated_at': datetime.now().isoformat(),
            'language': 'cn',
            'title': title,
            'episode': episode,
            'total_shots': len(shots_cn),
            'shots': shots_cn
        }
        shots_v2_cn_file = episode_dir / 'shots_v2_cn.json'
        with open(shots_v2_cn_file, 'w', encoding='utf-8') as f:
            json.dump(shots_v2_cn_data, f, ensure_ascii=False, indent=2)
        logger.info(f'✅ [创意导入] 中文分镜头已保存: {shots_v2_cn_file}')

        # 使用中文版本作为前端展示的shots
        shots = shots_cn
        
        # 6. 创建项目信息（兼容前端格式）
        project_data = {
            'id': str(uuid.uuid4())[:8],
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'status': 'draft',
            'episodes': [{
                'id': episode_name,
                'title': f'第{episode}集',
                'name': episode_name,
                'content': description,
                'shot_count': len(shots),
                'shot_duration': shot_duration,
                'shots': shots  # 添加前端兼容的shots数组
            }],
            'characters': [],  # 创意导入暂无角色，后续可添加
            'settings': {
                'aspect_ratio': '9:16',
                'quality': '1080p',
                'model': 'veo_3_1-fast',
                'use_first_last_frame': True
            },
            'storyBeats': story_beats  # 保存原始故事节拍
        }

        # 7. 保存项目JSON
        project_file = project_dir / '项目信息.json'
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ [创意导入] 项目已创建: {project_file}')
        logger.info(f'✅ [创意导入] 故事节拍已生成: {len(story_beats.get("scenes", []))} 场景')

        return jsonify({
            'success': True,
            'project': project_data,
            'storyBeats': story_beats,
            'message': f'成功创建项目并生成故事节拍，共{len(story_beats.get("scenes", []))}个场景'
        }), 201

    except Exception as e:
        logger.error(f'❌ [创意导入] 创建失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_story_beats_from_idea(title: str, description: str, style: str, total_duration: int = 80) -> dict:
    """
    根据创意描述生成故事节拍 (Step 3)
    
    Args:
        title: 剧集标题
        description: 创意描述
        style: 风格
        total_duration: 总时长（秒）
        
    Returns:
        故事节拍数据字典
    """
    try:
        # 计算场景数（每个场景平均4-8秒）
        avg_scene_duration = 6
        scene_count = max(3, min(15, total_duration // avg_scene_duration))
        
        # 调整每个场景时长使总和等于总时长
        base_duration = total_duration // scene_count
        remainder = total_duration % scene_count
        
        system_prompt = f"""你是一个专业的短剧编剧。请根据以下创意描述，生成{total_duration}秒的故事节拍(Story Beats)。

## 输出要求

1. **三幕结构分配**
   - 第一幕「建立」(0-30%)：建立场景、人物、核心矛盾
   - 第二幕「对抗」(30-70%)：冲突升级、内心挣扎
   - 第三幕「高潮」(70-100%)：高潮时刻、人物觉醒、悬念收尾

2. **场景设计原则**
   - 生成{scene_count}个场景
   - 每个场景时长4-10秒
   - 总时长严格等于{total_duration}秒
   - 场景之间有逻辑连贯性

3. **对白设计**
   - 每个场景至少1句对白
   - 对白要推动剧情或展示人物性格
   - 提供中英文双语

4. **输出格式**
只输出JSON，格式如下：
{{
  "scenes": [
    {{
      "sceneNumber": 1,
      "sceneTitleCn": "中文场景标题",
      "sceneTitleEn": "English Scene Title",
      "storyBeatCn": "中文叙事目的",
      "storyBeatEn": "English story purpose",
      "durationSeconds": 6,
      "emotionalArc": "绝决→紧张",
      "dialogues": [
        {{
          "timestamp": 0,
          "speaker": "角色名",
          "linesCn": "中文台词",
          "linesEn": "English lines",
          "toneCn": "语气描述",
          "toneEn": "Tone description"
        }}
      ]
    }}
  ]
}}
"""

        user_prompt = f"""
剧集标题：{title}
风格：{style}
总时长：{total_duration}秒
预计场景数：{scene_count}

创意描述：
{description}

请生成故事节拍JSON。
"""

        if api_client:
            try:
                response = api_client.call_api(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=0.7,
                    purpose="故事节拍生成"
                )
                
                content = response.get('content', '') if isinstance(response, dict) else str(response)
                
                # 提取JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    story_beats = json.loads(json_match.group())
                else:
                    story_beats = json.loads(content)
                
                # 验证并调整时长
                if 'scenes' in story_beats:
                    scenes = story_beats['scenes']
                    # 调整场景数使之符合预期
                    if len(scenes) != scene_count:
                        logger.warning(f'故事节拍场景数不匹配: 期望{scene_count}, 实际{len(scenes)}')
                    
                    # 调整时长使总和等于总时长
                    total = sum(s.get('durationSeconds', base_duration) for s in scenes)
                    if total != total_duration:
                        # 均匀分配差额
                        diff = total_duration - total
                        if diff != 0 and len(scenes) > 0:
                            adjust = diff // len(scenes)
                            for s in scenes:
                                s['durationSeconds'] = s.get('durationSeconds', base_duration) + adjust
                
                return story_beats
                
            except Exception as e:
                logger.error(f'AI生成故事节拍失败: {e}')
                return _get_default_story_beats_for_idea(scene_count, base_duration, remainder)
        else:
            return _get_default_story_beats_for_idea(scene_count, base_duration, remainder)
            
    except Exception as e:
        logger.error(f'生成故事节拍失败: {e}')
        return _get_default_story_beats_for_idea(3, 8, 0)


def _get_default_story_beats_for_idea(scene_count: int, base_duration: int, remainder: int):
    """获取默认故事节拍（用于创意导入）"""
    scenes = []
    for i in range(scene_count):
        duration = base_duration + (1 if i < remainder else 0)
        scenes.append({
            'sceneNumber': i + 1,
            'sceneTitleCn': f'场景{i+1}',
            'sceneTitleEn': f'Scene {i+1}',
            'storyBeatCn': '展示情节发展',
            'storyBeatEn': 'Show plot development',
            'durationSeconds': duration,
            'emotionalArc': '平静→紧张',
            'dialogues': [{
                'timestamp': 0,
                'speaker': '主角',
                'linesCn': '这是一个重要的时刻...',
                'linesEn': 'This is an important moment...',
                'toneCn': '内心独白',
                'toneEn': 'Inner monologue'
            }]
        })
    return {'scenes': scenes}


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
        system_prompt = """你是一位专业的影视分镜头设计师，擅长为AI视频生成工具（如Sora、Runway、Veo）设计高质量的分镜头脚本。

每个镜头需要包含：
1. shot_number: 镜头编号（从1开始）
2. shot_type: 镜头类型（特写/主观视角/近景/中景/全景/远景）
3. veo_prompt: 画面描述（静态画面）- 这是最关键的部分，需要包含：

   【画面构成】
   - 描述在这个镜头范围内看到什么（人物状态、表情、服装、环境）
   - 用姿态词表达空间关系：站立/坐下/跪地/悬空/倒地/扑向/后退/侧身
   - 不要描述动作过程，只描述画面定格时的样子

   【运镜指令】（提升电影感的关键）
   - 推镜头（Push in）：从远到近，增强紧张感和代入感
   - 拉镜头（Pull out）：从近到远，展现环境和空间关系
   - 环绕镜头（Orbit）：围绕主体旋转，展现立体感
   - 跟随镜头（Follow）：跟随人物移动，增强动态感
   - 升降镜头（Crane up/down）：垂直移动，展现宏大场景
   - 示例："缓慢推镜头，从全景推至面部特写"、"环绕镜头，360度展现人物"

   【光影细节】（提升画面质感）
   - 体积光（Volumetric lighting）：光束穿透烟雾/尘埃的效果
   - 丁达尔效应（God rays）：光线透过缝隙形成的光柱
   - 边缘光（Rim light）：勾勒人物轮廓的背光
   - 戏剧性光影（Dramatic lighting）：强烈的明暗对比
   - 色温对比（Color temperature）：冷暖光源的对比
   - 示例："体积光穿透石室缝隙，形成明显的丁达尔效应"、"金色边缘光勾勒人物轮廓"

   【材质质感】（增强真实感）
   - 皮肤质感：细腻的毛孔、汗珠、血管
   - 服装材质：丝绸的光泽、布料的褶皱、金属的反光
   - 环境质感：石材的粗糙、水面的波纹、尘埃的漂浮
   - 特效质感：灵气的流动、能量的闪烁、光芒的扩散
   - 示例："皮肤呈现晶莹剔透的玉质光泽，细密的汗珠反射光线"

   【完整示例】
   "幽暗封闭的石室内部，缓慢推镜头从全景推至中景，地面刻画着繁复发光的聚灵阵法，慕佩灵身着素白长裙盘膝坐于阵眼中心，体积光从石室顶部缝隙射入形成明显的丁达尔效应，金色边缘光勾勒出人物轮廓，四周摆放着五色灵石散发柔和光晕，空气中漂浮着肉眼可见的灵气光尘如萤火虫般流动，皮肤呈现出玉质般的细腻光泽，衣料质感柔软飘逸，压抑而神圣的氛围。"

4. visual.description: 动作序列（动态过程）
   - 描述镜头中发生的动作变化，用箭头 → 连接
   - 格式：状态A → 状态B → 状态C
   - 示例："阵法光芒骤然亮起 → 灵石开始剧烈颤抖 → 灵气光尘疯狂涌向慕佩灵"

5. dialogue: 对话信息（可选，如果无对话则speaker为"无"，lines为""，tone为"无"）
   - speaker: 说话者
   - lines: 台词（中文）- 根据镜头时长合理安排台词量
   - lines_en: 台词（英文）
   - tone: 语气（中文）
   - tone_en: 语气（英文）
   - audio_note: 音效描述（中文）
   - audio_note_en: 音效描述（英文）

6. duration_seconds: 镜头时长（秒）- 根据镜头内容调整时长
   - 快节奏动作场景：4-6秒
   - 对话场景：6-8秒
   - 情绪渲染场景：8-10秒
   - 宏大场景展示：10-12秒

【节奏控制原则】
- 利用长短镜头交替制造节奏感
- 紧张场景用短镜头快切
- 情感高潮用长镜头渲染
- 避免所有镜头都是相同时长

【对话设计原则】
- 短剧节奏快，对话要密集
- 8秒镜头建议2-3句台词（每句2-3秒）
- 10秒以上镜头建议3-5句台词
- 对话要推动剧情，不要空洞
- 台词要符合人物性格和情境

【完整示例参考】
{
  "shot_number": 1,
  "shot_type": "全景",
  "veo_prompt": "幽暗封闭的石室内部，缓慢推镜头从全景推至中景，地面刻画着繁复发光的聚灵阵法，慕佩灵身着素白长裙盘膝坐于阵眼中心，体积光从石室顶部缝隙射入形成明显的丁达尔效应，金色边缘光勾勒出人物轮廓，四周摆放着五色灵石散发柔和光晕，空气中漂浮着肉眼可见的灵气光尘如萤火虫般流动，皮肤呈现出玉质般的细腻光泽，衣料质感柔软飘逸，压抑而神圣的氛围。",
  "dialogue": {
    "speaker": "慕佩灵",
    "lines": "如果不拼这一次，我永远只是韩前辈身边的累赘！",
    "lines_en": "If I don't risk it all this time, I'll forever be a burden to Senior Han!",
    "tone": "内心独白，决绝",
    "tone_en": "Inner monologue, determined",
    "audio_note": "低沉的阵法嗡鸣声，心跳声逐渐放大",
    "audio_note_en": "Low hum of the array, heartbeat gradually amplifying"
  },
  "visual": {
    "description": "阵法光芒骤然亮起 → 灵石开始剧烈颤抖 → 灵气光尘疯狂涌向慕佩灵"
  },
  "duration_seconds": 8
}

【重要规则】
- veo_prompt必须包含运镜指令、光影细节、材质质感
- veo_prompt只描述静态画面，不包含动作变化
- visual.description只描述动态过程，用箭头连接
- shot_type已定义构图范围，veo_prompt不需要重复说明"特写"等词汇
- 如果没有对话，dialogue的speaker设为"无"，lines为空字符串""，tone为"无"
- 根据镜头内容调整时长，避免所有镜头都是固定时长

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
- 每个镜头时长根据内容调整（快节奏4-6秒，对话6-8秒，情绪渲染8-10秒，宏大场景10-12秒）
- 风格要符合{style}特色
- 保持画面连贯性和节奏感，利用长短镜头交替制造节奏
- 确保视觉冲击力和电影感

【veo_prompt必须包含以下元素】
1. 运镜指令：推镜头/拉镜头/环绕镜头/跟随镜头/升降镜头
2. 光影细节：体积光/丁达尔效应/边缘光/戏剧性光影/色温对比
3. 材质质感：皮肤质感/服装材质/环境质感/特效质感
4. 画面构成：人物状态、表情、服装、环境

【visual.description要求】
- 用箭头→描述动作过程
- 描述画面中的动态变化

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


# ==================== 故事节拍 API ====================

@short_drama_api.route('/story-beats/generate', methods=['POST'])
def generate_story_beats():
    """
    生成故事节拍 (Step 3)
    根据集数内容生成叙事节拍框架
    """
    try:
        data = request.get_json()
        project_id = data.get('projectId')
        episode_id = data.get('episodeId')

        if not project_id:
            return jsonify({'success': False, 'message': '缺少项目ID'}), 400

        # 获取项目信息
        project_file = None
        for project_dir in VIDEO_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                pf = project_dir / '项目信息.json'
                if pf.exists():
                    try:
                        with open(pf, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)
                        if project_data.get('id') == project_id:
                            project_file = pf
                            break
                    except:
                        continue

        if not project_file:
            return jsonify({'success': False, 'message': '项目不存在'}), 404

        # 读取项目数据
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        # 获取集数信息
        episodes = project_data.get('episodes', [])
        if not episodes:
            return jsonify({'success': False, 'message': '项目没有集数'}), 400

        # 使用第一个集数
        episode = episodes[0] if isinstance(episodes, list) else episodes
        episode_title = episode.get('title', '') if isinstance(episode, dict) else str(episode)
        episode_content = episode.get('content', '') if isinstance(episode, dict) else ''

        # 获取角色信息
        characters = project_data.get('characters', [])

        # 调用AI生成故事节拍
        logger.info(f"[故事节拍] 开始生成: {episode_title}")

        if api_client:
            try:
                story_beats = _generate_story_beats_with_ai(
                    episode_title=episode_title,
                    episode_content=episode_content,
                    characters=characters,
                    total_duration=80  # 默认80秒
                )
            except Exception as e:
                logger.error(f"[故事节拍] AI生成失败: {e}")
                # 使用默认数据
                story_beats = _get_default_story_beats()
        else:
            # 没有AI客户端，使用默认数据
            story_beats = _get_default_story_beats()

        # 保存到项目数据
        project_data['storyBeats'] = story_beats
        project_data['updated_at'] = datetime.now().isoformat()

        logger.info(f"[故事节拍] 正在保存到: {project_file}")
        logger.info(f"[故事节拍] storyBeats scenes: {len(story_beats.get('scenes', []))}")

        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        # 验证保存是否成功
        with open(project_file, 'r', encoding='utf-8') as f:
            verify_data = json.load(f)
        logger.info(f"[故事节拍] 验证保存: storyBeats exists = {'storyBeats' in verify_data}")
        if 'storyBeats' in verify_data:
            logger.info(f"[故事节拍] 验证保存: scenes count = {len(verify_data['storyBeats'].get('scenes', []))}")

        logger.info(f"[故事节拍] 生成成功: {len(story_beats.get('scenes', []))} 场景")

        return jsonify({
            'success': True,
            'storyBeats': story_beats
        })

    except Exception as e:
        logger.error(f"[故事节拍] 生成失败: {e}")
        return jsonify({
            'success': False,
            'message': f'生成失败: {str(e)}'
        }), 500


def _generate_story_beats_with_ai(episode_title, episode_content, characters, total_duration=80):
    """
    使用AI生成故事节拍
    """
    # 构建Prompt
    characters_str = "\n".join([
        f"- {c.get('name', '')}: {c.get('identity', '')}, {c.get('traits', '')}"
        for c in characters
    ]) if characters else "- 未设置角色"

    prompt = f"""你是一个专业的短剧编剧。请根据以下集数内容，生成{total_duration}秒的叙事节拍(Story Beats)。

## 输入信息
集数标题：{episode_title}
集数内容：{episode_content[:2000] if episode_content else '（暂无详细内容，请根据标题生成）'}

角色设定：
{characters_str}

总时长要求：{total_duration}秒

## 输出要求

1. **三幕结构分配**
   - 第一幕「建立」(0-30%)：建立场景、人物、核心矛盾
   - 第二幕「对抗」(30-70%)：冲突升级、内心挣扎
   - 第三幕「高潮」(70-100%)：决战时刻、人物觉醒

2. **每个场景包含**
   - sceneNumber: 场景序号
   - sceneTitleCn/En: 中英文标题
   - storyBeatCn/En: 叙事目的
   - durationSeconds: 时长(秒)
   - emotionalArc: 情绪曲线（如：绝决→紧张→希望）
   - dialogues: 对白列表

3. **对白设计**
   - 每个场景至少1句对白
   - 包含speaker, linesCn, linesEn, toneCn, toneEn

只输出JSON格式，不要解释。
"""

    try:
        # 调用AI
        response = api_client.call_api(
            system_prompt="你是一个专业的短剧编剧，擅长设计故事节拍。请严格按照要求的JSON格式输出。",
            user_prompt=prompt,
            temperature=0.7,
            purpose="故事节拍生成"
        )

        # 解析JSON
        content = response.get('content', '') if isinstance(response, dict) else str(response)

        # 提取JSON部分
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            story_beats = json.loads(json_match.group())
        else:
            story_beats = json.loads(content)

        # 验证格式 - 处理 'beats'、'acts' 或 'scenes' 字段
        if 'scenes' not in story_beats:
            # 如果存在 'beats' 字段，将其重命名为 'scenes'
            if 'beats' in story_beats and isinstance(story_beats['beats'], list):
                story_beats['scenes'] = story_beats.pop('beats')
            # 如果存在 'acts' 字段，提取所有 acts 中的 scenes 合并
            elif 'acts' in story_beats and isinstance(story_beats['acts'], list):
                all_scenes = []
                for act in story_beats['acts']:
                    if 'scenes' in act and isinstance(act['scenes'], list):
                        all_scenes.extend(act['scenes'])
                story_beats['scenes'] = all_scenes
            elif isinstance(story_beats, list):
                story_beats = {'scenes': story_beats}
            else:
                story_beats = {'scenes': []}

        return story_beats

    except Exception as e:
        logger.error(f"AI生成故事节拍失败: {e}")
        return _get_default_story_beats()


def _get_default_story_beats():
    """获取默认故事节拍"""
    return {
        'scenes': [
            {
                'sceneNumber': 1,
                'sceneTitleCn': '开场',
                'sceneTitleEn': 'Opening',
                'storyBeatCn': '建立场景，展示主角状态',
                'storyBeatEn': 'Establish scene, show protagonist status',
                'durationSeconds': 8,
                'emotionalArc': '平静→紧张',
                'dialogues': [
                    {
                        'speaker': '主角',
                        'linesCn': '这是一个开始...',
                        'linesEn': 'This is a beginning...',
                        'toneCn': '内心独白',
                        'toneEn': 'Inner monologue'
                    }
                ]
            },
            {
                'sceneNumber': 2,
                'sceneTitleCn': '冲突',
                'sceneTitleEn': 'Conflict',
                'storyBeatCn': '冲突出现，推动剧情',
                'storyBeatEn': 'Conflict emerges, drive plot forward',
                'durationSeconds': 8,
                'emotionalArc': '紧张→焦虑',
                'dialogues': [
                    {
                        'speaker': '反派',
                        'linesCn': '你以为你能成功吗？',
                        'linesEn': 'Do you think you can succeed?',
                        'toneCn': '挑衅',
                        'toneEn': 'Provocative'
                    }
                ]
            },
            {
                'sceneNumber': 3,
                'sceneTitleCn': '高潮',
                'sceneTitleEn': 'Climax',
                'storyBeatCn': '主角觉醒，展现力量',
                'storyBeatEn': 'Protagonist awakens, shows power',
                'durationSeconds': 8,
                'emotionalArc': '绝望→希望',
                'dialogues': [
                    {
                        'speaker': '主角',
                        'linesCn': '我不会放弃！',
                        'linesEn': 'I will not give up!',
                        'toneCn': '坚定',
                        'toneEn': 'Determined'
                    }
                ]
            }
        ]
    }


@short_drama_api.route('/story-beats/<project_id>', methods=['GET'])
def get_story_beats(project_id):
    """
    获取项目的故事节拍
    """
    try:
        # 查找项目
        project_file = None
        for project_dir in VIDEO_PROJECTS_DIR.iterdir():
            if project_dir.is_dir():
                pf = project_dir / '项目信息.json'
                if pf.exists():
                    try:
                        with open(pf, 'r', encoding='utf-8') as f:
                            project_data = json.load(f)
                        if project_data.get('id') == project_id:
                            project_file = pf
                            break
                    except:
                        continue

        if not project_file:
            return jsonify({'success': False, 'message': '项目不存在'}), 404

        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)

        story_beats = project_data.get('storyBeats')

        if not story_beats:
            return jsonify({
                'success': True,
                'storyBeats': None,
                'message': '暂无故事节拍数据'
            })

        return jsonify({
            'success': True,
            'storyBeats': story_beats
        })

    except Exception as e:
        logger.error(f"[获取故事节拍] 失败: {e}")
        return jsonify({
            'success': False,
            'message': f'获取失败: {str(e)}'
        }), 500


@short_drama_api.route('/storyboard/generate-from-beats', methods=['POST'])
def generate_storyboard_from_beats():
    """
    从故事节拍生成分镜头 (Step 4)
    使用 VeOPromptService 生成三种模式的提示词
    """
    try:
        data = request.get_json()
        project_id = data.get('projectId')
        story_beats = data.get('storyBeats')
        has_reference_image = data.get('hasReferenceImage', False)
        has_first_last_frame = data.get('hasFirstLastFrame', False)
        
        if not project_id:
            return jsonify({'success': False, 'message': '缺少项目ID'}), 400
        
        if not story_beats:
            return jsonify({'success': False, 'message': '缺少故事节拍数据'}), 400
        
        logger.info(f'🎬 [生成分镜] 项目: {project_id}')
        logger.info(f'   参考图: {has_reference_image}, 首尾帧: {has_first_last_frame}')
        
        # 查找项目
        project_file = None
        project_dir = None
        for pd in VIDEO_PROJECTS_DIR.iterdir():
            if pd.is_dir():
                pf = pd / '项目信息.json'
                if pf.exists():
                    try:
                        with open(pf, 'r', encoding='utf-8') as f:
                            pd_data = json.load(f)
                        if pd_data.get('id') == project_id:
                            project_file = pf
                            project_dir = pd
                            break
                    except:
                        continue
        
        if not project_file or not project_dir:
            return jsonify({'success': False, 'message': '项目不存在'}), 404
        
        # 加载项目数据
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        
        # 获取角色列表
        characters = project_data.get('characters', [])
        
        # 🔥 使用 VeOPromptService 生成三种模式的提示词
        from web.services.veo_prompt_service import generate_veo_prompts_for_scenes

        shots = generate_veo_prompts_for_scenes(
            story_beats=story_beats,
            characters=characters,
            has_reference_image=has_reference_image,
            has_first_last_frame=has_first_last_frame
        )

        # 🔥 不再自动翻译，翻译功能改为 UI 手动触发
        logger.info(f'✅ [生成分镜] 生成 {len(shots)} 个镜头（未翻译，请使用批量翻译功能）')
        
        # 保存 shots 到项目文件
        project_data['shots'] = shots
        project_data['updatedAt'] = datetime.now().isoformat()
        
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'成功生成 {len(shots)} 个镜头',
            'shots': shots
        })
        
    except Exception as e:
        logger.error(f'❌ [生成分镜] 失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'生成分镜失败: {str(e)}'
        }), 500


def generate_shots_from_storybeats(title: str, story_beats: dict, style: str, shot_duration: int = 8) -> list:
    """
    基于故事节拍生成专业分镜头（全英文版本）
    
    Args:
        title: 剧集标题
        story_beats: 故事节拍数据
        style: 风格
        shot_duration: 每个镜头时长
        
    Returns:
        全英文的分镜头列表
    """
    try:
        scenes = story_beats.get('scenes', [])
        if not scenes:
            logger.warning('故事节拍没有场景数据，返回空分镜头')
            return []
        
        # 构建提示词
        system_prompt = f"""You are a professional cinematographer specializing in AI video generation prompts.

Based on the provided story beats, generate professional video shot descriptions in English.

Each shot must include:
1. shot_number: Sequential number
2. shot_type: Shot type (Close-up/Medium shot/Wide shot/Establishing shot/POV)
2. veo_prompt: Detailed English video prompt for AI generation, including:
   - Camera movement (push in, pull out, orbit, follow, crane up/down)
   - Lighting details (volumetric lighting, god rays, rim light, dramatic lighting)
   - Material textures (skin details, fabric, environment, special effects)
   - Cinematic composition
3. visual_description: Dynamic action sequence using arrows (→)
4. dialogue: 
   - speaker: Character name or "None"
   - lines: English dialogue lines (appropriate for shot duration)
   - lines_cn: Chinese translation
   - tone: English tone description
   - tone_cn: Chinese tone description
   - audio_note: Sound effect description in English
   - audio_note_cn: Sound effect description in Chinese
5. duration_seconds: Shot duration

Style: {style}

Output JSON format:
{{
    "shots": [
        {{
            "shot_number": 1,
            "shot_type": "Close-up",
            "veo_prompt": "Detailed English video generation prompt...",
            "visual_description": "Action A → Action B → Action C",
            "dialogue": {{
                "speaker": "Character Name",
                "lines": "English dialogue",
                "lines_cn": "中文台词",
                "tone": "determined, tense",
                "tone_cn": "决绝、紧张",
                "audio_note": "Sound description",
                "audio_note_cn": "音效描述"
            }},
            "duration_seconds": 8
        }}
    ]
}}"""

        # 构建故事节拍摘要
        scenes_summary = []
        for i, scene in enumerate(scenes, 1):
            scene_title = scene.get('sceneTitleEn', scene.get('sceneTitleCn', f'Scene {i}'))
            story_beat = scene.get('storyBeatEn', scene.get('storyBeatCn', ''))
            duration = scene.get('durationSeconds', shot_duration)
            dialogues = scene.get('dialogues', [])
            
            dialogue_summary = []
            for dlg in dialogues:
                speaker = dlg.get('speaker', 'Unknown')
                lines = dlg.get('linesEn', dlg.get('lines', ''))
                tone = dlg.get('toneEn', dlg.get('tone', ''))
                dialogue_summary.append(f"{speaker}: {lines} (Tone: {tone})")
            
            scenes_summary.append(f"""Scene {i}: {scene_title}
Duration: {duration}s
Story Beat: {story_beat}
Dialogues:
{chr(10).join(dialogue_summary) if dialogue_summary else 'No dialogue'}
""")

        user_prompt = f"""Generate professional video shots based on these story beats:

Title: {title}
Style: {style}

Story Beats:
{chr(10).join(scenes_summary)}

Requirements:
1. Create {len(scenes)} shots, one per scene
2. Each shot should have professional cinematography language
3. veo_prompt must include camera movement, lighting, and textures
4. Dialogue should be natural and fit the shot duration
5. Output valid JSON only

Generate shots now:"""

        logger.info(f'🎥 [分镜头生成] 调用AI生成全英文分镜头...')
        
        if not api_client:
            logger.error('AI客户端未初始化')
            return _get_default_shots_from_storybeats(scenes, shot_duration)
        
        response = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            purpose="创意分镜头生成-英文"
        )
        
        if not response:
            logger.error('AI返回空响应')
            return _get_default_shots_from_storybeats(scenes, shot_duration)
        
        # 解析JSON
        try:
            import re
            json_text = response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            elif json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            # 清理JSON
            json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
            
            data = json.loads(json_text)
            shots = data.get('shots', [])
            
            logger.info(f'✅ [分镜头生成] 成功生成 {len(shots)} 个全英文镜头')
            return shots
            
        except json.JSONDecodeError as e:
            logger.error(f'JSON解析失败: {e}')
            return _get_default_shots_from_storybeats(scenes, shot_duration)
            
    except Exception as e:
        logger.error(f'生成分镜头失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return _get_default_shots_from_storybeats(story_beats.get('scenes', []), shot_duration)


def _get_default_shots_from_storybeats(scenes: list, shot_duration: int) -> list:
    """默认分镜头生成（AI失败时的充底方案）"""
    shots = []
    for i, scene in enumerate(scenes, 1):
        story_beat = scene.get('storyBeatEn', scene.get('storyBeatCn', f'Scene {i}'))
        dialogues = scene.get('dialogues', [])
        
        if dialogues:
            dlg = dialogues[0]
            speaker = dlg.get('speaker', 'None')
            lines = dlg.get('linesEn', dlg.get('lines', ''))
            lines_cn = dlg.get('linesCn', lines)
            tone = dlg.get('toneEn', dlg.get('tone', ''))
            tone_cn = dlg.get('toneCn', tone)
        else:
            speaker = 'None'
            lines = ''
            lines_cn = ''
            tone = ''
            tone_cn = ''
        
        shots.append({
            'shot_number': i,
            'shot_type': 'Medium shot',
            'veo_prompt': f'{story_beat}. Cinematic composition, dramatic lighting.',
            'visual_description': f'Scene {i} unfolds',
            'dialogue': {
                'speaker': speaker,
                'lines': lines,
                'lines_cn': lines_cn,
                'tone': tone,
                'tone_cn': tone_cn,
                'audio_note': 'Ambient sound',
                'audio_note_cn': '环境音'
            },
            'duration_seconds': scene.get('durationSeconds', shot_duration)
        })
    
    logger.warning(f'使用默认分镜头: {len(shots)} 个')
    return shots


def translate_shots_to_chinese(shots: list) -> list:
    """
    将全英文分镜头翻译成中文，返回完全独立的中文版本
    
    翻译字段包括：
    - veo_prompt 相关字段
    - visual_description 相关字段  
    - dialogue 内的台词、语气、音效
    - image_prompt 相关字段
    - scene_title
    """
    if not shots:
        return shots
    
    # 创建深拷贝作为中文版本基础
    import copy
    shots_cn = copy.deepcopy(shots)
    
    try:
        logger.info(f'🌐 [翻译] 开始翻译 {len(shots_cn)} 个镜头...')
        
        if not api_client:
            logger.warning('AI客户端未初始化，返回原始数据')
            return shots_cn
        
        # 逐个翻译每个镜头
        for i, shot in enumerate(shots_cn):
            try:
                # 1. 翻译 veo_prompt 字段
                veo_fields = ['veo_prompt_standard', 'veo_prompt_reference', 'veo_prompt_frames']
                for field in veo_fields:
                    if field in shot and shot[field]:
                        shot[field] = _translate_text_to_chinese(shot[field])
                
                # 2. 翻译 visual_description 字段
                visual_fields = ['visual_description_standard', 'visual_description_reference', 'visual_description_frames']
                for field in visual_fields:
                    if field in shot and shot[field]:
                        shot[field] = _translate_text_to_chinese(shot[field])
                
                # 3. 翻译 image_prompt 字段
                if 'image_prompt' in shot and shot['image_prompt']:
                    shot['image_prompt'] = _translate_text_to_chinese(shot['image_prompt'])
                
                # 翻译 image_prompts 内的字段
                if 'image_prompts' in shot:
                    for key in shot['image_prompts']:
                        if shot['image_prompts'][key]:
                            shot['image_prompts'][key] = _translate_text_to_chinese(shot['image_prompts'][key])
                
                # 4. 翻译 dialogue 内的字段
                if 'dialogue' in shot:
                    dialogue = shot['dialogue']
                    # 台词：lines_en -> lines
                    if 'lines_en' in dialogue and dialogue['lines_en']:
                        dialogue['lines'] = _translate_text_to_chinese(dialogue['lines_en'])
                    # 语气：tone_en -> tone
                    if 'tone_en' in dialogue and dialogue['tone_en']:
                        dialogue['tone'] = _translate_text_to_chinese(dialogue['tone_en'])
                    # 音效：audio_note_en -> audio_note
                    if 'audio_note_en' in dialogue and dialogue['audio_note_en']:
                        dialogue['audio_note'] = _translate_text_to_chinese(dialogue['audio_note_en'])
                
                # 5. 翻译 scene_title
                if 'scene_title' in shot and shot['scene_title']:
                    shot['scene_title'] = _translate_text_to_chinese(shot['scene_title'])
                
                logger.info(f'   ✅ 镜头 {i+1} 翻译完成')
                
            except Exception as e:
                logger.warning(f'   ⚠️ 镜头 {i+1} 翻译失败: {e}')
                continue
        
        logger.info(f'✅ [翻译] 完成 {len(shots_cn)} 个镜头翻译')
        return shots_cn
        
    except Exception as e:
        logger.error(f'翻译分镜头失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return shots_cn


def _translate_text_to_chinese(text: str) -> str:
    """
    使用AI翻译单个文本到中文
    """
    if not text or not api_client:
        return text
    
    try:
        system_prompt = """你是一个专业的视频提示词翻译专家。
请将以下英文视频提示词翻译成流畅的中文，保持专业术语的准确性。
注意：
- 保持技术术语的准确性（如 cinematic, photorealistic, 8k 等可以保留或翻译为"电影级"、"写实风格"、"8K超清"）
- 翻译要自然流畅，符合中文表达习惯
- 只返回翻译结果，不要添加任何解释
- 保持原有的标点符号和格式"""

        response = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=f"请翻译以下内容：\n\n{text}",
            temperature=0.3,
            purpose="文本翻译-中文"
        )
        
        if response:
            return response.strip()
        return text
        
    except Exception as e:
        logger.warning(f'翻译失败: {e}')
        return text


# ==================== 翻译 API ====================

@short_drama_api.route('/translate/to-chinese', methods=['POST'])
def translate_to_chinese():
    """将英文提示词翻译成中文"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({
                'success': False,
                'error': '缺少文本'
            }), 400

        if not api_client:
            return jsonify({
                'success': False,
                'error': 'AI客户端未初始化'
            }), 500

        # 调用AI翻译
        system_prompt = """你是一个专业的视频提示词翻译专家。
请将英文视频生成提示词翻译成流畅的中文，保持专业术语的准确性。
注意：
- 保持技术术语的准确性（如 cinematic, photorealistic, 8k 等可以保留或翻译为"电影级"、"写实风格"、"8K超清"）
- 翻译要自然流畅，符合中文表达习惯
- 保持原文的结构和重点
- 只返回翻译结果，不要添加任何解释"""

        translated_text = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=f"请翻译以下视频提示词：\n\n{text}",
            json_mode=False
        )

        if not translated_text:
            return jsonify({
                'success': False,
                'error': '翻译失败'
            }), 500

        return jsonify({
            'success': True,
            'translated_text': translated_text.strip()
        }), 200

    except Exception as e:
        logger.error(f'翻译失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/translate/to-english', methods=['POST'])
def translate_to_english():
    """将中文提示词翻译成英文"""
    try:
        data = request.get_json()
        text = data.get('text', '')

        if not text:
            return jsonify({
                'success': False,
                'error': '缺少文本'
            }), 400

        if not api_client:
            return jsonify({
                'success': False,
                'error': 'AI客户端未初始化'
            }), 500

        # 调用AI翻译
        system_prompt = """你是一个专业的视频提示词翻译专家。
请将中文视频生成提示词翻译成专业的英文，适合用于AI视频生成。
注意：
- 使用专业的视频生成术语（如 cinematic, photorealistic, 8k, medium shot, soft lighting 等）
- 翻译要准确，符合英文表达习惯
- 保持原文的结构和重点
- 只返回翻译结果，不要添加任何解释"""

        translated_text = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=f"请翻译以下视频提示词：\n\n{text}",
            json_mode=False
        )

        if not translated_text:
            return jsonify({
                'success': False,
                'error': '翻译失败'
            }), 500

        return jsonify({
            'success': True,
            'translated_text': translated_text.strip()
        }), 200

    except Exception as e:
        logger.error(f'翻译失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots/translate-all', methods=['POST'])
def translate_all_shots():
    """
    批量翻译所有镜头的提示词
    一次性翻译整个文件的所有英文提示词为中文
    """
    try:
        data = request.get_json()
        novel_title = data.get('novel')
        episode_name = data.get('episode')
        
        if not novel_title or not episode_name:
            return jsonify({
                'success': False,
                'error': '缺少小说标题或集数名称'
            }), 400
        
        # 构建 shots_v2.json 文件路径
        shots_file = VIDEO_PROJECTS_DIR / novel_title / episode_name / 'shots_v2.json'
        
        if not shots_file.exists():
            return jsonify({
                'success': False,
                'error': '分镜文件不存在'
            }), 404
        
        # 读取文件
        with open(shots_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        shots = data.get('shots', [])
        if not shots:
            return jsonify({
                'success': False,
                'error': '没有可翻译的镜头'
            }), 400
        
        if not api_client:
            return jsonify({
                'success': False,
                'error': 'AI客户端未初始化'
            }), 500
        
        logger.info(f'🌐 [批量翻译] 开始翻译 {len(shots)} 个镜头...')
        
        translated_count = 0
        failed_count = 0
        
        for shot in shots:
            try:
                # 翻译三种模式的英文提示词
                if shot.get('veo_prompt_standard') and not shot.get('veo_prompt_standard_cn'):
                    shot['veo_prompt_standard_cn'] = _translate_to_chinese_sync(shot['veo_prompt_standard'])
                
                if shot.get('veo_prompt_reference') and not shot.get('veo_prompt_reference_cn'):
                    shot['veo_prompt_reference_cn'] = _translate_to_chinese_sync(shot['veo_prompt_reference'])
                
                if shot.get('veo_prompt_frames') and not shot.get('veo_prompt_frames_cn'):
                    shot['veo_prompt_frames_cn'] = _translate_to_chinese_sync(shot['veo_prompt_frames'])
                
                translated_count += 1
                logger.info(f'   ✅ 镜头 {shot.get("shot_number", "?")} 翻译完成')
            except Exception as e:
                failed_count += 1
                logger.warning(f'   ⚠️ 镜头 {shot.get("shot_number", "?")} 翻译失败: {e}')
                continue
        
        # 保存翻译后的数据
        data['shots'] = shots
        data['updatedAt'] = datetime.now().isoformat()
        
        with open(shots_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f'✅ [批量翻译] 完成: {translated_count} 成功, {failed_count} 失败')
        
        return jsonify({
            'success': True,
            'message': f'翻译完成: {translated_count} 个镜头成功, {failed_count} 个失败',
            'translatedCount': translated_count,
            'failedCount': failed_count,
            'shots': shots
        })
        
    except Exception as e:
        logger.error(f'❌ [批量翻译] 失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': f'批量翻译失败: {str(e)}'
        }), 500


# ==================== 分镜头管理 API ====================

@short_drama_api.route('/shots-v2', methods=['GET'])
def get_shots_v2():
    """获取优化格式的分镜头数据（数据流A）"""
    try:
        novel_title = request.args.get('novel')
        episode_name = request.args.get('episode')

        if not novel_title or not episode_name:
            return jsonify({
                'success': False,
                'error': '缺少参数'
            }), 400

        # 构建 shots_v2.json 文件路径
        shots_file = VIDEO_PROJECTS_DIR / novel_title / episode_name / 'shots_v2.json'

        if not shots_file.exists():
            return jsonify({
                'success': True,
                'shots': []
            })

        # 读取文件
        with open(shots_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        shots = data.get('shots', [])
        logger.info(f'✅ [shots-v2] 加载了 {len(shots)} 个镜头')

        return jsonify({
            'success': True,
            'shots': shots
        }), 200

    except Exception as e:
        logger.error(f'获取 shots_v2 失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots-v2', methods=['POST'])
def save_shots_v2():
    """保存优化格式的分镜头数据（数据流A持久化）"""
    try:
        data = request.get_json()
        novel_title = data.get('novel')
        episode_name = data.get('episode')
        shots = data.get('shots', [])

        if not novel_title or not episode_name:
            return jsonify({
                'success': False,
                'error': '缺少参数'
            }), 400

        # 确保目录存在
        episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_name
        episode_dir.mkdir(parents=True, exist_ok=True)

        # 构建文件路径
        shots_file = episode_dir / 'shots_v2.json'

        # 保存数据
        save_data = {
            'version': '2.0',
            'created_at': datetime.now().isoformat(),
            'shots': shots
        }

        with open(shots_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ [shots-v2] 保存了 {len(shots)} 个镜头到 {shots_file}')

        return jsonify({
            'success': True,
            'message': f'成功保存 {len(shots)} 个镜头'
        }), 200

    except Exception as e:
        logger.error(f'保存 shots_v2 失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
                'storyboards': []  # 返回空数组而不是空字典
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
        
        # 获取请求体中的生成参数
        prompt = data.get('prompt', '')  # 前端传入的提示词（备用）
        preferred_mode = data.get('preferred_mode', 'standard')  # 🔥 用户选择的模式
        image_urls = data.get('image_urls', [])
        orientation = data.get('orientation', 'portrait')
        duration = data.get('duration', 8)  # 🔥 VeO API 只支持 8 秒
        
        logger.info(f'🎬 生成镜头视频: shot_id={shot_id}, project_id={project_id}, mode={preferred_mode}')
        
        # 🔥 加载项目配置和shot数据，获取对应模式的提示词
        use_first_last_frame = False
        first_frame = None
        last_frame = None
        final_prompt = prompt  # 默认使用前端传入的提示词
        
        if project_id:
            try:
                project = ShortDramaProject.load(project_id)
                if project:
                    settings = project.settings or {}
                    use_first_last_frame = settings.get('use_first_last_frame', True)  # 默认开启
                    logger.info(f'🎬 项目首尾帧模式: {use_first_last_frame}')
                    
                    # 🔥 根据用户选择的模式获取对应的提示词
                    shots = project.data.get('shots', [])
                    shot = None
                    for s in shots:
                        if s.get('id') == shot_id:
                            shot = s
                            break
                    
                    if shot:
                        # 根据preferred_mode选择对应的提示词
                        if preferred_mode == 'reference' and shot.get('veo_prompt_reference'):
                            final_prompt = shot['veo_prompt_reference']
                            logger.info(f'🎬 使用参考图模式提示词')
                        elif preferred_mode == 'frames' and shot.get('veo_prompt_frames'):
                            final_prompt = shot['veo_prompt_frames']
                            logger.info(f'🎬 使用首尾帧模式提示词')
                        elif shot.get('veo_prompt_standard'):
                            final_prompt = shot['veo_prompt_standard']
                            logger.info(f'🎬 使用标准模式提示词')
                        else:
                            # 兼容旧数据
                            final_prompt = shot.get('veo_prompt', prompt)
                            logger.info(f'🎬 使用备用提示词')
                    
                    # 🔥 如果启用首尾帧且有多张参考图，分别设置首帧和尾帧
                    if use_first_last_frame and len(image_urls) >= 2:
                        first_frame = image_urls[0]  # 第一张作为首帧
                        last_frame = image_urls[-1]  # 最后一张作为尾帧
                        logger.info(f'🎬 使用首尾帧: 首帧={first_frame[:50]}..., 尾帧={last_frame[:50]}...')
                    elif use_first_last_frame and len(image_urls) == 1:
                        # 只有一张图时，同时作为首帧和尾帧（静态效果）
                        first_frame = image_urls[0]
                        last_frame = image_urls[0]
                        logger.info(f'🎬 单图首尾帧模式: {first_frame[:50]}...')
            except Exception as e:
                logger.warning(f'⚠️ 加载项目配置失败: {e}')
        
        # 导入 VeOVideoManager
        from src.managers.VeOVideoManager import get_veo_video_manager
        from src.models.veo_models import VeOCreateVideoRequest, VeOVideoRequest
        
        # 获取 VeO 管理器实例
        veo_manager = get_veo_video_manager()
        
        # 🔥 创建原生格式请求（支持首尾帧模式）
        if use_first_last_frame and (first_frame or last_frame):
            # 首尾帧模式
            native_request = VeOCreateVideoRequest(
                use_first_last_frame=True,
                first_frame=first_frame,
                last_frame=last_frame,
                model="veo_3_1-fast",
                orientation=orientation,
                prompt=final_prompt,  # 🔥 使用选择的提示词
                size="large",
                duration=duration,
                watermark=False,
                private=True,
                metadata={
                    'shot_id': shot_id,
                    'project_id': project_id,
                    'novel_title': data.get('novel_title', ''),
                    'episode_title': data.get('episode_title', ''),
                    'event_name': data.get('event_name', ''),
                    'scene_number': data.get('scene_number', 1),
                    'shot_number': data.get('shot_number', '1'),
                    'shot_type': data.get('shot_type', 'shot'),
                    'use_first_last_frame': True,
                    'preferred_mode': preferred_mode  # 🔥 记录选择的模式
                }
            )
            logger.info('🎬 创建首尾帧模式请求')
        else:
            # 普通参考图模式
            native_request = VeOCreateVideoRequest(
                images=image_urls,
                model="veo_3_1-fast",
                orientation=orientation,
                prompt=final_prompt,  # 🔥 使用选择的提示词
                size="large",
                duration=duration,
                watermark=False,
                private=True,
                metadata={
                    'shot_id': shot_id,
                    'project_id': project_id,
                    'novel_title': data.get('novel_title', ''),
                    'episode_title': data.get('episode_title', ''),
                    'event_name': data.get('event_name', ''),
                    'scene_number': data.get('scene_number', 1),
                    'shot_number': data.get('shot_number', '1'),
                    'shot_type': data.get('shot_type', 'shot'),
                    'preferred_mode': preferred_mode  # 🔥 记录选择的模式
                }
            )
            logger.info('🎬 创建普通参考图模式请求')
        
        # 创建 OpenAI 格式请求（用于兼容性）
        openai_request = VeOVideoRequest(
            model="veo_3_1-fast",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": final_prompt}  # 🔥 使用选择的提示词
                ]
            }]
        )
        
        # 提交生成任务
        response = veo_manager.create_generation(openai_request, native_request)
        
        # 从响应中获取任务ID
        task_id = response.id
        
        logger.info(f'✅ 视频生成任务已提交: task_id={task_id}')

        return jsonify({
            'success': True,
            'message': '视频生成任务已提交',
            'task_id': task_id
        }), 202
        
    except Exception as e:
        logger.error(f'生成视频失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots/<shot_id>/status', methods=['GET'])
def get_shot_status(shot_id):
    """获取镜头生成状态"""
    try:
        # 从 VeOVideoManager 查询任务状态
        from src.managers.VeOVideoManager import get_veo_video_manager
        
        # 获取 VeO 任务管理器实例（单例）
        veo_manager = get_veo_video_manager()
        
        # 查找与该镜头相关的任务
        # 任务ID格式为 veo_{uuid}，我们需要查找包含 shot_id 的任务
        task = None
        for task_id, t in veo_manager.tasks.items():
            # 检查任务元数据中的 shot_id
            if t.metadata.get('shot_id') == shot_id:
                task = t
                break
            # 或者检查任务ID是否包含 shot_id（备用匹配）
            if shot_id in task_id:
                task = t
                break
        
        if task:
            # 返回任务的实际状态
            status = task.status.value if hasattr(task.status, 'value') else str(task.status)
            response = {
                'success': True,
                'status': status,
                'progress': task._current_progress if hasattr(task, '_current_progress') else 0,
                'stage': task._current_stage if hasattr(task, '_current_stage') else ''
            }
            
            # 如果任务失败，包含错误信息
            if status == 'failed' and task.error:
                response['error'] = task.error
                logger.warning(f'❌ 镜头 {shot_id} 生成失败: {task.error}')
            
            return jsonify(response), 200
        else:
            # 没有找到任务，返回待生成状态
            return jsonify({
                'success': True,
                'status': 'pending',
                'progress': 0
            }), 200
            
    except Exception as e:
        logger.error(f'获取镜头状态失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
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
    
    # 注册导出功能 API
    try:
        from web.api.export_api import export_api
        app.register_blueprint(export_api)
        logger.info('✅ 导出功能 API 已注册')
    except Exception as e:
        logger.warning(f'⚠️ 导出功能 API 注册失败: {e}')
    
    logger.info('✅ 短剧工作台 API 已注册')
