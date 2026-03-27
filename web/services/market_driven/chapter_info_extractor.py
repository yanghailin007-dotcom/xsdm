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
            
            result_text = response if isinstance(response, str) else str(response)
            
            # 提取JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', result_text)
            if json_match:
                data = json.loads(json_match.group())
                logger.info(f"[InfoExtractor] 第{chapter_num}章信息提取完成")
                return data
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
        
        Args:
            extractions: 多个章节的提取结果
            current_state: 当前世界状态（可选）
            
        Returns:
            更新后的世界状态
        """
        if current_state is None:
            current_state = {
                "total_chapters": 0,
                "characters": {},
                "power_system": {},
                "factions": {},
                "timeline": [],
                "pending_hooks": [],
                "resolved_hooks": []
            }
        
        for extraction in extractions:
            ch_num = extraction.get('chapter_number')
            
            # 合并新角色
            for char in extraction.get('new_characters', []):
                char_name = char.get('name')
                if char_name and char_name not in current_state['characters']:
                    current_state['characters'][char_name] = {
                        **char,
                        "introduced_chapter": ch_num
                    }
            
            # 合并角色变化
            for change in extraction.get('character_changes', []):
                char_name = change.get('name')
                if char_name in current_state['characters']:
                    if 'changes' not in current_state['characters'][char_name]:
                        current_state['characters'][char_name]['changes'] = []
                    current_state['characters'][char_name]['changes'].append({
                        **change,
                        "chapter": ch_num
                    })
            
            # 合并新钩子
            for hook in extraction.get('new_hooks', []):
                current_state['pending_hooks'].append({
                    **hook,
                    "introduced_chapter": ch_num,
                    "status": "pending"
                })
            
            # 移出已解决的钩子
            for resolved in extraction.get('resolved_hooks', []):
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
            
            # 合并世界变化
            for change in extraction.get('world_changes', []):
                current_state.setdefault('world_changes', []).append({
                    **change,
                    "chapter": ch_num
                })
        
        # 更新总章节数
        if extractions:
            current_state['total_chapters'] = max(
                current_state.get('total_chapters', 0),
                max(e.get('chapter_number', 0) for e in extractions)
            )
        
        return current_state
