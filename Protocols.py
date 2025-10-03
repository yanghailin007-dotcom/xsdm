# Protocols.py
from datetime import datetime
from typing import Dict


class DataProtocol:
    """模块间数据交换协议"""
    
    @staticmethod
    def serialize_chapter_data(chapter_data: Dict) -> Dict:
        """序列化章节数据"""
        return {
            'metadata': {
                'chapter_number': chapter_data.get('chapter_number'),
                'title': chapter_data.get('chapter_title'),
                'word_count': chapter_data.get('word_count', 0),
                'timestamp': datetime.now().isoformat()
            },
            'content': chapter_data.get('content', ''),
            'design': chapter_data.get('chapter_design', {}),
            'quality': chapter_data.get('quality_assessment', {})
        }
    
    @staticmethod
    def validate_context(context: Dict) -> bool:
        """验证上下文数据"""
        required_keys = ['chapter_number', 'novel_title', 'novel_synopsis']
        return all(key in context for key in required_keys)