"""
短剧工作台 API
处理项目、角色、分镜头、视频生成等操作
"""

from flask import Blueprint, request, jsonify, send_from_directory
from pathlib import Path
import json
import uuid
import os
from datetime import datetime

from src.utils.logger import get_logger

logger = get_logger(__name__)

short_drama_api = Blueprint('short_drama_api', __name__, url_prefix='/api/short-drama')

# 项目存储目录 - 使用视频项目目录
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
VIDEO_PROJECTS_DIR = BASE_DIR / '视频项目'
VIDEO_PROJECTS_DIR.mkdir(exist_ok=True)


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

        # 扫描分镜头文件
        storyboards = {}
        for json_file in storyboard_dir.glob('*.json'):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 使用文件名（不含扩展名）作为 key
                    key = json_file.stem
                    storyboards[key] = data
            except Exception as e:
                logger.error(f'读取分镜头文件失败 {json_file}: {e}')

        logger.info(f'📜 [分镜头] 加载了 {len(storyboards)} 个分镜头文件')

        return jsonify({
            'success': True,
            'storyboards': storyboards
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
        # 🔥 同时扫描父项目目录（用于 _三视图.png 等高优先级剧照）
        project_dir = VIDEO_PROJECTS_DIR / novel_title

        logger.info(f'📸 [剧照] 扫描目录: {episode_dir}')
        logger.info(f'📸 [剧照] 同时扫描项目目录: {project_dir}')

        # 扫描剧照文件 - 先扫描剧集目录，再扫描项目目录的 _三视图 文件
        portraits = {}
        portrait_files = []

        # 剧集目录中的所有剧照
        if episode_dir.exists():
            portrait_files.extend(list(episode_dir.glob('*.png')) + list(episode_dir.glob('*.jpg')))

        # 🔥 项目目录中的 _三视图 剧照（最高优先级）
        if project_dir.exists():
            three_view_files = [f for f in project_dir.glob('*_三视图.*')]
            portrait_files.extend(three_view_files)
            logger.info(f'📸 [剧照] 发现三视图文件: {[f.name for f in three_view_files]}')

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
            # 从文件名提取信息: "1_川剧变脸：从退婚到'送温暖'_中景.mp4"
            name = video_file.stem  # 不含扩展名
            import re
            match = re.match(r'^(\d+)_(.+)', name)
            if match:
                seq_num = int(match.group(1))
                # 剩余部分是 "storyboard_title_shot_type" 或完整标题
                rest_of_name = match.group(2)

                videos.append({
                    'sequence': seq_num,
                    'name': name,
                    'filename': video_file.name,
                    'storyboard_key': rest_of_name,  # 🔥 用于匹配storyboard
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


def register_short_drama_routes(app):
    """注册短剧工作台路由"""
    app.register_blueprint(short_drama_api)
    logger.info('✅ 短剧工作台 API 已注册')
