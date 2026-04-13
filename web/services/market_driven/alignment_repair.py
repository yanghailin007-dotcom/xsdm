# -*- coding: utf-8 -*-
"""
Alignment Repair - P1轮修复逻辑
包含：自动修复 + AI辅助修复
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from web.services.market_driven.alignment_scanners import AlignmentIssue, _get_fantasy_replacement, CONFLICT_PAIRS

logger = logging.getLogger(__name__)


class AutoRepair:
    """自动修复器：处理无需AI的规则修复"""
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.products_path = self.project_path / "phase_one_products"
    
    def repair(self, issues: List[AlignmentIssue]) -> Dict[str, Any]:
        """
        执行自动修复
        返回: {"fixed_count": int, "remaining_issues": List[AlignmentIssue], "modified_files": List[str]}
        """
        fixed_count = 0
        remaining = []
        modified_files = set()
        
        # 按文件加载数据缓存
        file_cache = {}
        
        def _get_file(filename: str) -> Any:
            if filename not in file_cache:
                path = self.products_path / filename
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            file_cache[filename] = json.load(f)
                    except Exception as e:
                        logger.warning(f"[AutoRepair] 加载 {filename} 失败: {e}")
                        file_cache[filename] = None
                else:
                    file_cache[filename] = None
            return file_cache.get(filename)
        
        def _save_file(filename: str, data: Any):
            path = self.products_path / filename
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                modified_files.add(filename)
            except Exception as e:
                logger.error(f"[AutoRepair] 保存 {filename} 失败: {e}")
        
        for issue in issues:
            if issue.fix_strategy != "auto":
                remaining.append(issue)
                continue
            
            try:
                repaired = False
                
                if issue.category == "cross_product_consistency":
                    repaired = self._repair_consistency(issue, _get_file, _save_file)
                
                elif issue.category == "character_tag_conflict":
                    repaired = self._repair_tag_conflict(issue, _get_file, _save_file)
                
                if repaired:
                    fixed_count += 1
                else:
                    remaining.append(issue)
                    
            except Exception as e:
                logger.error(f"[AutoRepair] 修复失败 {issue.message}: {e}")
                remaining.append(issue)
        
        return {
            "fixed_count": fixed_count,
            "remaining_issues": remaining,
            "modified_files": sorted(list(modified_files)),
        }
    
    def _repair_consistency(self, issue: AlignmentIssue, get_file, save_file) -> bool:
        """修复跨产物一致性问题"""
        details = issue.details
        
        # 金手指名称不一致 -> 以完整方案为基准
        if "golden_finger.name" in issue.field_path and "plan_value" in details:
            target_name = details["plan_value"]
            gf_design = get_file("金手指设计.json")
            if gf_design and isinstance(gf_design, dict):
                if "basic_info" in gf_design and isinstance(gf_design["basic_info"], dict):
                    gf_design["basic_info"]["name"] = target_name
                else:
                    gf_design["name"] = target_name
                save_file("金手指设计.json", gf_design)
                logger.info(f"[AutoRepair] 统一金手指名称为: {target_name}")
                return True
        
        # 返利倍率矛盾 -> 无法纯自动修复（需要AI重写句子），降级为标记
        if "conflicting_rates" in details:
            # 这个需要AI来重写具体句子，自动修复器不处理
            return False
        
        # 主角标签不一致 -> 以角色设计为基准
        if "protagonist.traits" in issue.field_path and "char_traits" in details:
            char_traits = details.get("char_traits", [])
            plan = get_file("完整方案.json")
            if plan and isinstance(plan, dict) and "protagonist" in plan:
                plan["protagonist"]["traits"] = list(char_traits)
                save_file("完整方案.json", plan)
                logger.info(f"[AutoRepair] 统一主角标签为: {char_traits}")
                return True
        
        return False
    
    def _repair_tag_conflict(self, issue: AlignmentIssue, get_file, save_file) -> bool:
        """修复角色标签矛盾"""
        details = issue.details
        
        if "protagonist.traits" in issue.field_path:
            char_design = get_file("角色设计.json")
            if not char_design or not isinstance(char_design, dict):
                return False
            
            protagonist = char_design.get("protagonist", {})
            if not isinstance(protagonist, dict):
                return False
            
            traits = protagonist.get("traits", [])
            personality = protagonist.get("personality_description", "")
            
            if not isinstance(traits, list):
                return False
            
            group_a = details.get("group_a", [])
            group_b = details.get("group_b", [])
            
            # 决策：如果 personality_description 包含 group_b 的词，则移除 group_a
            has_bias_b = any(tb in personality for tb in group_b)
            
            removed = False
            if has_bias_b:
                # 移除 group_a 中的词
                new_traits = [t for t in traits if not any(ta in t for ta in group_a)]
                if len(new_traits) != len(traits):
                    protagonist["traits"] = new_traits
                    removed = True
            else:
                # 默认移除 group_b 中的词（保守策略）
                new_traits = [t for t in traits if not any(tb in t for tb in group_b)]
                if len(new_traits) != len(traits):
                    protagonist["traits"] = new_traits
                    removed = True
            
            if removed:
                save_file("角色设计.json", char_design)
                logger.info(f"[AutoRepair] 移除主角互斥标签: {group_a if has_bias_b else group_b}")
                return True
        
        return False


class AIAssistedRepair:
    """AI辅助修复器：处理需要语义理解的修复"""
    
    def __init__(self, api_client, genre: str, project_path: Path):
        self.api_client = api_client
        self.genre = genre
        self.project_path = Path(project_path)
        self.products_path = self.project_path / "phase_one_products"
    
    def repair(self, issues: List[AlignmentIssue]) -> Dict[str, Any]:
        """
        执行AI辅助修复
        策略：将所有同类问题聚合，批量发送给AI，减少API调用次数
        """
        if not issues or not self.api_client:
            return {"fixed_count": 0, "remaining_issues": issues, "modified_files": []}
        
        # 按文件和问题类型聚合
        issues_by_file = {}
        for issue in issues:
            filename = issue.source_file.split(" / ")[0]  # 取第一个文件
            key = (filename, issue.category)
            issues_by_file.setdefault(key, []).append(issue)
        
        fixed_count = 0
        remaining = []
        modified_files = set()
        
        for (filename, category), file_issues in issues_by_file.items():
            try:
                path = self.products_path / filename
                if not path.exists():
                    continue
                
                with open(path, "r", encoding="utf-8") as f:
                    original_data = json.load(f)
                
                repaired_data = self._call_ai_repair(filename, category, file_issues, original_data)
                
                if repaired_data and repaired_data != original_data:
                    with open(path, "w", encoding="utf-8") as f:
                        json.dump(repaired_data, f, ensure_ascii=False, indent=2)
                    modified_files.add(filename)
                    fixed_count += len(file_issues)
                    logger.info(f"[AIAssistedRepair] 已修复 {filename} 中的 {len(file_issues)} 个问题")
                else:
                    remaining.extend(file_issues)
                    
            except Exception as e:
                logger.error(f"[AIAssistedRepair] 修复 {filename} 失败: {e}")
                remaining.extend(file_issues)
        
        return {
            "fixed_count": fixed_count,
            "remaining_issues": remaining,
            "modified_files": sorted(list(modified_files)),
        }
    
    def _call_ai_repair(self, filename: str, category: str, issues: List[AlignmentIssue], data: Any) -> Any:
        """调用AI进行修复"""
        
        if category == "genre_firewall" or category == "progression_fantasy":
            return self._repair_fantasy_elements(filename, issues, data)
        
        elif category == "cross_product_consistency":
            return self._repair_consistency_with_ai(filename, issues, data)
        
        elif category == "character_tag_conflict":
            return self._repair_character_with_ai(filename, issues, data)
        
        return data
    
    def _repair_fantasy_elements(self, filename: str, issues: List[AlignmentIssue], data: Any) -> Any:
        """修复玄幻/越界元素"""
        hit_words = []
        contexts = []
        for issue in issues:
            if "hit_word" in issue.details:
                hit_words.append(issue.details["hit_word"])
            if "context" in issue.details:
                contexts.append(issue.details["context"])
        
        hit_words = list(set(hit_words))
        if not hit_words:
            return data
        
        # 构建替换映射表
        replacement_table = "\n".join([
            f"- '{w}' → {_get_fantasy_replacement(w)}"
            for w in hit_words
        ])
        
        data_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        prompt = f"""你是一位资深的{self.genre}编辑。以下JSON文件中包含不符合该题材设定的词汇，请将其改写为符合题材现实的表达。

## 题材要求
当前题材为：{self.genre}
以下概念绝对禁止出现：{', '.join(hit_words)}
即使为了增加爽感，也绝对不能使用玄幻、修仙、异能、科幻、游戏化的机制。

## 词汇替换要求
{replacement_table}

## 修改原则
1. 必须保持JSON格式完整，只修改文本内容，不修改结构
2. 严禁引入新的禁用词或玄幻概念
3. 替换后的表达必须在{self.genre}题材下现实可解释
4. 保持原有的爽点和情绪张力

## 待修改的JSON
```json
{data_str}
```

请直接输出修改后的完整JSON，不要添加任何解释。"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="conversation",
                user_prompt=prompt,
                temperature=0.3,
                purpose="alignment_ai_repair_fantasy"
            )
            
            if response:
                # 尝试从响应中提取JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    try:
                        result = json.loads(json_match.group())
                        return result
                    except Exception:
                        pass
            
            logger.warning(f"[AIAssistedRepair] AI修复 {filename} 响应解析失败")
            return data
            
        except Exception as e:
            logger.error(f"[AIAssistedRepair] AI调用失败: {e}")
            return data
    
    def _repair_consistency_with_ai(self, filename: str, issues: List[AlignmentIssue], data: Any) -> Any:
        """AI修复一致性问题（主要是倍率描述重写）"""
        # 筛选出倍率矛盾问题
        rate_issues = [i for i in issues if "conflicting_rates" in i.details]
        
        if not rate_issues:
            return data
        
        # 找到基准倍率（从完整方案或金手指设计中提取）
        baseline = rate_issues[0].details.get("plan_value", "")
        if not baseline:
            baseline = rate_issues[0].details.get("design_value", "")
        
        data_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        prompt = f"""你是一位{self.genre}的设定编辑。以下JSON中的数值描述存在矛盾，请以基准描述为准，统一重写相关文本。

## 基准描述
{baseline}

## 问题
同一金手指在不同文件中出现了多种倍率说法（如"万倍"、"双倍"、"100倍"等），这会导致后续章节生成混乱。

## 修改要求
1. 将JSON中所有关于倍率/等级的描述统一为与基准描述一致的逻辑
2. 保持原有的升级节奏和爽点
3. 只修改数值相关文本，不修改结构
4. 输出完整JSON

## 待修改的JSON
```json
{data_str}
```

请直接输出修改后的完整JSON。"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="conversation",
                user_prompt=prompt,
                temperature=0.3,
                purpose="alignment_ai_repair_consistency"
            )
            
            if response:
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except Exception:
                        pass
            
            return data
            
        except Exception as e:
            logger.error(f"[AIAssistedRepair] AI一致化修复失败: {e}")
            return data
    
    def _repair_character_with_ai(self, filename: str, issues: List[AlignmentIssue], data: Any) -> Any:
        """AI修复角色设定"""
        data_str = json.dumps(data, ensure_ascii=False, indent=2)
        
        conflict_list = []
        for issue in issues:
            if "group_a" in issue.details and "group_b" in issue.details:
                conflict_list.append(f"- {issue.details['group_a'][0]} vs {issue.details['group_b'][0]}")
        
        prompt = f"""你是一位{self.genre}的角色编辑。以下角色设计JSON中存在标签或设定矛盾，请修正。

## 发现的问题
{chr(10).join(conflict_list)}

## 修改要求
1. 移除互斥的标签，保留最符合角色核心性格的一方
2. 如果 personality_description 与 traits 矛盾，以 personality_description 为准调整 traits
3. 将跨题材身份（如"兵王"、"战神"）改为现实可解释的身份（如"顶尖安保顾问"、"退役特种兵队长"）
4. 保持JSON结构完整

## 待修改的JSON
```json
{data_str}
```

请直接输出修改后的完整JSON。"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="conversation",
                user_prompt=prompt,
                temperature=0.3,
                purpose="alignment_ai_repair_character"
            )
            
            if response:
                import re
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    try:
                        return json.loads(json_match.group())
                    except Exception:
                        pass
            
            return data
            
        except Exception as e:
            logger.error(f"[AIAssistedRepair] AI角色修复失败: {e}")
            return data
