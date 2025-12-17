"""
文件处理工具模块
提供文件读取、写入、验证等功能
"""

import os
import json
import re
import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime


class FileHandler:
    """文件处理工具类"""
    
    def __init__(self, config_loader=None):
        """
        初始化文件处理器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
    
    def ensure_directory_exists(self, directory: str) -> str:
        """
        确保目录存在，如果不存在则创建
        
        Args:
            directory: 目录路径
            
        Returns:
            目录路径
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"创建目录: {directory}")
        return directory
    
    def list_json_files(self, directory: str, suffix: str = "项目信息.json") -> List[str]:
        """
        列出指定目录下的JSON文件
        
        Args:
            directory: 目录路径
            suffix: 文件后缀
            
        Returns:
            匹配的文件路径列表
        """
        try:
            self.ensure_directory_exists(directory)
            
            matched_files = []
            for filename in os.listdir(directory):
                if filename.endswith(suffix):
                    filepath = os.path.join(directory, filename)
                    if os.path.isfile(filepath):
                        matched_files.append(filepath)
            return matched_files
        except FileNotFoundError:
            print(f"错误：目录 '{directory}' 不存在，已自动创建")
            return []
        except Exception as e:
            print(f"列出JSON文件时出错: {e}")
            return []
    
    def sort_files_by_chapter(self, file_paths: List[str]) -> List[str]:
        """
        按章节号对文件路径进行排序
        
        Args:
            file_paths: 文件路径列表
            
        Returns:
            排序后的文件路径列表
        """
        def extract_chapter_number(filepath):
            match = re.search(r"_第(\d+)章_", os.path.basename(filepath))
            return int(match.group(1)) if match else 0
        
        return sorted(file_paths, key=extract_chapter_number)
    
    def load_json_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        加载JSON文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            JSON数据或None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载JSON文件失败 {file_path}: {e}")
            return None
    
    def save_json_file(self, file_path: str, data: Dict[str, Any], indent: int = 2) -> bool:
        """
        保存JSON文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
            indent: 缩进空格数
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            directory = os.path.dirname(file_path)
            if directory:
                self.ensure_directory_exists(directory)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            return True
        except Exception as e:
            print(f"保存JSON文件失败 {file_path}: {e}")
            return False
    
    def validate_chapter_file(self, file_path: str) -> bool:
        """
        验证章节文件的有效性
        
        Args:
            file_path: 章节文件路径
            
        Returns:
            文件是否有效
        """
        try:
            if not os.path.exists(file_path):
                print(f"✗ 文件不存在: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
            
            # 检查必需字段
            required_fields = ['chapter_number', 'chapter_title', 'content']
            missing_fields = []
            for field in required_fields:
                if field not in chapter_data:
                    missing_fields.append(field)
            
            if missing_fields:
                print(f"✗ 文件缺少必需字段 {missing_fields}: {file_path}")
                return False
            
            return True
            
        except json.JSONDecodeError:
            print(f"✗ JSON 格式错误: {file_path}")
            return False
        except Exception as e:
            print(f"✗ 验证章节文件失败 {file_path}: {e}")
            return False
    
    def check_and_rename_duplicate_chapters(self, chapter_files: List[str], novel_title: str) -> List[str]:
        """
        检查并重命名重复的章节文件
        
        Args:
            chapter_files: 章节文件列表
            novel_title: 小说标题
            
        Returns:
            处理后的章节文件列表
        """
        print("检查章节文件名重复...")
        
        chapter_title_count = {}
        renamed_files = []
        renamed_count = 0
        
        for chapter_file in chapter_files:
            try:
                chapter_data = self.load_json_file(chapter_file)
                if not chapter_data:
                    renamed_files.append(chapter_file)
                    continue
                
                original_chapter_title = chapter_data.get('chapter_title', '')
                
                if original_chapter_title in chapter_title_count:
                    chapter_title_count[original_chapter_title] += 1
                    count = chapter_title_count[original_chapter_title]
                    
                    # 创建新的章节标题
                    new_chapter_title = f"{original_chapter_title}（{count}）"
                    
                    # 更新文件内的章节标题
                    chapter_data['chapter_title'] = new_chapter_title
                    
                    # 保存更新后的内容
                    if self.save_json_file(chapter_file, chapter_data):
                        # 构建新的文件名
                        dir_path = os.path.dirname(chapter_file)
                        filename = os.path.basename(chapter_file)
                        
                        parts = filename.split('_')
                        if len(parts) >= 2:
                            chapter_num_part = parts[0]
                            extension = '.txt' if filename.endswith('.txt') else ''
                            new_filename = f"{chapter_num_part}_{new_chapter_title}{extension}"
                            new_filepath = os.path.join(dir_path, new_filename)
                            
                            # 重命名文件
                            try:
                                os.rename(chapter_file, new_filepath)
                                renamed_files.append(new_filepath)
                                renamed_count += 1
                                print(f"重命名: {filename} -> {new_filename}")
                                print(f"  更新章节标题: {original_chapter_title} -> {new_chapter_title}")
                            except Exception as e:
                                print(f"重命名失败 {filename}: {e}")
                                renamed_files.append(chapter_file)
                        else:
                            renamed_files.append(chapter_file)
                            renamed_count += 1
                else:
                    chapter_title_count[original_chapter_title] = 1
                    renamed_files.append(chapter_file)
                
            except Exception as e:
                print(f"处理章节文件失败 {chapter_file}: {e}")
                renamed_files.append(chapter_file)
        
        if renamed_count > 0:
            print(f"✓ 已完成 {renamed_count} 个文件的重命名和内容更新")
        else:
            print("✓ 没有发现重复的章节文件名")
        
        return renamed_files
    
    def validate_and_fix_chapter_files(self, chapter_files: List[str], novel_title: str) -> List[str]:
        """
        验证和修复章节文件
        
        Args:
            chapter_files: 章节文件列表
            novel_title: 小说标题
            
        Returns:
            有效的章节文件列表
        """
        print("验证和修复章节文件...")
        
        # 首先检查并修复重复的章节
        fixed_files = self.check_and_rename_duplicate_chapters(chapter_files, novel_title)
        
        # 然后验证文件完整性
        valid_files = []
        error_count = 0
        
        for chapter_file in fixed_files:
            if self.validate_chapter_file(chapter_file):
                valid_files.append(chapter_file)
            else:
                error_count += 1
        
        if error_count > 0:
            print(f"⚠ 发现 {error_count} 个文件问题")
        else:
            print("✓ 所有章节文件验证通过")
        
        return valid_files
    
    def move_completed_novel_to_published(self, novel_title: str, json_file_path: str) -> bool:
        """
        将已完成发布的小说移动到已发布目录
        
        Args:
            novel_title: 小说标题
            json_file_path: JSON文件路径
            
        Returns:
            是否移动成功
        """
        try:
            if not self.config_loader:
                print("✗ 配置加载器未初始化")
                return False
            
            # 确保已发布目录存在
            published_dir = self.ensure_directory_exists(
                self.config_loader.get_published_path()
            )
            
            # 创建目标子目录
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_subdir = os.path.join(published_dir, f"{novel_title}_{timestamp}")
            self.ensure_directory_exists(target_subdir)
            
            # 移动相关文件
            moved_items = []
            source_dir = self.config_loader.get_novel_path()
            
            print(f"正在从 '{source_dir}' 目录查找所有与《{novel_title}》相关的文件和目录...")
            
            for item_name in os.listdir(source_dir):
                if item_name.startswith(f"{novel_title}_"):
                    source_path = os.path.join(source_dir, item_name)
                    target_path = os.path.join(target_subdir, item_name)
                    
                    try:
                        shutil.move(source_path, target_path)
                        moved_items.append(item_name)
                    except Exception as e:
                        print(f"✗ 移动 '{item_name}' 失败: {e}")
            
            if not moved_items:
                print(f"⚠ 未找到任何与《{novel_title}》相关的文件进行移动。")
            else:
                print(f"✓ 小说《{novel_title}》发布完成，已移动到: {target_subdir}")
                print(f"  移动的项目: {', '.join(moved_items)}")
            
            return True
            
        except Exception as e:
            print(f"✗ 移动已发布小说时出错: {e}")
            return False
    
    def count_content_chars(self, text: str) -> int:
        """
        统计字符串中字母、数字和汉字的总数量
        
        Args:
            text: 要统计的文本
            
        Returns:
            字符数量
        """
        pattern = r'[a-zA-Z0-9\u4e00-\u9fa5]'
        content_chars = re.findall(pattern, text)
        return len(content_chars)
    
    def normalize_line_breaks(self, text: str) -> str:
        """
        处理各种换行符组合
        
        Args:
            text: 要处理的文本
            
        Returns:
            处理后的文本
        """
        text = re.sub(r'\r\n|\r', '\n', text)
        text = re.sub(r'\n[ \t]*\n', '\n\n', text)
        return re.sub(r'\n{3,}', '\n\n', text)
    
    def format_synopsis_for_fanqie(self, text: str, novel_data: Optional[Dict] = None, max_length: int = 500) -> str:
        """
        针对番茄小说优化简介排版
        
        Args:
            text: 原始简介文本
            novel_data: 小说数据
            max_length: 最大长度
            
        Returns:
            格式化后的简介
        """
        if not text or len(text.strip()) == 0:
            return ""
        
        # 清理文本，去除多余空格和换行
        text = re.sub(r'\s+', ' ', text.strip())
        
        # 如果有完整的novel_data，尝试提取标签和核心卖点
        if novel_data and isinstance(novel_data, dict):
            tag_line = ""
            
            # 方法1: 从简介开头提取标签
            tag_match = re.search(r'^(\[[^\]]+\])', text)
            if tag_match:
                tag_line = tag_match.group(1)
                text = text.replace(tag_line, "").strip()
            
            # 方法2: 如果没有找到标签，尝试从creative_seed或core_settings中提取
            if not tag_line:
                if "creative_seed" in novel_data:
                    creative_seed = novel_data["creative_seed"]
                    tag_match = re.search(r'(\[[^\]]+\])', creative_seed)
                    if tag_match:
                        tag_line = tag_match.group(1)
                
                # 方法3: 如果还是没有，使用默认标签
                if not tag_line:
                    tag_line = "[系统+爽文]"
            
            # 对原简介部分进行换行处理
            original_synopsis = text
            
            # 按句子分割原简介
            sentences = re.split(r'([。！？])', original_synopsis)
            
            # 重新组合句子，保留标点
            processed_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                    if sentence.strip():
                        processed_sentences.append(sentence.strip())
            
            # 如果分割失败，使用简单分割
            if not processed_sentences:
                processed_sentences = [s.strip() for s in original_synopsis.split('。') if s.strip()]
                processed_sentences = [s + '。' for s in processed_sentences]
            
            # 构建新格式的简介
            formatted_lines = [tag_line, ""]
            formatted_lines.extend(processed_sentences)
            
            formatted_text = '\n'.join(formatted_lines)
        else:
            # 对于没有完整novel_data的情况，使用原有的处理逻辑
            if len(text) <= 100:
                return text
            
            sentences = re.split(r'([。！？])', text)
            processed_sentences = []
            for i in range(0, len(sentences) - 1, 2):
                if i + 1 < len(sentences):
                    sentence = sentences[i] + sentences[i + 1]
                    if sentence.strip():
                        processed_sentences.append(sentence.strip())
            
            if not processed_sentences:
                processed_sentences = [s.strip() for s in text.split('。') if s.strip()]
                processed_sentences = [s + '。' for s in processed_sentences]
            
            formatted_text = '\n'.join(processed_sentences)
        
        # 确保不超过最大长度
        if len(formatted_text) > max_length:
            formatted_text = formatted_text[:max_length - 3] + '...'
        
        return formatted_text