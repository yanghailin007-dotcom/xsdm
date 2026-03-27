# -*- coding: utf-8 -*-
"""
爆款反向工程分析器
通过分析真实Top10爆款小说，提炼可复用的创作公式
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class BestsellerAnalyzer:
    """
    爆款反向工程分析器
    
    分析维度：
    1. 开局3章详细拆解（每章的场景、对话、钩子）
    2. 金手指设计规律（初始值、成长曲线、限制条件）
    3. 角色塑造公式（主角、反派、配角的功能定位）
    4. 情绪节奏控制（每章情绪曲线设计）
    5. 爽点设计模板（打脸、收获、装逼的具体写法）
    """
    
    # 缓存有效期（天）
    CACHE_TTL_DAYS = 7
    
    def __init__(self, api_client=None, log_dir: str = "logs/bestseller_analysis"):
        self.api_client = api_client
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 🔥 持久化缓存目录
        self._cache_dir = Path("data/bestseller_cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._cache = {}
        
        # 加载持久化缓存
        self._load_persistent_cache()
    
    def analyze_genre(self, genre: str, use_cache: bool = True) -> Dict:
        """
        分析指定题材的Top10爆款，提炼创作公式
        
        Returns:
            包含详细创作公式的字典，可直接用于生成Prompt
        """
        if use_cache and genre in self._cache:
            logger.info(f"[BestsellerAnalyzer] 使用缓存: {genre}")
            return self._cache[genre]
        
        logger.info(f"[BestsellerAnalyzer] 开始分析题材: {genre}")
        
        # 构建分析Prompt
        analysis_prompt = self._build_reverse_engineering_prompt(genre)
        
        try:
            if not self.api_client:
                raise ValueError("爆款分析需要API客户端，请检查API配置")
            
            result = self._call_ai_analysis(analysis_prompt, genre)
            
            # 添加元数据
            result["genre"] = genre
            result["analyzed_at"] = datetime.now().isoformat()
            result["analysis_version"] = "2.0"
            
            # 保存分析日志（Markdown格式，给人看）
            self._save_analysis_log(genre, analysis_prompt, result)
            
            # 🔥 持久化缓存（JSON格式，给程序用）
            self._save_persistent_cache(genre, result)
            
            # 内存缓存
            self._cache[genre] = result
            
            logger.info(f"[BestsellerAnalyzer] 分析完成: {genre}")
            return result
            
        except Exception as e:
            logger.error(f"[BestsellerAnalyzer] 分析失败: {e}", exc_info=True)
            return self._get_default_analysis(genre)
    
    def _build_reverse_engineering_prompt(self, genre: str) -> str:
        """
        构建反向工程分析Prompt
        要求AI深度分析该题材Top10爆款的写法规律
        """
        return f"""你是一位资深的番茄小说爆款拆解专家，专门分析均订10万+的头部作品。

请深度拆解"{genre}"题材的Top10爆款小说，提炼出**可复制的创作公式**。

## 分析要求

不要泛泛而谈，必须给出**具体到字句级**的创作指导。

### 1. 开局3章拆解（必须具体到场景和对话）

分析Top10爆款的开局3章，提炼出**开局公式**：

**第1章公式**：
- **开篇场景**：具体是什么场景？（如：深夜11点，暴雨中的街头）
- **主角困境**：具体数字和细节？（如：欠35万，被房东赶出门）
- **系统觉醒触发点**：什么动作/事件触发系统？（如：被车撞、被羞辱到极致）
- **章尾钩子**：用什么悬念让读者必须看第2章？（如：系统激活倒计时、神秘声音响起）
- **情绪曲线**：本章情绪如何设计？（如：压抑→绝望→希望）
- **字数控制**：多少字？（番茄黄金开局通常2500-3000字）

**第2章公式**：
- **第一次使用系统**：什么场景？遇到什么反派？
- **周围人反应**：分几层写？（如：路人惊讶→反派不屑→被打脸后震惊）
- **第一次收获**：具体是什么？（如：获得10万现金、能力提升10%）
- **章尾钩子**：引出什么新冲突？

**第3章公式**：
- **打脸场景**：具体地点？（如：4S店、高档餐厅、同学会）
- **反派类型**：什么身份？（如：势利眼销售、前女友、宝马男）
- **反转设计**：如何先抑后扬？（如：被嘲讽→展示实力→反派后悔）
- **收获设计**：打脸后获得什么实质性奖励？

### 2. 金手指设计公式

分析Top10作品的金手指，提炼出**数值设计模板**：

**初始奖励公式**：
- 数值：XX点/XX万元/XX倍
- 等效战斗力：相当于什么水平？（如：特种兵王/上市公司CEO）
- 首次使用限制：有什么使用条件？（如：必须在24小时内使用、只能使用3次）

**成长曲线公式**：
- 前期（1-30级）：每级需要XX点，升级后提升XX%
- 中期（31-80级）：每级需要XX点，升级后提升XX%
- 后期（81-100级）：每级需要XX点，升级后提升XX%

**限制条件设计**：
- 冷却时间：XX小时/天
- 使用次数：每天XX次
- 副作用：使用后会XX（如：虚弱24小时、引起敌人注意）

### 3. 角色塑造公式

**主角人设公式**：
- 开局身份：具体到职业+困境（如：被裁员的外卖员，负债35万，女友刚分手）
- 性格标签：3个核心标签（如：隐忍/护短/不圣母）
- 成长弧线：从XX到XX到XX（三阶段）
- 口头禅/标志性动作：什么细节让读者记住主角？

**反派设计公式**：
- 早期反派（1-30章）：什么类型？如何设计让读者恨得牙痒痒？
- 中期反派（31-100章）：什么类型？有什么背景？
- 后期反派（100章+）：什么级别？（如：国际势力、上古世家）
- 打脸节奏：每个反派几章内被打脸？

**配角功能定位**：
- 捧哏型配角：什么功能？如何衬托主角？
- 传声筒型配角：如何传播主角的事迹？
- 对比组配角：如何反衬主角的优秀？

### 4. 情绪节奏公式

**情绪节拍设计**（每5章一个循环）：
- 第1章：什么情绪？如何铺垫？
- 第2章：什么情绪？如何升级压抑？
- 第3章：什么情绪？爽点如何爆发？
- 第4章：什么情绪？如何巩固爽感？
- 第5章：什么情绪？如何埋下新伏笔？

**章尾钩子类型**（轮替使用）：
- 悬念型：留下什么悬念？（如：神秘电话响起、敌人出现）
- 爽点型：以什么爽点结尾？（如：主角获得新能力、反派被震惊）
- 期待型：建立什么期待？（如：明天就是决战、重要人物即将到来）
- 震惊型：以什么震惊事件结尾？（如：身份曝光、惊天秘密揭晓）

### 5. 爽点设计公式

**小爽点设计**（每3章一个）：
- 类型：收获型/打脸型/装逼型/震惊型
- 具体写法：如何设计让读者感到"爽"？
- 铺垫技巧：前面几章如何铺垫这个爽点？

**中爽点设计**（每10章一个）：
- 类型：升级型/身份曝光型/资源获取型
- 具体写法：如何设计让读者感到"大爽"？
- 周围人反应：分几层写震惊？（如：路人→朋友→敌人→高层）

**大爽点设计**（每30章一个）：
- 类型：阶段性总结/身份全网曝光/开启新地图
- 具体写法：如何设计让读者感到"爆爽"？
- 后续铺垫：如何在爽完后埋下新的期待？

## 输出格式

返回JSON格式，结构如下：

```json
{{
  "genre_formula": "该题材的核心公式（一句话总结）",
  "opening_3_chapters": {{
    "chapter_1": {{
      "scene": "具体场景描述",
      "protagonist_situation": "主角困境（带数字）",
      "system_trigger": "系统触发条件和表现",
      "hook": "章尾钩子设计",
      "emotion_curve": "情绪曲线设计",
      "word_count": "建议字数"
    }},
    "chapter_2": {{...}},
    "chapter_3": {{...}}
  }},
  "golden_finger_formula": {{
    "initial_reward": "初始奖励设计",
    "growth_curve": "成长曲线公式",
    "limitations": "限制条件设计"
  }},
  "character_formula": {{
    "protagonist": {{"archetype": "人设原型", "traits": ["标签1", "标签2", "标签3"], "growth_arc": "成长弧线"}},
    "antagonists": {{"early": "早期反派", "mid": "中期反派", "late": "后期反派"}},
    "supporting": ["配角1功能", "配角2功能", "配角3功能"]
  }},
  "emotion_formula": {{
    "cycle": "情绪循环设计（5章一个周期）",
    "hook_types": ["悬念型", "爽点型", "期待型", "震惊型"],
    "intensity_control": "强度控制方法"
  }},
  "climax_formula": {{
    "small_climax": {{"interval": 3, "types": ["类型1", "类型2"], "design_principles": "设计原则"}},
    "medium_climax": {{"interval": 10, "types": ["类型1", "类型2"], "design_principles": "设计原则"}},
    "large_climax": {{"interval": 30, "types": ["类型1", "类型2"], "design_principles": "设计原则"}}
  }},
  "writing_techniques": ["技巧1", "技巧2", "技巧3"],
  "taboos": ["禁忌1", "禁忌2", "禁忌3"]
}}
```

## Output Format Requirements

### ⚠️ 极其重要 - 必须遵守

1. **只返回一个完整的 JSON 对象** - 不要返回多个 JSON 对象拼接
2. **不要分段返回** - 必须一次性返回包含所有字段的完整 JSON
3. **确保所有字段在一个 JSON 中** - genre_formula, opening_3_chapters, golden_finger_formula, character_formula, emotion_formula, climax_formula 都必须在同一个 {{}} 内
4. **以 {{ 开始，以 }} 结束** - 中间不要有任何断开

### JSON 格式检查清单
- [ ] 整个响应只有一个根对象 {{...}}
- [ ] 所有引号成对出现
- [ ] 所有括号成对出现
- [ ] 数组/对象末尾没有多余的逗号
- [ ] 字符串中没有未转义的换行符

### ❌ 错误示例（不要这样做）
```
{{"field1": "value1"}}, {{"field2": "value2"}}  // 错误：两个JSON拼接
```

### ✅ 正确示例（必须这样做）
```
{{"field1": "value1", "field2": "value2"}}  // 正确：一个完整JSON
```

Note: All content must be specific and actionable, not vague."""
    
    def _call_ai_analysis(self, prompt: str, genre: str) -> Dict:
        """调用AI进行分析，带多重错误处理和回退"""
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="bestseller_analysis",
                user_prompt=prompt,
                temperature=0.3,
                purpose=f"爆款反向工程分析-{genre}"
            )
            
            if isinstance(response, dict):
                logger.info(f"[BestsellerAnalyzer] AI直接返回字典，解析成功")
                return response
            elif isinstance(response, str):
                # 尝试直接解析
                try:
                    result = json.loads(response)
                    logger.info(f"[BestsellerAnalyzer] JSON直接解析成功")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"[BestsellerAnalyzer] JSON直接解析失败: {e}，尝试提取...")
                    # 尝试从文本中提取JSON
                    extracted = self._extract_json_from_text(response)
                    if extracted and not extracted.get("parse_error"):
                        logger.info(f"[BestsellerAnalyzer] 从文本中提取JSON成功")
                        return extracted
                    else:
                        logger.error(f"[BestsellerAnalyzer] JSON提取也失败，使用默认模板")
                        return self._get_default_analysis(genre)
            else:
                logger.error(f"[BestsellerAnalyzer] AI返回格式错误: {type(response)}")
                return self._get_default_analysis(genre)
                
        except Exception as e:
            logger.error(f"[BestsellerAnalyzer] AI调用异常: {e}")
            return self._get_mock_analysis(genre)
    
    def _extract_json_from_text(self, text: str) -> Dict:
        """从文本中提取JSON，支持处理多个JSON拼接的情况"""
        import re
        
        # 清理文本
        text = text.strip()
        
        # 尝试直接解析
        try:
            return json.loads(text)
        except:
            pass
        
        # 尝试提取JSON块
        json_match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except:
                pass
        
        # 🔥 关键改进：处理多个JSON对象拼接的情况
        # 查找第一个完整的JSON对象
        first_json = self._extract_first_json_object(text)
        if first_json:
            try:
                result = json.loads(first_json)
                logger.info(f"[BestsellerAnalyzer] 成功提取第一个JSON对象 ({len(first_json)} 字符)")
                
                # 检查后面是否还有更多JSON对象，尝试合并
                remaining = text[len(first_json):].strip()
                if remaining and remaining.startswith(','):
                    remaining = remaining[1:].strip()
                    second_json = self._extract_first_json_object(remaining)
                    if second_json:
                        try:
                            second_result = json.loads(second_json)
                            # 合并两个字典
                            result.update(second_result)
                            logger.info(f"[BestsellerAnalyzer] 检测到并合并了第二个JSON对象")
                        except:
                            pass
                
                return result
            except Exception as e:
                logger.warning(f"提取第一个JSON失败: {e}")
        
        # 回退：尝试提取任意花括号内容
        brace_match = re.search(r'\{.*\}', text, re.DOTALL)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except:
                pass
        
        return {"raw_text": text[:500], "parse_error": True}
    
    def _extract_first_json_object(self, text: str) -> Optional[str]:
        """
        从文本中提取第一个完整的JSON对象
        
        Args:
            text: 包含JSON的文本
            
        Returns:
            第一个JSON对象的字符串，如果没有则返回None
        """
        text = text.strip()
        if not text.startswith('{'):
            return None
        
        brace_count = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        return text[:i+1]
        
        return None
    
    def _load_persistent_cache(self):
        """从磁盘加载持久化缓存"""
        try:
            cache_file = self._cache_dir / "bestseller_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 检查缓存是否过期
                now = datetime.now()
                valid_cache = {}
                for genre, item in data.items():
                    cached_at = item.get('cached_at', '')
                    if cached_at:
                        try:
                            cache_time = datetime.fromisoformat(cached_at)
                            age_days = (now - cache_time).days
                            if age_days < self.CACHE_TTL_DAYS:
                                valid_cache[genre] = item.get('data', {})
                                logger.info(f"[BestsellerAnalyzer] 加载缓存: {genre} ({age_days}天前)")
                            else:
                                logger.info(f"[BestsellerAnalyzer] 缓存过期: {genre} ({age_days}天前)")
                        except:
                            pass
                
                self._cache = valid_cache
                logger.info(f"[BestsellerAnalyzer] 持久化缓存加载完成: {len(valid_cache)} 个类型")
        except Exception as e:
            logger.warning(f"[BestsellerAnalyzer] 加载持久化缓存失败: {e}")
            self._cache = {}
    
    def _save_persistent_cache(self, genre: str, result: Dict):
        """保存分析结果到持久化缓存"""
        try:
            cache_file = self._cache_dir / "bestseller_cache.json"
            
            # 读取现有缓存
            existing = {}
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            
            # 更新缓存
            existing[genre] = {
                'cached_at': datetime.now().isoformat(),
                'data': result
            }
            
            # 保存
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[BestsellerAnalyzer] 缓存已持久化: {genre}")
        except Exception as e:
            logger.warning(f"[BestsellerAnalyzer] 持久化缓存保存失败: {e}")
    
    def get_cached_genres(self) -> List[str]:
        """获取当前已缓存的所有类型"""
        return list(self._cache.keys())
    
    def clear_expired_cache(self):
        """清理过期缓存"""
        try:
            cache_file = self._cache_dir / "bestseller_cache.json"
            if not cache_file.exists():
                return
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            now = datetime.now()
            valid_data = {}
            removed_count = 0
            
            for genre, item in data.items():
                cached_at = item.get('cached_at', '')
                if cached_at:
                    try:
                        cache_time = datetime.fromisoformat(cached_at)
                        age_days = (now - cache_time).days
                        if age_days < self.CACHE_TTL_DAYS:
                            valid_data[genre] = item
                        else:
                            removed_count += 1
                    except:
                        valid_data[genre] = item
                else:
                    valid_data[genre] = item
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(valid_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[BestsellerAnalyzer] 清理过期缓存完成，移除 {removed_count} 个")
        except Exception as e:
            logger.warning(f"[BestsellerAnalyzer] 清理过期缓存失败: {e}")
    
    def _save_analysis_log(self, genre: str, prompt: str, result: Dict):
        """保存分析日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"bestseller_analysis_{genre.replace('/', '_')}_{timestamp}.md"
        
        lines = [
            f"# 📚 爆款反向工程分析 - {genre}",
            "",
            f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 分析Prompt",
            "",
            "```",
            prompt[:2000] + "..." if len(prompt) > 2000 else prompt,
            "```",
            "",
            "## 分析结果",
            "",
            "```json",
            json.dumps(result, ensure_ascii=False, indent=2),
            "```"
        ]
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            logger.info(f"[BestsellerAnalyzer] 分析日志已保存: {log_file}")
        except Exception as e:
            logger.error(f"保存分析日志失败: {e}")
    
    def _get_default_analysis(self, genre: str) -> Dict:
        """默认分析（当API调用失败时返回基本结构）"""
        return {
            "genre_formula": "底层逆袭套路：困境→觉醒→成长→逆袭",
            "opening_3_chapters": {
                "chapter_1": {"scene": "待AI分析", "hook": "等待分析"},
                "chapter_2": {"scene": "待AI分析", "hook": "等待分析"},
                "chapter_3": {"scene": "待AI分析", "hook": "等待分析"}
            },
            "golden_finger_formula": {"initial_reward": "待分析", "growth_curve": "待分析"},
            "character_formula": {"protagonist": {"archetype": "待分析"}},
            "emotion_formula": {"cycle": "待分析"},
            "climax_formula": {"small_climax": {"interval": 3}},
            "note": "API调用失败，返回默认结构，请检查API配置"
        }
