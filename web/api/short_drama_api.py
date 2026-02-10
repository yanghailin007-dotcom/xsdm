# -*- coding: utf-8 -*-
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
from urllib.parse import unquote, quote

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
    """同步翻译英文到中文(内部使用)"""
    try:
        if not api_client:
            logger.warning('AI客户端未初始化，跳过翻译')
            return text

        system_prompt = """你是一个专业的视频提示词翻译专家。
请将英文视频生成提示词翻译成流畅的中文，保持专业术语的准确性。
注意：
- 保持技术术语的准确性(如 cinematic, photorealistic, 8k 等可以保留或翻译为"电影级"、"写实风格"、"8K超清")
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


def _generate_bilingual_character_description(
    char_id: str,
    name: str,
    raw_description: str,
    raw_clothing: str,
    raw_expression: str
) -> dict:
    """
    生成标准中英双语角色描述
    
    Returns:
        {
            'character_id': '角色ID',
            'chinese': '中文描述',
            'english': '英文描述(用于AI生成)',
            'tags': ['标签1', '标签2']
        }
    """
    try:
        if not api_client:
            logger.warning('AI客户端未初始化，使用简单描述')
            return {
                'character_id': char_id,
                'chinese': f'{name}，{raw_description}，穿着{raw_clothing}，{raw_expression}',
                'english': f'{name}, {raw_description}, wearing {raw_clothing}, {raw_expression} expression',
                'tags': []
            }
        
        system_prompt = """You are a professional character description engineer.
Based on the provided character information, generate a STANDARDIZED bilingual character description.

OUTPUT FORMAT (JSON):
{
    "chinese": "完整的中文角色描述，包含外貌、服装、气质",
    "english": "Complete English character description for AI image generation, include appearance, clothing, personality",
    "tags": ["tag1", "tag2", "tag3"]
}

GUIDELINES:
- Chinese: Natural, descriptive, suitable for display
- English: Detailed, vivid adjectives, suitable for Stable Diffusion/Midjourney prompts
- Include age, gender, distinctive features, clothing details
- Tags should be key visual identifiers
- Character name should appear in both languages"""

        user_prompt = f"""Generate bilingual description for character:

Character ID: {char_id}
Name: {name}
Raw Description: {raw_description}
Clothing: {raw_clothing}
Expression: {raw_expression}

Provide JSON output with chinese, english, and tags."""

        response = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True
        )
        
        if response:
            import json
            try:
                result = json.loads(response)
                result['character_id'] = char_id
                return result
            except json.JSONDecodeError:
                # 如果不是JSON，手动构建
                return {
                    'character_id': char_id,
                    'chinese': f'{name}，{raw_description}',
                    'english': response.strip(),
                    'tags': [name]
                }
        
        # 回退
        return {
            'character_id': char_id,
            'chinese': f'{name}，{raw_description}',
            'english': f'{name}, {raw_description}',
            'tags': [name]
        }
        
    except Exception as e:
        logger.error(f'生成双语描述失败: {e}')
        return {
            'character_id': char_id,
            'chinese': f'{name}，{raw_description}',
            'english': f'{name}, {raw_description}',
            'tags': []
        }


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
        self.visualAssets = {   # 🔥 视觉资产库
            'characters': {},   # {name: {description, tags, referenceUrl, ...}}
            'scenes': {},       # {name: {description, tags, referenceUrl, ...}}
            'props': {}         # {name: {description, tags, referenceUrl, ...}}
        }
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
            'visualAssets': self.visualAssets,
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
                            project.visualAssets = data.get('visualAssets', {'characters': {}, 'scenes': {}, 'props': {}})
                            project.settings = data.get('settings', project.settings)
                            logger.info(f"[ShortDramaProject.load] 加载后storyBeats: {project.storyBeats is not None}, visualAssets: {len(project.visualAssets.get('characters', {}))}角色")

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
            # 构建episode目录路径
            if isinstance(episode_name, dict):
                # 如果是字典对象，提取 name 或 id 字段作为目录名
                episode_dir_name = episode_name.get('name') or episode_name.get('id') or episode_name.get('title', '')
                episode_dir = project_dir / episode_dir_name
            else:
                episode_dir = project_dir / episode_name
                episode_dir_name = episode_name

            # 🔥 优先检查是否存在 shots_v2_cn.json(创意导入格式)
            shots_v2_cn_file = episode_dir / 'shots_v2_cn.json'
            shots_v2_en_file = episode_dir / 'shots_v2.json'

            if shots_v2_cn_file.exists() and shots_v2_en_file.exists():
                try:
                    # 加载中文版本(用于显示)
                    with open(shots_v2_cn_file, 'r', encoding='utf-8') as f:
                        shots_cn_data = json.load(f)

                    # 加载英文版本(用于AI提示词)
                    with open(shots_v2_en_file, 'r', encoding='utf-8') as f:
                        shots_en_data = json.load(f)

                    shots_cn = shots_cn_data.get('shots', [])
                    shots_en = shots_en_data.get('shots', [])

                    # 创建episode对象
                    episode_obj = {
                        'title': episode_dir_name,
                        'shots': []
                    }

                    # 如果原来是字典对象，保留其他字段
                    if isinstance(episode_name, dict):
                        episode_obj.update(episode_name)
                        episode_obj['shots'] = []  # 清空原有的 shots，使用 shots_v2 的数据

                    # 合并中英文数据
                    for i, (shot_cn, shot_en) in enumerate(zip(shots_cn, shots_en), 1):
                        shot_obj = {
                            'id': f"shot_{i}",
                            'shot_number': shot_cn.get('shot_number', i),
                            'scene_number': 1,
                            'scene_title': shot_cn.get('scene_title', ''),
                            'shot_type': shot_cn.get('shot_type', ''),
                            'duration': shot_cn.get('duration_seconds', 8),
                            # 🔥 英文提示词(用于AI生成)
                            'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                            'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                            'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                            # 🔥 中文描述(用于显示)
                            'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                            'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                            'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                            # 🔥 四种图片提示词(英文，用于AI生成)
                            'image_prompts': shot_en.get('image_prompts', {}),
                            # 🔥 四种图片提示词(中文，用于显示)
                            'image_prompts_cn': shot_cn.get('image_prompts_cn', {}),
                            # 兼容旧模式
                            'image_prompt': shot_cn.get('image_prompt', ''),
                            'image_prompt_en': shot_en.get('image_prompt', ''),
                            'veo_prompt': shot_en.get('veo_prompt_standard', ''),
                            'visual_description': shot_cn.get('visual_description_standard', ''),
                            'preferred_mode': 'standard',
                            'dialogue': shot_cn.get('dialogue', {}),
                            'visual': {},
                            'status': 'pending'
                        }
                        episode_obj['shots'].append(shot_obj)

                    logger.info(f'📋 [Episode] {episode_dir_name}: 从 shots_v2 加载了 {len(episode_obj["shots"])} 个镜头')
                    enriched_episodes.append(episode_obj)
                    continue

                except Exception as e:
                    logger.error(f'加载 shots_v2 文件失败 {episode_dir_name}: {e}')

            # 如果已经是字典对象(有shots)，直接使用
            if isinstance(episode_name, dict):
                enriched_episodes.append(episode_name)
                continue

            # 创建episode对象
            episode_obj = {
                'title': episode_dir_name,
                'shots': []
            }

            storyboard_dir = episode_dir / 'storyboards'

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
        project.visualAssets = data.get('visualAssets', {'characters': {}, 'scenes': {}, 'props': {}})
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

        # 🔥 同步角色到视觉资产库
        if project.characters:
            _sync_characters_to_visual_assets(project)

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


def _sync_characters_to_visual_assets_obj(characters, visual_assets):
    """将角色列表同步到视觉资产字典
    
    Args:
        characters: 角色列表
        visual_assets: 视觉资产字典(将被修改)
    """
    try:
        if not characters:
            return
            
        if 'characters' not in visual_assets:
            visual_assets['characters'] = {}
        
        characters_assets = visual_assets['characters']
        
        for char in characters:
            if isinstance(char, dict):
                char_name = char.get('name')
                if char_name and char_name not in characters_assets:
                    # 提取角色描述
                    description = char.get('living_characteristics', {}).get('physical_presence', '')
                    if not description:
                        description = char.get('initial_state', {}).get('description', '')
                    if not description:
                        description = char.get('appearance', '')
                    if not description:
                        description = char.get('description', '')
                    
                    characters_assets[char_name] = {
                        'id': str(uuid.uuid4())[:8],
                        'name': char_name,
                        'description': description,
                        'tags': [char.get('role', '')] if char.get('role') else [],
                        'referenceUrl': '',
                        'role': char.get('role', ''),
                        'clothing': '',
                        'expression': '',
                        'createdAt': datetime.now().isoformat(),
                        'updatedAt': datetime.now().isoformat()
                    }
    except Exception as e:
        logger.error(f'同步角色到视觉资产失败: {e}')


def _sync_characters_to_visual_assets(project):
    """将项目中的角色同步到视觉资产库"""
    try:
        if not project.visualAssets:
            project.visualAssets = {'characters': {}, 'scenes': {}, 'props': {}}
        
        characters_assets = project.visualAssets.get('characters', {})
        
        for char in project.characters:
            if isinstance(char, dict):
                char_name = char.get('name')
                if char_name and char_name not in characters_assets:
                    # 提取角色描述
                    description = char.get('living_characteristics', {}).get('physical_presence', '')
                    if not description:
                        description = char.get('initial_state', {}).get('description', '')
                    if not description:
                        description = char.get('appearance', '')
                    if not description:
                        description = char.get('description', '')
                    
                    characters_assets[char_name] = {
                        'id': str(uuid.uuid4())[:8],
                        'name': char_name,
                        'description': description,
                        'tags': [char.get('role', '')] if char.get('role') else [],
                        'referenceUrl': '',
                        'role': char.get('role', ''),
                        'clothing': '',
                        'expression': '',
                        'createdAt': datetime.now().isoformat(),
                        'updatedAt': datetime.now().isoformat()
                    }
                    logger.info(f'🔧 同步角色到视觉资产: {char_name}')
        
        project.visualAssets['characters'] = characters_assets
    except Exception as e:
        logger.error(f'同步角色到视觉资产失败: {e}')


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
    """从创意创建项目，先生成故事节拍(Step 3)"""
    try:
        data = request.json or {}
        title = data.get('title', '').strip()

        # 🔥 支持多集数据结构
        episodes_data = data.get('episodes', [])
        selected_episode_number = data.get('episode_number')  # 指定要生成的集数

        # 兼容旧的单集格式
        if not episodes_data:
            episode = data.get('episode', 1)
            description = data.get('description', '').strip()
            world_setting = data.get('world_setting', '').strip()
            style = data.get('style', '通用')
            shot_count = data.get('shot_count', 3)
            shot_duration = data.get('shot_duration', 8)
            protagonist = data.get('protagonist', {})
            episode_title = f'第{episode}集'
            episode_focus = data.get('first_episode_focus', {})
        else:
            # 🔥 从episodes数组中提取数据
            if selected_episode_number is None:
                # 如果没有指定集数，生成第一个未生成的集
                selected_episode_number = 1

            # 查找指定的集数据(兼容 episode 和 ep 字段)
            episode_data = None
            for ep in episodes_data:
                ep_num = ep.get('episode') or ep.get('ep')
                if ep_num == selected_episode_number:
                    episode_data = ep
                    break

            if not episode_data:
                return jsonify({
                    'success': False,
                    'error': f'未找到第{selected_episode_number}集的数据'
                }), 400

            # 🔥 检查该集是否已经生成
            project_dir = VIDEO_PROJECTS_DIR / title
            episode_name = f'{selected_episode_number}集_创意导入'
            episode_dir = project_dir / episode_name
            shots_v2_file = episode_dir / 'shots_v2.json'

            if shots_v2_file.exists() and episode_data.get('status') != 'pending':
                logger.info(f'⏭️ [创意导入] 第{selected_episode_number}集已生成，跳过')
                return jsonify({
                    'success': True,
                    'message': f'第{selected_episode_number}集已生成，无需重复生成',
                    'skipped': True,
                    'episode': selected_episode_number
                })

            # 提取集数据
            episode = selected_episode_number
            episode_title = episode_data.get('episode_title', f'第{episode}集')
            description = episode_data.get('description', '').strip()
            shot_duration = episode_data.get('shot_duration', 5)
            episode_focus = episode_data.get('focus', {})

            # 从根级别获取共享数据
            world_setting = data.get('world_setting', '').strip()
            style = data.get('style', '通用')
            protagonist = data.get('protagonist', {})
            shot_count = 3

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
        
        # 验证主角信息
        protagonist_name = protagonist.get('name', '').strip()
        protagonist_appearance = protagonist.get('appearance', '').strip()
        if not protagonist_name:
            return jsonify({
                'success': False,
                'error': '请输入主角姓名'
            }), 400
        if not protagonist_appearance:
            return jsonify({
                'success': False,
                'error': '请输入主角外观特征'
            }), 400

        # 限制参数范围
        episode = max(1, min(999, int(episode)))
        # 🔥 移除 shot_count 限制，让AI自由决定分镜数量
        shot_duration = max(3, min(10, int(shot_duration)))  # 短视频节奏：3-10秒/镜头
        
        # 🔥 基于故事复杂度预估总时长(不再用 shot_count * shot_duration)
        # 让AI先决定分镜数量，再计算总时长
        total_duration = 60  # 默认60秒，实际由故事节拍决定

        logger.info(f'📝 [创意导入] 标题: {title}, 第{episode}集, 风格: {style}, 镜头时长{shot_duration}秒, AI自由决定分镜数量')
        logger.info(f'🎭 [创意导入] 主角: {protagonist_name}, 外观: {protagonist_appearance[:50]}...')
        if world_setting:
            logger.info(f'   世界观设定: {world_setting[:100]}...')

        # 1. 创建项目目录
        project_dir = VIDEO_PROJECTS_DIR / title
        project_dir.mkdir(exist_ok=True)

        episode_name = f'{episode}集_创意导入'
        episode_dir = project_dir / episode_name
        episode_dir.mkdir(exist_ok=True)
        
        # 🔥 创建主角角色信息
        protagonist_role = protagonist.get('role', '主角')
        protagonist_age = protagonist.get('age', '')
        protagonist_character = {
            'id': 'protagonist_001',
            'name': protagonist_name,
            'role': protagonist_role,
            'age': protagonist_age,
            'description': f'{protagonist_name}，{protagonist_age + "，" if protagonist_age else ""}{protagonist_appearance}',
            'appearance': protagonist_appearance,
            'living_characteristics': {
                'physical_presence': protagonist_appearance
            },
            'is_protagonist': True
        }

        # 检查是否提供了完整的分镜列表
        provided_shots = data.get('shots')
        
        if provided_shots and len(provided_shots) > 0:
            # 🔥 使用用户提供的完整分镜数据
            logger.info(f'[创意导入] 使用用户提供的分镜数据，共{len(provided_shots)}个镜头')
            
            # 从分镜生成故事节拍(用于兼容)
            story_beats = generate_story_beats_from_shots(
                title=f"{title} 第{episode}集",
                description=description,
                shots=provided_shots,
                protagonist=protagonist_character
            )
            
            # 转换用户提供的分镜为标准格式
            shots_en = []
            shots_cn = []
            for i, shot in enumerate(provided_shots, 1):
                # 构建标准英文分镜格式
                shot_en = {
                    'shot_number': shot.get('shot_number', i),
                    'scene_title': shot.get('scene_title', f'Scene {i}'),
                    'shot_type': shot.get('shot_type', 'standard'),
                    'duration_seconds': shot.get('duration', 5),
                    'veo_prompt_standard': shot.get('veo_prompt', shot.get('content', '')),
                    'veo_prompt_reference': shot.get('veo_prompt', shot.get('content', '')),
                    'veo_prompt_frames': shot.get('veo_prompt', shot.get('content', '')),
                    'dialogue': shot.get('dialogues', [])
                }
                shots_en.append(shot_en)
                
                # 构建中文分镜格式(复用英文或翻译)
                shot_cn = {
                    'shot_number': shot.get('shot_number', i),
                    'scene_title': shot.get('scene_title', f'场景 {i}'),
                    'shot_type': shot.get('shot_type', 'standard'),
                    'duration_seconds': shot.get('duration', 5),
                    'visual_description_standard': shot.get('content', ''),
                    'visual_description_reference': shot.get('content', ''),
                    'visual_description_frames': shot.get('content', ''),
                    'dialogue': shot.get('dialogues', [])
                }
                shots_cn.append(shot_cn)
            
            # 保存用户提供的分镜
            shots_v2_data = {
                'version': '2.0',
                'generated_at': datetime.now().isoformat(),
                'source': 'user_import',
                'title': title,
                'episode': episode,
                'total_shots': len(shots_en),
                'shots': shots_en
            }
            shots_v2_file = episode_dir / 'shots_v2.json'
            with open(shots_v2_file, 'w', encoding='utf-8') as f:
                json.dump(shots_v2_data, f, ensure_ascii=False, indent=2)
                
            shots_v2_cn_file = episode_dir / 'shots_v2_cn.json'
            with open(shots_v2_cn_file, 'w', encoding='utf-8') as f:
                json.dump({**shots_v2_data, 'language': 'cn', 'shots': shots_cn}, f, ensure_ascii=False, indent=2)
                
        else:
            # 2. 调用AI生成故事节拍 (Step 3)
            logger.info(f'[创意导入] 开始生成故事节拍...')
            story_beats = generate_story_beats_from_idea(
                title=f"{title} 第{episode}集",
                description=description,
                world_setting=world_setting,
                style=style,
                total_duration=total_duration,
                protagonist=protagonist_character
            )

            # 3. 基于故事节拍生成专业分镜头(全英文)(Step 4)
            logger.info(f'[创意导入] 基于故事节拍生成分镜头(全英文)...')
            
            # 🔥 创建基础视觉资产(包含主角信息)
            visual_assets = {
                'characters': {
                    'protagonist': protagonist_character
                },
                'scenes': {},
                'props': {}
            }
            
            shots_en = generate_shots_from_storybeats(
                title=title,
                story_beats=story_beats,
                style=style,
                shot_duration=shot_duration,
                visual_assets=visual_assets
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

        # 🔥 提取视觉资产清单 (Step 6)
        logger.info(f'🎨 [创意导入] 开始提取视觉资产...')
        visual_assets = extract_visual_assets_from_shots(shots_en, shots_cn, title)

        # 保存视觉资产到文件
        visual_assets_file = episode_dir / 'visual_assets.json'
        with open(visual_assets_file, 'w', encoding='utf-8') as f:
            json.dump(visual_assets, f, ensure_ascii=False, indent=2)
        logger.info(f'✅ [创意导入] 视觉资产已保存: {visual_assets_file}')
        logger.info(f'   - 角色: {len(visual_assets.get("characters", []))} 个')
        logger.info(f'   - 场景: {len(visual_assets.get("scenes", []))} 个')
        logger.info(f'   - 道具: {len(visual_assets.get("props", []))} 个')

        # 🔥 生成帧序列提示词 (Step 7)
        logger.info(f'🎬 [创意导入] 开始生成帧序列提示词...')
        frame_sequences = generate_frame_sequences_from_shots(shots_en, shots_cn, visual_assets, title)

        # 保存帧序列到文件
        frame_sequences_file = episode_dir / 'frame_sequences.json'
        with open(frame_sequences_file, 'w', encoding='utf-8') as f:
            json.dump(frame_sequences, f, ensure_ascii=False, indent=2)
        logger.info(f'✅ [创意导入] 帧序列已保存: {frame_sequences_file}')
        logger.info(f'   - 总镜头数: {len(frame_sequences.get("sequences", []))} 个')

        # 🔥 合并中英文数据，保存完整的 shots 到项目信息
        merged_shots = []
        for i, (shot_cn, shot_en) in enumerate(zip(shots_cn, shots_en), 1):
            merged_shot = {
                'id': f'shot_{i}',
                'shot_number': shot_cn.get('shot_number', i),
                'scene_number': 1,
                'scene_title': shot_cn.get('scene_title', ''),
                'shot_type': shot_cn.get('shot_type', ''),
                'duration': shot_cn.get('duration_seconds', 8),
                # 🔥 英文提示词(用于AI生成)
                'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                # 🔥 中文描述(用于显示)
                'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                # 🔥 四种图片提示词(英文，用于AI生成)
                'image_prompts': shot_en.get('image_prompts', {}),
                # 🔥 四种图片提示词(中文，用于显示)
                'image_prompts_cn': shot_cn.get('image_prompts_cn', {}),
                # 兼容旧模式
                'veo_prompt': shot_en.get('veo_prompt_standard', ''),
                'visual_description': shot_cn.get('visual_description_standard', ''),
                'preferred_mode': 'standard',
                'dialogue': shot_cn.get('dialogue', {}),
                'status': 'pending'
            }
            merged_shots.append(merged_shot)

        # 将视觉资产转换为字典格式(兼容存储)
        visual_assets_dict = {
            'characters': {item.get('name', f'char_{i}'): item for i, item in enumerate(visual_assets.get('characters', []))},
            'scenes': {item.get('name', f'scene_{i}'): item for i, item in enumerate(visual_assets.get('scenes', []))},
            'props': {item.get('name', f'prop_{i}'): item for i, item in enumerate(visual_assets.get('props', []))}
        }

        # 6. 创建项目信息(兼容前端格式)
        project_data = {
            'id': str(uuid.uuid4())[:8],
            'title': title,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'status': 'draft',
            'episodes': [{
                'id': episode_name,
                'title': episode_title if 'episode_title' in locals() else f'第{episode}集',
                'name': episode_name,
                'content': description,
                'shot_count': len(merged_shots),
                'shot_duration': shot_duration,
                'shots': merged_shots  # 🔥 保存合并后的完整数据
            }],
            'characters': [protagonist_character],  # 🔥 保存主角信息
            'visualAssets': visual_assets_dict,  # 🔥 保存视觉资产
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
            'episode': episode,
            'episode_title': episode_title if 'episode_title' in locals() else f'第{episode}集',
            'message': f'成功创建第{episode}集并生成故事节拍，共{len(story_beats.get("scenes", []))}个场景'
        }), 201

    except Exception as e:
        logger.error(f'❌ [创意导入] 创建失败: {e}')
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_story_beats_from_idea(title: str, description: str, world_setting: str, style: str, total_duration: int = 80, protagonist: dict = None) -> dict:
    """
    根据创意描述生成故事节拍 (Step 3)
    
    Args:
        title: 剧集标题
        description: 创意描述
        world_setting: 世界观设定
        style: 风格
        total_duration: 总时长(秒)
        protagonist: 主角信息字典
        
    Returns:
        故事节拍数据字典
    """
    # 🔥 优化：让AI自由决定场景数量和时长
    # 根据创意复杂度预估：简单故事6-8场景，复杂故事10-15场景
    min_scenes = 6
    max_scenes = 15
    suggested_duration = total_duration or 60  # 默认60秒
    
    # 计算参考场景数和时长分配(用于回退逻辑)
    scene_count = max(min_scenes, min(max_scenes, suggested_duration // 8))
    base_duration = suggested_duration // scene_count
    remainder = suggested_duration % scene_count
    
    try:
        
        system_prompt = f"""你是一个专业的【短视频短剧】编剧。请根据以下创意描述，生成故事节拍(Story Beats)。

## 🎬 场景设计原则(AI自由决定)

1. **场景数量由AI根据故事复杂度决定**
   - 简单故事(单线叙事)：6-8个场景
   - 标准故事(有转折)：8-10个场景  
   - 复杂故事(多冲突、多转折)：10-15个场景
   - **关键：每个情绪转折都应该是一个独立场景**

2. **场景时长原则**
   - 快节奏/动作场景：3-5秒
   - 对白/情绪场景：5-8秒
   - 高潮/关键转折：8-12秒
   - **总时长约{suggested_duration}秒(可上下浮动20%)**

3. **短视频叙事结构(不是传统三幕)**
   - **0-10%：黄金3秒钩子** - 炸裂开场，立即抓住注意力
   - **10-30%：快速铺垫** - 用画面快速建立人物和背景
   - **30-50%：第一次转折** - 小高潮或意外事件
   - **50-70%：冲突升级** - 主角面临更大危机
   - **70-90%：大高潮** - 情绪顶点，解决核心冲突
   - **90-100%：强钩子结尾** - 引出下集或留下悬念

4. **情绪过山车设计(关键)**
   - 相邻场景情绪必须不同(如：紧张→幽默→紧张)
   - 禁止连续3个场景同一情绪
   - 必须有至少一次180°情绪反转

5. **对白设计**
   - 每个场景1-2句对白，简短有力
   - 对白必须是"钩子型"(留悬念、带情绪)
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

        # 构建用户提示词 - 优化版：让AI自由决定场景数
        world_setting_section = f"""
世界观设定：
{world_setting}
""" if world_setting else ""
        
        # 🔥 构建主角信息部分
        protagonist_section = ""
        if protagonist:
            protagonist_name = protagonist.get('name', '主角')
            protagonist_age = protagonist.get('age', '')
            protagonist_appearance = protagonist.get('appearance', '')
            protagonist_role = protagonist.get('role', '主角')
            protagonist_section = f"""
主角信息：
- 姓名：{protagonist_name}
- 年龄：{protagonist_age or '未指定'}
- 身份/性格：{protagonist_role}
- 外观特征：{protagonist_appearance}

**重要：在对话中直接使用主角姓名"{protagonist_name}"，不要使用"主角"这个词。**
"""

        user_prompt = f"""
剧集标题：{title}
风格：{style}
参考总时长：{suggested_duration}秒(AI可根据故事需要调整±20%)
建议场景数：{min_scenes}-{max_scenes}个(AI根据创意复杂度自由决定)
{world_setting_section}
{protagonist_section}

## 🔥 核心创意(必须紧紧围绕此展开)
{description}

## 生成要求：
1. **AI自由决定场景数量**：根据创意复杂度生成{min_scenes}-{max_scenes}个场景
2. **每个场景必须有明确的情绪标签**：如"疑惑→贪婪→决绝"
3. **相邻场景情绪必须不同**：形成情绪过山车
4. **场景时长由AI决定**：快节奏3-5秒，对白5-8秒，高潮8-12秒
5. **必须有强钩子开场和悬念结尾**
6. **对白中的speaker必须使用角色真实姓名**，如"{protagonist.get('name', '主角') if protagonist else '主角'}"，而不是"主角"

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
                    
                    # 🔥 将"主角"替换为具体名字
                    if protagonist:
                        protagonist_name = protagonist.get('name', '主角')
                        for scene in scenes:
                            for dialogue in scene.get('dialogues', []):
                                if dialogue.get('speaker') == '主角':
                                    dialogue['speaker'] = protagonist_name
                
                return story_beats
                
            except Exception as e:
                logger.error(f'AI生成故事节拍失败: {e}')
                return _get_default_story_beats_for_idea(scene_count, base_duration, remainder, protagonist)
        else:
            return _get_default_story_beats_for_idea(scene_count, base_duration, remainder, protagonist)
            
    except Exception as e:
        logger.error(f'生成故事节拍失败: {e}')
        return _get_default_story_beats_for_idea(3, 8, 0, protagonist)


def _get_default_story_beats_for_idea(scene_count: int, base_duration: int, remainder: int, protagonist: dict = None):
    """获取默认故事节拍(用于创意导入)"""
    # 🔥 获取主角名字
    protagonist_name = protagonist.get('name', '主角') if protagonist else '主角'
    
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
                'speaker': protagonist_name,
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
        system_prompt = """你是一位专业的影视分镜头设计师，擅长为AI视频生成工具(如Sora、Runway、Veo)设计高质量的分镜头脚本。

每个镜头需要包含：
1. shot_number: 镜头编号(从1开始)
2. shot_type: 镜头类型(特写/主观视角/近景/中景/全景/远景)
3. veo_prompt: 画面描述(静态画面)- 这是最关键的部分，需要包含：

   【画面构成】
   - 描述在这个镜头范围内看到什么(人物状态、表情、服装、环境)
   - 用姿态词表达空间关系：站立/坐下/跪地/悬空/倒地/扑向/后退/侧身
   - 不要描述动作过程，只描述画面定格时的样子

   【运镜指令】(提升电影感的关键)
   - 推镜头(Push in)：从远到近，增强紧张感和代入感
   - 拉镜头(Pull out)：从近到远，展现环境和空间关系
   - 环绕镜头(Orbit)：围绕主体旋转，展现立体感
   - 跟随镜头(Follow)：跟随人物移动，增强动态感
   - 升降镜头(Crane up/down)：垂直移动，展现宏大场景
   - 示例："缓慢推镜头，从全景推至面部特写"、"环绕镜头，360度展现人物"

   【光影细节】(提升画面质感)
   - 体积光(Volumetric lighting)：光束穿透烟雾/尘埃的效果
   - 丁达尔效应(God rays)：光线透过缝隙形成的光柱
   - 边缘光(Rim light)：勾勒人物轮廓的背光
   - 戏剧性光影(Dramatic lighting)：强烈的明暗对比
   - 色温对比(Color temperature)：冷暖光源的对比
   - 示例："体积光穿透石室缝隙，形成明显的丁达尔效应"、"金色边缘光勾勒人物轮廓"

   【材质质感】(增强真实感)
   - 皮肤质感：细腻的毛孔、汗珠、血管
   - 服装材质：丝绸的光泽、布料的褶皱、金属的反光
   - 环境质感：石材的粗糙、水面的波纹、尘埃的漂浮
   - 特效质感：灵气的流动、能量的闪烁、光芒的扩散
   - 示例："皮肤呈现晶莹剔透的玉质光泽，细密的汗珠反射光线"

   【完整示例】
   "幽暗封闭的石室内部，缓慢推镜头从全景推至中景，地面刻画着繁复发光的聚灵阵法，慕佩灵身着素白长裙盘膝坐于阵眼中心，体积光从石室顶部缝隙射入形成明显的丁达尔效应，金色边缘光勾勒出人物轮廓，四周摆放着五色灵石散发柔和光晕，空气中漂浮着肉眼可见的灵气光尘如萤火虫般流动，皮肤呈现出玉质般的细腻光泽，衣料质感柔软飘逸，压抑而神圣的氛围。"

4. visual.description: 动作序列(动态过程)
   - 描述镜头中发生的动作变化，用箭头 → 连接
   - 格式：状态A → 状态B → 状态C
   - 示例："阵法光芒骤然亮起 → 灵石开始剧烈颤抖 → 灵气光尘疯狂涌向慕佩灵"

5. dialogue: 对话信息(可选，如果无对话则speaker为"无"，lines为""，tone为"无")
   - speaker: 说话者
   - lines: 台词(中文)- 根据镜头时长合理安排台词量
   - lines_en: 台词(英文)
   - tone: 语气(中文)
   - tone_en: 语气(英文)
   - audio_note: 音效描述(中文)
   - audio_note_en: 音效描述(英文)

6. duration_seconds: 镜头时长(秒)- 根据镜头内容调整时长
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
- 8秒镜头建议2-3句台词(每句2-3秒)
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
    "hook": "开篇钩子(一句话吸引眼球)",
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
- 生成 {shot_count} 个镜头，每个镜头一个独立场景(scene_number从1开始)
- 每个镜头时长根据内容调整(快节奏4-6秒，对话6-8秒，情绪渲染8-10秒，宏大场景10-12秒)
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

        # 使用APIClient调用AI(不使用流式，需要JSON格式)
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
            # 尝试提取JSON(可能被```json包裹)
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
            json_text = re.sub(r',(\s*[}\]])', '\\1', json_text)

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
    """生成默认分镜头模板(AI失败时的兜底方案)"""
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

        # 🔥 获取视觉资产库(同步角色到视觉资产)
        visual_assets = project_data.get('visualAssets', {'characters': {}, 'scenes': {}, 'props': {}})
        if not visual_assets:
            visual_assets = {'characters': {}, 'scenes': {}, 'props': {}}
        
        # 🔥 自动同步角色到视觉资产
        _sync_characters_to_visual_assets_obj(characters, visual_assets)

        # 调用AI生成故事节拍
        logger.info(f"[故事节拍] 开始生成: {episode_title}")

        # 🔥 获取项目的初始创意和世界观(如果有)
        initial_idea = episode_content  # 这就是初始创意
        world_setting = project_data.get('world_setting', '') or project_data.get('settings', {}).get('world_setting', '')
        
        if api_client:
            try:
                story_beats = _generate_story_beats_with_ai(
                    episode_title=episode_title,
                    episode_content=episode_content,
                    characters=characters,
                    total_duration=80,  # 默认80秒
                    initial_idea=initial_idea,  # 🔥 传递初始创意
                    world_setting=world_setting,   # 🔥 传递世界观
                    visual_assets=visual_assets    # 🔥 传递视觉资产
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


def _generate_story_beats_with_ai(episode_title, episode_content, characters, total_duration=80, initial_idea=None, world_setting=None, visual_assets=None):
    """
    使用AI生成故事节拍 - 优化版，充分利用初始创意和视觉资产
    
    Args:
        visual_assets: 视觉资产库，用于标准化角色/场景/道具描述
    """
    # 🔥 优先使用初始创意作为核心设计依据
    core_concept = initial_idea or episode_content
    
    # 🔥 从视觉资产库获取标准描述
    visual_assets = visual_assets or {'characters': {}, 'scenes': {}, 'props': {}}
    va_characters = visual_assets.get('characters', {})
    va_scenes = visual_assets.get('scenes', {})
    
    # 构建角色字符串(使用视觉资产的标准描述)
    characters_str = ""
    if characters:
        char_list = []
        for c in characters:
            char_name = c.get('name', '')
            # 优先使用视觉资产的标准描述
            if char_name in va_characters:
                va_char = va_characters[char_name]
                description = va_char.get('description', '')
                clothing = va_char.get('clothing', '')
                expression = va_char.get('expression', '')
                char_info = f"- {char_name}"
                if description:
                    char_info += f" [外观: {description}]"
                if clothing:
                    char_info += f" [服装: {clothing}]"
                if expression:
                    char_info += f" [标志表情: {expression}]"
                char_list.append(char_info)
            else:
                # 使用基础信息
                char_list.append(f"- {char_name}: {c.get('identity', '')}, {c.get('traits', '')}")
        characters_str = "\n".join(char_list)
    else:
        characters_str = "- 未设置角色"
    
    # 🔥 构建场景资产字符串
    scenes_str = ""
    if va_scenes:
        scene_list = []
        for scene_name, scene_data in va_scenes.items():
            scene_info = f"- {scene_name}"
            if scene_data.get('description'):
                scene_info += f": {scene_data['description']}"
            if scene_data.get('lighting'):
                scene_info += f" [光线: {scene_data['lighting']}"
            if scene_data.get('colorTone'):
                scene_info += f" 色调: {scene_data['colorTone']}]"
            scene_list.append(scene_info)
        scenes_str = "\n".join(scene_list)

    # 🔥 构建世界观部分
    world_setting_section = f"""
## 世界观设定
{world_setting}
""" if world_setting else ""

    # 🔥 构建场景资产部分
    scenes_section = f"""
## 预设场景库(可使用)
{scenes_str}
""" if scenes_str else ""

    # 🔥 优化：计算高密度场景数
    avg_scene_duration = 3
    scene_count = max(6, min(20, total_duration // avg_scene_duration))
    base_duration = total_duration // scene_count
    
    prompt = f"""你是一个专业的【抖音/快手短剧】编剧。请基于以下**核心创意**生成{total_duration}秒的高密度故事节拍。

## 🔥 核心创意(必须紧紧围绕此展开)
{core_concept[:2000] if core_concept else '(暂无详细内容，请根据标题生成)'}

## 补充信息
集数标题：{episode_title}
{world_setting_section}{scenes_section}
角色设定(使用标准描述)：
{characters_str}

总时长要求：{total_duration}秒
场景密度：{scene_count}个场景(约每{base_duration}秒一个)

## 🎬 短视频节奏铁律(必须遵守)

### 1. 黄金3秒法则
- **第1个场景必须是"炸裂开场"** - 冲突、悬念、或视觉冲击
- 严禁慢热铺垫！前3秒必须抓住观众

### 2. 节奏密度要求
- 生成{scene_count}个场景
- **每3秒必须有：情绪转折 或 视觉变化 或 新信息**
- 相邻场景之间必须有强烈对比(情绪/视觉/节奏)

### 3. 情绪过山车设计(关键)
每个场景必须标注情绪，且整体形成波浪：
```
例：平静→惊讶→恐惧→荒诞→紧张→爆笑→悬疑
```
- 禁止连续3个场景同一情绪
- 必须有至少一次180°情绪反转(如恐惧→爆笑)

### 4. 短视频结构(不是三幕)
- **0-10%：超级钩子**(炸裂开场，颠覆预期)
- **10-30%：快速铺垫**(用画面而非对话交代背景)
- **30-50%：第一次转折**(小高潮或意外)
- **50-70%：第二次转折**(升级或反转)
- **70-90%：大高潮**(情绪顶点)
- **90-100%：强钩子结尾**(必须引出下集/悬念)

### 5. 视觉变化要求
- 每个场景必须有明确的【视觉变化描述】
- 镜头类型必须交替(特写→全景→POV等)，禁止连续同类型
- 必须有"视觉冲击点"(炸裂特效、夸张表情、反转画面)

### 6. 对白设计
- 每个场景最多2句对白(短视频节奏快)
- 对白必须是"钩子型"(留悬念、带情绪、有反转)
- 严禁解释性对白

### 7. 视觉资产使用规范(关键)
**生成分镜时必须严格使用以上角色标准描述，确保视觉一致性：**
- 角色外观必须与标准描述完全一致
- 服装必须使用规定的服装描述
- 表情必须符合标志性表情设定

## 输出要求
每个场景包含：
- sceneNumber: 场景序号
- sceneTitleCn/En: 中英文标题(突出情绪或转折)
- storyBeatCn/En: 叙事目的 + 视觉变化描述(必须使用标准角色描述)
- durationSeconds: 时长(秒)
- emotionalArc: 情绪曲线(如：绝决→紧张→希望)
- visualChange: 画面如何变化(如：从特写拉远到全景)
- dialogues: 对白列表(最多2句，简短有力)

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
    🔥 使用 AI 生成高质量提示词(与创意导入一致)
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

        # 🔥 使用 AI 生成分镜头(与创意导入一致)
        logger.info(f'🤖 [生成分镜] 使用 AI 生成高质量分镜头(全英文)...')

        title = project_data.get('title', '')
        style = project_data.get('settings', {}).get('style', 'cinematic')

        # 🔥 获取视觉资产库
        visual_assets = project_data.get('visualAssets', {'characters': {}, 'scenes': {}, 'props': {}})
        if not visual_assets:
            visual_assets = {'characters': {}, 'scenes': {}, 'props': {}}
        
        # 同步角色到视觉资产
        characters = project_data.get('characters', [])
        _sync_characters_to_visual_assets_obj(characters, visual_assets)

        # 调用 AI 生成分镜头(全英文，传递视觉资产)
        shots_en = generate_shots_from_storybeats(
            title=title,
            story_beats=story_beats,
            style=style,
            shot_duration=8,
            visual_assets=visual_assets
        )

        if not shots_en:
            logger.error('❌ [生成分镜] AI 生成失败')
            return jsonify({
                'success': False,
                'message': 'AI 生成分镜失败，请检查 AI 配置'
            }), 500

        logger.info(f'✅ [生成分镜] AI 生成了 {len(shots_en)} 个英文镜头')

        # 🔥 调用 AI 翻译成中文
        logger.info(f'🌐 [生成分镜] 翻译分镜头为中文...')
        shots_cn = translate_shots_to_chinese(shots_en)

        logger.info(f'✅ [生成分镜] 翻译完成')

        # 🔥 合并中英文数据(与 _load_episode_storyboards 一致)
        merged_shots = []
        for i, (shot_cn, shot_en) in enumerate(zip(shots_cn, shots_en), 1):
            merged_shot = {
                'id': f"shot_{i}",
                'shot_number': shot_cn.get('shot_number', i),
                'scene_number': 1,
                'scene_title': shot_cn.get('scene_title', ''),
                'shot_type': shot_cn.get('shot_type', ''),
                'duration': shot_cn.get('duration_seconds', 8),
                # 🔥 英文提示词(用于AI生成)
                'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                # 🔥 中文描述(用于显示)
                'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                # 🔥 图片生成提示词(四种类型)
                'image_prompts': shot_en.get('image_prompts', {}),
                'image_prompts_cn': shot_cn.get('image_prompts_cn', {}),
                # 兼容旧格式
                'image_prompt': shot_cn.get('image_prompt', ''),
                'image_prompt_en': shot_en.get('image_prompt', ''),
                # 兼容旧模式
                'veo_prompt': shot_en.get('veo_prompt_standard', ''),
                'visual_description': shot_cn.get('visual_description_standard', ''),
                'preferred_mode': 'standard',
                'dialogue': shot_cn.get('dialogue', {}),
                'visual': {},
                'status': 'pending'
            }
            merged_shots.append(merged_shot)

        logger.info(f'✅ [生成分镜] 合并中英文数据完成')

        # 🔥 检查是否是创意导入的项目
        episodes = project_data.get('episodes', [])
        is_creative_import = False
        episode_dir = None

        if episodes and len(episodes) > 0:
            first_episode = episodes[0]
            if isinstance(first_episode, dict):
                episode_name = first_episode.get('name') or first_episode.get('id') or first_episode.get('title', '')
                if '创意导入' in episode_name:
                    is_creative_import = True
                    episode_dir = project_dir / episode_name

        if is_creative_import and episode_dir:
            # 🔥 创意导入项目：更新 episodes[0].shots 和 shots_v2 文件
            logger.info(f'📝 [生成分镜] 检测到创意导入项目，更新 episodes 和 shots_v2 文件')

            # 更新 episodes[0].shots(使用合并后的数据)
            project_data['episodes'][0]['shots'] = merged_shots

            # 保存英文版 shots_v2.json
            shots_v2_en_data = {
                'version': '2.0',
                'generated_at': datetime.now().isoformat(),
                'language': 'en',
                'title': project_data.get('title', ''),
                'episode': 1,
                'total_shots': len(shots_en),
                'shots': shots_en
            }
            shots_v2_en_file = episode_dir / 'shots_v2.json'
            with open(shots_v2_en_file, 'w', encoding='utf-8') as f:
                json.dump(shots_v2_en_data, f, ensure_ascii=False, indent=2)
            logger.info(f'✅ [生成分镜] 已更新英文版: {shots_v2_en_file}')

            # 保存中文版 shots_v2_cn.json
            shots_v2_cn_data = {
                'version': '2.0',
                'generated_at': datetime.now().isoformat(),
                'language': 'cn',
                'title': project_data.get('title', ''),
                'episode': 1,
                'total_shots': len(shots_cn),
                'shots': shots_cn
            }
            shots_v2_cn_file = episode_dir / 'shots_v2_cn.json'
            with open(shots_v2_cn_file, 'w', encoding='utf-8') as f:
                json.dump(shots_v2_cn_data, f, ensure_ascii=False, indent=2)
            logger.info(f'✅ [生成分镜] 已更新中文版: {shots_v2_cn_file}')
        else:
            # 🔥 非创意导入项目：保存到项目根级别的 shots 字段(使用合并后的数据)
            logger.info(f'📝 [生成分镜] 普通项目，保存到项目根级别 shots 字段')
            project_data['shots'] = merged_shots

        # 保存项目文件
        project_data['updatedAt'] = datetime.now().isoformat()
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project_data, f, ensure_ascii=False, indent=2)

        return jsonify({
            'success': True,
            'message': f'成功生成 {len(merged_shots)} 个镜头',
            'shots': merged_shots
        })
        
    except Exception as e:
        logger.error(f'❌ [生成分镜] 失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'生成分镜失败: {str(e)}'
        }), 500


def generate_shots_from_storybeats(title: str, story_beats: dict, style: str, shot_duration: int = 8, visual_assets: dict = None) -> list:
    """
    基于故事节拍生成专业分镜头(全英文版本)
    
    Args:
        title: 剧集标题
        story_beats: 故事节拍数据
        style: 风格
        shot_duration: 每个镜头时长
        visual_assets: 视觉资产库，用于标准化角色描述
        
    Returns:
        全英文的分镜头列表
    """
    try:
        scenes = story_beats.get('scenes', [])
        if not scenes:
            logger.warning('故事节拍没有场景数据，返回空分镜头')
            return []
        
        # 🔥 处理视觉资产
        visual_assets = visual_assets or {'characters': {}, 'scenes': {}, 'props': {}}
        va_characters = visual_assets.get('characters', {})
        
        # 构建提示词 - 优化版：让AI自由决定分镜数量
        system_prompt = f"""You are a professional cinematographer and short film director specializing in AI video generation for viral short videos (抖音/快手 style).

Based on the provided story beats, generate professional video shot descriptions in English.

## 🎬 Shot Generation Guidelines

### Shot Count Strategy (AI decides based on story complexity)
- **Simple scene** (establishing shot, transition): 1-2 shots
- **Standard scene** (dialogue, action): 2-3 shots  
- **Complex scene** (fight, chase, emotional turning point): 3-4 shots
- **Key dramatic moments**: Use multiple shots with different angles for impact

### Rhythm Requirements for Short Videos
- **3-second rule**: Every 3 seconds must have visual change or emotional shift
- **Shot variety**: Alternate between Close-up, Medium, Wide, POV shots
- **Pacing**: Fast-paced action = more cuts; Emotional moments = longer takes
- **Hook shots**: First shot must grab attention within 1 second

### Each shot must include:
1. shot_number: Sequential number
2. shot_type: Shot type (Close-up/Medium shot/Wide shot/Establishing shot/POV)
3. scene_title: Brief scene title in English
4. Three different video generation modes:
   - veo_prompt_standard: Standard mode prompt (text-only, no reference images)
   - veo_prompt_reference: Reference mode prompt (with character reference images)
   - veo_prompt_frames: Frame mode prompt (with scene reference frames)
5. Three corresponding visual descriptions:
   - visual_description_standard: Dynamic action for standard mode
   - visual_description_reference: Dynamic action for reference mode
   - visual_description_frames: Dynamic action for frame mode
6. image_prompts: Four types of image generation prompts (for external AI image tools like Midjourney/Stable Diffusion)
   - scene: Empty scene background (no characters, just environment)
   - character: Character portrait/reference image
   - first_frame: Starting frame of the shot
   - last_frame: Ending frame of the shot
7. dialogue:
   - speaker: Character name or "None"
   - lines_en: English dialogue lines (appropriate for shot duration)
   - tone_en: English tone description
   - audio_note_en: Sound effect description in English
8. duration_seconds: Shot duration

Style: {style}

## 🔥 Character Visual Assets (MUST USE for consistency)
When generating character descriptions in prompts, you MUST use the following standardized character descriptions from the visual asset library:
{chr(10).join([f"- {name}: {data.get('description', '')} [Clothing: {data.get('clothing', 'N/A')}] [Expression: {data.get('expression', 'N/A')}]" for name, data in va_characters.items()]) if va_characters else "- Use detailed descriptions from story beats"}

IMPORTANT: 
1. In Standard Mode: Include complete character appearance using the above standardized descriptions
2. In Reference Mode: Use character name + the standardized clothing/expression details
3. Maintain visual consistency across all shots for the same character
4. Character clothing and appearance must match the visual assets exactly

【Three Generation Modes Explained】
1. Standard Mode (veo_prompt_standard): Pure text prompt without any reference images
   - Include complete character appearance descriptions
   - Detailed environment and lighting
   - Camera movements and composition

2. Reference Mode (veo_prompt_reference): Uses character reference images
   - Character name only (system will match reference images)
   - Focus on actions, expressions, and poses
   - Environment and lighting details

3. Frame Mode (veo_prompt_frames): Uses scene reference frames
   - Minimal description, rely on reference frame
   - Focus on camera movement and action changes
   - Lighting and atmosphere adjustments

【image_prompts Guidelines】
Generate four types of prompts for external image generation:

1. scene: Empty scene background
   - No characters, no people
   - Focus on environment, architecture, lighting
   - Suitable for background composition
   - Example: "cinematic scene background, abandoned urban demolition zone at dusk, twisted rebar and concrete debris, volumetric fog, cold blue lighting, photorealistic, 8k, highly detailed environment, no people, empty scene"

2. character: Character portrait/reference
   - Focus on character appearance, clothing, expression
   - Upper body or full body shot
   - Neutral pose, suitable for reference
   - Example: "cinematic character portrait, young delivery rider, yellow tactical jacket, cracked helmet, determined expression, photorealistic, 8k, highly detailed face, character reference, upper body"

3. first_frame: Starting frame of the shot
   - Complete scene with character in starting position
   - Static composition, frozen moment
   - Include character, environment, lighting
   - Example: "cinematic film frame, medium shot, young delivery rider looking at phone in demolition zone, dusk lighting, photorealistic, 8k, still image, frozen moment, vertical 9:16 format"

4. last_frame: Ending frame of the shot
   - Complete scene with character in ending position
   - Show action completion or transition
   - Should connect naturally with first_frame
   - Example: "cinematic film frame, medium shot, young delivery rider looking up from phone with concerned expression, demolition zone, dusk lighting, photorealistic, 8k, action completed, still image, vertical 9:16 format"

Output JSON format:
{{
    "shots": [
        {{
            "shot_number": 1,
            "shot_type": "Close-up",
            "scene_title": "Scene title in English",
            "veo_prompt_standard": "Complete text prompt with full character descriptions, environment, lighting, camera movement...",
            "veo_prompt_reference": "Character name, action, expression, environment, lighting...",
            "veo_prompt_frames": "Camera movement, action changes, lighting adjustments...",
            "visual_description_standard": "Action A → Action B → Action C",
            "visual_description_reference": "Action A → Action B → Action C",
            "visual_description_frames": "Action A → Action B → Action C",
            "image_prompts": {{
                "scene": "Empty scene background prompt...",
                "character": "Character portrait prompt...",
                "first_frame": "Starting frame prompt...",
                "last_frame": "Ending frame prompt..."
            }},
            "dialogue": {{
                "speaker": "Character Name",
                "lines_en": "English dialogue",
                "tone_en": "determined, tense",
                "audio_note_en": "Sound description"
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

        # 计算参考分镜数(给AI参考，不限制)
        estimated_shots = len(scenes) * 2  # 建议每个场景2个分镜左右
        
        user_prompt = f"""Generate professional video shots based on these story beats:

Title: {title}
Style: {style}
Total Scenes: {len(scenes)}
Suggested Shot Count: {estimated_shots}-{estimated_shots + len(scenes)} (AI decides exact number based on complexity)

Story Beats:
{chr(10).join(scenes_summary)}

## Requirements:
1. **AI decides shot count** based on each scene's narrative complexity
   - Simple scenes: 1-2 shots
   - Complex/action scenes: 3-4 shots with multiple angles
   - Key emotional moments: Use shot-reverse-shot, close-ups for impact
2. **Pacing for short videos**: Fast rhythm, 3-second visual changes
3. **First shot must be a HOOK** - grab attention immediately
4. **Include visual variety**: Mix close-ups, medium, wide shots, POV
5. **Show, don't tell**: Use visual storytelling over exposition
6. **End with cliffhanger**: Last shot should leave viewer wanting more
7. **Professional cinematography**: Include camera movement, lighting, textures
8. **Dialogue**: Natural, concise, fit the shot duration (max 2 lines per shot)
9. **Output valid JSON only**

Generate shots now:
        """
        
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
            json_text = re.sub(r',(\s*[}\]])', '\\1', json_text)
            
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
    """默认分镜头生成(AI失败时的充底方案)"""
    shots = []
    for i, scene in enumerate(scenes, 1):
        story_beat = scene.get('storyBeatEn', scene.get('storyBeatCn', f'Scene {i}'))
        scene_title = scene.get('sceneTitleEn', scene.get('sceneTitleCn', f'Scene {i}'))
        dialogues = scene.get('dialogues', [])

        if dialogues:
            dlg = dialogues[0]
            speaker = dlg.get('speaker', 'None')
            lines_en = dlg.get('linesEn', dlg.get('lines', ''))
            tone_en = dlg.get('toneEn', dlg.get('tone', ''))
        else:
            speaker = 'None'
            lines_en = ''
            tone_en = ''

        # 生成基础提示词
        base_prompt = f'{story_beat}. Cinematic composition, dramatic lighting.'

        shots.append({
            'shot_number': i,
            'shot_type': 'Medium shot',
            'scene_title': scene_title,
            # 三种模式的提示词
            'veo_prompt_standard': f'{base_prompt} Full character appearance description.',
            'veo_prompt_reference': f'Character in scene. {base_prompt}',
            'veo_prompt_frames': f'Camera follows action. {base_prompt}',
            # 三种模式的视觉描述
            'visual_description_standard': f'Scene {i} unfolds with cinematic movement',
            'visual_description_reference': f'Character performs action in scene {i}',
            'visual_description_frames': f'Camera captures scene {i} dynamics',
            # 场景图提示词
            'image_prompt': f'Photorealistic scene: {story_beat}. Cinematic lighting, detailed environment.',
            'dialogue': {
                'speaker': speaker,
                'lines_en': lines_en,
                'tone_en': tone_en,
                'audio_note_en': 'Ambient sound'
            },
            'duration_seconds': scene.get('durationSeconds', shot_duration)
        })

    logger.warning(f'使用默认分镜头: {len(shots)} 个')
    return shots


def translate_shots_to_chinese(shots: list) -> list:
    """
    将全英文分镜头翻译成中文
    发送完整JSON结构，AI翻译指定字段的值
    """
    if not shots:
        return shots
    
    try:
        logger.info(f'🌐 [翻译] 开始翻译 {len(shots)} 个镜头...')
        
        if not api_client:
            logger.warning('AI客户端未初始化，返回原始数据')
            return shots
        
        # 构建翻译指令，明确指定哪些字段需要翻译
        translation_instruction = """请翻译以下JSON中所有指定字段的值(只翻译值，不翻译key)：

【需要翻译的字段】
1. shot级别字段：
   - veo_prompt_standard
   - veo_prompt_reference  
   - veo_prompt_frames
   - visual_description_standard
   - visual_description_reference
   - visual_description_frames
   - image_prompt
   - scene_title
   - shot_type (镜头类型：Wide shot→全景, Close-up→特写, Medium shot→中景, 等)

2. dialogue对象内的字段：
   - speaker (说话者名称，如果是英文人名进行音译或意译为中文名)
   - lines_en → 翻译后存到 lines(保留lines_en原文)
   - tone_en → 翻译后存到 tone(保留tone_en原文)
   - audio_note_en → 翻译后存到 audio_note(保留audio_note_en原文)

3. image_prompts对象内的所有字段

【翻译要求】
- 保持JSON结构完整，不要修改任何key名
- 只翻译指定字段的值，其他字段保持不变
- 技术术语：cinematic→电影级, photorealistic→写实风格, 8k→8K超清
- shot_type常见翻译：Wide shot→全景, Close-up→特写, Medium shot→中景, Extreme close-up→极特写, POV→第一人称视角, Establishing shot→定场镜头, Over-the-shoulder→过肩镜头
- speaker翻译：英文人名进行音译或意译为中文名(如 Zheng→郑, Li→李)
- 翻译要自然流畅，符合中文表达习惯

【重要】
- lines_en 翻译成中文后放到 lines 字段，同时保留 lines_en 的英文原文
- tone_en 翻译成中文后放到 tone 字段，同时保留 tone_en 的英文原文
- audio_note_en 同理

返回完整JSON数组。"""

        user_prompt = f"{translation_instruction}\n\n{json.dumps(shots, ensure_ascii=False, indent=2)}"
        
        response = api_client.call_api(
            system_prompt="你是一个专业的视频提示词翻译专家。严格按照用户指令翻译JSON中的指定字段。",
            user_prompt=user_prompt,
            temperature=0.3,
            purpose="JSON结构翻译-中文"
        )
        
        if not response:
            logger.error('翻译AI返回空响应')
            return shots
        
        # 解析翻译结果
        try:
            json_text = response.strip()
            if json_text.startswith("```json"):
                json_text = json_text[7:]
            elif json_text.startswith("```"):
                json_text = json_text[3:]
            if json_text.endswith("```"):
                json_text = json_text[:-3]
            json_text = json_text.strip()
            
            translated_shots = json.loads(json_text)
            
            if not isinstance(translated_shots, list) or len(translated_shots) != len(shots):
                logger.error(f'翻译结果格式或数量不匹配: {len(translated_shots)} vs {len(shots)}')
                return shots
            
            logger.info(f'✅ [翻译] 完成 {len(translated_shots)} 个镜头翻译')
            return translated_shots
            
        except json.JSONDecodeError as e:
            logger.error(f'解析翻译结果JSON失败: {e}')
            return shots
        
    except Exception as e:
        logger.error(f'翻译分镜头失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return shots


def extract_visual_assets_from_shots(shots_en: list, shots_cn: list, title: str) -> dict:
    """
    从分镜脚本中提取视觉资产清单(角色、场景、道具)

    Args:
        shots_en: 英文分镜脚本
        shots_cn: 中文分镜脚本
        title: 项目标题

    Returns:
        视觉资产字典
    """
    if not shots_en or not api_client:
        logger.warning('无法提取视觉资产：数据为空或AI客户端未初始化')
        return {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'characters': [],
            'scenes': [],
            'props': []
        }

    try:
        logger.info(f'🎨 [视觉资产] 开始从 {len(shots_en)} 个镜头中提取...')

        # 构建提取指令
        system_prompt = f"""你是一个专业的视觉资产分析师。请分析以下分镜脚本，提取所有出现的角色、场景和道具。

## 分析要求

1. **角色 (Characters)**
   - 提取所有出现的人物或生物
   - 包含主要角色和次要角色
   - 记录外貌特征、服装、表情等关键特征
   - 生成适合图片生成的 reference_prompt(英文)

2. **场景 (Scenes)**
   - 提取所有不同的场景/地点
   - 描述环境特征、光线、氛围
   - 记录关键元素(建筑、地形、天气等)
   - 生成适合图片生成的 reference_prompt(英文)

3. **道具 (Props)**
   - 提取重要的物品、工具、装备
   - 描述外观、材质、特征
   - 生成适合图片生成的 reference_prompt(英文)

## 输出格式

只输出JSON，格式如下：
{{
  "characters": [
    {{
      "name": "角色中文名",
      "name_en": "Character English Name",
      "description": "中文描述",
      "description_en": "English description",
      "appearances": [1, 3, 4],
      "key_features": ["特征1", "特征2"],
      "reference_prompt": "cinematic character portrait, detailed English prompt for image generation, photorealistic, 8k"
    }}
  ],
  "scenes": [
    {{
      "name": "场景中文名",
      "name_en": "Scene English Name",
      "description": "中文描述",
      "description_en": "English description",
      "appearances": [1, 2],
      "key_elements": ["元素1", "元素2"],
      "reference_prompt": "cinematic scene background, detailed English prompt, no people, empty scene, 8k"
    }}
  ],
  "props": [
    {{
      "name": "道具中文名",
      "name_en": "Prop English Name",
      "description": "中文描述",
      "description_en": "English description",
      "appearances": [3],
      "reference_prompt": "cinematic object close up, detailed English prompt, 8k"
    }}
  ]
}}

## 注意事项
- reference_prompt 必须是英文，适合 FLUX/DALL-E 等图片生成模型
- 只提取真正重要的资产，避免过于细碎
- appearances 数组记录该资产出现在哪些镜头(shot_number)
"""

        # 准备分镜数据(只发送关键信息以节省token)
        shots_summary = []
        for shot_en, shot_cn in zip(shots_en, shots_cn):
            shots_summary.append({
                'shot_number': shot_en.get('shot_number'),
                'scene_title': shot_cn.get('scene_title'),
                'scene_title_en': shot_en.get('scene_title'),
                'veo_prompt': shot_en.get('veo_prompt_standard', ''),
                'visual_description': shot_cn.get('visual_description_standard', ''),
                'dialogue': shot_cn.get('dialogue', {})
            })

        user_prompt = f"""项目：{title}

分镜脚本：
{json.dumps(shots_summary, ensure_ascii=False, indent=2)}

请分析并提取视觉资产清单。"""

        # 调用AI
        result_text = api_client.call_api(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            purpose="提取视觉资产"
        )

        if not result_text:
            logger.error('AI调用失败，返回空结果')
            return {
                'version': '1.0',
                'generated_at': datetime.now().isoformat(),
                'characters': [],
                'scenes': [],
                'props': []
            }

        result_text = result_text.strip()

        # 清理可能的markdown代码块标记
        if result_text.startswith('```'):
            result_text = result_text.split('```')[1]
            if result_text.startswith('json'):
                result_text = result_text[4:]
            result_text = result_text.strip()

        assets = json.loads(result_text)

        # 添加元数据
        assets['version'] = '1.0'
        assets['generated_at'] = datetime.now().isoformat()
        assets['title'] = title

        logger.info(f'✅ [视觉资产] 提取完成: {len(assets.get("characters", []))} 角色, {len(assets.get("scenes", []))} 场景, {len(assets.get("props", []))} 道具')

        return assets

    except Exception as e:
        logger.error(f'提取视觉资产失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'characters': [],
            'scenes': [],
            'props': []
        }


def extract_first_last_frames(grid_image_path, grid_layout, output_dir):
    """
    从网格图中提取第一帧和最后一帧

    Args:
        grid_image_path: 网格图路径
        grid_layout: 网格布局 ('1x3', '2x3', '3x3')
        output_dir: 输出目录

    Returns:
        包含第一帧和最后一帧路径的字典
    """
    try:
        from PIL import Image

        logger.info(f'🖼️ [帧提取] 从 {grid_layout} 网格图提取首尾帧...')

        # 打开网格图
        img = Image.open(grid_image_path)
        width, height = img.size

        # 根据网格布局计算单帧尺寸
        if grid_layout == '1x3':
            cols, rows = 3, 1
        elif grid_layout == '2x3':
            cols, rows = 3, 2
        elif grid_layout == '3x3':
            cols, rows = 3, 3
        else:
            raise ValueError(f'不支持的网格布局: {grid_layout}')

        frame_width = width // cols
        frame_height = height // rows

        # 提取第一帧 (左上角)
        first_frame = img.crop((0, 0, frame_width, frame_height))
        first_frame_path = os.path.join(output_dir, 'first_frame.png')
        first_frame.save(first_frame_path)

        # 提取最后一帧 (右下角)
        last_col = cols - 1
        last_row = rows - 1
        last_frame = img.crop((
            last_col * frame_width,
            last_row * frame_height,
            (last_col + 1) * frame_width,
            (last_row + 1) * frame_height
        ))
        last_frame_path = os.path.join(output_dir, 'last_frame.png')
        last_frame.save(last_frame_path)

        logger.info(f'✅ [帧提取] 提取完成')

        return {
            'first_frame': first_frame_path,
            'last_frame': last_frame_path
        }

    except Exception as e:
        logger.error(f'提取首尾帧失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return None


def generate_frame_sequences_from_shots(shots_en, shots_cn, visual_assets, title):
    """
    从分镜头脚本生成帧序列提示词

    根据镜头时长动态决定帧数:
    - ≤5秒: 3帧 (1x3网格)
    - ≤8秒: 5帧 (2x3网格，中间一列只有2帧)
    - >8秒: 9帧 (3x3网格)

    Args:
        shots_en: 英文分镜头列表
        shots_cn: 中文分镜头列表
        visual_assets: 视觉资产数据
        title: 剧集标题

    Returns:
        包含帧序列数据的字典
    """
    if not shots_en or not api_client:
        logger.warning('无法生成帧序列：数据为空或AI客户端未初始化')
        return {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'sequences': []
        }

    try:
        logger.info(f'🎬 [帧序列] 开始生成帧序列提示词...')

        frame_sequences = []

        for idx, (shot_en, shot_cn) in enumerate(zip(shots_en, shots_cn), 1):
            shot_id = shot_en.get('shot_id', f'shot_{idx}')
            duration = shot_en.get('duration', 5)

            # 根据时长决定帧数和网格布局
            if duration <= 5:
                frame_count = 3
                grid_layout = '1x3'
            elif duration <= 8:
                frame_count = 5
                grid_layout = '2x3'
            else:
                frame_count = 9
                grid_layout = '3x3'

            logger.info(f'  处理 {shot_id} (时长: {duration}s, 帧数: {frame_count})')

            # 构建AI提示词
            system_prompt = f"""你是一个专业的视频分镜设计师。请为短剧分镜头生成{frame_count}个连续的画面提示词，用于生成{grid_layout}网格图。

每个提示词应该:
1. 描述具体的画面内容(角色位置、动作、表情、场景细节)
2. 保持视觉风格一致
3. 体现时间的连续性和动作的流畅性
4. 使用英文，适合直接用于图像生成(FLUX/DALL-E等)

返回JSON格式:
{{
    "frames": [
        {{
            "frame_number": 1,
            "prompt": "详细的英文画面描述",
            "description_cn": "中文画面描述"
        }},
        ...
    ]
}}"""

            user_prompt = f"""剧集标题: {title}

分镜头信息:
- 镜头ID: {shot_id}
- 时长: {duration}秒
- 场景标题: {shot_cn.get('scene_title', '')}
- 视觉描述: {shot_cn.get('visual_description_standard', '')}
- VEO提示词: {shot_en.get('veo_prompt_standard', '')}
- 对话: {json.dumps(shot_cn.get('dialogue', {}), ensure_ascii=False)}

视觉资产参考:
- 角色: {json.dumps([c.get('name', '') for c in visual_assets.get('characters', [])], ensure_ascii=False)}
- 场景: {json.dumps([s.get('name', '') for s in visual_assets.get('scenes', [])], ensure_ascii=False)}
- 道具: {json.dumps([p.get('name', '') for p in visual_assets.get('props', [])], ensure_ascii=False)}

请生成{frame_count}个连续的画面提示词。"""

            # 调用AI生成
            result_text = api_client.call_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
                purpose=f"生成帧序列-{shot_id}"
            )

            if not result_text:
                logger.warning(f'  ⚠️ {shot_id} AI调用失败，跳过')
                continue

            result_text = result_text.strip()

            # 清理markdown代码块标记
            if result_text.startswith('```'):
                result_text = result_text.split('```')[1]
                if result_text.startswith('json'):
                    result_text = result_text[4:]
                result_text = result_text.strip()

            frame_data = json.loads(result_text)

            # 构建帧序列数据
            sequence = {
                'shot_id': shot_id,
                'duration': duration,
                'frame_count': frame_count,
                'grid_layout': grid_layout,
                'frames': frame_data.get('frames', []),
                'scene': shot_cn.get('scene', ''),
                'characters': shot_cn.get('characters', ''),
                'visual_style': shot_cn.get('visual_style', '')
            }

            frame_sequences.append(sequence)
            logger.info(f'  ✅ {shot_id} 生成完成 ({frame_count}帧)')

        result = {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'title': title,
            'sequences': frame_sequences
        }

        logger.info(f'✅ [帧序列] 生成完成: {len(frame_sequences)} 个镜头')
        return result

    except Exception as e:
        logger.error(f'生成帧序列失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return {
            'version': '1.0',
            'generated_at': datetime.now().isoformat(),
            'sequences': []
        }


# ============================================================
# Shots V2 API 路由 - 用于加载和保存优化格式的分镜头数据
# ============================================================

@short_drama_api.route('/shots-v2', methods=['GET'])
def get_shots_v2():
    """获取英文版 shots_v2.json 数据"""
    try:
        novel = request.args.get('novel', '').strip()
        episode = request.args.get('episode', '').strip()
        
        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400
        
        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode
        shots_file = episode_dir / 'shots_v2.json'
        
        if not shots_file.exists():
            return jsonify({
                'success': False,
                'error': 'shots_v2.json 不存在'
            }), 404
        
        with open(shots_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        shots = data.get('shots', [])
        
        return jsonify({
            'success': True,
            'shots': shots,
            'language': 'en'
        }), 200
        
    except Exception as e:
        logger.error(f'获取 shots_v2 失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots-v2-cn', methods=['GET'])
def get_shots_v2_cn():
    """获取中文版 shots_v2_cn.json 数据"""
    try:
        novel = request.args.get('novel', '').strip()
        episode = request.args.get('episode', '').strip()
        
        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400
        
        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode
        shots_file = episode_dir / 'shots_v2_cn.json'
        
        if not shots_file.exists():
            return jsonify({
                'success': False,
                'error': 'shots_v2_cn.json 不存在'
            }), 404
        
        with open(shots_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        shots = data.get('shots', [])
        
        return jsonify({
            'success': True,
            'shots': shots,
            'language': 'cn'
        }), 200
        
    except Exception as e:
        logger.error(f'获取 shots_v2_cn 失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/shots-v2', methods=['POST'])
def save_shots_v2():
    """保存 shots_v2.json 数据(英文版)"""
    try:
        data = request.json or {}
        novel = data.get('novel', '').strip()
        episode = data.get('episode', '').strip()
        shots = data.get('shots', [])
        
        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400
        
        if not shots:
            return jsonify({
                'success': False,
                'error': 'shots 数据为空'
            }), 400
        
        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode
        shots_file = episode_dir / 'shots_v2.json'
        
        # 确保目录存在
        episode_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存数据
        shots_data = {
            'shots': shots,
            'language': 'en',
            'updated_at': datetime.now().isoformat()
        }
        
        with open(shots_file, 'w', encoding='utf-8') as f:
            json.dump(shots_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f'✅ [Shots V2] 已保存 {len(shots)} 个镜头到 {shots_file}')
        
        return jsonify({
            'success': True,
            'message': f'已保存 {len(shots)} 个镜头'
        }), 200
        
    except Exception as e:
        logger.error(f'保存 shots_v2 失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 视觉资产库 API ====================

@short_drama_api.route('/projects/<project_id>/visual-assets', methods=['GET'])
def get_visual_assets(project_id):
    """
    获取项目的视觉资产库

    返回: {
        'characters': {...},
        'scenes': {...},
        'props': {...}
    }
    """
    try:
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 🔥 优先从文件加载视觉资产(如果存在)
        visual_assets = None

        # 尝试从文件加载
        try:
            base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            novel_dir = base_dir / '视频项目' / project.title
            logger.info(f'[视觉资产] 尝试从目录加载: {novel_dir}')

            # 查找第一个集的视觉资产文件
            if project.episodes and len(project.episodes) > 0:
                first_episode = project.episodes[0]
                episode_id = first_episode.get('id') or first_episode.get('name')
                logger.info(f'[视觉资产] 找到集: episode_id={episode_id}')
                if episode_id:
                    assets_file = novel_dir / episode_id / 'visual_assets.json'
                    logger.info(f'[视觉资产] 检查文件: {assets_file}, 存在={assets_file.exists()}')
                    if assets_file.exists():
                        with open(assets_file, 'r', encoding='utf-8') as f:
                            file_assets = json.load(f)
                            # 转换数组格式为字典格式
                            visual_assets = {
                                'characters': {item.get('name', f'char_{i}'): item for i, item in enumerate(file_assets.get('characters', []))},
                                'scenes': {item.get('name', f'scene_{i}'): item for i, item in enumerate(file_assets.get('scenes', []))},
                                'props': {item.get('name', f'prop_{i}'): item for i, item in enumerate(file_assets.get('props', []))}
                            }
                            logger.info(f'✅ 从文件加载视觉资产: {assets_file}, 角色={len(visual_assets["characters"])}, 场景={len(visual_assets["scenes"])}')
                    else:
                        logger.warning(f'[视觉资产] 文件不存在: {assets_file}')
                else:
                    logger.warning(f'[视觉资产] 无法获取集ID: {first_episode}')
            else:
                logger.warning(f'[视觉资产] 项目没有集数据: episodes={project.episodes}')
        except Exception as e:
            logger.warning(f'从文件加载视觉资产失败: {e}')
            import traceback
            logger.warning(traceback.format_exc())

        # 如果文件加载失败，使用项目对象中的数据
        if not visual_assets:
            # 🔥 自动同步角色到视觉资产库
            if project.characters:
                _sync_characters_to_visual_assets(project)
                project.save()

            visual_assets = project.visualAssets or {'characters': {}, 'scenes': {}, 'props': {}}
            logger.info('使用项目对象中的视觉资产')
        
        # 🔥修复URL：根据localPath生成正确的访问URL
        for category in ['characters', 'scenes', 'props']:
            if category in visual_assets:
                for name, asset in visual_assets[category].items():
                    local_path = asset.get('localPath', '')
                    reference_url = asset.get('referenceUrl', '')
                    correct_url = None
                    
                    if local_path and '视频项目' in local_path:
                        # 从视频项目路径生成URL
                        rel_path = local_path.split('视频项目')[-1].replace('\\', '/')
                        if rel_path.startswith('/'):
                            rel_path = rel_path[1:]
                        # 🔥对中文路径进行URL编码
                        encoded_path = quote(rel_path, safe='/')
                        correct_url = f"/project-files/{encoded_path}"
                    elif local_path and 'generated_images' in local_path:
                        # 从generated_images路径生成URL（兼容旧数据）
                        rel_path = local_path.split('generated_images')[-1].replace('\\', '/')
                        if rel_path.startswith('/'):
                            rel_path = rel_path[1:]
                        # 🔥对中文路径进行URL编码
                        encoded_path = quote(rel_path, safe='/')
                        correct_url = f"/generated_images/{encoded_path}"
                    
                    if correct_url and reference_url != correct_url:
                        logger.info(f'修复URL: {name} - {reference_url} -> {correct_url}')
                        asset['referenceUrl'] = correct_url

        return jsonify({
            'success': True,
            'data': visual_assets
        })
    except Exception as e:
        logger.error(f'获取视觉资产失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/projects/<project_id>/visual-assets/<category>', methods=['POST'])
def create_visual_asset(project_id, category):
    """
    创建新的视觉资产
    
    category: characters | scenes | props
    
    请求体: {
        'name': '资产名称',
        'description': '标准描述',
        'tags': ['标签1', '标签2'],
        'referenceUrl': '参考图URL'
    }
    """
    try:
        if category not in ['characters', 'scenes', 'props']:
            return jsonify({'success': False, 'error': '无效的类别'}), 400
        
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        data = request.json
        if not data or 'name' not in data:
            return jsonify({'success': False, 'error': '缺少资产名称'}), 400
        
        asset_name = data['name']
        
        # 创建资产数据
        asset_data = {
            'id': str(uuid.uuid4())[:8],
            'name': asset_name,
            'description': data.get('description', ''),
            'tags': data.get('tags', []),
            'referenceUrl': data.get('referenceUrl', ''),
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat()
        }
        
        # 添加类别特定字段
        if category == 'characters':
            asset_data['clothing'] = data.get('clothing', '')
            asset_data['expression'] = data.get('expression', '')
        elif category == 'scenes':
            asset_data['lighting'] = data.get('lighting', '')
            asset_data['colorTone'] = data.get('colorTone', '')
        elif category == 'props':
            asset_data['category'] = data.get('category', '')
        
        # 保存到项目
        if not project.visualAssets:
            project.visualAssets = {'characters': {}, 'scenes': {}, 'props': {}}
        
        project.visualAssets[category][asset_name] = asset_data
        project.updated_at = datetime.now().isoformat()
        project.save()
        
        logger.info(f'✅ 创建视觉资产: {category}/{asset_name}')
        
        return jsonify({
            'success': True,
            'message': '资产创建成功',
            'data': asset_data
        })
        
    except Exception as e:
        logger.error(f'创建视觉资产失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/projects/<project_id>/visual-assets/<category>/<asset_name>', methods=['PUT'])
def update_visual_asset(project_id, category, asset_name):
    """
    更新视觉资产
    
    请求体: {
        'description': '标准描述',
        'tags': [...],
        ...
    }
    """
    try:
        if category not in ['characters', 'scenes', 'props']:
            return jsonify({'success': False, 'error': '无效的类别'}), 400
        
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        if not project.visualAssets or asset_name not in project.visualAssets.get(category, {}):
            return jsonify({'success': False, 'error': '资产不存在'}), 404
        
        data = request.json
        asset = project.visualAssets[category][asset_name]
        
        # 更新字段
        if 'description' in data:
            asset['description'] = data['description']
        if 'tags' in data:
            asset['tags'] = data['tags']
        if 'referenceUrl' in data:
            asset['referenceUrl'] = data['referenceUrl']
        if 'clothing' in data:
            asset['clothing'] = data['clothing']
        if 'expression' in data:
            asset['expression'] = data['expression']
        if 'lighting' in data:
            asset['lighting'] = data['lighting']
        if 'colorTone' in data:
            asset['colorTone'] = data['colorTone']
        
        asset['updatedAt'] = datetime.now().isoformat()
        project.updated_at = datetime.now().isoformat()
        project.save()
        
        logger.info(f'✅ 更新视觉资产: {category}/{asset_name}')
        
        return jsonify({
            'success': True,
            'message': '资产更新成功',
            'data': asset
        })
        
    except Exception as e:
        logger.error(f'更新视觉资产失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/projects/<project_id>/visual-assets/<category>/<asset_name>', methods=['DELETE'])
def delete_visual_asset(project_id, category, asset_name):
    """删除视觉资产"""
    try:
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        if category in project.visualAssets and asset_name in project.visualAssets[category]:
            del project.visualAssets[category][asset_name]
            project.updated_at = datetime.now().isoformat()
            project.save()
            
            logger.info(f'✅ 删除视觉资产: {category}/{asset_name}')
            return jsonify({'success': True, 'message': '资产已删除'})
        
        return jsonify({'success': False, 'error': '资产不存在'}), 404
        
    except Exception as e:
        logger.error(f'删除视觉资产失败: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@short_drama_api.route('/projects/<project_id>/visual-assets/generate', methods=['POST'])
def generate_visual_asset(project_id):
    """
    AI 生成视觉资产(角色、场景或道具)
    
    请求体: {
        'category': 'characters' | 'scenes' | 'props',
        'name': '名称',
        'prompt': '生成提示词(英文)',
        'aspect_ratio': '16:9' | '9:16' | '1:1' | '4:3',  # 仅用于场景和道具
        'image_size': '1K' | '2K' | '4K',
        # 角色特有字段(用于生成四视图):
        'description': '角色描述',
        'clothing': '服装描述',
        'expression': '表情描述'
    }
    
    注意：角色图(character)生成流程:
    1. 前端传递角色特征(description, clothing, expression)
    2. 后端自动翻译中文描述为英文(如果需要)
    3. 后端构建完整的四视图提示词(Character Design Sheet)
    4. AI生成单张16:9图片，包含:
       - 左30%: 头部特写(正面)
       - 右70%: 正面/背面/侧面全身视图(垂直排列)

    前端只需提供简单特征，复杂的提示词工程由后端自动处理。
    """
    try:
        data = request.json
        category = data.get('category')
        
        if category not in ['characters', 'scenes', 'props']:
            return jsonify({'success': False, 'error': '不支持的类别'}), 400
        
        project = ShortDramaProject.load(project_id)
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        
        name = data.get('name')
        prompt = data.get('prompt', '')
        aspect_ratio = data.get('aspect_ratio', '9:16')  # 默认竖屏
        image_size = data.get('image_size', '2K')  # 默认2K
        
        if not name:
            return jsonify({'success': False, 'error': '缺少名称'}), 400
        
        # 调用 NanoBanana 生成图像
        try:
            from src.utils.NanoBananaImageGenerator import NanoBananaImageGenerator
            
            generator = NanoBananaImageGenerator()
            
            if not generator.is_available():
                return jsonify({
                    'success': False, 
                    'error': '图片生成服务未配置，请在 config/config.py 中配置 nanobanana.api_key'
                }), 500
            
            # 🔥生成图片保存路径 - 按类别分目录，使用中文名称保存，方便识别
            # 使用项目标题（小说名）作为基础目录
            safe_title = re.sub(r'[\\/*?:"<>|]', '_', project.title)
            # 类别目录映射：characters->角色, scenes->场景, props->道具
            category_dirs = {
                'characters': '角色',
                'scenes': '场景', 
                'props': '道具'
            }
            category_dir = category_dirs.get(category, category)
            project_dir = BASE_DIR / '视频项目' / safe_title / category_dir
            project_dir.mkdir(parents=True, exist_ok=True)
            # 使用中文名称保存，方便识别（保留时间戳避免重名）
            save_path = str(project_dir / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            logger.info(f'🎨 开始生成视觉资产: {category}/{name}, 比例: {aspect_ratio}, 尺寸: {image_size}')
            
            # 🔥 角色使用四视图生成，场景和道具使用单图生成
            if category == 'characters':
                # 🔥🔥🔥 新流程：后端调用AI生成中英双语角色描述，然后构建四视图提示词
                char_id = name  # 角色ID
                raw_description = data.get('description', '')
                raw_clothing = data.get('clothing', '')
                raw_expression = data.get('expression', '')
                
                logger.info(f'🎭 角色 [{char_id}] 生成流程开始...')
                logger.info(f'📝 原始描述: {raw_description[:50]}...')
                
                # Step 1: 调用AI生成标准中英双语角色描述
                try:
                    bilingual_desc = _generate_bilingual_character_description(
                        char_id=char_id,
                        name=name,
                        raw_description=raw_description,
                        raw_clothing=raw_clothing,
                        raw_expression=raw_expression
                    )
                    logger.info(f'✅ 生成双语描述: {bilingual_desc["english"][:80]}...')
                except Exception as e:
                    logger.error(f'❌ 生成双语描述失败: {e}')
                    # 回退到简单描述
                    bilingual_desc = {
                        'character_id': char_id,
                        'chinese': f'{name}，{raw_description}',
                        'english': f'{name}, {raw_description}',
                        'tags': []
                    }
                
                # Step 2: 使用生成的英文描述构建四视图提示词
                result = generator.generate_character_model_sheet(
                    name=name,
                    character_id=char_id,
                    bilingual_desc=bilingual_desc,
                    save_path=save_path,
                    image_size=image_size
                )
            else:
                result = generator.generate_image(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size,
                    save_path=save_path
                )
            
            if not result.get('success'):
                error_msg = result.get('error', '生成失败')
                logger.error(f'❌ 图片生成失败: {error_msg}')
                return jsonify({'success': False, 'error': f'图片生成失败: {error_msg}'}), 500
            
            # 获取生成的图片路径
            local_path = result.get('local_path', '')
            
            # 🔥使用项目路径构建URL（使用/project-files/路径，对中文进行URL编码）
            if local_path and '视频项目' in local_path:
                # 从localPath提取相对路径
                rel_path = local_path.split('视频项目')[-1].replace('\\', '/')
                if rel_path.startswith('/'):
                    rel_path = rel_path[1:]
                # 🔥对中文路径进行URL编码
                encoded_path = quote(rel_path, safe='/')
                image_url = f"/project-files/{encoded_path}"
            else:
                # 回退到生成器返回的URL
                image_url = result.get('url', '')
            
            logger.info(f'✅ 图片生成成功: {image_url}')
            
            # 🔥 场景和道具添加文字水印，角色四视图已经有中文标签
            if category != 'characters':
                try:
                    # 构建水印文字
                    category_cn = {'scenes': '场景', 'props': '道具'}.get(category, '资产')
                    watermark_text = f"{category_cn}: {name}"
                    
                    # 添加水印
                    generator.add_text_watermark(
                        image_path=local_path,
                        text=watermark_text,
                        position='bottom_right',
                        font_size=32,
                        text_color=(255, 255, 255),
                        bg_color=(0, 0, 0, 200),
                        padding=15
                    )
                    logger.info(f'✅ 已添加水印: {watermark_text}')
                except Exception as watermark_error:
                    logger.warning(f'⚠️ 添加水印失败(不影响主流程): {watermark_error}')
            
        except ImportError as e:
            logger.error(f'❌ 图片生成模块导入失败: {e}')
            return jsonify({'success': False, 'error': '图片生成模块未安装'}), 500
        except Exception as gen_error:
            logger.error(f'❌ 图片生成异常: {gen_error}')
            import traceback
            logger.error(traceback.format_exc())
            return jsonify({'success': False, 'error': f'图片生成异常: {str(gen_error)}'}), 500
        
        # 构建资产数据
        asset_data = {
            'id': str(uuid.uuid4())[:8],
            'name': name,
            'description': prompt,
            'referenceUrl': image_url,
            'localPath': local_path,
            'aspectRatio': aspect_ratio,
            'imageSize': image_size,
            'createdAt': datetime.now().isoformat(),
            'updatedAt': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        # 获取现有的额外字段
        existing_asset = project.visualAssets.get(category, {}).get(name, {})
        
        if category == 'characters':
            asset_data['clothing'] = existing_asset.get('clothing', '')
            asset_data['expression'] = existing_asset.get('expression', '')
        elif category == 'scenes':
            asset_data['lighting'] = existing_asset.get('lighting', '')
            asset_data['colorTone'] = existing_asset.get('colorTone', '')
        elif category == 'props':
            asset_data['category'] = existing_asset.get('category', '')
        
        # 保存到项目
        if not project.visualAssets:
            project.visualAssets = {'characters': {}, 'scenes': {}, 'props': {}}
        
        # 合并新数据和现有数据
        project.visualAssets[category][name] = {
            **existing_asset,
            **asset_data
        }
        project.updated_at = datetime.now().isoformat()
        project.save()
        
        logger.info(f'✅ AI生成视觉资产完成: {category}/{name}')
        
        return jsonify({
            'success': True,
            'message': '视觉资产生成成功',
            'data': asset_data
        })
        
    except Exception as e:
        logger.error(f'生成视觉资产失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# 图片生成配置 API
# ============================================================

# 配置文件路径
IMAGE_GEN_CONFIG_FILE = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) / 'config' / 'image_gen_config.json'

@short_drama_api.route('/image-gen/config', methods=['GET'])
def get_image_gen_config():
    """获取图片生成配置"""
    try:
        if IMAGE_GEN_CONFIG_FILE.exists():
            with open(IMAGE_GEN_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return jsonify({
                'success': True,
                'configured': True,
                'provider': config.get('provider', ''),
                'api_url': config.get('api_url', ''),
                'api_key': config.get('api_key', ''),
                'model': config.get('model', ''),
                'size': config.get('size', '1024x1024')
            }), 200
        else:
            return jsonify({
                'success': True,
                'configured': False
            }), 200
    except Exception as e:
        logger.error(f'获取图片配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/image-gen/config', methods=['POST'])
def save_image_gen_config():
    """保存图片生成配置"""
    try:
        data = request.json or {}
        provider = data.get('provider', '')
        api_url = data.get('api_url', '')
        api_key = data.get('api_key', '')
        model = data.get('model', '')
        size = data.get('size', '1024x1024')

        if not provider or not api_url or not api_key:
            return jsonify({
                'success': False,
                'error': '缺少必要参数'
            }), 400

        # 确保配置目录存在
        IMAGE_GEN_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        # 保存配置
        config = {
            'provider': provider,
            'api_url': api_url,
            'api_key': api_key,
            'model': model,
            'size': size,
            'updated_at': datetime.now().isoformat()
        }

        with open(IMAGE_GEN_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ 图片生成配置已保存: provider={provider}, model={model}')

        return jsonify({
            'success': True,
            'message': '配置已保存'
        }), 200

    except Exception as e:
        logger.error(f'保存图片配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================
# 视觉资产 API
# ============================================================

@short_drama_api.route('/visual-assets', methods=['GET'])
def get_visual_assets_from_file():
    """获取视觉资产清单(从文件)"""
    try:
        novel = request.args.get('novel', '').strip()
        episode = request.args.get('episode', '').strip()

        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400

        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode
        assets_file = episode_dir / 'visual_assets.json'

        if not assets_file.exists():
            return jsonify({
                'success': True,
                'assets': {
                    'characters': [],
                    'scenes': [],
                    'props': []
                },
                'message': '视觉资产文件不存在'
            }), 200

        with open(assets_file, 'r', encoding='utf-8') as f:
            assets = json.load(f)

        return jsonify({
            'success': True,
            'assets': assets
        }), 200

    except Exception as e:
        logger.error(f'获取视觉资产失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/frame-sequences', methods=['GET'])
def get_frame_sequences():
    """获取帧序列数据"""
    try:
        novel = request.args.get('novel', '').strip()
        episode = request.args.get('episode', '').strip()

        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400

        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode
        sequences_file = episode_dir / 'frame_sequences.json'

        if not sequences_file.exists():
            return jsonify({
                'success': True,
                'sequences': {
                    'sequences': []
                },
                'message': '帧序列文件不存在'
            }), 200

        with open(sequences_file, 'r', encoding='utf-8') as f:
            sequences = json.load(f)

        return jsonify({
            'success': True,
            'sequences': sequences
        }), 200

    except Exception as e:
        logger.error(f'获取帧序列失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/visual-assets/regenerate', methods=['POST'])
def regenerate_visual_assets():
    """重新生成视觉资产清单"""
    try:
        data = request.get_json()
        novel = data.get('novel', '').strip()
        episode = data.get('episode', '').strip()

        if not novel:
            return jsonify({
                'success': False,
                'error': '缺少 novel 参数'
            }), 400

        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel

        # 🔥 如果没有提供 episode，自动检测项目目录下的集数
        if not episode:
            logger.info(f'🔍 [重新生成] 未提供 episode，自动检测 {novel} 目录下的集数')
            
            if not novel_dir.exists():
                return jsonify({
                    'success': False,
                    'error': f'项目目录不存在: {novel}'
                }), 404
            
            # 查找包含 shots_v2.json 的子目录
            available_episodes = []
            for item in novel_dir.iterdir():
                if item.is_dir():
                    shots_v2_file = item / 'shots_v2.json'
                    shots_v2_cn_file = item / 'shots_v2_cn.json'
                    if shots_v2_file.exists() and shots_v2_cn_file.exists():
                        available_episodes.append(item.name)
            
            if not available_episodes:
                return jsonify({
                    'success': False,
                    'error': f'项目 "{novel}" 下没有找到可用的集数。请先完成【分镜生成】步骤，生成分镜头文件后再试。'
                }), 404
            
            # 使用第一个可用的集数
            episode = available_episodes[0]
            logger.info(f'✅ [重新生成] 自动选择集数: {episode} (可用: {available_episodes})')

        episode_dir = novel_dir / episode

        # 检查分镜头文件是否存在
        shots_en_file = episode_dir / 'shots_v2.json'
        shots_cn_file = episode_dir / 'shots_v2_cn.json'

        if not shots_en_file.exists() or not shots_cn_file.exists():
            return jsonify({
                'success': False,
                'error': f'分镜头文件不存在: {episode}，无法重新生成视觉资产'
            }), 404

        # 读取分镜头数据
        with open(shots_en_file, 'r', encoding='utf-8') as f:
            shots_en_data = json.load(f)
            shots_en = shots_en_data.get('shots', [])

        with open(shots_cn_file, 'r', encoding='utf-8') as f:
            shots_cn_data = json.load(f)
            shots_cn = shots_cn_data.get('shots', [])

        # 获取标题
        title = shots_en_data.get('title', episode)

        logger.info(f'🔄 [重新生成] 开始重新生成视觉资产: {novel}/{episode}')

        # 调用视觉资产提取函数
        visual_assets = extract_visual_assets_from_shots(shots_en, shots_cn, title)

        # 保存到文件
        assets_file = episode_dir / 'visual_assets.json'
        with open(assets_file, 'w', encoding='utf-8') as f:
            json.dump(visual_assets, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ [重新生成] 视觉资产已保存: {assets_file}')

        return jsonify({
            'success': True,
            'message': '视觉资产重新生成成功',
            'assets': visual_assets,
            'stats': {
                'characters': len(visual_assets.get('characters', [])),
                'scenes': len(visual_assets.get('scenes', [])),
                'props': len(visual_assets.get('props', []))
            }
        }), 200

    except Exception as e:
        logger.error(f'重新生成视觉资产失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@short_drama_api.route('/frame-sequences/regenerate', methods=['POST'])
def regenerate_frame_sequences():
    """重新生成帧序列"""
    try:
        data = request.get_json()
        novel = data.get('novel', '').strip()
        episode = data.get('episode', '').strip()

        if not novel or not episode:
            return jsonify({
                'success': False,
                'error': '缺少 novel 或 episode 参数'
            }), 400

        # 构建文件路径
        base_dir = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        novel_dir = base_dir / '视频项目' / novel
        episode_dir = novel_dir / episode

        # 检查必需文件是否存在
        shots_en_file = episode_dir / 'shots_v2.json'
        shots_cn_file = episode_dir / 'shots_v2_cn.json'
        assets_file = episode_dir / 'visual_assets.json'

        if not shots_en_file.exists() or not shots_cn_file.exists():
            return jsonify({
                'success': False,
                'error': '分镜头文件不存在，无法重新生成帧序列'
            }), 404

        # 读取分镜头数据
        with open(shots_en_file, 'r', encoding='utf-8') as f:
            shots_en_data = json.load(f)
            shots_en = shots_en_data.get('shots', [])

        with open(shots_cn_file, 'r', encoding='utf-8') as f:
            shots_cn_data = json.load(f)
            shots_cn = shots_cn_data.get('shots', [])

        # 读取视觉资产(如果存在)
        if assets_file.exists():
            with open(assets_file, 'r', encoding='utf-8') as f:
                visual_assets = json.load(f)
        else:
            logger.warning('视觉资产文件不存在，使用空资产')
            visual_assets = {
                'characters': [],
                'scenes': [],
                'props': []
            }

        # 获取标题
        title = shots_en_data.get('title', episode)

        logger.info(f'🔄 [重新生成] 开始重新生成帧序列: {novel}/{episode}')

        # 调用帧序列生成函数
        frame_sequences = generate_frame_sequences_from_shots(shots_en, shots_cn, visual_assets, title)

        # 保存到文件
        sequences_file = episode_dir / 'frame_sequences.json'
        with open(sequences_file, 'w', encoding='utf-8') as f:
            json.dump(frame_sequences, f, ensure_ascii=False, indent=2)

        logger.info(f'✅ [重新生成] 帧序列已保存: {sequences_file}')

        return jsonify({
            'success': True,
            'message': '帧序列重新生成成功',
            'sequences': frame_sequences,
            'stats': {
                'total_shots': len(frame_sequences.get('sequences', []))
            }
        }), 200

    except Exception as e:
        logger.error(f'重新生成帧序列失败: {e}')
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def generate_story_beats_from_shots(title: str, description: str, shots: list, protagonist: dict = None) -> dict:
    """
    根据用户提供的分镜生成故事节拍(用于JSON导入模式)
    
    Args:
        title: 剧集标题
        description: 创意描述
        shots: 用户提供的分镜列表
        protagonist: 主角信息字典
        
    Returns:
        dict: 故事节拍数据
    """
    scenes = []
    current_scene = {
        'scene_number': 1,
        'title': '场景 1',
        'shots': []
    }
    
    for shot in shots:
        shot_number = shot.get('shot_number', len(current_scene['shots']) + 1)
        
        # 构建镜头数据
        shot_data = {
            'shot_number': shot_number,
            'description': shot.get('content', shot.get('veo_prompt', '')),
            'camera_angle': shot.get('camera_angle', '中景'),
            'camera_movement': shot.get('camera_movement', '固定'),
            'duration': shot.get('duration', 5)
        }
        
        # 添加对话信息
        dialogues = shot.get('dialogues', [])
        if dialogues:
            shot_data['dialogues'] = dialogues
        
        current_scene['shots'].append(shot_data)
    
    # 设置场景标题为第一个镜头的场景标题(如果有)
    if shots and shots[0].get('scene_title'):
        current_scene['title'] = shots[0]['scene_title']
    
    scenes.append(current_scene)
    
    # 构建完整的故事节拍
    story_beats = {
        'title': title,
        'description': description,
        'total_scenes': len(scenes),
        'total_shots': len(shots),
        'source': 'user_import',
        'scenes': scenes
    }
    
    # 添加主角信息
    if protagonist:
        story_beats['protagonist'] = {
            'name': protagonist.get('name', '主角'),
            'appearance': protagonist.get('appearance', ''),
            'role': protagonist.get('role', '')
        }
    
    logger.info(f'✅ [故事节拍] 从用户分镜生成: {len(scenes)}场景, {len(shots)}镜头')
    return story_beats


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
