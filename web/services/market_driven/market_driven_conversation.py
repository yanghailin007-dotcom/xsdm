"""
市场导向对话生成器
在一个连续对话中完成套路分析 → 方案生成 → 一阶段产物生成
利用Kimi的256K上下文窗口和缓存机制

v2.0更新：基于爆款反向工程分析生成Prompt
v3.0更新：支持提示词包（PromptPackage）动态加载
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

# 🔥 导入提示词包支持
try:
    from web.services.prompt_package import PromptPackage, PromptPackageManager
    HAS_PROMPT_PACKAGE = True
    logging.info("[MarketDrivenConversation] PromptPackage支持已加载")
except ImportError as e:
    HAS_PROMPT_PACKAGE = False
    logging.warning(f"[MarketDrivenConversation] PromptPackage未加载: {e}")

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
        # 🔥 移除：generate_emotion_curve - 情绪曲线改在战术规划中分批生成
    ]
    
    def __init__(self, api_client, genre: str, user_choices: Dict, 
                 tropes: Optional[Dict] = None, provider: str = None,
                 prompt_package: Optional['PromptPackage'] = None,
                 user_id: Optional[str] = None):
        """
        初始化市场导向对话会话
        
        Args:
            api_client: APIClient实例
            genre: 题材
            user_choices: 用户选择（包含标题、剧情路线、主角等）
            tropes: 套路分析结果（可选，作为参考）
            provider: 提供商，None则使用APIClient默认提供商
            prompt_package: 提示词包（可选，用于自定义提示词）
            user_id: 用户ID（用于加载用户的提示词包）
        """
        # 🔥 修复：支持任意提供商，不再硬编码kimi
        if provider is None:
            provider = getattr(api_client, 'default_provider', 'kimi')
            logger.info(f"[对话模式] 使用APIClient默认提供商: {provider}")
        
        self.api_client = api_client
        self.genre = genre
        
        # 🔥 修复章节数：根据字数重新计算正确的章节数
        from .config import get_config, get_target_words
        target_words = user_choices.get('target_words') or get_target_words(genre)
        correct_chapters = target_words // get_config(genre)["words_per_chapter"]
        user_chapters = user_choices.get('chapters', 0)
        if user_chapters and user_chapters != correct_chapters:
            logger.error(f"[🔥章节数修正] {user_chapters} -> {correct_chapters} (基于{target_words}字)")
            user_choices = {**user_choices, "chapters": correct_chapters}
        else:
            logger.info(f"[章节数检查] 使用原始值: {user_chapters} 章, 目标字数: {target_words}")
        
        self.user_choices = user_choices
        self.tropes = tropes or {}
        
        # 🔥 处理主角名：如果包含多个候选名（如 "苏辰/叶枫/秦天"），只取第一个
        protagonist_name = self.user_choices.get('protagonist_name', '')
        if protagonist_name and '/' in str(protagonist_name):
            first_name = str(protagonist_name).split('/')[0].strip()
            self.user_choices['protagonist_name'] = first_name
            logger.info(f"[对话模式 {self.session_id}] 多个主角候选名 detected，使用第一个: {first_name}")
        self.provider = provider
        self.results = {}
        
        # 🔥 生成唯一会话ID，用于日志追踪
        import uuid
        self.session_id = f"MDC-{uuid.uuid4().hex[:8].upper()}"
        
        # 🔥 加载提示词包
        self._prompt_package = None
        if HAS_PROMPT_PACKAGE:
            if prompt_package:
                self._prompt_package = prompt_package
                logger.info(f"[对话模式 {self.session_id}] 使用指定的提示词包: {prompt_package.name}")
            elif user_id:
                # 从管理器加载用户的提示词包
                try:
                    pkg_manager = PromptPackageManager()
                    self._prompt_package = pkg_manager.get_package_for_generation(
                        user_id=user_id,
                        mode="market_driven"
                    )
                    logger.info(f"[对话模式 {self.session_id}] 已加载用户提示词包: {self._prompt_package.name}")
                except Exception as e:
                    logger.warning(f"[对话模式 {self.session_id}] 加载提示词包失败: {e}，将使用默认方式")
        
        # 🔥 加载步骤提示词配置
        self._step_prompts_config = self._load_step_prompts_config()
        
        # 🔥 基于爆款反向工程分析，生成高质量Prompt模板
        self._prompt_generator = None
        if HAS_BESTSELLER_ANALYSIS and api_client:
            try:
                logger.info(f"[对话模式 {self.session_id}] 启动爆款反向工程分析...")
                analyzer = BestsellerAnalyzer(api_client=api_client)
                # 🔥 修复：禁用缓存，确保每次生成都是新鲜的分析结果
                bestseller_analysis = analyzer.analyze_genre(genre, use_cache=False)
                
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
    
    def _load_step_prompts_config(self) -> Dict:
        """加载步骤提示词配置"""
        try:
            from pathlib import Path
            import json
            config_path = Path("prompt_packages/default/market_driven/conversation_step_prompts.json")
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.warning(f"[对话模式 {self.session_id}] 无法加载步骤提示词配置: {e}")
            return {}
    
    def _get_step_prompt(self, step_name: str, **kwargs) -> str:
        """获取步骤提示词"""
        step_config = self._step_prompts_config.get("steps", {}).get(step_name, {})
        template = step_config.get("fallback_template", "")
        
        if not template:
            error_msg = f"""
❌ 错误：步骤 '{step_name}' 的提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/conversation_step_prompts.json

或使用API创建配置：
POST /api/v2/prompt-config/component/{step_name}
"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.warning(f"[对话模式 {self.session_id}] 提示词模板变量缺失: {e}，使用原始模板")
            return template
    
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
        # 🔥 确保是字符串
        if not isinstance(selected_plot_name, str):
            selected_plot_name = str(selected_plot_name)
        
        # 1. 移除所有备选标题（用户已确定标题，不需要其他选项）
        if 'title_templates' in filtered:
            del filtered['title_templates']
        
        # 2. 只保留用户选择的那条剧情路线
        if 'plot_templates' in filtered and selected_plot_name:
            original_plots = filtered['plot_templates']
            # 查找用户选择的那条路线
            selected_plot_template = None
            for plot in original_plots:
                plot_name = plot.get('name', '')
                # 🔥 确保是字符串
                if not isinstance(plot_name, str):
                    plot_name = str(plot_name)
                if plot_name == selected_plot_name:
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
        
        # 🔥 确保是字符串
        if not isinstance(plot_name, str):
            plot_name = str(plot_name)
        if not isinstance(plot_detail, str):
            plot_detail = str(plot_detail)
        
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
5. **阶段目标** - 基于成长路线，划分阶段目标（情绪曲线改在战术规划中分批生成）

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
        """构建默认的设定阶段System Prompt（当TropePromptBuilder不可用时使用）- 从JSON配置加载"""
        # 尝试从JSON配置加载
        try:
            config_file = Path(__file__).parent.parent.parent.parent / \
                "prompt_packages" / "default" / "market_driven" / "conversation_step_prompts.json"
            
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                template_config = config.get("setting_system_prompt", {})
                template = template_config.get("template", "")
                
                if template:
                    return template.replace("{title}", title)
        except Exception as e:
            logger.warning(f"[对话模式 {getattr(self, 'session_id', 'N/A')}] 加载setting_system_prompt配置失败: {e}")
        
        # 降级：硬编码
        logger.warning(f"[对话模式 {getattr(self, 'session_id', 'N/A')}] 使用硬编码setting_system_prompt")
        return f"# 🎯 角色：顶级网文策划专家\n\n目标作品：《{title}\n\n## 创作指导原则\n- 结构对标\n- 数值精确\n- 节奏精准"
    
    def _get_step_prompt_from_package(self, step_id: str, variables: Dict) -> Optional[str]:
        """
        从提示词包获取步骤提示词
        
        Args:
            step_id: 步骤ID（如 step_1_plan）
            variables: 变量字典
            
        Returns:
            渲染后的提示词，如果提示词包不可用则返回None
        """
        if not self._prompt_package:
            return None
        
        try:
            step_config = self._prompt_package.get_step(step_id)
            if not step_config:
                logger.warning(f"[对话模式 {self.session_id}] 提示词包中未找到步骤: {step_id}")
                return None
            
            # 渲染提示词
            prompt = step_config.render_prompt(variables)
            logger.info(f"[对话模式 {self.session_id}] 已从提示词包加载步骤 [{step_id}]")
            return prompt
            
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 从提示词包加载步骤失败 [{step_id}]: {e}")
            return None
    
    def _save_step_result(self, step_name: str, results: Dict, project_path: str = None):
        """保存步骤结果到项目目录
        
        Args:
            step_name: 步骤名称
            results: 当前所有结果
            project_path: 项目路径（可选）
        """
        if not project_path:
            return
            
        try:
            from pathlib import Path
            import json
            
            base_path = Path(project_path)
            base_path.mkdir(parents=True, exist_ok=True)
            
            # 保存到 project_info.json 的 generation_metadata 中
            info_path = base_path / "project_info.json"
            
            # 读取现有内容
            project_info = {}
            if info_path.exists():
                with open(info_path, 'r', encoding='utf-8') as f:
                    project_info = json.load(f)
            
            # 初始化 generation_metadata
            if "generation_metadata" not in project_info:
                project_info["generation_metadata"] = {}
            
            # 🔥 保存目标章节数到 generation_metadata，用于前端进度计算
            total_chapters = self.user_choices.get('chapters')
            if total_chapters:
                try:
                    project_info["generation_metadata"]["target_chapters"] = int(total_chapters)
                except (ValueError, TypeError):
                    pass
            
            # 保存当前步骤结果
            if "mode_specific" not in project_info["generation_metadata"]:
                project_info["generation_metadata"]["mode_specific"] = {}
            
            if "info" not in project_info["generation_metadata"]["mode_specific"]:
                project_info["generation_metadata"]["mode_specific"]["info"] = {}
            
            # 更新结果
            project_info["generation_metadata"]["mode_specific"]["info"].update(results)
            project_info["generation_metadata"]["step_completed"] = step_name
            project_info["generation_metadata"]["updated_at"] = datetime.now().isoformat()
            
            # 写入文件
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(project_info, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[对话模式 {self.session_id}] 步骤 [{step_name}] 结果已保存到: {info_path}")
            
            # 🔥 同时保存独立的产物文件到 phase_one_products/ 目录
            self._save_phase_one_product(step_name, results, base_path)
            
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 保存步骤结果失败: {e}")
    
    def _save_phase_one_product(self, step_name: str, results: Dict, base_path: Path):
        """保存第一阶段产物到独立文件
        
        Args:
            step_name: 步骤名称
            results: 当前所有结果
            base_path: 项目基础路径
        """
        try:
            import json
            
            # 步骤名称到产物文件名的映射
            product_mapping = {
                "plan": ("完整方案.json", "plan"),
                "fanqie_data": ("番茄上传数据.json", "fanqie_upload_data"),
                "worldview": ("世界观设定.json", "core_worldview"),
                "characters": ("角色设计.json", "character_design"),
                "growth_plan": ("升级路线.json", "global_growth_plan"),
                "stage_goals": ("阶段目标.json", "stage_goals"),
                "emotion_curve": ("情绪曲线.json", "emotion_curve"),
                "tactical_plan": ("战术规划.json", "tactical_plan"),
                "writing_style_guide": ("写作风格指南.json", "writing_style_guide"),
                "market_analysis": ("市场分析.json", "market_analysis"),
                "emotional_blueprint": ("情绪蓝图.json", "emotional_blueprint"),
                "alignment": ("爆款对齐报告.json", "alignment_report"),
            }
            
            if step_name not in product_mapping:
                return
            
            filename, result_key = product_mapping[step_name]
            product_path = base_path / "phase_one_products" / filename
            product_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 获取对应的数据
            if result_key in results:
                data = results[result_key]
                with open(product_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                logger.info(f"[对话模式 {self.session_id}] 产物 [{step_name}] 已保存到: {product_path}")
            
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 保存产物文件失败 [{step_name}]: {e}")
    
    def generate_all(self, progress_callback=None, project_path: str = None) -> Dict:
        """
        执行所有生成步骤
        
        Args:
            progress_callback: 进度回调函数(step_name, progress_percent)
            project_path: 项目路径，用于每步保存中间结果
        
        Returns:
            所有产物字典
        """
        # 🔥 版本标记，确保代码已更新
        logger.info(f"[对话模式 {self.session_id}] ===== CODE VERSION: DEBUG_v2_with_logging =====")
        
        results = {
            "generation_mode": "market_driven_conversation",
            "generated_at": datetime.now().isoformat(),
            "genre": self.genre,
        }
        
        logger.info(f"[对话模式 {self.session_id}] 开始5步对话生成流程...")
        
        # 步骤1: 生成方案 (20%) -> UI阶段: planning
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1/6: 生成完整方案")
        if progress_callback:
            progress_callback("generate_plan", 20)
        plan = self._generate_plan()
        results["plan"] = plan
        results["title"] = plan.get("title", "")
        self._save_step_result("plan", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1完成 | 标题: {plan.get('title', 'N/A')}")
        
        # 🔥 步骤1B: 生成番茄上传数据（书名、简介、标签）
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1B/6: 生成番茄上传数据")
        if progress_callback:
            progress_callback("generate_fanqie_data", 28)
        fanqie_data = self._generate_fanqie_upload_data(plan)
        results["fanqie_upload_data"] = fanqie_data
        # 同步到 plan 以便后续使用
        plan["recommended_title"] = fanqie_data["title"]
        plan["core_selling_points"] = [{"point": fanqie_data["synopsis"]}]
        plan["tags"] = fanqie_data["tags"]
        self._save_step_result("fanqie_data", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] [UI:planning] 步骤1B完成 | 书名: {fanqie_data['title']}")
        
        # 步骤2: 生成世界观 (35%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤2/7: 生成世界观")
        if progress_callback:
            progress_callback("generate_worldview", 35)
        worldview = self._generate_worldview()
        results["core_worldview"] = worldview
        results["faction_system"] = self._extract_faction_system(worldview)
        self._save_step_result("worldview", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤2完成 | 世界观已保存")
        
        # 步骤3: 生成角色 (50%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤3/7: 生成角色设计")
        if progress_callback:
            progress_callback("generate_characters", 50)
        characters = self._generate_characters()
        results["character_design"] = characters
        self._save_step_result("characters", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤3完成 | 角色设计已保存")
        
        # 步骤4: 生成成长路线 (65%) -> UI阶段: worldview
        logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤4/7: 生成成长路线")
        if progress_callback:
            progress_callback("generate_growth_plan", 65)
        try:
            growth_plan = self._generate_growth_plan()
            results["global_growth_plan"] = growth_plan
            self._save_step_result("growth_plan", results, project_path)
            logger.info(f"[对话模式 {self.session_id}] [UI:worldview] 步骤4完成 | 成长路线已保存")
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 步骤4失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # 步骤5: 生成阶段目标 (80%) -> UI阶段: chapters
        # 🔥 优化：情绪曲线改在战术规划中分批生成（每30章），避免一次性生成200章导致超时
        logger.info(f"[对话模式 {self.session_id}] [UI:chapters] 步骤5/6: 生成阶段目标")
        if progress_callback:
            progress_callback("generate_stage_goals", 80)
        
        try:
            stage_goals = self._generate_stage_goals(results)
            results["stage_goals"] = stage_goals
            # 🔥 使用默认情绪曲线模板（战术规划时会细化每30章的情绪设计）
            results["emotion_curve"] = self._get_default_emotion_curve()
            self._save_step_result("stage_goals", results, project_path)
            logger.info(f"[对话模式 {self.session_id}] [UI:chapters] 步骤5完成 | 阶段目标数: {len(stage_goals)} 已保存")
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 步骤5失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        
        # 🔥 步骤6: 爆款对齐检查与优化 (90%) -> UI阶段: final_check
        logger.info(f"[对话模式 {self.session_id}] [UI:final_check] 步骤6/6: 爆款对齐检查与优化")
        if progress_callback:
            progress_callback("bestseller_alignment", 90)
        aligned_results = self._bestseller_alignment_check(results)
        results.update(aligned_results)
        self._save_step_result("alignment", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] [UI:final_check] 步骤6完成 | 对齐优化已保存")
        
        # 步骤6B: 生成附加产物 (100%) -> UI阶段: complete
        logger.info(f"[对话模式 {self.session_id}] [UI:complete] 步骤6B/6: 生成附加产物")
        if progress_callback:
            progress_callback("generate_supplementary", 100)
        
        # 补充产物
        results["writing_style_guide"] = self._generate_writing_style_guide()
        results["market_analysis"] = self._generate_market_analysis()
        results["emotional_blueprint"] = self._generate_emotional_blueprint()
        
        # 🔥 保存补充产物
        if project_path:
            self._save_phase_one_product("writing_style_guide", results, Path(project_path))
            self._save_phase_one_product("market_analysis", results, Path(project_path))
            self._save_phase_one_product("emotional_blueprint", results, Path(project_path))
            logger.info(f"[对话模式 {self.session_id}] 补充产物已保存到 phase_one_products/")
        
        # 🔥 最终保存
        self._save_step_result("complete", results, project_path)
        logger.info(f"[对话模式 {self.session_id}] ✅ 所有6个步骤完成 | 总轮次: {self.session.turn_count} | 全部结果已保存")
        return results
    
    def _generate_plan(self) -> Dict:
        """生成完整方案（使用基于爆款的Prompt模板或提示词包）"""
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        selected_plot = self.user_choices.get('selected_plot', {})
        
        # 🔥 首先尝试从提示词包加载
        if self._prompt_package:
            # 准备变量
            variables = {
                "genre": self.genre,
                "title": title,
                "protagonist_name": protagonist_name,
                "plot_detail": selected_plot.get("detail", "") if selected_plot else "",
            }
            
            # 如果爆款分析可用，添加相关变量
            if self._prompt_generator:
                analysis = self._prompt_generator.analysis
                variables.update({
                    "genre_formula": analysis.get("genre_formula", ""),
                    "ch1_scene": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("scene", ""),
                    "ch1_protagonist_situation": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("protagonist_situation", ""),
                    "ch1_system_trigger": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("system_trigger", ""),
                    "ch1_hook": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("hook", ""),
                    "ch1_emotion_curve": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("emotion_curve", ""),
                    "ch1_word_count": analysis.get("opening_3_chapters", {}).get("chapter_1", {}).get("word_count", "2500-2800"),
                    "ch2_scene": analysis.get("opening_3_chapters", {}).get("chapter_2", {}).get("scene", ""),
                    "ch2_reward": analysis.get("opening_3_chapters", {}).get("chapter_2", {}).get("reward", ""),
                    "ch2_reactions": analysis.get("opening_3_chapters", {}).get("chapter_2", {}).get("reactions", ""),
                    "ch2_hook": analysis.get("opening_3_chapters", {}).get("chapter_2", {}).get("hook", ""),
                    "ch2_word_count": analysis.get("opening_3_chapters", {}).get("chapter_2", {}).get("word_count", "2500-2800"),
                    "ch3_scene": analysis.get("opening_3_chapters", {}).get("chapter_3", {}).get("scene", ""),
                    "ch3_antagonist": analysis.get("opening_3_chapters", {}).get("chapter_3", {}).get("antagonist", ""),
                    "ch3_plot": analysis.get("opening_3_chapters", {}).get("chapter_3", {}).get("plot", ""),
                    "ch3_hook": analysis.get("opening_3_chapters", {}).get("chapter_3", {}).get("hook", ""),
                    "ch3_word_count": analysis.get("opening_3_chapters", {}).get("chapter_3", {}).get("word_count", "2800-3000"),
                    "gf_initial_reward": analysis.get("golden_finger_formula", {}).get("initial_reward", ""),
                    "gf_growth_curve": analysis.get("golden_finger_formula", {}).get("growth_curve", ""),
                    "gf_limitations": analysis.get("golden_finger_formula", {}).get("limitations", ""),
                    "character_formula": analysis.get("character_formula", {}),
                    "taboo_list": "\n".join([f"- {t}" for t in analysis.get("taboos", [])]),
                })
            
            # 从提示词包获取提示词
            package_prompt = self._get_step_prompt_from_package("step_1_plan", variables)
            if package_prompt:
                prompt = package_prompt
                logger.info(f"[对话模式 {self.session_id}] 使用提示词包的步骤1提示词")
            else:
                prompt = None
        else:
            prompt = None
        
        # 🔥 如果没有从提示词包获取到，使用基于爆款分析的Prompt模板
        if prompt is None and self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤1）")
            prompt = self._prompt_generator.generate_step1_plan_prompt(
                title=title,
                protagonist_name=protagonist_name,
                selected_plot=selected_plot,
                tropes=self.tropes
            )
        elif prompt is None:
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
                "## 输出格式（严格JSON）",
                "返回标准JSON格式，包含: title, opening_design, golden_finger, protagonist, emotion_blueprint\n",
                "**严格要求**：字符串值内部的双引号必须转义为 \\\"，不要返回Markdown代码块\n",
                "只返回JSON，不要其他说明。"
            ]
            prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤1提示词 | 当前消息历史: {len(self.session.messages)}条")
        # 🔥 提高 temperature 增加多样性，使用随机种子
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤1-生成方案")
        self._logger.log_round("generate_plan", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤1响应接收 | 总对话轮次: {self.session.turn_count}")
        
        try:
            result = self._parse_json_response(response, "plan")
            # 验证必要字段
            required_fields = ["protagonist", "golden_finger", "core_conflict", "worldview", "recommended_title"]
            missing = [f for f in required_fields if f not in result]
            if missing:
                raise ValueError(f"plan 缺少必要字段: {missing}")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[对话模式 {self.session_id}] 生成 plan 失败: {e}")
            raise RuntimeError(f"生成方案失败: {e}") from e
    
    # 🔥 番茄小说标签预制映射（参考 plan_generator.py）
    FANQIE_TAG_MAPPINGS = {
        "male": {
            "神豪文-花钱返利类": {"main_category": "都市", "themes": ["神豪", "赚钱", "逆袭"], "roles": ["屌丝", "神豪", "美女"], "plots": ["系统流", "打脸", "逆袭"]},
            "国运文-直播类": {"main_category": "都市", "themes": ["国运", "直播", "无敌流"], "roles": ["主播", "选手", "观众"], "plots": ["直播流", "国运流", "召唤流"]},
            "国运文-扮演类": {"main_category": "都市", "themes": ["国运", "扮演", "无敌流"], "roles": ["扮演者", "选手", "历史人物"], "plots": ["扮演流", "国运流", "召唤流"]},
            "奶爸文-萌宝类": {"main_category": "都市", "themes": ["奶爸", "萌宝", "温馨"], "roles": ["奶爸", "萌娃", "宝妈"], "plots": ["带娃流", "温馨流", "日常流"]},
            "签到文-系统类": {"main_category": "都市", "themes": ["签到", "系统", "无敌流"], "roles": ["普通人", "强者", "美女"], "plots": ["签到流", "系统流", "无敌流"]},
            "末日求生-囤货类": {"main_category": "科幻", "themes": ["末日", "囤货", "求生"], "roles": ["求生者", "幸存者", "异能者"], "plots": ["末日流", "囤货流", "求生流"]},
            "灵气复苏-修炼类": {"main_category": "都市", "themes": ["灵气复苏", "修炼", "无敌流"], "roles": ["修炼者", "强者", "校花"], "plots": ["灵气复苏流", "修炼流", "无敌流"]},
        },
        "female": {
            "甜宠文-总裁类": {"main_category": "现代言情", "themes": ["甜宠", "总裁", "豪门"], "roles": ["女主", "总裁", "情敌"], "plots": ["先婚后爱", "追妻火葬场", "甜宠"]},
            "重生文-复仇类": {"main_category": "古代言情", "themes": ["重生", "复仇", "宅斗"], "roles": ["重生女主", "王爷", "白莲花"], "plots": ["重生复仇", "宅斗", "打脸"]},
        }
    }
    
    DEFAULT_TAGS = {
        "male": {"main_category": "都市", "themes": ["系统", "爽文", "无敌流"], "roles": ["男主", "美女", "反派"], "plots": ["系统流", "打脸", "逆袭"]},
        "female": {"main_category": "现代言情", "themes": ["甜宠", "爽文", "豪门"], "roles": ["女主", "男主", "女配"], "plots": ["甜宠", "打脸", "逆袭"]}
    }
    
    def _generate_fanqie_upload_data(self, plan: Dict) -> Dict:
        """
        生成番茄上传所需的专业数据（书名、简介、标签）
        
        🔥 参考 plan_generator.py 的专业实现：
        - 标签使用预制映射（FANQIE_TAG_MAPPINGS）
        - 简介使用番茄爆款公式生成
        """
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        genre = self.genre
        
        # 1. 书名优化（基于用户确定的标题）
        optimized_title = self._optimize_title_for_fanqie(title, genre)
        
        # 2. 生成专业简介（使用番茄爆款公式）
        synopsis = self._generate_synopsis_by_formula(plan, protagonist_name, genre)
        
        # 3. 获取预制标签（参考 plan_generator.py）
        tags = self._get_fanqie_tags(genre)
        
        return {
            "title": optimized_title,
            "synopsis": synopsis,
            "tags": tags
        }
    
    def _optimize_title_for_fanqie(self, title: str, genre: str) -> str:
        """优化书名符合番茄爆款公式"""
        # 去除书名号
        title = title.replace('《', '').replace('》', '').strip()
        
        # 确保≤15字
        if len(title) > 15:
            title = title[:15]
        
        return title
    
    def _generate_synopsis_by_formula(self, plan: Dict, protagonist_name: str, genre: str) -> str:
        """
        使用番茄爆款简介公式生成简介
        
        🔥 爆款简介公式（5段式，必须有情绪爆点）：
        第1段：【极端反差】主角表面身份 vs 实际能力（制造悬念）
        第2段：【困境铺垫】被嘲讽/被看不起的场景（引发共鸣）
        第3段：【金手指揭秘】核心能力+独特设定（期待感）
        第4段：【爽点预告】具体会做什么（打脸/震惊/收获）
        第5段：【情绪钩子】书名号/别名（增加传播性）
        """
        # 从 plan 提取关键信息
        gf = plan.get("golden_finger", {})
        protagonist = plan.get("protagonist", {})
        opening = plan.get("opening_design", {})
        
        # 提取金手指核心词（简化描述）
        gf_desc = gf.get("initial", "") if isinstance(gf, dict) else ""
        # 提取关键能力词
        gf_keywords = []
        if "扮演" in gf_desc or "模板" in gf_desc:
            gf_keywords.append("扮演系统")
        if "剑" in gf_desc or "剑仙" in gf_desc:
            gf_keywords.append("酒剑仙")
        if "雷神" in gf_desc:
            gf_keywords.append("雷神")
        if "签到" in gf_desc:
            gf_keywords.append("签到")
        
        gf_core = gf_keywords[0] if gf_keywords else "神秘系统"
        
        # 提取主角表面身份（从开局第1章）
        ch1 = opening.get("chapter_1", {}) if isinstance(opening, dict) else {}
        scene = ch1.get("scene", "")
        surface_identity = "普通人"
        if "保安" in scene or "保安" in str(protagonist):
            surface_identity = "醉酒保安"
        elif "外卖" in scene:
            surface_identity = "外卖小哥"
        elif "废柴" in scene or "落魄" in scene:
            surface_identity = "废柴"
        elif "屌丝" in scene:
            surface_identity = "穷屌丝"
        
        # 提取核心爽点动作
        cool_action = "装逼打脸"
        if "国运" in genre:
            cool_action = "一剑秒杀凶兽，百倍具现资源"
        elif "神豪" in genre:
            cool_action = "花钱返利，越花越有钱"
        elif "末日" in genre:
            cool_action = "囤货求生，建立末世帝国"
        
        # 🔥 构建爆款简介（必须包含情绪词和具体数字/场景）
        if "国运" in genre:
            synopsis = f"""【国运禁地，全球直播】
当其他国家派出特种兵、基因战士时，龙国选中的竟是一个{surface_identity}。
全网谩骂："龙国完了！"
直到{protagonist_name}拔出腰间铁剑，一剑斩断S级凶兽...
全球震惊："这特么是{surface_identity}？"

【{gf_core}，越醉越强】
别人求生，他求醉；别人逃跑，他御剑飞行。
当{protagonist_name}{cool_action}时，
全球选手集体破防："这还玩个屁！"

本书又名：《{surface_identity}，一剑开天门》《我在国运禁地当{gf_core.replace('系统', '')}》"""
        
        elif "神豪" in genre:
            synopsis = f"""【花钱百倍返利，越花越有钱】
{protagonist_name}原本是个被前女友甩、被亲戚嘲的穷屌丝。
直到绑定{gf_core}，花钱就能获得百倍返利！

"劳斯莱斯幻影？买！"
"市中心豪宅？买！"
"看不起我的前女友？跪舔也没用，滚！"

当{protagonist_name}用钞票砸翻一切时，
全世界才发现：有钱，真的可以为所欲为！

本书又名：《神豪：从外卖员到全球首富》《我花钱就能变强》"""
        
        elif "末日" in genre:
            synopsis = f"""【末日降临，囤货百亿】
丧尸病毒爆发，世界陷入混乱。
{protagonist_name}却提前觉醒{gf_core}，疯狂囤货百亿物资！

当别人为了一块面包互相残杀时，
他在别墅里吃着牛排喝着红酒；
当别人被丧尸追得满山跑时，
他的安全固若金汤。

【杀伐果断，建立末世帝国】
背叛者，杀！掠夺者，杀！丧尸，杀！
{protagonist_name}要成为这末世唯一的王！

本书又名：《末日：我有无限囤货空间》《我在末世当霸主》"""
        
        elif "奶爸" in genre:
            synopsis = f"""【神级奶爸，萌宝无敌】
{protagonist_name}突然多了一个软萌女儿，还绑定了{gf_core}！

"爸爸，那个坏叔叔欺负我~"
下一秒，反派直接被萌宝的守护灵拍飞。
"爸爸，我想坐大飞机~"
第二天，私人飞机停在楼顶。

【宠娃狂魔，护短到底】
谁敢动我女儿一根头发，我就让他全家后悔来到这个世上！

本书又名：《奶爸：我的女儿有守护灵》《萌宝助攻，奶爸无敌》"""
        
        else:
            # 通用模板
            synopsis = f"""【{gf_core}，逆袭人生】
{protagonist_name}原本是个被人看不起的{surface_identity}。
直到意外获得{gf_core}，从此人生逆转！

{cool_action}，一路逆袭，震惊全场！
曾经看不起他的人，现在跪舔都来不及。

本书又名：《从{surface_identity}到无敌强者》《我有{gf_core}》"""
        
        return synopsis
    
    def _get_fanqie_tags(self, genre: str) -> Dict:
        """
        获取番茄上传标签（参考 plan_generator.py 的预制映射）
        """
        # 判断男女频
        female_keywords = ["奶爸", "萌宝", "甜宠", "重生", "穿越", "快穿", "言情", "娱乐圈"]
        is_female = any(kw in genre for kw in female_keywords)
        gender_key = "female" if is_female else "male"
        
        # 查找预制标签
        tag_mappings = self.FANQIE_TAG_MAPPINGS.get(gender_key, self.FANQIE_TAG_MAPPINGS["male"])
        tags = tag_mappings.get(genre)
        
        # 如果没有精确匹配，尝试模糊匹配
        if not tags:
            for mapped_genre, mapped_tags in tag_mappings.items():
                if any(keyword in genre for keyword in mapped_genre.split("-")):
                    tags = mapped_tags
                    break
        
        # 如果仍然没有匹配，使用默认标签
        if not tags:
            tags = self.DEFAULT_TAGS.get(gender_key, self.DEFAULT_TAGS["male"])
        
        # 🔥 防御性类型处理：确保标签值是列表（严格类型检查）
        themes = tags.get("themes", [])
        if isinstance(themes, dict):
            themes = list(themes.keys())
        elif not isinstance(themes, list):
            themes = [themes] if themes else []
        
        roles = tags.get("roles", [])
        if isinstance(roles, dict):
            roles = list(roles.keys())
        elif not isinstance(roles, list):
            roles = [roles] if roles else []
        
        plots = tags.get("plots", [])
        if isinstance(plots, dict):
            plots = list(plots.keys())
        elif not isinstance(plots, list):
            plots = [plots] if plots else []
        
        # 构建完整标签字典
        return {
            "target_audience": "女频" if is_female else "男频",
            "main_category": tags["main_category"],
            "themes": themes[:3],
            "roles": roles[:3],
            "plots": plots[:3]
        }
    
    def _generate_fallback_fanqie_data(self, plan: Dict, title: str, genre: str) -> Dict:
        """备用方案：使用同样的专业方法生成"""
        return self._generate_fanqie_upload_data(plan)
    
    def _generate_worldview(self) -> Dict:
        """生成世界观（使用基于爆款的Prompt模板）"""
        total_chapters = self.user_choices.get('chapters', 100)
        
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤2）")
            prompt = self._prompt_generator.generate_step2_worldview_prompt(total_chapters=total_chapters)
        else:
            # 从JSON配置加载提示词
            prompt = self._get_step_prompt("step2_worldview")
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤2提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤2-生成世界观")
        self._logger.log_round("generate_worldview", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤2响应接收 | 总对话轮次: {self.session.turn_count}")
        
        try:
            result = self._parse_json_response(response, "worldview")
            # 验证必要字段
            required_fields = ["world_overview", "power_system", "social_structure"]
            missing = [f for f in required_fields if f not in result]
            if missing:
                raise ValueError(f"worldview 缺少必要字段: {missing}")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[对话模式 {self.session_id}] 生成 worldview 失败: {e}")
            raise RuntimeError(f"生成世界观失败: {e}") from e
    
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
            logger.warning(f"[对话模式 {self.session_id}] 模板生成失败，使用配置提示词")
            prompt = self._get_step_prompt("step3_characters", protagonist_name=protagonist_name)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤3提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤3-生成角色")
        self._logger.log_round("generate_characters", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤3响应接收 | 总对话轮次: {self.session.turn_count}")
        
        result = self._parse_json_response(response, "characters")
        
        # 🔥 如果返回空或null，使用简化提示词重试
        if not result:
            logger.warning(f"[对话模式 {self.session_id}] 步骤3返回空，使用简化提示词重试...")
            retry_prompt = self._get_step_prompt("step3_characters_retry", protagonist_name=protagonist_name)
            
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
        total_chapters = self.user_choices.get('chapters', 100)
        
        # 🔥 使用基于爆款分析的Prompt模板
        if self._prompt_generator:
            logger.info(f"[对话模式 {self.session_id}] 使用基于爆款的Prompt模板（步骤4）")
            prompt = self._prompt_generator.generate_step4_growth_prompt(total_chapters=total_chapters)
        else:
            # 从JSON配置加载提示词
            prompt = self._get_step_prompt("step4_growth")
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤4提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤4-生成成长路线")
        self._logger.log_round("generate_growth_plan", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤4响应接收 | 总对话轮次: {self.session.turn_count}")
        
        try:
            result = self._parse_json_response(response, "growth_plan")
            # 验证必要字段
            required_fields = ["protagonist_growth", "ability_system_progression"]
            missing = [f for f in required_fields if f not in result]
            if missing:
                raise ValueError(f"growth_plan 缺少必要字段: {missing}")
            return result
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[对话模式 {self.session_id}] 生成 growth_plan 失败: {e}")
            raise RuntimeError(f"生成成长路线失败: {e}") from e
    
    def _generate_emotion_curve(self) -> List[Dict]:
        """生成情绪曲线（使用基于爆款的Prompt模板）"""
        # 🔥 强制修正：根据字数计算正确的章节数（防止前端传错值）
        from .config import get_config, get_target_words
        target_words = self.user_choices.get('target_words') or get_target_words(self.genre)
        # 确保 target_words 是整数
        if isinstance(target_words, str):
            try:
                target_words = int(target_words)
            except (ValueError, TypeError):
                target_words = get_target_words(self.genre)
        elif not isinstance(target_words, int):
            target_words = int(target_words) if target_words else get_target_words(self.genre)
        
        correct_chapters = target_words // get_config(self.genre)["words_per_chapter"]
        # 确保 correct_chapters 是整数
        if not isinstance(correct_chapters, int):
            correct_chapters = int(correct_chapters)
        
        user_chapters = self.user_choices.get('chapters', 0)
        # 确保 user_chapters 是整数
        if isinstance(user_chapters, str):
            try:
                user_chapters = int(user_chapters)
            except (ValueError, TypeError):
                user_chapters = 0
        elif not isinstance(user_chapters, int):
            user_chapters = int(user_chapters) if user_chapters else 0
        
        if user_chapters and user_chapters != correct_chapters:
            logger.error(f"[🔥步骤5强制修正] {user_chapters} -> {correct_chapters} (基于{target_words}字)")
            self.user_choices['chapters'] = correct_chapters
        
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
                "## 输出格式（严格JSON数组）",
                f"**极其重要**：",
                f"1. 必须返回**完整的{total_chapters}章情绪曲线**，每章都要有数据！",
                f"2. curve数组长度必须等于总章数（{total_chapters}章）",
                f"3. 不能只返回里程碑（如1, 10, 20章），必须每章都有：1, 2, 3...一直到{total_chapters}",
                f"4. 返回格式：{{\"curve\": [{{\"chapter\": 1, ...}}, ...]}}",
                f"",
                f"**错误示例（会被拒绝）**：",
                f"- 只返回12个里程碑：{{\"curve\": [{{\"chapter\":1}}, {{\"chapter\":10}}, ...]}}",
                f"- 返回字典：{{\"curve\": {{\"chapter\": 1}}}}",
                f"",
                f"**正确示例**：",
                f"- 完整的{total_chapters}章：{{\"curve\": [{{\"chapter\":1}}, {{\"chapter\":2}}, ..., {{\"chapter\":{total_chapters}}}]}}",
                f"",
                f"严格要求：",
                "1. curve 必须是数组（[]），不能是字典（{}）",
                f"2. 数组长度必须等于{total_chapters}章",
                "3. 字符串值内部的双引号必须转义为 \\\""
            ]
            prompt = "\n".join(prompt_parts)
        
        logger.info(f"[对话模式 {self.session_id}] 发送步骤5提示词 | 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤5-生成情绪曲线")
        self._logger.log_round("generate_emotion_curve", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤5响应接收 | 总对话轮次: {self.session.turn_count}")
        
        try:
            result = self._parse_json_response(response, "emotion_curve")
            
            # 数据验证
            curve_data = None
            if isinstance(result, dict):
                curve_data = result.get("curve", [])
            elif isinstance(result, list):
                curve_data = result
            else:
                raise ValueError(f"emotion_curve 返回类型错误: {type(result)}")
            
            # 验证数组长度
            if not isinstance(curve_data, list):
                raise ValueError(f"emotion_curve 必须是数组，当前类型: {type(curve_data)}")
            
            if len(curve_data) == 0:
                raise ValueError("emotion_curve 数组为空")
            
            if len(curve_data) != total_chapters:
                logger.warning(f"[对话模式 {self.session_id}] emotion_curve长度({len(curve_data)})与目标章节数({total_chapters})不一致，尝试补全...")
                # 尝试补全或截断
                curve_data = self._normalize_emotion_curve(curve_data, total_chapters)
            
            logger.info(f"[对话模式 {self.session_id}] emotion_curve 生成成功: {len(curve_data)} 章")
            return curve_data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"[对话模式 {self.session_id}] 生成 emotion_curve 失败: {e}")
            raise RuntimeError(f"生成情绪曲线失败: {e}") from e
    
    def _get_default_emotion_curve(self) -> List[Dict]:
        """
        获取默认情绪曲线模板（简化版）
        
        🔥 优化：不再一次性生成200章详细情绪曲线
        详细情绪设计改在战术规划中分批生成（每30章）
        
        Returns:
            基础情绪曲线模板（仅里程碑章节）
        """
        from .config import get_config
        total_chapters = self.user_choices.get('chapters', 200)
        
        # 只生成关键里程碑的情绪标记
        milestones = [
            {"ch": 1, "emotion": "压抑", "intensity": 9, "beat_type": "钩子", "event": "绝望开局+系统觉醒"},
            {"ch": 3, "emotion": "爽快", "intensity": 7, "beat_type": "爽点", "event": "第一次打脸"},
            {"ch": 10, "emotion": "震惊", "intensity": 8, "beat_type": "震惊", "event": "身份小曝光"},
            {"ch": 15, "emotion": "大爽快", "intensity": 9, "beat_type": "高潮", "event": "阶段性大高潮"},
            {"ch": 30, "emotion": "满足", "intensity": 8, "beat_type": "高潮", "event": "第一幕大高潮"},
            {"ch": 60, "emotion": "满足", "intensity": 9, "beat_type": "高潮", "event": "中期大高潮"},
            {"ch": 100, "emotion": "满足", "intensity": 10, "beat_type": "高潮", "event": "全书大高潮"},
        ]
        
        # 过滤超出总章节数的里程碑
        milestones = [m for m in milestones if m["ch"] <= total_chapters]
        
        logger.info(f"[对话模式 {self.session_id}] 使用默认情绪曲线模板: {len(milestones)}个里程碑")
        return milestones
    
    def _normalize_emotion_curve(self, curve: list, target_length: int) -> list:
        """
        标准化情绪曲线长度，使其符合目标章节数
        
        Args:
            curve: 原始情绪曲线数组
            target_length: 目标章节数
            
        Returns:
            标准化后的情绪曲线数组
        """
        if len(curve) == target_length:
            # 确保所有章节都有新字段
            for i, item in enumerate(curve):
                if "climax_type" not in item:
                    item["climax_type"] = ""
                if "climax_subtype" not in item:
                    item["climax_subtype"] = ""
                # 统一章节号字段
                if "chapter" in item and "ch" not in item:
                    item["ch"] = item.pop("chapter")
            return curve
        
        if len(curve) < target_length:
            # 需要补全 - 复制最后一个元素
            last_item = curve[-1] if curve else {
                "ch": 1, "emotion": "期待", "intensity": 5,
                "beat_type": "铺垫", "climax_type": "", "climax_subtype": "",
                "event": "", "purpose": ""
            }
            for i in range(len(curve), target_length):
                new_item = last_item.copy()
                new_item["ch"] = i + 1
                curve.append(new_item)
            logger.info(f"[对话模式 {self.session_id}] emotion_curve 已补全至 {target_length} 章")
        else:
            # 需要截断
            curve = curve[:target_length]
            logger.info(f"[对话模式 {self.session_id}] emotion_curve 已截断至 {target_length} 章")
        
        # 确保所有章节都有新字段
        for item in curve:
            if "climax_type" not in item:
                item["climax_type"] = ""
            if "climax_subtype" not in item:
                item["climax_subtype"] = ""
            if "beat_type" not in item:
                item["beat_type"] = "铺垫"
            if "event" not in item:
                item["event"] = ""
            if "purpose" not in item:
                item["purpose"] = ""
            # 统一章节号字段
            if "chapter" in item and "ch" not in item:
                item["ch"] = item.pop("chapter")
        
        return curve
    
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
    
    def _generate_stage_goals(self, previous_results: Dict) -> List[Dict]:
        """
        生成阶段目标（步骤5的一部分）
        
        🔥 修正：只生成阶段目标（stage_goals），不生成战术规划（tactical_plan）
        战术规划由 TacticalPlanner 在生成阶段动态生成，避免与阶段目标冲突
        
        阶段目标特点：
        - 不绑定具体章数（柔性目标）
        - 定义关键交付物和成功标准
        - 系统根据实际进度自动推进
        """
        title = self.user_choices.get('title', '未命名')
        protagonist_name = self.user_choices.get('protagonist_name', '主角')
        
        # 🔥 强制修正：确保章节数正确（双重保险）
        from .config import get_config, get_target_words
        target_words = self.user_choices.get('target_words') or get_target_words(self.genre)
        # 确保 target_words 是整数
        if isinstance(target_words, str):
            try:
                target_words = int(target_words)
            except (ValueError, TypeError):
                target_words = get_target_words(self.genre)
        elif not isinstance(target_words, int):
            target_words = int(target_words) if target_words else get_target_words(self.genre)
        
        correct_chapters = target_words // get_config(self.genre)["words_per_chapter"]
        # 确保 correct_chapters 是整数
        if not isinstance(correct_chapters, int):
            correct_chapters = int(correct_chapters)
        
        user_chapters = self.user_choices.get('chapters', 0)
        # 确保 user_chapters 是整数
        if isinstance(user_chapters, str):
            try:
                user_chapters = int(user_chapters)
            except (ValueError, TypeError):
                user_chapters = 0
        elif not isinstance(user_chapters, int):
            user_chapters = int(user_chapters) if user_chapters else 0
        
        if user_chapters and user_chapters != correct_chapters:
            logger.error(f"[🔥步骤5B强制修正] {user_chapters} -> {correct_chapters} (基于{target_words}字)")
            self.user_choices['chapters'] = correct_chapters
        
        # 🔥 使用 user_choices 中的章节数
        total_chapters = self.user_choices.get('chapters', 200)
        # 确保 total_chapters 是整数
        if isinstance(total_chapters, str):
            try:
                total_chapters = int(total_chapters)
            except (ValueError, TypeError):
                total_chapters = 200
        elif not isinstance(total_chapters, int):
            total_chapters = int(total_chapters) if total_chapters else 200
        emotion_curve_count = len(previous_results.get('emotion_curve', []))
        if emotion_curve_count != total_chapters:
            logger.warning(f"[步骤5B] emotion_curve长度({emotion_curve_count})与目标章节数({total_chapters})不一致，使用目标章节数")
        
        # 🔥 安全获取里程碑（处理字典/列表类型问题）
        # 支持两种字段名：milestones 或 protagonist_growth
        growth_plan = previous_results.get('global_growth_plan', {})
        milestones = growth_plan.get('milestones') or growth_plan.get('protagonist_growth', [])
        
        # 严格类型检查：确保 milestones 是列表
        if isinstance(milestones, dict):
            logger.warning(f"[对话模式 {self.session_id}] milestones 是字典而非列表，转换为单元素列表")
            milestones = [milestones]
        elif not isinstance(milestones, list):
            milestones = []
        
        if milestones:
            _milestones_text = json.dumps(milestones[:3], ensure_ascii=False)
        else:
            _milestones_text = "[]"
        
        # 构建基于前4步产物的提示词
        prompt = f"""请执行【步骤5B：生成阶段目标】

基于前面步骤已生成的完整设定，现在创建阶段目标（stage_goals）。

## 已完成的设定（上下文中的产物）

### 1. 核心方案
书名：{title}
主角：{protagonist_name}
金手指：{json.dumps(previous_results.get('plan', {}).get('golden_finger', {}), ensure_ascii=False)[:500]}

### 2. 世界观概要
{previous_results.get('core_worldview', {}).get('world_overview', '国运禁地求生')}

### 3. 成长路线里程碑
{_milestones_text}

### 4. 总章数
总章数为 {total_chapters} 章

## 你需要生成

### 阶段目标（stage_goals）
根据总章数 {total_chapters}，定义3-5个阶段目标，每个目标包含：
- goal_id: 目标ID（如G1, G2, G3）
- description: 目标描述（清晰说明这一阶段要达成什么）
- expected_chapters: 预估章数范围（如"10-20章"，仅参考，非强制）
- key_deliverables: 关键交付物列表（必须完成的具体事项）
- success_criteria: 完成标准（可衡量的指标）

**重要原则**：
1. 阶段目标不绑定具体章数！如果第3章就完成了G1的目标，就直接进入G2
2. 每个阶段目标必须有明确的成功标准（如"扮演度≥30%"）
3. 阶段目标之间要有递进关系，不能重复
4. **必须根据总章数 {total_chapters} 来划分阶段范围**！

**阶段数量与划分指导**（根据总章数动态调整）：
- 如果 ≥500章：6个阶段，每个阶段约80-100章
- 如果 300-499章：5个阶段 (1-40, 41-100, 101-180, 181-250, 251-总章数)
- 如果 200-299章：5个阶段 (1-30, 31-70, 71-120, 121-170, 171-总章数)
- 如果 150-199章：4个阶段 (1-25, 26-55, 56-100, 101-总章数)
- 如果 80-149章：3个阶段，均匀划分
- 如果 <80章：2-3个阶段，根据篇幅调整

**关键原则**：
- 阶段数量 = 3-6个，根据总章数决定
- 每个阶段跨度不要太短（至少20章以上）
- 每个阶段必须有明确的扮演度目标和剧情里程碑

## 输出格式（严格JSON数组）

**必须返回JSON数组格式**：
```json
{{
  "stage_goals": [
    {{
      "goal_id": "G1",
      "description": "建立主角形象，首次展现实力",
      "expected_chapters": "1-X章",
      "key_deliverables": ["扮演度达到30%", "获得第一个强力技能", "震惊全场"],
      "success_criteria": "扮演度≥30%，至少1次全场震惊"
    }},
    {{
      "goal_id": "G2",
      "description": "快速成长，建立盟友",
      "expected_chapters": "X-Y章",
      "key_deliverables": ["扮演度达到50%", "收服第一个盟友", "首次击败强敌"],
      "success_criteria": "扮演度≥50%，盟友数量≥1"
    }}
  ]
}}
```

**严格警告**：
1. **stage_goals 必须是数组（方括号）不是字典（花括号）！**
2. 错误示例（会被拒绝）：stage_goals后面跟花括号包裹的对象
3. 正确示例（必须）：stage_goals后面跟方括号包裹的数组
4. 必须按照总章数 {total_chapters} 调整阶段范围，不要生成固定的100章划分！
5. 字符串值内部的双引号必须转义为 \\"

只返回JSON，不要其他说明。"""

        logger.info(f"[对话模式 {self.session_id}] 发送步骤5B提示词（阶段目标）| 当前消息历史: {len(self.session.messages)}条")
        response = self.session.send_message(prompt, temperature=0.85, purpose="步骤5B-生成阶段目标")
        self._logger.log_round("generate_stage_goals", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
        logger.info(f"[对话模式 {self.session_id}] 步骤5B响应接收 | 总对话轮次: {self.session.turn_count}")
        
        try:
            result = self._parse_json_response(response, "stage_goals")
            
            # 解析返回格式
            stage_goals = None
            if isinstance(result, dict) and "stage_goals" in result:
                sg = result["stage_goals"]
                stage_goals = sg if isinstance(sg, list) else [sg]
            elif isinstance(result, list):
                stage_goals = result
            else:
                raise ValueError(f"stage_goals 返回格式错误: {type(result)}")
            
            # 验证数组长度
            if len(stage_goals) == 0:
                raise ValueError("stage_goals 数组为空")
            
            logger.info(f"[对话模式 {self.session_id}] 生成 stage_goals 成功: {len(stage_goals)} 个阶段")
            return stage_goals
            
        except (json.JSONDecodeError, ValueError) as e:
            # 获取总章数用于默认目标
            total_chapters = len(previous_results.get('emotion_curve', []))
            logger.error(f"[对话模式 {self.session_id}] 生成 stage_goals 失败: {e}，使用默认值")
            return self._get_default_stage_goals(total_chapters)
    
    def _get_default_stage_goals(self, total_chapters: int = 100) -> List[Dict]:
        """获取默认阶段目标（当AI生成失败时使用）
        
        Args:
            total_chapters: 总章数，根据此值动态计算阶段数量和范围
        """
        # 根据总章数决定阶段数量和每个阶段的范围
        if total_chapters >= 500:
            # 超长篇：6个阶段
            num_stages = 6
            stage_size = total_chapters // 6
            ranges = [(i * stage_size + 1, (i + 1) * stage_size if i < 5 else total_chapters) 
                     for i in range(6)]
        elif total_chapters >= 300:
            # 长篇：5个阶段
            num_stages = 5
            ranges = [(1, 40), (41, 100), (101, 180), (181, 250), (251, total_chapters)]
        elif total_chapters >= 200:
            # 中长篇：4-5个阶段
            num_stages = 5
            ranges = [(1, 30), (31, 70), (71, 120), (121, 170), (171, total_chapters)]
        elif total_chapters >= 150:
            # 中篇：4个阶段
            num_stages = 4
            ranges = [(1, 25), (26, 55), (56, 100), (101, total_chapters)]
        elif total_chapters >= 80:
            # 中短篇：3个阶段
            num_stages = 3
            mid = total_chapters // 3
            ranges = [(1, mid), (mid + 1, mid * 2), (mid * 2 + 1, total_chapters)]
        else:
            # 短篇：2-3个阶段
            num_stages = 3 if total_chapters >= 50 else 2
            if num_stages == 3:
                mid = total_chapters // 3
                ranges = [(1, mid), (mid + 1, mid * 2), (mid * 2 + 1, total_chapters)]
            else:
                mid = total_chapters // 2
                ranges = [(1, mid), (mid + 1, total_chapters)]
        
        # 阶段定义模板
        stage_templates = [
            {
                "description": "建立主角形象，首次展现实力",
                "deliverables": ["扮演度达到20%", "获得第一个强力技能", "震惊全场"],
                "criteria": "扮演度≥20%，至少1次全场震惊",
                "power": "S级"
            },
            {
                "description": "快速成长，建立盟友",
                "deliverables": ["扮演度达到40%", "收服第一个盟友", "首次击败强敌"],
                "criteria": "扮演度≥40%，盟友数量≥1",
                "power": "SS级"
            },
            {
                "description": "国运争霸，区域崛起",
                "deliverables": ["扮演度达到60%", "龙国区域第一", "击败区域强敌"],
                "criteria": "扮演度≥60%，区域排名No.1",
                "power": "SSS级"
            },
            {
                "description": "全球争霸，登顶巅峰",
                "deliverables": ["扮演度达到80%", "成为全球第一", "击败多国联盟"],
                "criteria": "扮演度≥80%，全球排名No.1",
                "power": "SSS+级"
            },
            {
                "description": "文明跃迁，星际接触" if total_chapters >= 300 else "终极对决，守护龙国",
                "deliverables": ["扮演度达到90%", "接触更高维度" if total_chapters >= 300 else "击败终极BOSS", "开启新篇章"],
                "criteria": "扮演度≥90%，掌控全局",
                "power": "神级"
            },
            {
                "description": "主宰万界，圆满结局",
                "deliverables": ["扮演度达到100%", "成为禁地主宰", "龙国永世长存"],
                "criteria": "扮演度≥95%，圆满结局",
                "power": "超神级"
            }
        ]
        
        # 生成阶段目标
        goals = []
        for i in range(num_stages):
            template = stage_templates[i]
            start, end = ranges[i]
            goals.append({
                "goal_id": f"G{i+1}",
                "description": template["description"],
                "expected_chapters": f"{start}-{end}章",
                "key_deliverables": template["deliverables"],
                "success_criteria": template["criteria"]
            })
        
        return goals
    
    def _parse_json_response(self, response: str, step_name: str, max_retries: int = 3) -> Any:
        """
        解析JSON响应，带重试机制
        
        Args:
            response: API返回的响应
            step_name: 步骤名称（用于日志）
            max_retries: 最大重试次数
            
        Returns:
            解析后的JSON对象
            
        Raises:
            JSONDecodeError: 解析失败且重试次数用尽
        """
        # 🔥 修复：如果API已经返回了解析后的对象，直接使用
        if isinstance(response, dict):
            logger.info(f"[DEBUG][{step_name}] API返回已是dict，直接使用")
            self._log_response_data(step_name, response)
            return response
        if isinstance(response, list):
            logger.info(f"[DEBUG][{step_name}] API返回已是list，直接使用")
            return response
        
        if not response:
            raise json.JSONDecodeError(f"步骤 {step_name} 返回空响应", "", 0)
        
        import re
        
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # 尝试直接解析
                try:
                    result = json.loads(response)
                    logger.info(f"[DEBUG][{step_name}] JSON直接解析成功（尝试{attempt+1}/{max_retries}），返回类型: {type(result)}")
                    self._log_response_data(step_name, result)
                    return result
                except json.JSONDecodeError as e:
                    last_error = e
                    # 只有在不是Markdown格式时才记录为警告
                    if '```' not in response and attempt == 0:
                        logger.warning(f"[DEBUG][{step_name}] JSON直接解析失败: {e}")
                
                # 尝试提取JSON块
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'```\s*(.*?)\s*```', response, re.DOTALL)
                candidate = json_match.group(1) if json_match else None
                
                # 如果没有代码块，尝试提取花括号内容
                if not candidate:
                    brace_match = re.search(r'\{[\s\S]*\}', response, re.DOTALL)
                    candidate = brace_match.group(0) if brace_match else None
                
                if candidate:
                    # 先尝试直接解析提取的内容
                    try:
                        result = json.loads(candidate)
                        extraction_source = "Markdown代码块" if json_match else "花括号"
                        logger.info(f"[DEBUG][{step_name}] 从{extraction_source}提取并解析成功，返回类型: {type(result)}")
                        self._log_response_data(step_name, result)
                        return result
                    except json.JSONDecodeError as e:
                        last_error = e
                    
                    # 🔥 智能修复常见的AI JSON错误
                    fixed = self._fix_json_string(candidate)
                    try:
                        result = json.loads(fixed)
                        logger.info(f"[DEBUG][{step_name}] JSON智能修复后解析成功，返回类型: {type(result)}")
                        self._log_response_data(step_name, result)
                        return result
                    except json.JSONDecodeError as e:
                        last_error = e
                
                # 解析失败，如果还有重试机会，请求AI重新生成
                if attempt < max_retries - 1:
                    logger.warning(f"[DEBUG][{step_name}] 解析失败，笮{attempt+2}次重试...")
                    retry_prompt = f"""之前的响应格式错误，无法解析为JSON。
错误信息: {str(last_error)}

请重新返回符合JSON格式的数据，要求：
1. 必须是标准JSON格式
2. 不要有多余的前后文本
3. 字符串中的引号必须正确转义

请直接返回JSON，不要用```json包裹。"""
                    
                    response = self.session.send_message(
                        retry_prompt, 
                        temperature=0.7, 
                        purpose=f"{step_name}-重试{attempt+2}"
                    )
                    self._logger.log_round(f"{step_name}_retry_{attempt+2}", self.session.messages.copy(), response if isinstance(response, str) else json.dumps(response))
                
            except Exception as e:
                last_error = e
                logger.error(f"[DEBUG][{step_name}] 第{attempt+1}次尝试异常: {e}")
        
        # 所有重试都失败
        error_msg = f"无法解析步骤 {step_name} 的响应，已重试{max_retries}次. 最后错误: {last_error}"
        logger.error(error_msg)
        raise json.JSONDecodeError(error_msg, response[:500] if response else "", 0)
    
    def _log_response_data(self, step_name: str, data: Any):
        """记录响应数据的关键字段类型（用于debug）"""
        try:
            if isinstance(data, dict):
                # 记录关键字段的类型
                type_info = {}
                for key in ['stage_goals', 'emotion_curve', 'stage_goal_issues', 
                           'emotion_issues', 'gf_issues', 'milestones']:
                    if key in data:
                        val = data[key]
                        type_info[key] = type(val).__name__
                        if isinstance(val, list):
                            type_info[f"{key}_len"] = len(val)
                        elif isinstance(val, dict):
                            type_info[f"{key}_keys"] = list(val.keys())[:3]
                
                if type_info:
                    logger.info(f"[DEBUG][{step_name}] 数据字段类型: {type_info}")
        except Exception as e:
            logger.warning(f"[DEBUG] 记录数据类型时出错: {e}")
    
    def _fix_json_string(self, json_str: str) -> str:
        """智能修复AI返回的常见JSON格式错误 - 仅基本修复"""
        import re

        s = json_str.strip().lstrip('\ufeff').lstrip('\u3000')

        # 1. 修复中文标点（AI经常混淆中英文标点）
        s = s.replace('，', ',').replace('。', '.').replace('：', ':')
        s = s.replace('"', '"').replace('"', '"')

        # 2. 修复尾部逗号（对象和数组）
        s = re.sub(r',(\s*[}\]])', r'\1', s)

        # 注意：不修复内部引号问题，让AI通过重试学习正确格式
        return s

    def _bestseller_alignment_check(self, previous_results: Dict) -> Dict:
        """
        步骤6: 爆款对齐检查与优化
        
        对比一阶段产物与爆款公式，识别偏差并优化
        返回优化后的结果和优化报告
        """
        logger.info(f"[对话模式 {self.session_id}] 开始爆款对齐检查...")
        
        # 🔥 DEBUG: 记录previous_results中关键字段的类型
        debug_info = {}
        for key in ['stage_goals', 'emotion_curve']:
            if key in previous_results:
                val = previous_results[key]
                debug_info[key] = type(val).__name__
                if isinstance(val, list):
                    debug_info[f"{key}_len"] = len(val)
        logger.info(f"[DEBUG][_bestseller_alignment_check] previous_results类型: {debug_info}")
        
        # 如果没有爆款分析数据，跳过检查
        if not self._prompt_generator:
            logger.warning(f"[对话模式 {self.session_id}] 无Prompt生成器，跳过爆款对齐检查")
            return {"alignment_report": {"skipped": True, "reason": "无爆款分析数据"}}
        
        # 获取爆款分析数据
        bestseller_analysis = self._prompt_generator.analysis
        
        # 1. 检查情绪曲线是否符合爆款节奏
        emotion_curve = previous_results.get('emotion_curve', [])
        # 🔥 DEBUG: 检查 emotion_curve 类型
        logger.info(f"[DEBUG] emotion_curve 类型: {type(emotion_curve).__name__}, "
                   f"长度: {len(emotion_curve) if isinstance(emotion_curve, (list, dict)) else 'N/A'}")
        if not isinstance(emotion_curve, list):
            logger.error(f"[DEBUG] emotion_curve 不是列表！实际内容: {emotion_curve}")
            emotion_curve = []
        emotion_issues = self._check_emotion_curve_bestseller_gap(
            emotion_curve, 
            bestseller_analysis
        )
        
        # 2. 检查阶段目标是否符合爆款结构
        stage_goals = previous_results.get('stage_goals', [])
        stage_goal_issues = self._check_stage_goals_bestseller_gap(
            stage_goals,
            bestseller_analysis
        )
        
        # 3. 检查金手指设计是否爆款化
        golden_finger = previous_results.get('plan', {}).get('golden_finger', {})
        gf_issues = self._check_golden_finger_bestseller_gap(
            golden_finger,
            bestseller_analysis
        )
        
        # 🔥 DEBUG: 记录issues的类型
        logger.info(f"[DEBUG] issues类型 - emotion_issues: {type(emotion_issues).__name__}, "
                   f"stage_goal_issues: {type(stage_goal_issues).__name__}, "
                   f"gf_issues: {type(gf_issues).__name__}")
        
        # 4. 生成对齐报告
        total_issues = len(emotion_issues) + len(stage_goal_issues) + len(gf_issues)
        alignment_report = {
            "checked_at": datetime.now().isoformat(),
            "total_issues": total_issues,
            "emotion_issues_count": len(emotion_issues),
            "stage_goal_issues_count": len(stage_goal_issues),
            "golden_finger_issues_count": len(gf_issues),
            "emotion_issues": emotion_issues,
            "stage_goal_issues": stage_goal_issues,
            "golden_finger_issues": gf_issues,
            "skipped": False
        }
        
        # 🔥 输出检查摘要（让用户清楚看到检查结果）
        logger.info(f"[对话模式 {self.session_id}] ═══════════════════════════════════════")
        logger.info(f"[对话模式 {self.session_id}] 【步骤6 爆款对齐检查摘要】")
        logger.info(f"[对话模式 {self.session_id}]   情绪曲线检查: {len(emotion_issues)} 个问题")
        logger.info(f"[对话模式 {self.session_id}]   阶段目标检查: {len(stage_goal_issues)} 个问题")
        logger.info(f"[对话模式 {self.session_id}]   金手指检查:   {len(gf_issues)} 个问题")
        logger.info(f"[对话模式 {self.session_id}]   总计: {total_issues} 个问题")
        
        # 输出详细问题（前3个）
        if emotion_issues:
            for i, issue in enumerate(emotion_issues[:3], 1):
                ch = issue.get('chapter', 'N/A')
                issue_type = issue.get('type', 'unknown')
                severity = issue.get('severity', 'medium')
                logger.info(f"[对话模式 {self.session_id}]   ⚠️  情绪问题{i}: 第{ch}章 [{issue_type}] (严重度:{severity})")
        if stage_goal_issues:
            for i, issue in enumerate(stage_goal_issues[:3], 1):
                stage = issue.get('stage', 'N/A')
                issue_type = issue.get('type', 'unknown')
                logger.info(f"[对话模式 {self.session_id}]   ⚠️  阶段问题{i}: {stage} [{issue_type}]")
        if gf_issues:
            for i, issue in enumerate(gf_issues[:3], 1):
                issue_type = issue.get('type', 'unknown')
                logger.info(f"[对话模式 {self.session_id}]   ⚠️  金手指问题{i}: [{issue_type}]")
        logger.info(f"[对话模式 {self.session_id}] ═══════════════════════════════════════")
        
        # 5. 如果有偏差，进行优化
        if emotion_issues or stage_goal_issues or gf_issues:
            logger.info(f"[对话模式 {self.session_id}] 对齐检查发现 {total_issues} 个问题，开始AI优化...")
            optimized = self._optimize_for_bestseller(
                previous_results,
                emotion_issues,
                stage_goal_issues,
                gf_issues,
                bestseller_analysis
            )
            optimized["alignment_report"] = alignment_report
            
            # 输出优化结果摘要
            logger.info(f"[对话模式 {self.session_id}] ═══════════════════════════════════════")
            logger.info(f"[对话模式 {self.session_id}] 【步骤6 爆款对齐优化完成】")
            if 'emotion_curve' in optimized:
                logger.info(f"[对话模式 {self.session_id}]   ✅ 情绪曲线已优化")
            if 'stage_goals' in optimized:
                logger.info(f"[对话模式 {self.session_id}]   ✅ 阶段目标已优化")
            if 'plan' in optimized and 'golden_finger' in optimized.get('plan', {}):
                logger.info(f"[对话模式 {self.session_id}]   ✅ 金手指已优化")
            logger.info(f"[对话模式 {self.session_id}] ═══════════════════════════════════════")
            return optimized
        
        logger.info(f"[对话模式 {self.session_id}] ✅ 对齐检查通过，无需优化（所有指标符合爆款公式）")
        return {"alignment_report": alignment_report}
    
    def _check_emotion_curve_bestseller_gap(self, emotion_curve: List[Dict], 
                                             bestseller_analysis: Dict) -> List[Dict]:
        """检查情绪曲线与爆款的差距"""
        issues = []
        
        # 严格类型检查：必须是列表
        if not isinstance(emotion_curve, list):
            raise TypeError(f"emotion_curve 必须是列表，实际类型: {type(emotion_curve).__name__}")
        
        if not emotion_curve:
            issues.append({
                "type": "missing_emotion_curve",
                "description": "情绪曲线为空",
                "severity": "high"
            })
            return issues
        
        # 获取爆款情绪节奏模板
        bs_emotion_template = bestseller_analysis.get('emotion_curve', {})
        
        # 检查前30章（黄金期）的情绪节奏
        for i, point in enumerate(emotion_curve[:30]):
            ch_num = point.get('chapter', i+1)
            emotion = point.get('emotion', '')
            intensity = point.get('intensity', 0)
            
            # 获取期望的爆款情绪（如果存在）
            bs_point = bs_emotion_template.get(str(ch_num), {})
            if not bs_point and isinstance(bs_emotion_template, list) and i < len(bs_emotion_template):
                bs_point = bs_emotion_template[i]
            
            bs_emotion = bs_point.get('emotion', '') if isinstance(bs_point, dict) else ''
            bs_intensity = bs_point.get('intensity', 0) if isinstance(bs_point, dict) else 0
            
            # 检查情绪类型偏差（仅前10章严格检查）
            if ch_num <= 10 and bs_emotion and emotion != bs_emotion:
                # 允许类似情绪的替换（如"压抑"和"紧张"算同类）
                similar_emotions = [['压抑', '紧张', '绝望'], ['兴奋', '爽快', '振奋'], ['震惊', '震撼']]
                is_similar = any(emotion in group and bs_emotion in group for group in similar_emotions)
                if not is_similar:
                    issues.append({
                        "type": "emotion_mismatch",
                        "chapter": ch_num,
                        "current": emotion,
                        "expected": bs_emotion,
                        "severity": "high"
                    })
            
            # 检查情绪强度偏差
            if bs_intensity and abs(intensity - bs_intensity) > 2:
                issues.append({
                    "type": "intensity_mismatch",
                    "chapter": ch_num,
                    "current": intensity,
                    "expected": bs_intensity,
                    "severity": "medium" if ch_num > 10 else "high"
                })
        
        # 检查5章循环节奏（压抑→紧张→反转→震惊→期待）
        cycle_issues = self._check_5_chapter_cycle(emotion_curve[:30])
        issues.extend(cycle_issues)
        
        # 检查爽点密度（每章至少1个高潮）
        try:
            climax_count = sum(1 for p in emotion_curve if isinstance(p, dict) and p.get('intensity', 0) >= 7)
            total_chapters = len(emotion_curve) if isinstance(emotion_curve, (list, tuple)) else 0
            climax_ratio = (climax_count / total_chapters) if total_chapters > 0 else 0.0
            
            if climax_ratio < 0.5:  # 至少50%的章有高情绪
                issues.append({
                    "type": "low_climax_density",
                    "current_ratio": f"{climax_ratio:.1%}",
                    "expected_ratio": ">=50%",
                    "current_count": f"{climax_count}/{total_chapters}",
                    "severity": "high"
                })
        except Exception as e:
            logger.warning(f"[对话模式 {self.session_id}] 检查爽点密度时出错: {e}")
        
        return issues
    
    def _check_5_chapter_cycle(self, emotion_curve: List[Dict]) -> List[Dict]:
        """检查5章情绪循环节奏"""
        issues = []
        
        if len(emotion_curve) < 5:
            return issues
        
        # 期望的5章循环：压抑(7) → 紧张/嘲讽(8) → 反转/爆发(9) → 震惊(8) → 期待(6)
        expected_cycle = [
            {'emotion': '压抑', 'min_intensity': 6, 'max_intensity': 8},
            {'emotion': '紧张', 'min_intensity': 7, 'max_intensity': 9},  # 或嘲讽
            {'emotion': '反转', 'min_intensity': 8, 'max_intensity': 10}, # 或爆发
            {'emotion': '震惊', 'min_intensity': 7, 'max_intensity': 9},
            {'emotion': '期待', 'min_intensity': 5, 'max_intensity': 7}
        ]
        
        # 检查前20章的循环
        for start in range(0, min(20, len(emotion_curve)), 5):
            cycle = emotion_curve[start:start+5]
            if len(cycle) < 5:
                break
            
            for i, (point, expected) in enumerate(zip(cycle, expected_cycle)):
                ch_num = point.get('chapter', start + i + 1)
                emotion = point.get('emotion', '')
                intensity = point.get('intensity', 0)
                
                # 检查情绪类型（前3章严格检查）
                if i < 3:
                    expected_emotions = [expected['emotion']]
                    if expected['emotion'] == '紧张':
                        expected_emotions.extend(['嘲讽', '质疑', '挑衅'])
                    elif expected['emotion'] == '反转':
                        expected_emotions.extend(['爆发', '反击', '打脸'])
                    
                    if emotion not in expected_emotions:
                        issues.append({
                            "type": "cycle_emotion_mismatch",
                            "chapter": ch_num,
                            "position_in_cycle": i + 1,
                            "current_emotion": emotion,
                            "expected_emotions": expected_emotions,
                            "severity": "medium"
                        })
                
                # 检查强度范围
                if intensity < expected['min_intensity'] or intensity > expected['max_intensity']:
                    issues.append({
                        "type": "cycle_intensity_out_of_range",
                        "chapter": ch_num,
                        "current_intensity": intensity,
                        "expected_range": f"{expected['min_intensity']}-{expected['max_intensity']}",
                        "severity": "low"
                    })
        
        return issues
    
    def _check_stage_goals_bestseller_gap(self, stage_goals: List[Dict],
                                           bestseller_analysis: Dict) -> List[Dict]:
        """检查阶段目标与爆款的差距"""
        issues = []
        
        # 🔥 安全处理：确保 stage_goals 是列表
        if isinstance(stage_goals, dict):
            # 如果AI返回的是字典（如 {"stage_goals": [...]}），尝试提取列表
            if 'stage_goals' in stage_goals:
                stage_goals = stage_goals['stage_goals']
            else:
                # 将整个字典作为单元素列表
                stage_goals = [stage_goals]
            logger.warning(f"[对话模式 {self.session_id}] stage_goals 是字典，已转换为列表")
        elif not isinstance(stage_goals, list):
            logger.error(f"[对话模式 {self.session_id}] stage_goals 类型异常: {type(stage_goals).__name__}，返回空issues")
            return issues
        
        if not stage_goals:
            issues.append({
                "type": "missing_stage_goals",
                "description": "阶段目标为空",
                "severity": "high"
            })
            return issues
        
        # 获取爆款的阶段性节奏
        bs_stages = bestseller_analysis.get('stage_goals', [])
        
        # 检查阶段数量
        if len(stage_goals) < 3:
            issues.append({
                "type": "insufficient_stages",
                "current_count": len(stage_goals),
                "expected_count": "3-6",
                "severity": "medium"
            })
        
        # 检查每个阶段的关键交付物是否爆款化
        climax_keywords = ['震惊', '震撼', '全场', '吊打', '碾压', '曝光', ' reveal', '反转', '爆发']
        
        for i, goal in enumerate(stage_goals):
            # 🔥 防御性类型处理：确保 goal 是字典
            if not isinstance(goal, dict):
                logger.warning(f"[对话模式 {self.session_id}] stage_goals[{i}] 不是字典，类型: {type(goal)}，跳过")
                continue
            goal_id = goal.get('goal_id', f'G{i+1}')
            description = goal.get('description', '')
            deliverables = goal.get('key_deliverables', [])
            
            # 检查描述中是否有爽点关键词
            has_climax_in_desc = any(k in description for k in climax_keywords)
            
            # 检查交付物中是否有爽点
            has_climax_in_deliverables = any(
                any(k in d for k in climax_keywords) 
                for d in deliverables
            )
            
            if not has_climax_in_desc and not has_climax_in_deliverables:
                issues.append({
                    "type": "missing_climax_in_stage",
                    "stage": goal_id,
                    "description": description[:50],
                    "suggestion": f"阶段{goal_id}缺少明确的爽点/高潮交付物，建议添加如'震惊全场'、'首次展现实力'等",
                    "severity": "high"
                })
            
            # 检查是否有具体的成功标准
            success_criteria = goal.get('success_criteria', '')
            if not success_criteria or len(success_criteria) < 10:
                issues.append({
                    "type": "weak_success_criteria",
                    "stage": goal_id,
                    "current": success_criteria,
                    "suggestion": "添加可衡量的成功标准，如'扮演度≥30%'、'获得X个技能'等",
                    "severity": "medium"
                })
        
        return issues
    
    def _check_golden_finger_bestseller_gap(self, golden_finger: Dict,
                                             bestseller_analysis: Dict) -> List[Dict]:
        """检查金手指设计是否爆款化"""
        issues = []
        
        if not golden_finger:
            issues.append({
                "type": "missing_golden_finger",
                "description": "金手指设计为空",
                "severity": "high"
            })
            return issues
        
        # 获取爆款金手指公式
        bs_gf_formula = bestseller_analysis.get('golden_finger_formula', '')
        
        # 检查金手指名称/概念
        gf_name = golden_finger.get('name', '') or golden_finger.get('concept', '')
        if not gf_name or len(gf_name) < 3:
            issues.append({
                "type": "weak_gf_name",
                "issue": "金手指名称/概念不够具体",
                "suggestion": "给金手指一个具体、有记忆点的名称",
                "severity": "medium"
            })
        
        # 检查金手指是否有层次感（成长空间）
        growth_curve = golden_finger.get('growth_curve', [])
        stages = golden_finger.get('stages', [])
        
        if len(growth_curve) < 3 and len(stages) < 3:
            issues.append({
                "type": "insufficient_gf_depth",
                "issue": "金手指缺乏层次感和成长空间",
                "current_stages": max(len(growth_curve), len(stages)),
                "suggestion": "建议设计3-5个成长阶段，如'解锁→熟练→精通→大师→传说'",
                "severity": "high"
            })
        
        # 检查是否有具体的数值体系
        numeric_system = golden_finger.get('numeric_system', {})
        if not numeric_system:
            # 检查是否有其他形式的数值
            has_numeric = any(k in str(golden_finger) for k in ['数值', '等级', '经验', '积分', '点数'])
            if not has_numeric:
                issues.append({
                    "type": "missing_numeric_system",
                    "issue": "金手指缺乏具体数值体系，不够直观",
                    "suggestion": "添加数值化指标，如'熟练度0-100'、'等级Lv.1-10'等",
                    "severity": "medium"
                })
        
        # 检查是否有独特的触发机制
        trigger = golden_finger.get('trigger_mechanism', '')
        if not trigger or trigger in ['自动触发', '被动触发', '随时可用']:
            issues.append({
                "type": "weak_trigger",
                "issue": "金手指触发机制缺乏创意或限制",
                "current_trigger": trigger,
                "suggestion": "设计有创意的触发条件，如'醉酒状态下触发'、'每日限时触发'等",
                "severity": "medium"
            })
        
        # 检查是否有独特的副作用或限制（增加戏剧性）
        limitations = golden_finger.get('limitations', []) or golden_finger.get('side_effects', [])
        if not limitations:
            issues.append({
                "type": "missing_limitations",
                "issue": "金手指没有副作用或限制，缺乏戏剧性",
                "suggestion": "添加限制条件，如'每日使用次数限制'、'使用后虚弱'、'暴露身份风险'等",
                "severity": "low"
            })
        
        return issues
    
    def _optimize_for_bestseller(self, previous_results: Dict,
                                  emotion_issues: List[Dict],
                                  stage_goal_issues: List[Dict],
                                  gf_issues: List[Dict],
                                  bestseller_analysis: Dict) -> Dict:
        """基于爆款数据优化一阶段产物"""
        
        # 🔥 严格类型检查：确保所有 issues 都是列表，否则报错
        if not isinstance(emotion_issues, list):
            raise TypeError(f"emotion_issues 必须是列表，实际类型: {type(emotion_issues).__name__}, 内容: {emotion_issues}")
        if not isinstance(stage_goal_issues, list):
            raise TypeError(f"stage_goal_issues 必须是列表，实际类型: {type(stage_goal_issues).__name__}, 内容: {stage_goal_issues}")
        if not isinstance(gf_issues, list):
            raise TypeError(f"gf_issues 必须是列表，实际类型: {type(gf_issues).__name__}, 内容: {gf_issues}")
        
        results = previous_results.copy()
        
        # 构建优化提示词
        prompt_parts = ["# 爆款对齐优化专家\n"]
        prompt_parts.append("你是一名专业的爆款小说优化专家。请基于爆款分析数据，优化以下设计。\n")
        
        # 添加发现的偏差
        all_issues = emotion_issues + stage_goal_issues + gf_issues
        prompt_parts.append(f"\n## 发现的偏差（共{len(all_issues)}个）\n")
        
        if emotion_issues:
            prompt_parts.append("\n### 情绪曲线偏差")
            for issue in emotion_issues[:5]:  # 最多显示5个
                prompt_parts.append(f"- [{issue['type']}] 第{issue.get('chapter', 'N')}章: {issue.get('description', issue.get('current', '未知'))}")
        
        if stage_goal_issues:
            prompt_parts.append("\n### 阶段目标偏差")
            for issue in stage_goal_issues[:3]:  # 最多显示3个
                prompt_parts.append(f"- [{issue['type']}] {issue.get('stage', '')}: {issue.get('suggestion', issue.get('description', ''))}")
        
        if gf_issues:
            prompt_parts.append("\n### 金手指偏差")
            for issue in gf_issues[:3]:  # 最多显示3个
                prompt_parts.append(f"- [{issue['type']}] {issue.get('suggestion', issue.get('issue', ''))}")
        
        # 添加爆款参考数据
        prompt_parts.append("\n## 爆款参考数据\n")
        
        bs_emotion = bestseller_analysis.get('emotion_curve', {})
        if bs_emotion:
            prompt_parts.append("\n### 爆款情绪节奏要点")
            prompt_parts.append("- 严格5章循环：压抑(7)→紧张/嘲讽(8)→反转/爆发(9)→震惊(8)→期待(6)")
            prompt_parts.append("- 每章至少1个爽点（强度≥7）")
            prompt_parts.append("- 前10章必须有3个以上高情绪高潮")
        
        bs_gf_formula = bestseller_analysis.get('golden_finger_formula', '')
        # 🔥 安全处理：确保可以正确转换为字符串和切片
        try:
            # 无论什么类型，先转字符串
            if bs_gf_formula is None:
                formula_str = ''
            elif isinstance(bs_gf_formula, str):
                formula_str = bs_gf_formula
            else:
                # dict/list 等类型转JSON字符串
                formula_str = json.dumps(bs_gf_formula, ensure_ascii=False)
            
            # 安全切片
            if formula_str and formula_str not in ['None', 'null', '', '{}']:
                if len(formula_str) > 500:
                    formula_text = formula_str[:500] + "..."
                else:
                    formula_text = formula_str
                prompt_parts.append("\n### 爆款金手指公式\n" + formula_text)
        except Exception as e:
            logger.warning(f"[对话模式 {self.session_id}] golden_finger_formula 处理失败: {e}，跳过")
        
        # 添加当前设计
        prompt_parts.append("\n## 当前设计（需优化）\n")
        
        emotion_curve = previous_results.get('emotion_curve', [])
        if isinstance(emotion_curve, list) and emotion_curve:
            prompt_parts.append("\n### 情绪曲线（前10章）")
            for point in emotion_curve[:10]:
                prompt_parts.append(f"- 第{point.get('chapter', '?')}章: {point.get('emotion', '?')} (强度{point.get('intensity', '?')})")
        
        stage_goals = previous_results.get('stage_goals', [])
        # 🔥 DEBUG: 记录 stage_goals 的详细信息
        logger.info(f"[DEBUG] previous_results.get('stage_goals') 类型: {type(stage_goals).__name__}")
        if isinstance(stage_goals, dict):
            logger.error(f"[DEBUG] stage_goals 是字典！内容: {stage_goals}")
            stage_goals = [stage_goals]
        elif not isinstance(stage_goals, list):
            logger.error(f"[DEBUG] stage_goals 类型异常: {type(stage_goals)}, 内容: {stage_goals}")
            stage_goals = []
        if stage_goals:
            prompt_parts.append("\n### 阶段目标")
            for goal in stage_goals[:3]:
                if isinstance(goal, dict):
                    prompt_parts.append(f"- {goal.get('goal_id', '?')}: {goal.get('description', '?')[:50]}")
                    prompt_parts.append(f"  交付物: {', '.join(goal.get('key_deliverables', []))}")
        
        golden_finger = previous_results.get('plan', {}).get('golden_finger', {})
        if golden_finger:
            prompt_parts.append(f"\n### 金手指\n{json.dumps(golden_finger, ensure_ascii=False, indent=2)[:800]}")
        
        # 添加优化要求
        prompt_parts.append("\n## 优化要求\n")
        prompt_parts.append("1. **情绪曲线**：严格遵循爆款的5章循环节奏（压抑→嘲讽→反转→震惊→期待）")
        prompt_parts.append("2. **阶段目标**：每个阶段必须有明确的'爽点交付物'，如'震惊全场'、'首次展现实力'")
        prompt_parts.append("3. **金手指**：增加层次感和具体数值体系，设计3-5个成长阶段")
        prompt_parts.append("4. **保持原有设定**：优化时不要改变书名、主角名、世界观等核心设定")
        
        # 添加输出格式
        prompt_parts.append("\n## 输出格式\n")
        prompt_parts.append("返回优化后的完整JSON（只返回有优化的部分，其他可省略）：")
        prompt_parts.append("""
{
  "emotion_curve": [...],  // 优化后的完整情绪曲线（如果需优化）
  "stage_goals": [...],    // 优化后的阶段目标（如果需优化）
  "plan": {
    "golden_finger": {...} // 优化后的金手指（如果需优化）
  }
}

严格要求：字符串值内部的双引号必须转义为 \\"
""")
        prompt_parts.append("\n只返回JSON，不要其他说明。")
        
        prompt = "\n".join(prompt_parts)
        
        # 调用AI进行优化
        try:
            logger.info(f"[对话模式 {self.session_id}] 发送爆款对齐优化请求...")
            response = self.session.send_message(
                prompt,
                temperature=0.7,
                purpose="步骤6-爆款对齐优化"
            )
            self._logger.log_round("bestseller_alignment", self.session.messages.copy(), 
                                   response if isinstance(response, str) else json.dumps(response))
            
            # 解析优化结果
            optimized = self._parse_json_response(response, "bestseller_optimization")
            
            if optimized:
                # 合并优化结果（严格验证格式，发现问题立即报错）
                if 'emotion_curve' in optimized and optimized['emotion_curve']:
                    ec = optimized['emotion_curve']
                    if not isinstance(ec, list):
                        raise ValueError(f"步骤6优化返回的 emotion_curve 必须是列表，实际类型: {type(ec).__name__}")
                    results['emotion_curve'] = ec
                    logger.info(f"[对话模式 {self.session_id}] 情绪曲线已优化")
                
                if 'stage_goals' in optimized and optimized['stage_goals']:
                    sg = optimized['stage_goals']
                    if not isinstance(sg, list):
                        raise ValueError(f"步骤6优化返回的 stage_goals 必须是列表，实际类型: {type(sg).__name__}。请检查AI响应格式")
                    results['stage_goals'] = sg
                    logger.info(f"[对话模式 {self.session_id}] 阶段目标已优化")
                
                if 'plan' in optimized and 'golden_finger' in optimized['plan']:
                    if 'plan' not in results:
                        results['plan'] = {}
                    results['plan']['golden_finger'] = optimized['plan']['golden_finger']
                    logger.info(f"[对话模式 {self.session_id}] 金手指已优化")
            else:
                logger.warning(f"[对话模式 {self.session_id}] 优化响应解析失败，使用原始结果")
            
        except Exception as e:
            logger.error(f"[对话模式 {self.session_id}] 爆款对齐优化失败: {e}")
        
        return results


class MarketDrivenConversationManager:
    """市场导向对话管理器"""
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.active_sessions: Dict[str, MarketDrivenConversationSession] = {}
    
    def start_conversation(self, genre: str, user_choices: Dict, 
                          tropes: Optional[Dict] = None, provider: str = None) -> MarketDrivenConversationSession:
        """开始新的对话会话
        
        Args:
            genre: 题材
            user_choices: 用户选择
            tropes: 套路分析结果
            provider: 提供商，None则使用APIClient默认提供商
        """
        # 🔥 修复：传递provider参数，不再硬编码kimi
        session = MarketDrivenConversationSession(
            api_client=self.api_client,
            genre=genre,
            user_choices=user_choices,
            tropes=tropes,
            provider=provider  # 允许传入None，让内部自动选择
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
                               progress_callback=None,
                               project_path: str = None) -> Dict:
    """
    使用对话模式生成市场导向产物
    
    Args:
        api_client: APIClient实例
        genre: 题材
        user_choices: 用户选择
        tropes: 套路分析结果（可选）
        progress_callback: 进度回调
        project_path: 项目路径，用于每步保存中间结果
    
    Returns:
        所有产物字典
    """
    manager = MarketDrivenConversationManager(api_client)
    session = manager.start_conversation(genre, user_choices, tropes)
    return session.generate_all(progress_callback, project_path)
