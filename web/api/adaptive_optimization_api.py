"""
Adaptive Optimization API - 三轮优化适配系统
用于一阶段产物完成后的深度优化
"""

import json
import os
from datetime import datetime
from pathlib import Path
from flask import Blueprint, request, jsonify
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

adaptive_opt_api = Blueprint('adaptive_optimization', __name__, url_prefix='/api/adaptive-optimization')


class AdaptiveOptimizer:
    """三轮优化适配器"""
    
    # 优化轮次定义
    ROUNDS = {
        1: {
            'name': '平台风格适配',
            'description': '检查核心设定、卖点、人设是否符合目标平台读者喜好',
            'checkpoints': [
                '核心卖点提炼清晰度',
                '主角人设讨喜度',
                '世界观设定与平台热门作品对比',
                '开篇钩子吸引力',
                '目标读者群体匹配度'
            ]
        },
        2: {
            'name': '数据匹配优化',
            'description': '检查是否符合市场流行套路，同时具备创意点',
            'checkpoints': [
                '符合当前热门题材趋势',
                '创新点与差异化分析',
                '爽点节奏设计合理性',
                '预期追读率评估',
                '市场饱和风险分析'
            ]
        },
        3: {
            'name': '内容完整性检查',
            'description': '检查是否有重大脱节问题',
            'checkpoints': [
                '世界观设定自洽性',
                '角色动机与行为一致性',
                '剧情逻辑连贯性',
                '设定与情节匹配度',
                '伏笔与回收设计'
            ]
        }
    }
    
    def __init__(self, project_title: str, username: str = None):
        self.project_title = project_title
        self.username = username or 'default'
        self.project_dir = self._get_project_dir()
        self.cache_dir = self.project_dir / "adaptive_optimization"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def _get_project_dir(self) -> Path:
        """获取项目目录"""
        from web.services.upload_package_manager import UploadPackageManager
        manager = UploadPackageManager()
        user_novel_dir = manager._get_user_novel_dir(self.username)
        safe_title = "".join(c for c in self.project_title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title.replace(' ', '_')
        return user_novel_dir / safe_title
    
    def load_phase_one_products(self) -> Dict[str, Any]:
        """加载一阶段产物"""
        from web.api.phase_generation_api import ProductLoader
        loader = ProductLoader(self.project_title, self.username)
        return loader.load_all_products()
    
    def start_optimization(self, target_platform: str = "番茄小说") -> Dict[str, Any]:
        """开始三轮优化"""
        session_id = f"opt_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 加载产物
        products = self.load_phase_one_products()
        
        # 创建优化会话
        session = {
            'session_id': session_id,
            'project_title': self.project_title,
            'target_platform': target_platform,
            'start_time': datetime.now().isoformat(),
            'status': 'in_progress',
            'current_round': 1,
            'products_snapshot': {k: v['content'][:500] if v['content'] else '' 
                                 for k, v in products.items()},
            'rounds': {},
            'dialogue_history': []
        }
        
        # 保存会话
        self._save_session(session)
        
        # 生成轮初始分析
        round_1_result = self._analyze_round_1(products, target_platform)
        session['rounds'][1] = round_1_result
        self._save_session(session)
        
        return {
            'session_id': session_id,
            'current_round': 1,
            'round_info': self.ROUNDS[1],
            'analysis': round_1_result,
            'dialogue_prompt': self._generate_dialogue_prompt(1, round_1_result)
        }
    
    def _analyze_round_1(self, products: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """轮分析：平台风格适配"""
        # 提取关键信息
        worldview = products.get('worldview', {}).get('content', '')
        characters = products.get('characters', {}).get('content', '')
        market = products.get('market', {}).get('content', '')
        
        # 模拟AI分析（实际应调用AI API）
        analysis = {
            'overall_score': 78,
            'platform_fit': {
                'score': 82,
                'comment': '世界观设定符合玄幻修仙主流，但创新点略显不足',
                'suggestions': [
                    '建议在开篇前三章强化金手指的独特性',
                    '主角性格可以更突出一些复仇爽感'
                ]
            },
            'character_design': {
                'score': 75,
                'comment': '主角人设基本讨喜，但反派设计较为脸谱化',
                'suggestions': [
                    '增加主角在危机中的智慧表现，不只是靠金手指',
                    '给主要反派增加一些悲剧色彩，避免纯恶'
                ]
            },
            'selling_points': {
                'score': 80,
                'comment': '核心卖点"杀戮成仙"有吸引力，但需强化冲突密度',
                'suggestions': [
                    '每3章至少设置一个小高潮',
                    '强化主角与各大势力的博弈过程'
                ]
            },
            'opening_hook': {
                'score': 72,
                'comment': '开篇节奏稍慢，建议直接切入冲突',
                'suggestions': [
                    '第1章直接进入主角被追杀场景，回忆可以穿插',
                    '金手指在第1章就要出现，不能拖到第3章之后'
                ]
            }
        }
        
        return analysis
    
    def _analyze_round_2(self, products: Dict[str, Any], platform: str, 
                         round_1_feedback: str) -> Dict[str, Any]:
        """二轮分析：数据匹配优化"""
        analysis = {
            'overall_score': 81,
            'market_trend': {
                'score': 85,
                'comment': '符合当前"无敌流+宗门建设"的热门趋势',
                'suggestions': [
                    '参考《万古神帝》的势力博弈写法',
                    '宗门建设部分可以学习《天道图书馆》的爽点设计'
                ]
            },
            'innovation': {
                'score': 70,
                'comment': '"杀戮提取"金手指有创意，但使用方式较单一',
                'suggestions': [
                    '增加金手指的进阶形态，如后期可以提取神通、法则',
                    '设计一些金手指的限制和代价，增加紧张感'
                ]
            },
            'pacing': {
                'score': 83,
                'comment': '爽点节奏设计合理，但支线剧情可能拖沓',
                'suggestions': [
                    '支线剧情控制在3章内解决，避免主线中断超过5章',
                    '每10章设置一个中高潮，每30章一个大高潮'
                ]
            },
            'retention_prediction': {
                'score': 88,
                'comment': '预计首章读完率65%，十章追读率45%',
                'suggestions': [
                    '每章结尾设置悬念，提升翻页率',
                    '章尾预告下一章爽点'
                ]
            }
        }
        
        return analysis
    
    def _analyze_round_3(self, products: Dict[str, Any], 
                         previous_feedback: Dict[str, str]) -> Dict[str, Any]:
        """三轮分析：内容完整性检查"""
        analysis = {
            'overall_score': 76,
            'consistency': {
                'score': 78,
                'comment': '世界观整体自洽，但修炼体系后期可能需要补充',
                'issues': [
                    '目前只定义了筑基-金丹-元婴，后期需要补充化神以上',
                    '杀戮值提取比例在不同境界需要差异化'
                ]
            },
            'motivation': {
                'score': 82,
                'comment': '主角复仇动机清晰，但中期目标需要明确',
                'issues': [
                    '复仇完成后需要有新的长期目标',
                    '建议增加"探索父母死亡真相"的副线'
                ]
            },
            'plot_logic': {
                'score': 74,
                'comment': '主线逻辑通顺，但部分情节转折较生硬',
                'issues': [
                    '第三章主角反杀追兵过于轻松，需要增加危机感',
                    '获得传承的过程缺乏竞争和考验'
                ]
            },
            'foreshadowing': {
                'score': 70,
                'comment': '伏笔设置较少，后期可能缺乏回收爽点',
                'issues': [
                    '建议在第1章埋下主角身世之谜的伏笔',
                    '金手指来源可以作为一个长期伏笔'
                ]
            }
        }
        
        return analysis
    
    def _generate_dialogue_prompt(self, round_num: int, analysis: Dict[str, Any]) -> str:
        """生成对话提示"""
        round_info = self.ROUNDS[round_num]
        
        prompt = f"""## 第{round_num}轮优化：{round_info['name']}

{round_info['description']}

### 检查维度：
"""
        for checkpoint in round_info['checkpoints']:
            prompt += f"- {checkpoint}\n"
        
        prompt += "\n### 初步分析结果：\n"
        
        if 'overall_score' in analysis:
            prompt += f"**综合评分：{analysis['overall_score']}/100**\n\n"
        
        for key, value in analysis.items():
            if isinstance(value, dict) and 'score' in value:
                prompt += f"\n**{key}** (评分：{value['score']})\n"
                prompt += f"- 评价：{value.get('comment', '')}\n"
                if 'suggestions' in value:
                    prompt += "- 建议：\n"
                    for suggestion in value['suggestions']:
                        prompt += f"  * {suggestion}\n"
                if 'issues' in value:
                    prompt += "- 问题：\n"
                    for issue in value['issues']:
                        prompt += f"  * {issue}\n"
        
        prompt += """
### 对话任务：
请针对以上分析结果，回答以下问题：
1. 您是否同意这些评价？
2. 您希望如何调整？
3. 有什么额外的想法或要求？

请输入您的反馈，AI将根据您的意见生成优化方案。
"""
        
        return prompt
    
    def submit_feedback(self, session_id: str, round_num: int, 
                       feedback: str, user_decisions: Dict = None) -> Dict[str, Any]:
        """提交用户反馈，进入下一轮或生成最终方案"""
        session = self._load_session(session_id)
        if not session:
            return {'error': '会话不存在'}
        
        # 记录对话
        session['dialogue_history'].append({
            'round': round_num,
            'user_feedback': feedback,
            'timestamp': datetime.now().isoformat()
        })
        
        # 如果还有下一轮
        if round_num < 3:
            next_round = round_num + 1
            products = self.load_phase_one_products()
            
            if next_round == 2:
                next_analysis = self._analyze_round_2(
                    products, 
                    session['target_platform'],
                    feedback
                )
            else:
                prev_feedback = {f"round_{round_num}": feedback}
                next_analysis = self._analyze_round_3(products, prev_feedback)
            
            session['current_round'] = next_round
            session['rounds'][next_round] = next_analysis
            self._save_session(session)
            
            return {
                'completed_round': round_num,
                'next_round': next_round,
                'round_info': self.ROUNDS[next_round],
                'analysis': next_analysis,
                'dialogue_prompt': self._generate_dialogue_prompt(next_round, next_analysis)
            }
        
        # 三轮完成，生成最终优化方案
        else:
            final_plan = self._generate_final_plan(session, feedback)
            session['status'] = 'completed'
            session['final_plan'] = final_plan
            self._save_session(session)
            
            return {
                'completed_round': 3,
                'status': 'completed',
                'final_plan': final_plan
            }
    
    def _generate_final_plan(self, session: Dict, final_feedback: str) -> Dict[str, Any]:
        """生成最终优化方案"""
        # 汇总三轮分析结果
        all_suggestions = []
        
        for round_num, analysis in session['rounds'].items():
            for key, value in analysis.items():
                if isinstance(value, dict):
                    if 'suggestions' in value:
                        all_suggestions.extend(value['suggestions'])
                    if 'issues' in value:
                        all_suggestions.extend(value['issues'])
        
        # 去重并分类
        unique_suggestions = list(set(all_suggestions))
        
        categorized_plan = {
            'immediate_fixes': [s for s in unique_suggestions if any(kw in s for kw in ['第1章', '第3章', '开篇', '前三章'])],
            'character_enhancements': [s for s in unique_suggestions if any(kw in s for kw in ['主角', '人设', '反派', '角色'])],
            'plot_improvements': [s for s in unique_suggestions if any(kw in s for kw in ['剧情', '节奏', '爽点', '高潮'])],
            'worldbuilding_extensions': [s for s in unique_suggestions if any(kw in s for kw in ['世界观', '修炼', '设定', '境界'])],
            'long_term_planning': [s for s in unique_suggestions if any(kw in s for kw in ['伏笔', '后期', '中期', '长期'])]
        }
        
        return {
            'summary': f"基于三轮优化分析，为《{session['project_title']}》生成优化方案",
            'categorized_plan': categorized_plan,
            'priority_actions': unique_suggestions[:5],
            'estimated_improvement': '预计优化后首章读完率提升10-15%，追读率提升8-12%',
            'export_file': str(self.cache_dir / f"optimization_plan_{session['session_id']}.json")
        }
    
    def _save_session(self, session: Dict):
        """保存会话"""
        file_path = self.cache_dir / f"session_{session['session_id']}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
    
    def _load_session(self, session_id: str) -> Optional[Dict]:
        """加载会话"""
        file_path = self.cache_dir / f"session_{session_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None


# API 路由

@adaptive_opt_api.route('/start', methods=['POST'])
def start_optimization():
    """开始三轮优化"""
    try:
        data = request.get_json()
        title = data.get('title')
        platform = data.get('platform', '番茄小说')
        
        if not title:
            return jsonify({'error': '缺少项目标题'}), 400
        
        optimizer = AdaptiveOptimizer(title)
        result = optimizer.start_optimization(platform)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"开始优化失败: {e}")
        return jsonify({'error': str(e)}), 500


@adaptive_opt_api.route('/feedback', methods=['POST'])
def submit_feedback():
    """提交反馈"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        round_num = data.get('round')
        feedback = data.get('feedback')
        
        if not all([session_id, round_num, feedback]):
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 从session_id提取项目标题
        optimizer = AdaptiveOptimizer("temp")  # 临时实例，实际应从session加载
        result = optimizer.submit_feedback(session_id, round_num, feedback)
        
        if 'error' in result:
            return jsonify(result), 404
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"提交反馈失败: {e}")
        return jsonify({'error': str(e)}), 500


@adaptive_opt_api.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话状态"""
    try:
        optimizer = AdaptiveOptimizer("temp")
        session = optimizer._load_session(session_id)
        
        if not session:
            return jsonify({'error': '会话不存在'}), 404
        
        return jsonify({
            'session_id': session_id,
            'status': session.get('status'),
            'current_round': session.get('current_round'),
            'rounds_completed': list(session.get('rounds', {}).keys())
        })
        
    except Exception as e:
        logger.error(f"获取会话失败: {e}")
        return jsonify({'error': str(e)}), 500
