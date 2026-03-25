"""
市场导向对话生成器
在一个连续对话中完成套路分析 → 方案生成 → 一阶段产物生成
利用Kimi的256K上下文窗口和缓存机制
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ConversationLogger:
    """对话生成日志记录器 - 保存为易读的Markdown格式"""
    
    def __init__(self, session_id: str, log_dir: str = "logs/ai_interactions"):
        self.session_id = session_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.messages = []  # 记录所有消息（包括累积历史）
        self.start_time = datetime.now()
        self.current_history = []  # 当前累积的对话历史
        
    def log_message(self, role: str, content: str, step: str = "", history: List[Dict] = None):
        """记录一条消息，同时保存当前累积的历史"""
        self.messages.append({
            "timestamp": datetime.now(),
            "role": role,
            "step": step,
            "content": content,
            "content_length": len(content),
            "history_snapshot": history.copy() if history else []  # 保存历史快照
        })
        
    def update_history(self, role: str, content: str):
        """更新累积的对话历史"""
        self.current_history.append({"role": role, "content": content})
    
    def save(self, final_result: Dict = None):
        """保存为Markdown格式 - 显示完整的累积对话历史"""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"conversation_{self.session_id}_{timestamp}.md"
        
        # 构建Markdown内容
        lines = []
        
        # 标题
        lines.append(f"# 🤖 AI对话记录 - {self.session_id}")
        lines.append("")
        lines.append(f"**开始时间**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**结束时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**总轮次**: {len([m for m in self.messages if m['role'] == 'user'])}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 系统提示词（折叠）
        system_prompt = ""
        for msg in self.messages:
            if msg["role"] == "system_prompt":
                system_prompt = msg["content"]
                break
        
        if system_prompt:
            lines.append("## 📋 系统提示词（System）")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>点击展开查看完整的系统提示词</summary>")
            lines.append("")
            lines.append("```")
            lines.append(system_prompt[:2000] + "..." if len(system_prompt) > 2000 else system_prompt)
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")
            lines.append("---")
            lines.append("")
        
        # 🔥 按轮次组织，每轮显示完整的历史累积
        lines.append("## 💬 完整对话历史（按轮次展开）")
        lines.append("")
        lines.append("每轮对话包含之前所有轮次的累积历史 + 当前轮次的新消息")
        lines.append("")
        
        # 按轮次分组
        rounds = []
        current_round = {"step": "", "user": None, "assistant": None, "history": []}
        
        for msg in self.messages:
            if msg["role"] == "system_prompt":
                continue
            elif msg["role"] == "system":
                continue
            elif msg["role"] == "user":
                if current_round["user"] is not None:
                    # 保存上一round
                    rounds.append(current_round)
                    current_round = {"step": msg["step"], "user": msg, "assistant": None, 
                                   "history": msg.get("history_snapshot", [])}
                else:
                    current_round["step"] = msg["step"]
                    current_round["user"] = msg
                    current_round["history"] = msg.get("history_snapshot", [])
            elif msg["role"] == "assistant":
                current_round["assistant"] = msg
        
        # 添加最后一轮
        if current_round["user"] is not None:
            rounds.append(current_round)
        
        # 渲染每轮
        step_names = {
            "generate_plan": "步骤1：生成完整方案",
            "generate_worldview": "步骤2：生成世界观",
            "generate_characters": "步骤3：生成角色设计",
            "generate_growth_plan": "步骤4：生成成长路线",
            "generate_emotion_curve": "步骤5：生成情绪曲线"
        }
        
        for i, round_data in enumerate(rounds, 1):
            step = round_data["step"]
            user_msg = round_data["user"]
            assistant_msg = round_data["assistant"]
            history = round_data["history"]
            
            step_name = step_names.get(step, f"轮次{i}")
            
            lines.append(f"### {step_name}")
            lines.append("")
            lines.append(f"**发送时间**: {user_msg['timestamp'].strftime('%H:%M:%S')}")
            lines.append(f"**历史消息数**: {len(history)} 条（System + {len(history)-1} 轮对话）")
            lines.append("")
            
            # 🔥 显示当前轮次的历史快照（累积的对话）
            lines.append("<details>")
            lines.append(f"<summary>📜 点击查看第{i}轮时的完整历史（{len(history)}条消息）</summary>")
            lines.append("")
            
            for idx, hist_msg in enumerate(history):
                role_emoji = {"system": "📋", "user": "👤", "assistant": "🤖"}.get(hist_msg["role"], "📝")
                lines.append(f"{role_emoji} **{hist_msg['role'].upper()}** (历史#{idx})")
                lines.append("")
                content = hist_msg.get("content", "")
                if len(content) > 200:
                    lines.append("```")
                    lines.append(content[:200] + f"... [{len(content)-200}字符省略]")
                    lines.append("```")
                else:
                    lines.append("```")
                    lines.append(content)
                    lines.append("```")
                lines.append("")
            
            lines.append("</details>")
            lines.append("")
            
            # 显示当前轮次的新消息
            if assistant_msg:
                lines.append(f"**🤖 AI响应** ({assistant_msg['timestamp'].strftime('%H:%M:%S')})")
                lines.append("")
                content = assistant_msg["content"]
                try:
                    if content.strip().startswith('{'):
                        json_obj = json.loads(content)
                        lines.append("```json")
                        lines.append(json.dumps(json_obj, ensure_ascii=False, indent=2))
                        lines.append("```")
                    else:
                        lines.append("```")
                        lines.append(content)
                        lines.append("```")
                except:
                    lines.append("```")
                    lines.append(content)
                    lines.append("```")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        # 最终结果
        if final_result:
            lines.append("## ✅ 最终结果汇总")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(final_result, ensure_ascii=False, indent=2)[:3000])
            lines.append("```")
            lines.append("")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            logger.info(f"[对话日志] 已保存: {log_file}")
            return str(log_file)
        except Exception as e:
            logger.error(f"[对话日志] 保存失败: {e}")
            return ""


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
        
        # 创建对话会话
        from src.core.APIClient import ConversationSession
        system_prompt = self._build_system_prompt()
        
        # 🔥 创建对话日志记录器（记录完整的系统提示词和所有对话）
        self._logger = ConversationLogger(self.session_id)
        self._logger.log_message("system", f"题材: {genre}, 标题: {user_choices.get('title', 'Unknown')}", "session_init")
        self._logger.log_message("system_prompt", system_prompt, "system_prompt")  # 记录完整系统提示词
        
        self.session = ConversationSession(
            api_client=api_client,
            system_prompt=system_prompt,
            provider=provider,
            purpose_prefix=f"MDC-{self.session_id}"  # 用于日志标识
        )
        # 设置历史限制（直接修改属性）
        self.session.max_history = 20
        
        logger.info(f"[对话模式 {self.session_id}] 会话创建 | 题材: {genre} | 标题: {user_choices.get('title', 'Unknown')}")
    
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
        """构建系统提示词 - 只包含用户选择的内容，移除干扰选项"""
        # 用户选择的信息（必须明确标注）
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        golden_finger = self.user_choices.get('golden_finger_desc', '金手指')
        main_plot = self.user_choices.get('main_plot', '主线剧情')
        
        # 获取剧情路线
        selected_plot = self.user_choices.get('selected_plot', {})
        plot_name = selected_plot.get('name', '默认路线') if selected_plot else '默认路线'
        plot_detail = selected_plot.get('detail', '') if selected_plot else ''
        
        # 🔥 清理套路分析结果，只保留必要信息，移除干扰选项
        filtered_tropes = self._filter_tropes_for_prompt()
        tropes_json = json.dumps(filtered_tropes, ensure_ascii=False, indent=2)
        
        return f"""# 角色：顶级网文策划专家

你正在为一部网络小说进行【市场导向创作】。这是一个基于爆款套路的连续创作过程，你将通过多轮对话逐步完成所有设定。

---

## 🎯 【用户最终选择 - 必须严格遵循】

### ✅ 最终确定的书名（必须使用）
**{title}**

### ✅ 最终确定的主角姓名（必须使用）
**{protagonist_name}**

### ✅ 最终确定的金手指（必须使用）
**{golden_finger}**

### ✅ 最终选择的剧情路线名称
**{plot_name}**

### ✅ 最终选择的剧情路线详情（必须遵循此节奏）
```
{plot_detail}
```

### ✅ 最终确定的主线剧情
```
{main_plot}
```

---

## 📊 【套路分析结果 - 参考依据】

以下是对该题材Top10爆款的分析结果（已过滤，只保留与用户选择相关的信息）。请基于此进行创作，但**必须服从上面的【用户最终选择】**。

```json
{tropes_json}
```

---

## ⚠️ 重要规则

1. **用户选择优先**：上面的【用户最终选择】是用户已经确定的，必须严格遵循，不能改动
2. **套路作为参考**：下面的【套路分析结果】是参考依据，用于指导创作方向
3. **剧情路线必须遵循**：用户选择的剧情路线详情中的节奏（第1/3/10/20/30章节点）必须严格执行
4. **标题必须使用**：用户确定的书名必须直接使用，不要修改
5. **主角名必须使用**：用户确定的主角姓名必须直接使用

## 你的工作流程
你将按照以下顺序完成创作，每轮对话我会指示你进行下一步：

1. **生成完整方案** - 基于用户选择和套路，生成标题确认、开局设计、金手指细化、主角人设、前30章大纲
2. **生成世界观** - 基于题材套路，创建世界观框架和势力系统
3. **生成角色设计** - 基于主角人设和剧情路线，设计完整的角色阵容
4. **生成成长路线** - 基于前30章大纲，规划主角成长里程碑
5. **生成情绪曲线** - 基于剧情节奏，设计每章的情绪节拍

## 核心规则
1. **严格遵循套路** - 所有设计必须符合提供的爆款公式
2. **保持一致性** - 后续步骤必须参考前面步骤的设定
3. **具体可执行** - 所有设计必须是可落地的，不能泛泛而谈
4. **番茄风格** - 快节奏、强爽点、章章有钩子

## 输出规范
- 所有输出必须是合法的 JSON 格式
- 使用中文，符合中国网文市场特点
- 保持前后一致，后续步骤要参考前面的设定
- 每轮只输出当前步骤的内容

## 当前状态
等待第 1 步指令：生成完整方案...
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
        
        # 🔥 保存完整对话日志
        self._logger.save(results)
        
        return results
    
    def _generate_plan(self) -> Dict:
        """生成完整方案"""
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        
        # 使用字符串拼接而不是f-string，避免嵌套问题
        prompt_parts = [
            "请执行【步骤1：生成完整方案】\n",
            "基于系统提示词中的【用户最终选择】和【完整的套路分析结果】，生成完整的小说方案。\n",
            "## 重要提醒",
            f'1. **书名**：必须使用用户确定的「{title}」',
            f'2. **主角名**：必须使用用户确定的「{protagonist_name}」',
            "3. **剧情路线**：必须遵循用户选择的剧情路线详情中的节奏（第1/3/10/20/30章节点）",
            "4. **参考套路**：参考系统提示词中的完整套路分析结果\n",
            "## 你需要生成",
            "1. **标题确认** - 确认使用用户确定的标题（≤15字）",
            "2. **开局设计** - 第1-3章详细剧本，具体到场景和对话",
            "3. **金手指细化** - 基于用户描述，细化具体数值和成长曲线",
            "4. **主角人设** - 生成完整人设",
            '5. **前30章大纲** - 严格遵循"3-10-20-30"节奏\n',
            "## 输出格式",
            "返回JSON格式，包含: title, opening_design, golden_finger, protagonist, outline_first_30\n",
            "只返回JSON，不要其他说明。"
        ]
        prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤1提示词 | 当前消息历史: {len(self.session.messages)}条")
        self._logger.log_message("user", prompt, "generate_plan", self.session.messages)
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_message("assistant", response if isinstance(response, str) else json.dumps(response), "generate_plan", self.session.messages)
        logger.info(f"[对话模式 {self.session_id}] 步骤1响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "plan")
    
    def _generate_worldview(self) -> Dict:
        """生成世界观"""
        prompt = """请执行【步骤2：生成世界观】

基于系统提示词中的【完整的套路分析结果】和已确定的题材、主角设定，生成完整的世界观。

## 关键参考（在系统提示词中）
- must_have: 必须包含的元素
- must_not_have: 绝对不能有的元素
- faction_system: 势力系统参考
- world_rules: 世界规则

## 关键要求
1. 世界观必须支持主角的金手指和成长路线
2. 势力系统必须提供足够的冲突来源
3. 社会规则必须有利于"装逼打脸"情节

## 输出格式
返回JSON格式，包含: world_overview, power_system, social_structure, factions, world_rules, key_locations

只返回JSON。"""
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤2提示词 | 当前消息历史: {len(self.session.messages)}条")
        self._logger.log_message("user", prompt, "generate_worldview", self.session.messages)
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_message("assistant", response if isinstance(response, str) else json.dumps(response), "generate_worldview", self.session.messages)
        logger.info(f"[对话模式 {self.session_id}] 步骤2响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "worldview")
    
    def _generate_characters(self) -> Dict:
        """生成角色设计"""
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        
        prompt_parts = [
            "请执行【步骤3：生成角色设计】\n",
            "基于系统提示词中的【完整的套路分析结果】和已确定的主角人设、世界观，设计完整的角色阵容。\n",
            "## 重要提醒",
            f'- **主角姓名**：必须使用用户确定的「{protagonist_name}」',
            "- **参考模板**：系统提示词中的 protagonist（主角模板）和 antagonist（反派设计套路）\n",
            "## 输出格式",
            "返回JSON格式，包含: protagonist, core_allies, main_antagonists, supporting_roles\n",
            "只返回JSON。"
        ]
        prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤3提示词 | 当前消息历史: {len(self.session.messages)}条")
        self._logger.log_message("user", prompt, "generate_characters", self.session.messages)
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_message("assistant", response if isinstance(response, str) else json.dumps(response), "generate_characters", self.session.messages)
        logger.info(f"[对话模式 {self.session_id}] 步骤3响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "characters")
    
    def _generate_growth_plan(self) -> Dict:
        """生成成长路线"""
        prompt = """请执行【步骤4：生成成长路线】

基于前30章大纲和主角人设，规划详细的成长里程碑。

## 输出格式
返回JSON格式，包含: protagonist_growth, ability_system_progression, key_relationships_development

只返回JSON。"""
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤4提示词 | 当前消息历史: {len(self.session.messages)}条")
        self._logger.log_message("user", prompt, "generate_growth_plan", self.session.messages)
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_message("assistant", response if isinstance(response, str) else json.dumps(response), "generate_growth_plan", self.session.messages)
        logger.info(f"[对话模式 {self.session_id}] 步骤4响应接收 | 总对话轮次: {self.session.turn_count}")
        return self._parse_json_response(response, "growth_plan")
    
    def _generate_emotion_curve(self) -> List[Dict]:
        """生成情绪曲线"""
        total_chapters = self.user_choices.get('chapters', 100)
        
        prompt_parts = [
            "请执行【步骤5：生成情绪曲线】\n",
            f"基于系统提示词中的【完整的套路分析结果】和前30章大纲，设计{total_chapters}章的情绪曲线。\n",
            "## 关键参考（在系统提示词中）",
            "- emotion_curve: 情绪曲线模式",
            "- first_climax_design: 第一个大高潮设计（关键节点）",
            "- pacing: 节奏控制\n",
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
        self._logger.log_message("user", prompt, "generate_emotion_curve", self.session.messages)
        response = self.session.send_message(prompt, temperature=0.7)
        self._logger.log_message("assistant", response if isinstance(response, str) else json.dumps(response), "generate_emotion_curve", self.session.messages)
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
