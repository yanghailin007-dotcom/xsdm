"""
方案生成器
负责小说方案的生成、评估和优化
"""

import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class PlanGenerator:
    """方案生成器类"""
    
    def __init__(self, api_client, quality_assessor, content_generator):
        self.api_client = api_client
        self.quality_assessor = quality_assessor
        self.content_generator = content_generator
        
        # 初始化平台适配器工厂
        try:
            from config.platform_adapters import PlatformAdapterFactory
            self.platform_adapter_factory = PlatformAdapterFactory
        except ImportError:
            self.platform_adapter_factory = None
        
        # 高分爆款方案创作蓝图
        self.HIGH_SCORING_PLAN_BLUEPRINT = """
        # 高分爆款方案创作蓝图 (Blueprint for High-Scoring Blockbuster Plans)
        在构思方案时，请主动遵循以下蓝图，以确保方案天然具备爆款潜力：

        1.  **【金手指设计原则】**:
            *   **钩子优先**: 金手指的初次亮相必须极具"爽感"和"戏剧性"，能立刻抓住读者眼球。
            *   **玩法清晰**: 金手指不能只是简单的属性加点，必须有清晰、可延展的"玩法"（如炼制、合成、顿悟、签到特殊奖励等），让读者能持续期待主角如何使用它。
            *   **深度绑定**: 金手指最好与主角的身份、血脉或故事核心秘密深度绑定，而不是凭空出现。

        2.  **【核心卖点原则】**:
            *   **极致清晰**: 必须有1-2个极其明确、能在简介中一句话说清楚的核心卖点（例如："天生废体，但每次受伤都能抽取敌人天赋"）。
            *   **高频展示**: 构思的情节要能让核心卖点被反复、花式地展现，持续刺激读者。

        3.  **【角色与代入感原则】 (现代化升级版)**:
            *   **人格魅力驱动**: 主角开局必须有一个由其鲜明人格决定的、能引发读者好奇与共鸣的"主动追求"目标。这比传统的被动复仇更具吸引力。
                *   **新潮趋势示例 (优先考虑):**
                    *   **苟道求长生**: 目标是"活下去"，通过极度稳健和风险规避，熬死所有敌人，享受生存的终极乐趣。
                    *   **乐子人玩转世界**: 目标是"找乐子"，通过在幕后操纵局势、导演大戏来满足自己的娱乐心态。
                    *   **秩序建设者**: 目标是"搞建设"，通过发展势力、领地、家族，享受从零到一创造伟业的成就感。
                    *   **规则探索者**: 目标是"卡Bug"，通过研究世界底层逻辑和玩法机制，用智慧和骚操作碾压敌人。
                *   **经典有效目标 (作为备选):**
                    *   摆脱屈辱、守护亲人、寻找真相、为血亲复仇等。如果使用经典目标，必须在实现方式上做出新意。
            *   **标签鲜明**: 主角人设要有一个鲜明的记忆点（如：杀伐果断、腹黑老六、稳健苟道、技术狂人等），并贯穿始终。

        4.  **【世界观与冲突原则】**:
            *   **冲突前置**: 开局必须立刻抛出一个与主角核心目标紧密相关的冲突，让主角迅速行动起来，而不是平淡地介绍世界观。
            *   **升级路径清晰**: 世界观要能清晰地支撑主角的"成长路线"，有明确的地图和敌人等级划分，让读者有清晰的成长预期。
            *   **🆕 背景资料深度融入**: 如果提供了原著背景资料，【必须】深度理解和运用这些资料，确保方案与原著设定完美契合，同时找到创新的切入点。

        5.  **同人小说特殊创作原则** (仅适用于同人小说):
            *   **原著尊重**: 严格遵循原著世界观、角色设定、力量体系，不得出现明显设定冲突。
            *   **创新视角**: 在尊重原著的基础上，找到新的叙事角度或切入点，避免简单重复原著情节。
            *   **角色关系重构**: 可以合理重构角色间的关系网络，但要符合角色性格和原著逻辑。
            *   **时间线把控**: 严格把控故事时间线，避免与原著重大事件发生冲突。

        6.  标题创作原则**:
            *   **字数严格限制**: 生成的标题【必须】严格控制在 **15个汉字以内**，最佳长度为7-12个字。
            *   **卖点突出**: 标题必须能直接或间接反映小说最核心的卖点或金手指。
            *   **同人特色**: 如果是同人小说，标题可适当体现原著元素，增强辨识度。
            *   **避免复杂**: 避免使用生僻词或过于复杂的长句，追求简洁、有力、高辨识度。

        7.  简介创作原则 (番茄风格)**:
            *   **忠于大纲**: 简介【必须】是`completeStoryline`部分的直接商业化转述，特别是要准确反映`opening`阶段的核心设定（如主角的真实身份、初始目标）。【严禁】为简介编造一个与`completeStoryline.opening`相矛盾的开局。
            *   **黄金三句式**: 简介开头三句内，【必须】清晰交代：**主角身份 + 遭遇的离奇事件/获得的金手指 + 他即将要做什么爽事**。
            *   **冲突前置与悬念**: 【必须】立刻展现一个核心矛盾或一个极具吸引力的"钩子"，让读者产生"接下来会发生什么"的强烈好奇。
            *   **口语化与快节奏**: 语言风格应通俗易懂、节奏明快，多用短句，【严禁】使用冗长的背景介绍和复杂的文学性修辞。
            *   **背景资料体现**: 如果提供了背景资料，简介中应自然体现对原著的理解，让同好读者能够识别。
        """
        
        # 绝对创作红线与毒点规避指令
        self.POISON_POINT_RULES_FOR_GENERATION = """
        # 绝对创作红线与毒点规避指令 (Absolute Creative Red Lines & Poison Point Avoidance Directives)
        在构思所有方案时，你【必须】严格遵守以下红线，任何触犯以下任意一条的方案都将被视为无效：

        1.  **【主角地位绝对核心】**: 严禁设计任何可能削弱或取代主角光环的"天命之子"、"真主角"或背景更强的同辈角色。主角必须是其所在阶段的唯一核心。
        2.  **【严防情感背叛】**: 严禁设计主角被核心伴侣/后宫、已确认关系的女性角色、生死兄弟或至亲背叛的情节。尤其禁止"绿帽"和"送女"桥段。
        3.  **【杜绝强行降智】**: 必须保持主角智商和人设的连贯性。严禁为了制造冲突或推进剧情，让主角做出不符合其性格和过往经历的愚蠢决定（即"强行降智"或"圣母行为"）。
        4.  **【拒绝无意义虐主】**: 所有挫折和压抑情节都必须是为后续更高潮的爽点做铺垫。严禁设计长时间、无明确回报的憋屈情节。
        5.  **【避免空洞说教】**: 故事必须由具体事件和角色行动驱动。严禁将核心冲突建立在对"天道"、"法则"等抽象概念的空洞辩论上。创新应体现在情节、设定和金手指玩法上，而非哲学探讨。
        6.  **【🆕 背景资料红线】**: 如果提供了原著背景资料：
            *   **严禁违背核心设定**: 不得与背景资料中的核心世界观、角色性格、力量体系发生冲突。
            *   **尊重时间线**: 严格遵循原著的时间线逻辑，不允许出现明显的时间线矛盾。
            *   **可信度警示**: 如果背景资料可信度较低，设计方案时必须更加谨慎，优先选择已验证的信息。
        """
    
    def _update_step_status(self, step_name: str, status: str, progress: int = None):
        """更新步骤状态"""
        try:
            if hasattr(self.content_generator, 'generator') and self.content_generator.generator:
                generator = self.content_generator.generator
                if hasattr(generator, '_update_task_status_callback'):
                    task_id = getattr(generator, '_current_task_id', None)
                    if task_id and callable(generator._update_task_status_callback):
                        generator._update_task_status_callback(
                            task_id, 'generating', progress or 0, None,
                            current_step=step_name,
                            step_status={step_name: status}
                        )
            # 同时通过事件总线发布
            if hasattr(self.content_generator, 'generator') and self.content_generator.generator:
                generator = self.content_generator.generator
                if hasattr(generator, 'event_bus'):
                    generator.event_bus.publish('phase_one.step_status', {
                        'step': step_name,
                        'status': status,
                        'progress': progress
                    })
        except Exception as e:
            print(f"⚠️ 步骤状态更新失败: {e}")

    def generate_and_select_plan(self, creative_seed: str, content_generator, target_platform: str = "fanqie") -> Optional[Dict]:
        """
        生成多个方案并让用户选择
        
        Args:
            creative_seed: 创意种子
            content_generator: 内容生成器实例
            target_platform: 目标平台 (fanqie/qidian/zhihu)  # 🔥 新增平台参数
            
        Returns:
            选中的方案数据，失败返回None
        """
        # 🔥 记录平台选择
        print(f"📱 [PLATFORM] 目标平台: {target_platform}")
        print("=== 步骤1: 基于创意种子生成多个小说方案 ===")
        
        # 预设临时标题用于文件名
        temp_title_for_filename = "未定稿小说" 
        
        # 确保creative_work是字典格式
        if isinstance(creative_seed, str):
            try:
                creative_work = json.loads(creative_seed)
            except:
                creative_work = {"coreSetting": creative_seed, "coreSellingPoints": "", "completeStoryline": {}}
        else:
            creative_work = creative_seed
        
        # 注入"毒点红线"和"高分蓝图"，并传递平台参数
        refined_creative_seed = self._prepare_refined_seed(creative_work, temp_title_for_filename, target_platform)
        
        # 更新步骤状态：正在生成多个方案
        self._update_step_status('multiple_plans', 'active', 18)
        
        # 生成方案
        plans_data = content_generator.generate_multiple_plans(refined_creative_seed, "")
        
        if not plans_data or 'plans' not in plans_data:
            print("❌ 方案生成失败")
            return None
        
        plans = plans_data['plans']
        print(f"✅ 成功生成 {len(plans)} 个方案")
        
        # 处理主角名字
        self._extract_main_character_name(plans_data, content_generator)
        
        # 更新步骤状态：开始新鲜度评估
        self._update_step_status('freshness_assessment', 'active', 22)
        
        # 评估方案质量
        qualified_plans = self._evaluate_plans(plans, creative_work)
        
        if not qualified_plans:
            print("❌ 所有方案评价均未通过")
            return None
        
        # 更新步骤状态：开始选择最佳方案
        self._update_step_status('plan_selection', 'active', 28)
        
        # 选择最佳方案
        selected_plan = self._select_best_plan(qualified_plans)
        
        # 更新步骤状态：方案选择完成
        if selected_plan:
            self._update_step_status('plan_selection', 'completed', 30)
        
        return selected_plan

    def _prepare_refined_seed(self, creative_work: dict, temp_title: str, target_platform: str = "fanqie") -> str:
        """准备精炼后的创意种子"""
        # 从原NovelGenerator提取的精炼逻辑
        core_setting = creative_work.get("coreSetting", "未提供核心设定。")
        core_selling_points = creative_work.get("coreSellingPoints", "未提供核心卖点。")
        storyline = creative_work.get("completeStoryline", {})
        
        # 构建基础指令模板
        instructions = []
        instructions.append("# AI创作最高指令：创作大纲与绝对约束")
        instructions.append("你是一位顶级的小说策划AI。以下内容是你本次创作的【唯一真相来源】和【绝对行为准则】。你必须严格、完整、精确地遵循所有指令，任何偏离或遗漏都将被视为任务失败。")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第一部分：世界观与不可逾越的边界")
        instructions.append(f"\n**核心设定：**\n{core_setting}")
        
        # 🆕 添加背景资料信息（如果有）
        original_work_background = creative_work.get("original_work_background")
        if original_work_background:
            instructions.append("\n**【背景资料参考】**：")
            instructions.append("以下是原著作品的背景资料，你必须严格遵循这些设定进行创作：")
            
            # 提取并格式化背景资料的关键信息
            # 修正：直接使用标准的背景资料格式
            if isinstance(original_work_background, dict):
                # 世界观信息
                worldview = original_work_background.get("worldview", {})
                if worldview:
                    instructions.append(f"\n- **世界观背景**: {json.dumps(worldview, ensure_ascii=False)}")
                
                # 角色信息
                characters = original_work_background.get("characters", {})
                if characters:
                    key_characters = {}
                    # 只提取主要角色，避免信息过载
                    for char_name, char_data in list(characters.items())[:5]:
                        if isinstance(char_data, str):
                            # 如果是字符串格式，直接使用
                            key_characters[char_name] = char_data
                        elif isinstance(char_data, dict):
                            # 如果是字典格式，提取关键信息
                            key_characters[char_name] = {
                                "身份": char_data.get("身份", char_data.get("身份", "")),
                                "修为": char_data.get("修为", char_data.get("修为", "")),
                                "性格": char_data.get("性格特点", char_data.get("性格", "")),
                                "核心能力": char_data.get("核心能力", char_data.get("能力", ""))
                            }
                    if key_characters:
                        instructions.append(f"\n- **主要角色设定**: {json.dumps(key_characters, ensure_ascii=False, indent=2)}")
                
                # 修炼体系
                power_system = original_work_background.get("power_system", {})
                if power_system:
                    instructions.append(f"\n- **修炼体系**: {json.dumps(power_system, ensure_ascii=False)}")
                
                # 门派势力（如果有）
                sects_and_factions = original_work_background.get("sects_and_factions", {})
                if sects_and_factions:
                    instructions.append(f"\n- **门派势力**: {json.dumps(sects_and_factions, ensure_ascii=False)}")
                
                # 重要地点（如果有）
                important_locations = original_work_background.get("important_locations", {})
                if important_locations:
                    instructions.append(f"\n- **重要地点**: {json.dumps(important_locations, ensure_ascii=False)}")
                
                # 关键宝物（如果有）
                key_treasures = original_work_background.get("key_treasures", {})
                if key_treasures:
                    instructions.append(f"\n- **关键宝物**: {json.dumps(key_treasures, ensure_ascii=False)}")
            
            # 添加验证结果信息
            verification_result = original_work_background.get("verification_result")
            if verification_result:
                credibility_level = verification_result.get("credibility_level", "未知")
                confidence_score = verification_result.get("confidence_score", 0)
                background_source = verification_result.get("background_source", "未知")
                
                instructions.append(f"\n- **背景资料可信度**: {credibility_level} (置信度: {confidence_score:.2f})")
                instructions.append(f"- **数据来源**: {background_source}")
                
                # 如果有问题，添加警告
                issues_found = verification_result.get("issues_found", [])
                if issues_found:
                    instructions.append(f"\n- **需要注意的问题**: {', '.join(issues_found[:3])}")
                    instructions.append(f"- **问题数量**: 共发现 {len(issues_found)} 个问题")
                
                # 添加改进建议
                suggestions = verification_result.get("suggestions", [])
                if suggestions:
                    instructions.append(f"\n- **改进建议**: {', '.join(suggestions[:3])}")
                
                # 如果可信度低，特别提醒
                is_credible = verification_result.get("is_credible", True)
                if not is_credible:
                    instructions.append(f"\n- **⚠️ 重要警告**: 背景资料可信度验证未通过，设计时请特别谨慎，建议优先使用验证通过的信息！")
            
            instructions.append("\n【重要提醒】：所有方案设计必须严格基于以上背景资料，确保与原著设定一致。")
        
        # 自动生成否定约束
        negative_constraints = []
        if "凡人" in core_setting and "落云宗" in core_setting:
            negative_constraints.append("**绝对禁止**：故事时间线在韩立从乱星海回归之后，因此**严禁**让主角前往乱星海、参与虚天殿夺宝等已发生的剧情。主角在结婴前的活动范围**必须**锁定在天南大陆。")
        else:
            negative_constraints.append("**绝对禁止**：你的一切情节设计都不能超出上述【核心设定】所定义的范围。不要引入设定之外的时间段、地点或世界背景。")
        
        instructions.append("\n**绝对禁止事项：**")
        instructions.extend([f"- {constraint}" for constraint in negative_constraints])
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第二部分：核心卖点与执行纲领")
        instructions.append("你的所有情节设计，都必须以服务和凸显以下核心卖点为首要目标：")
        instructions.append(f"\n{core_selling_points}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 第三部分：分阶段故事线框架")
        instructions.append("你必须严格按照以下阶段的设定来构建故事的起承转合。")
        
        if storyline:
            for stage_key, stage_data in storyline.items():
                stage_name = stage_data.get('stageName', '未知阶段')
                summary = stage_data.get('summary', '无')
                arc_goal = stage_data.get('arc_goal', '无')
                
                instructions.append(f"\n### {stage_name}")
                instructions.append(f"- **情节概要：** {summary}")
                instructions.append(f"- **强制目标：** {arc_goal}")
        
        instructions.append("\n" + "="*30)
        instructions.append("\n## 最终指令确认")
        instructions.append("以上所有内容是不可违背的创作铁律。现在，请基于这份【最高指令】，开始你的工作。")
        
        refined_seed = "\n".join(instructions)
        
        # 🔥 获取平台适配器
        platform_guidance = ""
        if self.platform_adapter_factory:
            adapter = self.platform_adapter_factory.get_adapter(target_platform)
            platform_context = adapter.get_prompt_context()
            platform_style_guide = adapter.get_content_style_guide()
            
            platform_guidance = f"""

## 📱 平台适配指导 (目标平台: {adapter.platform_name})

{platform_context}

{platform_style_guide}

【重要提示】：
- 标题创作必须遵循 {adapter.platform_name} 的标题风格指南
- 内容风格必须符合上述平台风格指导
- 简介和核心卖点需要针对该平台读者群体进行优化
"""
        else:
            # 默认使用番茄风格
            platform_guidance = """

## 📱 平台适配指导 (目标平台: 番茄小说)

**目标平台：番茄小说**
番茄小说是字节跳动旗下的免费阅读平台，用户群体庞大，偏好快节奏、强代入感的爽文。

**平台特点：**
1. **读者画像**：以年轻读者为主（18-35岁），喜欢轻松、直接的阅读体验
2. **阅读场景**：碎片化阅读为主，需要快速吸引注意力
3. **付费模式**：免费阅读+广告变现，依靠高留存率和完读率
4. **推荐机制**：基于完读率、追读率、互动数据推荐

**内容偏好：**
- **黄金三章**：前3章必须有强烈冲突、金手指激活、打脸逆袭
- **高爽点密度**：每章都要有小高潮，每3-5章一个大高潮
- **强代入感**：主角设定贴近普通人，让读者容易代入
- **直白易懂**：语言简洁，避免复杂设定和长篇解释
- **情绪调动**：愤怒→压抑→爆发→爽快的情绪曲线

**标题风格**：6-14字，简洁、有冲击力、抓眼球
"""
        
        # 注入平台指导、规则和蓝图
        return refined_seed + platform_guidance + "\n\n" + self.POISON_POINT_RULES_FOR_GENERATION + "\n\n" + self.HIGH_SCORING_PLAN_BLUEPRINT

    def _extract_main_character_name(self, plans_data: Dict, content_generator):
        """提取并设置主角名字"""
        suggestions = plans_data.get("suggestions", [])
        if suggestions:
            name = suggestions[0].get("name")
            if name and 2 <= len(name) <= 3:
                print(f"  ✅ 获取主角名字: {name}")
                content_generator.set_custom_main_character_name(name)
                return
        
        # 备选方案
        name = plans_data.get("name")
        if name and 2 <= len(name) <= 3:
            print(f"  ✅ 获取主角名字: {name}")
            content_generator.set_custom_main_character_name(name)

    def _evaluate_plans(self, plans: List[Dict], creative_work: dict) -> List[Dict]:
        """
        评估方案质量 - 🔥 优化版本：优先使用AI自带评分，减少API调用
        """
        qualified_plans = []
        
        for i, plan in enumerate(plans):
            print(f"  🔍 评估方案 {i+1}...")
            
            # 获取分类信息
            category_from_plan = plan.get('tags', {}).get('main_category', '未分类')
            
            # 分类修正逻辑
            category_from_plan = self._correct_category(plan, creative_work, category_from_plan)
            
            # 🔥 优化：优先使用AI自带的评分（减少API调用）
            ai_quality_score = plan.get('_quality_score', 0)
            ai_freshness_score = plan.get('_freshness_score', 0)
            ai_total_score = plan.get('_total_score', 0)
            
            # 如果AI自带评分且分数合理，直接使用
            if ai_quality_score >= 7.0 and ai_freshness_score >= 2.5:
                quality_score = ai_quality_score
                freshness_score = ai_freshness_score
                total_score = ai_total_score
                
                evaluation_result = {
                    "quality_score": quality_score,
                    "freshness_score": freshness_score,
                    "total_score": total_score,
                    "evaluation_notes": plan.get('_evaluation_notes', 'AI自评'),
                    "source": "ai_self_assessment"
                }
                print(f"    ✅ 使用AI自带评分 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
            else:
                # AI评分不合格，进行额外评估
                print(f"    🔄 AI自评分数不足，进行深度评估...")
                evaluation_result = self._evaluate_single_plan(plan, category_from_plan, creative_work)
                
                quality_score = evaluation_result.get("quality_score", 0)
                freshness_score = evaluation_result.get("freshness_score", 0)
                total_score = evaluation_result.get("total_score", 0)
            
            # 记录评分到方案数据
            plan['_quality_score'] = quality_score
            plan['_freshness_score'] = freshness_score
            plan['_total_score'] = total_score
            
            # 🔥 优化：降低门槛到质量7.5/新鲜度2.5（因为只生成2个高质量方案）
            if quality_score >= 7.5 and freshness_score >= 2.5:
                qualified_plans.append({
                    'plan': plan,
                    'quality_score': quality_score,
                    'freshness_score': freshness_score,
                    'total_score': total_score,
                    'evaluation_result': evaluation_result,
                    'category': category_from_plan
                })
                print(f"    ✅ 方案 {i+1} 通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
            else:
                print(f"    ❌ 方案 {i+1} 未通过评价 (质量: {quality_score:.1f}, 新鲜度: {freshness_score:.1f})")
        
        return qualified_plans

    def _correct_category(self, plan: Dict, creative_work: dict, current_category: str) -> str:
        """修正方案分类"""
        title = plan.get('title', '')
        synopsis = plan.get('synopsis', '')
        keywords = plan.get('tags', {}).get('keywords', [])
        keywords_str = "".join(keywords)
        
        # 检查创意种子内容
        creative_core_setting = creative_work.get('coreSetting', '') if isinstance(creative_work, dict) else str(creative_work)
        creative_selling_points = creative_work.get('coreSellingPoints', '') if isinstance(creative_work, dict) else ""
        
        # 合并所有文本进行检查
        combined_text = f"{title} {synopsis} {keywords_str} {creative_core_setting} {creative_selling_points}"
        
        has_tongren = "同人" in combined_text
        has_dongman = any(keyword in combined_text for keyword in ["动漫", "动画", "漫画"])
        
        if has_tongren:
            if has_dongman:
                corrected_category = "动漫衍生"
                reason = "同人+动漫"
            else:
                corrected_category = "男频衍生" 
                reason = "同人"
            
            print(f"    🔄 分类修正: 检测到'{reason}'关键字，分类已修正为 '{corrected_category}'")
            
            if 'tags' not in plan:
                plan['tags'] = {}
            plan['tags']['main_category'] = corrected_category
            print(f"    📝 同步更新方案内部分类字段")
            
            return corrected_category
        
        return current_category

    def _evaluate_single_plan(self, plan: Dict, category: str, creative_seed) -> Dict:
        """评估单个方案的质量"""
        # 🔧 修复：即使 quality_assessor 未初始化，也要调用AI进行新鲜度评估
        if self.quality_assessor is None:
            print("  ⚠️ 质量评估器尚未初始化，直接调用AI进行新鲜度评估")
            freshness_result = self._ai_freshness_assessment(plan, category, creative_seed)
        else:
            # 使用质量评估器进行新鲜度评估
            freshness_result = self.quality_assessor.assess_freshness(plan, "novel_plan")
        
        freshness_score = freshness_result["score"]["total"]
        
        # 构建质量评估提示词
        title = plan.get('title', '')
        synopsis = plan.get('synopsis', '')
        core_direction = plan.get('core_direction', '')
        golden_finger = plan.get('core_settings', {}).get('golden_finger', '')
        core_selling_points = plan.get('core_settings', {}).get('core_selling_points', [])
        world_background = plan.get('core_settings', {}).get('world_background', '')
        main_character_archetype = plan.get('main_character', {}).get('archetype', '')

        quality_prompt = f"""
        你是一位**拥有超过50年经验、眼光毒辣、对网文商业成功和艺术质量有着极度严苛、吹毛求疵**的顶级网文主编，同时也是一个追求**商业价值与艺术成就双丰收的"网文传世经典"**的超级评审员。你的任务是对以下小说方案进行**最高标准的艺术性与市场价值评估**。你必须找出**任何可能阻碍其成为"网文精品乃至现象级爆款"**的瑕疵，并给出**提升至市场和口碑双赢的、可操作的、有建设性的建议**。

        【小说分类】{category}
        【创意种子】{creative_seed} (这是最初的灵感源泉，你需评估方案是否完美继承并升华了它，使其更符合网文市场爆款潜力)

        【待评估小说方案内容】
        书名：《{title}》
        简介：{synopsis}
        核心方向：{core_direction}
        核心世界观概要: {world_background}
        金手指：{golden_finger}
        核心卖点：{json.dumps(core_selling_points, ensure_ascii=False)}
        主角原型/人设初步构思: {main_character_archetype}

        【！！！最高评价标准 (请你以"能否成为网文现象级爆款"的标准，极度严格地审查)！！！】
        以下每一项都将以10分制打分，并给出极其详细的评语：
        """

        try:
            # 调用AI进行质量评价
            quality_result = self.api_client.generate_content_with_retry(
                "plan_quality_evaluation_super_reviewer",
                quality_prompt,
                purpose="【AI超级评审员】进行方案质量评价"
            )

            if quality_result:
                # 安全获取分数
                def safe_get_score(result, key, default=0.0):
                    score = result.get(key, default)
                    if isinstance(score, str):
                        try:
                            import re
                            numbers = re.findall(r'\d+\.?\d*', score)
                            return float(numbers[0]) if numbers else default
                        except (ValueError, TypeError):
                            return default
                    elif isinstance(score, (int, float)):
                        return float(score)
                    return default

                overall_quality_score = safe_get_score(quality_result, "overall_quality_score", 0.0)
                gf_score = safe_get_score(quality_result, "golden_finger_score", 0.0)
                sp_score = safe_get_score(quality_result, "selling_points_score", 0.0)
                wv_score = safe_get_score(quality_result, "worldview_coherence_score", 0.0)
                cd_score = safe_get_score(quality_result, "character_depth_score", 0.0)

                # 为了兼容性，将分数存入quality_result
                quality_result["golden_finger_score"] = gf_score
                quality_result["selling_points_score"] = sp_score
                quality_result["worldview_coherence_score"] = wv_score
                quality_result["character_depth_score"] = cd_score
                quality_result["overall_quality_score"] = overall_quality_score

                # 计算总分（降低新鲜度权重，提高整体质量权重）
                total_score = (overall_quality_score * 0.8) + (freshness_score * 0.2)

                result = {
                    "quality_score": overall_quality_score,
                    "freshness_score": freshness_score,
                    "freshness_details": freshness_result,
                    "total_score": total_score,
                    "quality_details": quality_result,
                    "super_reviewer_verdict": quality_result.get("verdict", "未知"),
                    "perfection_suggestions": quality_result.get("recommendations", []),
                    "recommendation": overall_quality_score >= 8.5 and freshness_score >= 7.5
                }

                print(f"📊 AI【超级评审员】评估结果:")
                print(f"  🥇 总质量评分: {overall_quality_score:.1f}/10分")
                print(f"  📈 新鲜度评分: {freshness_score:.1f}/10分")
                print(f"  🌟 最终综合评分: {total_score:.1f}/10分")
                print(f"  💬 评审员最终评语: {result['super_reviewer_verdict']}")

                recommendations_list = result.get('perfection_suggestions', [])
                if recommendations_list:
                    print(f"  💡 提升建议: {recommendations_list}")

                print(f'  ✨ 是否达到"精品"标准: {"是" if result["recommendation"] else "否"}')

                return result
            else:
                print("  ⚠️ AI【超级评审员】评估失败或未返回有效数据。")
                return {
                    "quality_score": 0.0,
                    "freshness_score": freshness_score,
                    "total_score": freshness_score,
                    "recommendation": False
                }

        except Exception as e:
            print(f"⚠️ AI【超级评审员】评估过程中出错: {e}，使用默认评分。")
            return {
                "quality_score": 0.0,
                "freshness_score": freshness_score,
                "total_score": freshness_score,
                "recommendation": False
            }

    def _select_best_plan(self, qualified_plans: List[Dict]) -> Optional[Dict]:
        """选择最佳方案"""
        if not qualified_plans:
            return None
        
        # 按总分排序
        qualified_plans.sort(key=lambda x: x['total_score'], reverse=True)
        best_plan_data = qualified_plans[0]
        
        print(f"\n🏆 已确定最优方案: 《{best_plan_data['plan'].get('title', '未知标题')}》")
        print(f"   【AI超级评审员】总评分: {best_plan_data['total_score']:.2f} (总质量: {best_plan_data['quality_score']:.1f}, 新鲜度: {best_plan_data['freshness_score']:.1f})")
        print(f"   分类: {best_plan_data['category']}")
        
        return best_plan_data['plan']

    def _ai_freshness_assessment(self, plan: Dict, category: str, creative_seed) -> Dict:
        """
        使用AI直接进行新鲜度评估（当QualityAssessor未初始化时使用）
        
        Args:
            plan: 方案数据
            category: 分类
            creative_seed: 创意种子
            
        Returns:
            新鲜度评估结果（与QualityAssessor返回格式相同）
        """
        print("  📊 使用AI进行新鲜度评估")
        
        try:
            # 构建新鲜度评估提示词
            freshness_prompt = self._generate_freshness_assessment_prompt(plan, category, creative_seed)
            
            # 调用AI进行评估
            result = self.api_client.generate_content_with_retry(
                "freshness_assessment",
                freshness_prompt,
                purpose="方案新鲜度评估"
            )
            
            if result and "score" in result:
                print(f"    ✅ AI新鲜度评估成功，总分: {result['score'].get('total', 0):.1f}")
                return self._validate_freshness_result(result)
            else:
                print(f"    ⚠️ AI评估失败，使用默认评分")
                return self._get_default_freshness_assessment()
                
        except Exception as e:
            print(f"    ❌ AI新鲜度评估出错: {e}")
            return self._get_default_freshness_assessment()
    
    def _generate_freshness_assessment_prompt(self, plan: Dict, category: str, creative_seed) -> str:
        """生成新鲜度评估提示词"""
        import json
        
        title = plan.get('title', '')
        synopsis = plan.get('synopsis', '')
        core_direction = plan.get('core_direction', '')
        golden_finger = plan.get('core_settings', {}).get('golden_finger', '')
        core_selling_points = plan.get('core_settings', {}).get('core_selling_points', [])
        
        return f"""
你是一位顶级的网络小说市场分析师，精通数据分析，对起点、番茄、飞卢等主流平台的流行趋势、读者偏好和内容稀缺性了如指掌。

## 核心任务
你的核心任务是基于用户提供的小说方案，从市场角度进行严格、客观、数据驱动的新鲜度评估，并提供可行的改进建议，帮助创意脱颖而出。

## 待评估方案内容
**分类**: {category}
**书名**: 《{title}》
**简介**: {synopsis}
**核心方向**: {core_direction}
**金手指**: {golden_finger}
**核心卖点**: {json.dumps(core_selling_points, ensure_ascii=False)}

## 评估维度（总分10分）

### 1. 核心概念新颖度 (3分)
- 金手指设定是否有创新性，避免常见套路
- 核心设定是否在市场中具有独特性
- 主角身份和开局设定是否新颖

### 2. 系统机制创新度 (3分)
- 金手指的玩法机制是否有新意
- 成长体系是否与众不同
- 爽点设计是否避免了常见的模板化

### 3. 市场稀缺性 (4分)
- 与当前热门作品的差异化程度
- 是否填补了市场空白
- 目标读者群体的竞争态势

## 输出格式要求
请严格按照以下JSON格式返回评估结果：

```json
{{
    "score": {{
        "total": 总分(满分10分),
        "core_concept_novelty": 核心概念新颖度分数,
        "system_innovation": 系统机制创新度分数,
        "market_scarcity": 市场稀缺性分数
    }},
    "analysis": {{
        "core_concept_novelty": "核心概念新颖度分析",
        "system_innovation": "系统机制创新度分析",
        "market_scarcity": "市场稀缺性分析"
    }},
    "verdict": "总体评价（优秀/良好/中规中矩/待提升）",
    "suggestions": [
        "具体改进建议1",
        "具体改进建议2",
        "具体改进建议3"
    ]
}}
```

请立即开始评估，只返回JSON结果，不要其他解释。
"""
    
    def _validate_freshness_result(self, result: Dict) -> Dict:
        """验证新鲜度评估结果的新结构"""
        # 确保所有必需的字段都存在
        required_structure = {
            "score": {
                "total": 0,
                "core_concept_novelty": 0,
                "system_innovation": 0,
                "market_scarcity": 0
            },
            "analysis": {
                "core_concept_novelty": "",
                "system_innovation": "",
                "market_scarcity": ""
            },
            "verdict": "中规中矩",
            "suggestions": []
        }
        # 确保顶层字段存在
        for key, default_value in required_structure.items():
            if key not in result:
                result[key] = default_value
            elif isinstance(default_value, dict):
                # 确保嵌套字典字段存在
                for sub_key, sub_default in default_value.items():
                    if sub_key not in result[key]:
                        result[key][sub_key] = sub_default
        return result
    
    def _get_default_freshness_assessment(self) -> Dict:
        """获取默认的新鲜度评估结果 - 新结构"""
        return {
            "score": {
                "total": 6.0,
                "core_concept_novelty": 6.0,
                "system_innovation": 6.0,
                "market_scarcity": 6.0
            },
            "analysis": {
                "core_concept_novelty": "评估异常",
                "system_innovation": "评估异常",
                "market_scarcity": "评估异常"
            },
            "verdict": "评估异常",
            "suggestions": ["重新评估内容新鲜度", "增加创新元素", "避免常见套路"]
        }
    
    def optimize_plan_with_market_data(self, plan: Dict, category: str, optimization_params: Dict) -> Optional[Dict]:
        """使用市场数据优化方案"""
        if self.quality_assessor is None:
            print("  ⚠️ 质量评估器未初始化，跳过方案优化")
            return None
        
        try:
            optimized_plan = self.quality_assessor.optimize_novel_plan(plan, optimization_params)
            return optimized_plan
        except Exception as e:
            print(f"⚠️ 方案优化失败: {e}")
            return None