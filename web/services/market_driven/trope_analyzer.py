# -*- coding: utf-8 -*-
"""
Trope Analyzer Service
套路分析服务

基于AI实时分析番茄头部作品，提取爆款套路
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class TropeAnalyzer:
    """
    套路分析器
    使用AI实时分析番茄头部作品，总结爆款套路
    """
    
    # 预定义的题材列表（用户可以选择的）
    AVAILABLE_GENRES = {
        "神豪文-花钱返利类": {
            "description": "主角获得花钱返利系统，越花越有钱，装逼打脸",
            "expected_retention": "12-18%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "神豪文-签到奖励类": {
            "description": "每日签到获得奖励，逐步积累财富和实力",
            "expected_retention": "10-15%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "国运文-直播类": {
            "description": "主角代表国家参赛，全国直播，获得国运奖励",
            "expected_retention": "15-20%",
            "competition": "激烈",
            "market_status": "上升期"
        },
        "国运文-禁地探险类": {
            "description": "探索禁地，为国争光，获得神秘奖励",
            "expected_retention": "12-16%",
            "competition": "中等",
            "market_status": "平稳"
        },
        "签到文-日常签到类": {
            "description": "日常生活签到获得各种奖励，轻松变强",
            "expected_retention": "10-14%",
            "competition": "低",
            "market_status": "蓝海"
        },
        "奶爸文-萌宝类": {
            "description": "主角带娃，萌宝助攻，温馨搞笑",
            "expected_retention": "18-25%",
            "competition": "低",
            "market_status": "上升期"
        },
        "奶爸文-修炼类": {
            "description": "带娃同时修炼，保护家人，双重爽点",
            "expected_retention": "15-20%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "神选文-神明选拔类": {
            "description": "被神明选中，获得神级能力，征战诸天",
            "expected_retention": "12-16%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "模拟器文-人生模拟类": {
            "description": "可以模拟人生，提前知道未来，改变命运",
            "expected_retention": "14-18%",
            "competition": "中等",
            "market_status": "上升期"
        },
        "灵气复苏-觉醒类": {
            "description": "灵气复苏时代，主角觉醒特殊能力，崛起",
            "expected_retention": "12-16%",
            "competition": "激烈",
            "market_status": "稳定"
        },
        "末日求生-囤货类": {
            "description": "末日来临前大量囤货，末日中享受生活",
            "expected_retention": "15-20%",
            "competition": "中等",
            "market_status": "稳定"
        },
        "四合院-日常类": {
            "description": "在四合院中生活，处理邻里关系，逐步发展",
            "expected_retention": "15-22%",
            "competition": "低",
            "market_status": "蓝海"
        }
    }
    
    def __init__(self, api_client=None):
        """
        初始化套路分析器
        
        Args:
            api_client: AI API客户端
        """
        self.api_client = api_client
        self._cache = {}  # 简单缓存，避免重复分析
    
    @classmethod
    def get_available_genres(cls) -> Dict[str, Dict]:
        """
        获取可选择的题材列表
        
        Returns:
            题材列表，包含描述和预期数据
        """
        return cls.AVAILABLE_GENRES
    
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
        
        try:
            # 调用AI分析
            if self.api_client:
                result = self._call_ai_analysis(analysis_prompt)
            else:
                # 模拟模式：返回预设的套路模板
                result = self._get_mock_tropes(genre)
            
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
            # 返回默认套路
            return self._get_default_tropes(genre)
    
    def _build_analysis_prompt(self, genre: str) -> str:
        """
        构建套路分析Prompt
        """
        return f"""你是一位专业的网络文学分析师，深谙番茄小说平台的爆款规律。

请分析"{genre}"题材的爆款作品套路。

基于你对该题材Top20头部作品的理解，总结以下要素：

## 1. 核心套路公式
- 用一句话概括该题材的爆款公式
- 例：穷屌丝→获得系统→花钱返利→装逼打脸→身份升级

## 2. 开局套路（前3章）
- 第1章必须发生什么？
- 第2章必须发生什么？
- 第3章必须发生什么？
- 开局禁忌（绝对不能写的）

## 3. 金手指设计规律
- 金手指类型：
- 核心机制：
- 限制条件：
- 升级方式：

## 4. 主角人设特征
- 开局身份：
- 性格特点：
- 成长路线：
- 绝对不能有的人设（会扑街的）

## 5. 节奏安排
- 第几章出系统？
- 第几章第一次爽点？
- 爽点间隔：每X章一个
- 身份升级节点：第X章、第X章
- 大高潮位置：第X章左右

## 6. 反派设计套路
- 初期反派（1-30章）：
- 中期反派（30-100章）：
- 后期反派（100章+）：
- 打脸模式：

## 7. 世界观设定特点
- 世界背景：
- 力量体系：
- 必要场景（必须有）：
- 社会规则：

## 8. 情绪曲线设计
- 标准情绪节奏：
- 压抑→爆发周期：
- 高潮情绪强度：

## 9. 必须要素（缺了就不火）
- 列出5-8个该题材必须有的元素

## 10. 禁忌（有就死）
- 列出5-8个该题材绝对不能有的元素

## 11. 平台适配要点
- 番茄读者特别喜欢什么？
- 标题应该怎么起？
- 章节结尾应该怎么写？

请用JSON格式输出，确保内容具体可执行，不要泛泛而谈。"""

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
        
        # 解析JSON响应
        if isinstance(response, dict):
            return response
        elif isinstance(response, str):
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.error("AI返回的不是有效JSON，尝试提取")
                return self._extract_json_from_text(response)
        else:
            raise ValueError(f"AI返回格式错误: {type(response)}")
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """
        从文本中提取JSON
        """
        import re
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 尝试提取花括号内容
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except:
                pass
        
        # 返回默认结构
        return {"raw_text": text, "parse_error": True}

    def _get_mock_tropes(self, genre: str) -> Dict:
        """
        获取模拟的套路数据（用于测试）
        """
        mock_data = {
            "神豪文-花钱返利类": {
                "core_formula": "穷屌丝→获得花钱返利系统→被迫高消费→装逼打脸→身份升级→更大场面",
                "opening_pattern": {
                    "chapter_1": "主角送外卖/当保安/摆地摊，穷到极点，被宝马男/前女友/上司羞辱，获得花钱返利系统",
                    "chapter_2": "系统激活，第一次被迫花钱，周围人震惊",
                    "chapter_3": "第一次返利到账，实力提升，开始第一次小规模打脸",
                    "taboos": ["主角开局不穷", "系统不给钱", "主角圣母不反击"]
                },
                "golden_finger": {
                    "type": "花钱返利",
                    "ratio": "10倍是标配，后期可提升",
                    "activation": "必须完成任务激活（如：24小时内花光1万元）",
                    "limitation": "初期有金额上限，随等级提升",
                    "upgrade": "消费额度达标后升级，返利比例提升"
                },
                "protagonist": {
                    "background": "必须是穷屌丝：外卖员、保安、摆地摊、负债者",
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
            "opening_pattern": {
                "chapter_1": "主角现状介绍，获得系统/能力",
                "chapter_2": "初步使用能力，小试牛刀",
                "chapter_3": "遇到第一个挑战，成功解决"
            },
            "golden_finger": {
                "type": "系统/特殊能力",
                "activation": "自动激活",
                "upgrade": "通过使用升级"
            },
            "protagonist": {
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
