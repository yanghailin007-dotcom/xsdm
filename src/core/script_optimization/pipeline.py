"""
优化管道主类
整合所有优化器，执行完整的多轮优化流程
"""
from typing import Dict, List, Any, Optional, Tuple
from copy import deepcopy

from .config import OptimizationConfig
from .optimizers import (
    BeatStructureOptimizer,
    DialogueOptimizer,
    VisualOptimizer,
    InfoLayerOptimizer,
    PlatformValidator
)


class ScriptOptimizationPipeline:
    """
    剧本优化管道
    
    使用示例:
        pipeline = ScriptOptimizationPipeline()
        
        # 完整流程
        result = pipeline.full_pipeline(story_outline, config={
            'platform': 'douyin',
            'target_duration': 46
        })
    """
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.optimization_logs: List[Dict[str, Any]] = []
    
    def optimize_beats(self, beats_json: Dict[str, Any], 
                       config: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        第1轮：优化节拍表结构
        
        Args:
            beats_json: 节拍表JSON
            config: 可选配置覆盖
            
        Returns:
            (优化后的beats_json, 优化日志)
        """
        if config:
            beat_config = self.config.beat_structure_config
            if 'check_emotional_arc' in config:
                beat_config.check_emotional_arc = config['check_emotional_arc']
            if 'check_turning_points' in config:
                beat_config.check_turning_points = config['check_turning_points']
        else:
            beat_config = self.config.beat_structure_config
        
        optimizer = BeatStructureOptimizer(beat_config)
        result, log = optimizer.optimize(beats_json)
        self.optimization_logs.append(log)
        
        return result, log
    
    def optimize_shots(self, shots_v2_json: Dict[str, Any],
                       rounds: Optional[List[str]] = None,
                       config: Optional[OptimizationConfig] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        第2-5轮：优化分镜剧本
        
        Args:
            shots_v2_json: shots_v2格式JSON
            rounds: 指定要执行的轮次 ['dialogue', 'visual', 'info_layer', 'validation']
            config: 可选配置覆盖
            
        Returns:
            (优化后的shots_v2_json, 所有优化日志列表)
        """
        cfg = config or self.config
        
        if rounds is None:
            rounds = []
            if cfg.dialogue:
                rounds.append('dialogue')
            if cfg.visual:
                rounds.append('visual')
            if cfg.info_layer:
                rounds.append('info_layer')
            if cfg.validation:
                rounds.append('validation')
        
        result = deepcopy(shots_v2_json)
        logs = []
        
        # 第2轮：对白优化
        if 'dialogue' in rounds and cfg.dialogue:
            optimizer = DialogueOptimizer(cfg.dialogue_config)
            result, log = optimizer.optimize(result)
            logs.append(log)
            self.optimization_logs.append(log)
        
        # 第3轮：视觉优化
        if 'visual' in rounds and cfg.visual:
            optimizer = VisualOptimizer(cfg.visual_config)
            result, log = optimizer.optimize(result)
            logs.append(log)
            self.optimization_logs.append(log)
        
        # 第4轮：信息层次优化
        if 'info_layer' in rounds and cfg.info_layer:
            optimizer = InfoLayerOptimizer(cfg.info_layer_config)
            result, log = optimizer.optimize(result)
            logs.append(log)
            self.optimization_logs.append(log)
        
        # 第5轮：平台质检
        if 'validation' in rounds and cfg.validation:
            validator = PlatformValidator(cfg.validation_config)
            result, log = validator.validate(result, cfg.target_duration)
            logs.append(log)
            self.optimization_logs.append(log)
        
        return result, logs
    
    def full_pipeline(self, beats_json: Dict[str, Any],
                      config: Optional[OptimizationConfig] = None) -> Dict[str, Any]:
        """
        完整优化流程：从节拍表到最终分镜
        
        注意：这里假设节拍表已包含shots或需要先生成shots
        实际使用时，应该先生成shots_v2，然后调用optimize_shots
        
        Args:
            beats_json: 节拍表JSON（如果包含shots则直接优化）
            config: 完整配置
            
        Returns:
            包含优化结果和报告的完整字典
        """
        cfg = config or self.config
        self.optimization_logs = []
        
        # 第1轮：优化节拍结构
        optimized_beats = beats_json
        if cfg.beat_structure:
            optimized_beats, beat_log = self.optimize_beats(beats_json)
        else:
            beat_log = {'round': 1, 'stage': 'beat_structure', 'skipped': True}
            self.optimization_logs.append(beat_log)
        
        # 检查是否需要生成shots（这里简化处理，假设输入已包含shots）
        if 'shots' in optimized_beats:
            shots_v2 = optimized_beats
        elif 'beats' in optimized_beats:
            # 需要生成shots（这里简化，实际应该调用生成器）
            shots_v2 = self._convert_beats_to_shots(optimized_beats)
        else:
            shots_v2 = optimized_beats
        
        # 第2-5轮：优化分镜
        optimized_shots, shot_logs = self.optimize_shots(shots_v2, config=cfg)
        
        # 生成报告
        report = self._generate_report(optimized_shots)
        
        return {
            'optimized_beats': optimized_beats,
            'optimized_shots': optimized_shots,
            'optimization_logs': self.optimization_logs,
            'report': report
        }
    
    def quick_optimize(self, shots_v2_json: Dict[str, Any],
                       focus: str = 'all') -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        快速优化（单次）
        
        Args:
            shots_v2_json: shots_v2格式JSON
            focus: 优化重点 'all'|'dialogue'|'visual'|'validation'
            
        Returns:
            (优化后的shots_v2_json, 优化报告)
        """
        rounds_map = {
            'all': ['dialogue', 'visual', 'validation'],
            'dialogue': ['dialogue'],
            'visual': ['visual'],
            'validation': ['validation']
        }
        
        rounds = rounds_map.get(focus, ['dialogue', 'visual', 'validation'])
        
        result, logs = self.optimize_shots(shots_v2_json, rounds=rounds)
        
        report = {
            'focus': focus,
            'rounds_executed': rounds,
            'logs': logs,
            'total_changes': sum(log.get('changes_count', 0) for log in logs)
        }
        
        return result, report
    
    def _convert_beats_to_shots(self, beats_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        将节拍表转换为shots_v2格式（简化版）
        实际使用时应该调用正式的生成器
        """
        beats = beats_json.get('beats', [])
        shots = []
        
        for i, beat in enumerate(beats, 1):
            shot = {
                'shot_number': i,
                'shot_type': 'Medium Shot',
                'scene_title': beat.get('description', f'Scene {i}'),
                'veo_prompt_standard': beat.get('description', ''),
                'veo_prompt_reference': beat.get('description', ''),
                'veo_prompt_frames': beat.get('description', ''),
                'visual_description_standard': beat.get('description', ''),
                'visual_description_reference': beat.get('description', ''),
                'visual_description_frames': beat.get('description', ''),
                'image_prompts': {
                    'scene': beat.get('description', ''),
                    'character': '',
                    'first_frame': '',
                    'last_frame': ''
                },
                'dialogue': {
                    'speaker': 'None',
                    'lines_en': 'None',
                    'tone_en': 'None',
                    'audio_note_en': ''
                },
                'duration_seconds': beat.get('duration_seconds', 3)
            }
            shots.append(shot)
        
        return {
            'version': '2.0',
            'language': 'en',
            'title': beats_json.get('title', 'Untitled'),
            'episode': beats_json.get('episode', 1),
            'total_shots': len(shots),
            'shots': shots
        }
    
    def _generate_report(self, shots_v2: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终优化报告"""
        shots = shots_v2.get('shots', [])
        total_duration = sum(s.get('duration_seconds', 3) for s in shots)
        
        # 计算最终分数（取最后一轮validation的分数，如果没有则估算）
        final_score = 7.0
        for log in reversed(self.optimization_logs):
            if 'score' in log:
                final_score = log['score']
                break
            elif 'score_after' in log:
                final_score = log['score_after']
                break
        
        # 确定等级
        if final_score >= 9:
            grade = 'excellent'
        elif final_score >= 8:
            grade = 'good'
        elif final_score >= 7:
            grade = 'acceptable'
        else:
            grade = 'needs_work'
        
        # 收集所有问题
        all_issues = []
        all_warnings = []
        for log in self.optimization_logs:
            if 'issues' in log:
                all_issues.extend(log['issues'])
            if 'warnings' in log:
                all_warnings.extend(log['warnings'])
        
        return {
            'final_score': round(final_score, 1),
            'grade': grade,
            'total_shots': len(shots),
            'total_duration': total_duration,
            'optimization_rounds': len(self.optimization_logs),
            'issues': all_issues,
            'warnings': all_warnings,
            'passed': final_score >= self.config.quality_threshold and len(all_issues) == 0
        }
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """获取优化历史"""
        return self.optimization_logs.copy()
    
    def reset_history(self):
        """重置优化历史"""
        self.optimization_logs = []
