#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创意文件管理器 - 支持多文件创意存储和加载
"""
import os
import json
from typing import List, Dict, Optional
from datetime import datetime


class CreativeIdeasManager:
    """创意文件管理器"""
    
    def __init__(self, creative_ideas_dir: Optional[str] = None):
        """
        初始化创意管理器
        
        Args:
            creative_ideas_dir: 创意文件目录路径
        """
        if creative_ideas_dir is None:
            # 默认使用项目根目录下的 data/creative_ideas
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_dir))
            creative_ideas_dir = os.path.join(project_root, "data", "creative_ideas")
        
        self.creative_ideas_dir = creative_ideas_dir
        self.legacy_file = os.path.join(creative_ideas_dir, "novel_ideas.txt")
        
        # 缓存加载的创意
        self._cache: Optional[Dict] = None
        
    def load_creative_ideas(self, force_reload: bool = False) -> Dict:
        """
        加载创意数据
        
        优先级：
        1. 如果存在 index.json（多文件模式），使用多文件模式加载
        2. 否则，尝试从 novel_ideas.txt 加载（单文件模式，向后兼容）
        
        Args:
            force_reload: 是否强制重新加载（忽略缓存）
            
        Returns:
            创意数据字典，格式为：
            {
                "format": "multi_file" or "single_file",
                "creativeWorks": [...]
            }
        """
        if self._cache is not None and not force_reload:
            return self._cache
        
        print(f"📂 创意管理器: 加载创意数据...")
        
        # 检查目录中是否有JSON文件（多文件模式）
        json_files = self._get_creative_json_files()
        
        if json_files:
            print(f"  ✅ 检测到 {len(json_files)} 个创意JSON文件，使用多文件模式")
            self._cache = self._load_multi_file_mode()
        elif os.path.exists(self.legacy_file):
            print(f"  ✅ 检测到 novel_ideas.txt，使用单文件模式（向后兼容）")
            self._cache = self._load_single_file_mode()
        else:
            print(f"  ⚠️  未找到创意文件，返回空数据")
            self._cache = {
                "format": "none",
                "creativeWorks": []
            }
        
        return self._cache
    
    def _get_creative_json_files(self) -> List[str]:
        """获取目录中所有创意JSON文件（排除index.json）"""
        if not os.path.exists(self.creative_ideas_dir):
            return []
        
        json_files = []
        for filename in os.listdir(self.creative_ideas_dir):
            if filename.endswith('.json') and filename != 'index.json':
                filepath = os.path.join(self.creative_ideas_dir, filename)
                if os.path.isfile(filepath):
                    json_files.append(filepath)
        
        # 按文件名排序，确保顺序一致
        json_files.sort()
        return json_files
    
    def _load_multi_file_mode(self) -> Dict:
        """多文件模式加载（直接扫描目录，无需索引文件）"""
        try:
            json_files = self._get_creative_json_files()
            creative_ideas = []
            
            for filepath in json_files:
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        idea_data = json.load(f)
                    creative_ideas.append(idea_data)
                except Exception as e:
                    filename = os.path.basename(filepath)
                    print(f"  ⚠️  加载创意文件失败 {filename}: {e}")
            
            print(f"  ✅ 多文件模式加载成功，共 {len(creative_ideas)} 个创意")
            
            return {
                "format": "multi_file",
                "total_count": len(creative_ideas),
                "creativeWorks": creative_ideas
            }
            
        except Exception as e:
            print(f"  ❌ 多文件模式加载失败: {e}")
            print(f"  🔄 尝试回退到单文件模式...")
            return self._load_single_file_mode()
    
    def _load_single_file_mode(self) -> Dict:
        """单文件模式加载（向后兼容）"""
        try:
            with open(self.legacy_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = json.loads(content)
            creative_works = data.get("creativeWorks", [])
            
            print(f"  ✅ 单文件模式加载成功，共 {len(creative_works)} 个创意")
            
            return {
                "format": "single_file",
                "creativeWorks": creative_works
            }
            
        except Exception as e:
            print(f"  ❌ 单文件模式加载失败: {e}")
            return {
                "format": "error",
                "error": str(e),
                "creativeWorks": []
            }
    
    def get_creative_idea(self, idea_id: int) -> Optional[Dict]:
        """
        获取指定ID的创意
        
        Args:
            idea_id: 创意ID（从1开始）
            
        Returns:
            创意数据字典，如果不存在则返回None
        """
        data = self.load_creative_ideas()
        creative_works = data.get("creativeWorks", [])
        
        if idea_id < 1 or idea_id > len(creative_works):
            return None
        
        return creative_works[idea_id - 1]
    
    def get_all_creative_ideas(self) -> List[Dict]:
        """获取所有创意列表"""
        data = self.load_creative_ideas()
        return data.get("creativeWorks", [])
    
    def get_creative_count(self) -> int:
        """获取创意数量"""
        data = self.load_creative_ideas()
        return len(data.get("creativeWorks", []))
    
    def add_creative_idea(self, creative_data: Dict) -> int:
        """
        添加新创意
        
        Args:
            creative_data: 创意数据字典
            
        Returns:
            新创意的ID
        """
        data = self.load_creative_ideas(force_reload=True)
        creative_works = data.get("creativeWorks", [])
        
        # 分配新ID
        new_id = len(creative_works) + 1
        creative_data["lastUpdated"] = datetime.now().isoformat()
        
        # 根据当前模式决定保存方式
        if data.get("format") == "multi_file":
            # 多文件模式：保存为独立文件
            novel_title = creative_data.get("novelTitle", f"创意{new_id}")
            safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_')).strip()
            if not safe_title:
                safe_title = f"creative_idea_{new_id}"
            
            filename = f"{new_id:03d}_{safe_title}.json"
            filepath = os.path.join(self.creative_ideas_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(creative_data, f, ensure_ascii=False, indent=2)
            
        else:
            # 单文件模式：追加到现有文件
            creative_works.append(creative_data)
            
            with open(self.legacy_file, 'w', encoding='utf-8') as f:
                json.dump({"creativeWorks": creative_works}, f, ensure_ascii=False, indent=2)
        
        # 清除缓存
        self._cache = None
        
        return new_id
    
    def update_creative_idea(self, idea_id: int, updated_data: Dict) -> bool:
        """
        更新指定ID的创意
        
        Args:
            idea_id: 创意ID
            updated_data: 更新的创意数据
            
        Returns:
            是否成功
        """
        data = self.load_creative_ideas(force_reload=True)
        creative_works = data.get("creativeWorks", [])
        
        if idea_id < 1 or idea_id > len(creative_works):
            return False
        
        # 更新数据
        updated_data["lastUpdated"] = datetime.now().isoformat()
        
        if data.get("format") == "multi_file":
            # 多文件模式：更新独立文件
            # 获取JSON文件列表
            json_files = self._get_creative_json_files()
            
            if idea_id - 1 < len(json_files):
                filepath = json_files[idea_id - 1]
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(updated_data, f, ensure_ascii=False, indent=2)
            else:
                return False
            
        else:
            # 单文件模式：更新数组中的项
            creative_works[idea_id - 1] = updated_data
            
            with open(self.legacy_file, 'w', encoding='utf-8') as f:
                json.dump({"creativeWorks": creative_works}, f, ensure_ascii=False, indent=2)
        
        # 清除缓存
        self._cache = None
        
        return True
    
    def delete_creative_idea(self, idea_id: int) -> bool:
        """
        删除指定ID的创意
        
        Args:
            idea_id: 创意ID
            
        Returns:
            是否成功
        """
        data = self.load_creative_ideas(force_reload=True)
        creative_works = data.get("creativeWorks", [])
        
        if idea_id < 1 or idea_id > len(creative_works):
            return False
        
        if data.get("format") == "multi_file":
            # 多文件模式：删除文件
            json_files = self._get_creative_json_files()
            
            if idea_id - 1 < len(json_files):
                filepath = json_files[idea_id - 1]
                if os.path.exists(filepath):
                    os.remove(filepath)
            else:
                return False
            
        else:
            # 单文件模式：从数组中移除
            creative_works.pop(idea_id - 1)
            
            with open(self.legacy_file, 'w', encoding='utf-8') as f:
                json.dump({"creativeWorks": creative_works}, f, ensure_ascii=False, indent=2)
        
        # 清除缓存
        self._cache = None
        
        return True
    
    def get_storage_info(self) -> Dict:
        """获取存储信息"""
        data = self.load_creative_ideas()
        
        info = {
            "format": data.get("format", "unknown"),
            "total_count": len(data.get("creativeWorks", [])),
            "directory": self.creative_ideas_dir
        }
        
        if data.get("format") == "multi_file":
            json_files = self._get_creative_json_files()
            info["files"] = [os.path.basename(f) for f in json_files]
            info["legacy_file_exists"] = os.path.exists(self.legacy_file)
        
        return info