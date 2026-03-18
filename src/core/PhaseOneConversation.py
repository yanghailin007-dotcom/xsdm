"""
一阶段多轮对话会话管理
仅在 Kimi 端点启用，利用 256K 上下文窗口和缓存机制实现 Token 节省
"""

import json
from typing import Dict, Optional, Any, List
from src.core.APIClient import ConversationSession
from src.utils.logger import get_logger


class PhaseOneConversationSession(ConversationSession):
    """
    一阶段专用多轮对话会话
    
    将一阶段所有步骤整合为单个连续对话，利用 Kimi 的:
    - 256K 上下文窗口
    - 上下文缓存机制（缓存命中仅 ¥0.7/1M tokens）
    - 中文长文本理解能力
    
    预计节省 60-70% Token 成本
    """
    
    # 一阶段各步骤的定义
    STEPS = [
        "foundation_planning",      # 基础规划（写作风格+市场分析）
        "worldview_factions",       # 世界观+势力系统
        "character_design",         # 核心角色设计
        "emotional_growth",         # 情绪蓝图+成长规划
        "stage_overview",           # 全书阶段划分
        "stage_details",            # 各阶段详细计划
        "supplementary_chars",      # 补充角色
    ]
    
    def __init__(self, api_client, novel_data: Dict, provider: str = "kimi", model_name: str = None):
        """
        初始化一阶段对话会话
        
        Args:
            api_client: APIClient 实例
            novel_data: 小说基础数据（标题、简介、创意种子等）
            provider: 必须为 "kimi" 才启用此模式
            model_name: 模型名称（如 kimi-k2.5）
        """
        if provider != "kimi":
            raise ValueError(f"PhaseOneConversationSession 仅支持 kimi provider, 当前: {provider}")
        
        self.logger = get_logger("PhaseOneConversation")
        self.novel_data = novel_data
        self.current_step_index = 0
        self.results = {}
        
        # 构建系统提示词（一次性发送，后续缓存命中）
        system_prompt = self._build_system_prompt()
        
        # kimi k2.5 requires temperature=1.0
        self.requires_temp_one = model_name and "k2.5" in model_name
        
        super().__init__(api_client, system_prompt, provider=provider, model_name=model_name)
        self.logger.info(f"[PhaseOne] Session started | Novel: {novel_data.get('novel_title', 'Unknown')} | Model: {model_name}")
    
    def _build_system_prompt(self) -> str:
        """构建一阶段系统提示词"""
        title = self.novel_data.get("novel_title", "")
        synopsis = self.novel_data.get("novel_synopsis", "")
        category = self.novel_data.get("category", "未分类")
        
        # 获取创意种子信息
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        core_direction = creative_seed.get("core_direction", "") if isinstance(creative_seed, dict) else ""
        
        return f"""# 角色：顶级网文策划专家

你正在为一部网络小说进行【第一阶段设定生成】。这是一个连续的多步骤创作过程，你将通过多轮对话逐步完成所有设定。

## 小说基础信息
- **书名**: {title}
- **类型**: {category}
- **简介**: {synopsis}
- **核心方向**: {core_direction}

## 你的工作流程
你将按照以下顺序完成设定，每轮对话我会指示你进行下一步：

1. **基础规划** - 写作风格指南 + 市场分析
2. **世界观与势力** - 世界观框架 + 势力/阵营系统
3. **核心角色设计** - 主角、盟友、反派等核心角色
4. **情绪与成长规划** - 情绪蓝图 + 角色成长路线
5. **全书阶段划分** - 整体章节阶段规划
6. **阶段详细计划** - 每个阶段的具体写作计划
7. **补充角色** - 基于全书规划的额外角色

## 输出规范
- 所有输出必须是合法的 JSON 格式
- 使用中文，符合中国网文市场特点
- 保持前后一致，后续步骤要参考前面的设定
- 每轮只输出当前步骤的内容，不要重复输出之前的内容

## 当前状态
等待第 1 步指令...
"""
    
    def execute_step(self, step_name: str, **context) -> Optional[Dict]:
        """
        执行指定步骤
        
        Args:
            step_name: 步骤名称，必须在 STEPS 中
            **context: 额外上下文数据
            
        Returns:
            该步骤的生成结果
        """
        if step_name not in self.STEPS:
            self.logger.error(f"❌ 未知步骤: {step_name}")
            return None
        
        self.logger.info(f"📝 执行步骤 [{self.current_step_index + 1}/{len(self.STEPS)}]: {step_name}")
        
        # 构建用户提示词
        prompt = self._build_step_prompt(step_name, **context)
        
        # 发送消息并获取结果
        # Note: kimi-k2.5 requires temperature=1.0
        temp = 1.0 if self.requires_temp_one else 0.7
        response = self.send_message(prompt, temperature=temp)
        
        if not response:
            self.logger.error(f"❌ 步骤 {step_name} 生成失败")
            return None
        
        # 解析结果
        try:
            result = self._parse_response(response, step_name)
            self.results[step_name] = result
            self.current_step_index += 1
            self.logger.info(f"✅ 步骤 {step_name} 完成")
            return result
        except Exception as e:
            self.logger.error(f"❌ 解析步骤 {step_name} 结果失败: {e}")
            return None
    
    def _build_step_prompt(self, step_name: str, **context) -> str:
        """构建各步骤的用户提示词"""
        
        prompts = {
            "foundation_planning": self._build_foundation_prompt,
            "worldview_factions": self._build_worldview_prompt,
            "character_design": self._build_character_prompt,
            "emotional_growth": self._build_emotional_prompt,
            "stage_overview": self._build_stage_overview_prompt,
            "stage_details": self._build_stage_details_prompt,
            "supplementary_chars": self._build_supplementary_chars_prompt,
        }
        
        builder = prompts.get(step_name)
        if not builder:
            raise ValueError(f"未找到步骤 {step_name} 的提示词构建器")
        
        return builder(**context)
    
    def _build_foundation_prompt(self, **kwargs) -> str:
        """基础规划提示词"""
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        
        return f"""
请执行【步骤1：基础规划】

基于小说基础信息，同时生成【写作风格指南】和【市场分析】。

## 创意种子
{json.dumps(creative_seed, ensure_ascii=False, indent=2)}

## 输出要求
返回 JSON 格式，必须包含两个顶层字段：
1. "writing_style_guide" - 写作风格指南
2. "market_analysis" - 市场分析

writing_style_guide 字段内容：
- core_style: 核心风格定位（100字以内）
- language_characteristics: 语言特点（列表，3-5个）
- narration_techniques: 叙事技巧（列表，2-3个）
- dialogue_style: 对话风格
- chapter_techniques: 章节技巧（列表）
- key_principles: 核心原则（列表，3-5条）

market_analysis 字段内容：
- target_platform: 目标平台（如：番茄小说）
- genre_positioning: 类型定位
- core_selling_points: 核心卖点（列表，3-5条）
- target_audience: 目标读者画像
- competitive_advantages: 竞争优势（列表）
- market_risks: 市场风险（列表）
- confidence_score: 信心评分（1-10分）

只返回 JSON，不要其他说明文字。
"""
    
    def _build_worldview_prompt(self, **kwargs) -> str:
        """世界观与势力系统提示词"""
        # 获取上一步结果
        foundation = self.results.get("foundation_planning", {})
        writing_style = foundation.get("writing_style_guide", {})
        market = foundation.get("market_analysis", {})
        
        creative_seed = self.novel_data.get("creative_seed") or self.novel_data.get("selected_plan", {})
        core_settings = creative_seed.get("core_settings", {}) if isinstance(creative_seed, dict) else {}
        
        return f"""
请执行【步骤2：世界观与势力系统】

基于已确定的写作风格和市场定位，设计小说的世界观和势力系统。

## 已确定的写作风格
- 核心风格: {writing_style.get('core_style', '待定')}
- 语言特点: {writing_style.get('language_characteristics', [])}

## 市场定位
- 目标平台: {market.get('target_platform', '番茄小说')}
- 类型定位: {market.get('genre_positioning', '待定')}

## 核心设定
- 世界观背景: {core_settings.get('world_background', '待定')}
- 金手指/系统: {core_settings.get('golden_finger', '待定')}
- 核心爽点: {core_settings.get('core_selling_points', [])}

## 输出要求
返回 JSON 格式，必须包含两个顶层字段：
1. "core_worldview" - 世界观框架
2. "faction_system" - 势力系统

core_worldview 字段内容：
- world_overview: 世界概览（200字以内）
- power_system: 力量体系详细说明
- world_rules: 世界规则（列表）
- key_locations: 关键地点（列表，3-5个）
- time_background: 时间背景

faction_system 字段内容：
- factions: 势力列表（3-7个），每个包含 name, description, goals, strengths, weaknesses, relationships
- main_conflict: 主要冲突描述
- faction_power_balance: 势力力量对比
- recommended_starting_faction: 推荐主角初始势力

注意：势力系统必须与世界观设定（尤其是力量体系）保持一致。

只返回 JSON，不要其他说明文字。
"""
    
    def _build_character_prompt(self, **kwargs) -> str:
        """核心角色设计提示词"""
        worldview = self.results.get("worldview_factions", {})
        core_worldview = worldview.get("core_worldview", {})
        faction_system = worldview.get("faction_system", {})
        
        custom_name = kwargs.get("custom_main_character_name", "")
        
        return f"""
请执行【步骤3：核心角色设计】

基于已设计的世界观和势力系统，设计小说的核心角色。

## 已确定的世界观
- 世界概览: {core_worldview.get('world_overview', '待定')}
- 力量体系: {core_worldview.get('power_system', '待定')}

## 已确定的势力系统
- 主要势力: {[f.get('name') for f in faction_system.get('factions', [])]}
- 主要冲突: {faction_system.get('main_conflict', '待定')}

## 设计要求
设计以下核心角色：
1. **主角** - 包含姓名、性格、背景、目标、金手指等
2. **核心盟友** - 1-3位重要盟友
3. **主要反派/宿敌** - 1-2位主要对立角色
4. **导师/引路人** - 1位引导角色

每个角色需包含：
- basic_info: 基本信息（姓名、年龄、身份等）
- personality: 性格特征
- background: 背景故事
- goals: 目标动机
- abilities: 能力/金手指
- relationships: 与其他角色的关系
- growth_arc: 成长弧线

{f'注意：主角姓名请使用 "{custom_name}"' if custom_name else ''}

返回 JSON 格式，顶层字段为 "characters"，内含角色列表。

只返回 JSON，不要其他说明文字。
"""
    
    def _build_emotional_prompt(self, **kwargs) -> str:
        """情绪蓝图与成长规划提示词"""
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        
        return f"""
请执行【步骤4：情绪蓝图与成长规划】

基于前面的所有设定，同时设计【情绪蓝图】和【成长规划】。

## 全书信息
- 总章节数: {total_chapters}

## 已确定的设定（见前文）
- 写作风格
- 世界观与势力
- 核心角色

## 输出要求
返回 JSON 格式，必须包含两个顶层字段：

1. "emotional_blueprint" - 情绪蓝图
   - emotional_curves: 情绪曲线设计（列表，每阶段包含情绪类型、强度、触发点）
   - emotional_hooks: 情绪钩子设计（悬念、冲突、爽点安排）
   - reader_journey: 读者情感旅程映射

2. "global_growth_plan" - 成长规划
   - protagonist_growth: 主角成长阶段划分
   - power_progression: 力量体系进阶路线
   - milestone_events: 关键里程碑事件
   - stage_goals: 各阶段目标

注意：情绪蓝图和成长规划要相互协调，成长节点的情绪要有起伏变化。

只返回 JSON，不要其他说明文字。
"""
    
    def _build_stage_overview_prompt(self, **kwargs) -> str:
        """全书阶段划分提示词"""
        total_chapters = self.novel_data.get("current_progress", {}).get("total_chapters", 200)
        
        emotional_growth = self.results.get("emotional_growth", {})
        growth_plan = emotional_growth.get("global_growth_plan", {})
        
        return f"""
请执行【步骤5：全书阶段划分】

基于成长规划和情绪蓝图，将全书 {total_chapters} 章划分为若干阶段。

## 成长规划要点
- 主角成长阶段: {len(growth_plan.get('protagonist_growth', []))}
- 关键里程碑: {len(growth_plan.get('milestone_events', []))}

## 输出要求
返回 JSON 格式，顶层字段 "overall_stage_plan"，包含：
- stages: 阶段列表，每个阶段包含：
  - stage_number: 阶段序号
  - stage_name: 阶段名称
  - chapter_range: 章节范围（如 "1-30"）
  - chapter_count: 本章节点数
  - core_conflict: 核心冲突
  - emotional_focus: 情绪重点
  - growth_goals: 成长目标
  - key_events: 关键事件列表

建议划分 5-8 个阶段，每阶段 20-50 章。

只返回 JSON，不要其他说明文字。
"""
    
    def _build_stage_details_prompt(self, **kwargs) -> str:
        """阶段详细计划提示词 - 一次性生成所有阶段"""
        stage_overview = self.results.get("stage_overview", {})
        stages = stage_overview.get("stages", [])
        
        stage_count = len(stages)
        
        return f"""
请执行【步骤6：阶段详细写作计划】

为全部 {stage_count} 个阶段生成详细的写作计划。

## 阶段概览
{json.dumps([{"num": s.get("stage_number"), "name": s.get("stage_name"), "chapters": s.get("chapter_range")} for s in stages], ensure_ascii=False, indent=2)}

## 输出要求
返回 JSON 格式，顶层字段 "stage_writing_plans"，为对象格式：
{{
  "阶段1名称": {{
    "opening_hook": "开局钩子设计",
    "chapter_breakdown": [
      {{
        "chapter_num": 1,
        "title": "章节标题",
        "key_events": "关键事件",
        "emotional_beats": "情绪节奏",
        "plot_progression": "剧情推进点",
        "suspense_setup": "悬念设置"
      }}
    ],
    "cliffhanger": "阶段结尾悬念",
    "transition_to_next": "与下阶段衔接"
  }},
  "阶段2名称": {{...}}
}}

为每个阶段提供：
- 开局钩子设计
- 每章的标题、关键事件、情绪节奏、剧情推进点
- 阶段结尾悬念
- 与下阶段的衔接

只返回 JSON，不要其他说明文字。
"""
    
    def _build_supplementary_chars_prompt(self, **kwargs) -> str:
        """补充角色提示词"""
        stage_plans = self.results.get("stage_details", {})
        
        return f"""
请执行【步骤7：全书补充角色生成】

基于全书阶段计划，生成各阶段需要的补充角色。

## 全书阶段计划
已为 {len(stage_plans.get('stage_writing_plans', {}))} 个阶段制定详细计划。

## 输出要求
返回 JSON 格式，顶层字段 "supplementary_characters"，为列表格式：
[
  {{
    "character_name": "角色名",
    "character_type": "角色类型（盟友/反派/中立/NPC）",
    "importance": "重要程度（主要/次要/龙套）",
    "introduce_stage": "登场阶段",
    "introduce_chapter": "登场章节",
    "role_in_story": "在故事中的作用",
    "relationship_to_protagonist": "与主角关系",
    "key_traits": "关键特征",
    "plot_function": "剧情功能说明"
  }}
]

要求：
- 覆盖所有主要阶段的关键角色
- 与已有核心角色形成互补
- 每个角色有明确的剧情功能
- 预计生成 15-30 个补充角色

只返回 JSON，不要其他说明文字。
"""
    
    def _parse_response(self, response: str, step_name: str) -> Dict:
        """解析 API 响应 - 增强容错版本"""
        import re
        
        # 首先清理响应文本
        cleaned = response.strip()
        
        # 移除可能的 BOM 字符
        cleaned = cleaned.lstrip('\ufeff')
        
        try:
            # 尝试 1: 直接解析
            return json.loads(cleaned)
        except json.JSONDecodeError as e1:
            self.logger.warning(f"[{step_name}] 直接解析失败: {e1}")
            
            try:
                # 尝试 2: 从代码块中提取
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', cleaned, re.DOTALL)
                if json_match:
                    code_content = json_match.group(1).strip()
                    return json.loads(code_content)
            except json.JSONDecodeError as e2:
                self.logger.warning(f"[{step_name}] 代码块提取失败: {e2}")
            
            try:
                # 尝试 3: 查找最外层 JSON 对象（使用平衡括号）
                # 找到第一个 { 和最后一个匹配的 }
                start = cleaned.find('{')
                if start != -1:
                    brace_count = 0
                    end = start
                    for i, char in enumerate(cleaned[start:]):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end = start + i + 1
                                break
                    json_str = cleaned[start:end]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError) as e3:
                self.logger.warning(f"[{step_name}] 括号匹配提取失败: {e3}")
            
            try:
                # 尝试 4: 使用更宽松的匹配
                # 尝试修复常见的 JSON 错误
                json_match = re.search(r'\{[\s\S]*\}', cleaned)
                if json_match:
                    json_str = json_match.group(0)
                    # 尝试修复尾部逗号
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    return json.loads(json_str)
            except json.JSONDecodeError as e4:
                self.logger.warning(f"[{step_name}] 宽松匹配失败: {e4}")
            
            # 所有尝试都失败，记录详细错误并保存响应
            error_msg = f"[{step_name}] 无法解析 JSON，所有方法都失败"
            self.logger.error(error_msg)
            self.logger.error(f"[{step_name}] 响应前500字符: {cleaned[:500]}")
            
            # 保存失败响应用于调试
            try:
                from pathlib import Path
                debug_dir = Path("debug_responses")
                debug_dir.mkdir(exist_ok=True)
                timestamp = int(time.time())
                debug_file = debug_dir / f"parse_error_{step_name}_{timestamp}.txt"
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(f"步骤: {step_name}\n")
                    f.write(f"错误: {e1}\n\n")
                    f.write("="*60 + "\n")
                    f.write("原始响应:\n")
                    f.write(cleaned)
                self.logger.info(f"[{step_name}] 错误响应已保存到: {debug_file}")
            except Exception as save_err:
                self.logger.error(f"[{step_name}] 保存错误响应失败: {save_err}")
            
            raise ValueError(f"无法从响应中解析 JSON: {cleaned[:200]}...")
    
    def export_all_results(self) -> Dict:
        """
        导出所有步骤的结果为统一格式，兼容现有 novel_data 结构
        """
        foundation = self.results.get("foundation_planning", {})
        worldview = self.results.get("worldview_factions", {})
        characters = self.results.get("character_design", {})
        emotional_growth = self.results.get("emotional_growth", {})
        stage_overview = self.results.get("stage_overview", {})
        stage_details = self.results.get("stage_details", {})
        supplementary = self.results.get("supplementary_chars", {})
        
        return {
            # 基础规划
            "writing_style_guide": foundation.get("writing_style_guide", {}),
            "market_analysis": foundation.get("market_analysis", {}),
            
            # 世界观与势力
            "core_worldview": worldview.get("core_worldview", {}),
            "faction_system": worldview.get("faction_system", {}),
            
            # 角色设计
            "character_design": characters.get("characters", {}),
            
            # 情绪与成长
            "emotional_blueprint": emotional_growth.get("emotional_blueprint", {}),
            "global_growth_plan": emotional_growth.get("global_growth_plan", {}),
            
            # 阶段规划
            "overall_stage_plans": stage_overview,
            "stage_writing_plans": stage_details.get("stage_writing_plans", {}),
            
            # 补充角色
            "supplementary_characters": supplementary.get("supplementary_characters", []),
            
            # 元数据
            "generation_method": "conversation_session",
            "total_turns": self.turn_count,
        }


class PhaseOneConversationManager:
    """
    一阶段对话管理器
    负责判断是否启用多轮对话模式，并协调执行
    """
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.logger = get_logger("PhaseOneConversationManager")
        self.session: Optional[PhaseOneConversationSession] = None
    
    def should_use_conversation_mode(self) -> bool:
        """
        判断是否应使用多轮对话模式
        条件：
        1. 当前 provider 为 kimi
        2. 配置中启用了 conversation_mode
        """
        # 检查 provider
        provider = getattr(self.generator, 'api_client', None)
        if provider:
            actual_provider = provider.default_provider if hasattr(provider, 'default_provider') else None
            if actual_provider != "kimi":
                return False
        
        # 检查配置
        config = getattr(self.generator, 'config', {})
        if isinstance(config, dict):
            use_conversation = config.get('use_conversation_mode_for_kimi', True)
            return use_conversation
        
        return True  # 默认启用
    
    def start_conversation(self) -> Optional[PhaseOneConversationSession]:
        """启动一阶段对话会话"""
        if not self.should_use_conversation_mode():
            self.logger.info("[PhaseOne] Conversation mode not enabled")
            return None
        
        try:
            # Get model name from config
            model_name = None
            config = getattr(self.generator, 'config', {})
            if isinstance(config, dict):
                model_name = config.get('models', {}).get('kimi')
            
            # 如果没有获取到 model_name，尝试从全局 CONFIG 获取
            if not model_name:
                from config.config import CONFIG
                model_name = CONFIG.get('models', {}).get('kimi')
            
            self.session = PhaseOneConversationSession(
                api_client=self.generator.api_client,
                novel_data=self.generator.novel_data,
                provider="kimi",
                model_name=model_name
            )
            # 检查端点配置的默认模型
            endpoint_model = None
            try:
                pool = self.generator.api_client.endpoint_pools.get('kimi')
                if pool:
                    available = pool.get_available_endpoints()
                    if available:
                        endpoint_model = available[0].get_config().get('model')
            except:
                pass
            
            actual_model = model_name or endpoint_model or 'default'
            self.logger.info(f"[PhaseOne] Session started | Config model: {model_name or 'None'} | Endpoint model: {endpoint_model or 'None'} | Using: {actual_model}")
            return self.session
        except Exception as e:
            self.logger.error(f"[PhaseOne] Failed to start session: {e}")
            return None
    
    def execute_all_steps(self, progress_callback=None) -> bool:
        """
        执行所有一阶段步骤
        
        Args:
            progress_callback: 进度回调函数 (step_name, progress, message)
            
        Returns:
            是否全部成功
        """
        if not self.session:
            self.logger.error("❌ 对话会话未启动")
            return False
        
        steps = PhaseOneConversationSession.STEPS
        total_steps = len(steps)
        
        for i, step in enumerate(steps):
            progress = int((i / total_steps) * 100)
            if progress_callback:
                progress_callback(step, progress, f"正在执行: {step}")
            
            # 准备额外上下文
            context = {}
            if step == "character_design":
                context["custom_main_character_name"] = getattr(self.generator, 'custom_main_character_name', None)
            
            result = self.session.execute_step(step, **context)
            
            if not result:
                self.logger.error(f"❌ 步骤 {step} 失败，终止生成")
                return False
            
            if progress_callback:
                progress_callback(step, int(((i + 1) / total_steps) * 100), f"{step} 完成")
        
        # 导出结果到 novel_data
        all_results = self.session.export_all_results()
        self.generator.novel_data.update(all_results)
        
        self.logger.info(f"✅ 一阶段全部 {total_steps} 个步骤完成")
        return True
    
    def get_conversation_stats(self) -> Dict:
        """获取对话统计信息"""
        if not self.session:
            return {"mode": "standard", "turns": 0}
        
        return {
            "mode": "conversation_session",
            "turns": self.session.turn_count,
            "steps_completed": self.session.current_step_index,
            "total_steps": len(PhaseOneConversationSession.STEPS),
            "estimated_tokens_saved": f"~{self.session.turn_count * 2000}"  # 估算
        }
