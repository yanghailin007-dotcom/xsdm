"""
Tactical Planner
战术层规划器 v2.0

每30章滚动规划详细战术蓝图
基于番茄爆款算法要求，生成可执行的章节设计
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# 导入提示词加载器
from .prompt_loader import get_prompt_loader

logger = logging.getLogger(__name__)


def _parse_numeric(value, default=0):
    """
    安全地解析数值，处理字符串格式如 '≥3', '<5' 等
    
    Args:
        value: 待解析的值（可能是数字、字符串）
        default: 默认值
        
    Returns:
        float: 解析后的数值
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # 移除前缀符号如 ≥, >, <, ≤
        cleaned = value.lstrip('≥><≤').strip()
        try:
            return float(cleaned)
        except ValueError:
            return float(default)
    return float(default)


class TacticalPlanner:
    """
    战术层规划器
    
    职责：
    1. 每30章详细规划情绪曲线
    2. 基于前序总结动态调整
    3. 与阶段目标对齐
    4. 保证章节间连贯性
    """
    
    DEFAULT_WINDOW = 30      # 每次规划30章
    
    def __init__(
        self, 
        api_client=None,
        project_path: Path = None
    ):
        self.api_client = api_client
        self.project_path = project_path
        self.generated_chapters = []  # 已生成章节记录
        
        # 加载战术规划配置
        self._prompt_loader = get_prompt_loader()
        self._planning_config = self._load_planning_config()
        self._fix_config = self._load_fix_config()  # 加载修复配置
        
    def _load_fix_config(self) -> Dict:
        """加载情绪修复配置"""
        try:
            config = self._prompt_loader.load_json("components/planning/emotion_fix_prompts.json")
            if config:
                logger.info("[TacticalPlanner] 加载情绪修复配置成功")
                return config
            else:
                logger.warning("[TacticalPlanner] 情绪修复配置加载失败，使用默认配置")
                return self._get_default_fix_config()
        except Exception as e:
            logger.error(f"[TacticalPlanner] 加载修复配置失败: {e}")
            return self._get_default_fix_config()
    
    def _get_default_fix_config(self) -> Dict:
        """获取默认修复配置"""
        return {
            "fix_strategies": {
                "levels": {
                    "critical": {"action": "regenerate_all", "max_attempts": 3},
                    "high": {"action": "ai_partial_fix", "max_attempts": 2},
                    "medium": {"action": "auto_adjust", "max_attempts": 1},
                    "low": {"action": "mark_only", "max_attempts": 0}
                }
            },
            "validation_rules": {
                "emotion_variance": {
                    "min_variance_by_pattern": {
                        "开局爆发型": 3, "递进高潮型": 2, 
                        "蓄力积累型": 1, "收束过渡型": 2
                    }
                }
            },
            "ai_fix_prompts": {
                "system_role": "你是一位专业的小说情绪设计修复专家。",
                "templates": {}
            }
        }
        
    def _load_planning_config(self) -> Dict:
        """加载战术规划配置"""
        try:
            config = self._prompt_loader.load_json("components/planning/tactical_planning_prompts.json")
            if config:
                logger.info("[TacticalPlanner] 加载战术规划配置成功")
                return config
            else:
                logger.warning("[TacticalPlanner] 战术规划配置加载失败，使用默认配置")
                return self._get_default_config()
        except Exception as e:
            logger.error(f"[TacticalPlanner] 加载配置失败: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "algorithm_requirements": {
                "emotion_density": {"target": "≥2.0个/千字", "min_count_per_chapter": 10},
                "appeal_density": {"target": "≥1.5个/千字", "min_moments_per_chapter": 3},
                "hook_requirements": {"required": True, "position": "最后50字"}
            },
            "stage_emotion_patterns": {
                "patterns": {
                    "开局爆发型": {
                        "applicable_goals": ["黄金三章", "首次展现实力", "系统觉醒", "开局打脸"],
                        "emotion_arc": ["压抑(9)", "反转(8)", "爽快(9)", "震惊(8)", "期待(7)"],
                        "key_metrics": {"emotion_variance": 3, "climax_in_3_chapters": True}
                    },
                    "蓄力积累型": {
                        "applicable_goals": ["成长积累", "能力解锁前", "地图切换前", "势力扩张"],
                        "emotion_arc": ["小压抑(6)", "小冲突(7)", "小爽快(7)", "小期待(6)", "新伏笔(6)"],
                        "key_metrics": {"emotion_variance": 1, "max_intensity": 7}
                    },
                    "递进高潮型": {
                        "applicable_goals": ["阶段性高潮", "BOSS战", "身份大曝光", "大型打脸现场"],
                        "emotion_arc": ["紧张(7)", "冲突升级(8)", "第一波爽(8)", "第二波爽(9)", "巅峰(9)"],
                        "key_metrics": {"emotion_variance": 2, "shock_layers": 3}
                    },
                    "收束过渡型": {
                        "applicable_goals": ["阶段总结", "地图切换", "能力提升后", "新目标开启"],
                        "emotion_arc": ["满足(7)", "收获(6)", "新线索(6)", "新期待(7)", "新目标(7)"],
                        "key_metrics": {"emotion_variance": 1, "foreshadowing_resolution": True}
                    }
                }
            }
        }
    
    def _detect_emotion_pattern(self, stage_goal: Dict, start_chapter: int) -> Dict:
        """
        自动识别阶段目标适用的情绪模式
        
        Args:
            stage_goal: 阶段目标
            start_chapter: 起始章节号
            
        Returns:
            情绪模式配置
        """
        goal_id = stage_goal.get('goal_id', '')
        goal_desc = stage_goal.get('description', '')
        
        # 获取配置中的模式定义
        patterns_config = self._planning_config.get('stage_emotion_patterns', {}).get('patterns', {})
        
        # 关键词匹配表
        pattern_keywords = {
            "开局爆发型": ['开局', '黄金', '首次', '觉醒', '激活', '初始', '新手', '入门', '第一张', '开局打脸'],
            "蓄力积累型": ['积累', '成长', '提升', '准备', '蓄力', '打磨', '历练', '修炼', '解锁前', '突破前'],
            "递进高潮型": ['高潮', '大战', 'BOSS', '决战', '巅峰', '终极', '总攻', '爆发', '曝光', '摊牌'],
            "收束过渡型": ['总结', '过渡', '切换', '转移', '收获', '结算', '结束', '完成', '新阶段', '新地图']
        }
        
        # 计算每个模式的匹配分数
        scores = {name: 0 for name in pattern_keywords}
        check_text = f"{goal_id} {goal_desc}".lower()
        
        for pattern_name, keywords in pattern_keywords.items():
            for keyword in keywords:
                if keyword.lower() in check_text:
                    scores[pattern_name] += 1
        
        # 根据起始章节辅助判断
        if start_chapter <= 3:
            scores["开局爆发型"] += 2  # 前3章优先开局模式
        elif start_chapter <= 30:
            if scores["开局爆发型"] == 0:
                scores["蓄力积累型"] += 1  # 1-30章默认蓄力
        
        # 选择最高分的模式
        best_pattern = max(scores, key=scores.get)
        
        if scores[best_pattern] == 0:
            # 没有匹配到，根据阶段类型默认
            # 🔥 开局爆发型只用于前3章（黄金三章）
            if start_chapter <= 3:
                best_pattern = "开局爆发型"
            elif 'opening' in goal_id.lower() and start_chapter <= 5:
                # 开局相关但超过前3章，用蓄力积累型过渡
                best_pattern = "蓄力积累型"
            elif 'climax' in goal_id.lower() or 'peak' in goal_id.lower():
                best_pattern = "递进高潮型"
            elif 'transition' in goal_id.lower() or 'summary' in goal_id.lower():
                best_pattern = "收束过渡型"
            else:
                best_pattern = "蓄力积累型"
        
        pattern_config = patterns_config.get(best_pattern, {})
        
        logger.info(f"[TacticalPlanner] 阶段目标'{goal_id}'识别为{best_pattern} | 匹配分数: {scores}")
        
        # 解析 emotion_arc（支持字符串或列表格式）
        emotion_arc = pattern_config.get('emotion_arc', [])
        if isinstance(emotion_arc, str):
            # 字符串格式："压抑(9)→反转(8)→爽快(9)"
            emotion_arc = [item.strip() for item in emotion_arc.split('→')]
        
        return {
            "pattern_name": best_pattern,
            "pattern_id": pattern_config.get('pattern_id', best_pattern),
            "description": pattern_config.get('description', ''),
            "emotion_arc": emotion_arc,
            "key_metrics": pattern_config.get('key_metrics', {}),
            "applicable_goals": pattern_config.get('applicable_goals', [])
        }
    
    def _validate_emotion_design(self, chapters: List[Dict], expected_pattern: Dict) -> Dict:
        """
        验证情绪设计 - 增强版（带精准定位和修复计划）
        
        Args:
            chapters: 生成的章节列表
            expected_pattern: 期望的情绪模式
            
        Returns:
            验证结果，包含精准问题定位和修复计划
        """
        issues = []
        fixes = {}  # 章节号 -> 修复指令
        
        pattern_name = expected_pattern.get('pattern_name', '')
        key_metrics = expected_pattern.get('key_metrics', {})
        
        # 获取最小起伏度要求
        variance_config = self._fix_config.get('validation_rules', {}).get('emotion_variance', {})
        min_variance_by_pattern = variance_config.get('min_variance_by_pattern', {})
        min_variance = min_variance_by_pattern.get(pattern_name, 
                         _parse_numeric(key_metrics.get('emotion_variance', 1), 1))
        
        # 1. 检查情绪起伏度 - 精准定位每一对相邻章节
        intensities = [(ch.get('chapter_number'), ch.get('intensity', 5)) for ch in chapters]
        
        for i in range(1, len(intensities)):
            ch_num_prev, intensity_prev = intensities[i-1]
            ch_num_curr, intensity_curr = intensities[i]
            variance = abs(intensity_curr - intensity_prev)
            
            if variance < min_variance:
                # 精准定位到具体章节对
                location = f"第{ch_num_prev}章→第{ch_num_curr}章"
                severity = self._calculate_severity(variance, min_variance, pattern_name)
                
                # 自动生成修复值
                suggested_intensity = self._calculate_fix_intensity(
                    intensity_prev, intensity_curr, min_variance
                )
                
                issue = {
                    "type": "情绪起伏不足",
                    "chapters": [ch_num_prev, ch_num_curr],
                    "location": location,
                    "current_values": [intensity_prev, intensity_curr],
                    "expected_min_variance": min_variance,
                    "actual_variance": variance,
                    "severity": severity,
                    "fix_instruction": f"将第{ch_num_curr}章强度从{intensity_curr}改为{suggested_intensity}，确保与第{ch_num_prev}章差值≥{min_variance}",
                    "suggested_fix": {
                        "chapter": ch_num_curr,
                        "field": "intensity",
                        "old_value": intensity_curr,
                        "new_value": suggested_intensity,
                        "reason": f"情绪起伏不足({variance} < {min_variance})"
                    }
                }
                
                issues.append(issue)
                fixes[ch_num_curr] = issue["suggested_fix"]
                
                # 记录详细日志
                logger.warning(f"[TacticalPlanner]   - {location}: 情绪起伏不足 | 差值{variance} < 要求{min_variance}")
        
        # 2. 模式特定检查 - 开局爆发型
        if pattern_name == "开局爆发型":
            first_3 = intensities[:3] if len(intensities) >= 3 else intensities
            if first_3:
                max_in_first_3 = max([v for _, v in first_3])
                
                if max_in_first_3 < 8:
                    weak_chapters = [ch for ch, v in first_3 if v < 8]
                    # 为前3章生成修复计划
                    target_arc = [9, 6, 9]  # 理想的U型弧线
                    for idx, (ch_num, current) in enumerate(first_3):
                        if current < target_arc[idx]:
                            fixes[ch_num] = {
                                "chapter": ch_num,
                                "field": "intensity",
                                "old_value": current,
                                "new_value": target_arc[idx],
                                "reason": f"开局爆发型第{idx+1}章强度不达标",
                                "pattern_fix": True
                            }
                    
                    issue = {
                        "type": "开局强度不足",
                        "chapters": weak_chapters,
                        "current_max": max_in_first_3,
                        "required_min": 8,
                        "severity": "critical",
                        "fix_instruction": f"前3章必须有强度≥8的高潮，当前最高仅{max_in_first_3}。建议弧线：9(压抑)→6(反转)→9(爽快)",
                        "suggested_fix": {"chapters": weak_chapters, "target_arc": target_arc}
                    }
                    issues.append(issue)
                    logger.warning(f"[TacticalPlanner]   - 开局爆发型: 前3章最高强度{max_in_first_3} < 要求8")
        
        # 3. 模式特定检查 - 递进高潮型
        elif pattern_name == "递进高潮型":
            if len(intensities) >= 2:
                start_intensity = intensities[0][1]
                end_intensity = intensities[-1][1]
                
                if end_intensity < start_intensity:
                    issue = {
                        "type": "递增趋势不足",
                        "chapters": [ch[0] for ch in intensities],
                        "start_intensity": start_intensity,
                        "end_intensity": end_intensity,
                        "severity": "high",
                        "fix_instruction": "递进高潮型要求情绪强度总体递增，建议后期章节提升到9"
                    }
                    issues.append(issue)
                    logger.warning(f"[TacticalPlanner]   - 递进高潮型: 末期强度{end_intensity} < 初期{start_intensity}")
        
        # 4. 通用检查 - 钩子
        for ch in chapters:
            ch_num = ch.get('chapter_number')
            if not ch.get('hook_content'):
                issue = {
                    "type": "缺少钩子",
                    "chapter": ch_num,
                    "severity": "high",
                    "fix_instruction": f"为第{ch_num}章添加章尾钩子"
                }
                issues.append(issue)
                fixes[ch_num] = {
                    "chapter": ch_num,
                    "field": "hook_content",
                    "old_value": None,
                    "new_value": "TODO",
                    "reason": "缺少章尾钩子"
                }
                logger.warning(f"[TacticalPlanner]   - 第{ch_num}章: 缺少钩子")
            
            # 检查强度范围
            intensity = ch.get('intensity', 5)
            if intensity < 1 or intensity > 10:
                clamped = max(1, min(10, intensity))
                issue = {
                    "type": "强度超出范围",
                    "chapter": ch_num,
                    "intensity": intensity,
                    "severity": "medium",
                    "fix_instruction": f"第{ch_num}章强度{intensity}超出1-10范围，应调整为{clamped}"
                }
                issues.append(issue)
                fixes[ch_num] = {
                    "chapter": ch_num,
                    "field": "intensity",
                    "old_value": intensity,
                    "new_value": clamped,
                    "reason": f"强度超出有效范围"
                }
                logger.warning(f"[TacticalPlanner]   - 第{ch_num}章: 强度{intensity}超出1-10范围")
        
        # 计算整体严重程度和修复策略
        fix_strategy = self._calculate_fix_strategy(issues, len(chapters))
        
        is_valid = len(issues) == 0
        
        if is_valid:
            logger.info(f"[TacticalPlanner] 情绪设计验证通过 | 模式:{pattern_name}")
        else:
            logger.warning(f"[TacticalPlanner] 情绪设计验证发现问题:{len(issues)}个 | 模式:{pattern_name} | 策略:{fix_strategy['action']}")
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "fixes": fixes,
            "pattern_name": pattern_name,
            "fix_strategy": fix_strategy,
            "needs_regeneration": fix_strategy['action'] == 'regenerate_all'
        }
    
    def _calculate_severity(self, variance: float, min_variance: float, pattern_name: str) -> str:
        """计算问题严重程度"""
        if variance == 0:
            # 开局爆发型前3章如果是0差值，标记为high（用auto_adjust修复），避免regenerate_all
            if pattern_name == "开局爆发型" and min_variance >= 3:
                return "high"
            return "high"
        elif variance < min_variance * 0.5:
            return "medium"
        else:
            return "low"
    
    def _calculate_fix_strategy(self, issues: List[Dict], total_chapters: int) -> Dict:
        """计算修复策略"""
        if not issues:
            return {"action": "none", "max_attempts": 0}
        
        # 统计严重程度
        critical_count = sum(1 for i in issues if i.get('severity') == 'critical')
        high_count = sum(1 for i in issues if i.get('severity') == 'high')
        affected_chapters = len(set(
            ch for i in issues for ch in i.get('chapters', [i.get('chapter')])
        ))
        
        # 根据配置选择策略
        strategy_config = self._fix_config.get('fix_strategies', {}).get('levels', {})
        
        if critical_count > 0 or affected_chapters > total_chapters * 0.5:
            level = strategy_config.get('critical', {})
            return {"action": level.get('action', 'regenerate_all'), 
                   "max_attempts": level.get('max_attempts', 3)}
        elif high_count > 0 or affected_chapters >= 3:
            level = strategy_config.get('high', {})
            return {"action": level.get('action', 'ai_partial_fix'), 
                   "max_attempts": level.get('max_attempts', 2)}
        elif affected_chapters > 0:
            level = strategy_config.get('medium', {})
            return {"action": level.get('action', 'auto_adjust'), 
                   "max_attempts": level.get('max_attempts', 1)}
        else:
            level = strategy_config.get('low', {})
            return {"action": level.get('action', 'mark_only'), 
                   "max_attempts": level.get('max_attempts', 0)}
    
    def _calculate_fix_intensity(self, prev: int, current: int, min_variance: int) -> int:
        """计算修复后的强度值"""
        # 如果前一章强度高，当前降低形成反差
        if prev >= 7:
            return max(1, prev - min_variance - (1 if prev > 8 else 0))
        # 如果前一章低，当前升高形成高潮
        else:
            return min(10, prev + min_variance + (1 if prev < 4 else 0))
        
    def plan_next_batch(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,           # ← 新增：当前阶段目标
        previous_summary: Dict = None,  # ← 新增：前序总结
        emotion_curve: List[Dict] = None,  # ← 新增：一阶段情绪曲线（200章）
        bestseller_analysis: Dict = None   # ← 新增：爆款分析数据
    ) -> Dict:
        """
        规划下一批章节
        
        Args:
            start_chapter: 起始章节号
            end_chapter: 结束章节号
            novel_title: 书名
            protagonist_name: 主角名
            stage_goal: 当前阶段目标（来自WorldBuilder）
            previous_summary: 前序批次总结
            emotion_curve: 一阶段生成的200章情绪曲线（用于确保战术规划符合爆款设计）
            bestseller_analysis: 爆款分析数据（钩子公式、爽点模式等）
            
        Returns:
            战术规划字典
        """
        logger.info(f"[TacticalPlanner] 规划第{start_chapter}-{end_chapter}章 | 阶段目标: {stage_goal.get('goal_id', 'Unknown')}")
        
        # 🔥 提取当前窗口对应的一阶段情绪设计
        window_emotion_design = []
        if emotion_curve:
            window_emotion_design = [
                point for point in emotion_curve 
                if start_chapter <= point.get('chapter', 0) <= end_chapter
            ]
            logger.info(f"[TacticalPlanner] 加载窗口情绪设计: {len(window_emotion_design)}章")
        
        # 生成战术规划
        if self.api_client:
            tactical_plan = self._generate_with_ai(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_goal, previous_summary,
                window_emotion_design, bestseller_analysis
            )
        else:
            tactical_plan = self._generate_from_template(
                start_chapter, end_chapter,
                novel_title, protagonist_name,
                stage_goal, previous_summary,
                window_emotion_design, bestseller_analysis
            )
        
        # 🔥 步骤3: 验证情绪设计是否符合模式要求
        chapters = tactical_plan.get('chapters', [])
        if chapters:
            detected_pattern = self._detect_emotion_pattern(stage_goal, start_chapter)
            validation = self._validate_emotion_design(chapters, detected_pattern)
            
            # 将验证结果添加到战术规划中
            tactical_plan['emotion_validation'] = validation
            
            if not validation['is_valid']:
                logger.warning(f"[TacticalPlanner] 情绪设计验证未通过，问题数:{len(validation['issues'])}")
                
                # 启动自动修复
                fixed_chapters, fix_report = self._fix_emotion_design(
                    chapters, validation, stage_goal,
                    novel_title=novel_title, protagonist_name=protagonist_name
                )
                
                # 更新章节和修复报告
                tactical_plan['chapters'] = fixed_chapters
                tactical_plan['emotion_fix_report'] = fix_report
                
                # 修复后再次验证
                re_validation = self._validate_emotion_design(fixed_chapters, detected_pattern)
                tactical_plan['emotion_re_validation'] = re_validation
                
                if re_validation['is_valid']:
                    logger.info(f"[TacticalPlanner] 自动修复后验证通过")
                    tactical_plan['needs_review'] = False
                else:
                    logger.warning(f"[TacticalPlanner] 自动修复后仍有问题，需人工审核")
                    tactical_plan['needs_review'] = True
                    tactical_plan['review_issues'] = re_validation['issues']
            else:
                tactical_plan['needs_review'] = False
        
        return tactical_plan
    
    def _generate_with_ai(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> Dict:
        """使用AI生成战术规划"""
        
        # 构建提示词
        prompt = self._build_tactical_prompt(
            start_chapter, end_chapter,
            novel_title, protagonist_name,
            stage_goal, previous_summary,
            window_emotion_design, bestseller_analysis
        )
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="tactical_planning",
                user_prompt=prompt,
                temperature=0.7,
                purpose="生成战术规划"
            )
            
            if isinstance(response, dict):
                return response
            elif isinstance(response, str):
                return json.loads(response)
        except Exception as e:
            logger.warning(f"AI战术规划生成失败: {e}，使用模板")
        
        return self._generate_from_template(
            start_chapter, end_chapter,
            novel_title, protagonist_name,
            stage_goal, previous_summary
        )
    
    def _build_tactical_prompt(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> str:
        """构建战术规划提示词"""
        
        # 🔥 步骤1: 自动识别阶段目标适用的情绪模式
        detected_pattern = self._detect_emotion_pattern(stage_goal, start_chapter)
        
        # 构建模式指导文本（强制注入提示词）
        pattern_guidance = f"""
## 🔥 强制情绪模式（必须遵循）

基于阶段目标分析，本批次适用：**{detected_pattern['pattern_name']}**

**模式说明**: {detected_pattern['description']}

**推荐情绪弧线**: {' → '.join(detected_pattern['emotion_arc'])}

**关键指标要求**:
"""
        for metric, value in detected_pattern['key_metrics'].items():
            pattern_guidance += f"- {metric}: {value}\n"
        
        pattern_guidance += f"""
**设计原则**:
- 必须严格按照上述情绪弧线设计本批次{start_chapter}-{end_chapter}章
- 相邻章强度差必须≥1，确保有起伏
- 严禁使用机械5章循环

**自检要求**:
生成完成后，请自检情绪设计是否符合上述模式要求。
"""
        
        # 前序总结部分
        summary_text = ""
        if previous_summary:
            summary_text = f"""
## 前序总结（必须承接）

### 已发生关键事件
{chr(10).join([f"- 第{e.get('chapter', '?')}章: {e.get('event', '')}" for e in previous_summary.get('completed_events', [])[:5]])}

### 角色当前状态
- 主角进度/能力层级: {previous_summary.get('character_states', {}).get('protagonist', {}).get('进度', previous_summary.get('character_states', {}).get('protagonist', {}).get('扮演度', '未知'))}
- 主角已解锁能力: {', '.join(previous_summary.get('character_states', {}).get('protagonist', {}).get('新技能', []))}
- 队友态度: {previous_summary.get('character_states', {}).get('ally', {}).get('态度', '未知')}

### 待回收伏笔（必须优先处理）
{chr(10).join([f"- [{h.get('priority', 'medium')}] 第{h.get('chapter', '?')}章埋下: {h.get('content', '')}" for h in previous_summary.get('pending_hooks', [])[:3]])}

### 阶段目标完成度
{previous_summary.get('goal_progress', {}).get(stage_goal.get('goal_id', ''), '未知')}
"""
        else:
            summary_text = "## 前序总结\n这是开局第一批，无前置内容。"
        
        # 🔥 构建爆款设计参考部分
        bestseller_ref = ""
        if window_emotion_design or bestseller_analysis:
            bestseller_parts = ["## 爆款设计参考（必须遵循）\n"]
            
            # 添加窗口情绪设计
            if window_emotion_design:
                bestseller_parts.append("### 一阶段情绪曲线设计（本窗口）")
                bestseller_parts.append("以下是一阶段生成的核心设定审核情绪设计，必须严格遵循：")
                for point in window_emotion_design[:10]:  # 最多显示10章
                    ch = point.get('chapter', '?')
                    emotion = point.get('emotion', '?')
                    intensity = point.get('intensity', '?')
                    bestseller_parts.append(f"- 第{ch}章: {emotion} (强度{intensity})")
                if len(window_emotion_design) > 10:
                    bestseller_parts.append(f"- ... 共{len(window_emotion_design)}章")
                bestseller_parts.append("")
            
            # 添加爆款公式参考
            if bestseller_analysis:
                bs_formula = bestseller_analysis.get('genre_formula', '')
                if bs_formula:
                    bestseller_parts.append(f"### 爆款题材公式\n{bs_formula}\n")
                
                # 添加爆款钩子公式
                bs_hook = bestseller_analysis.get('hook_formula', '')
                if bs_hook:
                    bestseller_parts.append(f"### 爆款钩子公式\n{bs_hook}\n")
                
                # 添加爆款爽点模式
                bs_climax = bestseller_analysis.get('climax_patterns', [])
                if bs_climax:
                    bestseller_parts.append("### 爆款爽点模式")
                    for pattern in bs_climax[:3]:
                        bestseller_parts.append(f"- {pattern}")
                    bestseller_parts.append("")
            
            bestseller_parts.append("⚠️ **重要**: 以上爆款设计优先于固定模板，如果与下面的'情绪循环公式'冲突，以这里的设计为准！")
            bestseller_ref = "\n".join(bestseller_parts)
        
        # 从JSON配置加载模板
        template_config = self._planning_config.get("system_prompt_template", {})
        template = template_config.get("template", "")
        
        if not template:
            raise ValueError("[TacticalPlanner] system_prompt_template 配置未找到，请检查 planning_config.json")
        
        # 使用JSON模板
        variables = {
            "novel_title": novel_title,
            "start_chapter": start_chapter,
            "end_chapter": end_chapter,
            "protagonist_name": protagonist_name,
            "bestseller_ref": bestseller_ref,
            "goal_id": stage_goal.get('goal_id', 'G1'),
            "goal_description": stage_goal.get('description', ''),
            "success_criteria": stage_goal.get('success_criteria', ''),
            "key_deliverables": ', '.join(stage_goal.get('key_deliverables', [])),
            "summary_text": summary_text,
            "pattern_guidance": pattern_guidance  # 🔥 注入模式指导
        }
        
        result = template
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        # 🔥 如果模板中没有pattern_guidance变量，在阶段目标后插入
        if "{pattern_guidance}" not in template:
            # 在"## 阶段目标"后面插入模式指导
            if "## 阶段目标" in result:
                result = result.replace(
                    "## 阶段目标",
                    f"## 阶段目标\n{pattern_guidance}"
                )
        
        return result
    
    def _generate_from_template(
        self,
        start_chapter: int,
        end_chapter: int,
        novel_title: str,
        protagonist_name: str,
        stage_goal: Dict,
        previous_summary: Optional[Dict],
        window_emotion_design: List[Dict] = None,
        bestseller_analysis: Dict = None
    ) -> Dict:
        """
        从模板生成战术规划（使用一阶段情绪设计）
        
        🔥 v2.0 增强：生成包含番茄算法指标、微创新要求、自检清单的详细产物
        """
        
        chapters = []
        num_chapters = end_chapter - start_chapter + 1
        
        # 根据阶段目标确定基调
        goal_id = stage_goal.get('goal_id', 'G1')
        
        # 🔥 构建一阶段情绪设计的查找字典
        emotion_lookup = {}
        if window_emotion_design:
            for point in window_emotion_design:
                ch = point.get('chapter', 0)
                emotion_lookup[ch] = point
        
        # 获取配置
        algo_config = self._planning_config.get('algorithm_requirements', {})
        emotion_config = algo_config.get('emotion_density', {})
        appeal_config = algo_config.get('appeal_density', {})
        hook_config = algo_config.get('hook_requirements', {})
        micro_innov_config = self._planning_config.get('micro_innovation_requirements', {})
        self_check_config = self._planning_config.get('self_check_template', {})
        
        # 🔥 自动识别阶段目标适用的情绪模式
        detected_pattern = self._detect_emotion_pattern(stage_goal, start_chapter)
        pattern_name = detected_pattern['pattern_name']
        emotion_arc = detected_pattern.get('emotion_arc', [])
        
        # 计算本批次整体情绪弧线
        batch_emotion_arc = self._calculate_batch_emotion_arc(start_chapter, end_chapter, emotion_lookup)
        
        for i in range(num_chapters):
            ch_num = start_chapter + i
            
            # 🔥 优先使用一阶段情绪设计（如果存在）
            if ch_num in emotion_lookup:
                point = emotion_lookup[ch_num]
                emotion = point.get('emotion', '期待')
                intensity = point.get('intensity', 6)
                beat_type = self._emotion_to_beat_type(emotion)
                cycle_template = self._get_pattern_template(pattern_name, i, emotion_arc)
            else:
                # 🔥 使用阶段目标驱动的情绪模式
                cycle_template = self._get_pattern_template(pattern_name, i, emotion_arc)
                emotion = cycle_template.get('emotion', '期待')
                intensity = cycle_template.get('intensity', 6)
                beat_type = cycle_template.get('beat_type', '推进')
                
                # 🔥 开局爆发型特殊处理：确保前3章是 9→7→9 的U型曲线
                if pattern_name == "开局爆发型" and ch_num <= 3:
                    opening_intensities = {1: 9, 2: 7, 3: 9}  # 第1章压抑9, 第2章反转7, 第3章爽快9
                    if ch_num in opening_intensities:
                        intensity = opening_intensities[ch_num]
                        # 同步更新情绪类型
                        opening_emotions = {1: "压抑", 2: "反转", 3: "爽快"}
                        emotion = opening_emotions.get(ch_num, emotion)
                        beat_type = self._emotion_to_beat_type(emotion)
                
                # 🔥 通用起伏逻辑：确保相邻章节有起伏（避免连续相同强度）
                elif i > 0 and ch_num > 3:  # 第4章以后，检查与前章的差值
                    prev_ch = chapters[-1] if chapters else None
                    if prev_ch:
                        prev_intensity = prev_ch.get('intensity', 6)
                        # 如果差值<2，调整当前章节强度
                        if abs(intensity - prev_intensity) < 2:
                            # 根据位置决定升还是降
                            if i % 2 == 0:  # 偶数位，升高
                                intensity = min(10, prev_intensity + 2)
                            else:  # 奇数位，降低
                                intensity = max(1, prev_intensity - 2)
            
            # 根据阶段目标生成事件
            event = self._generate_event_for_goal(ch_num, goal_id, i, protagonist_name)
            
            # 确定钩子类型和内容
            hook_type, hook_content = self._generate_hook_design(ch_num, emotion, cycle_template)
            
            # 生成微创新要求
            micro_innovation = self._generate_micro_innovation(ch_num, i % 5, micro_innov_config)
            
            # 构建详细的算法要求
            algorithm_requirements = {
                "emotion_density_target": emotion_config.get('target', '≥2.0/千字'),
                "emotion_words_min": emotion_config.get('min_count_per_chapter', 10),
                "emotion_distribution": emotion_config.get('distribution', '每500字至少1个强烈情绪词'),
                "emotion_vocabulary": self._get_emotion_vocabulary_for_type(emotion, emotion_config),
                "appeal_density_target": appeal_config.get('target', '≥1.5/千字'),
                "appeal_moments_min": appeal_config.get('min_moments_per_chapter', 3),
                "appeal_reaction_chain": appeal_config.get('reaction_chain', '主角行动→具体数字→围观者震惊→弹幕扩散→权威反应→主角内心爽感'),
                "hook_required": hook_config.get('required', True),
                "hook_position": hook_config.get('position', '最后50字'),
                "hook_types": [h.get('type') for h in hook_config.get('types', [])],
                "basic": [
                    "前300字必须出现冲突/悬念",
                    "对话占比≥50%",
                    "每段1-3行，多用换行",
                    "最后50字必须是钩子",
                    "第三人称上帝视角"
                ]
            }
            
            # 生成自检清单
            self_check_items = self._generate_self_check_items(ch_num, emotion, self_check_config)
            
            chapters.append({
                "chapter_number": ch_num,
                "emotion": emotion,
                "intensity": intensity,
                "beat_type": beat_type,
                "function": cycle_template.get('function', '推进剧情'),
                "event": event,
                "purpose": f"推进{goal_id}阶段目标: {stage_goal.get('description', '')}",
                "stage_goal_alignment": f"本章节通过{event}推进{goal_id}的关键交付物",
                "key_requirements": cycle_template.get('key_requirements', []),
                "hook_type": hook_type,
                "hook_content": hook_content,
                "micro_innovation": micro_innovation,
                "algorithm_requirements": algorithm_requirements,
                "self_check_items": self_check_items,
                "algorithm_focus": cycle_template.get('algorithm_focus', ''),
                "previous_chapter_connection": f"承接第{ch_num-1}章结尾" if ch_num > start_chapter else "开局第一章"
            })
        
        return {
            "batch_info": {
                "start_chapter": start_chapter,
                "end_chapter": end_chapter,
                "stage_goal_id": goal_id,
                "stage_goal_description": stage_goal.get('description', ''),
                "stage_goal_success_criteria": stage_goal.get('success_criteria', ''),
                "emotion_arc": batch_emotion_arc,
                "total_chapters_in_batch": num_chapters,
                "generated_at": datetime.now().isoformat()
            },
            "chapters": chapters,
            "batch_algorithm_summary": {
                "emotion_density_target": emotion_config.get('target', '≥2.0/千字'),
                "appeal_density_target": appeal_config.get('target', '≥1.5/千字'),
                "hook_compliance_target": hook_config.get('compliance_rate', '100%'),
                "basic_requirements": algo_config.get('basic', [])
            }
        }
    
    def _generate_event_for_goal(self, ch_num: int, goal_id: str, index: int, protagonist_name: str = "主角") -> str:
        """根据阶段目标生成事件"""
        
        # 使用传入的主角名替换"主角"
        p = protagonist_name
        
        events_map = {
            'G1': [  # establish形象
                f"{p}在平凡生活中被意外选中",
                f"外媒嘲讽大夏选手{p}是酒鬼",
                f"{p}首次展露出人意料的能力",
                f"直播间观众震惊于{p}实力",
                f"{p}发现隐藏机遇的线索"
            ],
            'G2': [  # 解锁酒神咒
                f"{p}收集上古灵酒配方",
                f"{p}遭遇强敌陷入苦战",
                f"{p}触发酒神传承试炼",
                f"{p}领悟酒神咒雏形",
                f"{p}首次用酒神咒斩杀伪神"
            ],
            'G3': [  # 诸神黄昏
                f"{p}突破第一道外部阻碍",
                f"{p}遭遇异界文明先锋",
                f"{p}发现诸神黄昏遗迹",
                f"{p}与高魔文明初次交锋",
                f"{p}建立跨位面盟友"
            ],
            'G4': [  # 揭露真相
                f"{p}发现国运游戏监控痕迹",
                f"{p}遭遇高维文明使者",
                f"{p}揭露游戏真相",
                f"{p}联合其他觉醒者",
                f"{p}向高维意志挥剑"
            ]
        }
        
        events = events_map.get(goal_id, [f"{p}推进剧情"] * 5)
        return events[index % len(events)]
    
    def update_generated_chapters(self, chapters: List[Dict]):
        """更新已生成章节记录"""
        self.generated_chapters.extend(chapters)
        logger.info(f"[TacticalPlanner] 已更新生成记录: {len(self.generated_chapters)}章")
    
    def _emotion_to_beat_type(self, emotion: str) -> str:
        """根据情绪类型推断节拍类型"""
        emotion_beat_map = {
            "压抑": "铺垫",
            "紧张": "冲突",
            "嘲讽": "冲突",
            "质疑": "冲突",
            "小爽快": "反转",
            "反转": "反转",
            "爆发": "反转",
            "反击": "反转",
            "震惊": "渲染",
            "震撼": "渲染",
            "期待": "伏笔",
            "铺垫": "伏笔",
            "绝望": "危机",
            "危机": "危机"
        }
        return emotion_beat_map.get(emotion, "Transition")
    
    def _get_cycle_template(self, cycle_pos: int, emotion: str = None) -> Dict:
        """获取循环模板"""
        cycles = self._planning_config.get('emotion_cycle_template', {}).get('cycles', [])
        if cycle_pos < len(cycles):
            return cycles[cycle_pos]
        # 默认模板
        defaults = [
            {"position": 1, "emotion": "压抑", "intensity_range": "7-8", "beat_type": "铺垫", 
             "function": "积蓄情绪", "key_requirements": ["主角被质疑"], "algorithm_focus": "情绪词密度≥2.0/千字"},
            {"position": 2, "emotion": "紧张", "intensity_range": "8-9", "beat_type": "冲突",
             "function": "矛盾升级", "key_requirements": ["反派嚣张"], "algorithm_focus": "情绪强度8以上"},
            {"position": 3, "emotion": "反转", "intensity_range": "8-9", "beat_type": "反转",
             "function": "主角反击", "key_requirements": ["展现实力"], "algorithm_focus": "爽点密度≥1.5/千字"},
            {"position": 4, "emotion": "震惊", "intensity_range": "7-8", "beat_type": "渲染",
             "function": "放大震惊", "key_requirements": ["震惊反应链"], "algorithm_focus": "三层震惊铺展"},
            {"position": 5, "emotion": "期待", "intensity_range": "6-7", "beat_type": "伏笔",
             "function": "埋下伏笔", "key_requirements": ["具体钩子"], "algorithm_focus": "最后50字必须是钩子"}
        ]
        return defaults[cycle_pos % 5]
    
    def _get_pattern_template(self, pattern_name: str, chapter_index: int, emotion_arc: List[str]) -> Dict:
        """
        根据情绪模式获取章节模板
        
        Args:
            pattern_name: 情绪模式名称
            chapter_index: 章节在批次中的索引（0-5）
            emotion_arc: 情绪弧线定义
            
        Returns:
            章节模板字典
        """
        # 解析情绪弧线
        # 格式如：["压抑(9)", "反转(8)", "爽快(9)", "震惊(8)", "期待(7)"]
        arc_position = chapter_index % len(emotion_arc) if emotion_arc else 0
        arc_item = emotion_arc[arc_position] if emotion_arc else "期待(6)"
        
        # 解析情绪和强度
        import re
        match = re.match(r'(.+)\((\d+)\)', arc_item)
        if match:
            emotion = match.group(1)
            intensity = int(match.group(2))
        else:
            emotion = arc_item
            intensity = 6
        
        # 根据模式返回模板
        pattern_templates = {
            "开局爆发型": {
                0: {"emotion": "压抑", "intensity": 9, "beat_type": "铺垫", 
                    "function": "极端压抑，让读者同情", "key_requirements": ["主角被严重质疑", "绝望处境", "系统即将觉醒"]},
                1: {"emotion": "反转", "intensity": 8, "beat_type": "反转",
                    "function": "系统觉醒，点燃希望", "key_requirements": ["系统激活", "初步反击", "点燃期待"]},
                2: {"emotion": "爽快", "intensity": 9, "beat_type": "高潮",
                    "function": "第一次大打脸", "key_requirements": ["爆发反击", "震惊全场", "建立信心"]}
            },
            "蓄力积累型": {
                0: {"emotion": "小压抑", "intensity": 6, "beat_type": "铺垫",
                    "function": "小挫折，为成长铺垫", "key_requirements": ["小困难", "不透支情绪"]},
                1: {"emotion": "小冲突", "intensity": 7, "beat_type": "冲突",
                    "function": "小挑战，小紧张", "key_requirements": ["适度冲突", "保持节奏"]},
                2: {"emotion": "小爽快", "intensity": 7, "beat_type": "爽点",
                    "function": "小胜利，小收获", "key_requirements": ["小爽点", "积累成就感"]}
            },
            "递进高潮型": {
                0: {"emotion": "紧张", "intensity": 7, "beat_type": "铺垫",
                    "function": "紧张氛围营造", "key_requirements": ["压力升级", "敌人逼近"]},
                1: {"emotion": "冲突升级", "intensity": 8, "beat_type": "冲突",
                    "function": "矛盾激化", "key_requirements": ["正面对抗", "危机四伏"]},
                2: {"emotion": "第一波爽", "intensity": 8, "beat_type": "爽点",
                    "function": "初步胜利", "key_requirements": ["第一层震惊", "小优势"]},
                3: {"emotion": "第二波爽", "intensity": 9, "beat_type": "高潮",
                    "function": "关键突破", "key_requirements": ["第二层震惊", "大优势"]},
                4: {"emotion": "巅峰", "intensity": 9, "beat_type": "大高潮",
                    "function": "最终爆发", "key_requirements": ["第三层震惊", "决定性胜利"]}
            },
            "收束过渡型": {
                0: {"emotion": "满足", "intensity": 7, "beat_type": "收获",
                    "function": "享受成果", "key_requirements": ["收获展示", "成果巩固"]},
                1: {"emotion": "收获", "intensity": 6, "beat_type": "整理",
                    "function": "盘点收获", "key_requirements": ["能力提升", "资源获取"]},
                2: {"emotion": "新线索", "intensity": 6, "beat_type": "伏笔",
                    "function": "埋下新伏笔", "key_requirements": ["新地图线索", "新能力线索"]}
            }
        }
        
        # 获取模式模板
        pattern_template = pattern_templates.get(pattern_name, {})
        
        # 获取当前位置模板，如果没有则使用默认
        position_template = pattern_template.get(chapter_index % len(pattern_template) if pattern_template else 1, {
            "emotion": emotion,
            "intensity": intensity,
            "beat_type": "推进",
            "function": "推进剧情",
            "key_requirements": ["保持节奏"]
        })
        
        # 如果解析出的情绪和模板不一致，以解析的为准（因为可能是一阶段情绪设计）
        if emotion != position_template.get("emotion"):
            position_template = position_template.copy()
            position_template["emotion"] = emotion
            position_template["intensity"] = intensity
        
        return position_template
    
    def _calculate_batch_emotion_arc(self, start: int, end: int, emotion_lookup: Dict) -> str:
        """计算本批次整体情绪弧线"""
        emotions = []
        for ch in range(start, end + 1):
            if ch in emotion_lookup:
                emotions.append(emotion_lookup[ch].get('emotion', '期待'))
        
        if not emotions:
            return "标准5章循环弧线"
        
        # 简化描述
        unique_emotions = list(dict.fromkeys(emotions))  # 保持顺序去重
        return " → ".join(unique_emotions[:5]) + ("..." if len(unique_emotions) > 5 else "")
    
    def _generate_hook_design(self, ch_num: int, emotion: str, cycle_template: Dict) -> Tuple[str, str]:
        """生成钩子设计"""
        hook_types = [
            ("时间锁", "手机突然震动：【倒计时71:59:59，死局已锁定】"),
            ("信息差", "他嘴角微扬，那畜生不知道的是..."),
            ("危机预警", "远处，一道S级气息正在苏醒..."),
            ("身份揭露", "电话那头传来一个不可能的声音：'是我。'"),
            ("反派出招", "'你以为这就完了？'黑袍人冷笑，'游戏才刚开始。'")
        ]
        
        if emotion in ["期待", "伏笔"]:
            idx = ch_num % 5
        else:
            idx = (ch_num + 2) % 5
        
        return hook_types[idx]
    
    def _generate_micro_innovation(self, ch_num: int, cycle_pos: int, config: Dict) -> str:
        """生成微创新要求"""
        innovations = []
        
        # 根据循环位置添加不同的微创新
        if cycle_pos == 0:  # 压抑章
            time_opts = config.get('time_scene', {}).get('recommended', [])
            if time_opts:
                innovations.append(f"时间场景：尝试{time_opts[ch_num % len(time_opts)]}，避开深夜暴雨套路")
        
        elif cycle_pos == 2:  # 反转章
            villain_opts = config.get('villain_humiliation', {}).get('recommended', [])
            if villain_opts:
                innovations.append(f"反派设计：{villain_opts[ch_num % len(villain_opts)]}")
        
        # 配角设计
        roles = config.get('supporting_roles', [])
        if roles:
            innovations.append(f"配角要求：至少设计2-3个配角（{', '.join([r.get('type', '') for r in roles])}）")
        
        return "；".join(innovations) if innovations else "保持套路新鲜感，避免 cliché"
    
    def _get_emotion_vocabulary_for_type(self, emotion: str, config: Dict) -> List[str]:
        """获取情绪词汇"""
        vocab = config.get('vocabulary', {})
        
        emotion_map = {
            "压抑": ["oppression"],
            "绝望": ["oppression"],
            "紧张": ["anger"],
            "愤怒": ["anger"],
            "反转": ["twist"],
            "震惊": ["shock"],
            "爽快": ["satisfaction"],
            "期待": ["satisfaction"]
        }
        
        keys = emotion_map.get(emotion, [])
        words = []
        for k in keys:
            words.extend(vocab.get(k, []))
        return words[:6]  # 返回前6个词汇
    
    def _generate_self_check_items(self, ch_num: int, emotion: str, config: Dict) -> List[str]:
        """生成自检清单"""
        steps = config.get('steps', [])
        items = []
        
        for step in steps:
            step_name = step.get('name', '')
            step_items = step.get('items', [])
            items.extend([f"【{step_name}】{item}" for item in step_items])
        
        return items
    
    # ==================== 情绪设计修复方法 ====================

    def _fix_emotion_design(self, chapters, validation, stage_goal, **context):
        """修复情绪设计问题"""
        fix_strategy = validation.get('fix_strategy', {})
        action = fix_strategy.get('action', 'none')
        max_attempts = fix_strategy.get('max_attempts', 0)
        
        if action == 'none' or max_attempts == 0:
            return chapters, {"fixed": False, "reason": "无需修复"}
        
        fix_report = {
            "fixed": False, "strategy": action, "max_attempts": max_attempts,
            "attempts": 0, "details": [],
            "before_issues": len(validation.get('issues', []))
        }
        
        fixes = validation.get('fixes', {})
        problem_chapters = list(fixes.keys())[:5]
        logger.info(f"[TacticalPlanner] 启动自动修复 | 策略:{action} | 问题章节:{problem_chapters}")
        
        current_chapters = chapters
        for attempt in range(max_attempts):
            fix_report['attempts'] = attempt + 1
            
            if action == 'regenerate_all':
                current_chapters = self._regenerate_with_stronger_prompt(
                    current_chapters, validation, stage_goal, **context
                )
            elif action == 'ai_partial_fix':
                current_chapters = self._ai_fix_chapters(current_chapters, validation, stage_goal, **context)
            elif action == 'auto_adjust':
                current_chapters = self._auto_adjust_values(current_chapters, fixes)
            
            if current_chapters:
                detected_pattern = self._detect_emotion_pattern(stage_goal, current_chapters[0].get('chapter_number', 1))
                re_validation = self._validate_emotion_design(current_chapters, detected_pattern)
                
                if re_validation['is_valid']:
                    fix_report['fixed'] = True
                    fix_report['after_issues'] = 0
                    logger.info(f"[TacticalPlanner] 自动修复成功 | 策略:{action} | 尝试{attempt+1}次")
                    break
                else:
                    fix_report['after_issues'] = len(re_validation.get('issues', []))
                    if attempt < max_attempts - 1:
                        validation = re_validation
        
        if not fix_report['fixed']:
            logger.warning(f"[TacticalPlanner] 自动修复失败 | 已达最大尝试次数{max_attempts}")
        
        return current_chapters, fix_report

    def _ai_fix_chapters(self, chapters, validation, stage_goal, **context):
        """使用AI修复特定章节"""
        fixes = validation.get('fixes', {})
        if not fixes:
            return chapters
        
        fixed_chapters = []
        for ch in chapters:
            ch_num = ch.get('chapter_number')
            if ch_num in fixes:
                fix = fixes[ch_num]
                field = fix.get('field')
                try:
                    if field == 'intensity':
                        fixed_ch = self._fix_chapter_intensity(ch, fix)
                    elif field == 'hook_content':
                        fixed_ch = self._fix_chapter_hook(ch, fix)
                    else:
                        fixed_ch = ch.copy()
                    fixed_chapters.append(fixed_ch)
                    logger.info(f"[TacticalPlanner]   修复第{ch_num}章: {field} {fix.get('old_value')}->{fix.get('new_value')}")
                except Exception as e:
                    logger.error(f"[TacticalPlanner] 修复第{ch_num}章失败: {e}")
                    ch_copy = ch.copy()
                    ch_copy['_fix_failed'] = True
                    fixed_chapters.append(ch_copy)
            else:
                fixed_chapters.append(ch)
        return fixed_chapters

    def _fix_chapter_intensity(self, chapter, fix):
        """修复章节强度值"""
        ch_copy = chapter.copy()
        new_intensity = fix.get('new_value')
        old_intensity = fix.get('old_value')
        ch_copy['intensity'] = new_intensity
        ch_copy['_auto_fixed'] = True
        ch_copy['_fix_note'] = f"强度从{old_intensity}调整为{new_intensity}"
        return ch_copy

    def _fix_chapter_hook(self, chapter, fix):
        """为章节添加钩子"""
        ch_copy = chapter.copy()
        emotion = chapter.get('emotion', '期待')
        hook_templates = {
            '压抑': ['绝望之际，手机突然震动：【系统激活倒计时：71:59:59】', '他抬头，发现所有人都在看他'],
            '反转': ['他嘴角微扬，他们不知道的是，这一切都在计划之中', '远处，一道S级气息正在苏醒'],
            '爽快': ['就在他享受胜利时，一条匿名短信让他瞳孔骤缩', '直播间弹幕突然静止'],
            '震惊': ['电话那头传来一个声音：游戏才刚开始', '他低头看着手中的物品，发现底部刻着一行小字'],
            '期待': ['明天，就是最后的期限', '他不知道的是，此刻正有无数双眼睛盯着屏幕']
        }
        import random
        templates = hook_templates.get(emotion, hook_templates['期待'])
        ch_copy['hook_content'] = random.choice(templates)
        ch_copy['hook_type'] = 'auto_generated'
        ch_copy['_auto_fixed'] = True
        return ch_copy

    def _auto_adjust_values(self, chapters, fixes):
        """自动调整数值"""
        fixed_chapters = []
        for ch in chapters:
            ch_num = ch.get('chapter_number')
            if ch_num in fixes:
                fix = fixes[ch_num]
                field = fix.get('field')
                ch_copy = ch.copy()
                if field == 'intensity':
                    ch_copy['intensity'] = fix.get('new_value')
                    ch_copy['_auto_fixed'] = True
                    ch_copy['_fix_note'] = f"强度从{fix.get('old_value')}调整为{fix.get('new_value')}"
                elif field == 'hook_content':
                    ch_copy = self._fix_chapter_hook(ch, fix)
                fixed_chapters.append(ch_copy)
            else:
                fixed_chapters.append(ch)
        return fixed_chapters

    def _regenerate_with_stronger_prompt(self, chapters, validation, stage_goal, **context):
        """使用更强约束重新生成"""
        logger.info("[TacticalPlanner] 重新生成批次 | 增强约束")
        if not chapters:
            return []
        
        # 使用模板重新生成
        start_chapter = chapters[0].get('chapter_number', 1)
        end_chapter = chapters[-1].get('chapter_number', start_chapter + 5)
        novel_title = context.get('novel_title', '未知')
        protagonist_name = context.get('protagonist_name', '主角')
        
        result = self._generate_from_template(
            start_chapter, end_chapter, novel_title, protagonist_name,
            stage_goal, None, [], {}
        )
        
        # 返回章节列表
        return result.get('chapters', [])


# 便捷函数
def create_tactical_plan(
    start_chapter: int,
    end_chapter: int,
    novel_title: str,
    protagonist_name: str,
    stage_goal: Dict,
    previous_summary: Optional[Dict] = None,
    api_client=None
) -> Dict:
    """便捷函数：创建战术规划"""
    planner = TacticalPlanner(api_client)
    return planner.plan_next_batch(
        start_chapter, end_chapter,
        novel_title, protagonist_name,
        stage_goal, previous_summary
    )
