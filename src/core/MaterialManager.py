"""材料管理器 - 统一管理小说生成过程中的所有材料"""

import os
import json
import re
import shutil
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

class MaterialManager:
    """材料管理器 - 统一管理小说生成过程中的所有材料"""
    
    def __init__(self, novel_title: str):
        """
        初始化材料管理器
        
        Args:
            novel_title: 小说标题
        """
        self.novel_title = novel_title
        self.safe_title = self._sanitize_filename(novel_title)
        
        # 🔥 创建基础目录结构（使用用户隔离路径）
        try:
            from web.utils.path_utils import get_user_novel_dir
            user_dir = get_user_novel_dir(create=True)
            self.base_dir = user_dir / self.safe_title
        except Exception:
            # 如果没有 Flask 上下文，使用默认路径
            self.base_dir = Path("小说项目") / self.safe_title
        
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建子目录
        self.materials_dir = self.base_dir / "生成材料"
        self.plans_dir = self.base_dir / "写作计划"
        self.data_dir = self.base_dir / "数据文件"
        self.export_dir = self.base_dir / "导出包"
        
        for dir_path in [self.materials_dir, self.plans_dir, self.data_dir, self.export_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # 时间标签配置
        self.timestamp_format = "%Y%m%d_%H%M%S"
        self.date_format = "%Y-%m-%d"
        
        # 文件命名规则
        self.naming_rules = {
            # 核心生成材料
            "project_info": "{safe_title}_项目信息_{timestamp}.json",
            "chapter": "{safe_title}_章节_第{chapter:03d}章_{title}_{timestamp}.txt",
            "chapter_json": "{safe_title}_章节_第{chapter:03d}章_{title}_{timestamp}.json",
            
            # 写作计划类
            "market_analysis": "{safe_title}_市场分析_{timestamp}.json",
            "worldview": "{safe_title}_世界观_{timestamp}.json",
            "character_design": "{safe_title}_角色设计_{timestamp}.json",
            "faction_system": "{safe_title}_势力系统.json",  # 🔥 新增：势力系统命名规则（不带时间戳，固定文件名）
            "stage_plan": "{safe_title}_阶段计划_{stage_name}_{timestamp}.json",
            "writing_style": "{safe_title}_写作风格指南_{timestamp}.json",
            "growth_plan": "{safe_title}_成长规划_{timestamp}.json",
            
            # 生成过程记录
            "generation_log": "{safe_title}_生成日志_{timestamp}.json",
            "api_calls": "{safe_title}_API调用记录_{timestamp}.json",
            "quality_assessment": "{safe_title}_质量评估_{timestamp}.json",
            "events_log": "{safe_title}_事件记录_{timestamp}.json",
            
            # 素引和数据文件
            "index": "{safe_title}_材料索引_{timestamp}.json",
            "manifest": "{safe_title}_文件清单_{timestamp}.json",
            "search_index": "{safe_title}_搜索索引_{timestamp}.json"
        }
        
        # 材料类型映射
        self.material_types = {
            "项目信息": "project_info",
            "章节内容": "chapter",
            "写作计划": "plans",
            "市场分析": "market_analysis", 
            "世界观": "worldview",
            "角色设计": "character_design",
            "阶段计划": "stage_plan",
            "写作风格": "writing_style",
            "成长规划": "growth_plan",
            "生成日志": "generation_log",
            "API调用": "api_calls",
            "质量评估": "quality_assessment",
            "事件记录": "events_log",
            "原始数据": "raw_data"
        }
        
        # 材料元数据结构
        self.material_metadata = {
            "novel_title": novel_title,
            "created_time": "",
            "updated_time": "",
            "material_type": "",
            "file_path": "",
            "file_size": 0,
            "checksum": "",
            "generation_stage": "",
            "related_chapters": [],
            "content_summary": "",
            "tags": []
        }
        
        self.logger = self._get_logger()
        
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的特殊字符"""
        # 移除或替换文件名中的特殊字符
        sanitized = re.sub(r'[\\/*?:"<>|]', '_', filename)
        # 移除多余的连续下划线
        sanitized = re.sub(r'_+', '_', sanitized)
        # 移除首尾的下划线
        sanitized = sanitized.strip('_')
        return sanitized
    
    def _get_logger(self):
        """获取日志记录器"""
        try:
            from src.utils.logger import get_logger
            return get_logger("MaterialManager")
        except Exception:
            import logging
            return logging.getLogger("MaterialManager")
    
    def get_timestamp(self, include_date: bool = False) -> str:
        """获取时间戳"""
        if include_date:
            return datetime.now().strftime(self.date_format)
        return datetime.now().strftime(self.timestamp_format)
    
    def format_filename(self, material_type: str, **kwargs) -> str:
        """
        格式化文件名
        
        Args:
            material_type: 材料类型
            **kwargs: 其他参数
            
        Returns:
            str: 格式化后的文件名
        """
        safe_title = self.safe_title
        
        # 获取对应类型的命名规则
        filename_template = self.naming_rules.get(material_type)
        if not filename_template:
            # 如果没有对应规则，使用默认规则
            filename_template = f"{safe_title}_{material_type}_{self.get_timestamp()}.json"
        
        # 替换模板变量
        filename = filename_template.format(
            safe_title=safe_title,
            timestamp=self.get_timestamp(),
            **kwargs
        )
        
        return filename
    
    def create_material(self, material_type: str, content: Any, **kwargs) -> Dict:
        """
        创建材料文件并记录元数据
        
        Args:
            material_type: 材料类型
            content: 内容数据
            **kwargs: 其他参数
            
        Returns:
            Dict: 创建结果信息
        """
        timestamp = self.get_timestamp()
        
        # 生成文件名（不传递timestamp，让format_filename内部生成）
        filename = self.format_filename(material_type, **kwargs)
        file_path = self._get_file_path(material_type, filename)
        
        try:
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据类型选择保存方式
            if material_type in ["章节内容", "chapter_json"]:
                # 章节内容使用特殊处理
                result = self._save_chapter_material(
                    material_type, content, filename, file_path, timestamp, **kwargs
                )
            elif material_type in ["项目信息", "manifest", "index", "search_index"]:
                # 项目信息使用JSON格式
                result = self._save_json_material(
                    material_type, content, filename, file_path, timestamp, **kwargs
                )
            else:
                # 其他类型使用JSON格式
                result = self._save_json_material(
                    material_type, content, filename, file_path, timestamp, **kwargs
                )
            
            if result["success"]:
                # 记录到索引
                self._record_material_index(material_type, result["file_path"], timestamp)
                
            return result
                
        except Exception as e:
            self.logger.error(f"创建材料文件失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "file_path": str(file_path),
                "material_type": material_type
            }
    
    def _save_chapter_material(self, material_type: str, content: Dict, 
                              filename: str, file_path: Path, 
                              timestamp: str, **kwargs) -> Dict:
        """保存章节材料（支持文本和JSON格式）"""
        try:
            chapter_num = kwargs.get('chapter_number', 1)
            
            # 保存JSON格式
            json_filename = filename.replace('.txt', '.json')
            json_path = file_path.parent / json_filename
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            # 保存文本格式（正文）
            txt_filename = filename
            txt_path = file_path
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                if isinstance(content, dict):
                    # 如果是字典，提取内容字段
                    chapter_content = content.get('content', '')
                else:
                    chapter_content = str(content)
                f.write(chapter_content)
            
            return {
                "success": True,
                "file_path": str(file_path),
                "json_path": str(json_path),
                "material_type": material_type,
                "chapter_number": chapter_num
            }
            
        except Exception as e:
            self.logger.error(f"保存章节材料失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "material_type": material_type
            }
    
    def _save_json_material(self, material_type: str, content: Any, 
                         filename: str, file_path: Path, 
                         timestamp: str, **kwargs) -> Dict:
        """保存JSON格式材料"""
        try:
            # 确保内容是可序列化的
            if not isinstance(content, (dict, list, str, int, float, bool)):
                if isinstance(content, object):
                    content = content.__dict__
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            
            # 计算文件大小
            file_size = file_path.stat().st_size if file_path.exists() else 0
            
            return {
                "success": True,
                "file_path": str(file_path),
                "material_type": material_type,
                "file_size": file_size,
                "checksum": self._calculate_checksum(file_path)
            }
            
        except Exception as e:
            self.logger.error(f"保存JSON材料失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "material_type": material_type
            }
    
    def _get_file_path(self, material_type: str, filename: str) -> Path:
        """获取文件路径"""
        if material_type == "章节内容":
            return self.materials_dir / filename
        elif material_type in self.material_types:
            type_dir = self.base_dir / self.material_types[material_type]
            return type_dir / filename
        else:
            # 默认放在生成材料目录
            return self.materials_dir / filename
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """计算文件校验和"""
        try:
            import hashlib
            
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception:
            return ""
    
    def _record_material_index(self, material_type: str, file_path: str, timestamp: str):
        """记录材料到索引"""
        index_file = self.base_dir / self.format_filename("index")
        
        # 加载现有索引
        index_data = {}
        if index_file.exists():
            try:
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            except Exception:
                index_data = {}
        
        # 添加新记录
        record = {
            "material_type": material_type,
            "file_path": str(file_path),
            "created_time": timestamp,
            "updated_time": timestamp,
            "novel_title": self.novel_title
        }
        
        # 按时间戳排序（最新的在前面）
        records = index_data.get("materials", [])
        records.insert(0, record)
        
        # 保存索引
        index_data["materials"] = records
        index_data["last_updated"] = timestamp
        index_data["total_materials"] = len(records)
        
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index_data, f, ensure_ascii=False, indent=2)
    
    def get_material_by_id(self, material_id: str) -> Optional[Dict]:
        """根据ID获取材料"""
        try:
            # 解析ID格式：书名_功能_时间戳.扩展名
            parts = material_id.split('_')
            if len(parts) < 3:
                return None
                
            # 提取时间戳和扩展名
            timestamp_part = parts[-2]  # 倒数第二个下划线后的部分
            extension = parts[-1]  # 最后一个下划线后的部分
            
            # 查找对应类型的索引文件
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return None
                
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            # 在材料中查找匹配的记录
            materials = index_data.get("materials", [])
            for material in materials:
                if (material.get("material_id") == material_id or 
                    material.get("novel_title") == self.novel_title):
                    return material
            
            return None
            
        except Exception as e:
            self.logger.error(f"根据ID获取材料失败: {e}")
            return None
    
    def list_materials_by_type(self, material_type: str) -> List[Dict]:
        """列出指定类型的所有材料"""
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return []
                
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            # 过滤出指定类型的材料
            filtered_materials = [
                material for material in materials 
                if material.get("material_type") == material_type
            ]
            
            # 按创建时间倒序排序
            filtered_materials.sort(
                key=lambda x: x.get("created_time", ""), 
                reverse=True
            )
            
            return filtered_materials
            
        except Exception as e:
            self.logger.error(f"列出材料失败: {e}")
            return []
    
    def get_materials_by_time_range(self, start_time: str, end_time: str = None) -> List[Dict]:
        """获取时间范围内的材料"""
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return []
                
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            # 过滤时间范围
            if start_time:
                start_dt = datetime.strptime(start_time, self.date_format)
                materials = [
                    material for material in materials
                    if datetime.strptime(material["created_time"], self.date_format) >= start_dt
                ]
            
            if end_time:
                end_dt = datetime.strptime(end_time, self.date_format)
                materials = [
                    material for material in materials
                    if datetime.strptime(material["created_time"], self.date_format) <= end_dt
                ]
            
            return materials
            
        except Exception as e:
            self.logger.error(f"获取时间范围材料失败: {e}")
            return []
    
    def search_materials(self, keyword: str, material_types: List[str] = None) -> List[Dict]:
        """搜索材料"""
        try:
            index_file = self.base_dir / self.format_filename("search_index")
            
            if not index_file.exists():
                return []
                
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            # 过滤关键词
            if keyword:
                keyword_lower = keyword.lower()
                materials = [
                    material for material in materials
                    if (keyword_lower in material.get("content_summary", "").lower() or
                     keyword_lower in material.get("novel_title", "").lower() or
                     keyword_lower in material.get("tags", []).lower())
                ]
            
            if material_types:
                materials = [
                    material for material in materials
                    if material.get("material_type") in material_types
                ]
            
            # 按相关性排序
            materials.sort(
                key=lambda x: x.get("relevance_score", 0), 
                reverse=True
            )
            
            return materials
            
        except Exception as e:
            self.logger.error(f"搜索材料失败: {e}")
            return []
    
    def create_material_bundle(self, bundle_name: str, 
                          material_types: List[str] = None,
                          time_range: Tuple[str, str] = None,
                          include_metadata: bool = True) -> str:
        """创建材料包"""
        timestamp = self.get_timestamp()
        
        # 生成材料包文件名
        bundle_filename = f"{self.safe_title}_{bundle_name}_{timestamp}.zip"
        bundle_path = self.export_dir / bundle_filename
        
        try:
            import zipfile
            with zipfile.ZipFile(bundle_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 获取指定类型的材料
                materials_to_pack = []
                
                if material_types:
                    materials_to_pack = []
                    for material_type in material_types:
                        type_materials = self.list_materials_by_type(material_type)
                        if time_range:
                            start_time, end_time = time_range
                            for material in type_materials:
                                material_time = datetime.strptime(material["created_time"], self.date_format)
                                if start_time and end_time:
                                    start_dt = datetime.strptime(start_time, self.date_format)
                                    end_dt = datetime.strptime(end_time, self.date_format)
                                    if start_dt <= material_time <= end_dt:
                                        materials_to_pack.append(material)
                        else:
                            materials_to_pack.extend(type_materials)
                else:
                    materials_to_pack = self.list_materials_by_time_range(*time_range) if time_range else []
                
                # 为每个材料创建README
                bundle_metadata = {
                    "bundle_name": bundle_name,
                    "novel_title": self.novel_title,
                    "created_time": timestamp,
                    "total_materials": len(materials_to_pack),
                    "bundle_description": f"{self.novel_title} - {bundle_name}",
                    "included_types": material_types or "全部",
                    "time_range": time_range or "全部",
                    "version": "1.0"
                }
                
                # 添加README
                readme_content = f"""# {bundle_name}

生成时间: {timestamp}
小说标题: {self.novel_title}

材料总数: {len(materials_to_pack)}

包含的材料类型:
"""
                
                if material_types:
                    for mat_type in material_types:
                        count = len([m for m in materials_to_pack if m.get("material_type") == mat_type])
                        readme_content += f"- {mat_type}: {count}个\n"
                
                readme_content += "\n文件清单:\n"
                for material in materials_to_pack:
                    readme_content += f"- {material['file_path']}\n"
                
                readme_content += f"\n元数据:\n{json.dumps(bundle_metadata, ensure_ascii=False, indent=2)}"
                
                zipf.writestr("README.txt", readme_content)
                
                # 添加文件到ZIP
                for material in materials_to_pack:
                    file_path = Path(material["file_path"])
                    if file_path.exists():
                        zipf.write(file_path, file_path.name)
                
                return {
                    "success": True,
                    "bundle_path": str(bundle_path),
                    "bundle_name": bundle_filename,
                    "total_materials": len(materials_to_pack)
                }
                
        except Exception as e:
            self.logger.error(f"创建材料包失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "bundle_name": bundle_filename
            }
    
    def export_novel_package(self, export_type: str = "complete") -> str:
        """导出完整的小说包"""
        timestamp = self.get_timestamp()
        
        package_name = f"{self.safe_title}_完整包_{timestamp}"
        package_path = self.export_dir / package_name
        
        try:
            import shutil
            
            if export_type == "complete":
                # 导出完整包
                package_name = f"{self.safe_title}_完整包_{timestamp}"
                package_path = self.export_dir / package_name
                package_dir = self.base_dir
                
                # 创建临时目录
                temp_dir = self.base_dir / f"temp_export_{timestamp}"
                temp_dir.mkdir(exist_ok=True)
                
                # 复制所有重要文件到临时目录
                files_to_export = [
                    (self.base_dir / f"{self.safe_title}_项目信息.json", "项目信息"),
                    (self.materials_dir, "生成材料"),
                    (self.plans_dir, "写作计划"),
                    (self.data_dir, "数据文件"),
                    (self.export_dir, "导出包")
                ]
                
                for source_path, dest_name in files_to_export:
                    if isinstance(source_path, Path):
                        dest_path = temp_dir / dest_name
                    elif isinstance(source_path, str):
                        dest_path = temp_dir / Path(source_path).name
                    else:
                        continue
                    
                    if dest_path.exists():
                        shutil.rmtree(dest_path)
                    shutil.copytree(source_path, dest_path)
                
                # 压缩到ZIP文件
                zip_filename = f"{self.safe_title}_完整包_{timestamp}.zip"
                zip_path = self.export_dir / zip_filename
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = Path(root) / file
                            if file_path.is_file():
                                zipf.write(file_path, file_path.relative_to(temp_dir))
                
                # 删除临时目录
                shutil.rmtree(temp_dir)
                
                return {
                    "success": True,
                    "package_path": str(zip_path),
                    "package_name": zip_filename,
                    "total_files": sum(len(files) for _, _, files in os.walk(temp_dir))
                }
                
            else:
                    # 创建轻量级导出
                    lightweight_name = f"{self.safe_title}_核心材料_{timestamp}.zip"
                    lightweight_path = self.export_dir / lightweight_name
                    
                    # 只包含核心文件
                    core_files = [
                        (self.base_dir / f"{self.safe_title}_项目信息.json", "项目信息"),
                        (self.materials_dir, "生成材料", True),
                        (self.plans_dir, "写作计划", True),
                        (self.data_dir, "数据文件", True)
                    ]
                    
                    with zipfile.ZipFile(lightweight_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(self.base_dir):
                            for file in files:
                                file_path = Path(root) / file
                                if file_path.is_file():
                                    zipf.write(file_path, file_path.relative_to(self.base_dir))
                    
                    return {
                        "success": True,
                        "package_path": str(lightweight_path),
                        "package_name": lightweight_name,
                        "total_files": sum(len(files) for _, _, files in os.walk(self.base_dir) for file in files if isinstance(file, str))
                    }
            
        except Exception as e:
            self.logger.error(f"导出小说包失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "export_type": export_type
            }
    
    def cleanup_old_materials(self, days_old: int = 7) -> int:
        """清理旧材料"""
        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime(self.date_format)
        
        removed_count = 0
        
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if index_file.exists():
                with open(index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                
                original_count = len(index_data.get("materials", []))
                materials_to_remove = [
                    material for material in index_data.get("materials", [])
                    if material.get("created_time", "") < cutoff_date
                ]
                
                # 删除过期文件
                for material in materials_to_remove:
                    material_path = Path(material["file_path"])
                    if material_path.exists():
                        material_path.unlink()
                        removed_count += 1
                
                # 更新索引
                remaining_materials = [
                    material for material in index_data.get("materials", [])
                    if material.get("created_time", "") >= cutoff_date
                ]
                
                index_data["materials"] = remaining_materials
                index_data["total_materials"] = len(remaining_materials)
                index_data["last_cleanup"] = self.get_timestamp()
                
                with open(index_file, 'w', encoding='utf-8') as f:
                    json.dump(index_data, f, ensure_ascii=False, indent=2)
                
                self.logger.info(f"清理完成，删除了 {removed_count} 个过期材料文件")
                return removed_count
                
        except Exception as e:
            self.logger.error(f"清理旧材料失败: {e}")
            return 0
    
    def generate_material_manifest(self) -> Dict:
        """生成材料清单"""
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return {}
                
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            # 按类型分组
            manifest = {
                "novel_title": self.novel_title,
                "generated_time": index_data.get("last_updated", ""),
                "total_materials": len(materials),
                "file_structure": {},
                "material_categories": {}
            }
            
            for material in materials:
                mat_type = material.get("material_type", "未知类型")
                if mat_type not in manifest["material_categories"]:
                    manifest["material_categories"][mat_type] = []
                
                manifest["material_categories"][mat_type].append({
                    "id": f"{self.novel_title}_{material['created_time']}",
                    "title": material.get("title", ""),
                    "file_path": material.get("file_path", ""),
                    "size": material.get("file_size", 0),
                    "created_time": material.get("created_time", ""),
                    "related_chapters": material.get("related_chapters", []),
                    "content_summary": material.get("content_summary", "")
                })
            
            # 生成目录结构
            manifest["file_structure"] = self._generate_directory_structure()
            
            return manifest
            
        except Exception as e:
            self.logger.error(f"生成材料清单失败: {e}")
            return {}
    
    def _generate_directory_structure(self) -> Dict:
        """生成目录结构"""
        structure = {
            "root": f"小说项目/{self.safe_title}",
            "子目录": {
                "生成材料": "生成材料",
                "写作计划": "写作计划", 
                "数据文件": "数据文件",
                "导出包": "导出包"
            }
        }
        
        return structure
    
    def get_material_statistics(self) -> Dict:
        """获取材料统计信息"""
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return {
                    "total_materials": 0,
                    "total_size": 0,
                    "by_type": {},
                    "by_date": {},
                    "recent_materials": []
                }
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            # 统计总数量和大小
            total_materials = len(materials)
            total_size = sum(m.get("file_size", 0) for m in materials)
            
            # 按类型统计
            by_type = {}
            for material in materials:
                mat_type = material.get("material_type", "未知类型")
                if mat_type not in by_type:
                    by_type[mat_type] = []
                by_type[mat_type].append(material)
            
            # 按日期统计
            by_date = {}
            for material in materials:
                created_date = material.get("created_time", "")
                date_key = created_date[:10]  # 按日期分组
                if date_key not in by_date:
                    by_date[date_key] = []
                by_date[date_key].append(material)
            
            recent_materials = materials[:10]  # 最近10个材料
            
            return {
                "total_materials": total_materials,
                "total_size": total_size,
                "by_type": by_type,
                "by_date": by_date,
                "recent_materials": recent_materials
            }
            
        except Exception as e:
            self.logger.error(f"获取材料统计失败: {e}")
            return {}
    
    def create_quick_access_links(self) -> Dict:
        """创建快速访问链接"""
        timestamp = self.get_timestamp()
        
        links = {
            "项目主页": f"#",
            "材料索引": f"#material_index",
            "材料统计": f"#material_statistics", 
            "导出下载": f"#export_section",
            "清理旧材料": f"#cleanup_section"
        }
        
        return links
    
    def validate_material_integrity(self) -> Dict:
        """验证材料完整性"""
        try:
            index_file = self.base_dir / self.format_filename("index")
            
            if not index_file.exists():
                return {
                    "valid": False,
                    "error": "索引文件不存在"
                }
            
            with open(index_file, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
            
            materials = index_data.get("materials", [])
            
            validation_result = {
                "valid": True,
                "total_materials": len(materials),
                "missing_files": [],
                "corrupted_files": [],
                "total_size": 0,
                "checked_files": 0
            }
            
            # 检查每个文件是否存在
            for material in materials:
                file_path = Path(material["file_path"])
                if not file_path.exists():
                    validation_result["missing_files"].append(material["file_path"])
                else:
                    validation_result["checked_files"] += 1
                    validation_result["total_size"] += material.get("file_size", 0)
                    
                    # 验证校验和
                    stored_checksum = material.get("checksum", "")
                    actual_checksum = self._calculate_checksum(file_path)
                    if stored_checksum and actual_checksum != actual_checksum:
                        validation_result["corrupted_files"].append(material["file_path"])
            
            validation_result["missing_files_count"] = len(validation_result["missing_files"])
            validation_result["corrupted_files_count"] = len(validation_result["corrupted_files"])
            
            return validation_result
            
        except Exception as e:
            self.logger.error(f"验证材料完整性失败: {e}")
            return {
                "valid": False,
                "error": str(e)
            }

    def backup_materials(self, backup_dir: str = None) -> bool:
        """备份所有材料"""
        if not backup_dir:
            backup_dir = f"{self.base_dir}_backup_{self.get_timestamp()}"
        
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copytree(self.base_dir, backup_path, ignore_patterns=[
                '*.log', '*.tmp', '*.cache'
            ])
            
            self.logger.info(f"材料备份完成: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"备份材料失败: {e}")
            return False