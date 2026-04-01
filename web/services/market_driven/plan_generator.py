# -*- coding: utf-8 -*-
"""
Market Driven Plan Generator
市场导向方案生成器

基于套路模板生成小说方案，不创新，只复用成功公式
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketDrivenPlanGenerator:
    """
    市场导向方案生成器
    基于AI分析的套路，生成符合爆款公式的小说方案
    """
    
    # 番茄小说标签映射（包含男女频差异）
    FANQIE_TAG_MAPPINGS = {
        # === 男频标签 ===
        "male": {
            "神豪文-花钱返利类": {
                "main_category": "都市",
                "themes": ["神豪", "赚钱", "逆袭"],
                "roles": ["屌丝", "神豪", "美女"],
                "plots": ["系统流", "打脸", "逆袭"]
            },
            "国运文-直播类": {
                "main_category": "都市",
                "themes": ["国运", "直播", "无敌流"],
                "roles": ["主播", "选手", "观众"],
                "plots": ["直播流", "国运流", "召唤流"]
            },
            "国运文-扮演类": {
                "main_category": "都市",
                "themes": ["国运", "扮演", "无敌流"],
                "roles": ["扮演者", "选手", "历史人物"],
                "plots": ["扮演流", "国运流", "召唤流"]
            },
            "奶爸文-萌宝类": {
                "main_category": "都市",
                "themes": ["奶爸", "萌宝", "温馨"],
                "roles": ["奶爸", "萌娃", "宝妈"],
                "plots": ["带娃流", "温馨流", "日常流"]
            },
            "签到文-系统类": {
                "main_category": "都市",
                "themes": ["签到", "系统", "无敌流"],
                "roles": ["普通人", "强者", "美女"],
                "plots": ["签到流", "系统流", "无敌流"]
            },
            "末日求生-囤货类": {
                "main_category": "科幻",
                "themes": ["末日", "囤货", "求生"],
                "roles": ["求生者", "幸存者", "异能者"],
                "plots": ["末日流", "囤货流", "求生流"]
            },
            "灵气复苏-修炼类": {
                "main_category": "都市",
                "themes": ["灵气复苏", "修炼", "无敌流"],
                "roles": ["修炼者", "强者", "校花"],
                "plots": ["灵气复苏流", "修炼流", "无敌流"]
            },
            "四合院-年代类": {
                "main_category": "都市",
                "themes": ["四合院", "年代", "日常"],
                "roles": ["普通工人", "贤妻", "反派"],
                "plots": ["年代流", "日常流", "怼禽流"]
            },
            "玄幻-东方玄幻": {
                "main_category": "玄幻",
                "themes": ["东方玄幻", "热血", "冒险"],
                "roles": ["少年", "强者", "美女"],
                "plots": ["废柴流", "逆袭流", "升级流"]
            },
            "修仙-凡人流": {
                "main_category": "仙侠",
                "themes": ["修仙", "凡人流", "长生"],
                "roles": ["散修", "天才", "仙子"],
                "plots": ["凡人流", "升级流", "夺宝流"]
            },
            "同人-动漫同人": {
                "main_category": "轻小说",
                "themes": ["同人", "动漫", "穿越"],
                "roles": ["穿越者", "原着角色", "改变者"],
                "plots": ["同人流", "改变剧情", "收女流"]
            },
            "同人-影视同人": {
                "main_category": "轻小说",
                "themes": ["同人", "影视", "穿越"],
                "roles": ["穿越者", "原着角色", "改变者"],
                "plots": ["同人流", "改变剧情", "收女流"]
            },
            "同人-小说同人": {
                "main_category": "轻小说",
                "themes": ["同人", "小说", "穿越"],
                "roles": ["穿越者", "原着角色", "改变者"],
                "plots": ["同人流", "改变剧情", "掠夺机缘"]
            }
        },
        # === 女频标签 ===
        "female": {
            "甜宠文-总裁类": {
                "main_category": "现代言情",
                "themes": ["甜宠", "总裁", "豪门"],
                "roles": ["女主", "总裁", "情敌"],
                "plots": ["先婚后爱", "追妻火葬场", "甜宠"]
            },
            "重生文-复仇类": {
                "main_category": "古代言情",
                "themes": ["重生", "复仇", "宅斗"],
                "roles": ["重生女主", "王爷", "白莲花"],
                "plots": ["重生复仇", "宅斗", "打脸"]
            },
            "穿越文-种田类": {
                "main_category": "古代言情",
                "themes": ["穿越", "种田", "发家致富"],
                "roles": ["穿越女", "猎户", "极品亲戚"],
                "plots": ["种田流", "发家致富", "经商"]
            },
            "快穿文-攻略类": {
                "main_category": "科幻空间",
                "themes": ["快穿", "攻略", "虐渣"],
                "roles": ["快穿女主", "男主", "炮灰"],
                "plots": ["快穿", "攻略男主", "虐渣打脸"]
            },
            "娱乐圈-逆袭类": {
                "main_category": "现代言情",
                "themes": ["娱乐圈", "逆袭", "系统"],
                "roles": ["女明星", "影帝", "经纪人"],
                "plots": ["逆袭", "系统", "打脸"]
            },
            "玄幻言情-修仙类": {
                "main_category": "仙侠奇缘",
                "themes": ["修仙", "师徒", "逆袭"],
                "roles": ["女修", "师尊", "魔尊"],
                "plots": ["师徒恋", "逆袭", "虐渣"]
            }
        }
    }
    
    # 默认标签（当题材未找到映射时使用）
    DEFAULT_TAGS = {
        "male": {
            "main_category": "都市",
            "themes": ["系统", "爽文", "无敌流"],
            "roles": ["男主", "美女", "反派"],
            "plots": ["系统流", "打脸", "逆袭"]
        },
        "female": {
            "main_category": "现代言情",
            "themes": ["甜宠", "爽文", "豪门"],
            "roles": ["女主", "男主", "女配"],
            "plots": ["甜宠", "打脸", "逆袭"]
        }
    }
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def generate_plan(self, genre: str, tropes: Dict, user_choices: Dict) -> Dict:
        """
        基于套路生成小说方案
        
        Args:
            genre: 题材
            tropes: 套路分析结果
            user_choices: 用户选择（在套路框架内的微调）
            
        Returns:
            完整的小说方案
        """
        logger.info(f"[PlanGenerator] 开始生成方案: {genre}")
        
        # 1. 生成标题选项
        titles = self._generate_titles(genre, tropes, user_choices)
        
        # 2. 生成开局设计
        opening = self._generate_opening(genre, tropes, user_choices)
        
        # 3. 生成金手指设计
        golden_finger = self._generate_golden_finger(tropes, user_choices)
        
        # 4. 生成主角人设
        protagonist = self._generate_protagonist(tropes, user_choices)
        
        # 🔥 移除：不再生成前30章固定大纲（outline_first_30）
        # 详细章节规划改由 TacticalPlanner 动态生成
        # outline = self._generate_outline(tropes, user_choices)
        
        # 5. 生成核心卖点
        selling_points = self._generate_selling_points(tropes)
        
        # 6. 生成番茄上传标签（关键！用于自动上传）
        tags = self._generate_fanqie_tags(genre, tropes, user_choices)
        
        plan = {
            "genre": genre,
            "generated_at": datetime.now().isoformat(),
            "generation_mode": "market_driven",
            
            # 标题选项
            "title_options": titles,
            "recommended_title": titles[0] if titles else "",
            
            # 开局设计
            "opening_design": opening,
            
            # 金手指
            "golden_finger": golden_finger,
            
            # 主角人设
            "protagonist": protagonist,
            
            # 🔥 移除：outline_first_30 不再在一阶段生成
            # 章节详细规划由 TacticalPlanner 在生成阶段动态提供
            # "outline_first_30": outline,
            
            # 核心卖点
            "core_selling_points": selling_points,
            
            # 番茄上传标签（关键字段！novel_publisher.py 依赖此字段）
            "tags": tags,
            
            # 用户选择记录
            "user_choices": user_choices,
            
            # 套路依据
            "trope_basis": {
                "core_formula": tropes.get("core_formula", ""),
                "must_have": tropes.get("must_have", []),
                "must_not_have": tropes.get("must_not_have", [])
            }
        }
        
        logger.info(f"[PlanGenerator] 方案生成完成: {genre}")
        logger.info(f"[PlanGenerator] 番茄标签: 主分类={tags['main_category']}, 受众={tags['target_audience']}")
        return plan
    
    def _generate_titles(self, genre: str, tropes: Dict, user_choices: Dict) -> List[str]:
        """
        生成符合套路的标题选项
        确保每次生成的标题都是唯一的，避免重复
        """
        import random
        import time
        
        # 从套路中提取标题风格
        title_tips = tropes.get("platform_tips", {}).get("title_examples", [])
        
        # 生成唯一种子，确保每次调用AI都生成不同结果
        unique_seed = int(time.time() * 1000) % 10000
        
        if self.api_client:
            # 使用AI生成标题
            prompt = f"""
            你是一位深谙番茄小说标题技巧的编辑。
            
            该题材的爆款标题风格：
            {json.dumps(title_tips, ensure_ascii=False)}
            
            用户选择的开局：{user_choices.get('opening_scenario', '送外卖')}
            金手指：{tropes.get('golden_finger', {}).get('type', '系统')}
            
            标题要求：
            - 15字以内
            - 有冲击力，一眼抓住读者
            - 包含核心爽点（系统、神豪、返利等）
            - 符合番茄风格
            - 必须与之前生成的标题不同，勿重复常见套路标题
            
            唯一标识（确保生成唯一性）：{unique_seed}
            
            请生成5个创意独特、从未见过的标题选项，按推荐程度排序。
            只返回标题列表，不要解释。
            
            格式：["标题1", "标题2", "标题3", "标题4", "标题5"]
            """
            
            try:
                response = self.api_client.generate_content_with_retry(
                    content_type="title_generation",
                    user_prompt=prompt,
                    temperature=0.9  # 提高temperature增加多样性
                )
                
                titles = []
                if isinstance(response, list):
                    titles = response[:5]
                elif isinstance(response, str):
                    try:
                        titles = json.loads(response)[:5]
                    except:
                        pass
                
                # 确保标题不为空
                if titles and len(titles) > 0:
                    logger.info(f"[PlanGenerator] AI生成标题: {titles}")
                    return titles
            except Exception as e:
                logger.warning(f"AI生成标题失败: {e}")
        
        # 使用默认模板，但添加随机元素确保唯一性
        return self._get_unique_default_titles(genre, user_choices)
    
    def _get_default_titles(self, genre: str, user_choices: Dict) -> List[str]:
        """
        获取唯一的默认标题
        通过扩展标题库并随机选择，确保每次生成的标题不同
        """
        import random
        import time
        
        # 初始化随机种子
        random.seed(int(time.time() * 1000))
        
        opening = user_choices.get('opening_scenario', '送外卖')
        
        # 扩展标题库（每个题材至少12个选项，确保随机性）
        title_templates = {
            "神豪文-花钱返利类": [
                "开局物价贬值百万倍", "我有九千万亿舔狗金", "神豪：从被校花拒绝开始",
                "花钱就十倍返利，我成了世界首富", "开局送外卖，我获得了花钱系统",
                "突然成为世界首富", "我的钱包有亿万", "消费十倍返利系统", "从外卖员到全球首富",
                "物价贬值后我无敌了", "开局一亿亿，花完还能赚", "神豪：花钱就能变强"
            ],
            "国运文-直播类": [
                "国运：开局扮演白起，我杀疯了", "直播国运：我为龙国开天门", "国运之战：开局召唤千古一帝",
                "绑定国运：开局扮演剑仙", "国运直播：我能召唤历史名将", "国运：我觉醒了神级天赋",
                "全球国运：我升级了龙国气运", "国运竞技：我代表龙国战斗", "国运觉醒：十万英雄降临"
            ],
            "国运文-扮演类": [
                "国运：开局扮演白起，我杀疯了", "绑定国运：开局扮演剑仙", "国运：我觉醒了神级天赋",
                "扮演雷神的我在国运战场无敌", "国运扮演：开局召唤千古一帝", "国运之战：我扮演项羽",
                "开局扮演孙悟空，我在国运战场无敌", "绑定国运：我扮演的是秦始皇"
            ],
            "奶爸文-萌宝类": [
                "奶爸：开局女儿堵门，震惊全网", "神级奶爸：萌娃助攻，妈妈找上门", "开局五个萌宝，我成了国民奶爸",
                "奶爸：从带娃开始火爆全网", "签到：开局获得神级奶爸系统", "萌娃：爸爸你是大明星",
                "神级奶爸在都市", "我家萌娃是天才", "奶爸开挂：娃娃助攻追妈妈"
            ]
        }
        
        # 获取该题材的标题库
        titles = title_templates.get(genre, [])
        if not titles:
            # 通用标题模板
            titles = [
                f"开局{opening}，我获得了系统",
                "获得系统后，我成了最强者",
                "从普通人到最强，我只用了系统",
                f"开局被羞辱，我觉醒了神级能力",
                f"从{opening}开始，我人生开挂",
                "突然觉醒，我成了万人迷",
                "获得神级能力，我无敌了",
                "开局逆天，我改写了命运"
            ]
        
        # 随机选择5个不同的标题
        selected = random.sample(titles, min(5, len(titles)))
        
        logger.info(f"[PlanGenerator] 生成唯一默认标题: {selected}")
        return selected[:5]

    def _generate_opening(self, genre: str, tropes: Dict, user_choices: Dict) -> Dict:
        """
        生成开局设计（前3章）
        严格遵循套路
        """
        opening_pattern = tropes.get("opening_pattern", {})
        
        # 用户选择的开局场景
        scenario = user_choices.get('opening_scenario', '送外卖被宝马男撞')
        
        return {
            "chapter_1": {
                "title": "开局被羞辱，获得系统",
                "must_happen": opening_pattern.get("chapter_1", "").split("→") if isinstance(opening_pattern.get("chapter_1"), str) else [
                    "主角现状展示（穷）",
                    "被羞辱（势利眼）",
                    "获得系统"
                ],
                "scenario": scenario,
                "key_scene": self._get_opening_scene_detail(scenario),
                "ending_hook": "系统激活，主角即将反击"
            },
            "chapter_2": {
                "title": "第一次花钱，震惊众人",
                "must_happen": opening_pattern.get("chapter_2", "").split("→") if isinstance(opening_pattern.get("chapter_2"), str) else [
                    "系统任务",
                    "被迫高消费",
                    "周围人震惊"
                ],
                "key_scene": f"主角使用系统资金，在{user_choices.get('first_face_slap', '4S店')}消费",
                "ending_hook": "返利到账，实力提升"
            },
            "chapter_3": {
                "title": "第一次打脸，初显神豪",
                "must_happen": opening_pattern.get("chapter_3", "").split("→") if isinstance(opening_pattern.get("chapter_3"), str) else [
                    "反派继续嘲讽",
                    "主角展示财力",
                    "第一次打脸成功"
                ],
                "key_scene": "打脸势利眼，展示系统实力",
                "ending_hook": "留下更大势力的伏笔"
            },
            "opening_principles": [
                "第1章必须出现系统",
                "第1章必须有冲突（被羞辱）",
                "前3章必须有第一次打脸",
                "节奏要快，不要铺垫"
            ]
        }
    
    def _get_opening_scene_detail(self, scenario: str) -> str:
        """获取开局场景细节"""
        scene_details = {
            "送外卖被宝马男撞": {
                "setting": "烈日下的城市街道",
                "protagonist_state": "外卖员，电动车被撞翻，餐洒了一地",
                "conflict": "宝马男下车不道歉，反而骂主角不长眼，要求赔偿",
                "humiliation": "路人围观，宝马男拿出钞票扔在主角脸上",
                "system_trigger": "主角愤怒时，系统激活"
            },
            "当保安被富二代羞辱": {
                "setting": "高档小区门口",
                "protagonist_state": "保安，月薪3000，被业主看不起",
                "conflict": "富二代业主不戴口罩硬闯，主角阻拦被辱骂",
                "humiliation": "富二代扇主角耳光，说要让主角失业",
                "system_trigger": "主角绝望时，系统激活"
            },
            "摆地摊被前女友看不起": {
                "setting": "夜市摊位",
                "protagonist_state": "摆地摊卖小商品，前女友路过",
                "conflict": "前女友和新男友（富二代）路过，当众羞辱主角",
                "humiliation": "前女友说幸好当初分手了，现在的男友多有钱",
                "system_trigger": "主角被羞辱后，系统激活"
            }
        }
        
        return scene_details.get(scenario, scene_details["送外卖被宝马男撞"])
    
    def _generate_golden_finger(self, tropes: Dict, user_choices: Dict) -> Dict:
        """
        生成金手指设计 - 强制包含所有爆款对齐要求的字段
        """
        gf_tropes = tropes.get("golden_finger", {})
        
        # 判断题材类型，选择默认模板
        genre = tropes.get("genre", "")
        if "神豪" in genre:
            default_name = "神级花钱系统"
            default_concept = "消费越多返利越多，花钱就能变强"
            default_stages = [
                {"name": "初级神豪", "range": "0-20%", "features": "10倍返利，日限额1万"},
                {"name": "中级神豪", "range": "21-40%", "features": "15倍返利，解锁透视眼"},
                {"name": "高级神豪", "range": "41-60%", "features": "20倍返利，解锁格斗术"},
                {"name": "顶级神豪", "range": "61-80%", "features": "50倍返利，全球资产"},
                {"name": "财神降世", "range": "81-100%", "features": "无限返利，掌控全球经济"}
            ]
            default_numeric = {"返利倍数": "10-100倍", "消费额度": "日限额1万-无限", "资产等级": "Lv.1-Lv.10"}
            default_trigger = "被羞辱后激活，每次消费触发返利"
            default_limitations = ["日消费限额", "不能恶意套现", "必须在正常消费场景使用"]
        elif "国运" in genre or "禁地" in genre:
            default_name = "神级扮演系统"
            default_concept = "扮演诸天强者，继承模板能力"
            default_stages = [
                {"name": "初窥门径", "range": "0-20%", "features": "基础能力觉醒，身体素质×10"},
                {"name": "略有小成", "range": "21-40%", "features": "核心技能解锁，剑气外放"},
                {"name": "炉火纯青", "range": "41-60%", "features": "领域能力觉醒，雷神领域"},
                {"name": "登峰造极", "range": "61-80%", "features": "大招完全体，万剑归宗"},
                {"name": "剑道通神", "range": "81-100%", "features": "位面主宰，一剑开天门"}
            ]
            default_numeric = {"扮演度": "0-100%", "剑意等级": "Lv.1-Lv.10", "醉酒值": "0-100（爆发加成）"}
            default_trigger = "执行符合角色性格的行为（饮酒诗百篇、仗剑行侠）或击杀禁地生物"
            default_limitations = ["觉醒大招每日限用1次", "超负荷输出导致扮演度倒退2%", "使用后进入1小时虚弱期"]
        else:
            default_name = "超级逆袭系统"
            default_concept = "通过完成任务获得奖励，不断变强"
            default_stages = [
                {"name": "新手菜鸟", "range": "0-20%", "features": "基础属性提升"},
                {"name": "初级高手", "range": "21-40%", "features": "解锁核心技能"},
                {"name": "中级强者", "range": "41-60%", "features": "属性翻倍"},
                {"name": "高级霸主", "range": "61-80%", "features": "领域觉醒"},
                {"name": "巅峰至尊", "range": "81-100%", "features": "天下无敌"}
            ]
            default_numeric = {"等级": "Lv.1-Lv.10", "经验值": "0-10000", "战力": "100-1000000"}
            default_trigger = "完成任务、击败敌人、达成成就"
            default_limitations = ["每日任务次数限制", "技能冷却时间", "能量消耗限制"]
        
        # 从 tropes 提取或生成各字段
        name = gf_tropes.get('name', '') or default_name
        concept = gf_tropes.get('concept', '') or gf_tropes.get('description', '') or default_concept
        
        # 成长阶段 - 优先使用 tropes 中的，否则用默认
        stages = gf_tropes.get('stages', [])
        if not stages:
            stages = default_stages
        
        # 成长曲线 - 从 stages 提取
        growth_curve = gf_tropes.get('growth_curve', [])
        if not growth_curve:
            growth_curve = [s["range"] for s in stages]
        
        # 数值体系
        numeric_system = gf_tropes.get('numeric_system', {})
        if not numeric_system:
            numeric_system = default_numeric
        
        # 触发机制
        trigger = gf_tropes.get('trigger_mechanism', '')
        if not trigger:
            trigger = gf_tropes.get('activation', '') or default_trigger
        
        # 限制条件
        limitations = gf_tropes.get('limitations', []) or gf_tropes.get('side_effects', [])
        if not limitations:
            limitations = default_limitations
        
        # 初始能力
        initial = gf_tropes.get('initial', '')
        if not initial:
            initial = f"{name}激活，{stages[0]['features']}"
        
        # 升级公式
        upgrade = gf_tropes.get('upgrade_formula', '')
        if not upgrade:
            upgrade = f"扮演度每提升1%，全属性增加50%。通过{trigger}提升扮演度"
        
        return {
            "name": name,
            "concept": concept,
            "initial": initial,
            "stages": stages,
            "growth_curve": growth_curve,
            "numeric_system": numeric_system,
            "trigger_mechanism": trigger,
            "limitations": limitations,
            "upgrade_formula": upgrade
        }
    
    def _generate_protagonist(self, tropes: Dict, user_choices: Dict) -> Dict:
        """
        生成主角人设
        符合读者代入感
        """
        p_tropes = tropes.get("protagonist", {})
        
        name = user_choices.get('protagonist_name', self._get_default_name())
        
        return {
            "basic_info": {
                "name": name,
                "age": 22,
                "gender": "男",
                "background": p_tropes.get("background", "穷屌丝")
            },
            
            "appearance": {
                "description": "普通长相，不帅不丑，方便读者代入",
                "dress": "初期：外卖服/保安服；后期：名牌西装",
                "presence": "后期有上位者气质"
            },
            
            "personality": {
                "core_traits": p_tropes.get("personality", "隐忍但不怂"),
                "principles": [
                    "人不犯我，我不犯人",
                    "有恩必报，有仇必报",
                    "不主动惹事，但不怕事"
                ],
                "flaws": "有时过于隐忍，爆发时才可怕",
                "growth": "从隐忍到霸气外露"
            },
            
            "initial_state": {
                "job": "外卖员/保安/摆地摊",
                "income": "月入3000",
                "living_condition": "出租屋，省吃俭用",
                "social_status": "底层，被人看不起",
                "motivation": "改变现状，出人头地"
            },
            
            "growth_arc": {
                "stage_1": {"chapter": "1-30", "status": "小有资产", "trait": "开始反击"},
                "stage_2": {"chapter": "31-80", "status": "地方富豪", "trait": "建立势力"},
                "stage_3": {"chapter": "81-150", "status": "全国富豪", "trait": "影响一方"},
                "stage_4": {"chapter": "151+", "status": "全球首富", "trait": "站在巅峰"}
            },
            
            "skills_and_abilities": {
                "initial": ["吃苦耐劳", "观察力强"],
                "from_system": ["花钱返利", "后期解锁特殊能力"],
                "developed": ["商业眼光", "领导能力", "格斗技能"]
            },
            
            "relationships": {
                "family": "父母普通工人/农民，后期被主角照顾",
                "love_interest": "初期看不起主角，后期被主角吸引",
                "friends": "少而精，都是真心朋友",
                "enemies": "势利眼→富二代→资本大佬"
            },
            
            "reader_identification": {
                "why_readers_like": "从底层逆袭，代入感强",
                "fantasy_fulfillment": "有钱能使鬼推磨，满足财富幻想",
                "emotional_resonance": "被看不起的经历很多人都有"
            }
        }
    
    def _get_default_name(self) -> str:
        """获取默认主角名"""
        # 不再随机选择，使用统一的默认名
        # 注意：实际项目中应该从user_choices获取 protagonist_name
        return "苏辰"
    
    def _generate_outline(self, tropes: Dict, user_choices: Dict) -> List[Dict]:
        """
        生成前30章情绪蓝图（不再生成固定情节，只定义情绪约束）
        """
        # 🔥 使用情绪蓝图替代固定大纲
        outline = []
        
        # 第1-3章：开局钩子（黄金三章）
        for ch in range(1, 4):
            outline.append({
                "chapter": ch,
                "phase": "开局钩子",
                "emotion_arc": "压抑→震惊→希望" if ch == 1 else "成长→收获",
                "intensity": 8 if ch == 1 else 7,
                "climax_type": "钩子章" if ch == 1 else "小爽点",
                "creative_hint": "AI自由设计具体情节"
            })
        
        # 第4-10章：小高潮密集期
        for ch in range(4, 11):
            outline.append({
                "chapter": ch,
                "phase": "小高潮密集",
                "emotion_arc": "积累→爆发→满足",
                "intensity": 7 if ch < 10 else 9,  # 第10章强度更高
                "climax_type": "小爽点" if ch < 10 else "中高潮",
                "creative_hint": "AI自由设计打脸/收获/震惊情节"
            })
        
        # 第11-20章：中期积累
        for ch in range(11, 21):
            outline.append({
                "chapter": ch,
                "phase": "中期积累",
                "emotion_arc": "平静→危机→突破",
                "intensity": 6 if ch < 18 else 8,  # 第18-20章逐渐升高
                "climax_type": "铺垫+小爽点" if ch < 18 else "中高潮",
                "creative_hint": "AI自由设计新地图/新敌人/队友成长"
            })
        
        # 第21-30章：大高潮期（AI自由创作）
        for ch in range(21, 31):
            is_climax = ch >= 28  # 最后3章是大高潮
            outline.append({
                "chapter": ch,
                "phase": "第一阶段大高潮",
                "emotion_arc": "绝望→逆转→炸裂→余波" if is_climax else "紧张→期待",
                "intensity": 10 if is_climax else 7,
                "climax_type": "大高潮" if is_climax else "铺垫",
                "must_have": ["绝境(<10%生存率)", "国际联盟(3国+)", "濒死突破", "国运级奖励"] if is_climax else [],
                "creative_hint": "AI自由创作：BOSS类型/敌人组合/战斗方式/具现奖励"
            })
        
        return outline
    
    def _generate_selling_points(self, tropes: Dict) -> List[Dict]:
        """
        生成核心卖点
        """
        return [
            {
                "point": "开局被羞辱，获得系统，强烈代入感",
                "appeal": "读者都有被看不起的经历",
                "platform_fit": "番茄读者最爱看的开局"
            },
            {
                "point": "花钱返利，越花越有钱，满足财富幻想",
                "appeal": "人人都想有钱，花钱不用心疼",
                "platform_fit": "神豪文核心爽点"
            },
            {
                "point": "连续打脸，节奏快，爽点密集",
                "appeal": "解压，让读者感到痛快",
                "platform_fit": "符合番茄快节奏风格"
            },
            {
                "point": "身份不断升级，从底层到巅峰",
                "appeal": "逆袭是人生最大爽点",
                "platform_fit": "长期追更动力"
            },
            {
                "point": "感情线自然，女主真心喜欢主角",
                "appeal": "不只是为了钱，满足情感需求",
                "platform_fit": "增加读者粘性"
            }
        ]
    
    def _generate_fanqie_tags(self, genre: str, tropes: Dict, user_choices: Dict) -> Dict:
        """
        生成番茄小说上传所需的标签信息
        
        关键字段（novel_publisher.py 依赖）：
        - main_category: 主分类（番茄界面：主分类标签页）
        - themes: 主题标签列表（番茄界面：主题标签页）
        - roles: 角色标签列表（番茄界面：角色标签页）
        - plots: 情节标签列表（番茄界面：情节标签页）
        - target_audience: 受众（男频/女频）
        
        Args:
            genre: 题材
            tropes: 套路分析
            user_choices: 用户选择
            
        Returns:
            符合番茄上传格式的标签字典
        """
        # 1. 确定男女频
        # 优先从用户选择中获取，否则根据题材判断
        target_audience = user_choices.get("target_audience", "")
        if not target_audience:
            # 根据题材判断男女频
            female_genres = ["甜宠", "重生", "穿越", "快穿", "娱乐圈", "古代言情", "现代言情", "仙侠奇缘"]
            if any(fg in genre for fg in female_genres):
                target_audience = "女频"
            else:
                target_audience = "男频"
        
        # 2. 选择对应的标签映射表
        gender_key = "female" if target_audience == "女频" else "male"
        tag_mappings = self.FANQIE_TAG_MAPPINGS.get(gender_key, self.FANQIE_TAG_MAPPINGS["male"])
        
        # 3. 查找题材对应的标签
        # 先尝试精确匹配
        tags = tag_mappings.get(genre)
        
        # 如果没有精确匹配，尝试模糊匹配
        if not tags:
            for mapped_genre, mapped_tags in tag_mappings.items():
                # 检查题材是否包含映射中的关键词
                if any(keyword in genre for keyword in mapped_genre.split("-")):
                    tags = mapped_tags
                    break
        
        # 如果仍然没有匹配，使用默认标签
        if not tags:
            tags = self.DEFAULT_TAGS.get(gender_key, self.DEFAULT_TAGS["male"])
            logger.warning(f"[PlanGenerator] 题材 '{genre}' 未找到标签映射，使用默认标签")
        
        # 4. 构建完整的标签字典
        result = {
            "main_category": tags["main_category"],
            "themes": tags["themes"][:3],  # 最多3个主题
            "roles": tags["roles"][:3],    # 最多3个角色
            "plots": tags["plots"][:3],    # 最多3个情节
            "target_audience": target_audience
        }
        
        logger.info(f"[PlanGenerator] 生成番茄标签: {result}")
        return result


# 便捷函数
def generate_market_driven_plan(genre: str, tropes: Dict, user_choices: Dict, api_client=None) -> Dict:
    """
    便捷函数：生成市场导向方案
    """
    generator = MarketDrivenPlanGenerator(api_client=api_client)
    return generator.generate_plan(genre, tropes, user_choices)
