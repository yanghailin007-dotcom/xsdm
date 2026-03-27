# -*- coding: utf-8 -*-
"""
Unified Project Manager
统一项目信息管理

市场导向模式和自由创作模式使用相同的项目信息结构
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class UnifiedProjectManager:
    """
    统一项目信息管理器
    两种模式使用相同的数据结构
    """
    
    @staticmethod
    def create_project_info(novel_title: str, generation_mode: str = "market_driven") -> Dict:
        """
        创建统一的项目信息结构
        
        Args:
            novel_title: 小说标题
            generation_mode: 生成模式 (market_driven / creative)
            
        Returns:
            项目信息字典
        """
        return {
            # ========== 基础信息（两种模式都有）==========
            "novel_title": novel_title,
            "novel_synopsis": "",  # 简介
            "genre": "",  # 题材
            "sub_genre": "",  # 子题材
            "target_platform": "番茄小说",
            "generation_mode": generation_mode,  # 区分生成模式
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            
            # ========== 作者信息（上传用）==========
            "author_info": {
                "author_name": "",
                "author_id": "",
                "author_statement": ""  # 作者的话
            },
            
            # ========== 分类标签（上传用，番茄要求）==========
            "category_tags": {
                "main_category": "",      # 主分类：都市/玄幻/科幻...
                "sub_category": "",       # 子分类：都市生活/异术超能...
                "tags": [],               # 标签：最多5个
                "target_audience": "男频", # 受众
                "content_rating": "全年龄"  # 分级
            },
            
            # ========== 生成元数据 ==========
            "generation_metadata": {
                "generated_at": datetime.now().isoformat(),
                "total_chapters": 0,
                "total_words": 0,
                "ai_model": "gpt-4",
                
                # 模式特定信息
                "mode_specific": {}
            },
            
            # ========== 产物映射（第一阶段）==========
            "products_mapping": {
                "writing_style_guide": "phase_one_products/写作风格指南.json",
                "market_analysis": "phase_one_products/市场分析.json",
                "core_worldview": "phase_one_products/世界观设定.json",
                "faction_system": "phase_one_products/势力设定.json",
                "character_design": "phase_one_products/角色设计.json",
                "global_growth_plan": "phase_one_products/升级路线.json",
                "stage_writing_plans": "phase_one_products/阶段计划.json",
                "emotional_blueprint": "phase_one_products/情绪蓝图.json",
                "expectation_mapping": "phase_one_products/期待感映射.json",
                "plan": "phase_one_products/完整方案.json",
                "emotion_curve": "phase_one_products/情绪曲线.json"
            },
            
            # ========== 章节索引 ==========
            "chapters_index": [],
            
            # ========== 质量评估 ==========
            "quality_assessment": {
                "overall_score": 0,
                "commercial_score": 0,  # 市场导向模式特有
                "readiness": "not_ready",
                "assessed_at": None
            },
            
            # ========== 上传相关信息（番茄）==========
            "upload_info": {
                "fanqie_book_id": None,
                "upload_status": "not_uploaded",  # not_uploaded / uploaded / published
                "upload_time": None,
                "published_chapters": 0,
                "contract_status": "none"  # none / signed
            }
        }
    
    @staticmethod
    def save_project_info(base_path: Path, project_info: Dict):
        """保存项目信息"""
        project_info["updated_at"] = datetime.now().isoformat()
        
        file_path = base_path / "project_info.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(project_info, f, ensure_ascii=False, indent=2)
        
        logger.info(f"项目信息已保存: {file_path}")
    
    @staticmethod
    def load_project_info(base_path: Path) -> Optional[Dict]:
        """加载项目信息"""
        file_path = base_path / "project_info.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载项目信息失败: {e}")
            return None
    
    @staticmethod
    def add_chapter_to_index(project_info: Dict, chapter_metadata: Dict):
        """添加章节到索引"""
        chapter_entry = {
            "chapter_number": chapter_metadata["chapter_number"],
            "title": chapter_metadata["title"],
            "word_count": chapter_metadata["word_count"],
            "file": f"chapters/chapter_{chapter_metadata['chapter_number']:03d}.json",
            "quality_score": chapter_metadata.get("quality_score", 0),
            "generated_at": chapter_metadata.get("generated_at", datetime.now().isoformat())
        }
        
        # 查找是否已存在
        existing = next(
            (c for c in project_info["chapters_index"] if c["chapter_number"] == chapter_entry["chapter_number"]),
            None
        )
        
        if existing:
            # 更新
            existing.update(chapter_entry)
        else:
            # 添加
            project_info["chapters_index"].append(chapter_entry)
        
        # 排序
        project_info["chapters_index"].sort(key=lambda x: x["chapter_number"])
        
        # 更新统计
        project_info["generation_metadata"]["total_chapters"] = len(project_info["chapters_index"])
        project_info["generation_metadata"]["total_words"] = sum(
            c["word_count"] for c in project_info["chapters_index"]
        )
    
    @staticmethod
    def set_mode_specific_info(project_info: Dict, mode: str, info: Dict):
        """设置模式特定信息"""
        project_info["generation_metadata"]["mode_specific"] = {
            "mode": mode,
            "info": info
        }
    
    @staticmethod
    def get_upload_data(project_info: Dict) -> Dict:
        """
        获取上传数据（两种模式统一接口）
        
        Returns:
            番茄上传所需的数据
        """
        return {
            # 基本信息
            "title": project_info["novel_title"],
            "synopsis": project_info["novel_synopsis"],
            
            # 分类标签
            "category": project_info["category_tags"]["main_category"],
            "sub_category": project_info["category_tags"]["sub_category"],
            "tags": project_info["category_tags"]["tags"],
            
            # 作者信息
            "author_name": project_info["author_info"]["author_name"],
            "author_statement": project_info["author_info"]["author_statement"],
            
            # 章节
            "chapters": [
                {
                    "number": c["chapter_number"],
                    "title": c["title"]
                }
                for c in project_info["chapters_index"]
            ]
        }


class FanqieUploadAdapter:
    """
    番茄上传适配器
    将统一项目信息转换为番茄上传格式
    """
    
    # 番茄分类映射
    CATEGORY_MAPPING = {
        "神豪文": {"main": "都市", "sub": "都市生活", "tags": ["神豪", "系统", "爽文"]},
        "国运文": {"main": "都市", "sub": "异术超能", "tags": ["国运", "直播", "爽文"]},
        "奶爸文": {"main": "都市", "sub": "都市生活", "tags": ["奶爸", "萌宝", "温馨"]},
        "签到文": {"main": "都市", "sub": "都市异能", "tags": ["签到", "系统", "爽文"]},
        "末日求生": {"main": "科幻", "sub": "末世危机", "tags": ["末日", "囤货", "求生"]},
        "灵气复苏": {"main": "都市", "sub": "异术超能", "tags": ["灵气复苏", "修炼", "爽文"]},
        "四合院": {"main": "都市", "sub": "都市生活", "tags": ["四合院", "年代", "日常"]}
    }
    
    @classmethod
    def auto_fill_category_tags(cls, project_info: Dict, genre: str):
        """自动填充分类标签"""
        mapping = cls.CATEGORY_MAPPING.get(genre, {
            "main": "都市",
            "sub": "都市生活",
            "tags": ["爽文", "系统"]
        })
        
        project_info["category_tags"]["main_category"] = mapping["main"]
        project_info["category_tags"]["sub_category"] = mapping["sub"]
        project_info["category_tags"]["tags"] = mapping["tags"]
    
    @classmethod
    def prepare_upload_payload(cls, project_info: Dict, chapters_content: List[Dict]) -> Dict:
        """
        准备番茄上传数据
        
        Args:
            project_info: 项目信息
            chapters_content: 章节内容列表
            
        Returns:
            番茄上传所需的完整数据
        """
        return {
            "book_info": {
                "title": project_info["novel_title"],
                "synopsis": project_info["novel_synopsis"],
                "category": project_info["category_tags"]["main_category"],
                "sub_category": project_info["category_tags"]["sub_category"],
                "tags": project_info["category_tags"]["tags"],
                "author_name": project_info["author_info"]["author_name"],
                "is_original": True,
                "is_exclusive": True
            },
            "chapters": [
                {
                    "chapter_number": ch["chapter_number"],
                    "title": ch["title"],
                    "content": ch["content"]
                }
                for ch in chapters_content
            ],
            "publish_settings": {
                "initial_chapters": min(3, len(chapters_content)),
                "update_frequency": "daily",
                "chapters_per_update": 2
            }
        }


class ProjectDirectoryManager:
    """
    项目目录管理器
    统一的项目文件结构
    """
    
    @staticmethod
    def create_project_structure(base_path: Path, novel_title: str, username: str = None) -> Path:
        """
        创建统一的项目目录结构
        
        Args:
            base_path: 基础路径（如"小说项目"）
            novel_title: 小说标题
            username: 用户名（如果提供，则创建在用户子目录下）
        
        Returns:
            项目根目录路径
        """
        # 🔥 如果提供了用户名，创建用户子目录
        if username:
            user_path = base_path / username
            user_path.mkdir(parents=True, exist_ok=True)
            project_path = user_path / novel_title
        else:
            # 兼容旧版：直接放在根目录
            project_path = base_path / novel_title
        
        # 创建目录
        (project_path / "phase_one_products").mkdir(parents=True, exist_ok=True)
        (project_path / "chapters").mkdir(exist_ok=True)
        (project_path / "uploads").mkdir(exist_ok=True)
        (project_path / "assets").mkdir(exist_ok=True)
        
        logger.info(f"项目目录已创建: {project_path} (用户: {username or '根目录'})")
        return project_path
    
    @staticmethod
    def get_chapter_path(project_path: Path, chapter_number: int) -> Path:
        """获取章节文件路径"""
        return project_path / "chapters" / f"chapter_{chapter_number:03d}.json"
    
    @staticmethod
    def get_product_path(project_path: Path, product_name: str) -> Path:
        """获取产物文件路径"""
        product_files = {
            "writing_style_guide": "phase_one_products/写作风格指南.json",
            "market_analysis": "phase_one_products/市场分析.json",
            "core_worldview": "phase_one_products/世界观设定.json",
            "faction_system": "phase_one_products/势力设定.json",
            "character_design": "phase_one_products/角色设计.json",
            "global_growth_plan": "phase_one_products/升级路线.json",
            "stage_writing_plans": "phase_one_products/阶段计划.json",
            "emotional_blueprint": "phase_one_products/情绪蓝图.json",
            "expectation_mapping": "phase_one_products/期待感映射.json",
            "plan": "phase_one_products/完整方案.json",
            "emotion_curve": "phase_one_products/情绪曲线.json"
        }
        
        relative_path = product_files.get(product_name, f"phase_one_products/{product_name}.json")
        return project_path / relative_path


# 便捷函数
def create_unified_project(novel_title: str, generation_mode: str, genre: str = "", username: str = None) -> Path:
    """
    便捷函数：创建统一项目
    
    Args:
        novel_title: 小说标题
        generation_mode: 生成模式
        genre: 题材（用于自动填充分类标签）
        username: 用户名（如果提供，项目会创建在用户子目录下）
        
    Returns:
        项目路径
    """
    # 🔥 如果没有提供用户名，尝试从Flask session获取
    if username is None:
        try:
            from flask import session
            username = session.get('user') or session.get('username') or 'anonymous'
        except:
            username = 'anonymous'
    
    # 创建目录
    base_path = Path("小说项目")
    project_path = ProjectDirectoryManager.create_project_structure(base_path, novel_title, username)
    
    # 创建项目信息
    project_info = UnifiedProjectManager.create_project_info(novel_title, generation_mode)
    
    # 🔥 记录创建者
    project_info["created_by"] = username
    
    # 自动填充分类标签
    if genre:
        FanqieUploadAdapter.auto_fill_category_tags(project_info, genre)
        project_info["genre"] = genre
    
    # 保存
    UnifiedProjectManager.save_project_info(project_path, project_info)
    
    logger.info(f"统一项目已创建: {project_path} (创建者: {username})")
    return project_path


def load_and_prepare_upload(novel_title: str) -> Optional[Dict]:
    """
    便捷函数：加载项目并准备上传数据
    """
    base_path = Path("小说项目") / novel_title
    
    # 加载项目信息
    project_info = UnifiedProjectManager.load_project_info(base_path)
    if not project_info:
        return None
    
    # 加载章节内容
    chapters_content = []
    for ch_entry in project_info["chapters_index"]:
        chapter_path = base_path / ch_entry["file"]
        if chapter_path.exists():
            with open(chapter_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                chapters_content.append({
                    "chapter_number": chapter_data["chapter_number"],
                    "title": chapter_data["title"],
                    "content": chapter_data["content"]
                })
    
    # 准备上传数据
    upload_data = FanqieUploadAdapter.prepare_upload_payload(project_info, chapters_content)
    
    return upload_data
