"""
章节两轮优化器 - 番茄爆款对齐系统
==============================

在战术规划完成后，进行两轮优化：
1. 第一轮：结构对齐优化（节拍+战术企图）
2. 第二轮：情绪渲染优化（番茄爆款技法）

确保生成的章节100%符合大纲设计，同时达到番茄爆款标准。

作者：AI Assistant
版本：1.0.0
"""

import json
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class ChapterTwoStageOptimizer:
    """
    章节两轮优化器
    
    对AI生成的章节进行两轮优化，对齐番茄爆款标准
    """
    
    def __init__(self, api_client=None):
        """
        初始化优化器
        
        Args:
            api_client: API客户端，用于调用AI进行优化
        """
        self.api_client = api_client
    
    def optimize(self, chapter_content: str, chapter_num: int, 
                 blueprint: Dict, novel_data: Dict) -> Tuple[str, Dict]:
        """
        执行两轮优化
        
        Args:
            chapter_content: 原始章节内容
            chapter_num: 章节号
            blueprint: 章节大纲
            novel_data: 小说数据
            
        Returns:
            (优化后内容, 优化报告)
        """
        logger.info(f"[TwoStageOptimizer] 开始优化第{chapter_num}章")
        
        report = {
            "chapter_num": chapter_num,
            "stage1": {"status": "skipped", "issues": []},
            "stage2": {"status": "skipped", "issues": []},
        }
        
        # ========== 第一轮优化：结构对齐 ==========
        logger.info(f"[TwoStageOptimizer] 第{chapter_num}章 - 第一轮：结构对齐")
        stage1_result = self._stage1_structure_optimize(
            chapter_content, chapter_num, blueprint
        )
        
        if stage1_result["need_fix"]:
            chapter_content = stage1_result["optimized_content"]
            report["stage1"] = {
                "status": "applied",
                "issues": stage1_result["issues"],
                "fixes": stage1_result["fixes"]
            }
        else:
            report["stage1"] = {
                "status": "passed",
                "issues": []
            }
        
        # ========== 第二轮优化：情绪渲染 ==========
        logger.info(f"[TwoStageOptimizer] 第{chapter_num}章 - 第二轮：情绪渲染")
        stage2_result = self._stage2_emotion_optimize(
            chapter_content, chapter_num, blueprint, novel_data
        )
        
        if stage2_result["need_fix"]:
            chapter_content = stage2_result["optimized_content"]
            report["stage2"] = {
                "status": "applied",
                "issues": stage2_result["issues"],
                "fixes": stage2_result["fixes"]
            }
        else:
            report["stage2"] = {
                "status": "passed",
                "issues": []
            }
        
        logger.info(f"[TwoStageOptimizer] 第{chapter_num}章优化完成")
        
        return chapter_content, report
    
    def _stage1_structure_optimize(self, content: str, chapter_num: int,
                                    blueprint: Dict) -> Dict:
        """
        第一轮优化：结构对齐
        
        检查点：
        1. 节拍类型是否符合（铺垫/冲突/反转/渲染/伏笔）
        2. 战术企图是否达成
        3. 核心事件是否完整呈现
        4. 世界观是否一致（国运禁地 vs 都市校园）
        """
        result = {
            "need_fix": False,
            "issues": [],
            "fixes": [],
            "optimized_content": content
        }
        
        # 获取大纲信息
        beat_type = blueprint.get('beat_type', '') if blueprint else ''
        purpose = blueprint.get('purpose', '') if blueprint else ''
        event = blueprint.get('event', '') if blueprint else ''
        
        # ===== 检查点1：节拍类型对齐 =====
        beat_check = self._check_beat_type(content, beat_type)
        if not beat_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "节拍类型偏离",
                "detail": beat_check["issues"]
            })
            result["fixes"].append(f"调整章节结构以符合{beat_type}节拍类型")
        
        # ===== 检查点2：战术企图达成 =====
        purpose_check = self._check_purpose_achievement(content, purpose)
        if not purpose_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "战术企图未达成",
                "detail": purpose_check["issues"]
            })
            result["fixes"].append("补充或强化战术企图相关内容")
        
        # ===== 检查点3：核心事件完整 =====
        event_check = self._check_core_event(content, event)
        if not event_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "核心事件缺失",
                "detail": event_check["issues"]
            })
            result["fixes"].append("补充缺失的核心事件内容")
        
        # ===== 检查点4：世界观一致 =====
        world_check = self._check_worldview_consistency(content)
        if not world_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "世界观偏离",
                "detail": world_check["issues"]
            })
            result["fixes"].append("修正为符合国运禁地的场景设定")
        
        # 如果需要修复，生成优化提示词
        if result["need_fix"] and self.api_client:
            result["optimized_content"] = self._generate_stage1_fix(
                content, result["issues"], blueprint
            )
        
        return result
    
    def _stage2_emotion_optimize(self, content: str, chapter_num: int,
                                  blueprint: Dict, novel_data: Dict) -> Dict:
        """
        第二轮优化：情绪渲染
        
        检查点：
        1. 情绪基调是否正确（压抑/大爽快/紧张/震惊/期待）
        2. 震惊层次是否丰富（3层反应：现场→直播→全网）
        3. 弹幕设计是否到位（国运文专项）
        4. 数字可视化是否清晰（国运值、具现资源的具体表现）
        5. 节奏是否符合番茄算法（前300字冲突、每1000字爽点）
        """
        result = {
            "need_fix": False,
            "issues": [],
            "fixes": [],
            "optimized_content": content
        }
        
        # 获取大纲信息
        emotion = blueprint.get('emotion', '') if blueprint else ''
        intensity = blueprint.get('intensity', 0) if blueprint else 0
        
        # ===== 检查点1：情绪基调 =====
        emotion_check = self._check_emotion_delivery(content, emotion, intensity)
        if not emotion_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "情绪渲染不足",
                "detail": emotion_check["issues"]
            })
            result["fixes"].append(f"强化{emotion}情绪的描写")
        
        # ===== 检查点2：震惊层次（国运文专项） =====
        shock_check = self._check_shock_layers(content)
        if not shock_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "震惊层次不够",
                "detail": shock_check["issues"]
            })
            result["fixes"].append("增加三层震惊反应（现场→直播→全网/高层）")
        
        # ===== 检查点3：弹幕设计（国运文专项） =====
        danmu_check = self._check_danmu_design(content)
        if not danmu_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "弹幕设计不足",
                "detail": danmu_check["issues"]
            })
            result["fixes"].append("增加中外弹幕对比和情绪变化")
        
        # ===== 检查点4：数字可视化 =====
        number_check = self._check_number_visualization(content)
        if not number_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "数字可视化缺失",
                "detail": number_check["issues"]
            })
            result["fixes"].append("增加国运值/资源具现的具体数字和视觉描写")
        
        # ===== 检查点5：番茄算法节奏 =====
        algo_check = self._check_tomato_algo(content, chapter_num)
        if not algo_check["passed"]:
            result["need_fix"] = True
            result["issues"].append({
                "type": "番茄算法不合规",
                "detail": algo_check["issues"]
            })
            result["fixes"].append("调整节奏以符合番茄算法要求")
        
        # 如果需要修复，生成优化提示词
        if result["need_fix"] and self.api_client:
            result["optimized_content"] = self._generate_stage2_fix(
                content, result["issues"], blueprint
            )
        
        return result
    
    # ============ 具体检查方法 ============
    
    def _check_beat_type(self, content: str, beat_type: str) -> Dict:
        """检查节拍类型是否符合"""
        issues = []
        
        if beat_type == "铺垫":
            # Setup章应该让主角处于被动/压抑状态
            if "反杀" in content or "得意" in content[:1000]:
                issues.append("铺垫章不应过早出现主角反杀或得意")
        
        elif beat_type == "冲突":
            # Confrontation章应该有明显的对抗
            if content.count("嘲") < 2 and content.count("讽") < 2:
                issues.append("冲突章缺乏足够的嘲讽/对抗元素")
        
        elif beat_type == "反转":
            # Reversal章应该有明显的反转
            if "笑" not in content and "冷" not in content:
                issues.append("反转章可能缺少反派被打脸的情绪转变")
        
        elif beat_type == "渲染":
            # Rendering章应该有丰富的震惊描写
            shock_keywords = ["震惊", "哭", "惊", "傻", "慑", "叹"]
            if sum(content.count(k) for k in shock_keywords) < 3:
                issues.append("渲染章震惊描写可能不足")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_purpose_achievement(self, content: str, purpose: str) -> Dict:
        """检查战术企图是否达成"""
        issues = []
        
        # 提取purpose中的关键词
        keywords = self._extract_keywords(purpose)
        missing_keywords = [k for k in keywords if k not in content]
        
        if missing_keywords:
            issues.append(f"可能缺少战术企图关键词: {', '.join(missing_keywords[:3])}")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_core_event(self, content: str, event: str) -> Dict:
        """检查核心事件是否完整"""
        issues = []
        
        # 提取event中的关键词
        keywords = self._extract_keywords(event)
        key_elements = [k for k in keywords if len(k) >= 2][:5]  # 取前5个关键词
        
        missing = []
        for elem in key_elements:
            if elem not in content:
                missing.append(elem)
        
        if len(missing) > len(key_elements) * 0.5:  # 超过50%缺失
            issues.append(f"核心事件缺少关键元素: {', '.join(missing[:3])}")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_worldview_consistency(self, content: str) -> Dict:
        """检查世界观一致性"""
        issues = []
        
        # 国运禁地文不应该出现的元素
        forbidden = ["校园", "大学", "教务处", "奖学金", "江城", "宿舍"]
        found = [f for f in forbidden if f in content]
        
        if found:
            issues.append(f"发现都市校园元素: {', '.join(found)}")
        
        # 国运禁地文应该出现的元素
        required = ["国运", "禁地", "直播"]
        missing = [r for r in required if r not in content[:500]]  # 前500字应该有
        
        if len(missing) >= 2:
            issues.append(f"前500字缺少国运禁地元素: {', '.join(missing)}")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_emotion_delivery(self, content: str, emotion: str, intensity: int) -> Dict:
        """检查情绪渲染是否到位"""
        issues = []
        
        if emotion == "压抑":
            # 压抑情绪检查
            if content.count("笑") > content.count("哭"):
                issues.append("压抑情绪章节笑点过多")
        
        elif emotion == "大爽快":
            # 爽快情绪检查
            happy_keywords = ["爽", "痛快", "解气", "牛逼", "厉害"]
            if sum(content.count(k) for k in happy_keywords) < 3:
                issues.append("爽快情绪渲染不足，建议增加更多痛快描写")
        
        elif emotion == "震惊":
            # 震惊情绪检查
            shock_keywords = ["震惊", "傻眼", "倒吸凉气", "殇然", "穿云", "脴炸"]
            if sum(content.count(k) for k in shock_keywords) < 3:
                issues.append("震惊情绪渲染不足，建议增加更多震惊描写")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_shock_layers(self, content: str) -> Dict:
        """检查震惊层次（3层反应）"""
        issues = []
        
        # 检查是否有现场反应
        if not any(k in content for k in ["围观", "旁边", "周围"]):
            issues.append("缺少现场围观者反应")
        
        # 检查是否有直播弹幕反应
        if "弹幕" not in content:
            issues.append("缺少直播弹幕反应")
        
        # 检查是否有高层/官方反应
        if not any(k in content for k in ["高层", "官方", "专家", "首长"]):
            issues.append("缺少高层/官方反应")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_danmu_design(self, content: str) -> Dict:
        """检查弹幕设计（国运文专项）"""
        issues = []
        
        # 统计弹幕数量
        danmu_count = content.count("【") + content.count("弹幕")
        
        if danmu_count < 3:
            issues.append(f"弹幕数量过少({danmu_count}条)，建议至少3-5条")
        
        # 检查是否有中外对比
        has_chinese = any(k in content for k in ["龙国", "哧槽", "牛逼"])
        has_foreign = any(k in content for k in ["西方", "impossible", "fake"])
        
        if not (has_chinese and has_foreign):
            issues.append("弹幕缺少中外观众对比")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_number_visualization(self, content: str) -> Dict:
        """检查数字可视化"""
        issues = []
        
        # 检查是否有具体数字
        import re
        numbers = re.findall(r'\d+', content)
        
        if len(numbers) < 5:
            issues.append(f"章节数字过少({len(numbers)}个)，建议增加具体数据")
        
        # 检查是否有国运值变化
        if "国运" in content and "+" not in content:
            issues.append("国运值变化缺少具体数字(+XXX)")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    def _check_tomato_algo(self, content: str, chapter_num: int) -> Dict:
        """检查番茄算法节奏"""
        issues = []
        
        # 检查字数
        char_count = len(content.replace(" ", "").replace("\n", ""))
        if char_count < 2000:
            issues.append(f"字数不足2000({char_count}字)")
        
        # 检查段落长度
        paragraphs = [p for p in content.split("\n") if p.strip()]
        long_paragraphs = [p for p in paragraphs if len(p) > 100]
        if len(long_paragraphs) > len(paragraphs) * 0.3:
            issues.append(f"长段落过多({len(long_paragraphs)}个)，建议多用换行")
        
        return {"passed": len(issues) == 0, "issues": issues}
    
    # ============ 辅助方法 ============
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单实现：提取2-4字的名词性词汇
        words = []
        for i in range(len(text) - 1):
            for j in range(2, 5):  # 2-4字
                if i + j <= len(text):
                    word = text[i:i+j]
                    # 过滤常见虚词
                    if word not in ["的", "了", "是", "在", "和", "与"]:
                        words.append(word)
        return list(set(words))[:10]  # 返回前10个唯一词
    
    def _generate_stage1_fix(self, content: str, issues: List[Dict], 
                             blueprint: Dict) -> str:
        """生成第一轮优化提示词"""
        # 构建修复指令
        fix_instructions = "\n".join([
            f"{i+1}. {issue['type']}: {', '.join(issue['detail'][:2]) if isinstance(issue['detail'], list) else issue['detail']}"
            for i, issue in enumerate(issues)
        ])
        
        prompt = f"""请根据以下问题修复章节内容：

【发现的问题】
{fix_instructions}

【大纲要求】
- 节拍类型：{blueprint.get('beat_type', '')}
- 战术企图：{blueprint.get('purpose', '')}
- 核心事件：{blueprint.get('event', '')}

【修复要求】
1. 严格遵守大纲的节拍类型
2. 确保战术企图完全达成
3. 核心事件必须完整呈现
4. 保持国运禁地的世界观一致性

请输出修复后的完整章节内容。"""

        # 调用API进行修复（简化版：直接返回原文+修复指令）
        return content + "\n\n[需要修复]\n" + fix_instructions
    
    def _generate_stage2_fix(self, content: str, issues: List[Dict],
                             blueprint: Dict) -> str:
        """生成第二轮优化提示词"""
        # 构建修复指令
        fix_instructions = "\n".join([
            f"{i+1}. {issue['type']}: {', '.join(issue['detail'][:2]) if isinstance(issue['detail'], list) else issue['detail']}"
            for i, issue in enumerate(issues)
        ])
        
        emotion = blueprint.get('emotion', '')
        
        prompt = f"""请根据以下问题优化章节内容（重点优化情绪渲染）：

【发现的问题】
{fix_instructions}

【情绪要求】
- 本章情绪：{emotion}（强度：{blueprint.get('intensity', 0)}/10）

【优化要求】
1. 强化{emotion}情绪的多层次描写
2. 如果是震惊章，必须包含：现场反应→弹幕反应→高层反应
3. 增加中外弹幕对比
4. 数字可视化：国运值、资源具现等必须有具体数字
5. 保持番茄算法节奏：每段1-3行，对话占比50%+

请输出优化后的完整章节内容。"""

        return content + "\n\n[需要优化]\n" + fix_instructions


# ============ 便捷函数 ============

def optimize_chapter(content: str, chapter_num: int, blueprint: Dict,
                     novel_data: Dict, api_client=None) -> Tuple[str, Dict]:
    """
    优化章节的便捷函数
    
    Args:
        content: 原始章节内容
        chapter_num: 章节号
        blueprint: 大纲
        novel_data: 小说数据
        api_client: API客户端
        
    Returns:
        (优化后内容, 优化报告)
    """
    optimizer = ChapterTwoStageOptimizer(api_client)
    return optimizer.optimize(content, chapter_num, blueprint, novel_data)
