# -*- coding: utf-8 -*-
"""
Phase One Optimizer Service
第一阶段产品三轮优化系统

三轮优化流程:
1. 平台风格适配 - 检查核心设定、卖点设计、角色人设是否符合目标平台读者偏好
2. 数据匹配 - 验证写作计划是否符合当下市场趋势,同时确保创意性
3. 内容连贯性检查 - 检查小说内容是否存在严重的断档、脱节问题
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PhaseOneOptimizer:
    """
    第一阶段产品优化器
    通过三轮多轮对话对小说世界观、角色、势力、升级、写作风格、故事线等进行优化
    """

    # 产品名称映射
    PRODUCT_NAMES = {
        'worldview': '世界观与修炼体系',
        'characters': '核心角色设计',
        'factions': '势力设定',
        'growth': '升级路线',
        'writing': '写作风格',
        'storyline': '故事线规划',
        'market_analysis': '市场分析报告'
    }

    # 平台特征配置
    PLATFORM_PROFILES = {
        'fanqie': {
            'name': '番茄小说',
            'reader_preferences': [
                '偏好快节奏、爽点密集的剧情',
                '喜欢清晰的金手指/外挂设定',
                '对创新设定接受度高',
                '重视前3章的吸引力',
                '偏好单主角成长路线'
            ],
            'taboo_topics': [
                '过于阴暗压抑的世界观',
                '过于复杂的多线叙事',
                '慢热的剧情节奏'
            ],
            'hot_elements': [
                '签到流、直播流等创新流派',
                '国运、神选等宏大设定',
                '轻松幽默的文风',
                '明确的等级体系'
            ]
        },
        'qidian': {
            'name': '起点中文网',
            'reader_preferences': [
                '注重世界观完整性和逻辑性',
                '接受较慢热的剧情铺垫',
                '重视人物刻画深度',
                '喜欢复杂的势力斗争',
                '对长篇连载有耐心'
            ],
            'taboo_topics': [
                '过于简单的套路重复',
                '人物脸谱化',
                '逻辑漏洞明显的设定'
            ],
            'hot_elements': [
                '克苏鲁、赛博朋克等风格融合',
                '群像剧、多主角叙事',
                '深层哲学思考',
                '精妙的伏笔设计'
            ]
        },
        'general': {
            'name': '通用平台',
            'reader_preferences': [
                '平衡的剧情节奏',
                '清晰的主线目标',
                '有特色的角色设定',
                '合理的升级体系'
            ],
            'taboo_topics': [
                '极端的题材选择',
                '过于晦涩的表达'
            ],
            'hot_elements': [
                '创新的世界观设定',
                '立体的人物塑造',
                '紧凑的剧情推进'
            ]
        }
    }

    def __init__(self, api_client=None):
        """
        初始化优化器
        
        Args:
            api_client: AI API客户端,用于多轮对话
        """
        self.api_client = api_client
        self.conversation_history = []
        self.current_round = 0
        self.rounds_data = {}
        
    def optimize(self, products: Dict[str, Any], platform: str = "fanqie") -> Dict[str, Any]:
        """
        执行三轮优化
        
        Args:
            products: 第一阶段产品数据,包含worldview, characters等
            platform: 目标平台,默认fanqie
            
        Returns:
            优化结果,包含每轮的评分、建议、修订内容
        """
        logger.info(f"开始第一阶段产品优化,目标平台: {platform}")
        
        # 验证平台
        if platform not in self.PLATFORM_PROFILES:
            platform = 'general'
            
        self.platform = platform
        self.platform_profile = self.PLATFORM_PROFILES[platform]
        self.products = products
        
        # 重置状态
        self.conversation_history = []
        self.rounds_data = {}
        
        try:
            # 第一轮:平台风格适配
            logger.info("开始第一轮:平台风格适配")
            self.current_round = 1
            round1_result = self._round1_platform_adaptation()
            self.rounds_data['platform_adaptation'] = round1_result
            
            # 第二轮:数据匹配
            logger.info("开始第二轮:数据匹配")
            self.current_round = 2
            round2_result = self._round2_data_matching(round1_result)
            self.rounds_data['data_matching'] = round2_result
            
            # 第三轮:内容连贯性检查
            logger.info("开始第三轮:内容连贯性检查")
            self.current_round = 3
            round3_result = self._round3_coherence_check(round1_result, round2_result)
            self.rounds_data['coherence_check'] = round3_result
            
            # 生成最终优化报告
            final_result = self._generate_final_report()
            
            logger.info("第一阶段产品优化完成")
            return final_result
            
        except Exception as e:
            logger.error(f"优化过程出错: {str(e)}", exc_info=True)
            raise
    
    def _round1_platform_adaptation(self) -> Dict[str, Any]:
        """
        第一轮:平台风格适配
        
        检查内容:
        - 核心设定是否符合平台读者偏好
        - 卖点设计是否突出
        - 角色人设是否讨喜
        - 开篇吸引力是否足够
        """
        # 构建产品摘要
        products_summary = self._build_products_summary()
        
        # 构建提示词
        system_prompt = f"""你是一位专业的网络小说编辑,专门为{self.platform_profile['name']}平台审阅作品。

{self.platform_profile['name']}平台读者特征:
{chr(10).join(['- ' + p for p in self.platform_profile['reader_preferences']])}

禁忌题材:
{chr(10).join(['- ' + t for t in self.platform_profile['taboo_topics']])}

热门元素:
{chr(10).join(['- ' + e for e in self.platform_profile['hot_elements']])}

你的任务是对作品进行爽文平台适配性分析,从以下维度评分(0-100分):
1. 爽点密度 - 是否每2-4章至少一个小爽点？爽点设计是否多样化（装逼/打脸/收获/突破/反转）？
2. 黄金三章质量 - 前3章是否有强钩子、强冲突、首次爽点？严禁慢热！
3. 压抑-爆发配对 - 每个爽点前是否有足够的压抑设计？爽感是否来自压抑的释放？
4. 收获具象化 - 每次爽点后主角是否有具象收获（财富/地位/能力/人脉）？
5. 角色人设适配 - 主角人设是否符合平台主流偏好（是否有让读者代入的爽感基础）

请用JSON格式返回分析结果,包含score(总分), dimensions(各维度得分), issues(问题列表), suggestions(改进建议), revised_content(修订建议)。"""

        user_prompt = f"请分析以下作品在{self.platform_profile['name']}平台的适配性:\n\n{products_summary}"

        # 模拟API调用(实际使用时替换为真实API)
        # response = self.api_client.chat_completion(system_prompt, user_prompt)
        # result = json.loads(response)
        
        # 临时返回模拟结果
        result = {
            "score": 78,
            "dimensions": {
                "core_setting": 80,
                "selling_point": 75,
                "character_design": 82,
                "opening_tension": 75
            },
            "issues": [
                "开篇节奏略显平缓,建议在第一章增加冲突或悬念",
                "主角金手指的独特性可以进一步强化"
            ],
            "suggestions": [
                "考虑在开篇加入一个小高潮事件,展示主角的特殊能力",
                "为主角设计一个更具辨识度的标志性特征"
            ],
            "revised_content": {
                "opening_suggestion": "建议修改第一章开头,加入一场意外事件...",
                "character_highlight": "可增加主角的特殊习惯或口头禅..."
            }
        }
        
        return result
    
    def _round2_data_matching(self, round1_result: Dict) -> Dict[str, Any]:
        """
        第二轮:数据匹配
        
        检查内容:
        - 写作计划是否符合当前市场趋势
        - 创意性是否足够,避免落入俗套
        - 题材选择的市场空间
        - 与竞品相比的差异化优势
        """
        products_summary = self._build_products_summary()
        
        system_prompt = """你是一位资深的市场分析师,擅长分析网文市场趋势。

当前网文市场热门趋势(2024-2025):
- 国运流、神选流等宏大叙事持续火热
- 轻松搞笑文风受欢迎程度上升
- 创新世界观融合(如赛博修仙、克系武侠)
- 快节奏、高密度爽点成为主流
- 多女主/无女主等细分类型各有市场

你的任务是从市场角度分析作品的竞争力:
1. 市场契合度 - 作品是否符合当前市场热点
2. 创新性评估 - 是否有足够的新意避免同质化
3. 差异化优势 - 与同类作品相比的独特之处
4. 商业潜力 - 预估的市场表现潜力

请用JSON格式返回,包含score(总分), dimensions(各维度得分), market_analysis(市场分析), risks(潜在风险), opportunities(机会点)。"""

        user_prompt = f"请分析以下作品的市场竞争力:\n\n{products_summary}"
        
        # 模拟结果
        result = {
            "score": 82,
            "dimensions": {
                "market_fit": 85,
                "innovation": 78,
                "differentiation": 80,
                "commercial_potential": 85
            },
            "market_analysis": {
                "genre_positioning": "作品定位于玄幻修仙流派,属于市场主流题材",
                "target_audience": "适合18-30岁男性读者,追求爽快阅读体验",
                "competition_level": "中等竞争激烈,但有差异化空间"
            },
            "risks": [
                "同类题材较多,需要更强的差异化元素",
                "中期剧情容易陷入套路化"
            ],
            "opportunities": [
                "当前市场对此类创新设定接受度高",
                "有望通过特色角色塑造脱颖而出"
            ]
        }
        
        return result
    
    def _round3_coherence_check(self, round1_result: Dict, round2_result: Dict) -> Dict[str, Any]:
        """
        第三轮:内容连贯性检查
        
        检查内容:
        - 世界观设定内部逻辑是否一致
        - 角色行为是否符合其设定
        - 势力关系是否合理
        - 升级体系是否有矛盾
        - 故事线与世界观是否有冲突
        """
        products_summary = self._build_products_summary()
        
        system_prompt = """你是一位严格的设定审核编辑,专门检查小说设定的内部一致性。

你需要从爽文角度检查作品是否存在问题:
1. 爽点逻辑一致性 - 爽点爆发是否有足够的铺垫？收获是否与付出匹配？
2. 角色爽感逻辑 - 主角行为是否始终服务于爽感？有无"圣母"或"降智"行为？
3. 升级/收获节奏 - 能力/财富增长是否过于缓慢或过快？
4. 压抑设计合理性 - 反派/困境是否足够让读者生气？（但不要太久，否则读者流失）
5. 世界观与爽点兼容性 - 世界规则是否限制了爽点的展开？

请用JSON格式返回,包含score(总分), issues_by_category(分类问题列表), critical_issues(严重问题), warnings(一般警告), recommendations(修复建议)。"""

        user_prompt = f"请检查以下作品的内容连贯性:\n\n{products_summary}"
        
        # 模拟结果
        result = {
            "score": 85,
            "issues_by_category": {
                "worldview": [],
                "characters": [
                    "主角在第三章的决策与其谨慎人设略有出入"
                ],
                "factions": [],
                "growth_system": [],
                "storyline": []
            },
            "critical_issues": [],
            "warnings": [
                "建议为主角第三章的决策增加更多心理铺垫",
                "势力间的实力对比在中期需要保持平衡"
            ],
            "recommendations": [
                "可考虑在第二章增加一个事件,解释主角行为模式的转变",
                "建议建立势力实力对照表,避免后期战力崩坏"
            ]
        }
        
        return result
    
    def _build_products_summary(self) -> str:
        """构建产品摘要"""
        summary_parts = []
        
        for key, name in self.PRODUCT_NAMES.items():
            if key in self.products:
                content = self.products[key]
                if isinstance(content, dict):
                    content_str = json.dumps(content, ensure_ascii=False, indent=2)
                else:
                    content_str = str(content)
                
                # 截断过长的内容
                if len(content_str) > 1000:
                    content_str = content_str[:1000] + "...(已截断)"
                
                summary_parts.append(f"## {name}\n{content_str}\n")
        
        return "\n".join(summary_parts)
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """生成最终优化报告"""
        
        # 计算总分
        round_scores = [
            self.rounds_data['platform_adaptation']['score'],
            self.rounds_data['data_matching']['score'],
            self.rounds_data['coherence_check']['score']
        ]
        overall_score = round(sum(round_scores) / len(round_scores))
        
        # 汇总所有建议
        all_suggestions = []
        all_issues = []
        
        # 第一轮的建议
        r1 = self.rounds_data['platform_adaptation']
        all_suggestions.extend(r1.get('suggestions', []))
        all_issues.extend(r1.get('issues', []))
        
        # 第二轮的建议
        r2 = self.rounds_data['data_matching']
        if 'opportunities' in r2:
            all_suggestions.extend([f"[市场机会] {opp}" for opp in r2['opportunities']])
        if 'risks' in r2:
            all_issues.extend([f"[市场风险] {risk}" for risk in r2['risks']])
        
        # 第三轮的建议
        r3 = self.rounds_data['coherence_check']
        all_suggestions.extend(r3.get('recommendations', []))
        all_issues.extend(r3.get('critical_issues', []))
        all_issues.extend(r3.get('warnings', []))
        
        # 生成优先级排序
        priority_actions = self._prioritize_actions(all_issues, all_suggestions)
        
        return {
            "overall_score": overall_score,
            "platform": self.platform,
            "platform_name": self.platform_profile['name'],
            "rounds": {
                "platform_adaptation": {
                    "score": r1['score'],
                    "dimensions": r1.get('dimensions', {}),
                    "issues": r1.get('issues', []),
                    "suggestions": r1.get('suggestions', []),
                    "summary": f"平台适配性评分{r1['score']}分,基本符合{self.platform_profile['name']}读者偏好"
                },
                "data_matching": {
                    "score": r2['score'],
                    "dimensions": r2.get('dimensions', {}),
                    "market_analysis": r2.get('market_analysis', {}),
                    "risks": r2.get('risks', []),
                    "opportunities": r2.get('opportunities', []),
                    "summary": f"市场竞争力评分{r2['score']}分,{r2.get('market_analysis', {}).get('competition_level', '竞争情况待分析')}"
                },
                "coherence_check": {
                    "score": r3['score'],
                    "critical_issues": r3.get('critical_issues', []),
                    "warnings": r3.get('warnings', []),
                    "recommendations": r3.get('recommendations', []),
                    "summary": f"内容连贯性评分{r3['score']}分,{'存在' if r3.get('critical_issues') else '无明显'}严重逻辑问题"
                }
            },
            "summary": f"作品综合评分{overall_score}分,建议优先处理{len(priority_actions['high'])}项高优先级改进",
            "priority_actions": priority_actions,
            "optimization_time": datetime.now().isoformat()
        }
    
    def _prioritize_actions(self, issues: List[str], suggestions: List[str]) -> Dict[str, List[str]]:
        """对改进建议进行优先级排序"""
        # 简单的优先级规则
        high_priority = []
        medium_priority = []
        low_priority = []
        
        # 严重问题 -> 高优先级
        for issue in issues:
            if any(keyword in issue for keyword in ['严重', '致命', '矛盾', '漏洞']):
                high_priority.append(f"[修复] {issue}")
            elif any(keyword in issue for keyword in ['建议', '可以', '考虑']):
                low_priority.append(f"[优化] {issue}")
            else:
                medium_priority.append(f"[调整] {issue}")
        
        # 建议分类
        for suggestion in suggestions:
            if any(keyword in suggestion for keyword in ['必须', '务必', '关键']):
                high_priority.append(suggestion)
            elif any(keyword in suggestion for keyword in ['市场风险', '机会']):
                medium_priority.append(suggestion)
            else:
                low_priority.append(suggestion)
        
        return {
            "high": high_priority[:5],  # 最多5个高优先级
            "medium": medium_priority[:5],
            "low": low_priority[:5]
        }


# 简单的优化任务管理器
class OptimizationTaskManager:
    """优化任务管理器,用于跟踪异步优化任务"""
    
    def __init__(self):
        self.tasks = {}
        
    def create_task(self, title: str, platform: str) -> str:
        """创建新任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "title": title,
            "platform": platform,
            "status": "pending",  # pending, running, completed, failed
            "progress": 0,
            "current_round": None,
            "message": "等待开始...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
            self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
    
    def list_tasks(self, title: str = None) -> List[Dict]:
        """列出任务"""
        tasks = list(self.tasks.values())
        if title:
            tasks = [t for t in tasks if t.get("title") == title]
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)


# 全局任务管理器实例
task_manager = OptimizationTaskManager()
