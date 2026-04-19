"""
自由创意：创意到方案对话会话
================================
4步全自动流程：
1. 商业化分析与创意扩展（同人文检测+背景补充）
2. 多方案生成与评分（2-3个方案+AI评分）
3. 智能选优+爆款对标（自动选择+对比优化）
4. 最终方案深化（输出完整final_plan）

特点：
- 单一会话复用，4轮对话完成
- 全自动决策，无需前端选择
- 与市场导向模式UI步骤对齐
"""

import json
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# 导入对话基类
try:
    from src.core.APIClient import ConversationSession
    CONVERSATION_AVAILABLE = True
except ImportError:
    CONVERSATION_AVAILABLE = False
    logger.warning("ConversationSession 不可用，将使用降级模式")


@dataclass
class CreativeStep:
    """创意流程步骤定义"""
    step_id: str
    name: str
    progress: int
    ui_stage: str  # 前端UI对应阶段
    description: str


# 4步流程定义
CREATIVE_STEPS = [
    CreativeStep(
        step_id="commercial_analysis",
        name="商业化分析",
        progress=20,
        ui_stage="analysis",
        description="番茄平台适配分析、同人文检测与背景补充、核心卖点提炼"
    ),
    CreativeStep(
        step_id="multi_plan_generation",
        name="多方案生成",
        progress=40,
        ui_stage="planning",
        description="生成2-3个差异化方案并进行AI评分"
    ),
    CreativeStep(
        step_id="selection_bestseller",
        name="智能选优与爆款对标",
        progress=70,
        ui_stage="optimization",
        description="自动选择最优方案，对比番茄爆款进行优化"
    ),
    CreativeStep(
        step_id="final_plan_deepening",
        name="最终方案深化",
        progress=100,
        ui_stage="finalization",
        description="深化为完整可执行的final_plan"
    ),
]


class CreativeToPlanConversation:
    """
    创意到方案对话会话
    
    使用4轮对话完成从创意到最终方案的全过程
    """
    
    def __init__(
        self,
        api_client,
        novel_data: Dict[str, Any],
        provider: str = "gemini",
        model_name: str = None,
        temperature: float = 0.7
    ):
        """
        初始化创意到方案对话会话
        
        Args:
            api_client: APIClient 实例
            novel_data: 小说基础数据（标题、简介、创意种子等）
            provider: API 提供商
            model_name: 模型名称
            temperature: 温度参数
        """
        self.api_client = api_client
        self.novel_data = novel_data
        self.provider = provider
        self.model_name = model_name
        self.temperature = temperature
        self.session_id = f"CTPC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # 初始化对话会话
        if CONVERSATION_AVAILABLE:
            system_prompt = self._build_system_prompt()
            self.session = ConversationSession(
                api_client=api_client,
                system_prompt=system_prompt,
                provider=provider,
                model_name=model_name
            )
        else:
            self.session = None
            
        # 存储结果
        self.results = {}
        self.current_step = 0
        
        logger.info(f"[{self.session_id}] 创意到方案对话会话初始化完成")
        
    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        title = self.novel_data.get("title", "") or self.novel_data.get("novel_title", "")
        synopsis = self.novel_data.get("synopsis", "") or self.novel_data.get("novel_synopsis", "")
        category = self.novel_data.get("category", "未分类")
        creative_seed = self.novel_data.get("creative_seed", "")
        
        return f"""# 角色：番茄小说商业化策划专家

你是一位深谙番茄小说平台规则和读者喜好的网文策划专家。你的任务是将作者的创意转化为符合市场需求的商业化方案。

## 小说基础信息
- **书名**: {title}
- **类型**: {category}
- **简介**: {synopsis}
- **创意种子**: {creative_seed}

## 你的专业能力
1. **平台洞察**：深入了解番茄小说推荐机制、读者画像、付费点设计
2. **同人文专家**：准确识别同人文类型，自动补充原作世界观、角色关系
3. **爆款分析**：熟悉番茄各类爆款套路，能准确对标分析
4. **方案设计**：能设计差异化方案，避免同质化

## 输出规范
- 所有输出必须是合法的 JSON 格式
- 使用中文，符合中国网文市场特点
- 数据要具体、可执行，避免空泛描述
- 评分要客观，基于市场数据和可行性

## 工作流程
你将通过4轮对话完成任务：
1. 商业化分析（平台适配+同人文检测+卖点提炼）
2. 多方案生成（2-3个方案+AI评分）
3. 智能选优+爆款对标（自动选择+对比优化）
4. 最终方案深化（完整可执行的final_plan）

每轮对话我会给出明确的用户提示词，你只需输出该步骤的结果。"""

    def execute_all_steps(
        self,
        progress_callback: Optional[Callable[[str, int, str, Dict], None]] = None,
        project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        执行所有4个步骤
        
        Args:
            progress_callback: 进度回调函数(step_id, progress, message, ui_state)
            project_path: 项目路径，用于保存中间结果
            
        Returns:
            最终结果字典，包含final_plan
        """
        logger.info(f"[{self.session_id}] 开始执行4步创意到方案流程")
        
        if not self.session:
            raise RuntimeError("ConversationSession 不可用，无法执行对话模式")
        
        try:
            # 步骤1: 商业化分析与创意扩展
            step1_result = self._step1_commercial_analysis(progress_callback)
            self.results["commercial_analysis"] = step1_result
            self._save_step_result("step1_commercial_analysis", step1_result, project_path)
            
            # 步骤2: 多方案生成与评分
            step2_result = self._step2_multi_plan_generation(step1_result, progress_callback)
            self.results["multi_plan"] = step2_result
            self._save_step_result("step2_multi_plan", step2_result, project_path)
            
            # 步骤3: 智能选优+爆款对标
            step3_result = self._step3_selection_bestseller(step2_result, progress_callback)
            self.results["selected_plan"] = step3_result
            self._save_step_result("step3_selected_plan", step3_result, project_path)
            
            # 步骤4: 最终方案深化
            step4_result = self._step4_final_plan_deepening(step3_result, progress_callback)
            self.results["final_plan"] = step4_result
            self._save_step_result("step4_final_plan", step4_result, project_path)
            
            # 汇总结果
            final_result = {
                "session_id": self.session_id,
                "generation_mode": "creative_to_plan_conversation",
                "generated_at": datetime.now().isoformat(),
                "steps": CREATIVE_STEPS,
                "step1_commercial_analysis": step1_result,
                "step2_multi_plan": step2_result,
                "step3_selected_plan": step3_result,
                "step4_final_plan": step4_result,
                "final_plan": step4_result.get("final_plan", {}),
                "tomato_upload_data": step4_result.get("tomato_upload_data", {}),
                "turn_count": self.session.turn_count if self.session else 0
            }
            
            logger.info(f"[{self.session_id}] 4步流程完成 | 总轮次: {self.session.turn_count if self.session else 0}")
            return final_result
            
        except Exception as e:
            logger.error(f"[{self.session_id}] 执行失败: {e}")
            raise
    
    def _step1_commercial_analysis(
        self,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """步骤1: 商业化分析与创意扩展"""
        step = CREATIVE_STEPS[0]
        logger.info(f"[{self.session_id}] 步骤1: {step.name}")
        
        if progress_callback:
            progress_callback(
                step.step_id, 
                step.progress, 
                f"正在进行{step.name}...",
                {"stage": step.ui_stage, "detail": "检测同人文类型并补充背景资料"}
            )
        
        # 构建用户提示词
        title = self.novel_data.get("title", "") or self.novel_data.get("novel_title", "")
        synopsis = self.novel_data.get("synopsis", "") or self.novel_data.get("novel_synopsis", "")
        category = self.novel_data.get("category", "未分类")
        creative_seed = self.novel_data.get("creative_seed", "")
        
        user_prompt = f"""请对以下小说创意进行全面的商业化分析：

**原始创意**
- 书名: {title}
- 类型: {category}
- 简介: {synopsis}
- 创意种子: {creative_seed}

**你的任务**
1. **同人文检测**：判断是否基于现有作品（动漫、游戏、小说、影视等）
   - 如果是同人文：
     * 明确原作名称
     * 补充原作核心设定（世界观、力量体系、主要角色关系）
     * 分析原作粉丝群体特征
     * 指出同人文写作禁忌（不能改动的核心设定）
   - 如果不是同人文：分析为原创设定的市场空间

2. **番茄平台适配分析**
   - 该类型在番茄的历史表现（爆款案例）
   - 目标读者画像（年龄、性别、阅读偏好）
   - 推荐机制适配度（是否容易获得流量）

3. **核心卖点提炼**
   - 一句话卖点（电梯演讲）
   - 3个核心爽点
   - 差异化竞争力

4. **创意扩展建议**
   - 如何强化商业化属性
   - 潜在的风险点及规避方案

**输出格式（严格JSON，必须遵守以下规则）**

⚠️ **重要格式要求**：
1. **必须**使用双引号包裹所有字符串（不要用单引号）
2. **必须**确保JSON结构完整，每个 `{{` 都有对应的 `}}`
3. **必须**确保数组和对象最后一个元素后**没有**多余的逗号
4. **必须**确保所有键名用双引号包裹

```json
{{
  "is_fanfiction": false,
  "original_work": {{
    "name": "",
    "genre": "",
    "core_setting": "",
    "power_system": "",
    "main_characters": [],
    "fan_taboos": [],
    "target_fans": ""
  }},
  "tomato_analysis": {{
    "historical_performance": "",
    "target_audience": {{
      "age": "18-30",
      "gender": "均衡",
      "preferences": []
    }},
    "algorithm_fit": ""
  }},
  "core_selling_points": {{
    "one_liner": "",
    "main_hooks": [],
    "differentiation": ""
  }},
  "creative_expansion": {{
    "commercial_enhancement": "",
    "risks": [],
    "mitigations": []
  }}
}}
```

⚠️ **警告**：如果JSON格式错误，系统将无法解析你的回答！

请只输出JSON，不要任何其他文字、解释或代码块标记之外的字符。"""

        # 发送对话消息
        response = self.session.send_message(
            user_prompt=user_prompt,
            temperature=self.temperature,
            purpose="步骤1:商业化分析"
        )
        
        # 解析结果
        result = self._parse_json_response(response)
        logger.info(f"[{self.session_id}] 步骤1完成: 同人文={result.get('is_fanfiction', 'unknown')}")
        
        return result
    
    def _step2_multi_plan_generation(
        self,
        step1_result: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """步骤2: 多方案生成与评分"""
        step = CREATIVE_STEPS[1]
        logger.info(f"[{self.session_id}] 步骤2: {step.name}")
        
        if progress_callback:
            progress_callback(
                step.step_id,
                step.progress,
                f"正在{step.name}...",
                {"stage": step.ui_stage, "detail": "AI正在生成2-3个差异化方案并评分"}
            )
        
        # 构建用户提示词
        is_fanfiction = step1_result.get("is_fanfiction", False)
        original_work = step1_result.get("original_work", {})
        core_selling_points = step1_result.get("core_selling_points", {})
        
        fanfiction_context = ""
        if is_fanfiction and original_work:
            fanfiction_context = f"""
**同人文背景（必须严格遵守）**
- 原作: {original_work.get('name', '')}
- 核心设定: {original_work.get('core_setting', '')}
- 写作禁忌: {', '.join(original_work.get('fan_taboos', []))}
"""
        
        user_prompt = f"""基于步骤1的商业化分析，请生成2-3个差异化的小说方案。

**步骤1分析结果**
- 一句话卖点: {core_selling_points.get('one_liner', '')}
- 核心爽点: {', '.join(core_selling_points.get('main_hooks', []))}
- 差异化竞争力: {core_selling_points.get('differentiation', '')}
{fanfiction_context}

**方案设计要求**
每个方案必须包含：
1. **标题**：符合番茄风格，有吸引力
2. **核心设定**：主角身份、金手指/金大腿、核心冲突
3. **开篇设计**：前3章的核心爽点布局
4. **差异化亮点**：与同类作品的区别
5. **风险点**：该方案潜在的问题

**评分维度（1-100分）**
- commercial_potential: 商业潜力（市场接受度、变现能力）
- innovation: 创新性（是否新颖、避免同质化）
- feasibility: 可行性（作者能否驾驭、设定是否容易崩）
- tomato_fit: 番茄适配度（是否符合平台调性）

**输出格式（JSON）**
```json
{{
  "plans": [
    {{
      "id": 1,
      "title": "方案1标题",
      "subtitle": "副标题/一句话简介",
      "core_setting": {{
        "protagonist": "主角身份设定",
        "golden_finger": "金手指/能力",
        "core_conflict": "核心冲突"
      }},
      "opening_design": "前3章爽点布局",
      "differentiation": "差异化亮点",
      "risks": "潜在风险点",
      "score": {{
        "commercial_potential": 90,
        "innovation": 75,
        "feasibility": 85,
        "tomato_fit": 92
      }},
      "total_score": 85.5
    }},
    // 方案2、方案3...
  ],
  "comparison": "三个方案的对比分析总结"
}}
```

要求：
1. 生成2-3个方向明显不同的方案（激进/稳健/创新）
2. 评分要客观，基于市场数据和可行性
3. 只输出JSON，不要其他解释"""

        response = self.session.send_message(
            user_prompt=user_prompt,
            temperature=self.temperature + 0.1,  # 稍微提高创造性
            purpose="步骤2:多方案生成"
        )
        
        result = self._parse_json_response(response)
        plans = result.get("plans", [])
        logger.info(f"[{self.session_id}] 步骤2完成: 生成{len(plans)}个方案")
        
        return result
    
    def _step3_selection_bestseller(
        self,
        step2_result: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """步骤3: 智能选优+爆款对标"""
        step = CREATIVE_STEPS[2]
        logger.info(f"[{self.session_id}] 步骤3: {step.name}")
        
        if progress_callback:
            progress_callback(
                step.step_id,
                step.progress,
                f"正在{step.name}...",
                {"stage": step.ui_stage, "detail": "对比番茄爆款进行优化"}
            )
        
        plans = step2_result.get("plans", [])
        if not plans:
            raise ValueError("没有可用的方案")
        
        # 自动选择评分最高的方案
        best_plan = max(plans, key=lambda p: p.get("total_score", 0))
        
        user_prompt = f"""基于步骤2的多个方案，请完成智能选优和爆款对标优化。

**步骤2生成的方案**
{json.dumps(plans, ensure_ascii=False, indent=2)}

**自动选择结果**
- 选定方案: {best_plan.get('title', '')}
- 选择理由: 综合评分最高({best_plan.get('total_score', 0)}分)

**你的任务**
1. **确认选择**：分析为什么这个方案是最优的（评分维度拆解）

2. **番茄爆款对标分析**
   - 列出3-5部番茄同类爆款（书名+核心套路）
   - 对比选定的方案与爆款的差异
   - 识别差距（情绪曲线、爽点密度、人设等）

3. **针对性优化**
   - 基于爆款对比，优化选定方案
   - 强化商业属性
   - 修复潜在风险点

4. **输出优化后的方案框架**
   - 优化后的标题（如有必要可微调）
   - 优化后的核心设定
   - 优化后的开篇设计

**输出格式（JSON）**
```json
{{
  "selection": {{
    "selected_id": {best_plan.get('id', 1)},
    "selected_title": "{best_plan.get('title', '')}",
    "selection_reason": "选择理由（评分维度拆解）",
    "score_breakdown": "各维度得分分析"
  }},
  "bestseller_comparison": {{
    "reference_works": [
      {{"title": "爆款1", "core_routine": "核心套路", "similarities": "相似点", "gaps": "差距"}},
      // 更多爆款...
    ],
    "key_gaps": ["差距1", "差距2", "差距3"],
    "optimization_directions": ["优化方向1", "方向2"]
  }},
  "optimized_plan": {{
    "title": "优化后的标题",
    "subtitle": "优化后的副标题",
    "core_setting": {{
      "protagonist": "优化后的主角设定",
      "golden_finger": "优化后的金手指",
      "core_conflict": "优化后的核心冲突"
    }},
    "opening_design": "优化后的前3章设计",
    "emotion_curve": "情绪曲线设计（起承转合）",
    "爽点_layout": "全书爽点布局规划"
  }}
}}
```

请只输出JSON，不要其他解释。"""

        response = self.session.send_message(
            user_prompt=user_prompt,
            temperature=self.temperature,
            purpose="步骤3:智能选优+爆款对标"
        )
        
        result = self._parse_json_response(response)
        logger.info(f"[{self.session_id}] 步骤3完成: 选择方案={result.get('selection', {}).get('selected_title', '')}")
        
        return result
    
    def _step4_final_plan_deepening(
        self,
        step3_result: Dict,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """步骤4: 最终方案深化"""
        step = CREATIVE_STEPS[3]
        logger.info(f"[{self.session_id}] 步骤4: {step.name}")
        
        if progress_callback:
            progress_callback(
                step.step_id,
                step.progress,
                f"正在{step.name}...",
                {"stage": step.ui_stage, "detail": "生成完整的可执行方案"}
            )
        
        optimized_plan = step3_result.get("optimized_plan", {})
        
        user_prompt = f"""基于步骤3优化后的方案，请深化为完整可执行的final_plan。

**优化后的方案框架**
{json.dumps(optimized_plan, ensure_ascii=False, indent=2)}

**你的任务**
深化为完整的final_plan，包含：

1. **核心设定详解（世界观+角色+金手指）**
   - 世界观：背景、力量体系、规则
   - 主角：身份、性格、目标、成长线
   - 金手指：能力、限制、升级路线
   - 核心配角：盟友、反派、女主/男主

2. **全书结构框架**
   - 阶段划分（建议3-5个阶段）
   - 每个阶段的核心目标+关键事件
   - 阶段间的递进关系

3. **情绪曲线设计**
   - 全书情绪走向（压抑→爆发→更高潮）
   - 关键情绪转折点

4. **番茄上传数据**
   - 书名（主标题+副标题）
   - 简介（100字以内，突出卖点）
   - 标签（3-5个，符合番茄分类）
   - 核心卖点（3个，用于平台推广）

5. **执行建议**
   - 写作注意事项
   - 避坑指南

**输出格式（JSON）**
```json
{{
  "final_plan": {{
    "title": "书名",
    "subtitle": "副标题",
    "genre": "类型",
    "core_setting": {{
      "worldview": "世界观详解",
      "power_system": "力量体系",
      "protagonist": {{
        "identity": "身份",
        "personality": "性格",
        "goal": "目标",
        "growth_arc": "成长线"
      }},
      "golden_finger": {{
        "ability": "能力",
        "limitations": "限制",
        "upgrade_path": "升级路线"
      }},
      "key_characters": [
        {{"role": "盟友", "description": "..."}},
        {{"role": "反派", "description": "..."}}
      ]
    }},
    "book_structure": {{
      "total_stages": 4,
      "stages": [
        {{
          "stage_number": 1,
          "name": "阶段名",
          "chapters": "1-50",
          "goal": "阶段目标",
          "key_events": ["事件1", "事件2"],
          "climax": "阶段高潮"
        }},
        // 更多阶段...
      ]
    }},
    "emotion_curve": {{
      "overall_arc": "压抑→爆发→登顶",
      "key_turning_points": ["转折点1", "转折点2"]
    }},
    "execution_notes": ["注意1", "注意2"]
  }},
  "tomato_upload_data": {{
    "title": "番茄书名",
    "subtitle": "副标题",
    "synopsis": "简介（100字内）",
    "tags": ["标签1", "标签2", "标签3"],
    "selling_points": ["卖点1", "卖点2", "卖点3"]
  }}
}}
```

请只输出JSON，不要其他解释。"""

        response = self.session.send_message(
            user_prompt=user_prompt,
            temperature=self.temperature,
            purpose="步骤4:最终方案深化"
        )
        
        result = self._parse_json_response(response)
        logger.info(f"[{self.session_id}] 步骤4完成: final_plan生成完成")
        
        return result
    
    def _parse_json_response(self, response: str, max_retries: int = 2) -> Dict:
        """解析JSON响应 - 增强容错版，带自动重试"""
        import re
        
        # 🔥 防御：API返回None时的空值检查
        if response is None:
            logger.warning(f"[{self.session_id}] API返回空响应，跳过JSON解析")
            return {}
        
        # 先清理常见的格式问题
        cleaned = response.strip()
        
        # 移除 BOM 标记
        if cleaned.startswith('\ufeff'):
            cleaned = cleaned[1:]
        
        # 🔥 第一轮：尝试各种解析方法
        # 尝试直接解析
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass
        
        # 尝试提取JSON代码块
        try:
            json_match = re.search(r'```(?:json)?\s*({\s*".*?})\s*```', cleaned, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
        
        # 尝试查找第一个 { 和最后一个 }
        try:
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1 and start < end:
                json_str = cleaned[start:end+1]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 修复常见JSON错误后再尝试
        try:
            fixed = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            fixed = fixed.replace("'", '"')
            fixed = re.sub(r'([{,])\s*(\w+):', r'\1"\2":', fixed)
            start = fixed.find('{')
            end = fixed.rfind('}')
            if start != -1 and end != -1:
                return json.loads(fixed[start:end+1])
        except json.JSONDecodeError:
            pass
        
        # 🔥 第二轮：让AI修复JSON格式（重试机制）
        if max_retries > 0 and self.session:
            logger.warning(f"[{self.session_id}] JSON解析失败，请求AI修复格式（剩余重试次数: {max_retries}）")
            try:
                fix_prompt = f"""你刚才的返回JSON格式有误，请修复并重新输出正确的JSON。

**错误信息**: JSON格式错误，请检查引号、逗号等

**你的原始返回**:
```
{cleaned[:2000]}...
```

**要求**:
1. 只输出正确的JSON，不要其他解释
2. 确保所有字符串用双引号包裹
3. 确保没有多余的逗号
4. 确保JSON结构完整

请输出修复后的JSON:"""
                
                fixed_response = self.session.send_message(
                    user_prompt=fix_prompt,
                    temperature=0.3
                )
                
                # 递归调用，减少重试次数
                return self._parse_json_response(fixed_response, max_retries - 1)
                
            except Exception as e:
                logger.error(f"[{self.session_id}] AI修复JSON失败: {e}")
        
        # 记录失败的响应用于调试
        logger.error(f"[{self.session_id}] JSON解析失败，所有重试已用尽")
        error_file = Path(f"logs/json_parse_error_{self.session_id}.txt")
        try:
            error_file.parent.mkdir(exist_ok=True)
            with open(error_file, 'w', encoding='utf-8') as f:
                f.write(f"解析失败的响应:\n{cleaned}\n\n")
            logger.error(f"[{self.session_id}] 失败的响应已保存到: {error_file}")
        except:
            pass
        
        # 🔥 返回一个默认结果而不是崩溃
        logger.warning(f"[{self.session_id}] 返回默认结果，避免崩溃")
        return self._get_default_result()
    
    def _get_default_result(self) -> Dict:
        """获取默认结果，用于JSON解析失败时避免崩溃"""
        return {
            "error": "JSON解析失败，使用默认结果",
            "is_fanfiction": False,
            "original_work": {},
            "tomato_analysis": {
                "historical_performance": "解析失败，默认中等表现",
                "target_audience": {"age": "18-30岁", "gender": "均衡", "preferences": []},
                "algorithm_fit": "5"
            },
            "core_selling_points": {
                "one_liner": "解析失败，请检查创意输入",
                "main_hooks": [],
                "differentiation": "默认差异化"
            },
            "creative_expansion": {
                "commercial_enhancement": "解析失败，使用默认建议",
                "risks": [],
                "mitigations": []
            }
        }
    
    def _save_step_result(self, step_name: str, data: Dict, project_path: Optional[str]):
        """保存步骤结果到文件"""
        if not project_path:
            return
        
        try:
            output_dir = Path(project_path) / "creative_conversation"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            output_file = output_dir / f"{step_name}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[{self.session_id}] 步骤结果已保存: {output_file}")
        except Exception as e:
            logger.warning(f"[{self.session_id}] 保存步骤结果失败: {e}")


# 便捷函数
def generate_creative_to_plan(
    api_client,
    novel_data: Dict[str, Any],
    progress_callback: Optional[Callable] = None,
    project_path: Optional[str] = None,
    provider: str = "gemini",
    model_name: str = None
) -> Dict[str, Any]:
    """
    使用对话模式生成从创意到方案的完整流程
    
    这是便捷函数，用于快速调用
    
    Args:
        api_client: APIClient 实例
        novel_data: 小说基础数据
        progress_callback: 进度回调函数
        project_path: 项目路径
        provider: API 提供商
        model_name: 模型名称
        
    Returns:
        包含 final_plan 的完整结果
    """
    session = CreativeToPlanConversation(
        api_client=api_client,
        novel_data=novel_data,
        provider=provider,
        model_name=model_name
    )
    
    return session.execute_all_steps(
        progress_callback=progress_callback,
        project_path=project_path
    )
