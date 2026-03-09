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
        
        # 🔥 使用用户隔离路径
        try:
            from web.utils.path_utils import get_user_novel_dir
            base_dir = get_user_novel_dir(create=False)
            self.project_dir = base_dir / self.project_title
            if not self.project_dir.exists():
                self.project_dir = base_dir / self.safe_title
            # 如果用户路径不存在，回退到默认路径
            if not self.project_dir.exists():
                self.project_dir = Path("小说项目") / self.project_title
                if not self.project_dir.exists():
                    self.project_dir = Path("小说项目") / self.safe_title
        except Exception:
            self.project_dir = Path("小说项目") / self.project_title
            if not self.project_dir.exists():
                self.project_dir = Path("小说项目") / self.safe_title

        # 🔥 使用与EventExtractor相同的路径：characters/xxx_角色设计.json
        self.characters_dir = self.project_dir / "characters"
        self.characters_file = self.characters_dir / f"{self.project_title}_角色设计.json"
        if not self.characters_file.exists():
            # 如果项目标题包含特殊字符，尝试使用安全标题
            self.characters_file = self.characters_dir / f"{self.safe_title}_角色设计.json"

    def load_characters(self):
        """加载角色数据"""
        # 首先从项目目录加载
        if self.characters_file.exists():
            try:
                with open(self.characters_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info(f"从角色设计文件加载角色数据: {self.characters_file}")
                    # 从角色设计文件中提取角色列表
                    if isinstance(data, dict):
                        # 角色设计文件结构：{main_character: {...}, important_characters: [...]}
                        characters = []
                        if 'main_character' in data:
                            main = data['main_character']
                            if isinstance(main, dict) and 'name' in main:
                                characters.append(main)
                        # 优先使用 important_characters 字段
                        if 'important_characters' in data:
                            important = data['important_characters']
                            if isinstance(important, list):
                                characters.extend(important)
                        # 兼容 secondary_characters 字段
                        elif 'secondary_characters' in data:
                            secondary = data['secondary_characters']
                            if isinstance(secondary, list):
                                characters.extend(secondary)
                        # 兼容旧格式：如果存在 characters 字段
                        if 'characters' in data and isinstance(data['characters'], list):
                            characters.extend(data['characters'])
                        logger.info(f"加载到 {len(characters)} 个角色: {[c.get('name', 'unknown') for c in characters]}")
                        return characters
                    elif isinstance(data, list):
                        return data
                    return []
            except Exception as e:
                logger.error(f"加载角色数据失败: {e}")

        # 返回空数组
        logger.info("使用空角色数据")
        return []
    
    def save_characters(self, characters):
        """保存角色数据到角色设计文件"""
        try:
            self.characters_file.parent.mkdir(parents=True, exist_ok=True)

            # 🔥 读取现有的角色设计文件
            existing_data = {}
            if self.characters_file.exists():
                try:
                    with open(self.characters_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except Exception as e:
                    logger.warning(f"读取现有角色文件失败，将创建新文件: {e}")

            # 确保基本结构存在
            if 'main_character' not in existing_data:
                existing_data['main_character'] = {}
            # 使用 important_characters 字段（与实际文件结构一致）
            if 'important_characters' not in existing_data:
                existing_data['important_characters'] = []

            # 获取现有重要角色名称列表
            existing_char_names = {c.get('name', '') for c in existing_data['important_characters']}

            # 合并角色：只添加新的角色
            for char in characters:
                char_name = char.get('name', '')
                if char_name and char_name not in existing_char_names:
                    existing_data['important_characters'].append(char)
                    existing_char_names.add(char_name)

            # 保存回文件
            with open(self.characters_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

            logger.info(f"角色数据已保存到: {self.characters_file}")
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


@character_api.route('/characters/extract-from-storyboard', methods=['POST'])
@login_required
def extract_characters_from_storyboard():
    """
    从分镜头脚本中提取角色，对比现有角色列表，找出缺失的角色

    请求体：
    {
        "novel_title": "小说名",
        "storyboard_data": {...}  // 分镜头数据
    }

    响应：
    {
        "success": true,
        "existing_characters": ["林长生", "苏清歌", ...],
        "found_characters": ["林长生", "苏清歌", "林啸天", ...],
        "missing_characters": ["林啸天", ...],
        "dialogue_mentions": {"林啸天": 5, ...}  // 出现次数
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title', '')
        storyboard_data = data.get('storyboard_data', {})

        if not novel_title:
            return jsonify({
                'success': False,
                'error': '小说名不能为空'
            }), 400

        # 加载现有角色列表
        manager = CharacterDataManager(novel_title)
        existing_characters = manager.load_characters()
        existing_names = set()
        for char in existing_characters:
            if isinstance(char, dict):
                name = char.get('name', '')
            elif isinstance(char, str):
                name = char
            else:
                name = str(char)
            if name:
                existing_names.add(name.strip())

        logger.info(f"现有角色: {existing_names}")

        # 从分镜头中提取角色名
        found_names = {}
        dialogue_mentions = {}

        # 处理分镜头数据结构
        shots_data = []
        if isinstance(storyboard_data, dict):
            shots_data = storyboard_data.get('shots', [])
        elif isinstance(storyboard_data, list):
            shots_data = storyboard_data

        # 角色名模式（常见中文人名格式）
        # 2-4个汉字，可能包含姓氏
        name_pattern = r'[\u4e00-\u9fa5]{2,4}'

        for shot in shots_data:
            if not isinstance(shot, dict):
                continue

            # 从对话中提取角色名
            dialogue = shot.get('dialogue', '')
            if dialogue:
                # 格式: "角色名: 对话内容"
                for line in dialogue.split('\n'):
                    if ':' in line or '：' in line:
                        speaker = line.split(':')[0].split('：')[0].strip()
                        if speaker and len(speaker) >= 2 and len(speaker) <= 4:
                            # 验证是否为纯中文
                            if re.match(r'^[\u4e00-\u9fa5]+$', speaker):
                                found_names[speaker] = found_names.get(speaker, 0) + 1
                                dialogue_mentions[speaker] = dialogue_mentions.get(speaker, 0) + 1

            # 从 veo_prompt 中提取（可能包含角色动作描述）
            veo_prompt = shot.get('veo_prompt', '')
            if veo_prompt:
                # 查找符合人名模式的词
                matches = re.findall(name_pattern, veo_prompt)
                for match in matches:
                    # 过滤一些常见的非人名词汇
                    if match not in ['镜头', '画面', '场景', '背景', '特写', '全景', '中景',
                                    '近景', '远景', '人物', '角色', '少年', '少女', '老人',
                                    '男子', '女子', '青年', '中年', '光芒', '阴影', '身影']:
                        found_names[match] = found_names.get(match, 0) + 1

            # 从 screen_action 中提取
            screen_action = shot.get('screen_action', '')
            if screen_action:
                matches = re.findall(name_pattern, screen_action)
                for match in matches:
                    if match not in ['镜头', '画面', '场景', '背景', '特写', '全景', '中景',
                                    '近景', '远景', '人物', '角色', '少年', '少女', '老人',
                                    '男子', '女子', '青年', '中年']:
                        found_names[match] = found_names.get(match, 0) + 1

        # 去重并过滤出现次数过少的（可能是误判）
        found_characters = [name for name, count in found_names.items() if count >= 1]

        # 找出缺失的角色
        missing_characters = []
        for name in found_characters:
            if name not in existing_names:
                missing_characters.append({
                    'name': name,
                    'mention_count': dialogue_mentions.get(name, found_names.get(name, 0))
                })

        logger.info(f"从分镜头提取的角色: {found_characters}")
        logger.info(f"缺失的角色: {[c['name'] for c in missing_characters]}")

        return jsonify({
            'success': True,
            'existing_characters': list(existing_names),
            'found_characters': found_characters,
            'missing_characters': missing_characters,
            'dialogue_mentions': dialogue_mentions
        })

    except Exception as e:
        logger.error(f"提取角色失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@character_api.route('/characters/add-character', methods=['POST'])
@login_required
def add_character():
    """
    添加新角色并保存到角色文件

    请求体：
    {
        "novel_title": "小说名",
        "character": {
            "name": "林啸天",
            "description": "林家族长，威严霸气...",
            "age": "50岁左右",
            "gender": "男",
            "appearance": "身材高大，面容威严...",
            "personality": "威严、果断...",
            "role": "族长",  // 角色定位
            "background": "背景故事...",  // 背景故事
            "appearing_event": "事件名"  // 出现的事件
        },
        "generate_portrait": true  // 是否生成剧照
    }

    响应：
    {
        "success": true,
        "message": "角色添加成功",
        "character": {...}
    }
    """
    try:
        data = request.json
        novel_title = data.get('novel_title', '')
        character_data = data.get('character', {})
        generate_portrait = data.get('generate_portrait', False)

        if not novel_title:
            return jsonify({
                'success': False,
                'error': '小说名不能为空'
            }), 400

        if not character_data or not character_data.get('name'):
            logger.info(f"⚠️ 角色数据无效或缺少name: {character_data}")
            return jsonify({
                'success': False,
                'error': '角色名不能为空'
            }), 400

        # 加载现有角色
        manager = CharacterDataManager(novel_title)
        loaded_data = manager.load_characters()

        # 🔥 处理不同的数据格式
        if isinstance(loaded_data, dict):
            characters = loaded_data.get('characters', loaded_data.get('data', []))
        else:
            characters = loaded_data if isinstance(loaded_data, list) else []

        # 确保 characters 是列表
        if not isinstance(characters, list):
            characters = []

        # 检查角色是否已存在
        char_name = character_data['name']
        for char in characters:
            char_name_check = char.get('name') if isinstance(char, dict) else char
            if char_name_check == char_name:
                logger.info(f"⚠️ 角色已存在: {char_name}")
                return jsonify({
                    'success': False,
                    'error': f'角色 "{char_name}" 已存在'
                }), 400

        # 🔥 构建完整的角色数据（参考小说中的角色补充方式）
        new_character = {
            'name': char_name,
            'role': character_data.get('role', '配角'),  # 角色定位
            'description': character_data.get('description', ''),
            'age': character_data.get('age', ''),
            'gender': character_data.get('gender', ''),
            'appearance': character_data.get('appearance', ''),
            'personality': character_data.get('personality', ''),
            'background': character_data.get('background', ''),  # 背景故事
            'appearing_event': character_data.get('appearing_event', ''),  # 出现的事件
            'portraits': [],
            'created_at': datetime.now().isoformat()
        }

        # 🔥 只传递新角色列表（包含单个新角色）给save_characters
        # save_characters会将其合并到现有文件的secondary_characters中
        if manager.save_characters([new_character]):
            logger.info(f"新角色已添加: {char_name}")

            result = {
                'success': True,
                'message': '角色添加成功',
                'character': new_character
            }

            # 如果需要生成剧照，触发剧照生成
            if generate_portrait:
                try:
                    # 调用剧照生成服务
                    from src.managers.portrait_manager import get_portrait_manager

                    portrait_manager = get_portrait_manager()
                    portrait_prompt = _build_portrait_prompt(new_character)

                    # 创建剧照生成任务
                    portrait_result = portrait_manager.create_portrait_task(
                        novel_title=novel_title,
                        character_name=char_name,
                        prompt=portrait_prompt,
                        metadata={
                            'character_data': new_character
                        }
                    )

                    result['portrait_task'] = portrait_result
                    logger.info(f"已触发剧照生成任务: {portrait_result.get('task_id')}")

                except Exception as e:
                    logger.warning(f"触发剧照生成失败: {e}")
                    result['portrait_error'] = str(e)

            return jsonify(result)

        else:
            return jsonify({
                'success': False,
                'error': '保存角色数据失败'
            }), 500

    except Exception as e:
        logger.error(f"添加角色失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@character_api.route('/characters/generate-description', methods=['POST'])
@login_required
def generate_character_description():
    """
    根据角色名和上下文生成角色外貌描述

    请求体：
    {
        "novel_title": "小说名",
        "character_name": "林啸天",
        "context": "完整的上下文字符串，包含世界观、现有角色等",  // 🔥 现在是完整的上下文
        "worldview": {...},  // 可选：世界观信息
        "existing_characters": [...],  // 可选：现有角色列表
        "event_context": "..."  // 可选：事件上下文
    }

    响应：
    {
        "success": true,
        "description": "详细的AI生成的角色描述",
        "character_data": {
            "role": "角色定位",
            "background": "角色背景",
            "appearing_event": "出场事件",
            "age": "年龄",
            "gender": "性别",
            "personality": "性格特点",
            "description": "外貌描述"
        }
    }
    """
    try:
        data = request.json
        character_name = data.get('character_name', '')
        novel_title = data.get('novel_title', '')
        context = data.get('context', '')
        worldview = data.get('worldview', {})
        existing_characters = data.get('existing_characters', [])
        event_context = data.get('event_context', '')

        if not character_name:
            return jsonify({
                'success': False,
                'error': '角色名不能为空'
            }), 400

        # 🔥 调用AI生成角色描述 - 使用APIClient
        try:
            from src.core.APIClient import APIClient
            from config.config import CONFIG

            config = CONFIG
            api_client = APIClient(config)

            # 🔥 增强的系统提示词 - 生成结构化角色数据
            system_prompt = """你是一位专业的角色设计师，擅长为小说创作设计立体、生动的角色形象。

你的任务是为给定的角色名设计完整的角色档案。

角色档案应包含以下方面：
1. **角色定位(role)**：主角/配角/反派/导师等
2. **角色背景(background)**：身世、经历、动机（50字以内）
3. **外貌描述(description)**：脸型、五官、身材、服装、标志性特征（100字以内）
4. **性别(gender)**：男/女
5. **年龄(age)**：具体年龄段
6. **性格特点(personality)**：3-5个关键词
7. **出场原因(appearing_event)**：该角色在当前事件中出现的原因（如果有事件上下文）

请严格按照以下JSON格式输出（不要添加markdown标记）：
{
  "role": "角色定位",
  "background": "角色背景描述",
  "description": "外貌描述",
  "gender": "性别",
  "age": "年龄",
  "personality": "性格关键词",
  "appearing_event": "出场原因（如无事件上下文则为空字符串）"
}

使用简体中文，避免模板化描述。"""

            # 构建用户提示词，直接传入完整的上下文
            user_prompt_parts = [
                f"【角色名称】{character_name}"
            ]

            # 如果context包含完整信息（从frontend传入的新格式），直接使用
            if context and len(context) > 50:
                user_prompt_parts.append(f"【上下文信息】\n{context}")
            elif context:
                user_prompt_parts.append(f"【基本信息】{context}")

            if event_context:
                user_prompt_parts.append(f"【出场事件】该角色在以下情节中出现：{event_context}")

            user_prompt = '\n'.join(user_prompt_parts)
            user_prompt += f"\n\n请为角色【{character_name}】设计完整的角色档案，按JSON格式输出："

            logger.info(f"🤖 生成角色描述: {character_name}, 上下文长度: {len(context)}")

            # 调用API
            response = api_client.call_api(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
                purpose="角色档案生成"
            )

            if response:
                response_text = response.strip()

                # 🔥 尝试解析JSON响应
                character_data = {}
                description = ""

                # 移除可能的markdown标记
                response_text = response_text.strip()
                if response_text.startswith('```'):
                    # 移除markdown代码块
                    lines = response_text.split('\n')
                    response_text = '\n'.join(lines[1:-1]).strip()

                try:
                    import json
                    character_data = json.loads(response_text)
                    description = character_data.get('description', response_text)
                    logger.info(f"✅ 解析到结构化角色数据: {list(character_data.keys())}")
                except json.JSONDecodeError:
                    # JSON解析失败，尝试从文本中提取信息
                    logger.warning("⚠️ JSON解析失败，尝试文本提取")
                    description = response_text

                    # 简单的关键词匹配
                    character_data = {}
                    if '男' in description or '先生' in description or '族长' in description or '长老' in description or '父亲' in description:
                        character_data['gender'] = '男'
                    elif '女' in description or '小姐' in description or '女士' in description or '母亲' in description:
                        character_data['gender'] = '女'

                    age_match = re.search(r'(\d+岁|中年|青年|老年|少年|少女|儿童|少年郎|妙龄)', description)
                    if age_match:
                        character_data['age'] = age_match.group(1)

                    character_data['description'] = description

                # 确保有description字段
                if not character_data.get('description'):
                    character_data['description'] = description

                return jsonify({
                    'success': True,
                    'description': description,
                    'character_data': character_data
                })
            else:
                # AI调用失败，返回默认描述
                default_desc = f"{character_name}，{context}" if context else character_name
                return jsonify({
                    'success': True,
                    'description': default_desc,
                    'character_data': {
                        'description': default_desc
                    }
                })

        except Exception as e:
            logger.error(f"AI生成描述失败: {e}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            # 返回基于规则生成的描述
            default_desc = f"{character_name}，{context}" if context else character_name
            return jsonify({
                'success': True,
                'description': default_desc,
                'character_data': {
                    'description': default_desc
                },
                'note': 'AI生成失败，返回基础描述'
            })

    except Exception as e:
        logger.error(f"生成角色描述失败: {e}")
        import traceback
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def _build_portrait_prompt(character):
    """
    构建剧照生成提示词（三视图半身图）

    Args:
        character: 角色数据字典

    Returns:
        剧照生成提示词
    """
    name = character.get('name', '')
    description = character.get('description', '')
    appearance = character.get('appearance', '')
    age = character.get('age', '')
    gender = character.get('gender', '')
    personality = character.get('personality', '')

    # 构建详细的三视图提示词
    prompt_parts = []

    # 基础描述
    base_desc = f"Character portrait of {gender if gender else 'person'}"
    if age:
        base_desc += f", {age}"

    # 外貌特征
    if appearance:
        # 提取关键外貌特征
        appearance_keywords = appearance.replace('，', ',').replace('。', ' ').split()
        main_features = appearance_keywords[:5] if appearance_keywords else []
        if main_features:
            base_desc += f", {', '.join(main_features)}"

    prompt_parts.append(base_desc)

    # 三视图半身图要求
    prompt_parts.append("three-view drawing (front view, side view, back view)")
    prompt_parts.append("half-body shot (chest up)")
    prompt_parts.append("split view, character design reference sheet")

    # 表情
    if personality:
        # 从性格中提取表情关键词
        if '傲慢' in personality or '狂妄' in personality or '高高在上' in personality or '轻蔑' in personality:
            prompt_parts.append("arrogant expression, contemptuous sneer")
        elif '阴险' in personality or '狡诈' in personality or '算计' in personality:
            prompt_parts.append("sinister expression, calculating eyes")
        elif '坚毅' in personality or '不屈' in personality or '倔强' in personality:
            prompt_parts.append("determined expression, firm gaze")
        elif '温和' in personality or '慈祥' in personality:
            prompt_parts.append("kind expression, gentle smile")
        else:
            prompt_parts.append("neutral expression")
    else:
        prompt_parts.append("neutral expression")

    # 服装描述（从description或appearance中提取）
    if '长袍' in appearance or '长袍' in description or '锦袍' in description:
        prompt_parts.append("wearing ancient Chinese silk robes with gold embroidery")
    if '玉佩' in appearance or '首饰' in description or '饰物' in description:
        prompt_parts.append("jade accessories")

    # 风格要求
    prompt_parts.append("Style: Oriental fantasy Xianxia art style")
    prompt_parts.append("pure white background")
    prompt_parts.append("highly detailed")
    prompt_parts.append("clean lines")
    prompt_parts.append("professional character design")

    return ", ".join(prompt_parts)


# ==================== 路由注册函数 ====================

def register_character_routes(app):
    """注册角色API路由"""
    app.register_blueprint(character_api, url_prefix='/api')
    logger.debug("✅ 角色API路由已注册")