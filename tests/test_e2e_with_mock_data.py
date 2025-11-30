"""
端到端测试 (End-to-End Test) - 使用虚假数据完整执行小说生成流程
不依赖真实API返回，而是使用模拟数据来验证系统流程正确性

测试目标:
1. 验证创意加载和处理流程
2. 验证完整的章节生成上下文构建
3. 验证内容生成管道的数据流转
4. 验证质量评估系统
5. 验证项目保存和备份流程
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch
import tempfile
import shutil

# 设置路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import get_logger
from Contexts import GenerationContext

class MockAPIClient:
    """模拟 API 客户端 - 返回虚假但结构正确的数据"""
    
    def __init__(self, config=None):
        self.logger = get_logger("MockAPIClient")
        self.config = config or {}
        self.logger.info("✅ 模拟 API 客户端已初始化")
    
    def call_api(self, messages: list, role_name: str = None, **kwargs) -> str:
        """返回模拟的 API 响应"""
        
        # 根据请求内容返回不同的模拟数据
        content = messages[-1]["content"] if messages else ""
        
        # 创意精炼
        if "精炼" in content or "指令" in content:
            return self._mock_creative_refinement()
        
        # 章节大纲生成
        elif "章节" in content and "大纲" in content:
            return self._mock_chapter_outline()
        
        # 章节内容生成
        elif "内容" in content or "情节" in content:
            return self._mock_chapter_content()
        
        # 质量评估
        elif "评估" in content or "质量" in content:
            return self._mock_quality_assessment()
        
        # 角色设计
        elif "角色" in content or "人物" in content:
            return self._mock_character_design()
        
        # 世界设定
        elif "世界" in content or "设定" in content:
            return self._mock_world_setting()
        
        # 默认返回
        else:
            return self._mock_default_response()
    
    def _mock_creative_refinement(self) -> str:
        """模拟创意精炼响应"""
        return json.dumps({
            "创意名称": "凡人修仙同人转折版",
            "核心卖点": ["观战悟道体质", "因果干涉命运", "双星微妙博弈"],
            "故事线完整度": "高",
            "可执行性": "很强",
            "必要修正建议": ["加强梅凝角色的独立性", "明确天南派系地位"],
            "最终评分": 9.2
        }, ensure_ascii=False, indent=2)
    
    def _mock_chapter_outline(self) -> str:
        """模拟章节大纲生成"""
        return json.dumps({
            "章节号": 1,
            "章节标题": "乱星观劫·初现异象",
            "核心事件": [
                "与梅凝抵达乱星海观战点",
                "见证韩立 vs 温天仁结丹巅峰战",
                "主角通过观战悟道体质悟得辟邪神雷运用技巧",
                "空间突变，三人坠入阴冥之地"
            ],
            "情感节拍": [
                "压抑的期待 → 目睹大战的震撼 → 突然的危险"
            ],
            "字数预估": "3500-4000",
            "重点描写": ["战斗细节", "主角顿悟过程", "危险降临"],
            "关键细节": {
                "主角修为伪装": "结金期后期",
                "观战收获": "对辟邪神雷的深刻理解",
                "梅凝反应": "惊恐但信任主角"
            }
        }, ensure_ascii=False, indent=2)
    
    def _mock_chapter_content(self) -> str:
        """模拟章节内容生成"""
        return """
第一章 乱星观劫·初现异象

乱星海，一片扭曲而诡异的空间。无数陨石碎片在灵气漩涡中漂浮，形成了一个天然的隐蔽之地。

"还要再等多久？"梅凝贴近我的耳边，声音压得很低。她那张精致的面容上现出一丝焦虑——这个女孩总是这样，外表坚强，内心却需要一个依靠。

我没有转身，目光依旧锁定在远方那个逐渐聚集灵气的区域。"快了。我能感觉到那两股气息正在靠近。"

此刻的我，用秘术掩盖了真实修为，伪装成一个结金期后期的修士。在梅凝的眼中，我不过是个比她高一两个小境界的同龄人——这就足够了。她不需要知道，我真实的实力早已远超结丹期。

灵气漩涡中心，两道身影倏然显现。

一人衣着朴素，面容平静，却有种难以名状的气场——那是经历过无数风雨洗礼后沉淀出来的气质。另一人穿着华贵，周身缠绕着浓密的灵气，眼神凶狠而自信。

"韩立！"我在心中默念这个名字。

这就是那位时间线上的主角——日后会飞升灵界的存在。而另一人，应该就是幽州路上的强者，温天仁。

"算了，废话少说。"温天仁率先动作，一掌拍出，天地为之一暗。巨大的灵压碾压下来，整个乱星海的陨石都在震颤。

韩立神色不变，掌心浮现出诡异的青蓝色闪电。"辟邪神雷。"

两掌相撞的瞬间，整个乱星海陷入了雷光与灵气的混乱之中。

我却在这一刻，感受到了什么。

那种感觉就像是……整个宇宙的奥秘在我面前展开了一角。我的观战悟道体质被激发到了极限，我开始看清了辟邪神雷的运转轨迹——它如何汲取天地灵气，如何在瞬间汇聚成威力最大的闪电，如何在对手毫无防备的瞬间爆发。

这不仅是战斗的展现，这是……传承。

我的脑海中，辟邪神雷的完整运作方式逐渐清晰起来。不仅仅是表面的使用方法，更包括这门神通背后的核心奥秘。

"主角……"梅凝拉了拉我的衣袖，声音中带着害怕。

但我无暇回应她。此刻的我，整个身心都沉浸在这场大战的奥秘之中。

突然——

一声天崩地裂的巨响。

空间本身开始撕裂。

"糟糕！"我的意识在一瞬间清醒。我猛地拉起梅凝，试图施展逃遁之法，但那撕裂的空间已经卷住了我们。

最后的一刻，我看到了韩立和温天仁的身影也被卷入了同样的漩涡。

然后，一切陷入了黑暗。

---

当我再次睁眼时，我们已经置身于一个完全陌生的地方。

阴冥之地。

这个名字在我脑海中浮现——这是下一个目标。而现在，我们已经到达了。

"这……这是哪里？"梅凝紧紧抓住我的手臂，声音中带着颤抖。

我深吸一口气，感受着这片区域中几近绝灵的环境，还有远处隐隐约约传来的危险气息。

"活下去。"我轻声说，"相信我。"

这句话，不仅仅是对梅凝的承诺，也是对我自己的。

在这个充满了未知和危险的世界里，我要改写的，远远不止是一个人的命运。
        """
    
    def _mock_quality_assessment(self) -> str:
        """模拟质量评估响应"""
        return json.dumps({
            "整体评分": 8.7,
            "各维度评分": {
                "情节连贯性": 8.9,
                "人物塑造": 8.5,
                "世界观一致": 8.6,
                "文字质量": 8.8,
                "爽点设置": 8.4
            },
            "优点": [
                "开局有力，快速进入主线",
                "主角性格设定清晰",
                "悟道系统展现得当",
                "女主感情线自然",
                "转折点设置有效"
            ],
            "改进建议": [
                "可以加强环境描写的细节",
                "敌人刻画还可以更深入",
                "对话节奏可以更紧凑"
            ],
            "是否需要修改": False,
            "修改建议权重": "低"
        }, ensure_ascii=False, indent=2)
    
    def _mock_character_design(self) -> str:
        """模拟角色设计响应"""
        return json.dumps({
            "主角卡": {
                "姓名": "李尘",
                "年龄": "18岁",
                "外貌": "清秀而不失刚毅，眼神深邃，气质沉着冷静",
                "身份": "穿越者，被冤枉的天才修士",
                "核心能力": [
                    "观战悟道体质 - 可通过观摩强者对战获得功法领悟",
                    "太初道体 - 结婴时引发超规格天地异象",
                    "先知优势 - 对重要事件的预知"
                ],
                "性格特征": ["沉着冷静", "重情重义", "长期规划者", "风险规避者"],
                "成长空间": "从隐藏的结丹大圆满到元婴大能，最终飞升灵界",
                "核心目标": "找到回家的方法，或在这个世界中建立自己的势力"
            },
            "女主卡": {
                "姓名": "梅凝",
                "身份": "通玉凤髓体特殊体质拥有者",
                "性格": "柔弱外表，内心坚韧",
                "感情线": "与主角在生死考验中建立深厚羁绊"
            }
        }, ensure_ascii=False, indent=2)
    
    def _mock_world_setting(self) -> str:
        """模拟世界设定响应"""
        return json.dumps({
            "世界观": "仙侠世界，等级制度明确",
            "修炼体系": {
                "阶段": ["炼气期", "筑基期", "结丹期", "元婴期", "渡劫期", "飞升"],
                "特色": "存在特殊体质和金手指系统"
            },
            "关键地点": [
                "乱星海 - 隐蔽修行地",
                "阴冥之地 - 试炼之地",
                "天南 - 主要活动区域",
                "落云宗 - 第一大派"
            ],
            "势力分布": {
                "天南": "落云宗（将成为第一大派）",
                "敌对势力": "幽州路强者",
                "中立阵营": "散修联盟"
            }
        }, ensure_ascii=False, indent=2)
    
    def _mock_default_response(self) -> str:
        """默认模拟响应"""
        return json.dumps({
            "状态": "成功",
            "数据": "这是一个模拟响应，用于测试系统流程",
            "时间戳": datetime.now().isoformat()
        }, ensure_ascii=False, indent=2)


class MockEventBus:
    """模拟事件总线"""
    
    def __init__(self):
        self.logger = get_logger("MockEventBus")
        self.listeners = {}
    
    def subscribe(self, event_type: str, callback):
        """订阅事件"""
        if event_type not in self.listeners:
            self.listeners[event_type] = []
        self.listeners[event_type].append(callback)
    
    def emit(self, event_type: str, data: Any = None):
        """发出事件"""
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.info(f"❌ 事件回调执行失败: {e}")


class MockQualityAssessor:
    """模拟质量评估器"""
    
    def __init__(self, api_client):
        self.logger = get_logger("MockQualityAssessor")
        self.api_client = api_client
    
    def assess_content_quality(self, content: str, chapter_num: int = 1) -> Dict:
        """评估内容质量"""
        self.logger.info(f"📊 评估第 {chapter_num} 章内容质量...")
        
        # 调用 API 获取评估结果
        response = self.api_client.call_api([
            {"role": "user", "content": f"请评估这一章的质量: {content[:500]}"}
        ], role_name="质量评估员")
        
        try:
            return json.loads(response)
        except:
            return {
                "整体评分": 8.5,
                "状态": "成功",
                "优点": ["情节连贯", "人物清晰"],
                "改进建议": ["可加强细节描写"]
            }
    
    def assess_plan_quality(self, plan: Dict) -> Dict:
        """评估方案质量"""
        self.logger.info("📋 评估故事方案质量...")
        return {
            "方案评分": 9.1,
            "可执行性": "很强",
            "爆款潜力": "高"
        }


class TestScenario:
    """测试场景 - 完整的端到端流程"""
    
    def __init__(self, test_name: str = "TestRun"):
        self.logger = get_logger("TestScenario")
        self.test_name = test_name
        self.test_dir = Path(tempfile.mkdtemp(prefix=f"test_{test_name}_"))
        self.api_client = MockAPIClient()
        self.event_bus = MockEventBus()
        self.quality_assessor = MockQualityAssessor(self.api_client)
        
        # 创建模拟数据
        self.mock_creative = self._create_mock_creative()
        self.mock_novel_data = self._create_mock_novel_data()
        
        self.logger.info(f"✅ 测试场景初始化完成: {self.test_name}")
        self.logger.info(f"   测试目录: {self.test_dir}")
    
    def _create_mock_creative(self) -> Dict:
        """创建模拟创意数据"""
        return {
            "coreSetting": "凡人修仙传同人，时间线从韩立与温天仁结丹巅峰大战开始。主角为穿越者，身负'观战悟道'特殊体质，可通过观摩强者对战获得功法领悟。与梅凝在乱星海共观大战后卷入阴冥之地，脱困后抵达天南。",
            "coreSellingPoints": "双星潜藏下的微妙博弈+因果干涉带来的命运变奏+观战悟道创新体系",
            "completeStoryline": {
                "opening": {
                    "stageName": "乱星观劫·阴冥托孤",
                    "summary": "乱星海观战→阴冥绝地求生→绝境情缘→天南新生",
                    "arc_goal": "完成从乱星海到落云宗的过渡，建立与梅凝的生死羁绊"
                },
                "development": {
                    "stageName": "药园潜龙·双星暗弈",
                    "summary": "同期入宗→初识沛灵→微妙试探→资源暗争→情愫暗生",
                    "arc_goal": "建立稳固的潜伏环境，完成结婴前所有准备"
                },
                "conflict": {
                    "stageName": "元婴双曜·天南惊变",
                    "summary": "结婴天兆→韩立结婴→地位重定→幕兰来袭→沛灵元婴",
                    "arc_goal": "成功结婴并确立顶尖地位，深化女主情感关系"
                },
                "ending": {
                    "stageName": "道途共行·灵界曙光",
                    "summary": "道侣同心→知己至交→双星并立→宗门鼎盛→灵界之约",
                    "arc_goal": "实现个人、情感、宗门的圆满，为飞升灵界铺垫"
                }
            }
        }
    
    def _create_mock_novel_data(self) -> Dict:
        """创建模拟小说数据"""
        return {
            "novel_title": "凡人修仙同人·观战者",
            "novel_synopsis": "穿越者李尘身具观战悟道体质，通过观摩强者对战获得修行启悟。在乱星海见证韩立与温天仁的巅峰大战后，与梅凝坠入阴冥之地。历经生死考验后抵达天南，与韩立同期入落云宗，开始了一段充满微妙博弈与因果干涉的命运交织。",
            "novel_author": "AI系统",
            "novel_category": "网络文学 / 穿越 / 同人",
            "novel_genre": "仙侠",
            "total_chapters": 50,
            "current_progress": {
                "completed_chapters": 0,
                "current_chapter": 1,
                "characters": {
                    "主角": {
                        "name": "李尘",
                        "status": "初始化",
                        "abilities": ["观战悟道体质"]
                    },
                    "女主": {
                        "name": "梅凝",
                        "status": "初始化",
                        "abilities": ["通玉凤髓体"]
                    }
                }
            },
            "world_state": {
                "current_location": "乱星海",
                "main_storyline": "opening",
                "events_log": []
            }
        }
    
    def test_creative_loading(self):
        """测试 1: 创意加载"""
        self.logger.info("=" * 60)
        self.logger.info("测试 1: 创意数据加载 (Creative Loading)")
        self.logger.info("=" * 60)
        
        try:
            assert self.mock_creative["coreSetting"], "创意设定为空"
            assert self.mock_creative["coreSellingPoints"], "核心卖点为空"
            assert self.mock_creative["completeStoryline"], "完整故事线为空"
            
            self.logger.info("✅ 创意设定加载成功")
            self.logger.info(f"   核心设定: {self.mock_creative['coreSetting'][:50]}...")
            self.logger.info(f"   核心卖点: {self.mock_creative['coreSellingPoints']}")
            
            return True, "创意加载成功"
        except AssertionError as e:
            self.logger.info(f"❌ 创意加载失败: {e}")
            return False, str(e)
    
    def test_novel_initialization(self):
        """测试 2: 小说初始化"""
        self.logger.info("=" * 60)
        self.logger.info("测试 2: 小说初始化 (Novel Initialization)")
        self.logger.info("=" * 60)
        
        try:
            assert self.mock_novel_data["novel_title"], "小说标题为空"
            assert self.mock_novel_data["novel_synopsis"], "小说简介为空"
            assert self.mock_novel_data["total_chapters"] > 0, "总章节数无效"
            
            self.logger.info("✅ 小说初始化成功")
            self.logger.info(f"   标题: {self.mock_novel_data['novel_title']}")
            self.logger.info(f"   总章节数: {self.mock_novel_data['total_chapters']}")
            self.logger.info(f"   简介: {self.mock_novel_data['novel_synopsis'][:50]}...")
            
            return True, "小说初始化成功"
        except AssertionError as e:
            self.logger.info(f"❌ 小说初始化失败: {e}")
            return False, str(e)
    
    def test_generation_context_creation(self):
        """测试 3: 生成上下文创建"""
        self.logger.info("=" * 60)
        self.logger.info("测试 3: 生成上下文创建 (Generation Context)")
        self.logger.info("=" * 60)
        
        try:
            # 创建生成上下文
            context = GenerationContext(
                chapter_number=1,
                total_chapters=50,
                novel_data=self.mock_novel_data,
                stage_plan=self.mock_creative["completeStoryline"]["opening"],
                event_context={},
                foreshadowing_context={},
                growth_context={},
                expectation_context={}
            )
            
            # 验证上下文
            is_valid, message = context.validate()
            assert is_valid, f"上下文验证失败: {message}"
            
            self.logger.info("✅ 生成上下文创建成功")
            self.logger.info(f"   {context}")
            self.logger.info(f"   章节信息: {context.chapter_number}/{context.total_chapters}")
            
            return True, "生成上下文创建成功"
        except Exception as e:
            self.logger.info(f"❌ 生成上下文创建失败: {e}")
            return False, str(e)
    
    def test_chapter_outline_generation(self):
        """测试 4: 章节大纲生成"""
        self.logger.info("=" * 60)
        self.logger.info("测试 4: 章节大纲生成 (Chapter Outline Generation)")
        self.logger.info("=" * 60)
        
        try:
            # 调用 API 获取章节大纲
            response = self.api_client.call_api([
                {"role": "user", "content": "生成第1章大纲"}
            ], role_name="大纲生成器")
            
            outline = json.loads(response)
            
            assert outline["章节号"] > 0, "章节号无效"
            assert outline["章节标题"], "章节标题为空"
            assert outline["核心事件"], "核心事件为空"
            
            self.logger.info("✅ 章节大纲生成成功")
            self.logger.info(f"   标题: {outline['章节标题']}")
            self.logger.info(f"   核心事件数: {len(outline['核心事件'])}")
            self.logger.info(f"   字数预估: {outline['字数预估']}")
            
            return True, "章节大纲生成成功", outline
        except Exception as e:
            self.logger.info(f"❌ 章节大纲生成失败: {e}")
            return False, str(e), None
    
    def test_chapter_content_generation(self):
        """测试 5: 章节内容生成"""
        self.logger.info("=" * 60)
        self.logger.info("测试 5: 章节内容生成 (Chapter Content Generation)")
        self.logger.info("=" * 60)
        
        try:
            # 调用 API 生成章节内容
            response = self.api_client.call_api([
                {"role": "user", "content": "生成第1章具体内容"}
            ], role_name="内容生成器")
            
            content = response
            
            assert len(content) > 100, "生成的内容过短"
            assert "第" in content and "章" in content, "内容缺少章节标记"
            
            word_count = len(content)
            self.logger.info("✅ 章节内容生成成功")
            self.logger.info(f"   字数: {word_count}")
            self.logger.info(f"   内容预览: {content[:100]}...")
            
            return True, "章节内容生成成功", content
        except Exception as e:
            self.logger.info(f"❌ 章节内容生成失败: {e}")
            return False, str(e), None
    
    def test_quality_assessment(self):
        """测试 6: 质量评估"""
        self.logger.info("=" * 60)
        self.logger.info("测试 6: 质量评估 (Quality Assessment)")
        self.logger.info("=" * 60)
        
        try:
            # 获取模拟内容
            response = self.api_client.call_api([
                {"role": "user", "content": "生成章节内容"}
            ])
            
            # 评估质量
            assessment = self.quality_assessor.assess_content_quality(response, chapter_num=1)
            
            assert "整体评分" in assessment or "状态" in assessment, "评估结果格式错误"
            
            self.logger.info("✅ 质量评估成功")
            self.logger.info(f"   整体评分: {assessment.get('整体评分', 'N/A')}")
            self.logger.info(f"   优点: {assessment.get('优点', [])}")
            
            return True, "质量评估成功", assessment
        except Exception as e:
            self.logger.info(f"❌ 质量评估失败: {e}")
            return False, str(e), None
    
    def test_data_persistence(self):
        """测试 7: 数据持久化"""
        self.logger.info("=" * 60)
        self.logger.info("测试 7: 数据持久化 (Data Persistence)")
        self.logger.info("=" * 60)
        
        try:
            # 创建输出目录
            output_dir = self.test_dir / "output"
            output_dir.mkdir(exist_ok=True)
            
            # 保存创意数据
            creative_file = output_dir / "creative.json"
            with open(creative_file, 'w', encoding='utf-8') as f:
                json.dump(self.mock_creative, f, ensure_ascii=False, indent=2)
            
            assert creative_file.exists(), "创意文件保存失败"
            
            # 保存小说数据
            novel_file = output_dir / "novel_data.json"
            with open(novel_file, 'w', encoding='utf-8') as f:
                json.dump(self.mock_novel_data, f, ensure_ascii=False, indent=2)
            
            assert novel_file.exists(), "小说数据文件保存失败"
            
            # 保存生成的章节
            chapter_file = output_dir / "chapter_001.txt"
            response = self.api_client.call_api([{"role": "user", "content": "生成内容"}])
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write(response)
            
            assert chapter_file.exists(), "章节文件保存失败"
            
            self.logger.info("✅ 数据持久化成功")
            self.logger.info(f"   创意文件: {creative_file}")
            self.logger.info(f"   小说数据: {novel_file}")
            self.logger.info(f"   章节文件: {chapter_file}")
            
            return True, "数据持久化成功"
        except Exception as e:
            self.logger.info(f"❌ 数据持久化失败: {e}")
            return False, str(e)
    
    def test_complete_pipeline(self):
        """测试 8: 完整流程 (5章生成)"""
        self.logger.info("=" * 60)
        self.logger.info("测试 8: 完整流程 (Complete Pipeline - 5 Chapters)")
        self.logger.info("=" * 60)
        
        try:
            output_dir = self.test_dir / "novel_output"
            output_dir.mkdir(exist_ok=True)
            
            chapters_generated = []
            
            for chapter_num in range(1, 6):  # 生成5章
                self.logger.info(f"\n   【章节 {chapter_num}/5】")
                
                # 1. 生成大纲
                outline_response = self.api_client.call_api([
                    {"role": "user", "content": f"生成第{chapter_num}章大纲"}
                ])
                outline = json.loads(outline_response)
                self.logger.info(f"      ✓ 大纲: {outline.get('章节标题', '未知标题')}")
                
                # 2. 生成内容
                content_response = self.api_client.call_api([
                    {"role": "user", "content": f"生成第{chapter_num}章内容"}
                ])
                self.logger.info(f"      ✓ 内容: {len(content_response)} 字")
                
                # 3. 质量评估
                assessment = self.quality_assessor.assess_content_quality(
                    content_response, chapter_num=chapter_num
                )
                score = assessment.get("整体评分", assessment.get("评分", 8.5))
                self.logger.info(f"      ✓ 评分: {score}")
                
                # 4. 保存文件
                chapter_file = output_dir / f"chapter_{chapter_num:03d}.json"
                chapter_data = {
                    "chapter_number": chapter_num,
                    "title": outline.get("章节标题", f"第{chapter_num}章"),
                    "outline": outline,
                    "content": content_response,
                    "assessment": assessment,
                    "generated_at": datetime.now().isoformat()
                }
                
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    json.dump(chapter_data, f, ensure_ascii=False, indent=2)
                
                chapters_generated.append(chapter_data)
            
            self.logger.info(f"\n✅ 完整流程执行成功")
            self.logger.info(f"   生成章节数: {len(chapters_generated)}")
            self.logger.info(f"   输出目录: {output_dir}")
            
            return True, "完整流程执行成功", chapters_generated
        except Exception as e:
            self.logger.info(f"❌ 完整流程执行失败: {e}")
            return False, str(e), None
    
    def run_all_tests(self):
        """运行所有测试"""
        self.logger.info("\n\n")
        self.logger.info("🚀" * 30)
        self.logger.info("开始执行端到端测试 (E2E Test Suite)")
        self.logger.info(f"测试名称: {self.test_name}")
        self.logger.info(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("🚀" * 30)
        
        results = []
        
        # 执行所有测试
        test_functions = [
            ("创意加载", self.test_creative_loading),
            ("小说初始化", self.test_novel_initialization),
            ("生成上下文", self.test_generation_context_creation),
            ("章节大纲", self.test_chapter_outline_generation),
            ("章节内容", self.test_chapter_content_generation),
            ("质量评估", self.test_quality_assessment),
            ("数据持久化", self.test_data_persistence),
            ("完整流程", self.test_complete_pipeline),
        ]
        
        for test_name, test_func in test_functions:
            try:
                result = test_func()
                results.append((test_name, result[0], result[1]))
            except Exception as e:
                results.append((test_name, False, f"测试异常: {e}"))
        
        # 生成测试报告
        self._generate_test_report(results)
        
        return results
    
    def _generate_test_report(self, results):
        """生成测试报告"""
        self.logger.info("\n\n")
        self.logger.info("=" * 60)
        self.logger.info("📊 测试报告总结 (Test Report Summary)")
        self.logger.info("=" * 60)
        
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        
        for test_name, success, message in results:
            status = "✅ PASS" if success else "❌ FAIL"
            self.logger.info(f"{status} | {test_name}: {message}")
        
        self.logger.info("=" * 60)
        self.logger.info(f"📈 总体: {passed}/{total} 测试通过 ({100*passed/total:.1f}%)")
        self.logger.info(f"📁 测试目录: {self.test_dir}")
        self.logger.info("=" * 60)
        
        # 保存报告到文件
        report_file = self.test_dir / "test_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(f"测试报告: {self.test_name}\n")
            f.write(f"时间: {datetime.now().isoformat()}\n")
            f.write("=" * 60 + "\n\n")
            
            for test_name, success, message in results:
                status = "PASS" if success else "FAIL"
                f.write(f"[{status}] {test_name}: {message}\n")
            
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"总体: {passed}/{total} 测试通过 ({100*passed/total:.1f}%)\n")
        
        self.logger.info(f"✅ 报告已保存: {report_file}")


def main():
    """主测试函数"""
    # 创建测试场景
    test = TestScenario("凡人修仙同人E2E测试")
    
    # 运行所有测试
    results = test.run_all_tests()
    
    # 统计结果
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    print(f"\n\n测试完成！通过率: {100*passed/total:.1f}% ({passed}/{total})")
    print(f"测试目录: {test.test_dir}")
    
    # 清理（可选 - 注释掉以保留测试数据）
    # shutil.rmtree(test.test_dir)


if __name__ == "__main__":
    main()
