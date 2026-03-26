# -*- coding: utf-8 -*-
"""
Trope Analyzer Service
套路分析服务

基于AI实时分析番茄头部作品，提取爆款套路
"""

import json
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class AIInteractionLogger:
    """AI交互日志记录器 - 保存为易读的Markdown格式"""
    
    def __init__(self, log_dir: str = "logs/ai_interactions"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
    
    def log_interaction(self, genre: str, prompt: str, response: Dict, 
                       duration_ms: int = 0, success: bool = True) -> str:
        """
        记录一次AI交互为Markdown格式
        
        Returns:
            日志文件路径
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"trope_analysis_{genre.replace('/', '_')}_{timestamp}.md"
        
        # 构建Markdown内容
        lines = []
        
        # 标题
        lines.append(f"# 🔍 套路分析记录 - {genre}")
        lines.append("")
        lines.append(f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"**耗时**: {duration_ms/1000:.2f}秒")
        lines.append(f"**状态**: {'✅ 成功' if success else '❌ 失败'}")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 请求部分
        lines.append("## 📤 发送给AI的Prompt")
        lines.append("")
        lines.append("<details>")
        lines.append("<summary>点击展开查看完整的Prompt</summary>")
        lines.append("")
        lines.append("```")
        lines.append(prompt)
        lines.append("```")
        lines.append("")
        lines.append("</details>")
        lines.append("")
        lines.append("---")
        lines.append("")
        
        # 响应部分
        lines.append("## 📥 AI返回的结果")
        lines.append("")
        
        if not success:
            lines.append("```json")
            lines.append(json.dumps(response, ensure_ascii=False, indent=2))
            lines.append("```")
        else:
            # 核心套路公式
            if "core_formula" in response:
                lines.append(f"### 🎯 核心套路公式")
                lines.append("")
                lines.append(f"> {response['core_formula']}")
                lines.append("")
            
            # 剧情路线
            if "plot_templates" in response:
                plot_templates = response["plot_templates"]
                lines.append(f"### 🎭 剧情路线 ({len(plot_templates)}条)")
                lines.append("")
                for i, plot in enumerate(plot_templates, 1):
                    name = plot.get("name", f"路线{i}")
                    desc = plot.get("desc", "")
                    detail = plot.get("detail", "")
                    lines.append(f"#### {i}. {name}")
                    if desc:
                        lines.append(f"*{desc}*")
                    lines.append("")
                    if detail:
                        lines.append("```")
                        lines.append(detail)
                        lines.append("```")
                    lines.append("")
            
            # 阶段性节奏
            if "stage_rhythm" in response:
                sr = response["stage_rhythm"]
                lines.append("### ⏱️ 阶段性节奏")
                lines.append("")
                lines.append(f"- **描述**: {sr.get('description', 'N/A')}")
                lines.append(f"- **小高潮间隔**: {sr.get('small_climax_interval', 'N/A')}章")
                lines.append(f"- **中高潮间隔**: {sr.get('medium_climax_interval', 'N/A')}章")
                lines.append(f"- **大高潮间隔**: {sr.get('large_climax_interval', 'N/A')}章")
                lines.append(f"- **阶段间隔**: {sr.get('stage_climax_interval', 'N/A')}章")
                if "stage_climax_chapters" in sr:
                    lines.append(f"- **阶段高潮章节**: {', '.join(map(str, sr['stage_climax_chapters']))}")
                lines.append("")
            
            # 完整JSON（折叠）
            lines.append("### 📄 完整JSON响应")
            lines.append("")
            lines.append("<details>")
            lines.append("<summary>点击展开查看完整JSON</summary>")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(response, ensure_ascii=False, indent=2))
            lines.append("```")
            lines.append("")
            lines.append("</details>")
            lines.append("")
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            logger.info(f"[AI交互日志] 已保存: {log_file}")
            return str(log_file)
        except Exception as e:
            logger.error(f"[AI交互日志] 保存失败: {e}")
            return ""


class TropeAnalyzer:
    """
    套路分析器
    使用AI实时分析番茄头部作品，总结爆款套路
    """
    
    # 类型管理器实例（懒加载）
    _genre_manager = None
    
    @classmethod
    def _get_genre_manager(cls):
        """获取GenreManager实例"""
        if cls._genre_manager is None:
            from web.services.market_driven.genre_manager import get_genre_manager
            cls._genre_manager = get_genre_manager()
        return cls._genre_manager
    
    def __init__(self, api_client=None, log_ai_interactions: bool = True):
        """
        初始化套路分析器
        
        Args:
            api_client: AI API客户端
            log_ai_interactions: 是否记录AI交互日志
        """
        self.api_client = api_client
        self._cache = {}  # 简单缓存，避免重复分析
        
        # AI交互日志记录器
        self._interaction_logger = AIInteractionLogger() if log_ai_interactions else None
    
    @classmethod
    def get_available_genres(cls, api_client=None) -> Dict[str, Dict]:
        """
        获取可选择的题材列表（支持自动更新）
        
        Args:
            api_client: AI API客户端（用于自动更新）
            
        Returns:
            题材列表，包含描述和预期数据
        """
        manager = cls._get_genre_manager()
        if api_client:
            manager.api_client = api_client
        return manager.get_genres()
    
    def analyze_genre(self, genre: str, use_cache: bool = True) -> Dict:
        """
        分析指定题材的爆款套路
        
        Args:
            genre: 题材名称
            use_cache: 是否使用缓存
            
        Returns:
            套路分析结果
        """
        # 检查缓存
        if use_cache and genre in self._cache:
            logger.info(f"[TropeAnalyzer] 使用缓存的套路分析: {genre}")
            return self._cache[genre]
        
        logger.info(f"[TropeAnalyzer] 开始分析题材套路: {genre}")
        
        # 构建分析Prompt
        analysis_prompt = self._build_analysis_prompt(genre)
        
        # 记录开始时间
        start_time = datetime.now()
        
        try:
            # 调用AI分析
            if self.api_client:
                result = self._call_ai_analysis(analysis_prompt)
            else:
                # 模拟模式：返回预设的套路模板
                result = self._get_mock_tropes(genre)
                logger.info(f"[TropeAnalyzer] 使用模拟数据（无API客户端）")
            
            # 计算耗时
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            # 记录AI交互日志
            if self._interaction_logger:
                log_path = self._interaction_logger.log_interaction(
                    genre=genre,
                    prompt=analysis_prompt,
                    response=result,
                    duration_ms=duration_ms,
                    success=True
                )
                if log_path:
                    logger.info(f"[TropeAnalyzer] AI交互日志已保存: {log_path}")
            
            # 添加元数据
            result["genre"] = genre
            result["analyzed_at"] = datetime.now().isoformat()
            result["analysis_version"] = "1.0"
            
            # 缓存结果
            self._cache[genre] = result
            
            logger.info(f"[TropeAnalyzer] 套路分析完成: {genre}")
            return result
            
        except Exception as e:
            logger.error(f"[TropeAnalyzer] 套路分析失败: {e}", exc_info=True)
            
            # 记录失败的交互日志
            if self._interaction_logger:
                duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                error_response = {"error": str(e), "error_type": type(e).__name__}
                self._interaction_logger.log_interaction(
                    genre=genre,
                    prompt=analysis_prompt,
                    response=error_response,
                    duration_ms=duration_ms,
                    success=False
                )
            
            # 返回默认套路
            return self._get_default_tropes(genre)
    
    def _build_analysis_prompt(self, genre: str) -> str:
        """
        构建套路分析Prompt - 让AI根据题材自由设计节奏
        """
        return f"""你是一位资深的番茄小说爆款分析师，深谙"{genre}"题材的头部作品套路。

请深入分析该题材Top10爆款小说（均订10万+），提取其**真实的节奏规律**，生成可直接用于创作的执行级分析数据。

## 1. 核心套路公式
- 用一句话概括爆款公式（15字以内）
- 示例：穷屌丝→花钱返利系统→越花越有钱→装逼打脸→身份升级

## 2. 多路线剧情设计（plot_templates）
**必须提供3-5条真正不同的剧情路线供用户选择**，每条路线必须：
- 基于该题材Top10爆款的真实剧情走向
- **节奏节奏必须与该题材爆款高度一致**（不要套用固定模板）
- 每条路线的高潮分布可以不同

每条路线包含：
- **name**: 路线名称（体现该题材特色，如："稳健发育流"、"高调直播流"、"幕后投资流"）
- **desc**: 一句话描述该路线特点
- **detail**: 详细剧情走向，**必须基于该题材真实爆款节奏**：
  - 【第1章】开局触发（必须具体到场景和行为）
  - 后续高潮节点：**根据该题材真实节奏分布**，标记关键章节（如：【第3章】【第8章】【第15章】等）
  - 【第X章】阶段性总结高潮（根据题材确定X，可能是30/50/80/100章等）

**重要**：不要强行套用3-10-20-30节奏！请根据"{genre}"题材的真实爆款节奏来设计。

## 3. 开局3章详细剧本（必须具体到场景）
- **第1章：绝望开局+系统觉醒**
  - 主角具体身份（如：被裁员的外卖员/负债保安/穷学生）
  - 当前困境（具体到数字：欠多少钱、被谁羞辱）
  - 获得系统的触发场景（如：送外卖被撞、被房东赶出门）
  - 章尾钩子：系统激活，即将逆袭
  
- **第2章：初试锋芒+小爽点**
  - 第一次使用系统的场景（具体到地点和行为）
  - 周围人的反应（震惊/嘲讽→被打脸）
  - 获得的第一笔奖励/能力提升
  - 章尾钩子：引出第一个反派
  
- **第3章：第一次正式打脸**
  - 冲突场景（如：4S店买车、高档餐厅、同学会）
  - 反派身份（势利眼前女友/宝马男/势利眼销售）
  - 打脸过程（反转爽点）
  - 章尾钩子：更大的舞台/身份曝光/系统升级

## 4. 爆款标题公式库（5个可直接用的标题）
**严格要求**：每个标题≤15个字（不含书名号《》），必须包含数字或强烈对比
- 格式示例：
  1. 《物价贬值百万倍》（8字）
  2. 《开局激活百倍奖励》（8字）
  3. 《国运：我被选中》（7字）
  4. 《扮演雷神，全网跪了》（9字）
  5. 《具现石油，龙国暴富》（9字）

## 5. 金手指数值设计（具体到数字）
- **类型**：国运专属系统（具体类型：扮演类/召唤类/选择类/签到类）
- **初始奖励**：
  - 数值：XXX点（国运值/能量点/信仰值）
  - 等效价值：相当于XX万人民币/稀有资源
- **首次升级所需**：XX点
- **成长曲线**：用简洁的文字描述成长曲线（如："前期快(1-30级每级100点)，中期慢(31-80级每级500点)，后期极慢(81-100级每级2000点)")
- **限制条件**：具体冷却时间/使用次数/地点限制
- **升级方式**：具体行为（如：击杀1只禁地生物=10点）

## 6. 主角人设执行手册
- **主角姓名**：起一个简洁好记、符合题材风格的名字（2-3个字，避免生僻字）
- **开局身份**：具体到职业+困境（如：被裁员外卖员，负债50万，女友分手）
- **外貌特征**：让读者有代入感的描述
- **性格标签**：3个核心标签（如：隐忍/护短/不圣母）
- **绝对禁忌**：会导致读者弃书的人设（圣母/优柔寡断/主动惹事）

## 7. 阶段性大节奏设计（基于真实爆款分析）
深入分析该题材Top10爆款的**真实阶段性节奏规律**：

**该题材特有的大高潮间隔**（不要套用固定值，根据真实爆款分析）：
- 前期（开局-第一次阶段性高潮）：每X章一个大高潮（该题材真实间隔，可能是20/30/50章）
- 中期：每X章一个大高潮（该题材真实间隔）
- 后期：每X章一个大高潮（该题材真实间隔）

**具体的阶段性高潮节点**（根据该题材Top10爆款的真实分布）：
- 第一次阶段性高潮：第X章（类型：XXX，根据题材实际分析）
- 第二次阶段性高潮：第X章（类型：XXX）
- 第三次阶段性高潮：第X章（类型：XXX）
- 第四次阶段性高潮：第X章（类型：XXX）
- ...

**节奏数值定义**（必须基于真实爆款数据）：
- small_climax_interval: X章（该题材真实的小高潮间隔，可能是3/5/8章）
- medium_climax_interval: X章（该题材真实的中高潮间隔，可能是8/10/15章）
- large_climax_interval: X章（该题材真实的大高潮间隔，可能是15/20/30章）
- stage_climax_interval: X章（该题材真实的阶段性大高潮间隔，可能是30/50/80/100章）
- stage_climax_chapters: [X, X, X]（具体的阶段性高潮章节列表）
- stage_climax_types: ["高潮1类型", "高潮2类型", ...]

**节奏描述**：用一句话描述该题材的节奏特点（如："国运文采用30章周期，每30章一个地图升级"）

## 8. 情绪节奏表（前30章）
基于该题材真实爆款的**实际情绪曲线**：
- **压抑→爆发周期**：每X章一个循环（根据题材实际）
- **具体高潮分布**（根据题材实际分析）：
  - 第X章：第一次小高潮（根据真实爆款分布）
  - 第X章：第一次中高潮（根据真实爆款分布）
  - 第X章：第一个大高潮（根据真实爆款分布）
  - 第X章：阶段性总结高潮（根据真实爆款分布）
- **章尾钩子类型**：根据该题材真实爆款，列出常用的钩子类型

## 8. 第一个大高潮（前30章）详细设计
- **触发场景**：具体到地点（如：禁地第一层BOSS战）
- **冲突对象**：具体身份（如：漂亮国选手挑衅）
- **金手指使用**：具体能力展示
- **结果/奖励**：具现到龙国的具体资源（如：百亿吨石油）
- **全网反应**：从嘲讽到跪舔的反转过程
- **高层反应**：龙国高层紧急会议，主角进入国家视野

## 9. 反派设计套路
- **初期反派（1-30章）**：
  - 身份：势利眼（前女友/同学/同事）
  - 打脸模式：看不起→嘲讽→震惊→后悔→跪舔
- **中期反派（30-100章）**：
  - 身份：其他国家选手/资本大佬
  - 打脸模式：阴谋诡计→主角反杀→国家层面胜利
- **后期反派（100章+）**：
  - 身份：神秘势力/终极BOSS

## 10. 世界观关键场景（必须出现）
- 列出5-8个该题材必须有的场景（如：直播间、禁地入口、国运指挥部）
- 每个场景的作用和爽点设计

## 11. 番茄平台爆款 checklist
- 标题必备元素：
- 简介必备元素：
- 前3章必须出现：
- 章节结尾技巧：
- 写作风格：直白、短段落、多对话、少用形容词

## 输出要求
1. 所有内容必须**具体可执行**，不能泛泛而谈
2. 数字必须**具体**（如：负债50万，不是"负债累累"）
3. 场景必须**具体到地点和行为**
4. 用JSON格式输出，确保可以被程序解析
5. 标题库必须提供5个可直接复制使用的标题

## JSON输出格式示例
```json
{{
  "core_formula": "核心套路公式",
  "title_templates": ["标题1", "标题2", "标题3", "标题4", "标题5"],
  "plot_templates": [
    {{
      "name": "路线名称（如：稳健发育流）",
      "desc": "一句话描述该路线特点",
      "detail": "【第1章】第1章末尾，被选中的瞬间\n【第3章】第一次小高潮：打脸势利眼同事，展示金手指\n【第10章】第一次中高潮：具现首件国家级资源，地方震动\n【第20章】第一个大高潮：国家层面认可，主角进入高层视野\n【第30章】阶段性总结高潮：身份全网曝光，开启新地图\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（具现国家级资源），每30章一个大高潮（国家层面认可与身份曝光）"
    }},
    {{
      "name": "路线2名称（如：高调打脸流）",
      "desc": "一句话描述",
      "detail": "同上格式，包含完整的第1/3/10/20/30章节点描述"
    }},
    {{
      "name": "路线3名称（如：幕后布局流）",
      "desc": "一句话描述",
      "detail": "同上格式"
    }}
  ],
  "opening_pattern": {{
    "chapter_1": "第1章内容...",
    "chapter_2": "第2章内容...",
    "chapter_3": "第3章内容..."
  }},
  "golden_finger": {{
    "type": "系统类型",
    "initial_reward": "初始奖励描述（如：扮演度10%，等效价值100万）",
    "growth_curve": "用简洁文字描述成长曲线（如：前期每级100点，中期每级500点）",
    "limitation": "限制条件",
    "upgrade": "升级方式"
  }},
  "protagonist": {{
    "name": "主角姓名",
    "background": "主角背景",
    "personality": "性格标签"
  }},
  "pacing": {{
    "chapter_1": "第1章节奏",
    "chapter_3": "第3章节奏",
    "climax_interval": "高潮间隔"
  }},
  "stage_rhythm": {{
    "description": "该题材的阶段性大节奏描述",
    "small_climax_interval": 3,
    "medium_climax_interval": 10,
    "stage_climax_interval": 30,
    "stage_climax_chapters": [30, 60, 90, 120],
    "stage_climax_types": [
      "第一次阶段性高潮：本地称王",
      "第二次阶段性高潮：省城登顶",
      "第三次阶段性高潮：全国闻名",
      "第四次阶段性高潮：全球至尊"
    ],
    "early_stage": {{
      "range": "1-30章",
      "rhythm": "快节奏，密集爽点",
      "climax_interval": 30
    }},
    "mid_stage": {{
      "range": "31-100章",
      "rhythm": "中节奏，铺垫与爆发交替",
      "climax_interval": 30
    }},
    "late_stage": {{
      "range": "100章+",
      "rhythm": "慢节奏，大场面",
      "climax_interval": 30
    }}
  }},
  "first_climax_design": {{
    "scene": "触发场景",
    "conflict": "冲突对象",
    "reward": "结果奖励",
    "reaction": "全网反应"
  }},
  "antagonist": {{
    "early": "初期反派身份（如：势利眼销售、前女友、同事）",
    "mid": "中期反派身份（如：富二代、地方势力）",
    "late": "后期反派身份（如：国际势力、终极BOSS）",
    "pattern": "打脸模式（如：看不起→嘲讽→震惊→后悔→跪舔）",
    "early_stage": [
      {{"name": "反派1名称", "scene": "出现场景", "pattern": "打脸模式"}},
      {{"name": "反派2名称", "scene": "出现场景", "pattern": "打脸模式"}}
    ]
  }},
  "platform_tips": {{
    "title_style": "15字以内，有冲击力，包含数字或强烈对比",
    "writing_style": "直白、短段落、多对话、少用形容词",
    "chapter_ending": "每章结尾必须有钩子，让读者想看下一章"
  }},
  "must_have": ["全球直播弹幕互动", "国运具现奖励", "各国选手对比"],
  "must_not_have": ["主角开局太强", "圣母心泛滥", "缺少直播互动"],
  "emotion_curve": {{
    "pattern": "3章一小爽，10章一中爽，30章一大爽",
    "description": "全程无尿点，章章有钩子"
  }}
}}
```

请用严格的JSON格式输出。"""

    def _call_ai_analysis(self, prompt: str) -> Dict:
        """
        调用AI进行分析
        """
        # 实际调用API
        response = self.api_client.generate_content_with_retry(
            content_type="trope_analysis",
            user_prompt=prompt,
            temperature=0.3,
            purpose=f"分析题材套路"
        )
        
        # 解析JSON响应（严格要求标准格式）
        if isinstance(response, dict):
            result = response
        elif isinstance(response, str):
            # 清理响应
            response = response.strip()
            if response.startswith('\ufeff'):
                response = response[1:]
            
            # 尝试直接解析标准JSON
            try:
                result = json.loads(response)
            except json.JSONDecodeError as e:
                # 尝试从markdown代码块提取
                import re
                json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                if json_match:
                    try:
                        result = json.loads(json_match.group(1).strip())
                    except json.JSONDecodeError:
                        raise ValueError(f"AI返回的JSON格式错误（代码块内）: {e}")
                else:
                    raise ValueError(f"AI返回的不是有效JSON格式: {e}")
        else:
            raise ValueError(f"AI返回格式错误: {type(response)}")
        
        # 🔍 调试日志：检查plot_templates
        if "plot_templates" in result:
            templates = result["plot_templates"]
            logger.info(f"[TropeAnalyzer] AI返回了 {len(templates)} 条剧情路线")
            for i, t in enumerate(templates[:3]):
                logger.info(f"[TropeAnalyzer] 路线{i+1}: {t.get('name', 'N/A')} - {t.get('desc', 'N/A')[:30]}...")
        else:
            logger.warning("[TropeAnalyzer] AI返回的数据缺少plot_templates字段！")
        
        return result
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """
        从文本中提取JSON - 增强版，处理各种格式问题
        """
        import re
        
        # 清理文本：移除可能的BOM和特殊字符
        text = text.strip()
        if text.startswith('\ufeff'):
            text = text[1:]
        
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            json_str = json_match.group(1).strip()
            # 尝试直接解析
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"JSON块解析失败: {e}")
                # 尝试修复双花括号
                try:
                    fixed = json_str.replace('{{', '{').replace('}}', '}')
                    return json.loads(fixed)
                except:
                    pass
        
        # 尝试直接找到最外层的花括号（处理嵌套）
        # 使用计数方法找到匹配的括号
        start = text.find('{')
        if start != -1:
            count = 0
            end = start
            for i, char in enumerate(text[start:]):
                if char == '{':
                    count += 1
                elif char == '}':
                    count -= 1
                    if count == 0:
                        end = start + i + 1
                        break
            
            if end > start:
                json_str = text[start:end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.warning(f"提取的JSON解析失败: {e}")
                    # 尝试修复双花括号
                    try:
                        fixed = json_str.replace('{{', '{').replace('}}', '}')
                        return json.loads(fixed)
                    except:
                        pass
        
        # 尝试提取花括号内容（简单模式，最后一个）
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            json_str = brace_match.group(0)
            try:
                return json.loads(json_str)
            except:
                # 尝试修复双花括号
                try:
                    fixed = json_str.replace('{{', '{').replace('}}', '}')
                    return json.loads(fixed)
                except:
                    pass
        
        # 返回默认结构
        logger.error("无法从文本中提取有效JSON")
        return {"raw_text": text[:500] + "...", "parse_error": True}

    def _get_mock_tropes(self, genre: str) -> Dict:
        """
        获取模拟的套路数据（用于测试）
        """
        mock_data = {
            "神豪文-花钱返利类": {
                "core_formula": "穷屌丝→获得花钱返利系统→被迫高消费→装逼打脸→身份升级→更大场面",
                "title_templates": [
                    "开局物价贬值百万倍",
                    "我有九千万亿舔狗金",
                    "神豪：从被校花拒绝开始",
                    "花钱返利系统：越花越有钱",
                    "开局获得百倍返利系统"
                ],
                "plot_templates": [
                    {
                        "name": "都市神豪线", 
                        "desc": "现代都市花钱装逼，稳健发育", 
                        "detail": "【第1章】主角送外卖被撞，激活花钱返利系统，即将逆袭\n【第3章】第一次小高潮：4S店买车打脸势利眼销售，小范围震惊\n【第10章】第一次中高潮：高档餐厅一掷千金，身份初曝光，登上本地新闻\n【第20章】第一个大高潮：拍卖会力压富二代，身份全网曝光，进入富豪圈\n【第30章】阶段性总结高潮：收购本地龙头企业，成为省城首富，开启全国版图\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（具现国家级资源），每30章一个大高潮（国家层面认可与身份曝光）"
                    },
                    {
                        "name": "高调打脸流", 
                        "desc": "直播花钱，全网跪舔", 
                        "detail": "【第1章】主角直播送外卖被羞辱，激活神豪系统，开启直播\n【第3章】第一次小高潮：直播间打赏10万打脸嘲讽者，引发小范围关注\n【第10章】第一次中高潮：直播收购网红公司，全网热搜，地方媒体采访\n【第20章】第一个大高潮：直播对抗资本大鳄，身份曝光为隐世家族传人\n【第30章】阶段性总结高潮：建立直播帝国，国家部门关注，开启国际版图\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（具现国家级资源），每30章一个大高潮（国家层面认可与身份曝光）"
                    },
                    {
                        "name": "幕后布局流", 
                        "desc": "暗中投资，掌控全局", 
                        "detail": "【第1章】主角被裁员，激活投资返利系统，暗中布局\n【第3章】第一次小高潮：悄悄投资小公司，打脸前同事/前上司\n【第10章】第一次中高潮：投资独角兽企业曝光，身价暴涨百亿\n【第20章】第一个大高潮：幕后操控资本市场，国家金融部门关注\n【第30章】阶段性总结高潮：成为资本大鳄，影响国家经济，开启全球布局\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（具现国家级资源），每30章一个大高潮（国家层面认可与身份曝光）"
                    }
                ],
                "opening_pattern": {
                    "chapter_1": "主角送外卖/当保安/摆地摊，穷到极点，被宝马男/前女友/上司羞辱，获得花钱返利系统",
                    "chapter_2": "系统激活，第一次被迫花钱，周围人震惊",
                    "chapter_3": "第一次返利到账，实力提升，开始第一次小规模打脸",
                    "taboos": ["主角开局不穷", "系统不给钱", "主角圣母不反击"]
                },
                "golden_finger": {
                    "type": "花钱返利",
                    "initial_reward": "10倍返利，首单额外奖励",
                    "growth_curve": "前期快(1-10级每消费1万升1级)，中期慢(11-50级每消费10万升1级)，后期极慢(51-100级每消费100万升1级)",
                    "limitation": "初期有金额上限，随等级提升",
                    "upgrade": "消费额度达标后升级，返利比例提升"
                },
                "protagonist": {
                    "name": "李明",
                    "background": "28岁外卖员，被裁员后负债35万，父亲重病需手术费20万，女友因贫困分手，租住城中村隔断间",
                    "personality": "隐忍但不怂，不主动惹事但不怕事，有恩必报有仇必报",
                    "growth": "穷屌丝→小有资产→地方富豪→全国富豪→全球首富",
                    "taboos": ["开局有钱", "性格圣母", "优柔寡断", "不反击"]
                },
                "pacing": {
                    "system_appearance": "第1章必须出现",
                    "first_money": "第3章必须花第一次钱",
                    "first_face_slap": "第5章必须第一次打脸",
                    "climax_interval": "每3-5章一个小爽点，每10章一个大爽点",
                    "upgrade_milestones": {
                        "30": "地方富豪",
                        "80": "全国富豪",
                        "150": "全球首富"
                    }
                },
                "antagonist": {
                    "early": "势利眼（前女友、宝马男、外卖站长、保安队长）",
                    "mid": "富二代、地方势力",
                    "late": "资本大佬、国际势力",
                    "pattern": "看不起→羞辱→主角反击→震惊→后悔→更大的敌人"
                },
                "worldview": {
                    "setting": "现代都市，钱能通神，阶层分明",
                    "power_system": "资金等级：穷屌丝→万元户→百万富翁→千万富豪→亿万富翁→全球首富",
                    "required_scenes": ["4S店", "高档餐厅", "直播间", "豪宅", "高档商场", "拍卖行"],
                    "social_rules": "有钱就是大爷，豪车名表是身份象征"
                },
                "emotion_curve": {
                    "pattern": "压抑→愤怒→反击→爽快→期待",
                    "cycle": "每5章一个情绪小循环，每15章一个大高潮",
                    "intensity": " gradually上升，后期爽点更强烈"
                },
                "must_have": [
                    "开局被羞辱",
                    "获得花钱系统",
                    "10倍返利",
                    "装逼打脸",
                    "身份升级",
                    "豪车名表",
                    "周围人震惊"
                ],
                "must_not_have": [
                    "主角开局有钱",
                    "系统不给返利",
                    "主角圣母",
                    "节奏慢",
                    "大段背景介绍",
                    "主角主动惹事",
                    "不打脸"
                ],
                "platform_tips": {
                    "title_style": "15字以内，有冲击力，包含数字或强烈对比",
                    "title_examples": ["开局物价贬值百万倍", "我有九千万亿舔狗金", "神豪：从被校花拒绝开始"],
                    "chapter_ending": "每章结尾必须有钩子，让读者想看下一章",
                    "writing_style": "直白、短段落、多对话、少用形容词"
                }
            }
        }
        
        return mock_data.get(genre, self._get_default_tropes(genre))
    
    def _get_default_tropes(self, genre: str) -> Dict:
        """
        获取默认套路（当分析失败时使用）
        """
        return {
            "genre": genre,
            "core_formula": "主角获得特殊能力→逐步变强→战胜敌人→保护重要的人",
            "title_templates": [
                "开局获得逆天系统",
                "我有特殊能力",
                "从普通人到最强王者",
                "系统助我逆袭",
                "开局即巅峰"
            ],
            "plot_templates": [
                {
                    "name": "标准逆袭线", 
                    "desc": "经典成长路线", 
                    "detail": "【第1章】主角获得特殊能力，开启逆袭之路\n【第3章】第一次小高潮：小范围展现实力，打脸轻视者\n【第10章】第一次中高潮：能力大幅提升，引起势力关注\n【第20章】第一个大高潮：击败中期BOSS，身份地位跃升\n【第30章】阶段性总结高潮：阶段性胜利，开启新篇章\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（能力/资源提升），每30章一个大高潮（身份地位跃升）"
                },
                {
                    "name": "高调崛起线", 
                    "desc": "快速成名路线", 
                    "detail": "【第1章】主角高调获得能力，引起各方关注\n【第3章】第一次小高潮：公开展现实力，震惊围观者\n【第10章】第一次中高潮：击败挑战者，建立威名\n【第20章】第一个大高潮：击败强敌，成为一方霸主\n【第30章】阶段性总结高潮：统一地区，准备进军更高层次\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（能力/资源提升），每30章一个大高潮（身份地位跃升）"
                },
                {
                    "name": "幕后布局线", 
                    "desc": "暗中发展路线", 
                    "detail": "【第1章】主角低调获得能力，暗中布局\n【第3章】第一次小高潮：暗中解决麻烦，不暴露身份\n【第10章】第一次中高潮：幕后操控局势，积累资源\n【第20章】第一个大高潮：关键时刻出手，一鸣惊人\n【第30章】阶段性总结高潮：身份曝光，成为幕后大佬\n\n【节奏】每3章一个小高潮（打脸反派），每10章一个中高潮（能力/资源提升），每30章一个大高潮（身份地位跃升）"
                }
            ],
            "opening_pattern": {
                "chapter_1": "主角现状介绍，获得系统/能力",
                "chapter_2": "初步使用能力，小试牛刀",
                "chapter_3": "遇到第一个挑战，成功解决"
            },
            "golden_finger": {
                "type": "系统/特殊能力",
                "initial_reward": "初始能力觉醒",
                "growth_curve": "随使用逐步提升",
                "limitation": "无",
                "upgrade": "通过使用升级"
            },
            "protagonist": {
                "name": "夏天",
                "background": "普通人",
                "personality": "坚韧、善良、有正义感",
                "growth": "普通人→强者→守护者"
            },
            "pacing": {
                "system_appearance": "第1章",
                "first_climax": "第5章",
                "climax_interval": "每5-10章"
            },
            "must_have": ["金手指", "成长", "冲突"],
            "must_not_have": ["开局无敌", "圣母", "逻辑漏洞"],
            "platform_tips": {
                "title_style": "15字以内，有冲击力",
                "writing_style": "直白、短段落、多对话、少用形容词",
                "chapter_ending": "章章有钩子"
            },
            "emotion_curve": {
                "pattern": "压抑→爽快→期待→更爽快",
                "description": "每3-5章一个爽点"
            },
            "analyzed_at": datetime.now().isoformat(),
            "is_default": True
        }


class TropeCache:
    """
    套路缓存管理器
    可以保存到文件，避免重复分析
    """
    
    def __init__(self, cache_dir: str = "cache/tropes"):
        self.cache_dir = cache_dir
        import os
        os.makedirs(cache_dir, exist_ok=True)
    
    def get(self, genre: str) -> Optional[Dict]:
        """获取缓存的套路"""
        import os
        cache_file = os.path.join(self.cache_dir, f"{genre.replace('/', '_')}.json")
        
        if not os.path.exists(cache_file):
            return None
        
        # 检查是否过期（7天）
        import time
        if time.time() - os.path.getmtime(cache_file) > 7 * 24 * 3600:
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取套路缓存失败: {e}")
            return None
    
    def set(self, genre: str, tropes: Dict):
        """保存套路到缓存"""
        import os
        cache_file = os.path.join(self.cache_dir, f"{genre.replace('/', '_')}.json")
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(tropes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存套路缓存失败: {e}")


# 全局分析器实例
trope_analyzer = TropeAnalyzer()
