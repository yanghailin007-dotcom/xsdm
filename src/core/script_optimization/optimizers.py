"""
优化器模块
包含各轮优化器的实现
"""
from typing import Dict, List, Any, Tuple, Optional
from copy import deepcopy
import re

from .config import (
    OptimizationConfig,
    BeatStructureConfig,
    DialogueConfig,
    VisualConfig,
    InfoLayerConfig,
    ValidationConfig
)


class BeatStructureOptimizer:
    """节拍结构优化器"""
    
    def __init__(self, config: BeatStructureConfig = None):
        self.config = config or BeatStructureConfig()
    
    def optimize(self, beats_json: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        优化节拍表结构
        
        Returns:
            (优化后的beats_json, 优化日志)
        """
        result = deepcopy(beats_json)
        beats = result.get('beats', [])
        logs = []
        
        if not beats:
            return result, {'issues_found': 0, 'fixes': [], 'score_before': 0, 'score_after': 0}
        
        score_before = self._calculate_score(beats)
        
        # 1. 检查情绪曲线
        if self.config.check_emotional_arc:
            beats, arc_logs = self._optimize_emotional_arc(beats)
            logs.extend(arc_logs)
        
        # 2. 检查转折点位置
        if self.config.check_turning_points:
            beats, turn_logs = self._optimize_turning_points(beats, result.get('target_duration', 46))
            logs.extend(turn_logs)
        
        # 3. 检查时长分配
        if self.config.check_duration_distribution:
            beats, duration_logs = self._optimize_duration_distribution(beats)
            logs.extend(duration_logs)
        
        result['beats'] = beats
        score_after = self._calculate_score(beats)
        
        optimization_log = {
            'round': 1,
            'stage': 'beat_structure',
            'issues_found': len(logs),
            'fixes': logs,
            'score_before': round(score_before, 1),
            'score_after': round(score_after, 1)
        }
        
        return result, optimization_log
    
    def _optimize_emotional_arc(self, beats: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """优化情绪曲线"""
        logs = []
        
        # 检查是否有完整的情绪曲线
        emotions = [b.get('emotion', '') for b in beats]
        
        # 简单的情绪曲线检查
        has_setup = any(e in ['平静', '日常', 'calm'] for e in emotions)
        has_rising = any(e in ['紧张', '上升', 'tense', 'rising'] for e in emotions)
        has_climax = any(e in ['爆发', '高潮', '爆发', 'climax'] for e in emotions)
        has_resolution = any(e in ['释然', '回落', 'resolution'] for e in emotions)
        
        if not has_climax:
            # 找到情绪最紧张的地方标记为高潮
            for i, beat in enumerate(beats):
                if '紧张' in beat.get('emotion', '') or 'tense' in beat.get('emotion', ''):
                    beats[i]['emotion'] = '爆发/高潮'
                    beats[i]['beat_type'] = 'climax'
                    logs.append(f"beat_{i+1}: 标记高潮点")
                    break
        
        if not has_resolution and len(beats) > 0:
            # 最后一个节拍如果不是回落，添加悬念
            if beats[-1].get('beat_type') != 'resolution':
                beats[-1]['beat_type'] = 'resolution'
                beats[-1]['emotion'] = '悬念/余韵'
                logs.append(f"beat_{len(beats)}: 添加结尾悬念")
        
        return beats, logs
    
    def _optimize_turning_points(self, beats: List[Dict], target_duration: int) -> Tuple[List[Dict], List[str]]:
        """优化转折点位置"""
        logs = []
        total_beats = len(beats)
        
        if total_beats < 3:
            return beats, logs
        
        # 检查3秒钩子位置
        hook_idx = None
        for i, beat in enumerate(beats):
            if beat.get('beat_type') == 'hook':
                hook_idx = i
                break
        
        if hook_idx is None:
            # 第一个节拍如果不是hook，设为hook
            beats[0]['beat_type'] = 'hook'
            logs.append("beat_1: 设置开场钩子")
        
        # 检查15秒转折点（大约第4-5个beat）
        mid_idx = int(total_beats * 0.3)
        if mid_idx < total_beats and beats[mid_idx].get('beat_type') not in ['rising', 'climax']:
            beats[mid_idx]['beat_type'] = 'rising'
            logs.append(f"beat_{mid_idx+1}: 设置为上升转折点")
        
        return beats, logs
    
    def _optimize_duration_distribution(self, beats: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """优化时长分配"""
        logs = []
        
        total_duration = sum(b.get('duration_seconds', 3) for b in beats)
        
        # 计算高潮部分时长占比
        climax_duration = sum(
            b.get('duration_seconds', 3) 
            for b in beats 
            if b.get('beat_type') == 'climax'
        )
        
        if total_duration > 0:
            climax_ratio = climax_duration / total_duration
            if climax_ratio < self.config.climax_duration_ratio:
                logs.append(f"高潮部分时长占比{climax_ratio:.1%}偏低，建议增加")
        
        return beats, logs
    
    def _calculate_score(self, beats: List[Dict]) -> float:
        """计算节拍表质量分数"""
        if not beats:
            return 0.0
        
        score = 7.0  # 基础分
        
        # 检查beats数量
        beat_count = len(beats)
        min_beats, max_beats = self.config.target_beats_range
        if min_beats <= beat_count <= max_beats:
            score += 0.5
        
        # 检查是否有高潮
        has_climax = any(b.get('beat_type') == 'climax' for b in beats)
        if has_climax:
            score += 0.5
        
        # 检查是否有钩子
        has_hook = any(b.get('beat_type') == 'hook' for b in beats)
        if has_hook:
            score += 0.5
        
        return min(10.0, score)


class DialogueOptimizer:
    """对白优化器"""
    
    # 问题台词模式
    PREACHING_PATTERNS = [
        r'应该|下次|记住|should|next time|remember',
        r'这是\.{0,3}|原来\.{0,3}|这是…|原来…|Is this|So this',
        r'我好害怕|我生气了|I am scared|I am angry',
    ]
    
    def __init__(self, config: DialogueConfig = None):
        self.config = config or DialogueConfig()
    
    def optimize(self, shots_v2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """优化对白"""
        result = deepcopy(shots_v2)
        shots = result.get('shots', [])
        changes = []
        
        for i, shot in enumerate(shots):
            dialogue = shot.get('dialogue', {})
            if not dialogue:
                continue
            
            original_lines = dialogue.get('lines_en', '')
            if not original_lines or original_lines == 'None':
                continue
            
            # 检查并修复问题台词
            new_lines, change_log = self._fix_dialogue(original_lines, i+1)
            
            if new_lines != original_lines:
                shots[i]['dialogue']['lines_en'] = new_lines
                if change_log:
                    changes.append(change_log)
                
                # 同步更新audio_note
                if '说教' in str(change_log) or '直白' in str(change_log):
                    shots[i]['dialogue']['audio_note_en'] = 'Use breathing and ambient sound instead of dialogue'
        
        result['shots'] = shots
        
        optimization_log = {
            'round': 2,
            'stage': 'dialogue',
            'changes': changes,
            'changes_count': len(changes)
        }
        
        return result, optimization_log
    
    def _fix_dialogue(self, lines: str, shot_number: int) -> Tuple[str, str]:
        """修复单句台词"""
        original = lines
        
        # 检查说教模式
        for pattern in self.PREACHING_PATTERNS[:1]:
            if re.search(pattern, lines, re.IGNORECASE):
                # 删除说教台词，改为简洁表达或删除
                if len(lines) > 20:
                    return "...", f"shot_{shot_number}: 删除说教台词，改用省略号"
        
        # 检查直白解说
        for pattern in self.PREACHING_PATTERNS[1:2]:
            if re.search(pattern, lines, re.IGNORECASE):
                return "", f"shot_{shot_number}: 删除直白解说，改用视觉暗示"
        
        # 检查情绪标签
        for pattern in self.PREACHING_PATTERNS[2:]:
            if re.search(pattern, lines, re.IGNORECASE):
                return "...", f"shot_{shot_number}: 情绪标签化改为身体语言"
        
        return original, ""


class VisualOptimizer:
    """视觉优化器"""
    
    SHOT_TYPE_MAPPING = {
        '全景': 'Wide Shot',
        '中景': 'Medium Shot',
        '近景': 'Medium Close-up',
        '特写': 'Close-up',
        '大特写': 'Extreme Close-up'
    }
    
    def __init__(self, config: VisualConfig = None):
        self.config = config or VisualConfig()
    
    def optimize(self, shots_v2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """优化视觉描述"""
        result = deepcopy(shots_v2)
        shots = result.get('shots', [])
        changes = []
        
        for i, shot in enumerate(shots):
            # 1. 优化shot_type
            if self.config.add_shot_spec:
                shot_type = shot.get('shot_type', '')
                # 标准化shot_type格式
                if shot_type and not any(x in shot_type for x in ['Shot', 'Close-up', 'Angle']):
                    # 需要转换
                    for cn, en in self.SHOT_TYPE_MAPPING.items():
                        if cn in shot_type:
                            shots[i]['shot_type'] = en
                            changes.append(f"shot_{i+1}: 标准化shot_type为{en}")
                            break
            
            # 2. 优化veo_prompt
            if self.config.enhance_veo_prompt:
                veo_prompt = shot.get('veo_prompt_standard', '')
                if veo_prompt and 'cinematic' not in veo_prompt.lower():
                    shots[i]['veo_prompt_standard'] = f"Cinematic shot, {veo_prompt}"
                    changes.append(f"shot_{i+1}: 增强veo_prompt质量")
            
            # 3. 竖屏适配检查
            if self.config.vertical_frame_check:
                visual_desc = shot.get('visual_description_standard', '')
                if visual_desc and 'center' not in visual_desc.lower():
                    # 添加主体居中的提示
                    shots[i]['visual_description_standard'] = f"Subject centered, {visual_desc}"
        
        result['shots'] = shots
        
        optimization_log = {
            'round': 3,
            'stage': 'visual',
            'changes': changes,
            'changes_count': len(changes)
        }
        
        return result, optimization_log


class InfoLayerOptimizer:
    """信息层次优化器"""
    
    def __init__(self, config: InfoLayerConfig = None):
        self.config = config or InfoLayerConfig()
    
    def optimize(self, shots_v2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """优化信息层次"""
        result = deepcopy(shots_v2)
        shots = result.get('shots', [])
        changes = []
        
        total_shots = len(shots)
        if total_shots == 0:
            return result, {'round': 4, 'stage': 'info_layer', 'changes': [], 'changes_count': 0}
        
        # 1. 渐进式揭示检查
        if self.config.progressive_revelation:
            # 检查是否有突然的全局认知揭示
            for i, shot in enumerate(shots):
                visual_desc = shot.get('visual_description_standard', '')
                # 如果描述中包含"看到城市""看到世界"等全局视角
                if any(kw in visual_desc for kw in ['城市全景', '整个世界', 'city view', 'world view']):
                    # 建议改为局部视角
                    if i > 0:
                        changes.append(f"shot_{i+1}: 建议将全局视角改为渐进揭示")
        
        # 2. 添加伏笔
        if self.config.add_foreshadowing:
            # 检查第一个镜头是否有伏笔潜力
            if shots:
                first_shot = shots[0]
                scene_title = first_shot.get('scene_title', '')
                # 如果场景涉及危机，可以添加隐藏细节
                if any(kw in scene_title.lower() for kw in ['doom', 'danger', '危机', '危险']):
                    if 'hidden_detail' not in str(first_shot):
                        changes.append("shot_1: 建议添加隐藏伏笔细节（如眼神、阴影异常）")
        
        optimization_log = {
            'round': 4,
            'stage': 'info_layer',
            'changes': changes,
            'changes_count': len(changes)
        }
        
        return result, optimization_log


class PlatformValidator:
    """平台质检器"""
    
    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
    
    def validate(self, shots_v2: Dict[str, Any], target_duration: int = 46) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """平台规格质检"""
        result = deepcopy(shots_v2)
        shots = result.get('shots', [])
        
        issues = []
        warnings = []
        
        if not shots:
            return result, {
                'round': 5,
                'stage': 'validation',
                'passed': False,
                'score': 0,
                'issues': ['No shots found'],
                'warnings': []
            }
        
        # 1. 检查时长
        total_duration = sum(s.get('duration_seconds', 3) for s in shots)
        if total_duration > target_duration + 5:
            issues.append(f"总时长{total_duration}秒超过目标{target_duration}秒")
        elif total_duration < target_duration - 10:
            warnings.append(f"总时长{total_duration}秒偏短")
        
        # 2. 检查开场钩子
        if self.config.check_hook:
            first_shot = shots[0]
            first_duration = first_shot.get('duration_seconds', 3)
            scene_title = first_shot.get('scene_title', '')
            
            if first_duration > 3:
                warnings.append("开场镜头超过3秒，建议缩短以增强钩子效果")
            
            if not any(kw in scene_title.lower() for kw in ['doom', 'danger', 'crisis', '冲击', '危机']):
                warnings.append("开场建议设置更强的视觉钩子")
        
        # 3. 检查节奏
        if self.config.check_pacing:
            durations = [s.get('duration_seconds', 3) for s in shots]
            avg_duration = sum(durations) / len(durations)
            
            if avg_duration > self.config.max_avg_shot_duration:
                issues.append(f"平均每镜{avg_duration:.1f}秒偏长，建议加快节奏")
            elif avg_duration < self.config.min_avg_shot_duration:
                warnings.append(f"平均每镜{avg_duration:.1f}秒偏短，注意信息密度")
            
            # 检查连续慢镜头
            slow_streak = 0
            for d in durations:
                if d > 4:
                    slow_streak += 1
                    if slow_streak >= 3:
                        issues.append("存在连续3个以上慢镜头(>4秒)")
                        break
                else:
                    slow_streak = 0
        
        # 4. 检查结尾悬念
        if self.config.check_cliffhanger:
            last_shot = shots[-1]
            last_scene = last_shot.get('scene_title', '')
            
            if not any(kw in last_scene.lower() for kw in ['悬念', '震惊', '发现', 'hook', 'cliffhanger', 'mystery']):
                warnings.append("结尾建议设置悬念钩子")
        
        # 计算分数
        score = self._calculate_score(issues, warnings, shots)
        
        optimization_log = {
            'round': 5,
            'stage': 'validation',
            'passed': len(issues) == 0,
            'score': round(score, 1),
            'total_duration': total_duration,
            'issues': issues,
            'warnings': warnings
        }
        
        return result, optimization_log
    
    def _calculate_score(self, issues: List[str], warnings: List[str], shots: List[Dict]) -> float:
        """计算质量分数"""
        base_score = 8.0
        
        # 严重问题扣分
        base_score -= len(issues) * 1.0
        
        # 警告扣分
        base_score -= len(warnings) * 0.3
        
        # 加分项
        if len(shots) >= 10:
            base_score += 0.5
        
        return max(0.0, min(10.0, base_score))
