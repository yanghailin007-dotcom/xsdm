import re
import json
import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import WorldStateManager

class QualityAssessor:
    def __init__(self, api_client, storage_path: str = "./quality_data"):
        self.api_client = api_client
        self.storage_path = storage_path
        
        # 初始化世界状态管理器
        self.world_state_manager = WorldStateManager.WorldStateManager(storage_path)
        
        self.unified_quality_standards = {
            # === 质量等级标准 ===
            "quality_grades": {
                "perfect": 10.0,      # 完美 - 无需优化
                "excellent": 9.8,     # 优秀 - 轻微优化
                "good": 9.5,          # 良好 - 建议优化
                "acceptable": 9.0,    # 合格 - 必须优化
                "needs_rewrite": 8.5  # 需要重写
            },
            
            # === 优化决策阈值 ===
            "optimization_thresholds": {
                # 章节内容相对宽松（考虑创作难度）
                "chapter_content": 9.0,
                # 其他内容要求更高标准
                "market_analysis": 9.0,
                "writing_plan": 9.0,
                "core_worldview": 9.0,
                "character_design": 9.0,
                "creative_seed": 9.0,
                "novel_plan": 9.0
            },
            
            # === 番茄新鲜度评分 ===
            "freshness_standards": {
                "excellent": 8.5,     # 有一定创新性，同时保留经典元素
                "good": 8.0,          # 适当融合套路和创新
                "average": 7.0,       # 常见套路但执行良好
                "cliche": 6.0         # 过度老套重复
            },
            
            # === 黄金三章特殊标准 ===
            "golden_chapters": {
                1: {"min_quality": 9.2, "min_freshness": 9.0},
                2: {"min_quality": 9.1, "min_freshness": 8.8},
                3: {"min_quality": 9.0, "min_freshness": 8.5}
            }
        }
        
        # 新鲜度评估标准
        self.freshness_evaluation_criteria = {
            "concept_originality": {
                "weight": 0.3,
                "description": "核心概念的新颖程度",
                "evaluation_points": [
                    "是否使用了过度常见的套路模板",
                    "世界观设定是否有创新点", 
                    "主角设定是否独特",
                    "金手指/系统设计是否有新意"
                ]
            },
            "execution_uniqueness": {
                "weight": 0.25,
                "description": "执行方式的独特性",
                "evaluation_points": [
                    "情节展开方式是否新颖",
                    "角色互动模式是否有特色",
                    "冲突设计是否避免俗套",
                    "情感表达方式是否独特"
                ]
            },
            "market_differentiation": {
                "weight": 0.25,
                "description": "与市场上同类作品的区分度", 
                "evaluation_points": [
                    "与热门作品的相似度",
                    "是否有明显的差异化优势",
                    "目标读者群体是否明确",
                    "市场定位是否清晰"
                ]
            },
            "creative_risk": {
                "weight": 0.2,
                "description": "创意冒险程度",
                "evaluation_points": [
                    "是否敢于尝试新元素",
                    "是否打破常规设定",
                    "创新与传统的平衡", 
                    "读者接受度预估"
                ]
            }
        }

    def assess_freshness(self, content: Dict, content_type: str) -> Dict:
        """评估内容的新鲜度"""
        try:
            freshness_prompt = self._generate_freshness_assessment_prompt(content, content_type)
            
            result = self.api_client.generate_content_with_retry(
                "freshness_assessment",
                freshness_prompt,
                purpose=f"{content_type}新鲜度评估"
            )
            
            # 确保返回的结果有完整的结构
            if not result:
                return self._get_default_freshness_assessment()
            
            # 确保必要的字段都存在
            required_fields = ["freshness_score", "freshness_verdict", "cliche_elements", "improvement_suggestions"]
            for field in required_fields:
                if field not in result:
                    if field == "improvement_suggestions":
                        result[field] = ["增加创新元素，避免常见套路"]
                    elif field == "cliche_elements":
                        result[field] = []
                    elif field == "freshness_score":
                        result[field] = 8.0
                    elif field == "freshness_verdict":
                        result[field] = "需要改进"
            
            return result
            
        except Exception as e:
            print(f"  ❌ 新鲜度评估失败: {e}")
            return self._get_default_freshness_assessment()

    def _get_default_freshness_assessment(self) -> Dict:
        """获取默认的新鲜度评估结果"""
        return {
            "freshness_score": 8.0,
            "freshness_verdict": "评估异常",
            "cliche_elements": ["评估过程出现异常"],
            "innovative_elements": [],
            "improvement_suggestions": ["重新评估内容新鲜度", "增加创新元素", "避免常见套路"]
        }
    
    def _generate_freshness_assessment_prompt(self, content: Dict, content_type: str) -> str:
        """生成新鲜度评估提示词"""
        return f"""
    作为番茄平台内容创新性评估专家，请评估以下{content_type}内容的新鲜度：

    待评估内容：
    {json.dumps(content, ensure_ascii=False, indent=2)}

    评估维度（满分10分）：
    1. 概念原创性 (3分)：核心概念是否新颖，避免常见套路
    2. 执行独特性 (2.5分)：表达方式和情节设计是否独特  
    3. 市场区分度 (2.5分)：与同类作品的差异化程度
    4. 创意冒险度 (2分)：是否敢于尝试创新元素

    请特别关注：
    - 是否过度使用"退婚流"、"废柴逆袭"、"系统文"等常见套路
    - 世界观设定是否有真正创新点
    - 角色关系设计是否新颖
    - 金手指/系统设计是否独特
    - 情节发展是否可预测

    常见套路检测：
    - 开局退婚/被退婚
    - 废柴体质+逆袭
    - 签到/打卡系统
    - 过于相似的系统设定
    - 千篇一律的反派设定
    - 缺乏新意的修炼体系

    请严格按照以下JSON格式返回评估结果，确保所有字段都存在：
    {{
        "freshness_score": 新鲜度评分(0-10),
        "freshness_verdict": "新鲜度评级",
        "originality_analysis": "原创性分析",
        "cliche_elements": ["检测到的套路元素列表，至少提供1-3个"],
        "innovative_elements": ["创新点列表，至少提供1-3个"], 
        "improvement_suggestions": ["提升新鲜度建议列表，至少提供2-3个具体建议"]
    }}

    重要要求：
    - 如果未检测到套路元素，cliche_elements 设为空数组 []
    - 如果未发现创新点，innovative_elements 设为空数组 []
    - improvement_suggestions 必须至少包含2个具体建议
    - 所有字段都必须存在，不能缺少任何字段
    """

    def should_optimize_comprehensive(self, assessment: Dict, content_type: str, 
                                    chapter_number: int = None) -> Tuple[bool, str]:
        """综合优化决策 - 区分章节和非章节内容"""
        quality_score = assessment.get("overall_score", 0)
        freshness_score = assessment.get("freshness_score", 10.0)  # 默认10分
        
        standards = self.unified_quality_standards
        
        # 章节内容和非章节内容使用不同的标准
        if content_type == "chapter_content":
            # 章节内容只检查质量
            quality_threshold = standards["optimization_thresholds"]["chapter_content"]
            
            # 黄金三章特殊检查
            if chapter_number in [1, 2, 3]:
                golden_standard = standards["golden_chapters"][chapter_number]
                if quality_score < golden_standard["min_quality"]:
                    return True, f"黄金第{chapter_number}章质量分{quality_score:.1f}低于{golden_standard['min_quality']}"
            
            # 常规质量检查
            if quality_score < quality_threshold:
                return True, f"质量分{quality_score:.1f}低于阈值{quality_threshold}"
            
            return False, f"质量{quality_score:.1f}达标"
        
        else:
            # 非章节内容检查质量和新鲜度
            quality_threshold = standards["optimization_thresholds"].get(content_type, 9.8)
            freshness_threshold = standards["freshness_standards"]["good"]
            
            # 质量检查
            if quality_score < quality_threshold:
                return True, f"质量分{quality_score:.1f}低于阈值{quality_threshold}"
            
            # 新鲜度检查
            if freshness_score < freshness_threshold:
                return True, f"新鲜度{freshness_score:.1f}低于阈值{freshness_threshold}"
            
            return False, f"质量{quality_score:.1f}和新鲜度{freshness_score:.1f}均达标"

    def assess_chapter_quality(self, assessment_params: Dict) -> Optional[Dict]:
        """评估章节质量（包含一致性检查）- 增强黄金三章评估"""
        user_prompt = self._generate_chapter_assessment_prompt(assessment_params)
        result = self.api_client.generate_content_with_retry(
            "chapter_quality_assessment", 
            user_prompt, 
            temperature=0.3, 
            purpose="章节质量评估"
        )
        
        # 如果评估成功，处理黄金三章的特殊逻辑
        if result and 'overall_score' in result:
            chapter_number = assessment_params.get('chapter_number', 0)
            novel_title = assessment_params.get('novel_title', 'unknown')
            
            # 如果是黄金三章，应用更严格的标准
            if 1 <= chapter_number <= 3:
                result = self._apply_golden_chapters_standards(result, chapter_number)
            
            # 1. 首先处理角色状态变化
            character_status_changes = result.get('character_status_changes', [])
            for status_change in character_status_changes:
                character_name = status_change.get('character_name')
                status = status_change.get('status')
                if character_name and status in ['dead', 'exited']:
                    print(f"🔄 AI检测到角色状态变化: {character_name} -> {status}")
                    self.world_state_manager._simplify_character_status(novel_title, character_name, status, chapter_number)
            
            # 2. 处理世界状态增量更新
            if 'world_state_changes' in result:
                print("🧹 清洗世界状态变化数据...")
                print(f"   原始数据类型: {type(result['world_state_changes'])}")
                
                # 调试：打印原始数据结构
                for category, elements in result['world_state_changes'].items():
                    print(f"   {category}: {type(elements)} - {len(elements) if hasattr(elements, '__len__') else 'N/A'}")
                cleaned_changes = self.world_state_manager._validate_and_clean_world_state_changes(
                    result['world_state_changes'], 
                    chapter_number
                )
                
                if cleaned_changes:
                    self.world_state_manager._update_world_state_incrementally(novel_title, cleaned_changes, chapter_number)
                    result['updated_world_state'] = self.world_state_manager.current_world_state
                    result['world_state_changes'] = cleaned_changes
                    
                    # === 修复：从世界状态变化中提取角色信息，更新角色发展表 ===
                    self._update_character_development_from_world_state(novel_title, cleaned_changes, chapter_number)
                else:
                    print("⚠️ 世界状态变化数据清洗后为空")
            
            # 3. 保存评估数据
            self.world_state_manager.save_assessment_data(novel_title, chapter_number, result)
            
            # 4. 从评估结果更新角色发展表（原有的逻辑）
            self.world_state_manager.update_character_development_from_assessment(novel_title, result, chapter_number)
        return result

    def _update_character_development_from_world_state(self, novel_title: str, world_state_changes: Dict, chapter_number: int):
        """从世界状态变化中更新角色发展表"""
        characters_changes = world_state_changes.get('characters', {})
        
        for character_name, character_data in characters_changes.items():
            # 构建角色发展数据
            development_data = {
                "name": character_name,
                "role_type": character_data.get("attributes", {}).get("role_type", "次要配角"),
                "status": character_data.get("attributes", {}).get("status", "active")
            }
            
            # 添加修为信息
            attributes = character_data.get("attributes", {})
            cultivation_level = attributes.get("cultivation_level")
            cultivation_system = attributes.get("cultivation_system")
            
            if cultivation_level or cultivation_system:
                if "cultivation_info" not in development_data:
                    development_data["cultivation_info"] = {}
                if cultivation_level:
                    development_data["cultivation_info"]["level"] = cultivation_level
                if cultivation_system:
                    development_data["cultivation_info"]["system"] = cultivation_system
            
            # 更新角色发展表
            print(f"🔄 从世界状态更新角色发展表: {character_name}")
            self.world_state_manager.manage_character_development_table(
                novel_title, 
                development_data, 
                chapter_number, 
                "update"
            )

    def _apply_golden_chapters_standards(self, assessment_result: Dict, chapter_number: int) -> Dict:
        """对黄金三章应用更严格的评分标准"""
        
        # 黄金三章的特殊评分维度
        golden_chapters_criteria = {
            1: {
                "criteria": {
                    "opening_hook": 0.25,  # 开篇钩子权重25%
                    "protagonist_intro": 0.25,  # 主角介绍权重25%
                    "conflict_setup": 0.20,  # 冲突设置权重20%
                    "world_building": 0.15,  # 世界观展示权重15%
                    "pacing": 0.15  # 节奏控制权重15%
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.2
            },
            2: {
                "criteria": {
                    "conflict_development": 0.25,
                    "character_relationship": 0.20,
                    "plot_progression": 0.20,
                    "suspense_building": 0.20,
                    "pacing": 0.15
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.1
            },
            3: {
                "criteria": {
                    "climax_execution": 0.25,
                    "foreshadowing": 0.20,
                    "reader_engagement": 0.25,
                    "chapter_ending": 0.20,
                    "series_hook": 0.10
                },
                "minimum_acceptable": 8.5,
                "excellent_threshold": 9.0
            }
        }
        
        chapter_criteria = golden_chapters_criteria.get(chapter_number, {})
        if not chapter_criteria:
            return assessment_result
        
        # 调整总体评分
        original_score = assessment_result.get("overall_score", 0)
        
        # 如果有详细分数，按照黄金三章标准重新计算
        if "detailed_scores" in assessment_result:
            detailed = assessment_result["detailed_scores"]
            new_score = 0
            
            for criterion, weight in chapter_criteria["criteria"].items():
                # 将原有的分数映射到新标准
                criterion_score = detailed.get(criterion, original_score)
                new_score += criterion_score * weight
            
            assessment_result["overall_score"] = min(10.0, new_score * 2)  # 转换为10分制
        
        # 添加黄金三章特殊评估
        assessment_result["golden_chapters_assessment"] = {
            "chapter_number": chapter_number,
            "special_criteria": chapter_criteria["criteria"],
            "is_acceptable": assessment_result["overall_score"] >= chapter_criteria["minimum_acceptable"],
            "quality_tier": self._get_golden_chapters_quality_tier(assessment_result["overall_score"]),
            "improvement_suggestions": self._generate_golden_chapters_suggestions(assessment_result, chapter_number)
        }
        
        return assessment_result

    def _get_golden_chapters_quality_tier(self, score: float) -> str:
        """获取黄金三章质量等级"""
        if score >= 9.2:
            return "S级 - 完美开篇"
        elif score >= 8.8:
            return "A级 - 优秀开篇" 
        elif score >= 8.5:
            return "B级 - 合格开篇"
        else:
            return "C级 - 需要重写"

    def _generate_golden_chapters_suggestions(self, assessment: Dict, chapter_number: int) -> List[str]:
        """生成黄金三章改进建议"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        
        suggestions = []
        
        # 基于章节号的特殊建议
        if chapter_number == 1 and score < 8.8:
            suggestions.extend([
                "检查开篇500字是否足够吸引人",
                "强化主角登场场景的冲击力", 
                "确保冲突在开篇立即展现",
                "优化世界观展示的自然程度"
            ])
        elif chapter_number == 2 and score < 8.8:
            suggestions.extend([
                "深化第一章引入的冲突",
                "加强主角与配角的互动质量",
                "确保情节推进的节奏感",
                "检查悬念设置的强度"
            ])
        elif chapter_number == 3 and score < 8.8:
            suggestions.extend([
                "强化章节小高潮的情感冲击",
                "优化伏笔设置的自然程度",
                "检查章节结尾的追读钩子强度",
                "确保读者有强烈继续阅读的欲望"
            ])
        
        # 基于弱点的具体建议
        for weakness in weaknesses[:3]:
            if "开篇" in weakness or "开头" in weakness:
                suggestions.append("重新设计开篇场景，增加冲击力")
            elif "节奏" in weakness:
                suggestions.append("调整节奏，删除冗余描写")
            elif "悬念" in weakness:
                suggestions.append("加强悬念设置，提高读者好奇心")
            elif "主角" in weakness:
                suggestions.append("强化主角魅力和特质展现")
        
        return suggestions[:5]  # 返回前5个最重要的建议

    def detect_ai_artifacts(self, content: str) -> List[str]:
        """检测AI痕迹"""
        artifacts = []
        
        marker_patterns = [
            r'\*\*.*?：\*\*',
            r'【.*?】',
            r'第一[点、]|第二[点、]|第三[点、]',
            r'首先，|其次，|然后，|最后，',
            r'总的来说，|综上所述，|总而言之，',
            r'伏笔植入|铺垫手法|情节设计|结构安排',
            r'人物塑造|角色刻画|性格描写|形象建立',
            r'主题表达|思想内涵|深层意义|价值取向',
            r'情感渲染|气氛营造|情绪铺垫|感染力',
            r'叙事视角|叙述方式|描写手法|表现技巧',
            r'节奏控制|张弛有度|高潮部分|结局处理',
            r'象征意义|隐喻手法|对比运用|反复强调',
            r'在此基础上，|进一步来说，|值得注意的是，',
            r'从另一个角度|换而言之|具体而言',
            r'需要指出的是|值得关注的是|不容忽视的是',
            r'^[\d一二三四五六七八九十]、',
            r'^[•\-*]\s',
            r'^[A-Za-z]\.',
            r'使故事更加|让情节更|增强了作品的',
            r'提升了文章的|丰富了内容的|深化了主题的',
            r'达到了.*效果|产生了.*影响|具有.*价值',
            r'人物关系方面，|角色互动上，|彼此之间',
            r'父子关系|母女关系|夫妻关系|朋友关系',
            r'矛盾冲突|情感纠葛|关系发展|互动模式',
            r'开头部分|中间段落|结尾处|整体结构',
            r'起承转合|前后呼应|层层递进|环环相扣',
            r'艺术特色|文学价值|创作特点|风格特征',
            r'语言优美|文字精炼|表达生动|描写细腻'
        ]
        
        for pattern in marker_patterns:
            matches = re.findall(pattern, content)
            if matches:
                artifacts.append(f"模式化标记: {matches[:3]}")
        
        sentences = re.split(r'[。！？]', content)
        
        for sentence in sentences:
            if len(sentence) > 10:
                if "一边" in sentence and sentence.count("一边") > 1:
                    artifacts.append("重复句式: 一边...一边...")
                if "不仅" in sentence and "而且" in sentence:
                    artifacts.append("重复句式: 不仅...而且...")
        
        overused_words = ["显然", "无疑", "实际上", "事实上", "可以说", "值得注意的是"]
        for word in overused_words:
            count = content.count(word)
            if count > 3:
                artifacts.append(f"过度使用词汇: '{word}'出现{count}次")
        
        return artifacts[:10]

    def _generate_chapter_assessment_prompt(self, params: Dict) -> str:
        """生成章节质量评估提示词（重新组织修为+物品+功法结构）"""
        
        # 加载之前的世界状态
        novel_title = params.get('novel_title', 'unknown')
        previous_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        world_state_str = json.dumps(previous_world_state, ensure_ascii=False, indent=2) if previous_world_state else "{}"

        character_development_data = self._load_character_development_data(novel_title)
        character_development_str = json.dumps(character_development_data, ensure_ascii=False, indent=2) if character_development_data else "{}"        
        
        return f"""
    内容：
    你是一位资深的番茄小说内容分析师与世界观架构师。
    你的任务是根据提供的章节信息和之前的世界观状态，进行全面的质量评估，并识别出本章节对世界观的具体变化。

    ### 重要字段约定 - 重新组织为修为+物品+功法结构
    在返回的world_state_changes中，请严格遵守以下字段结构：

    **角色 (characters):**
    - name: string (角色名字)
    - description: string (角色当前状态描述)
    - attributes: object (包含以下固定字段)
      - status: string (活跃/死亡/退场/重伤/失踪)
      - location: string (当前所在地点)
      - title: string (称号/头衔，可选)
      - occupation: string (职业/身份，可选)
      - faction: string (所属势力，可选)
      - cultivation_level: string (修为等级) # 核心：角色当前修为
      - cultivation_system: string (修为体系) # 核心：修仙/异能/武侠等
      - emotional_state: string (情绪状态) # 新增：愤怒/平静/喜悦/悲伤等

    **修炼物品 (cultivation_items):**
    - description: string (物品描述)
    - owner: string (拥有者)
    - type: string (类型：丹药/法宝/材料/符箓/功法典籍等)
    - quality: string (品质：凡品/黄阶/玄阶/地阶/天阶/神品)
    - status: string (物品状态：已使用/未使用/损坏/遗失)
    - location: string (物品位置)
    - effect: string (效果描述) # 新增

    **功法技能 (cultivation_skills):**
    - description: string (技能描述)
    - owner: string (拥有者)
    - type: string (类型：功法/神通/秘术/体质/心法等)
    - level: string (掌握程度：入门/小成/大成/圆满)
    - quality: string (品质：凡品/黄阶/玄阶/地阶/天阶/神品)
    - status: string (技能状态：已掌握/修炼中/封印中)

    **关系变化 (relationships):** # 增强关系描述
    - type: string (关系类型：师徒/道侣/兄弟/仇敌/盟友/主仆)
    - description: string (关系详细描述)
    - status: string (关系状态：稳固/紧张/破裂/改善)
    - intimacy_level: number (亲密度1-10) # 新增
    - conflict_level: number (冲突度1-10) # 新增

    **心理状态记录 (mental_states):** # 新增：专门记录心理状态
    - character: string (角色名)
    - emotional_state: string (情绪状态)
    - motivation: string (当前动机)
    - internal_conflict: string (内心矛盾)
    - recent_trauma: string (近期创伤)
    - hope_fear: string (希望与恐惧)

    **地点 (locations):**
    - description: string (地点描述)
    - status: string (地点状态：安全/危险/探索中/已废弃)
    - significance: string (重要性) # 新增

    ### 信息记录规则
    请按照以下分类准确记录：

    1. **角色修为信息**：
    - cultivation_level: 当前修为等级（如：练气三层、筑基中期、金丹后期）
    - cultivation_system: 修为体系（如：修仙、异能、武侠、科技）

    2. **修炼物品分类**：
    - 丹药类：修炼丹药、疗伤丹药、突破丹药等
    - 法宝类：武器、防具、辅助法宝等
    - 材料类：灵草、矿石、妖兽材料等
    - 符箓类：攻击符、防御符、辅助符等

    3. **功法技能分类**：
    - 功法类：修炼心法、基础功法等
    - 神通类：攻击神通、防御神通、辅助神通等
    - 秘术类：特殊秘法、禁术等
    - 体质类：特殊体质、天赋等

    ### 1. 小说信息
    - **小说标题**: {params.get('novel_title', '未知')}
    - **章节标题**: {params.get('chapter_title', '未知')}
    - **章节编号**: {params.get('chapter_number', '未知')}
    - **前情提要**: {params.get('previous_summary', '无')}

    ### 2. 目前章节的世界状态
    {world_state_str}

    现有角色发展数据:
    {character_development_str}

    章节内容预览:
    {params.get('chapter_content', '')}

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": "number (0-10，基于细分维度计算)",
        "quality_verdict": "string (根据分数评定，如'卓越', '优秀', '良好', '合格'等)",
        "strengths": "array of strings (列出章节的主要优点)",
        "weaknesses": "array of strings (列出章节的主要待改进方面)",
        "detailed_scores": {{
            "plot_pacing_and_appeal": "number (0-2)",
            "characterization_and_consistency": "number (0-2)", 
            "writing_quality_and_immersion": "number (0-2)",
            "structure_and_cohesion": "number (0-2)",
            "world_state_consistency": "number (0-2)"
        }},
        "consistency_issues": [
            {{
                "type": "string (枚举: CHARACTER, ITEM, RELATIONSHIP, SKILL, TIMELINE, LOCATION, CULTIVATION)", 
                "description": "string (具体问题描述)", 
                "severity": "string (枚举: High, Medium, Low)",
                "suggestion": "string (修复建议)"
            }}
        ],
        "character_status_changes": [
            {{
                "character_name": "string",
                "status": "string (枚举: active, dead, exited)", 
                "reason": "string (状态变化原因)",
                "chapter": "number"
            }}
        ],
        "world_state_changes": {{
            // 严格遵守字段约定，重新组织为修为+物品+功法结构
            "characters": {{
                "角色名": {{
                    "name": "string (角色名)",
                    "description": "string (角色描述)",
                    "attributes": {{
                        "status": "string (活跃/死亡/退场)",
                        "location": "string (当前所在地点)",
                        "title": "string (可选)",
                        "occupation": "string (可选)",
                        "faction": "string (可选)",
                        "cultivation_level": "string (修为等级)",
                        "cultivation_system": "string (修为体系)"
                    }}
                }}
            }},
            "cultivation_items": {{
                "物品名": {{
                    "description": "string (物品描述)",
                    "owner": "string (拥有者)",
                    "type": "string (丹药/法宝/材料/符箓等)",
                    "quality": "string (品质等级)",
                    "status": "string (物品状态)",
                    "location": "string (物品位置)"
                }}
            }},
            "cultivation_skills": {{
                "技能名": {{
                    "description": "string (技能描述)",
                    "owner": "string (拥有者)",
                    "type": "string (功法/神通/秘术/体质等)",
                    "level": "string (掌握程度)",
                    "quality": "string (品质等级)",
                    "status": "string (技能状态)"
                }}
            }},
            "relationships": {{
                "角色A-角色B": {{
                    "type": "string (关系类型)",
                    "description": "string (关系描述)",
                    "status": "string (目前的实际关系状态)"
                }}
            }},
            "locations": {{
                "地点名": {{
                    "description": "string (地点描述)",
                    "status": "string (地点状态)"
                }}
            }}
        }},
        "assessment_timestamp": "string (生成报告的ISO 8601格式时间戳，例如: '2024-05-16T12:00:00Z')"
    }}

    重要说明：
    1. 严格按照新的分类结构记录：修为+物品+功法
    2. 角色修为信息集中在characters的cultivation_level和cultivation_system字段
    3. 所有修炼相关物品归入cultivation_items，并按类型分类
    4. 所有功法技能归入cultivation_skills，并按类型分类
    5. world_state_changes只包含本章节新增或发生变化的世界状态元素
    """

    def optimize_chapter_content(self, optimization_params: Dict) -> Optional[Dict]:
        """优化章节内容 - 返回标准章节格式"""
        try:
            user_prompt = self._generate_optimization_prompt(optimization_params)
            result = self.api_client.generate_content_with_retry(
                "chapter_optimization", 
                user_prompt, 
                purpose="章节内容优化",
                max_retries=3
            )
            
            # 验证优化结果并转换为标准章节格式
            if result and isinstance(result, dict) and result.get("content"):
                print(f"  ✅ 章节优化成功，生成内容长度: {len(result.get('content', ''))}")
                
                # 构建标准章节格式的返回数据
                standard_chapter_data = {
                    "content": result.get("content"),
                    "word_count": result.get("word_count", len(result.get("content", ""))),
                    # 保留优化器返回的额外信息，但放在单独的字段中
                    "optimization_details": {
                        "optimization_summary": result.get("optimization_summary", ""),
                        "changes_made": result.get("changes_made", []),
                        "quality_improvement": result.get("quality_improvement", "")
                    }
                }
                
                return standard_chapter_data
            else:
                print(f"  ❌ 章节优化失败，返回无效结果: {type(result)}")
                return None
                
        except Exception as e:
            print(f"  ❌ 章节优化过程异常: {e}")
            return None

    def _generate_optimization_prompt(self, params: Dict) -> str:
        """生成章节优化提示词 - 要求返回标准章节格式"""
        try:
            assessment = json.loads(params.get("assessment_results", "{}"))
        except:
            assessment = {}
            
        original_content = params.get("original_content", "")
        novel_title = params.get("novel_title", "未知小说")
        chapter_number = params.get("chapter_number", 0)
        chapter_title = params.get("chapter_title", "")
        writing_style_guide = params.get("writing_style_guide", {})
        
        # 获取完整的世界状态用于参考
        full_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        # 构建优化指导
        weaknesses = assessment.get('weaknesses', [])
        consistency_issues = assessment.get('consistency_issues', [])
        
        optimization_guide = "## 主要优化方向\n"
        if weaknesses:
            optimization_guide += "### 质量问题修复\n"
            for i, weakness in enumerate(weaknesses[:3], 1):
                optimization_guide += f"{i}. {weakness}\n"
        
        if consistency_issues:
            optimization_guide += "### 一致性问题修复\n"
            for i, issue in enumerate(consistency_issues[:2], 1):
                optimization_guide += f"{i}. {issue.get('description', '')} - 建议: {issue.get('suggestion', '')}\n"
        
        return f"""
    你是一个专业的小说编辑，需要对以下章节内容进行优化。请保持原有的章节结构和风格，只针对质量问题进行调整。

    ## 优化任务信息
    - **小说标题**: {novel_title}
    - **章节标题**: {chapter_title}
    - **章节编号**: 第{chapter_number}章
    - **当前评分**: {assessment.get('overall_score', 0)}/10分
    - **质量评级**: {assessment.get('quality_verdict', '未知')}

    ## 需要优化的主要问题
    {optimization_guide}

    ## 写作风格参考
    {json.dumps(writing_style_guide, ensure_ascii=False, indent=2) if writing_style_guide else "无特定风格要求"}

    ## 世界状态参考（请确保一致性）
    {json.dumps(full_world_state, ensure_ascii=False, indent=2) if full_world_state else "无世界状态数据"}

    ## 原始章节内容
    {original_content}

    ## 优化要求
    1. **保持核心情节**：不改变主要情节发展
    2. **提升文笔质量**：改善语言表达，消除AI痕迹
    3. **修复一致性问题**：确保角色、物品、关系等要素的一致性
    4. **增强可读性**：优化段落结构和叙事节奏
    5. **保持原有结构**：章节标题、段落结构等保持不变
    6. **目标字数**：优化后内容长度应在2000-3500字之间

    ## 输出格式要求
    请返回优化后的完整章节内容，使用以下标准的JSON格式：
    {{
        "content": "优化后的完整章节内容，保持原有的章节标题和段落结构",
        "word_count": 优化后的字数统计,
        "optimization_summary": "简要说明优化重点",
        "changes_made": ["具体修改1", "具体修改2", "具体修改3"],
        "quality_improvement": "质量提升说明"
    }}

    请确保返回的内容可以直接替换原始章节内容，同时保持所有必要的章节元素。
    """

    def _quick_optimize_chapter(self, chapter_data: Dict, assessment: Dict) -> Optional[Dict]:
        """快速优化章节（包含一致性修复）"""
        score = assessment.get("overall_score", 0)
        weaknesses = assessment.get("weaknesses", [])
        consistency_issues = assessment.get("consistency_issues", [])
        
        intensity_config = self.get_optimization_intensity(score, consistency_issues)
        
        if intensity_config["max_issues"] == 0:
            return None
        
        # 优先处理一致性问題
        priority_issues = []
        severe_consistency = [issue for issue in consistency_issues 
                            if issue.get('severity') == '高']
        
        # 添加严重一致性问題
        for issue in severe_consistency[:2]:
            priority_issues.append(f"修复一致性问題: {issue.get('description')}")
        
        # 添加其他弱点
        remaining_slots = intensity_config["max_issues"] - len(priority_issues)
        if remaining_slots > 0:
            priority_issues.extend(weaknesses[:remaining_slots])
        
        if not priority_issues:
            if score < self.quality_thresholds["needs_optimization"]:
                priority_issues = ["提升情节连贯性", "增强角色表现", "改善文笔质量"]
            else:
                return None
        
        optimization_params = {
            "assessment_results": json.dumps({
                "weaknesses": weaknesses,
                "consistency_issues": consistency_issues,
                "updated_world_state": assessment.get("updated_world_state", {}),
                "overall_score": score,
                "optimization_intensity": intensity_config["description"]
            }, ensure_ascii=False),
            "original_content": chapter_data.get("content", ""),
            "priority_fix_1": priority_issues[0] if len(priority_issues) > 0 else "提升整体质量",
            "priority_fix_2": priority_issues[1] if len(priority_issues) > 1 else "",
            "priority_fix_3": priority_issues[2] if len(priority_issues) > 2 else "",
            "optimization_intensity": intensity_config["description"]
        }
        
        return self.optimize_chapter_content(optimization_params)

    # ==================== 质量决策方法 ====================

    def should_optimize_chapter(self, assessment: Dict) -> Tuple[bool, str]:
        """判断是否需要优化章节（考虑黄金三章特殊要求）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        chapter_info = assessment.get("golden_chapters_assessment", {})
        
        # 检查是否为黄金三章
        is_golden_chapter = chapter_info.get("chapter_number", 0) in [1, 2, 3]
        
        # 黄金三章的特殊优化逻辑
        if is_golden_chapter:
            golden_minimum = 8.5
            if score < golden_minimum:
                return True, f"黄金三章评分低于{golden_minimum}分，必须优化"
            elif not chapter_info.get("is_acceptable", True):
                return True, "黄金三章未达到可接受标准"
        
        # 原有的优化逻辑（严重一致性问题的处理）
        severe_consistency_issues = [issue for issue in consistency_issues 
                                if issue.get('severity') == '高']
        
        if severe_consistency_issues:
            return True, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        thresholds = self.quality_thresholds
        
        if score >= thresholds["excellent"]:
            return False, "质量优秀，无需优化"
        elif score >= thresholds["good"]:
            return False, "质量良好，可选优化"
        elif score >= thresholds["acceptable"]:
            return True, "质量合格，建议优化"
        elif score >= thresholds["needs_optimization"]:
            return True, "需要优化提升质量"
        else:
            return True, "质量不合格，需要重点优化"

    def get_quality_verdict(self, score: float) -> Tuple[str, str]:
        """获取质量评级"""
        thresholds = self.quality_thresholds
        
        if score >= thresholds["excellent"]:
            return "优秀", "质量很高，无需优化"
        elif score >= thresholds["good"]:
            return "良好", "质量良好，可轻微优化"
        elif score >= thresholds["acceptable"]:
            return "合格", "建议优化以提升质量"
        elif score >= thresholds["needs_optimization"]:
            return "需要优化", "需要重点优化"
        else:
            return "需要重写", "质量不合格，建议重写"

    def should_skip_optimization(self, assessment: Dict, chapter_data: Dict) -> Tuple[bool, str]:
        """判断是否应该跳过优化（考虑一致性因素）"""
        score = assessment.get("overall_score", 0)
        consistency_issues = assessment.get("consistency_issues", [])
        skip_config = self.optimization_settings["skip_optimization_conditions"]
        
        # 如果有严重一致性问題，不跳过优化
        severe_consistency_issues = [issue for issue in consistency_issues 
                                   if issue.get('severity') == '高']
        if severe_consistency_issues:
            return False, f"存在{len(severe_consistency_issues)}个严重一致性问題，需要优化"
        
        if score >= skip_config["min_score_skip"]:
            return True, "质量优秀，跳过优化"
        
        ai_score = assessment.get("detailed_scores", {}).get("ai_artifacts_detected", 2)
        if ai_score >= skip_config["min_ai_score_skip"]:
            return True, "AI痕迹较少，跳过优化"
        
        word_count = chapter_data.get("word_count", 0)
        word_range = skip_config["word_count_range"]
        if word_range[0] <= word_count <= word_range[1]:
            if score >= skip_config["min_score_with_good_words"]:
                return True, "字数合适且质量良好，跳过优化"
        
        return False, "需要优化"

    def get_optimization_intensity(self, score: float, consistency_issues: List = None) -> Dict:
        """获取优化强度配置（考虑一致性因素）"""
        intensity_configs = self.optimization_settings["optimization_intensity"]
        
        # 如果有严重一致性问題，提高优化强度
        severe_issues = [issue for issue in (consistency_issues or []) 
                        if issue.get('severity') == '高']
        
        if severe_issues:
            return {
                "max_issues": len(severe_issues) + 2,
                "description": f"重点优化（包含{len(severe_issues)}个严重一致性问題）"
            }
        
        if score < intensity_configs["high"]["threshold"]:
            return intensity_configs["high"]
        elif score < intensity_configs["medium"]["threshold"]:
            return intensity_configs["medium"]
        elif score < intensity_configs["low"]["threshold"]:
            return intensity_configs["low"]
        else:
            return {"max_issues": 0, "description": "无需优化"}

    # ==================== 快速评估方法 ====================

    def quick_assess_chapter_quality(self, chapter_content: str, chapter_title: str, 
                                chapter_number: int, novel_title: str, previous_summary: str, 
                                word_count: int = 0) -> Dict:
        """快速评估章节质量（包含一致性检查）"""
        # 加载之前的世界状态
        self.world_state_manager.current_world_state = self.world_state_manager.load_previous_assessments(novel_title)
        
        return self.assess_chapter_quality({
            "chapter_content": chapter_content,
            "chapter_title": chapter_title,
            "chapter_number": chapter_number,
            "novel_title": novel_title,
            "previous_summary": previous_summary,
            "total_chapters": 100,  # 默认值，实际使用时应该传入
            "word_count": word_count
        })

    # ==================== 其他内容类型评估 ====================

    def assess_market_analysis_quality(self, market_analysis: Dict) -> Dict:
        """评估市场分析质量"""
        if not market_analysis:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_market_analysis_assessment_prompt(market_analysis)
        
        result = self.api_client.generate_content_with_retry(
            "market_analysis_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="市场分析质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_market_analysis_assessment_prompt(self, market_analysis: Dict) -> str:
        """生成市场分析评估提示词"""
        return f"""
请评估以下市场分析内容的质量：

市场分析内容:
{json.dumps(market_analysis, ensure_ascii=False, indent=2)}

评估维度：
1. 市场洞察深度 (2分): 对目标市场和读者需求的分析是否深入
2. 竞争分析准确性 (2分): 对竞争环境和自身优势的分析是否准确
3. 卖点提炼有效性 (2分): 核心卖点和差异化优势是否清晰有力
4. 数据支撑充分性 (2分): 是否有充分的数据和市场依据支撑分析
5. 可行性评估 (2分): 提出的策略和方向是否具备可行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_writing_plan_quality(self, writing_plan: Dict) -> Dict:
        """评估写作计划质量"""
        if not writing_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_writing_plan_assessment_prompt(writing_plan)
        
        result = self.api_client.generate_content_with_retry(
            "writing_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="写作计划质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_writing_plan_assessment_prompt(self, writing_plan: Dict) -> str:
        """生成写作计划评估提示词"""
        return f"""
请评估以下写作计划的质量：

写作计划内容:
{json.dumps(writing_plan, ensure_ascii=False, indent=2)}

评估维度：
1. 结构合理性 (2分): 章节节奏和情节分布是否合理
2. 角色成长设计 (2分): 主角成长轨迹是否清晰合理
3. 冲突设计质量 (2分): 主要冲突和矛盾设计是否吸引人
4. 伏笔设计 (2分): 伏笔线和情感线设计是否有机融合
5. 可行性评估 (2分): 计划是否具备可执行性

请按照以下JSON格式返回评估结果：
{{
    "overall_score": 总体评分(满分10分),
    "quality_verdict": "质量评级",
    "strengths": ["优点列表"],
    "weaknesses": ["待改进方面列表"],
    "optimization_suggestions": ["优化建议列表"]
}}
"""

    def assess_core_worldview_quality(self, worldview: Dict) -> Dict:
        """评估世界观质量"""
        if not worldview:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_worldview_assessment_prompt(worldview)
        
        result = self.api_client.generate_content_with_retry(
            "core_worldview_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="世界观质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_worldview_assessment_prompt(self, worldview: Dict) -> str:
        """生成世界观评估提示词"""
        return f"""
请评估以下世界观设定的质量：

世界观内容:
{json.dumps(worldview, ensure_ascii=False, indent=2)}

"""

    def assess_character_design_quality(self, character_design: Dict) -> Dict:
        """评估角色设计质量"""
        if not character_design:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_character_design_assessment_prompt(character_design)
        
        result = self.api_client.generate_content_with_retry(
            "character_design_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="角色设计质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_character_design_assessment_prompt(self, character_design: Dict) -> str:
        """生成角色设计评估提示词"""
        return f"""
内容:
请根据你作为角色设计顾问的专业身份，使用系统提示中定义的评估体系和JSON格式，对以下角色设计进行全面评估。

待评估的角色设计内容：
{json.dumps(character_design, ensure_ascii=False, indent=2)}

"""

    def optimize_market_analysis(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化市场分析 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_market_analysis_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "market_analysis_optimization", 
            user_prompt, 
            purpose="市场分析优化"
        )
        return result

    def optimize_writing_plan(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化写作计划 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_writing_plan_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "writing_plan_optimization", 
            user_prompt, 
            purpose="写作计划优化"
        )
        return result
    
    def optimize_core_worldview(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化世界观 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_worldview_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "core_worldview_optimization", 
            user_prompt, 
            purpose="世界观优化"
        )
        return result


    def optimize_novel_plan(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化小说方案 - 支持新鲜度要求"""
        # 直接从 assessment 字典中获取数据，而不是从字符串
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典，不序列化为字符串
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_novel_plan_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "novel_plan_optimization", 
            user_prompt, 
            purpose="小说方案优化"
        )
        return result

    def optimize_character_design(self, original_content: Dict, assessment: Dict) -> Optional[Dict]:
        """优化角色设计 - 支持新鲜度要求"""
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        priority_fixes = "\n".join([f"- {weakness}" for weakness in weaknesses[:3]])
        
        optimization_params = {
            "original_content": json.dumps(original_content, ensure_ascii=False, indent=2),
            "assessment_results": assessment,  # 直接传递字典
            "priority_fixes": priority_fixes
        }
        
        user_prompt = self._generate_character_design_optimization_prompt(optimization_params)
        result = self.api_client.generate_content_with_retry(
            "character_design_optimization", 
            user_prompt, 
            purpose="角色设计优化"
        )
        return result


    def calculate_quality_statistics(self, quality_records: Dict) -> Dict:
        """计算质量统计数据"""
        if not quality_records:
            return {}
        
        scores = []
        ai_scores = []
        detailed_scores = {
            "plot_coherence": [],
            "character_consistency": [],
            "chapter_connection": [],
            "writing_quality": [],
            "ai_artifacts_detected": [],
            "emotional_impact": []
        }
        
        for chapter_num, record in quality_records.items():
            assessment = record.get("assessment", {})
            overall_score = assessment.get("overall_score", 0)
            scores.append(overall_score)
            
            # 收集详细分数
            detailed = assessment.get("detailed_scores", {})
            for key in detailed_scores.keys():
                if key in detailed:
                    detailed_scores[key].append(detailed[key])
            
            # 特别收集AI痕迹分数
            ai_score = detailed.get('ai_artifacts_detected', 2)
            ai_scores.append(ai_score)
        
        if not scores:
            return {}
        
        # 计算统计信息
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        avg_ai_score = sum(ai_scores) / len(ai_scores) if ai_scores else 2
        
        # 计算质量分布
        quality_distribution = {
            "优秀": len([s for s in scores if s >= self.quality_thresholds["excellent"]]),
            "良好": len([s for s in scores if self.quality_thresholds["good"] <= s < self.quality_thresholds["excellent"]]),
            "合格": len([s for s in scores if self.quality_thresholds["acceptable"] <= s < self.quality_thresholds["good"]]),
            "需要优化": len([s for s in scores if s < self.quality_thresholds["acceptable"]])
        }
        
        # 计算AI痕迹分布
        ai_distribution = {
            "优秀(2分)": len([s for s in ai_scores if s == 2]),
            "良好(1.5-2分)": len([s for s in ai_scores if 1.5 <= s < 2]),
            "需改进(1-1.5分)": len([s for s in ai_scores if 1 <= s < 1.5]),
            "较差(<1分)": len([s for s in ai_scores if s < 1])
        }
        
        # 计算详细分数平均值
        avg_detailed_scores = {}
        for key, values in detailed_scores.items():
            if values:
                avg_detailed_scores[key] = round(sum(values) / len(values), 2)
        
        return {
            "total_chapters_assessed": len(scores),
            "average_score": round(avg_score, 2),
            "max_score": max_score,
            "min_score": min_score,
            "quality_distribution": quality_distribution,
            "average_detailed_scores": avg_detailed_scores,
            "ai_quality": {
                "average_ai_score": round(avg_ai_score, 2),
                "ai_distribution": ai_distribution,
                "chapters_with_ai_artifacts": len([s for s in ai_scores if s < 2])
            }
        }

    # ==================== 缺失的方法修复 ====================

    def _load_character_development_data(self, novel_title: str) -> Dict:
        """加载角色发展数据 - 修复缺失的方法"""
        return self.world_state_manager._load_character_development_data(novel_title)

    def get_comprehensive_previous_summary_enhanced(self, novel_title: str, chapter_number: int) -> str:
        """增强版前情提要生成"""
        character_status = self.world_state_manager.get_character_comprehensive_status_enhanced(novel_title)
        
        if not character_status:
            return "暂无角色状态信息"
        
        summary_parts = ["【主要角色状态】"]
        
        for char_name, status in character_status.items():
            char_summary = self._format_character_summary_enhanced(char_name, status, chapter_number)
            summary_parts.append(char_summary)
        
        return "\n".join(summary_parts)

    def _format_character_summary_enhanced(self, char_name: str, status: Dict, current_chapter: int) -> str:
        """增强版角色摘要格式化"""
        parts = []
        
        basic_info = status["basic_info"]
        cultivation_info = status["cultivation_info"]
        mental_state = status["mental_state"]
        
        # 基础状态行 - 增强位置和状态显示
        status_line = f"{char_name}"
        if cultivation_info.get("cultivation_level") and cultivation_info["cultivation_level"] != "未知":
            status_line += f"（{cultivation_info['cultivation_level']}）"
        
        location = cultivation_info.get("location", "")
        location_status = cultivation_info.get("location_status", "")
        
        if location_status == "移动中":
            status_line += f" 🚶{location}"
        else:
            status_line += f" 📍{location}"
        
        parts.append(status_line)
        
        # 心理状态和情绪 - 使用推断的情绪
        emotional_state = mental_state.get("recent_emotional_state", "平静")
        if mental_state.get("core_traits"):
            traits = "、".join(mental_state["core_traits"][:2])
            parts.append(f"  💭{traits}，情绪：{emotional_state}")
        
        # 重要关系 - 使用清理后的关系
        relationships = status["relationships"][:2]
        if relationships:
            rel_icons = {
                "师徒": "👥", "竞争师徒": "⚔️👥", "对手": "⚔️", 
                "敌对": "🔥", "盟友": "🤝", "道侣": "❤️"
            }
            
            rel_texts = []
            for rel in relationships:
                icon = rel_icons.get(rel["type"], "•")
                rel_texts.append(f"{icon}{rel['character']}（{rel['type']}）")
            
            parts.append(f"  🔗关系：{'，'.join(rel_texts)}")
        
        # 近期发展
        recent_dev = status["recent_development"]
        if recent_dev.get("milestones"):
            latest_milestone = recent_dev["milestones"][-1]
            milestone_icon = "⭐" if latest_milestone.get("type") in ["突破", "获得宝物"] else "📌"
            parts.append(f"  {milestone_icon}近期：{latest_milestone.get('description', '有所进展')}")
        
        return "\n".join(parts)

    def _get_recent_important_events(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取近期重要事件"""
        events = []
        
        # 检查角色状态变化（死亡、重伤等）
        characters = world_state.get("characters", {})
        for char_name, char_data in characters.items():
            attributes = char_data.get("attributes", {})
            last_updated = char_data.get("last_updated", 0)
            
            # 只关注最近3章内的事件
            if current_chapter - last_updated <= 3:
                status = attributes.get("status", "")
                if status in ["死亡", "重伤", "失踪"]:
                    events.append(f"• {char_name}{status}")
        
        return events[:3]  # 最多返回3个事件

    def _get_key_updates(self, world_state: Dict, current_chapter: int) -> List[str]:
        """获取关键物品和功法更新"""
        updates = []
        
        # 高品质物品获取
        cultivation_items = world_state.get("cultivation_items", {})
        for item_name, item_data in cultivation_items.items():
            last_updated = item_data.get("last_updated", 0)
            quality = item_data.get("quality", "")
            owner = item_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}获得{quality}物品「{item_name}」")
        
        # 重要功法掌握
        cultivation_skills = world_state.get("cultivation_skills", {})
        for skill_name, skill_data in cultivation_skills.items():
            last_updated = skill_data.get("last_updated", 0)
            quality = skill_data.get("quality", "")
            owner = skill_data.get("owner", "")
            
            if (current_chapter - last_updated <= 3 and 
                quality in ["地阶", "天阶", "神品"] and owner):
                updates.append(f"• {owner}掌握{quality}功法「{skill_name}」")
        
        return updates[:3]  # 最多返回3个更新


    def load_previous_assessments(self, novel_title: str, novel_data: Dict = None) -> Dict:
        """向后兼容：加载之前章节的评估数据"""
        return self.world_state_manager.load_previous_assessments(novel_title, novel_data)

    def save_assessment_data(self, novel_title: str, chapter_number: int, assessment_data: Dict):
        """向后兼容：保存评估数据"""
        self.world_state_manager.save_assessment_data(novel_title, chapter_number, assessment_data)

    def assess_character_importance(self, character_data: Dict, chapter_content: str = "") -> str:
        """向后兼容：评估角色重要性"""
        return self.world_state_manager.assess_character_importance(character_data, chapter_content)

    def manage_character_development_table(self, novel_title: str, character_data: Dict, 
                                        current_chapter: int, action: str = "update") -> Dict:
        """向后兼容：管理角色发展表"""
        return self.world_state_manager.manage_character_development_table(novel_title, character_data, current_chapter, action)

    def get_character_development_suggestions(self, character_name: str, novel_title: str, current_chapter: int) -> List[Dict]:
        """向后兼容：获取角色发展建议"""
        return self.world_state_manager.get_character_development_suggestions(character_name, novel_title, current_chapter)

    def assess_character_development(self, chapter_content: str, characters_in_chapter: List[str], 
                                novel_title: str, chapter_number: int) -> Dict:
        """向后兼容：评估角色发展质量"""
        return self.world_state_manager.assess_character_development(chapter_content, characters_in_chapter, novel_title, chapter_number)

    def update_character_development_from_assessment(self, novel_title: str, assessment: Dict, chapter_number: int):
        """向后兼容：从评估结果更新角色发展表"""
        self.world_state_manager.update_character_development_from_assessment(novel_title, assessment, chapter_number)

    def initialize_world_state_from_novel_data(self, novel_title: str, novel_data: Dict):
        """向后兼容：基于小说数据初始化世界状态"""
        return self.world_state_manager.initialize_world_state_from_novel_data(novel_title, novel_data)

    def cleanup_characters_by_strategy(self, novel_title: str, strategy_config: Dict) -> Dict:
        """向后兼容：根据策略清理角色数据"""
        return self.world_state_manager.cleanup_characters_by_strategy(novel_title, strategy_config)

    def get_novel_consistency_report(self, novel_title: str) -> Dict:
        """向后兼容：获取小说的整体一致性报告"""
        return self.world_state_manager.get_novel_consistency_report(novel_title)
    
    def _generate_market_analysis_optimization_prompt(self, params: Dict) -> str:
        """市场分析优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升分析的独特性和深度"}

    ### 新鲜度提升方向
    1. **挖掘独特市场切入点**：避免泛泛而谈，找到具体的、差异化的市场机会
    2. **提供深度洞察**：不只是罗列数据，要提供有见地的分析
    3. **差异化竞争策略**：提出与现有作品明显不同的竞争策略
    4. **创新营销角度**：从新的视角分析市场趋势和读者需求
    5. **具体可执行建议**：避免空泛描述，提供可落地的具体建议
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升分析深度**：确保每个观点都有充分的数据和逻辑支撑
    2. **优化结构逻辑**：使分析报告结构清晰，逻辑连贯
    3. **增强可读性**：使用更生动、专业的表达方式
    4. **加强数据支撑**：为每个结论提供充分的市场依据
    """
        
        return f"""
    你是一个专业的市场分析优化专家，需要对以下市场分析内容进行优化，同时提升质量和新鲜度。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始市场分析内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心结论**：不改变原有的核心市场判断和结论
    2. **提升分析深度**：为每个观点提供更充分的数据和逻辑支撑
    3. **增强独特性**：避免套路化分析，提供独特的市场洞察
    4. **优化表达方式**：使用更专业、生动的语言表达

    ### 质量标准
    - 分析逻辑严密，数据支撑充分
    - 结构清晰，层次分明
    - 观点鲜明，结论明确
    - 语言专业，表达准确

    ### 新鲜度标准  
    - 避免常见的市场分析套路
    - 提供独特的市场视角和洞察
    - 挖掘差异化的竞争策略
    - 提出创新的营销建议

    ## 输出格式
    请返回优化后的完整市场分析内容，保持原有的JSON结构，但提升内容的质量和新鲜度。
    """

    def _generate_writing_plan_optimization_prompt(self, params: Dict) -> str:
        """写作计划优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升写作计划的创新性"}

    ### 新鲜度提升方向
    1. **创新情节结构**：避免千篇一律的起承转合，尝试新的叙事结构
    2. **独特角色成长**：设计非传统的角色成长路径和转折点
    3. **新颖冲突设计**：创造独特的矛盾冲突，避免常见的情感套路
    4. **创新伏笔设置**：设计出人意料但又合理的伏笔和反转
    5. **差异化节奏控制**：尝试新的节奏变化模式，增强读者体验
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **优化结构合理性**：确保章节节奏和情节分布更加合理
    2. **加强角色成长设计**：使主角成长轨迹更加清晰和吸引人
    3. **提升冲突设计质量**：强化主要冲突的吸引力和张力
    4. **完善伏笔设计**：使伏笔线与情感线更好地融合
    5. **增强可行性**：确保计划具备良好的可执行性
    """
        
        return f"""
    你是一个专业的写作计划优化专家，需要对以下写作计划进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始写作计划内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心框架**：不改变原有的主要情节框架和角色设定
    2. **提升计划深度**：为每个阶段提供更详细和合理的规划
    3. **增强创新性**：避免套路化情节，提供独特的叙事设计
    4. **优化可行性**：确保计划在现实中具备良好的可执行性

    ### 质量标准
    - 情节结构合理，节奏把控得当
    - 角色成长轨迹清晰可信
    - 冲突设计有吸引力
    - 伏笔设置巧妙合理
    - 整体计划具备可执行性

    ### 新鲜度标准
    - 避免常见的情节套路和模板
    - 提供独特的叙事视角和结构
    - 设计创新的角色发展路径
    - 创造新颖的矛盾冲突类型
    - 设置出人意料的伏笔和转折

    ## 输出格式
    请返回优化后的完整写作计划内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def _generate_worldview_optimization_prompt(self, params: Dict) -> str:
        """世界观优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升世界观的独特性"}

    ### 新鲜度提升方向
    1. **创新世界观基础**：避免常见的修仙/异能/科幻设定，创造独特的世界观基础
    2. **独特力量体系**：设计非传统的修炼体系或能力系统
    3. **新颖社会结构**：创造独特的社会组织形态和权力结构
    4. **创新文化背景**：构建具有特色的文化习俗和价值观念
    5. **差异化地理环境**：设计独特的地理环境和生态体系
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升体系完整性**：确保世界观各个要素之间逻辑自洽
    2. **加强细节丰富度**：为世界观提供更丰富的细节支撑
    3. **优化层次结构**：使世界观呈现清晰的层次结构
    4. **增强扩展性**：确保世界观有足够的扩展空间和发展潜力
    5. **完善内在逻辑**：强化世界观内部各要素的逻辑关系
    """
        
        return f"""
    你是一个专业的世界观架构优化专家，需要对以下世界观设定进行优化，同时提升质量和独特性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始世界观内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心概念**：不改变世界观的基本概念和核心设定
    2. **提升体系完整性**：使世界观各个要素更加协调和完整
    3. **增强独特性**：避免常见的世界观套路，提供独特的设定
    4. **优化逻辑自洽**：确保世界观内部逻辑更加严密和合理

    ### 质量标准
    - 世界观体系完整，逻辑自洽
    - 各个要素协调统一，层次清晰
    - 设定丰富具体，细节充分
    - 扩展性强，有发展潜力
    - 与故事主题和情节匹配度高

    ### 新鲜度标准
    - 避免常见的世界观设定套路
    - 提供独特的世界观基础和概念
    - 设计创新的力量体系和社会结构
    - 构建具有特色的文化背景
    - 创造新颖的地理环境和生态

    ## 输出格式
    请返回优化后的完整世界观内容，保持原有的JSON结构，但提升内容的质量和独特性。
    """

    def _generate_character_design_optimization_prompt(self, params: Dict) -> str:
        """角色设计优化提示词 - 增强新鲜度要求"""
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升角色设计的创新性"}

    ### 新鲜度提升方向
    1. **创新角色设定**：避免脸谱化角色，创造独特的人物形象
    2. **独特成长路径**：设计非传统的角色发展轨迹
    3. **新颖关系网络**：构建独特的角色关系和互动模式
    4. **创新性格特质**：设计具有特色的性格特点和心理特征
    5. **差异化背景故事**：创造独特的角色背景和成长经历
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升角色深度**：使角色形象更加立体和丰满
    2. **加强动机合理性**：确保角色行为和动机更加合理可信
    3. **优化关系设计**：使角色关系更加复杂和有趣
    4. **增强成长弧线**：强化角色的成长轨迹和发展变化
    5. **完善背景设定**：为角色提供更丰富的背景故事
    """
        
        return f"""
    你是一个专业的角色设计优化专家，需要对以下角色设计进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始角色设计内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心特质**：不改变角色的核心性格和基本设定
    2. **提升角色深度**：使角色形象更加立体和丰满
    3. **增强独特性**：避免脸谱化角色，提供独特的人物设计
    4. **优化关系网络**：使角色关系更加复杂和有趣

    ### 质量标准
    - 角色形象立体丰满，性格鲜明
    - 行为动机合理可信，成长轨迹清晰
    - 角色关系复杂有趣，互动模式多样
    - 背景故事丰富具体，与角色特质匹配
    - 角色设计符合世界观和故事需求

    ### 新鲜度标准
    - 避免常见的角色设定套路
    - 提供独特的角色形象和性格
    - 设计创新的成长路径和发展
    - 构建新颖的角色关系和互动
    - 创造具有特色的背景故事

    ## 输出格式
    请返回优化后的完整角色设计内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def _generate_novel_plan_optimization_prompt(self, params: Dict) -> str:
        """小说方案优化提示词 - 增强新鲜度要求"""
        # 直接从 params 中获取 assessment_results，它现在是字典而不是字符串
        assessment = params.get("assessment_results", {})
        freshness_assessment = assessment.get("freshness_assessment", {})
        freshness_issues = freshness_assessment.get("cliche_elements", [])
        improvement_suggestions = freshness_assessment.get("improvement_suggestions", [])
        
        freshness_guidance = ""
        if freshness_issues or improvement_suggestions:
            freshness_guidance = f"""
    ## 🆕 新鲜度提升要求

    ### 检测到的套路问题
    {chr(10).join(f"- {issue}" for issue in freshness_issues) if freshness_issues else "- 暂无检测到明显套路元素"}

    ### 创新改进建议
    {chr(10).join(f"- {suggestion}" for suggestion in improvement_suggestions) if improvement_suggestions else "- 请进一步提升小说方案的创新性"}

    ### 新鲜度提升方向
    1. **创新核心概念**：避免常见的小说套路，创造独特的故事概念
    2. **独特情节设计**：设计非传统的情节发展和转折
    3. **新颖角色设定**：创造具有特色的主角和配角设定
    4. **创新金手指设计**：避免常见的系统设定，提供独特的能力设计
    5. **差异化世界观**：构建独特的世界观背景和设定
    """
        
        quality_assessment = assessment.get("quality_assessment", {})
        weaknesses = quality_assessment.get("weaknesses", [])
        
        quality_guidance = ""
        if weaknesses:
            quality_guidance = f"""
    ## 📊 质量提升要求

    ### 主要质量问题
    {chr(10).join(f"- {weakness}" for weakness in weaknesses[:3])}

    ### 质量改进重点
    1. **提升概念完整性**：使小说概念更加完整和吸引人
    2. **加强情节合理性**：确保情节发展更加合理和连贯
    3. **优化角色设计**：使角色设定更加立体和有趣
    4. **增强市场匹配度**：确保方案符合目标读者需求
    5. **完善核心设定**：强化金手指、世界观等核心设定
    """
        
        return f"""
    你是一个专业的小说方案优化专家，需要对以下小说方案进行优化，同时提升质量和创新性。

    ## 优化任务信息
    - **当前质量评分**: {quality_assessment.get('overall_score', 0):.1f}/10
    - **当前新鲜度评分**: {freshness_assessment.get('freshness_score', 0):.1f}/10
    - **优化目标**: 质量9.8分以上，新鲜度9.0分以上

    {quality_guidance}
    {freshness_guidance}

    ## 原始小说方案内容
    {params.get('original_content', '')}

    ## 优化要求
    ### 核心要求
    1. **保持核心创意**：不改变小说的核心创意和基本方向
    2. **提升方案完整性**：使小说方案更加完整和详细
    3. **增强创新性**：避免常见的小说套路，提供独特的故事设计
    4. **优化市场适应性**：确保方案符合市场需求和读者喜好

    ### 质量标准
    - 概念完整清晰，吸引力强
    - 情节设计合理，发展连贯
    - 角色设定立体，特点鲜明
    - 核心设定有趣，扩展性强
    - 市场定位准确，读者明确

    ### 新鲜度标准
    - 避免常见的小说创作套路
    - 提供独特的故事概念和创意
    - 设计创新的情节发展模式
    - 创造新颖的角色形象设定
    - 构建独特的金手指和世界观

    ## 输出格式
    请返回优化后的完整小说方案内容，保持原有的JSON结构，但提升内容的质量和创新性。
    """

    def assess_novel_plan_quality(self, novel_plan: Dict) -> Dict:
        """评估小说方案质量"""
        if not novel_plan:
            return {"overall_score": 0, "quality_verdict": "无内容"}
        
        user_prompt = self._generate_novel_plan_assessment_prompt(novel_plan)
        
        result = self.api_client.generate_content_with_retry(
            "novel_plan_quality_assessment", 
            user_prompt, 
            temperature=0.3,
            purpose="小说方案质量评估"
        )
        return result or {"overall_score": 7.0, "quality_verdict": "评估失败"}

    def _generate_novel_plan_assessment_prompt(self, novel_plan: Dict) -> str:
        """生成小说方案评估提示词"""
        return f"""
    请评估以下小说方案的质量：

    小说方案内容:
    {json.dumps(novel_plan, ensure_ascii=False, indent=2)}

    评估维度：
    1. 概念完整性 (2分): 核心概念是否完整清晰，吸引力如何
    2. 情节设计质量 (2分): 情节设计是否合理，发展是否连贯
    3. 角色设定质量 (2分): 角色设定是否立体，特点是否鲜明
    4. 核心设定创新性 (2分): 金手指、世界观等核心设定是否有创新
    5. 市场适应性 (2分): 方案是否符合市场需求和读者喜好

    请按照以下JSON格式返回评估结果：
    {{
        "overall_score": 总体评分(满分10分),
        "quality_verdict": "质量评级",
        "strengths": ["优点列表"],
        "weaknesses": ["待改进方面列表"],
        "optimization_suggestions": ["优化建议列表"]
    }}
    """