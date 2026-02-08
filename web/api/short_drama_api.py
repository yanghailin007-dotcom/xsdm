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
            # 构建episode目录路径
            if isinstance(episode_name, dict):
                # 如果是字典对象，提取 name 或 id 字段作为目录名
                episode_dir_name = episode_name.get('name') or episode_name.get('id') or episode_name.get('title', '')
                episode_dir = project_dir / episode_dir_name
            else:
                episode_dir = project_dir / episode_name
                episode_dir_name = episode_name

            # 🔥 优先检查是否存在 shots_v2_cn.json（创意导入格式）
            shots_v2_cn_file = episode_dir / 'shots_v2_cn.json'
            shots_v2_en_file = episode_dir / 'shots_v2.json'

            if shots_v2_cn_file.exists() and shots_v2_en_file.exists():
                try:
                    # 加载中文版本（用于显示）
                    with open(shots_v2_cn_file, 'r', encoding='utf-8') as f:
                        shots_cn_data = json.load(f)

                    # 加载英文版本（用于AI提示词）
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
                            # 🔥 英文提示词（用于AI生成）
                            'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                            'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                            'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                            # 🔥 中文描述（用于显示）
                            'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                            'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                            'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                            # 🔥 四种图片提示词（英文，用于AI生成）
                            'image_prompts': shot_en.get('image_prompts', {}),
                            # 🔥 四种图片提示词（中文，用于显示）
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

            # 如果已经是字典对象（有shots），直接使用
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
        world_setting = data.get('world_setting', '').strip()
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
        if world_setting:
            logger.info(f'   世界观设定: {world_setting[:100]}...')

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
            world_setting=world_setting,
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
                # 🔥 英文提示词（用于AI生成）
                'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                # 🔥 中文描述（用于显示）
                'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                # 🔥 四种图片提示词（英文，用于AI生成）
                'image_prompts': shot_en.get('image_prompts', {}),
                # 🔥 四种图片提示词（中文，用于显示）
                'image_prompts_cn': shot_cn.get('image_prompts_cn', {}),
                # 兼容旧模式
                'veo_prompt': shot_en.get('veo_prompt_standard', ''),
                'visual_description': shot_cn.get('visual_description_standard', ''),
                'preferred_mode': 'standard',
                'dialogue': shot_cn.get('dialogue', {}),
                'status': 'pending'
            }
            merged_shots.append(merged_shot)

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
                'shot_count': len(merged_shots),
                'shot_duration': shot_duration,
                'shots': merged_shots  # 🔥 保存合并后的完整数据
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


def generate_story_beats_from_idea(title: str, description: str, world_setting: str, style: str, total_duration: int = 80) -> dict:
    """
    根据创意描述生成故事节拍 (Step 3)
    
    Args:
        title: 剧集标题
        description: 创意描述
        world_setting: 世界观设定
        style: 风格
        total_duration: 总时长（秒）
        
    Returns:
        故事节拍数据字典
    """
    try:
        # 🔥 优化：增加场景密度，每3-4秒一个节拍（短视频节奏）
        avg_scene_duration = 3
        scene_count = max(6, min(20, total_duration // avg_scene_duration))
        
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

        # 构建用户提示词
        world_setting_section = f"""
世界观设定：
{world_setting}
""" if world_setting else ""

        user_prompt = f"""
剧集标题：{title}
风格：{style}
总时长：{total_duration}秒
预计场景数：{scene_count}
{world_setting_section}

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

    # 🔥 优化：计算高密度场景数
    avg_scene_duration = 3
    scene_count = max(6, min(20, total_duration // avg_scene_duration))
    base_duration = total_duration // scene_count
    
    prompt = f"""你是一个专业的【抖音/快手短剧】编剧。请根据以下集数内容，生成{total_duration}秒的高密度叙事节拍。

## 输入信息
集数标题：{episode_title}
集数内容：{episode_content[:2000] if episode_content else '（暂无详细内容，请根据标题生成）'}

角色设定：
{characters_str}

总时长要求：{total_duration}秒
场景密度：{scene_count}个场景（约每{base_duration}秒一个）

## 🎬 短视频节奏铁律（必须遵守）

### 1. 黄金3秒法则
- **第1个场景必须是"炸裂开场"** - 冲突、悬念、或视觉冲击
- 严禁慢热铺垫！前3秒必须抓住观众

### 2. 节奏密度要求
- 生成{scene_count}个场景
- **每3秒必须有：情绪转折 或 视觉变化 或 新信息**
- 相邻场景之间必须有强烈对比（情绪/视觉/节奏）

### 3. 情绪过山车设计（关键）
每个场景必须标注情绪，且整体形成波浪：
```
例：平静→惊讶→恐惧→荒诞→紧张→爆笑→悬疑
```
- 禁止连续3个场景同一情绪
- 必须有至少一次180°情绪反转（如恐惧→爆笑）

### 4. 短视频结构（不是三幕）
- **0-10%：超级钩子**（炸裂开场，颠覆预期）
- **10-30%：快速铺垫**（用画面而非对话交代背景）
- **30-50%：第一次转折**（小高潮或意外）
- **50-70%：第二次转折**（升级或反转）
- **70-90%：大高潮**（情绪顶点）
- **90-100%：强钩子结尾**（必须引出下集/悬念）

### 5. 视觉变化要求
- 每个场景必须有明确的【视觉变化描述】
- 镜头类型必须交替（特写→全景→POV等），禁止连续同类型
- 必须有"视觉冲击点"（炸裂特效、夸张表情、反转画面）

### 6. 对白设计
- 每个场景最多2句对白（短视频节奏快）
- 对白必须是"钩子型"（留悬念、带情绪、有反转）
- 严禁解释性对白

## 输出要求
每个场景包含：
- sceneNumber: 场景序号
- sceneTitleCn/En: 中英文标题（突出情绪或转折）
- storyBeatCn/En: 叙事目的 + 视觉变化描述
- durationSeconds: 时长(秒)
- emotionalArc: 情绪曲线（如：绝决→紧张→希望）
- visualChange: 画面如何变化（如：从特写拉远到全景）
- dialogues: 对白列表（最多2句，简短有力）

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
    🔥 使用 AI 生成高质量提示词（与创意导入一致）
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

        # 🔥 使用 AI 生成分镜头（与创意导入一致）
        logger.info(f'🤖 [生成分镜] 使用 AI 生成高质量分镜头（全英文）...')

        title = project_data.get('title', '')
        style = project_data.get('settings', {}).get('style', 'cinematic')

        # 调用 AI 生成分镜头（全英文）
        shots_en = generate_shots_from_storybeats(
            title=title,
            story_beats=story_beats,
            style=style,
            shot_duration=8
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

        # 🔥 合并中英文数据（与 _load_episode_storyboards 一致）
        merged_shots = []
        for i, (shot_cn, shot_en) in enumerate(zip(shots_cn, shots_en), 1):
            merged_shot = {
                'id': f"shot_{i}",
                'shot_number': shot_cn.get('shot_number', i),
                'scene_number': 1,
                'scene_title': shot_cn.get('scene_title', ''),
                'shot_type': shot_cn.get('shot_type', ''),
                'duration': shot_cn.get('duration_seconds', 8),
                # 🔥 英文提示词（用于AI生成）
                'veo_prompt_standard': shot_en.get('veo_prompt_standard', ''),
                'veo_prompt_reference': shot_en.get('veo_prompt_reference', ''),
                'veo_prompt_frames': shot_en.get('veo_prompt_frames', ''),
                # 🔥 中文描述（用于显示）
                'visual_description_standard': shot_cn.get('visual_description_standard', ''),
                'visual_description_reference': shot_cn.get('visual_description_reference', ''),
                'visual_description_frames': shot_cn.get('visual_description_frames', ''),
                # 🔥 图片生成提示词（四种类型）
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

            # 更新 episodes[0].shots（使用合并后的数据）
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
            # 🔥 非创意导入项目：保存到项目根级别的 shots 字段（使用合并后的数据）
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
        translation_instruction = """请翻译以下JSON中所有指定字段的值（只翻译值，不翻译key）：

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
   - lines_en → 翻译后存到 lines（保留lines_en原文）
   - tone_en → 翻译后存到 tone（保留tone_en原文）
   - audio_note_en → 翻译后存到 audio_note（保留audio_note_en原文）

3. image_prompts对象内的所有字段

【翻译要求】
- 保持JSON结构完整，不要修改任何key名
- 只翻译指定字段的值，其他字段保持不变
- 技术术语：cinematic→电影级, photorealistic→写实风格, 8k→8K超清
- shot_type常见翻译：Wide shot→全景, Close-up→特写, Medium shot→中景, Extreme close-up→极特写, POV→第一人称视角, Establishing shot→定场镜头, Over-the-shoulder→过肩镜头
- speaker翻译：英文人名进行音译或意译为中文名（如 Zheng→郑, Li→李）
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
    """保存 shots_v2.json 数据（英文版）"""
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
