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
        
        # 5. 生成前30章大纲
        outline = self._generate_outline(tropes, user_choices)
        
        # 6. 生成核心卖点
        selling_points = self._generate_selling_points(tropes)
        
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
            
            # 前30章大纲
            "outline_first_30": outline,
            
            # 核心卖点
            "core_selling_points": selling_points,
            
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
        return plan
    
    def _generate_titles(self, genre: str, tropes: Dict, user_choices: Dict) -> List[str]:
        """
        生成符合套路的标题选项
        """
        # 从套路中提取标题风格
        title_tips = tropes.get("platform_tips", {}).get("title_examples", [])
        
        if self.api_client:
            # 使用AI生成标题
            prompt = f"""
            你是一位深谙番茄小说标题技巧的编辑。
            
            该题材的爆款标题风格：
            {json.dumps(title_tips, ensure_ascii=False)}
            
            标题要求：
            - 15字以内
            - 有冲击力，一眼抓住读者
            - 包含核心爽点（系统、神豪、返利等）
            - 符合番茄风格
            
            用户选择的开局：{user_choices.get('opening_scenario', '送外卖')}
            金手指：{tropes.get('golden_finger', {}).get('type', '系统')}
            
            请生成5个标题选项，按推荐程度排序。
            只返回标题列表，不要解释。
            
            格式：["标题1", "标题2", "标题3", "标题4", "标题5"]
            """
            
            try:
                response = self.api_client.generate_content_with_retry(
                    content_type="title_generation",
                    user_prompt=prompt,
                    temperature=0.7
                )
                
                if isinstance(response, list):
                    return response[:5]
                elif isinstance(response, str):
                    try:
                        return json.loads(response)[:5]
                    except:
                        pass
            except Exception as e:
                logger.warning(f"AI生成标题失败: {e}")
        
        # 默认标题模板
        return self._get_default_titles(genre, user_choices)
    
    def _get_default_titles(self, genre: str, user_choices: Dict) -> List[str]:
        """获取默认标题"""
        opening = user_choices.get('opening_scenario', '送外卖')
        
        title_templates = {
            "神豪文-花钱返利类": [
                "开局物价贬值百万倍",
                "我有九千万亿舔狗金",
                "神豪：从被校花拒绝开始",
                "花钱就十倍返利，我成了世界首富",
                "开局送外卖，我获得了花钱系统"
            ],
            "国运文-直播类": [
                "国运：开局扮演白起，我杀疯了",
                "直播国运：我为龙国开天门",
                "国运之战：开局召唤千古一帝",
                "绑定国运：开局扮演剑仙",
                "国运直播：我能召唤历史名将"
            ],
            "奶爸文-萌宝类": [
                "奶爸：开局女儿堵门，震惊全网",
                "神级奶爸：萌娃助攻，妈妈找上门",
                "开局五个萌宝，我成了国民奶爸",
                "奶爸：从带娃开始火爆全网",
                "签到：开局获得神级奶爸系统"
            ]
        }
        
        return title_templates.get(genre, [
            f"开局{opening}，我获得了系统",
            "获得系统后，我成了最强者",
            "从普通人到最强，我只用了系统"
        ])
    
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
        生成金手指设计
        严格遵循套路规律
        """
        gf_tropes = tropes.get("golden_finger", {})
        
        return {
            "name": "神豪花钱系统" if "神豪" in tropes.get("genre", "") else "超级系统",
            "type": gf_tropes.get("type", "系统"),
            "core_mechanism": gf_tropes.get("ratio", "10倍返利"),
            "activation_condition": gf_tropes.get("activation", "被羞辱后激活"),
            "initial_limitation": gf_tropes.get("limitation", "初期每天限额1万元"),
            "upgrade_method": gf_tropes.get("upgrade", "消费达标后升级"),
            
            "level_system": [
                {
                    "level": 1,
                    "name": "初级神豪",
                    "unlock_condition": "激活系统",
                    "daily_limit": "1万元",
                    "rebate_ratio": "10倍",
                    "special_ability": "无"
                },
                {
                    "level": 2,
                    "name": "中级神豪",
                    "unlock_condition": "累计消费10万元",
                    "daily_limit": "10万元",
                    "rebate_ratio": "15倍",
                    "special_ability": "获得透视眼（用于赌石）"
                },
                {
                    "level": 3,
                    "name": "高级神豪",
                    "unlock_condition": "累计消费100万元",
                    "daily_limit": "100万元",
                    "rebate_ratio": "20倍",
                    "special_ability": "获得格斗术（用于防身）"
                }
            ],
            
            "usage_rules": [
                "必须在正常消费场景使用",
                "不能恶意套现",
                "完成任务有额外奖励",
                "升级后解锁新功能"
            ],
            
            "narrative_function": [
                "提供资金来源",
                "制造装逼机会",
                "推动主角成长",
                "创造爽点"
            ]
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
        import random
        names = ["夏天", "叶辰", "林凡", "萧战", "秦风", "杨明", "张浩", "李强"]
        return random.choice(names)
    
    def _generate_outline(self, tropes: Dict, user_choices: Dict) -> List[Dict]:
        """
        生成前30章大纲
        严格遵循节奏套路
        """
        pacing = tropes.get("pacing", {})
        
        outline = []
        
        # 第1-10章：开局激活
        outline.extend([
            {"chapter": 1, "title": "开局被羞辱，获得系统", "event": "系统激活", "climax": "转折", "emotion": "愤怒→希望"},
            {"chapter": 2, "title": "第一次花钱，震惊众人", "event": "第一次消费", "climax": "小爽点", "emotion": "紧张→爽快"},
            {"chapter": 3, "title": "打脸势利眼，初显神豪", "event": "第一次打脸", "climax": "爽点", "emotion": "压抑→爆发"},
            {"chapter": 4, "title": "返利到账，实力提升", "event": "资金到账", "climax": "小爽点", "emotion": "期待→满足"},
            {"chapter": 5, "title": "前女友后悔，跪求复合", "event": "前女友打脸", "climax": "爽点", "emotion": "爽"},
            {"chapter": 6, "title": "购买豪车，身份升级", "event": "买豪车", "climax": "爽点", "emotion": "爽"},
            {"chapter": 7, "title": "遇到新女主，英雄救美", "event": "女主登场", "climax": "小爽点", "emotion": "紧张→心动"},
            {"chapter": 8, "title": "富二代挑衅，主角隐忍", "event": "新冲突", "climax": "压抑", "emotion": "愤怒→隐忍"},
            {"chapter": 9, "title": "系统升级，能力增强", "event": "系统升级", "climax": "小爽点", "emotion": "期待→满足"},
            {"chapter": 10, "title": "当众打脸富二代", "event": "第一个大高潮", "climax": "大爽点", "emotion": "爆发→爽快"}
        ])
        
        # 第11-20章：小有名气
        outline.extend([
            {"chapter": 11, "title": "豪掷千金，拍下宝物", "event": "拍卖会", "climax": "爽点", "emotion": "爽"},
            {"chapter": 12, "title": "身份曝光，众人震惊", "event": "身份揭示", "climax": "爽点", "emotion": "震惊→爽"},
            {"chapter": 13, "title": "家族邀请，暗藏杀机", "event": "进入新圈子", "climax": "转折", "emotion": "期待→警惕"},
            {"chapter": 14, "title": "赌石大胜，日进斗金", "event": "赌石", "climax": "爽点", "emotion": "紧张→爽"},
            {"chapter": 15, "title": "系统任务，投资未来", "event": "长期布局", "climax": "期待", "emotion": "期待"},
            {"chapter": 16, "title": "旧敌卷土重来", "event": "新冲突", "climax": "压抑", "emotion": "愤怒"},
            {"chapter": 17, "title": "实力碾压，再次打脸", "event": "打脸", "climax": "爽点", "emotion": "爽"},
            {"chapter": 18, "title": "女主倾心，感情升温", "event": "感情线", "climax": "温馨", "emotion": "甜"},
            {"chapter": 19, "title": "更大势力注意到主角", "event": "升级冲突", "climax": "转折", "emotion": "警惕"},
            {"chapter": 20, "title": "阶段性高潮：击败地方势力", "event": "大高潮", "climax": "大爽点", "emotion": "爆发→爽"}
        ])
        
        # 第21-30章：进军更高层次
        outline.extend([
            {"chapter": 21, "title": "进入省城，新的舞台", "event": "地图切换", "climax": "期待", "emotion": "期待"},
            {"chapter": 22, "title": "省城富二代挑衅", "event": "新反派", "climax": "压抑", "emotion": "愤怒→隐忍"},
            {"chapter": 23, "title": "结识新朋友，建立人脉", "event": "人脉扩展", "climax": "温馨", "emotion": "欣慰"},
            {"chapter": 24, "title": "商业投资，眼光独到", "event": "商业线", "climax": "爽点", "emotion": "爽"},
            {"chapter": 25, "title": "敌人设局，主角中计", "event": "危机", "climax": "紧张", "emotion": "紧张→愤怒"},
            {"chapter": 26, "title": "绝处逢生，系统助力", "event": "化解危机", "climax": "爽点", "emotion": "绝望→希望→爽"},
            {"chapter": 27, "title": "反击开始，布局反击", "event": "准备反击", "climax": "期待", "emotion": "期待"},
            {"chapter": 28, "title": "收服对手，扩大势力", "event": "势力扩张", "climax": "爽点", "emotion": "爽"},
            {"chapter": 29, "title": "敌人联合，更大危机", "event": "升级冲突", "climax": "紧张", "emotion": "紧张"},
            {"chapter": 30, "title": "第一大高潮：省城称王", "event": "阶段性胜利", "climax": "大爽点", "emotion": "爆发→爽→期待"}
        ])
        
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


# 便捷函数
def generate_market_driven_plan(genre: str, tropes: Dict, user_choices: Dict, api_client=None) -> Dict:
    """
    便捷函数：生成市场导向方案
    """
    generator = MarketDrivenPlanGenerator(api_client=api_client)
    return generator.generate_plan(genre, tropes, user_choices)
