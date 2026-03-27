"""
市场导向对话生成器
在一个连续对话中完成套路分析 → 方案生成 → 一阶段产物生成
利用Kimi的256K上下文窗口和缓存机制

v2.0更新：基于爆款反向工程分析生成Prompt
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

# 导入新的分析器和模板生成器
try:
    from web.services.market_driven.bestseller_analyzer import BestsellerAnalyzer
    from web.services.market_driven.prompt_templates import PromptTemplateGenerator
    HAS_BESTSELLER_ANALYSIS = True
except ImportError:
    HAS_BESTSELLER_ANALYSIS = False
    logging.warning("[MarketDrivenConversation] 爆款分析模块未加载，将使用传统Prompt")

# 导入TropePromptBuilder（分层System Prompt支持）
try:
    from web.services.market_driven.trope_prompt_builder import TropePromptBuilder
    HAS_TROPE_PROMPT_BUILDER = True
    logging.info("[MarketDrivenConversation] TropePromptBuilder已加载")
except ImportError:
    HAS_TROPE_PROMPT_BUILDER = False
    logging.warning("[MarketDrivenConversation] TropePromptBuilder未加载")

logger = logging.getLogger(__name__)


class ConversationLogger:
    """对话生成日志记录器 - 保存为极简格式"""
    
    def __init__(self, session_id: str, log_dir: str = "logs/ai_interactions", novel_title: str = ""):
        self.session_id = session_id
        self.novel_title = novel_title
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.start_time = datetime.now()
        self.round_count = 0
        
    def _sanitize_filename(self, text: str) -> str:
        """清理文件名，去除特殊字符"""
        import re
        # 保留中文、英文、数字，替换其他字符为下划线
        sanitized = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '_', text)
        # 限制长度
        return sanitized[:20] if sanitized else "未命名"
        
    def log_round(self, step: str, messages: List[Dict], response: str):
        """
        记录一轮对话（极简格式）
        每个轮次单独一个文件
        """
        self.round_count += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 🔥 构建文件名：包含书名前缀（如果有）
        if self.novel_title:
            title_prefix = self._sanitize_filename(self.novel_title)
            log_file = self.log_dir / f"{self.session_id}_{title_prefix}_round{self.round_count:02d}_{step}_{timestamp}.md"
        else:
            log_file = self.log_dir / f"{self.session_id}_round{self.round_count:02d}_{step}_{timestamp}.md"
        
        lines = [
            f"# Round {self.round_count} - {step}",
            f"**Time**: {datetime.now().strftime('%H:%M:%S')}",
            f"**Messages**: {len(messages)}",
            "",
            "## Messages sent to AI",
            "",
            "```json",
            json.dumps(messages, ensure_ascii=False, indent=2),
            "```",
            "",
            "## AI Response",
            "",
            "```",
            response[:2000] + "..." if len(response) > 2000 else response,
            "```"
        ]
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            logger.info(f"[对话日志] Round {self.round_count} 已保存: {log_file}")
        except Exception as e:
            logger.error(f"[对话日志] 保存失败: {e}")


class MarketDrivenConversationSession:
    """
    市场导向对话会话
    
    流程：
    1. 发送完整的用户选择（标题、剧情路线、主角、金手指等）
    2. AI生成方案（基于套路模板微调）
    3. 基于方案继续生成一阶段产物（世界观、角色、情绪曲线等）
    
    所有步骤在一个对话中完成，保持上下文连贯
    """
    
    # 生成步骤
    STEPS = [
        "generate_plan",           # 生成完整方案
        "generate_worldview",      # 生成世界观
        "generate_characters",     # 生成角色设计
        "generate_growth_plan",    # 生成成长路线
        "generate_emotion_curve",  # 生成情绪曲线
    ]
    
    def __init__(self, api_client, genre: str, user_choices: Dict, 
                 tropes: Optional[Dict] = None, provider: str = "kimi"):
        """
        初始化市场导向对话会话
        
        Args:
            api_client: APIClient实例
            genre: 题材
            user_choices: 用户选择（包含标题、剧情路线、主角等）
            tropes: 套路分析结果（可选，作为参考）
            provider: 提供商，默认kimi
        """
        if provider != "kimi":
            raise ValueError(f"仅支持kimi provider, 当前: {provider}")
        
        self.api_client = api_client
        self.genre = genre
        self.user_choices = user_choices
        self.tropes = tropes or {}
        self.provider = provider
        self.results = {}
        
        # 🔥 生成唯一会话ID，用于日志追踪
        import uuid
        self.session_id = f"MDC-{uuid.uuid4().hex[:8].upper()}"
        
        # 🔥 基于爆款反向工程分析，生成高质量Prompt模板
        self._prompt_generator = None
        if HAS_BESTSELLER_ANALYSIS and api_client:
            try:
                logger.info(f"[对话模式 {self.session_id}] 启动爆款反向工程分析...")
                analyzer = BestsellerAnalyzer(api_client=api_client)
                bestseller_analysis = analyzer.analyze_genre(genre, use_cache=True)
                
                # 验证分析结果是否有效
                if bestseller_analysis and isinstance(bestseller_analysis, dict):
                    if not bestseller_analysis.get("parse_error") and "genre_formula" in bestseller_analysis:
                        self._prompt_generator = PromptTemplateGenerator(bestseller_analysis)
                        logger.info(f"[对话模式 {self.session_id}] ✅ 爆款分析完成，已加载高质量Prompt模板")
                    else:
                        logger.warning(f"[对话模式 {self.session_id}] ⚠️ 爆款分析结果无效，使用默认模板")
                else:
                    logger.warning(f"[对话模式 {self.session_id}] ⚠️ 爆款分析返回空结果，使用默认模板")
            except Exception as e:
                logger.warning(f"[对话模式 {self.session_id}] ⚠️ 爆款分析失败，将使用传统Prompt: {e}")
        
        # 创建对话会话
        from src.core.APIClient import ConversationSession
        system_prompt = self._build_system_prompt()
        
        # 🔥 创建对话日志记录器（传入书名，用于文件名）
        novel_title = self.user_choices.get('title', '')
        self._logger = ConversationLogger(self.session_id, novel_title=novel_title)
        logger.info(f"[对话模式 {self.session_id}] 日志记录器已启动，书名: {novel_title or '未命名'}")
        
        self.session = ConversationSession(
            api_client=api_client,
            system_prompt=system_prompt,
            provider=provider,
            purpose_prefix=f"MDC-{self.session_id}"  # 用于日志标识
        )
        # 设置历史限制（直接修改属性）
        self.session.max_history = 20
        
        logger.info(f"[对话模式 {self.session_id}] 会话创建 | 题材: {genre} | 标题: {user_choices.get('title', 'Unknown')} | 使用高质量Prompt: {self._prompt_generator is not None}")
    
    def _filter_tropes_for_prompt(self) -> Dict:
        """
        过滤套路分析结果，只保留必要信息，移除干扰选项
        
        移除内容：
        - title_templates: 所有备选标题（用户已选择）
        - plot_templates: 只保留用户选择的那条路线
        
        保留内容：
        - core_formula: 核心套路公式
        - golden_finger: 金手指设计
        - protagonist: 主角人设模板
        - opening_pattern: 开局3章剧本
        - pacing: 节奏控制
        - stage_rhythm: 阶段性节奏
        - antagonist: 反派设计
        - worldview: 世界观
        - emotion_curve: 情绪曲线
        - must_have/must_not_have: 必须有/不能有
        - platform_tips: 平台技巧
        """
        import copy
        
        # 深拷贝避免修改原始数据
        filtered = copy.deepcopy(self.tropes)
        
        # 获取用户选择的剧情路线名称
        selected_plot = self.user_choices.get('selected_plot', {})
        selected_plot_name = selected_plot.get('name', '') if selected_plot else ''
        
        # 1. 移除所有备选标题（用户已确定标题，不需要其他选项）
        if 'title_templates' in filtered:
            del filtered['title_templates']
        
        # 2. 只保留用户选择的那条剧情路线
        if 'plot_templates' in filtered and selected_plot_name:
            original_plots = filtered['plot_templates']
            # 查找用户选择的那条路线
            selected_plot_template = None
            for plot in original_plots:
                if plot.get('name') == selected_plot_name:
                    selected_plot_template = plot
                    break
            
            if selected_plot_template:
                # 只保留用户选择的那条
                filtered['plot_templates'] = [selected_plot_template]
            else:
                # 如果没找到，清空（避免AI看到其他选项）
                filtered['plot_templates'] = []
        
        return filtered
    
    def _build_system_prompt(self) -> str:
        """构建系统提示词 - 使用TropePromptBuilder分层架构"""
        # 用户选择的信息（必须明确标注）
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        golden_finger = self.user_choices.get('golden_finger_desc', '金手指')
        main_plot = self.user_choices.get('main_plot', '主线剧情')
        
        # 获取剧情路线
        selected_plot = self.user_choices.get('selected_plot', {})
        plot_name = selected_plot.get('name', '默认路线') if selected_plot else '默认路线'
        plot_detail = selected_plot.get('detail', '') if selected_plot else ''
        
        # 🔥 使用TropePromptBuilder构建基础System Prompt（仿写头部作品框架）
        if HAS_TROPE_PROMPT_BUILDER:
            try:
                builder = TropePromptBuilder(self.tropes)
                base_prompt = builder.build_setting_system_prompt(title)
                logging.info(f"[对话模式 {self.session_id}] 使用TropePromptBuilder构建System Prompt")
            except Exception as e:
                logging.warning(f"[对话模式 {self.session_id}] TropePromptBuilder失败，使用默认框架: {e}")
                base_prompt = self._build_default_setting_prompt(title)
        else:
            base_prompt = self._build_default_setting_prompt(title)
        
        # 🔥 清理套路分析结果，只保留必要信息
        filtered_tropes = self._filter_tropes_for_prompt()
        tropes_json = json.dumps(filtered_tropes, ensure_ascii=False, indent=2)
        
        # 构建用户约束部分
        user_constraints = f"""
---

## 🎯 【用户最终选择 - 必须严格遵循】

### ✅ 最终确定的书名（必须使用）
**{title}**

### ✅ 最终确定的主角姓名（必须使用，禁止更改）
**{protagonist_name}**

⚠️ **强制要求**： protagonist.name 必须是 "{protagonist_name}"，禁止起任何其他名字或别名！

### ✅ 最终确定的金手指（必须使用）
**{golden_finger}**

### ✅ 参考剧情路线（仅作参考，非强制）
**{plot_name}**

```
{plot_detail}
```

### ✅ 主线剧情方向
```
{main_plot}
```

---

## 📊 【套路分析结果 - 参考依据】

以下是对该题材Top10爆款的分析结果，**仅供参考，用于启发创作**。AI应基于这些套路自由创作，不必严格遵循固定情节。

```json
{tropes_json}
```

---

## 🔥 AI自由创作提示
- 你可以自由设计BOSS类型（神话生物/机械/外星/克苏鲁等）
- 你可以自由设计敌人组合（任意国家/组织/联盟）
- 你可以自由设计战斗过程（任意战术/能力组合/场景）
- 你可以自由设计具现奖励（能源/科技/军事/民生等任意类型）
- 唯一约束：必须符合情绪蓝图的节奏要求！

## 你的工作流程
你将按照以下顺序完成创作，每轮对话我会指示你进行下一步：

1. **生成完整方案** - 基于用户选择和套路，生成标题确认、开局设计、金手指细化、主角人设、前30章大纲
2. **生成世界观** - 基于题材套路，创建世界观框架和势力系统
3. **生成角色设计** - 基于主角人设和剧情路线，设计完整的角色阵容
4. **生成成长路线** - 基于前30章大纲，规划主角成长里程碑
5. **生成情绪曲线** - 基于剧情节奏，设计每章的情绪节拍

## 核心规则
1. **固定元素必须遵循**：书名、主角名、题材类型、系统类型（如果有）必须严格遵循用户选择
2. **自由创作**：具体情节、BOSS设计、敌人组合、奖励类型等由AI自由发挥，不必遵循固定大纲
3. **情绪蓝图约束**：必须遵循情绪节奏（每章强度、爽点类型、钩子设计），但具体情节自由
4. **不可预测性**：避免套路化，让读者猜不到下一章会发生什么
5. **番茄风格**：快节奏、强爽点、章章有钩子

## 输出规范
- 所有输出必须是合法的 JSON 格式
- 使用中文，符合中国网文市场特点
- 保持前后一致，后续步骤要参考前面的设定
- 每轮只输出当前步骤的内容

## 当前状态
等待第 1 步指令：生成完整方案...
"""
        
        return base_prompt + user_constraints
    
    def _build_default_setting_prompt(self, title: str) -> str:
        """构建默认的设定阶段System Prompt（当TropePromptBuilder不可用时使用）"""
        return f"""# 🎯 角色：顶级网文策划专家

你正在为一部网络小说进行【市场导向创作】。这是一个基于爆款套路的连续创作过程，你将通过多轮对话逐步完成所有设定。

目标作品：《{title}"

## 🎨 创作指导原则

### ✅ 必须做到的
1. **结构对标**：遵循成功模式的叙事结构
2. **数值精确**：所有数据必须具体（如"欠费24000元"而非"欠很多钱"）
3. **节奏精准**：情绪曲线必须符合类型规范
4. **创新内容**：在成功结构的框架下创造全新具体内容

### ❌ 严禁事项
1. **直接抄袭**：不要复制对标作品的具体情节、人物名字
2. **套路堆砌**：不要为了爽而爽，忽视逻辑
3. **数值模糊**：禁止"很多"、"很快"等模糊描述
4. **节奏混乱**：禁止情绪回退（爽点后突然压抑）

## ⚠️ 重要规则

1. **固定元素必须遵循**：书名、主角名、题材类型、系统类型（如果有）必须严格遵循用户选择
2. **自由创作**：具体情节、BOSS设计、敌人组合、奖励类型等由AI自由发挥，不必遵循固定大纲
3. **情绪蓝图约束**：必须遵循情绪节奏（每章强度、爽点类型、钩子设计），但具体情节自由
4. **不可预测性**：避免套路化，让读者猜不到下一章会发生什么
5. **番茄风格**：快节奏、强爽点、章章有钩子
"""
    
    def generate_all(self, progress_callback=None) -> Dict:
        """
        执行所有生成步骤
        
        Args:
            progress_callback: 进度回调函数(step_name, progress_percent)
        
        Returns:
            所有产物字典
        """
        results = {
            "generation_mode": "market_driven_conversation",
            "generated_at": datetime.now().isoformat(),
            "genre": self.genre,
        }
        
        logger.info(f"[对话模式 {self.session_id}] 开始5步对话生成流程...")
        
        # 步骤1: 生成方案 (20%) -> UI阶段: planning
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1/5: 生成完整方案")
        if progress_callback:
            progress_callback("generate_plan", 20)
        plan = self._generate_plan()
        results["plan"] = plan
        results["title"] = plan.get("title", "")
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1完成 | 标题: {plan.get('title', 'N/A')}")
        
        # 步骤2: 生成世界观 (35%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤2/5: 生成世界观")
        if progress_callback:
            progress_callback("generate_worldview", 35)
        worldview = self._generate_worldview()
        results["core_worldview"] = worldview
        results["faction_system"] = self._extract_faction_system(worldview)
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤2完成")
        
        # 步骤3: 生成角色 (50%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤3/5: 生成角色设计")
        if progress_callback:
            progress_callback("generate_characters", 50)
        characters = self._generate_characters()
        results["character_design"] = characters
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤3完成")
        
        # 步骤4: 生成成长路线 (65%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤4/5: 生成成长路线")
        if progress_callback:
            progress_callback("generate_growth_plan", 65)
        growth_plan = self._generate_growth_plan()
        results["global_growth_plan"] = growth_plan
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤4完成")
        
        # 步骤5: 生成情绪曲线 (80%) -> UI阶段: chapters
        logger.info(f"[对话模式 {self.session_id}] [UI:chapters] 步骤5/5: 生成情绪曲线")
        if progress_callback:
            progress_callback("generate_emotion_curve", 80)
        emotion_curve = self._generate_emotion_curve()
        results["emotion_curve"] = emotion_curve
        logger.info(f"[对话模式 {self.session_id}] [UI:chapters] 步骤5完成")
        
        # 补充产物
        results["writing_style_guide"] = self._generate_writing_style_guide()
        results["market_analysis"] = self._generate_market_analysis()
        results["emotional_blueprint"] = self._generate_emotional_blueprint()
        
        logger.info(f"[对话模式 {self.session_id}] ✅ 所有步骤完成 | 总轮次: {self.session.turn_count}")
        return results
    
    def _generate_plan(self) -> Dict:
        """生成完整方案（使用基于爆款的Prompt模板）"""
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        selected_plot = self.user_choices.get('selected_plot', {})
        
        # 🔥 使用基于爆款分析的Prompt模板（如果可用）
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤1）")
            prompt = self._prompt_generator.generate_step1_plan_prompt(
                title=title,
                protagonist_name=protagonist_name,
                selected_plot=selected_plot,
                tropes=self.tropes
            )
        else:
            # 传统Prompt（备用）
            prompt_parts = [
                "请执行【步骤1：生成完整方案】\n",
                "基于系统提示词中的【用户最终选择】和【完整的套路分析结果】，生成完整的小说方案。\n",
                "## 重要提醒",
                f'1. **书名**：必须使用用户确定的「{title}」',
                f'2. **主角名**：必须使用用户确定的「{protagonist_name}」',
                "3. **剧情路线**：参考用户选择的剧情路线，但具体情节由AI自由创作",
                "4. **情绪蓝图约束**：遵循情绪节奏（第1-3章钩子、第4-10章小高潮密集、第21-30章大高潮），但具体情节自由\n",
                "## 你需要生成",
                "1. **标题确认** - 确认使用用户确定的标题（≤15字）",
                "2. **开局设计** - 第1-3章详细剧本（情绪弧：压抑→震惊→希望）",
                "3. **金手指细化** - 基于用户描述，细化具体数值和成长曲线",
                "4. **主角人设** - 生成完整人设",
                "5. **前30章情绪蓝图** - 只定义每章情绪类型和强度，不定义具体情节\n",
                "## 输出格式",
                "返回JSON格式，包含: title, opening_design, golden_finger, protagonist, emotion_blueprint\n",
                "只返回JSON，不要其他说明。"
            ]
            prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤1提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_round("generate_plan", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤1响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "plan")
    
    def _generate_worldview(self) -> Dict:
        """生成世界观（使用基于爆款的Prompt模板）"""
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤2）")
            prompt = self._prompt_generator.generate_step2_worldview_prompt()
        else:
            # 传统Prompt
            prompt = """请执行【步骤2：生成世界观】

基于系统提示词中的【完整的套路分析结果】和已确定的题材、主角设定，生成完整的世界观。

## 关键要求
1. 世界观必须支持主角的金手指和成长路线
2. 势力系统必须提供足够的冲突来源
3. 社会规则必须有利于"装逼打脸"情节

## 输出格式
返回JSON格式，包含: world_overview, power_system, social_structure, factions, world_rules, key_locations

只返回JSON。"""
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤2提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_round("generate_worldview", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤2响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "worldview")
    
    def _generate_characters(self) -> Dict:
        """生成角色设计（使用基于爆款的Prompt模板 + TropePromptBuilder人物设定约束）"""
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        
        # 🔥 更新System Prompt为人物设定阶段（让AI知道在仿写头部作品的人设）
        if HAS_TROPE_PROMPT_BUILDER:
            try:
                builder = TropePromptBuilder(self.tropes)
                character_system_prompt = builder.build_character_system_prompt(protagonist_name)
                # 更新session的system message
                if self.session.messages and self.session.messages[0].get("role") == "system":
                    self.session.messages[0]["content"] = character_system_prompt
                    logger.info(f"[对话模式 {self.session_id}] 已更新System Prompt为人物设定阶段")
            except Exception as e:
                logger.warning(f"[对话模式 {self.session_id}] 更新人物设定System Prompt失败: {e}")
        
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤3）")
            prompt = self._prompt_generator.generate_step3_characters_prompt(protagonist_name)
        else:
            prompt = None
        
        # 如果模板生成失败，使用传统Prompt
        if not prompt:
            logger.warning(f"[对话模式 {self.session_id}] 模板生成失败，使用传统Prompt")
            prompt_parts = [
                "请执行【步骤3：生成角色设计】\n",
                "基于已确定的世界观，设计完整的角色阵容。\n",
                "## ⚠️ 强制要求",
                f'- **主角姓名**：**必须使用** "{protagonist_name}"',
                f'- **禁止**：给主角起其他名字或别名',
                "- 如果违反，生成将被视为失败\n",
                "## 输出格式",
                "返回JSON格式：{protagonist: {...}, core_allies: [...], main_antagonists: {...}, supporting_roles: [...]}\n",
                f'** protagonist.name 必须是 "{protagonist_name}" **',
                "只返回JSON，不要其他内容。"
            ]
            prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤3提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_round("generate_characters", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤3响应接收 | 总对话轮次: {self.session.turn_count}")
        
        result = self._parse_json_response(response, "characters")
        
        # 🔥 如果返回空或null，使用简化提示词重试
        if not result:
            logger.warning(f"[对话模式 {self.session_id}] 步骤3返回空，使用简化提示词重试...")
            retry_prompt = f"""请生成角色设计JSON。

必须包含：
1. protagonist: {{"name": "{protagonist_name}", "age": 25, "identity": "前外卖员", "traits": ["杀伐果断", "护短"]}}
2. core_allies: 3-5个队友
3. main_antagonists: {{"early_stage": [...], "mid_stage": [...], "late_stage": [...]}}
4. supporting_roles: 其他配角

 protagonist.name 必须是 "{protagonist_name}"！
只返回JSON，禁止返回null。"""
            
            response = self.session.send_message(retry_prompt, temperature=0.7)
            result = self._parse_json_response(response, "characters_retry")
        
        # 🔥 验证并强制修正主角名
        if result and result.get("protagonist"):
            actual_name = result["protagonist"].get("name", "")
            if actual_name != protagonist_name:
                logger.warning(f"[对话模式 {self.session_id}] AI生成的角色名 '{actual_name}' 与用户指定 '{protagonist_name}' 不符，强制修正！")
                result["protagonist"]["name"] = protagonist_name
        else:
            # 如果仍然失败，返回默认角色设计
            logger.error(f"[对话模式 {self.session_id}] 步骤3重试后仍失败，使用默认角色设计")
            result = self._get_default_characters(protagonist_name)
        
        return result
    
    def _get_default_characters(self, protagonist_name: str) -> Dict:
        """获取默认角色设计（当AI生成失败时使用）"""
        return {
            "protagonist": {
                "name": protagonist_name,
                "age": 25,
                "identity": "前外卖员，国运选手",
                "traits": ["杀伐果断", "极度护短", "低调装逼", "不圣母"],
                "background": "父亲早逝，母亲重病，送外卖三年攒下20万被骗"
            },
            "core_allies": [
                {"name": "白月魁", "role": "女主/战斗搭档", "template": "《灵笼》女主，冷艳刀姬"},
                {"name": "胖子", "role": "捧哏/解说", "template": "主角死党，网吧网管"},
                {"name": "苏明月", "role": "传声筒/美女军官", "template": "龙国特派员，负责联络"}
            ],
            "main_antagonists": {
                "early_stage": [
                    {"name": "麦克", "nationality": "漂亮国", "identity": "基因战士", "hate_points": "歧视龙国"},
                    {"name": "佐佐木", "nationality": "樱花国", "identity": "忍者", "hate_points": "阴险偷袭"}
                ],
                "mid_stage": [
                    {"name": "马克", "nationality": "漂亮国", "identity": "国防部长之子", "hate_points": "动用现实力量暗杀"},
                    {"name": "慕容云海", "nationality": "龙国（叛徒）", "identity": "古武世家", "hate_points": "出卖龙国"}
                ],
                "late_stage": [
                    {"name": "八岐大蛇", "origin": "樱花国神话", "identity": "SS级凶兽", "hate_points": "吞噬人类"},
                    {"name": "观察者", "origin": "高维文明", "identity": "禁地创造者", "hate_points": "视人类为实验品"}
                ]
            },
            "supporting_roles": [
                {"name": "张婷", "role": "势利眼前女友", "function": "让读者恨，然后爽"},
                {"name": "母亲", "role": "主角软肋", "function": "情感支柱"}
            ]
        }
    
    def _generate_growth_plan(self) -> Dict:
        """生成成长路线（使用基于爆款的Prompt模板）"""
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤4）")
            prompt = self._prompt_generator.generate_step4_growth_prompt()
        else:
            # 传统Prompt
            prompt = """请执行【步骤4：生成成长路线】

基于前30章大纲和主角人设，规划详细的成长里程碑。

## 输出格式
返回JSON格式，包含: protagonist_growth, ability_system_progression, key_relationships_development

只返回JSON。"""
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤4提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_round("generate_growth_plan", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤4响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "growth_plan")
    
    def _generate_emotion_curve(self) -> List[Dict]:
        """生成情绪曲线（使用基于爆款的Prompt模板）"""
        total_chapters = self.user_choices.get('chapters', 100)
        
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤5）")
            prompt = self._prompt_generator.generate_step5_emotion_prompt(total_chapters)
        else:
            # 传统Prompt
            prompt_parts = [
                "请执行【步骤5：生成情绪曲线】\n",
                f"基于系统提示词中的【完整的套路分析结果】和前30章大纲，设计{total_chapters}章的情绪曲线。\n",
                "## 节奏要求（必须严格遵循）",
                "- 每3章一个小高潮（强度7-8）",
                "- 每10章一个中高潮（强度8-9）",
                "- 每30章一个大高潮（强度9-10）",
                "- 大高潮后必须有1-2章缓冲（强度5-6）\n",
                "## 情绪类型",
                "震惊、期待、小爽快、大爽快、紧张、愤怒、满足\n",
                "## 输出格式",
                "返回JSON格式，包含curve数组，每个元素有: ch, emotion, intensity, beat_type, event, purpose"
            ]
            prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤5提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_round("generate_emotion_curve", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤5响应接收 | 总对话轮次: {self.session.turn_count}")
        result = self._parse_json_response(response, "emotion_curve")
        return result.get("curve", [])
    
    def _extract_faction_system(self, worldview: Dict) -> Dict:
        """从世界观提取势力系统"""
        return {
            "factions": worldview.get("factions", []),
            "faction_relationships": worldview.get("faction_relationships", {}),
            "power_dynamics": worldview.get("power_dynamics", {})
        }
    
    def _generate_writing_style_guide(self) -> Dict:
        """生成写作风格指南（基于套路模板）"""
        return self.tropes.get("platform_tips", {})
    
    def _generate_market_analysis(self) -> Dict:
        """生成市场分析（基于套路）"""
        return {
            "target_platform": "番茄小说",
            "genre_positioning": self.genre,
            "core_selling_points": self.tropes.get("success_factors", []),
            "target_audience": self.tropes.get("protagonist", {}).get("background", ""),
            "competitive_advantages": self.tropes.get("platform_tips", {}).get("writing_style", ""),
            "confidence_score": 8
        }
    
    def _generate_emotional_blueprint(self) -> Dict:
        """生成情绪蓝图（简化版）"""
        return {
            "emotional_spectrum": ["期待", "紧张", "愤怒", "爽快", "满足"],
            "stage_emotional_arcs": {
                "opening_stage": {"dominant_emotion": "期待", "intensity": 8},
                "development_stage": {"dominant_emotion": "爽快", "intensity": 8},
                "climax_stage": {"dominant_emotion": "爆发", "intensity": 9},
                "ending_stage": {"dominant_emotion": "满足", "intensity": 7}
            },
            "climax_moments": ["第3章", "第10章", "第20章", "第30章"]
        }
    
    def _parse_json_response(self, response: str, step_name: str) -> Any:
        """解析JSON响应"""
        if not response:
            logger.error(f"步骤 {step_name} 返回空")
            return {}
        
        try:
            # 尝试直接解析
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取JSON块
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except:
                    pass
            
            # 尝试提取花括号内容
            brace_match = re.search(r'\{.*\}', response, re.DOTALL)
            if brace_match:
                try:
                    return json.loads(brace_match.group(0))
                except:
                    pass
        
        logger.error(f"无法解析步骤 {step_name} 的响应")
        return {}


class MarketDrivenConversationManager:
    """市场导向对话管理器"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.active_sessions: Dict[str, MarketDrivenConversationSession] = {}
    
    def start_conversation(self, genre: str, user_choices: Dict, 
                          tropes: Optional[Dict] = None) -> MarketDrivenConversationSession:
        """开始新的对话会话"""
        session = MarketDrivenConversationSession(
            api_client=self.api_client,
            genre=genre,
            user_choices=user_choices,
            tropes=tropes,
            provider="kimi"
        )
        
        session_id = f"{genre}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.active_sessions[session_id] = session
        
        return session
    
    def get_conversation_stats(self) -> Dict:
        """获取对话统计"""
        return {
            "active_sessions": len(self.active_sessions),
            "mode": "market_driven_conversation"
        }


# 便捷函数
def generate_with_conversation(api_client, genre: str, user_choices: Dict, 
                               tropes: Optional[Dict] = None,
                               progress_callback=None) -> Dict:
    """
    使用对话模式生成市场导向产物
    
    Args:
        api_client: APIClient实例
        genre: 题材
        user_choices: 用户选择
        tropes: 套路分析结果（可选）
        progress_callback: 进度回调
    
    Returns:
        所有产物字典
    """
    manager = MarketDrivenConversationManager(api_client)
    session = manager.start_conversation(genre, user_choices, tropes)
    return session.generate_all(progress_callback)
