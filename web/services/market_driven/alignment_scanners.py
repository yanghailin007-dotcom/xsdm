# -*- coding: utf-8 -*-
"""
Alignment Scanners - P0轮硬规则扫描器集合
负责发现题材越界、数值矛盾、标签冲突、玄幻化设定
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher

from web.services.market_driven.genre_techniques_loader import load_genre_techniques

logger = logging.getLogger(__name__)


class AlignmentIssue:
    """对齐问题条目"""
    
    def __init__(self, severity: str, category: str, source_file: str,
                 field_path: str, message: str, suggestion: str = "",
                 fix_strategy: str = "auto", details: Dict = None):
        self.severity = severity  # critical/high/medium/low
        self.category = category
        self.source_file = source_file
        self.field_path = field_path
        self.message = message
        self.suggestion = suggestion
        self.fix_strategy = fix_strategy  # auto / ai / manual
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "source_file": self.source_file,
            "field_path": self.field_path,
            "message": self.message,
            "suggestion": self.suggestion,
            "fix_strategy": self.fix_strategy,
            "details": self.details,
        }


class BaseScanner:
    """扫描器基类"""
    
    def __init__(self, genre: str, project_path: Path):
        self.genre = genre
        self.project_path = Path(project_path)
        self.products_path = self.project_path / "phase_one_products"
    
    def scan(self, data: Dict[str, Any]) -> List[AlignmentIssue]:
        raise NotImplementedError
    
    def _load_json_file(self, filename: str, default: Any = None) -> Any:
        path = self.products_path / filename
        if not path.exists():
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[Scanner] 加载 {filename} 失败: {e}")
            return default
    
    def _extract_text_recursive(self, obj: Any, path: str = "") -> List[tuple]:
        """递归提取所有字符串及其路径"""
        results = []
        if isinstance(obj, str):
            results.append((path, obj))
        elif isinstance(obj, dict):
            for k, v in obj.items():
                results.extend(self._extract_text_recursive(v, f"{path}.{k}" if path else k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                results.extend(self._extract_text_recursive(v, f"{path}[{i}]"))
        return results
    
    def _contains_any(self, text: str, keywords: List[str]) -> Optional[str]:
        """检查文本中是否包含任一关键词，返回命中的关键词"""
        for kw in keywords:
            if kw in text:
                return kw
        return None


# ==================== 扩展的题材特定配置 ====================

FANTASY_KEYWORDS_BY_GENRE = {
    "通用": {
        "critical": ["领域", "绝对防御", "吞噬", "法则", "神格", "位面", "维度"],
        "high": ["技能", "Buff", "光环", "暴击", "觉醒", "进化", "血脉", "天赋神通"],
    },
    "神豪文": {
        "critical": ["领域", "绝对防御", "吞噬", "法则", "神格", "位面", "维度", "灵气", "修仙", "渡劫"],
        "high": ["技能", "Buff", "光环", "暴击", "觉醒", "进化", "兵王", "战神", "战力天花板", "龙组"],
    },
    "国运文": {
        "critical": ["花钱返利", "神豪", "股票", "股市", "泡妞", "夜店", "奢侈品"],
        "high": ["劳斯莱斯", "法拉利", "billionaire", "首富", "夜店"],
    },
    "末日求生文": {
        "critical": ["修仙", "灵气", "渡劫", "飞升", "魔法", "斗气", "武魂"],
        "high": ["领域", "觉醒", "进化", "异能", "神格"],
    },
    "种田文": {
        "critical": ["系统", "签到", "万倍返利", "百倍返利", "修仙", "灵气"],
        "high": ["领域", "吞噬", "觉醒", "神格"],
    },
    "奶爸文": {
        "critical": ["修仙", "渡劫", "飞升", "魔法", "斗气", "灵气"],
        "high": ["领域", "觉醒", "进化", "末日", "丧尸"],
    },
}

CONFLICT_PAIRS = {
    "通用": [
        (["善良仁慈", "仁慈善良", "心慈手软"], ["绝不圣母", "斩草除根", "心狠手辣"]),
        (["胆小懦弱", "懦弱胆小", "软弱无能"], ["杀伐果断", "果断决绝", "铁血无情"]),
        (["优柔寡断", "犹豫不决", "瞻前顾后"], ["果断决绝", "雷厉风行", "当机立断"]),
    ],
    "神豪文": [
        (["低调内敛", "低调隐忍", "隐忍低调", "淡泊名利"], ["消费狂魔", "张扬跋扈", "高调炫富", "降维打击", "锋芒毕露"]),
        (["淡泊名利", "不慕虚荣"], ["追求财富", "金钱至上", "消费狂魔"]),
    ],
    "国运文": [
        (["个人主义", "自私自利", "明哲保身"], ["为国牺牲", "民族大义", "舍己为人"]),
        (["冷漠无情", "冷酷无情"], ["民族大义", "家国情怀", "为国为民"]),
    ],
    "末日求生文": [
        (["圣母心", "圣母", "心慈手软"], ["冷血生存", "弱肉强食", "斩草除根"]),
    ],
}


# ==================== P0-1: 题材防火墙扫描器 ====================

class GenreFirewallScanner(BaseScanner):
    """题材防火墙扫描器：检测禁用词和越界概念"""
    
    def scan(self, data: Dict[str, Any]) -> List[AlignmentIssue]:
        issues = []
        
        # 加载题材配置
        forbidden_keywords = []
        try:
            gt = load_genre_techniques(self.genre)
            guardrails = gt.raw_data.get("final_plan_guardrails", {})
            gf_guard = guardrails.get("golden_finger", {})
            forbidden_keywords.extend(gf_guard.get("forbidden_keywords", []))
            
            fe_data = gt.raw_data.get("forbidden_elements", {})
            for item in fe_data.get("items", []):
                forbidden_keywords.append(item.get("element", ""))
                forbidden_keywords.extend(item.get("examples", []))
            
            forbidden_keywords = [w.strip() for w in forbidden_keywords if w and len(w.strip()) > 0]
        except Exception as e:
            logger.warning(f"[GenreFirewallScanner] 加载题材配置失败: {e}")
        
        # 文件 -> 扫描字段映射
        scan_targets = [
            ("世界观设定.json", ["world_overview", "power_system", "social_structure", "factions", "world_rules", "key_locations"]),
            ("升级路线.json", ["protagonist_growth", "ability_system_progression", "key_abilities", "key_relationships_development"]),
            ("完整方案.json", ["golden_finger", "protagonist", "worldview", "core_conflict", "opening_design"]),
            ("角色设计.json", ["protagonist", "core_allies", "main_antagonists"]),
            ("势力设定.json", ["factions", "faction_relationships", "power_dynamics"]),
        ]
        
        for filename, top_fields in scan_targets:
            file_data = self._load_json_file(filename, {})
            if not file_data:
                continue
            
            # 提取所有文本
            all_texts = self._extract_text_recursive(file_data)
            for field_path, text in all_texts:
                # 检查是否命中禁用词
                hit = self._contains_any(text, forbidden_keywords)
                if hit:
                    issues.append(AlignmentIssue(
                        severity="critical",
                        category="genre_firewall",
                        source_file=filename,
                        field_path=field_path,
                        message=f"文本中包含题材禁用词 '{hit}'",
                        suggestion=f"将 '{hit}' 替换为符合 '{self.genre}' 题材的现实/领域表达",
                        fix_strategy="ai",
                        details={"hit_word": hit, "context": text[:80]}
                    ))
        
        return issues


# ==================== P0-2: 升级路线玄幻化扫描器 ====================

class ProgressionFantasyScanner(BaseScanner):
    """升级路线玄幻化扫描器：检测游戏/玄幻词汇"""
    
    def scan(self, data: Dict[str, Any]) -> List[AlignmentIssue]:
        issues = []
        
        # 获取题材特定玄幻词表
        genre_keywords = FANTASY_KEYWORDS_BY_GENRE.get(self.genre, FANTASY_KEYWORDS_BY_GENRE.get("通用", {}))
        critical_words = genre_keywords.get("critical", [])
        high_words = genre_keywords.get("high", [])
        
        # 扫描升级路线
        progression = self._load_json_file("升级路线.json", {})
        if progression:
            all_texts = self._extract_text_recursive(progression)
            for field_path, text in all_texts:
                hit = self._contains_any(text, critical_words)
                if hit:
                    issues.append(AlignmentIssue(
                        severity="critical",
                        category="progression_fantasy",
                        source_file="升级路线.json",
                        field_path=field_path,
                        message=f"升级路线中出现玄幻/游戏化关键词 '{hit}'",
                        suggestion=_get_fantasy_replacement(hit),
                        fix_strategy="ai",
                        details={"hit_word": hit, "context": text[:80]}
                    ))
                    continue
                
                hit = self._contains_any(text, high_words)
                if hit:
                    issues.append(AlignmentIssue(
                        severity="high",
                        category="progression_fantasy",
                        source_file="升级路线.json",
                        field_path=field_path,
                        message=f"升级路线中出现游戏化/异能关键词 '{hit}'",
                        suggestion=_get_fantasy_replacement(hit),
                        fix_strategy="ai",
                        details={"hit_word": hit, "context": text[:80]}
                    ))
        
        # 同时扫描完整方案中的 golden_finger 和 protagonist
        plan = self._load_json_file("完整方案.json", {})
        if plan:
            gf = plan.get("golden_finger", {})
            for key in ["abilities", "restrictions"]:
                if key in gf:
                    all_texts = self._extract_text_recursive(gf[key])
                    for field_path, text in all_texts:
                        hit = self._contains_any(text, critical_words)
                        if hit:
                            issues.append(AlignmentIssue(
                                severity="critical",
                                category="progression_fantasy",
                                source_file="完整方案.json",
                                field_path=f"golden_finger.{key}.{field_path}",
                                message=f"金手指设定中出现玄幻关键词 '{hit}'",
                                suggestion=_get_fantasy_replacement(hit),
                                fix_strategy="ai",
                                details={"hit_word": hit, "context": text[:80]}
                            ))
            
            protagonist = plan.get("protagonist", {})
            growth_arc = protagonist.get("growth_arc", "")
            if growth_arc:
                hit = self._contains_any(growth_arc, critical_words)
                if hit:
                    issues.append(AlignmentIssue(
                        severity="critical",
                        category="progression_fantasy",
                        source_file="完整方案.json",
                        field_path="protagonist.growth_arc",
                        message=f"主角成长弧线中出现玄幻关键词 '{hit}'",
                        suggestion=_get_fantasy_replacement(hit),
                        fix_strategy="ai",
                        details={"hit_word": hit, "context": growth_arc[:80]}
                    ))
        
        return issues


def _get_fantasy_replacement(word: str) -> str:
    """获取玄幻词汇的替换建议"""
    replacements = {
        "领域": "商业影响力辐射范围 / 资本布局网络",
        "绝对防御": "顶级安保体系 / 法律防火墙 / 风险对冲机制",
        "吞噬": "收购 / 并购 / 控股",
        "技能": "商业策略 / 投资手段 / 运营方法",
        "Buff": "资源加持 / 资金注入 / 政策支持",
        "光环": "社会声望 / 品牌效应 / 口碑红利",
        "暴击": "高回报投资 / 超额收益 / 杠杆放大",
        "觉醒": "认知升级 / 战略转型 / 模式创新",
        "进化": "体系升级 / 迭代优化 / 规模扩张",
    }
    return replacements.get(word, "替换为符合题材现实的等价表达")


# ==================== P0-3: 角色标签矛盾扫描器 ====================

class CharacterTagScanner(BaseScanner):
    """角色标签矛盾扫描器"""
    
    def scan(self, data: Dict[str, Any]) -> List[AlignmentIssue]:
        issues = []
        
        char_design = self._load_json_file("角色设计.json", {})
        if not char_design:
            return issues
        
        protagonist = char_design.get("protagonist", {})
        if not isinstance(protagonist, dict):
            return issues
        
        traits = protagonist.get("traits", [])
        personality = protagonist.get("personality_description", "")
        
        # 加载互斥对
        conflict_pairs = CONFLICT_PAIRS.get("通用", [])
        if self.genre in CONFLICT_PAIRS:
            conflict_pairs.extend(CONFLICT_PAIRS[self.genre])
        
        # 检查 traits 中的互斥
        if isinstance(traits, list):
            trait_text = ",".join(traits)
            for group_a, group_b in conflict_pairs:
                has_a = any(ta in trait_text for ta in group_a)
                has_b = any(tb in trait_text for tb in group_b)
                if has_a and has_b:
                    issues.append(AlignmentIssue(
                        severity="high",
                        category="character_tag_conflict",
                        source_file="角色设计.json",
                        field_path="protagonist.traits",
                        message=f"主角标签存在矛盾: {group_a[0]} 与 {group_b[0]} 互斥",
                        suggestion=f"移除与 personality_description 不一致的标签，保留更贴合主角行为逻辑的一方",
                        fix_strategy="auto",
                        details={"group_a": group_a, "group_b": group_b, "traits": traits}
                    ))
        
        # 检查 personality_description 与 traits 的语义一致性（简化版）
        if personality and isinstance(traits, list):
            for group_a, group_b in conflict_pairs:
                # 如果 personality 明确偏向 B，但 traits 中有 A
                has_trait_a = any(ta in trait_text for ta in group_a)
                pers_bias_b = any(tb in personality for tb in group_b)
                if has_trait_a and pers_bias_b:
                    # 如果已经报过互斥，跳过避免重复
                    already_reported = any(
                        i.category == "character_tag_conflict" and i.field_path == "protagonist.traits"
                        for i in issues
                    )
                    if not already_reported:
                        issues.append(AlignmentIssue(
                            severity="high",
                            category="character_tag_conflict",
                            source_file="角色设计.json",
                            field_path="protagonist.traits",
                            message=f"personality_description 偏向 '{group_b[0]}'，但 traits 中包含 '{group_a[0]}'",
                            suggestion=f"移除 '{group_a[0]}'，使 traits 与 personality_description 一致",
                            fix_strategy="auto",
                            details={"personality_keyword": group_b[0], "conflicting_trait": group_a[0]}
                        ))
        
        # 检查配角中的兵王/战神（主要针对神豪文，但通用也可扫描）
        all_allies = char_design.get("core_allies", []) if isinstance(char_design.get("core_allies"), list) else []
        antagonists = char_design.get("main_antagonists", {}) if isinstance(char_design.get("main_antagonists"), dict) else {}
        
        for ally in all_allies:
            identity = ally.get("identity", "")
            if isinstance(identity, str):
                hit = self._contains_any(identity, ["兵王", "战神", "战力天花板", "龙组", "隐世家族"])
                if hit:
                    issues.append(AlignmentIssue(
                        severity="high",
                        category="character_tag_conflict",
                        source_file="角色设计.json",
                        field_path=f"core_allies.{ally.get('name','?')}.identity",
                        message=f"配角设定出现跨题材标签 '{hit}'",
                        suggestion="将身份改为现实可解释的角色（如'顶尖安保顾问'、'私人保镖队长'）",
                        fix_strategy="ai",
                        details={"hit_word": hit, "identity": identity}
                    ))
        
        return issues


# ==================== P0-4: 跨产物数值一致性扫描器 ====================

class CrossProductConsistencyScanner(BaseScanner):
    """跨产物数值一致性扫描器"""
    
    def scan(self, data: Dict[str, Any]) -> List[AlignmentIssue]:
        issues = []
        
        plan = self._load_json_file("完整方案.json", {})
        gf_design = self._load_json_file("金手指设计.json", {})
        progression = self._load_json_file("升级路线.json", {})
        char_design = self._load_json_file("角色设计.json", {})
        stage_goals = self._load_json_file("阶段目标.json", [])
        emotion_curve = self._load_json_file("情绪曲线.json", [])
        
        # 1. 金手指名称一致性
        plan_gf_name = _safe_nested_get(plan, ["golden_finger", "basic_info", "name"]) or \
                       _safe_nested_get(plan, ["golden_finger", "name"]) or ""
        design_gf_name = _safe_nested_get(gf_design, ["basic_info", "name"]) or \
                         _safe_nested_get(gf_design, ["name"]) or ""
        
        if plan_gf_name and design_gf_name and plan_gf_name != design_gf_name:
            issues.append(AlignmentIssue(
                severity="high",
                category="cross_product_consistency",
                source_file="完整方案.json / 金手指设计.json",
                field_path="golden_finger.name",
                message=f"金手指名称不一致: 完整方案中为'{plan_gf_name}'，金手指设计中为'{design_gf_name}'",
                suggestion=f"以完整方案为基准，统一为'{plan_gf_name}'",
                fix_strategy="auto",
                details={"plan_value": plan_gf_name, "design_value": design_gf_name}
            ))
        
        # 2. 返利倍率一致性（神豪文核心数值）
        if "神豪" in self.genre:
            plan_initial = _safe_nested_get(plan, ["golden_finger", "abilities", "initial"]) or ""
            design_initial = _safe_nested_get(gf_design, ["abilities", "initial"]) or ""
            
            plan_rates = _extract_rate_keywords(plan_initial)
            design_rates = _extract_rate_keywords(design_initial)
            
            if progression and isinstance(progression, dict):
                pg_milestones = progression.get("protagonist_growth", {}).get("milestones", [])
                prog_rates = set()
                for ms in pg_milestones:
                    ac = ms.get("ability_change", "")
                    prog_rates.update(_extract_rate_keywords(ac))
            else:
                prog_rates = set()
            
            all_rates = plan_rates | design_rates | prog_rates
            if len(all_rates) >= 2:
                issues.append(AlignmentIssue(
                    severity="critical",
                    category="cross_product_consistency",
                    source_file="完整方案.json / 金手指设计.json / 升级路线.json",
                    field_path="golden_finger.abilities.initial / milestones.ability_change",
                    message=f"返利倍率描述存在多处矛盾: {sorted(all_rates)}",
                    suggestion=f"以完整方案为基准，统一倍率描述。建议基准值: {plan_initial or design_initial}",
                    fix_strategy="auto",
                    details={"conflicting_rates": sorted(all_rates), "plan_rates": sorted(plan_rates), "design_rates": sorted(design_rates), "prog_rates": sorted(prog_rates)}
                ))
        
        # 3. 主角标签一致性
        plan_traits = _safe_nested_get(plan, ["protagonist", "traits"]) or []
        char_traits = _safe_nested_get(char_design, ["protagonist", "traits"]) or []
        
        if isinstance(plan_traits, list) and isinstance(char_traits, list):
            plan_set = set(plan_traits)
            char_set = set(char_traits)
            if plan_set != char_set and (plan_set and char_set):
                issues.append(AlignmentIssue(
                    severity="medium",
                    category="cross_product_consistency",
                    source_file="完整方案.json / 角色设计.json",
                    field_path="protagonist.traits",
                    message=f"主角标签在不同产物中不一致: 完整方案{sorted(plan_set)} vs 角色设计{sorted(char_set)}",
                    suggestion="以角色设计.json为基准统一traits（因为它更详细），或取两者交集",
                    fix_strategy="auto",
                    details={"plan_traits": sorted(plan_set), "char_traits": sorted(char_set)}
                ))
        
        # 4. 阶段目标与情绪曲线章节对齐
        if isinstance(stage_goals, list) and isinstance(emotion_curve, list):
            max_stage_ch = 0
            for sg in stage_goals:
                ec = sg.get("expected_chapters", "")
                if isinstance(ec, str):
                    m = re.search(r"(\d+)-(\d+)", ec)
                    if m:
                        max_stage_ch = max(max_stage_ch, int(m.group(2)))
            
            max_emotion_ch = max((e.get("chapter", 0) for e in emotion_curve), default=0)
            
            if max_stage_ch > 0 and max_emotion_ch > 0 and abs(max_stage_ch - max_emotion_ch) > 2:
                issues.append(AlignmentIssue(
                    severity="medium",
                    category="cross_product_consistency",
                    source_file="阶段目标.json / 情绪曲线.json",
                    field_path="expected_chapters / chapter",
                    message=f"阶段目标覆盖到第{max_stage_ch}章，但情绪曲线只规划到第{max_emotion_ch}章，两者不匹配",
                    suggestion="将情绪曲线延伸至与阶段目标对齐的章节数",
                    fix_strategy="ai",
                    details={"max_stage_chapter": max_stage_ch, "max_emotion_chapter": max_emotion_ch}
                ))
        
        return issues


def _safe_nested_get(obj: Any, keys: List[str], default: Any = "") -> Any:
    """安全嵌套获取"""
    for k in keys:
        if isinstance(obj, dict) and k in obj:
            obj = obj[k]
        else:
            return default
    return obj


def _extract_rate_keywords(text: str) -> set:
    """从文本中提取倍率关键词（如万倍、双倍、100倍）"""
    if not isinstance(text, str):
        return set()
    
    results = set()
    # 数字+倍 如 100倍、10倍、1倍
    for m in re.finditer(r'(\d+)\s*倍', text):
        results.add(m.group(0))
    # 常见中文倍率词
    for word in ["万倍", "千倍", "百倍", "十倍", "双倍", "单倍", "一倍"]:
        if word in text:
            results.add(word)
    return results


# ==================== 扫描器聚合入口 ====================

class AlignmentScannerSet:
    """扫描器集合"""
    
    def __init__(self, genre: str, project_path: Path):
        self.genre = genre
        self.project_path = Path(project_path)
        self.scanners = [
            GenreFirewallScanner(genre, project_path),
            ProgressionFantasyScanner(genre, project_path),
            CharacterTagScanner(genre, project_path),
            CrossProductConsistencyScanner(genre, project_path),
        ]
    
    def scan_all(self) -> List[AlignmentIssue]:
        """执行所有扫描"""
        all_issues = []
        for scanner in self.scanners:
            try:
                issues = scanner.scan({})
                all_issues.extend(issues)
                logger.info(f"[{scanner.__class__.__name__}] 发现 {len(issues)} 个问题")
            except Exception as e:
                logger.error(f"[{scanner.__class__.__name__}] 扫描异常: {e}", exc_info=True)
        
        # 按严重程度排序
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        all_issues.sort(key=lambda x: severity_order.get(x.severity, 99))
        return all_issues
