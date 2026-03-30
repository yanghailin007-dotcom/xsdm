"""
章节信息提取器 - 使用AI从生成的章节中提取结构化信息

提取内容：
1. 角色信息（新角色、角色状态变化）
2. 钩子信息（新埋下的、已回收的）
3. 世界设定（力量体系变化、势力变化）
4. 关键事件
"""

import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ChapterInfoExtractor:
    """
    使用AI从章节内容中提取结构化信息
    
    用于自动更新world_state.json等设定文件
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def extract_from_chapter(self, chapter: Dict) -> Dict:
        """
        从单个章节中提取所有信息
        
        Args:
            chapter: 章节数据字典
            
        Returns:
            提取的结构化信息
        """
        if not self.api_client:
            logger.warning("[InfoExtractor] 无API客户端，跳过提取")
            return self._empty_extraction(chapter)
        
        content = chapter.get('content', '')
        chapter_num = chapter.get('chapter_number', 0)
        
        try:
            # 构建提取prompt
            prompt = self._build_extraction_prompt(content, chapter_num)
            
            response = self.api_client.generate_content_with_retry(
                content_type="chapter_info_extraction",
                user_prompt=prompt,
                system_prompt="你是一个专业的小说信息提取助手。请从章节内容中提取结构化信息，输出JSON格式。",
                purpose=f"第{chapter_num}章信息提取"
            )
            
            # 🔥 修复：如果API客户端已经返回了解析后的dict/list，直接使用
            if isinstance(response, dict):
                logger.info(f"[InfoExtractor] 第{chapter_num}章信息提取完成（API已解析为dict）")
                return response
            elif isinstance(response, list) and response:
                logger.info(f"[InfoExtractor] 第{chapter_num}章信息提取完成（API已解析为list，取第一项）")
                return response[0] if isinstance(response[0], dict) else self._empty_extraction(chapter)
            
            result_text = response if isinstance(response, str) else str(response)
            
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                json_str = json_match.group()
                try:
                    data = json.loads(json_str)
                    logger.info(f"[InfoExtractor] 第{chapter_num}章信息提取完成")
                    return data
                except json.JSONDecodeError as e:
                    logger.warning(f"[InfoExtractor] 第{chapter_num}章JSON解析失败: {e}")
                    # 尝试清理JSON字符串
                    try:
                        # 移除可能的UTF-8 BOM和其他非标准字符
                        json_str_cleaned = json_str.strip().lstrip('\ufeff').lstrip('\u3000')
                        # 尝试替换单引号（仅替换JSON键值对中的单引号，避免破坏内容中的单引号）
                        json_str_cleaned = json_str_cleaned.replace("'", '"')
                        data = json.loads(json_str_cleaned)
                        logger.info(f"[InfoExtractor] 第{chapter_num}章信息提取完成（清理后）")
                        return data
                    except Exception as e2:
                        logger.error(f"[InfoExtractor] 第{chapter_num}章JSON清理后仍失败: {e2}")
                        return self._empty_extraction(chapter)
            else:
                logger.warning(f"[InfoExtractor] 第{chapter_num}章未返回有效JSON")
                return self._empty_extraction(chapter)
                
        except Exception as e:
            logger.error(f"[InfoExtractor] 第{chapter_num}章提取失败: {e}")
            return self._empty_extraction(chapter)
    
    def _build_extraction_prompt(self, content: str, chapter_num: int) -> str:
        """构建信息提取prompt"""
        
        # 只取前2000字作为分析（控制token）
        content_sample = content[:2000] if len(content) > 2000 else content
        
        return f"""请分析第{chapter_num}章的内容，提取以下结构化信息：

章节内容：
{content_sample}
{'' if len(content) <= 2000 else '...(内容截断，仅分析前2000字)...'}

请提取以下信息，输出JSON格式：

{{
    "new_characters": [
        {{
            "name": "角色名",
            "role": "角色定位（主角/配角/反派/盟友）",
            "description": "简要描述",
            "power_level": "实力等级（如有）"
        }}
    ],
    "character_changes": [
        {{
            "name": "角色名",
            "change": "变化描述（如：能力突破、立场转变、受伤等）",
            "details": "具体细节"
        }}
    ],
    "new_hooks": [
        {{
            "type": "钩子类型（悬念/震惊/期待/系统提示）",
            "content": "钩子内容摘要",
            "priority": "优先级（high/medium/low）"
        }}
    ],
    "resolved_hooks": [
        {{
            "content": "被回收的钩子内容",
            "resolution": "如何解决"
        }}
    ],
    "world_changes": [
        {{
            "type": "变化类型（力量体系/势力/道具/规则）",
            "description": "具体变化描述"
        }}
    ],
    "key_event": {{
        "title": "本章核心事件（20字以内）",
        "description": "事件描述",
        "impact": "影响程度（high/medium/low）"
    }},
    "power_progression": {{
        "protagonist_new_abilities": ["主角新获得的能力"],
        "power_level_change": "主角实力变化描述"
    }}
}}

注意：
1. 如果没有某类信息，返回空数组或null
2. 只提取明确出现的信息，不要推测
3. 对于"系统提示"类内容，请准确提取【】中的信息"""
    
    def _empty_extraction(self, chapter: Dict) -> Dict:
        """返回空提取结果"""
        return {
            "chapter_number": chapter.get('chapter_number'),
            "new_characters": [],
            "character_changes": [],
            "new_hooks": [],
            "resolved_hooks": [],
            "world_changes": [],
            "key_event": None,
            "power_progression": None
        }
    
    def batch_extract(self, chapters: List[Dict]) -> List[Dict]:
        """批量提取多个章节"""
        results = []
        for chapter in chapters:
            result = self.extract_from_chapter(chapter)
            results.append(result)
        return results
    
    def merge_to_world_state(self, extractions: List[Dict], 
                            current_state: Optional[Dict] = None) -> Dict:
        """
        将提取的信息合并到世界状态
        
        兼容 WorldStateManager 使用的格式:
        - protagonist: 主角状态
        - allies: 盟友字典
        - enemies: 敌人字典
        - plot_threads: 剧情线索
        - system_rules: 系统规则
        - important_items: 重要物品
        - global_events: 全局事件
        
        Args:
            extractions: 多个章节的提取结果
            current_state: 当前世界状态（可选）
            
        Returns:
            更新后的世界状态
        """
        # 🔥 确保 current_state 包含所有必需字段（WorldStateManager 格式）
        default_state = {
            "total_chapters": 0,
            "protagonist": {
                "name": "主角",
                "health": "健康",
                "injuries": [],
                "abilities_unlocked": [],
                "current_location": "",
                "relationships": {}
            },
            "allies": {},
            "enemies": {},
            "plot_threads": {},
            "system_rules": {
                "current_playing_degree": 0.0,
                "max_playing_degree": 0.0,
                "cooldown_end_chapter": 0,
                "special_states": [],
                "unlocked_skills": []
            },
            "important_items": [],
            "global_events": [],
            # 额外字段用于章节提取信息
            "timeline": [],
            "pending_hooks": [],
            "resolved_hooks": []
        }
        
        if current_state is None:
            current_state = default_state.copy()
        else:
            # 确保所有必需字段都存在
            for key, default_value in default_state.items():
                if key not in current_state:
                    current_state[key] = default_value
        
        for extraction in extractions:
            ch_num = extraction.get('chapter_number')
            
            # 🔥 修复：确保所有列表字段都是列表类型（不是None）
            new_characters = extraction.get('new_characters') or []
            character_changes = extraction.get('character_changes') or []
            new_hooks = extraction.get('new_hooks') or []
            resolved_hooks = extraction.get('resolved_hooks') or []
            world_changes = extraction.get('world_changes') or []
            
            # 合并新角色到 allies/enemies
            for char in new_characters:
                char_name = char.get('name')
                if not char_name:
                    continue
                    
                role = char.get('role', '')
                char_data = {
                    "name": char_name,
                    "health": "健康",
                    "injuries": [],
                    "abilities_unlocked": [],
                    "current_location": char.get('current_location', ''),
                    "relationships": {},
                    "description": char.get('description', ''),
                    "power_level": char.get('power_level', ''),
                    "introduced_chapter": ch_num
                }
                
                # 根据角色类型放入不同字典
                if '敌' in role or '反' in role or ' villain' in role.lower():
                    current_state['enemies'][char_name] = char_data
                else:
                    current_state['allies'][char_name] = char_data
            
            # 合并角色变化
            for change in character_changes:
                char_name = change.get('name')
                if not char_name:
                    continue
                
                # 查找角色位置
                char_dict = None
                if char_name == current_state['protagonist'].get('name'):
                    char_dict = current_state['protagonist']
                elif char_name in current_state['allies']:
                    char_dict = current_state['allies'][char_name]
                elif char_name in current_state['enemies']:
                    char_dict = current_state['enemies'][char_name]
                
                if char_dict:
                    if 'changes' not in char_dict:
                        char_dict['changes'] = []
                    char_dict['changes'].append({
                        **change,
                        "chapter": ch_num
                    })
                    
                    # 更新健康状态
                    change_desc = change.get('change', '')
                    if '重伤' in change_desc or '濒死' in change_desc:
                        char_dict['health'] = '重伤'
                    elif '轻伤' in change_desc:
                        char_dict['health'] = '轻伤'
                    elif '治愈' in change_desc or '恢复' in change_desc:
                        char_dict['health'] = '健康'
                        char_dict['injuries'] = []
            
            # 合并新钩子到 pending_hooks
            for hook in new_hooks:
                current_state['pending_hooks'].append({
                    **hook,
                    "introduced_chapter": ch_num,
                    "status": "pending"
                })
                
                # 同时创建 plot_thread（如果是重大线索）
                if hook.get('priority') == 'high':
                    hook_content = hook.get('content', '')[:20]  # 取前20字作为ID
                    thread_id = f"线索_{hook_content}"
                    if thread_id not in current_state['plot_threads']:
                        current_state['plot_threads'][thread_id] = {
                            "name": hook_content,
                            "status": "active",
                            "introduced_chapter": ch_num,
                            "last_mentioned": ch_num,
                            "priority": 8,
                            "description": hook.get('content', ''),
                            "next_trigger": "待触发"
                        }
            
            # 移出已解决的钩子
            for resolved in resolved_hooks:
                # 在pending中查找并标记为已解决
                for pending in current_state['pending_hooks']:
                    if pending.get('content') == resolved.get('content'):
                        pending['status'] = 'resolved'
                        pending['resolved_chapter'] = ch_num
                        current_state['resolved_hooks'].append(pending)
                # 从pending中移除
                current_state['pending_hooks'] = [
                    h for h in current_state['pending_hooks'] 
                    if h.get('status') != 'resolved'
                ]
            
            # 合并关键事件到时间线
            key_event = extraction.get('key_event')
            if key_event:
                current_state['timeline'].append({
                    **key_event,
                    "chapter": ch_num
                })
                # 同时添加到 global_events
                current_state['global_events'].append({
                    "chapter": ch_num,
                    "title": key_event.get('title', ''),
                    "description": key_event.get('description', ''),
                    "impact": key_event.get('impact', 'medium')
                })
            
            # 合并世界变化
            for change in world_changes:
                change_type = change.get('type', '')
                if change_type == '道具':
                    # 添加到重要物品
                    item_desc = change.get('description', '')
                    if item_desc and item_desc not in current_state['important_items']:
                        current_state['important_items'].append(item_desc)
                elif change_type == '力量体系':
                    # 更新系统规则中的技能
                    if 'new_abilities' in change:
                        for ability in change['new_abilities']:
                            if ability not in current_state['system_rules']['unlocked_skills']:
                                current_state['system_rules']['unlocked_skills'].append(ability)
                
                current_state.setdefault('world_changes', []).append({
                    **change,
                    "chapter": ch_num
                })
            
            # 更新扮演度
            power_progression = extraction.get('power_progression', {})
            if power_progression:
                playing_degree = power_progression.get('playing_degree')
                if playing_degree:
                    current_state['system_rules']['current_playing_degree'] = playing_degree
                    if playing_degree > current_state['system_rules'].get('max_playing_degree', 0):
                        current_state['system_rules']['max_playing_degree'] = playing_degree
        
        # 更新总章节数
        if extractions:
            current_state['total_chapters'] = max(
                current_state.get('total_chapters', 0),
                max(e.get('chapter_number', 0) for e in extractions)
            )
        
        return current_state
