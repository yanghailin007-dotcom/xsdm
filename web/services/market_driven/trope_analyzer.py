# -*- coding: utf-8 -*-
"""
Trope Analyzer Service
爆款分析服务

基于AI实时分析番茄头部作品，提取爆款套路
"""

import json
import logging
import os
import random  # 🔥 新增：用于生成随机性元素
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
        lines.append(f"# 🔍 爆款分析记录 - {genre}")
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
                core_formula = response['core_formula']
                if not isinstance(core_formula, str):
                    core_formula = str(core_formula)
                lines.append(f"### 🎯 核心套路公式")
                lines.append("")
                lines.append(f"> {core_formula}")
                lines.append("")
            
            # 剧情路线
            if "plot_templates" in response:
                plot_templates = response["plot_templates"]
                lines.append(f"### 🎭 剧情路线 ({len(plot_templates)}条)")
                lines.append("")
                for i, plot in enumerate(plot_templates, 1):
                    name = plot.get("name", f"路线{i}") if isinstance(plot.get("name"), str) else f"路线{i}"
                    desc = plot.get("desc", "") if isinstance(plot.get("desc"), str) else ""
                    detail = plot.get("detail", "") if isinstance(plot.get("detail"), str) else str(plot.get("detail", ""))
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
                desc = sr.get('description', 'N/A')
                small = sr.get('small_climax_interval', 'N/A')
                medium = sr.get('medium_climax_interval', 'N/A')
                large = sr.get('large_climax_interval', 'N/A')
                stage = sr.get('stage_climax_interval', 'N/A')
                lines.append(f"- **描述**: {desc if isinstance(desc, str) else str(desc)}")
                lines.append(f"- **小高潮间隔**: {small if isinstance(small, str) else str(small)}章")
                lines.append(f"- **中高潮间隔**: {medium if isinstance(medium, str) else str(medium)}章")
                lines.append(f"- **大高潮间隔**: {large if isinstance(large, str) else str(large)}章")
                lines.append(f"- **阶段间隔**: {stage if isinstance(stage, str) else str(stage)}章")
                if "stage_climax_chapters" in sr:
                    chapters = sr['stage_climax_chapters']
                    if isinstance(chapters, list):
                        lines.append(f"- **阶段高潮章节**: {', '.join(map(str, chapters))}")
                    else:
                        lines.append(f"- **阶段高潮章节**: {str(chapters)}")
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
    爆款分析器
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
        初始化爆款分析器
        
        Args:
            api_client: AI API客户端
            log_ai_interactions: 是否记录AI交互日志
        """
        self.api_client = api_client
        self._cache = {}  # 内存缓存
        self._cache_dir = Path("cache/tropes")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_ttl_days = 7
        
        # AI交互日志记录器
        self._interaction_logger = AIInteractionLogger() if log_ai_interactions else None
        
        # 加载提示词配置
        self._config = self._load_config()
    
    def _load_config(self) -> Dict:
        """从JSON加载提示词配置"""
        config_path = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven" / "components" / "trope_analysis_prompts.json"
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"[TropeAnalyzer] 加载配置失败: {e}")
        return {}
    
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
    
    def _load_file_cache(self, genre: str) -> Optional[Dict]:
        """加载本地文件缓存，7天内有效"""
        cache_file = self._cache_dir / f"{genre.replace('/', '_')}.json"
        if not cache_file.exists():
            return None
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            cached_at = data.get("analyzed_at", "")
            if cached_at:
                cached_date = datetime.fromisoformat(cached_at)
                if (datetime.now() - cached_date).days < self._cache_ttl_days:
                    logger.info(f"[TropeAnalyzer] 使用文件缓存({self._cache_ttl_days}天内): {genre}")
                    return data
                else:
                    logger.info(f"[TropeAnalyzer] 文件缓存已过期({(datetime.now() - cached_date).days}天): {genre}")
            else:
                return data  # 无时间戳也允许读取，保守兼容
        except Exception as e:
            logger.warning(f"[TropeAnalyzer] 加载文件缓存失败: {e}")
        return None
    
    def _save_file_cache(self, genre: str, result: Dict):
        """保存分析结果到本地文件缓存"""
        cache_file = self._cache_dir / f"{genre.replace('/', '_')}.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            logger.info(f"[TropeAnalyzer] 已保存文件缓存: {cache_file}")
        except Exception as e:
            logger.warning(f"[TropeAnalyzer] 保存文件缓存失败: {e}")
    
    def analyze_genre(self, genre: str, use_cache: bool = True) -> Dict:
        """
        分析指定题材的爆款套路
        
        Args:
            genre: 题材名称
            use_cache: 是否使用缓存
            
        Returns:
            爆款分析结果
        """
        # 1. 检查内存缓存
        if use_cache and genre in self._cache:
            logger.info(f"[TropeAnalyzer] 使用内存缓存: {genre}")
            return self._cache[genre]
        
        # 2. 检查文件缓存（7天）
        if use_cache:
            file_cache = self._load_file_cache(genre)
            if file_cache:
                self._cache[genre] = file_cache
                return file_cache
        
        logger.info(f"[TropeAnalyzer] 开始分析爆款题材规律: {genre}")
        
        # 构建分析Prompt
        analysis_prompt = self._build_analysis_prompt(genre)
        
        # 记录开始时间
        start_time = datetime.now()
        
        try:
            # 调用AI分析
            if not self.api_client:
                raise ValueError("爆款分析需要API客户端，请检查API配置")
            
            result = self._call_ai_analysis(analysis_prompt)
            
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
            self._save_file_cache(genre, result)
            
            logger.info(f"[TropeAnalyzer] 爆款分析完成: {genre}")
            return result
            
        except Exception as e:
            logger.error(f"[TropeAnalyzer] 爆款分析失败: {e}", exc_info=True)
            
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
        构建爆款分析Prompt - 从JSON配置加载，并添加随机性元素
        """
        # 从JSON配置加载模板
        template = self._config.get("analysis_template", "")
        
        if not template:
            error_msg = """
❌ 错误：爆款分析提示词配置缺失！

请检查以下配置文件是否存在：
- prompt_packages/default/market_driven/components/trope_analysis_prompts.json
"""
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        # 🔥 构建基础Prompt
        prompt = template.format(genre=genre)
        
        # 🔥 添加随机性元素，确保每次分析角度不同
        analysis_angles = [
            "从读者心理角度分析：什么样的设定能让读者欲罢不能",
            "从市场数据角度分析：哪些套路在番茄头部作品中反复出现",
            "从创意差异化角度分析：如何避免同质化，做出独特卖点",
            "从情绪曲线设计角度分析：如何安排爽点和期待感",
            "从角色塑造角度分析：什么样的主角人设最受欢迎",
            "从开篇钩子角度分析：黄金三章如何设计强吸引力"
        ]
        
        # 随机选择1-2个分析角度
        selected_angles = random.sample(analysis_angles, k=min(2, len(analysis_angles)))
        angle_prompt = "\n\n【本次分析重点】\n" + "\n".join([f"- {angle}" for angle in selected_angles])
        
        # 添加随机种子提示（让AI知道应该生成多样化内容）
        random_seed = random.randint(1000, 9999)
        diversity_prompt = f"\n\n【多样性要求】\n随机种子: {random_seed}\n请确保本次分析与以往不同，提供新鲜的观点和独特的发现。"
        
        prompt += angle_prompt + diversity_prompt
        
        return prompt

    def _call_ai_analysis(self, prompt: str) -> Dict:
        """
        调用AI进行分析
        """
        # 实际调用API
        response = self.api_client.generate_content_with_retry(
            content_type="trope_analysis",
            user_prompt=prompt,
            temperature=0.8,  # 🔥 修复：提高temperature以增加分析结果的多样性
            purpose=f"分析爆款题材规律"
        )
        
        # 解析JSON响应（兼容多种格式）
        if isinstance(response, dict):
            result = response
        elif isinstance(response, str):
            # 清理响应
            response = response.strip()
            if response.startswith('\ufeff'):
                response = response[1:]
            
            # 尝试直接解析
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # 尝试修复双花括号后解析
                try:
                    fixed = response.replace('{{', '{').replace('}}', '}')
                    result = json.loads(fixed)
                    logger.debug("通过修复双花括号成功解析JSON")
                except json.JSONDecodeError:
                    # 尝试从markdown代码块提取
                    import re
                    json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
                    if json_match:
                        try:
                            result = json.loads(json_match.group(1).strip())
                        except json.JSONDecodeError:
                            # 提取后也尝试修复双花括号
                            try:
                                fixed = json_match.group(1).strip().replace('{{', '{').replace('}}', '}')
                                result = json.loads(fixed)
                            except:
                                raise ValueError("AI返回的JSON格式错误")
                    else:
                        raise ValueError("AI返回的不是有效JSON格式")
        else:
            raise ValueError(f"AI返回格式错误: {type(response)}")
        
        # 🔍 调试日志：检查plot_templates
        if "plot_templates" in result:
            templates = result["plot_templates"]
            # 🔥 清理数据：确保 name 和 desc 是字符串
            for t in templates:
                if "name" in t and not isinstance(t["name"], str):
                    t["name"] = str(t["name"])
                if "desc" in t and not isinstance(t["desc"], str):
                    t["desc"] = str(t["desc"])
                if "detail" in t and not isinstance(t["detail"], str):
                    t["detail"] = str(t["detail"])
            logger.info(f"[TropeAnalyzer] AI返回了 {len(templates)} 条剧情路线")
            for i, t in enumerate(templates[:3]):
                logger.info(f"[TropeAnalyzer] 路线{i+1}: {t.get('name', 'N/A')} - {str(t.get('desc', 'N/A'))[:30]}...")
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


def clear_trope_cache():
    """清除 trope_analyzer 的内存缓存和文件缓存"""
    global trope_analyzer
    # 清空内存缓存
    if hasattr(trope_analyzer, '_cache'):
        trope_analyzer._cache.clear()
        logger.info("[TropeAnalyzer] 内存缓存已清空")
    
    # 清空文件缓存
    cache_dir = Path("cache/tropes")
    if cache_dir.exists():
        for cache_file in cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                logger.info(f"[TropeAnalyzer] 已删除缓存文件: {cache_file}")
            except Exception as e:
                logger.error(f"[TropeAnalyzer] 删除缓存文件失败: {e}")
