"""
TTS文字转语音API
集成MiniMax语音合成服务
"""

from flask import Blueprint, request, jsonify, send_from_directory
from pathlib import Path
import requests
import json
import os
from datetime import datetime
import time

# 创建蓝图
tts_api = Blueprint('tts_api', __name__, url_prefix='/api/tts')

# 导入日志记录器
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.utils.logger import get_logger

logger = get_logger(__name__)

# 导入配置文件
try:
    from config.config import CONFIG
    MINIMAX_CONFIG = CONFIG.get("minimax_tts", {})
except ImportError:
    MINIMAX_CONFIG = {}

# 基础目录
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
VIDEO_PROJECTS_DIR = BASE_DIR / '视频项目'

# MiniMax TTS配置
TTS_CONFIG = {
    "async_url": "https://api.minimaxi.com/v1/t2a_async_v2",  # 异步API
    "query_url": "https://api.minimaxi.com/v1/query/t2a_async_query_v2",  # 查询API
    "files_url": "https://api.minimaxi.com/v1/files/retrieve",  # 文件检索API
    'model_audio': MINIMAX_CONFIG.get("model", 'speech-2.8-turbo'),
    'default_sample_rate': MINIMAX_CONFIG.get("default_sample_rate", 32000),
    'default_bitrate': MINIMAX_CONFIG.get("default_bitrate", 128000),
    'default_format': MINIMAX_CONFIG.get("default_format", 'mp3')
}

# 角色音色映射
CHARACTER_VOICES = MINIMAX_CONFIG.get("character_voices", {
    '林战': 'male-qn-qingse',
    '大长老': 'male-qn-jingying',
    '三长老': 'male-qn-yuansu',
    '叶凡': 'male-qn-qingche',
    '旁白': 'male-qn-pingshu',
    '系统音': 'female-qn-dahu',
    '林啸天': 'male-qn-wengeng',
    '默认': 'female-qn-dahu'
})


class TTSManager:
    """TTS管理器"""

    def __init__(self):
        # 优先从环境变量读取，其次从配置文件读取
        self.group_id = os.getenv('MINIMAX_GROUP_ID') or MINIMAX_CONFIG.get("group_id", '')
        self.api_key = os.getenv('MINIMAX_API_KEY') or MINIMAX_CONFIG.get("api_key", '')

    def generate_speech(self, text, voice_id='female-qn-dahu', speed=1.0, pitch=0, vol=1.0):
        """
        生成语音 (使用异步API)

        Args:
            text: 要转换的文本
            voice_id: 音色ID
            speed: 语速 0.5-2.0
            pitch: 音调 -12到12
            vol: 音量 0.1-10.0

        Returns:
            {"success": bool, "audio_url": str, "audio_path": str, "duration": float}
        """
        if not self.group_id or not self.api_key:
            return {
                'success': False,
                'error': '未配置MiniMax API密钥，请在 config/config.py 中配置 minimax_tts.group_id 和 api_key'
            }

        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        # 按照新API格式构建请求
        payload = {
            'model': TTS_CONFIG['model_audio'],
            'text': text,
            'voice_setting': {
                'voice_id': voice_id,
                'speed': speed,
                'vol': vol,
                'pitch': pitch
            },
            'audio_setting': {
                'audio_sample_rate': TTS_CONFIG['default_sample_rate'],
                'bitrate': TTS_CONFIG['default_bitrate'],
                'format': TTS_CONFIG['default_format'],
                'channel': 1
            },
            'language_boost': 'Chinese'
        }

        try:
            logger.info(f'🎙️ [TTS] 提交异步任务: voice_id={voice_id}, text="{text[:30]}..."')
            logger.info(f'🎙️ [TTS] 请求URL: {TTS_CONFIG["async_url"]}')
            logger.info(f'🎙️ [TTS] 请求参数: model={TTS_CONFIG["model_audio"]}, speed={speed}, pitch={pitch}, vol={vol}')

            # 第一步：提交异步任务
            submit_response = requests.post(
                TTS_CONFIG['async_url'],
                headers=headers,
                json=payload,
                timeout=30
            )

            logger.info(f'🎙️ [TTS] 响应状态码: {submit_response.status_code}')

            if submit_response.status_code != 200:
                logger.error(f'TTS任务提交失败: {submit_response.status_code} - {submit_response.text}')
                return {
                    'success': False,
                    'error': f'任务提交失败: HTTP {submit_response.status_code}'
                }

            submit_data = submit_response.json()
            logger.info(f'🎙️ [TTS] 响应数据: {submit_data}')

            # 检查base_resp
            if 'base_resp' in submit_data:
                base_resp = submit_data['base_resp']
                logger.info(f'🎙️ [TTS] base_resp: status_code={base_resp.get("status_code")}, status_msg={base_resp.get("status_msg")}')
                if base_resp.get('status_code') != 0:
                    error_msg = base_resp.get('status_msg', '未知错误')
                    return {
                        'success': False,
                        'error': f'API返回错误: {error_msg} (code: {base_resp.get("status_code")})'
                    }

            # 获取task_id
            task_id = submit_data.get('task_id')
            if not task_id:
                logger.error(f'TTS响应缺少task_id: {submit_data}')
                return {
                    'success': False,
                    'error': f'API响应异常: 未返回task_id'
                }

            logger.info(f'🎙️ [TTS] 任务已提交: task_id={task_id}')

            # 第二步：轮询查询任务状态
            max_attempts = 60  # 最多查询60次
            poll_interval = 2  # 每2秒查询一次
            last_log_time = time.time()

            logger.info(f'🎙️ [TTS] 开始轮询任务状态，最多{max_attempts}次，间隔{poll_interval}秒')

            for attempt in range(max_attempts):
                query_url = f"{TTS_CONFIG['query_url']}?task_id={task_id}"

                query_response = requests.get(
                    query_url,
                    headers=headers,
                    timeout=10
                )

                if query_response.status_code != 200:
                    logger.warning(f'🎙️ [TTS] 查询任务状态失败: {query_response.status_code}')
                    time.sleep(poll_interval)
                    continue

                query_data = query_response.json()
                status = query_data.get('status', 'Unknown')

                # 每10秒或状态变化时记录一次日志
                current_time = time.time()
                if current_time - last_log_time >= 10 or attempt == 0:
                    logger.info(f'🎙️ [TTS] 任务状态: {status} ({attempt + 1}/{max_attempts})')
                    last_log_time = current_time

                if status == 'Success':
                    # 任务成功完成
                    file_id = query_data.get('file_id')
                    logger.info(f'🎙️ [TTS] 任务完成，file_id={file_id}')

                    # 🔥 使用 /v1/files/retrieve 获取下载链接
                    retrieve_url = f"https://api.minimaxi.com/v1/files/retrieve?file_id={file_id}"
                    retrieve_response = requests.get(
                        retrieve_url,
                        headers=headers,
                        timeout=10
                    )

                    if retrieve_response.status_code != 200:
                        logger.error(f'🎙️ [TTS] 获取文件信息失败: {retrieve_response.status_code}')
                        return {
                            'success': False,
                            'error': f'获取文件信息失败: HTTP {retrieve_response.status_code}'
                        }

                    retrieve_data = retrieve_response.json()
                    logger.info(f'🎙️ [TTS] 文件信息: {retrieve_data}')

                    if 'file' not in retrieve_data:
                        return {
                            'success': False,
                            'error': '文件信息异常'
                        }

                    file_info = retrieve_data['file']
                    download_url = file_info.get('download_url')
                    filename = file_info.get('filename', '')

                    if not download_url:
                        return {
                            'success': False,
                            'error': '未获取到下载链接'
                        }

                    logger.info(f'🎙️ [TTS] 下载音频文件: {filename}')

                    # 下载音频文件
                    audio_response = requests.get(download_url, timeout=30)
                    if audio_response.status_code == 200:
                        import base64

                        # 检查是否是tar包（包含音频+字幕+元数据）
                        if filename.endswith('.tar'):
                            import tarfile
                            import io
                            import os

                            # 解析tar包
                            tar_data = io.BytesIO(audio_response.content)
                            audio_base64 = None

                            with tarfile.open(fileobj=tar_data, mode='r') as tar:
                                for member in tar.getmembers():
                                    if member.name.endswith('.mp3') or member.name.endswith('.wav'):
                                        f = tar.extractfile(member)
                                        if f:
                                            audio_content = f.read()
                                            audio_base64 = base64.b64encode(audio_content).decode('utf-8')
                                            logger.info(f'🎙️ [TTS] 从tar包中提取音频: {member.name} ({len(audio_content)} bytes)')
                                            break

                            if not audio_base64:
                                logger.error(f'🎙️ [TTS] tar包内容: {tarfile.getmembers(tar_data)}')
                                return {
                                    'success': False,
                                    'error': 'tar包中未找到音频文件'
                                }
                        else:
                            # 直接是音频文件
                            audio_base64 = base64.b64encode(audio_response.content).decode('utf-8')

                        # 估算时长
                        duration = len(text) / 3.5

                        return {
                            'success': True,
                            'audio_base64': audio_base64,
                            'download_url': download_url,
                            'file_id': str(file_id),
                            'task_id': str(task_id),
                            'duration': duration,
                            'text_length': len(text)
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'下载音频失败: HTTP {audio_response.status_code}'
                        }

                elif status == 'Failed':
                    error_info = query_data.get('error_info', {})
                    error_msg = error_info.get('message', '未知错误')
                    return {
                        'success': False,
                        'error': f'任务失败: {error_msg}'
                    }

                elif status == 'Expired':
                    return {
                        'success': False,
                        'error': '任务已过期'
                    }

                # Processing状态，继续轮询
                time.sleep(poll_interval)

            # 超时
            return {
                'success': False,
                'error': f'任务超时 (超过{max_attempts * poll_interval}秒)'
            }

        except requests.exceptions.Timeout:
            logger.error(f'TTS请求超时')
            return {
                'success': False,
                'error': '请求超时，请稍后重试'
            }
        except Exception as e:
            logger.error(f'TTS生成失败: {e}')
            import traceback
            logger.error(f'错误堆栈: {traceback.format_exc()}')
            return {
                'success': False,
                'error': str(e)
            }

    def save_audio(self, audio_base64, output_path):
        """保存音频文件"""
        try:
            import base64
            audio_data = base64.b64decode(audio_base64)

            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'wb') as f:
                f.write(audio_data)

            logger.info(f'🎙️ [TTS] 音频已保存: {output_path}')
            return str(output_path)
        except Exception as e:
            logger.error(f'保存音频失败: {e}')
            return None


# 全局TTS管理器实例
tts_manager = TTSManager()


@tts_api.route('/config', methods=['GET'])
def get_tts_config():
    """获取TTS配置状态"""
    return jsonify({
        'success': True,
        'configured': bool(tts_manager.group_id and tts_manager.api_key),
        'voices': CHARACTER_VOICES
    })


@tts_api.route('/config', methods=['POST'])
def update_tts_config():
    """更新TTS配置"""
    try:
        data = request.json
        group_id = data.get('group_id')
        api_key = data.get('api_key')

        if group_id and api_key:
            # 更新环境变量
            os.environ['MINIMAX_GROUP_ID'] = group_id
            os.environ['MINIMAX_API_KEY'] = api_key
            tts_manager.group_id = group_id
            tts_manager.api_key = api_key

            return jsonify({
                'success': True,
                'message': 'TTS配置已更新'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'group_id和api_key不能为空'
            }), 400

    except Exception as e:
        logger.error(f'更新TTS配置失败: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/voices', methods=['GET'])
def get_available_voices():
    """获取可用音色列表"""
    voices = []
    for name, voice_id in CHARACTER_VOICES.items():
        voices.append({
            'name': name,
            'voice_id': voice_id,
            'character': name
        })
    return jsonify({
        'success': True,
        'voices': voices
    })


@tts_api.route('/generate', methods=['POST'])
def generate_speech():
    """
    生成单个镜头的配音

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scene_number": 1,
        "speaker": "林战",
        "lines": "老祖宗……苏醒了！",
        "voice_id": "male-qn-qingse",
        "speed": 1.0,
        "pitch": 0,
        "vol": 1.0
    }
    """
    try:
        data = request.json

        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scene_number = data.get('scene_number') or data.get('shot_number')
        speaker = data.get('speaker', '默认')
        lines = data.get('lines', '')
        voice_id = data.get('voice_id')
        speed = float(data.get('speed', 1.0))
        pitch = int(data.get('pitch', 0))
        vol = float(data.get('vol', 1.0))

        if not lines:
            return jsonify({
                'success': False,
                'error': '台词内容不能为空'
            }), 400

        # 使用指定的音色，或根据角色名选择默认音色
        final_voice_id = voice_id or CHARACTER_VOICES.get(speaker, CHARACTER_VOICES['默认'])

        # 生成语音
        result = tts_manager.generate_speech(lines, final_voice_id, speed, pitch, vol)

        if result.get('success'):
            # 保存音频文件
            episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'
            filename = f"{scene_number}_{speaker}_{hash(lines) % 1000}.mp3"
            audio_path = episode_dir / filename

            saved_path = tts_manager.save_audio(result['audio_base64'], audio_path)

            # 生成音频URL
            from urllib.parse import quote
            rel_path = audio_path.relative_to(VIDEO_PROJECTS_DIR)
            audio_url = f"/api/tts/audio/{quote(str(rel_path), safe='')}"

            result['audio_path'] = saved_path
            result['audio_url'] = audio_url
            result['filename'] = filename

        return jsonify(result)

    except Exception as e:
        logger.error(f'生成配音失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/generate-batch', methods=['POST'])
def generate_batch_speech():
    """
    批量生成配音

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scenes": [...]
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scenes = data.get('scenes', [])

        if not scenes:
            return jsonify({
                'success': False,
                'error': 'scenes不能为空'
            }), 400

        results = []
        success_count = 0

        for i, scene in enumerate(scenes):
            scene_number = scene.get('scene_number') or scene.get('shot_number') or (i + 1)

            # 检查是否有台词
            dialogue = scene.get('dialogue') or scene.get('_dialogue_data', {})
            if isinstance(dialogue, dict):
                speaker = dialogue.get('speaker', '')
                lines = dialogue.get('lines', '')
            else:
                speaker = str(dialogue) if dialogue else ''
                lines = ''

            if not speaker or not lines or speaker == '无':
                results.append({
                    'scene_number': scene_number,
                    'success': False,
                    'skipped': True,
                    'reason': '无台词'
                })
                continue

            # 确定音色
            voice_id = CHARACTER_VOICES.get(speaker, CHARACTER_VOICES['默认'])

            # 生成语音
            result = tts_manager.generate_speech(lines, voice_id)

            if result.get('success'):
                # 保存音频文件
                episode_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'audio'
                filename = f"{scene_number}_{speaker}.mp3"
                audio_path = episode_dir / filename

                saved_path = tts_manager.save_audio(result['audio_base64'], audio_path)

                from urllib.parse import quote
                rel_path = audio_path.relative_to(VIDEO_PROJECTS_DIR)
                audio_url = f"/api/tts/audio/{quote(str(rel_path), safe='')}"

                results.append({
                    'scene_number': scene_number,
                    'success': True,
                    'audio_url': audio_url,
                    'filename': filename,
                    'speaker': speaker,
                    'lines': lines,
                    'duration': result.get('duration', 0)
                })
                success_count += 1
            else:
                results.append({
                    'scene_number': scene_number,
                    'success': False,
                    'error': result.get('error', '未知错误')
                })

            # 避免API限流，每次请求间隔1秒
            time.sleep(1)

        return jsonify({
            'success': True,
            'results': results,
            'total': len(scenes),
            'success_count': success_count,
            'failed_count': len(scenes) - success_count
        })

    except Exception as e:
        logger.error(f'批量生成配音失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@tts_api.route('/audio/<path:filepath>', methods=['GET'])
def serve_audio_file(filepath):
    """提供音频文件访问"""
    try:
        from urllib.parse import unquote

        decoded_path = unquote(filepath)
        file_path = VIDEO_PROJECTS_DIR / decoded_path

        if file_path.exists() and file_path.is_file():
            return send_from_directory(str(file_path.parent), file_path.name)
        else:
            return jsonify({'error': '文件不存在'}), 404
    except Exception as e:
        logger.error(f'提供音频访问失败: {e}')
        return jsonify({'error': str(e)}), 500


@tts_api.route('/export-subtitle', methods=['POST'])
def export_subtitle():
    """
    导出SRT字幕文件

    请求体：
    {
        "novel_title": "小说名",
        "episode_title": "集数名",
        "scenes": [...]
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        scenes = data.get('scenes', [])

        # 生成SRT内容
        srt_content = []
        current_time = 0  # 当前时间（秒）

        for scene in scenes:
            scene_number = scene.get('scene_number') or scene.get('shot_number') or 1
            duration = scene.get('duration', 5)

            # 获取台词信息
            dialogue = scene.get('dialogue') or scene.get('_dialogue_data', {})
            if isinstance(dialogue, dict):
                speaker = dialogue.get('speaker', '')
                lines = dialogue.get('lines', '')
                tone = dialogue.get('tone', '')
            else:
                speaker = str(dialogue) if dialogue else ''
                lines = ''

            if not speaker or not lines or speaker == '无':
                # 无台词，跳过
                current_time += duration
                continue

            # 计算开始和结束时间
            start_time = current_time
            end_time = current_time + duration

            # 格式化为SRT时间格式
            def format_srt_time(seconds):
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                secs = int(seconds % 60)
                millis = int((seconds % 1) * 1000)
                return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

            srt_content.append(f"{scene_number}")
            srt_content.append(f"{format_srt_time(start_time)} --> {format_srt_time(end_time)}")
            srt_content.append(f"{speaker}: {lines}")
            srt_content.append("")

            current_time += duration

        srt_text = '\n'.join(srt_content)

        # 保存SRT文件
        subtitle_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title / 'subtitles'
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        subtitle_file = subtitle_dir / f"{episode_title}_配音字幕.srt"

        with open(subtitle_file, 'w', encoding='utf-8') as f:
            f.write(srt_text)

        logger.info(f'📝 SRT字幕已生成: {subtitle_file}')

        return jsonify({
            'success': True,
            'subtitle_file': str(subtitle_file),
            'content': srt_text
        })

    except Exception as e:
        logger.error(f'导出字幕失败: {e}')
        import traceback
        logger.error(f'错误堆栈: {traceback.format_exc()}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==================== 路由注册函数 ====================

def register_tts_routes(app):
    """注册TTS API路由"""
    app.register_blueprint(tts_api)
    logger.debug("✅ TTS API路由已注册")
