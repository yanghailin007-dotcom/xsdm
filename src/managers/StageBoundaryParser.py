"""
阶段边界解析器 - 支持从创意设定读取章节范围或按比例计算

优先级：
1. 从创意设定文件 (completeStoryline) 读取章节范围
2. 如果设定中没有，使用固定比例计算作为fallback

这样实现动态章节划分，适应每本书的创意设定。
"""
import re
from typing import Dict, List, Optional, Tuple
from src.utils.logger import get_logger


class StageBoundaryParser:
    """阶段边界解析器 - 统一的章节范围解析和计算"""
    
    # 支持的阶段名称映射
    STAGE_NAME_MAP = {
        "opening": ["opening", "opening_stage", "起", "起因", "开局", "开局阶段"],
        "development": ["development", "development_stage", "承", "发展", "发展阶段"],
        "conflict": ["conflict", "climax", "climax_stage", "转", "转折", "高潮", "高潮阶段"],
        "ending": ["ending", "ending_stage", "合", "结局", "结局阶段"]
    }
    
    # 默认四阶段比例
    DEFAULT_4_STAGE_RATIOS = [0.15, 0.35, 0.30, 0.20]
    
    # 默认五阶段比例（用于兼容旧代码）
    DEFAULT_5_STAGE_RATIOS = [0.16, 0.26, 0.28, 0.18, 0.12]
    
    def __init__(self):
        self.logger = get_logger("StageBoundaryParser")
    
    def parse_from_creative_seed(self, creative_seed: Dict, total_chapters: int) -> Optional[Dict]:
        """
        从创意设定解析章节范围
        
        Args:
            creative_seed: 创意设定字典
            total_chapters: 总章节数
            
        Returns:
            章节边界字典，如果解析失败返回None
            格式: {
                "opening_end": 25,
                "development_start": 26,
                "development_end": 90,
                "climax_start": 91,
                "climax_end": 150,
                "ending_start": 151
            }
        """
        if not creative_seed or not isinstance(creative_seed, dict):
            self.logger.info("⚠️ 创意设定为空，无法解析章节范围")
            return None
        
        # 尝试从 completeStoryline 解析
        complete_storyline = creative_seed.get("completeStoryline", {})
        
        if not complete_storyline:
            self.logger.info("⚠️ 创意设定中没有 completeStoryline 字段")
            return None
        
        # 解析各阶段章节范围
        boundaries = {}
        stage_ranges = {}
        
        # 遍历各个阶段
        for stage_key in ["opening", "development", "conflict", "ending"]:
            stage_data = complete_storyline.get(stage_key, {})
            
            if not stage_data:
                self.logger.info(f"⚠️ completeStoryline 中缺少 {stage_key} 阶段")
                return None
            
            # 优先从 summary 中提取章节范围
            chapter_range = self._extract_chapter_range_from_stage(stage_data)
            
            if chapter_range is None:
                self.logger.info(f"⚠️ 无法从 {stage_key} 阶段提取章节范围")
                return None
            
            stage_ranges[stage_key] = chapter_range
        
        # 验证边界连续性
        if not self._validate_stage_continuity(stage_ranges, total_chapters):
            self.logger.warning("⚠️ 章节范围验证失败，将使用固定比例")
            return None
        
        # 构建边界字典
        boundaries = self._build_boundaries_from_ranges(stage_ranges)
        
        self.logger.info(f"✅ 成功从创意设定解析章节范围: {boundaries}")
        return boundaries
    
    def _extract_chapter_range_from_stage(self, stage_data: Dict) -> Optional[Tuple[int, int]]:
        """
        从阶段数据中提取章节范围
        
        支持以下格式：
        1. chapter_range 字段: "1-25"
        2. summary 字段: "【第1章 - 第25章】..."
        """
        # 1. 优先使用 chapter_range 字段
        chapter_range_str = stage_data.get("chapter_range", "")
        if chapter_range_str:
            range_match = re.search(r'(\d+)\s*[-~到至]\s*(\d+)', str(chapter_range_str))
            if range_match:
                return int(range_match.group(1)), int(range_match.group(2))
        
        # 2. 从 summary 字段提取
        summary = stage_data.get("summary", "")
        if summary:
            # 匹配 "第X章 - 第Y章" 或 "第X章-第Y章" 等格式
            summary_match = re.search(r'第(\d+)[章节]*\s*[-~到至]\s*第(\d+)[章节]*', str(summary))
            if summary_match:
                return int(summary_match.group(1)), int(summary_match.group(2))
            
            # 匹配 "【第X章 - 第Y章】" 格式
            bracket_match = re.search(r'【第(\d+)[章节]*\s*[-~到至]\s*第(\d+)[章节]*】', str(summary))
            if bracket_match:
                return int(bracket_match.group(1)), int(bracket_match.group(2))
        
        return None
    
    def _validate_stage_continuity(self, stage_ranges: Dict[str, Tuple[int, int]], 
                                  total_chapters: int) -> bool:
        """
        验证阶段边界的连续性和完整性
        
        Args:
            stage_ranges: 各阶段的章节范围
            total_chapters: 总章节数
            
        Returns:
            是否验证通过
        """
        expected_order = ["opening", "development", "conflict", "ending"]
        last_end = 0
        
        for stage_key in expected_order:
            if stage_key not in stage_ranges:
                self.logger.warning(f"❌ 缺少 {stage_key} 阶段")
                return False
            
            start, end = stage_ranges[stage_key]
            
            # 检查范围有效性
            if start > end:
                self.logger.warning(f"❌ {stage_key} 阶段起始章节({start})大于结束章节({end})")
                return False
            
            # 检查连续性（允许+1的间隔，即前一阶段结束+1 = 下一阶段开始）
            if start != last_end + 1:
                self.logger.warning(f"⚠️ {stage_key} 阶段不连续: 前一阶段结束于{last_end}，当前阶段开始于{start}")
                # 对于小误差，可以自动修正
                if start > last_end + 1:
                    self.logger.warning(f"⚠️ 间隙过大，验证失败")
                    return False
            
            last_end = end
        
        # 检查是否覆盖到总章节数
        if last_end != total_chapters:
            self.logger.warning(f"⚠️ 阶段划分覆盖范围({last_end})与总章节数({total_chapters})不一致")
            # 这里不返回False，允许有差异
        
        return True
    
    def _build_boundaries_from_ranges(self, stage_ranges: Dict[str, Tuple[int, int]]) -> Dict:
        """
        从章节范围构建边界字典
        
        Args:
            stage_ranges: 各阶段的章节范围
            
        Returns:
            边界字典
        """
        opening_start, opening_end = stage_ranges["opening"]
        dev_start, dev_end = stage_ranges["development"]
        conflict_start, conflict_end = stage_ranges["conflict"]
        ending_start, ending_end = stage_ranges["ending"]
        
        return {
            "opening_end": opening_end,
            "development_start": dev_start,
            "development_end": dev_end,
            "climax_start": conflict_start,
            "climax_end": conflict_end,
            "ending_start": ending_start
        }
    
    def calculate_by_ratio(self, total_chapters: int, ratios: Optional[List[float]] = None,
                          stage_count: int = 4) -> Dict:
        """
        按比例计算章节边界
        
        Args:
            total_chapters: 总章节数
            ratios: 自定义比例，默认使用 DEFAULT_4_STAGE_RATIOS
            stage_count: 阶段数量（4或5）
            
        Returns:
            边界字典
        """
        if ratios is None:
            ratios = self.DEFAULT_4_STAGE_RATIOS if stage_count == 4 else self.DEFAULT_5_STAGE_RATIOS
        
        # 确保比例总和为1
        total_ratio = sum(ratios)
        if abs(total_ratio - 1.0) > 0.01:
            self.logger.warning(f"⚠️ 比例总和({total_ratio})不为1，将进行归一化")
            ratios = [r / total_ratio for r in ratios]
        
        # 计算累积章节数
        chapters = [0]
        cumulative_ratio = 0
        
        for ratio in ratios[:-1]:
            cumulative_ratio += ratio
            chapter_boundary = int(total_chapters * cumulative_ratio)
            chapters.append(chapter_boundary)
        
        chapters.append(total_chapters)
        
        # 构建边界字典
        if stage_count == 4:
            return {
                "opening_end": chapters[1],
                "development_start": chapters[1] + 1,
                "development_end": chapters[2],
                "climax_start": chapters[2] + 1,
                "climax_end": chapters[3],
                "ending_start": chapters[3] + 1
            }
        else:  # 5 stages
            return {
                "opening_end": chapters[1],
                "development_start": chapters[1] + 1,
                "development_end": chapters[2],
                "climax_start": chapters[2] + 1,
                "climax_end": chapters[3],
                "ending_start": chapters[3] + 1,
                "ending_end": chapters[4],
                "final_start": chapters[4] + 1
            }
    
    def validate_boundaries(self, boundaries: Dict, total_chapters: int) -> Tuple[bool, List[str]]:
        """
        验证边界覆盖的完整性和连续性
        
        Args:
            boundaries: 边界字典
            total_chapters: 总章节数
            
        Returns:
            (是否验证通过, 错误信息列表)
        """
        errors = []
        
        # 检查必需的字段
        required_fields = ["opening_end", "development_start", "development_end",
                          "climax_start", "climax_end", "ending_start"]
        
        for field in required_fields:
            if field not in boundaries:
                errors.append(f"缺少必需字段: {field}")
        
        if errors:
            return False, errors
        
        # 检查连续性
        expected_sequence = [
            ("opening_end", "development_start"),
            ("development_end", "climax_start"),
            ("climax_end", "ending_start")
        ]
        
        for prev_field, next_field in expected_sequence:
            prev_val = boundaries[prev_field]
            next_val = boundaries[next_field]
            
            if next_val != prev_val + 1:
                errors.append(f"{prev_field}({prev_val}) 和 {next_field}({next_val}) 不连续")
        
        # 检查范围有效性
        for key, value in boundaries.items():
            if "start" in key or "end" in key:
                if value < 1 or value > total_chapters:
                    errors.append(f"{key} 的值({value})超出章节范围(1-{total_chapters})")
        
        return len(errors) == 0, errors


# 导出的便捷函数
def parse_stage_boundaries(creative_seed: Dict, total_chapters: int, 
                          ratios: Optional[List[float]] = None) -> Dict:
    """
    便捷函数：解析阶段边界
    
    优先从创意设定读取，失败时使用比例计算
    
    Args:
        creative_seed: 创意设定
        total_chapters: 总章节数
        ratios: 自定义比例（可选）
        
    Returns:
        边界字典
    """
    parser = StageBoundaryParser()
    
    # 1. 尝试从创意设定解析
    boundaries = parser.parse_from_creative_seed(creative_seed, total_chapters)
    
    if boundaries:
        return boundaries
    
    # 2. Fallback: 使用比例计算
    stage_count = 5 if ratios and len(ratios) == 5 else 4
    return parser.calculate_by_ratio(total_chapters, ratios, stage_count)
