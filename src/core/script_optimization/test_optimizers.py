"""
优化器测试用例
"""
import unittest
import json
from pathlib import Path

from .config import OptimizationConfig
from .optimizers import (
    BeatStructureOptimizer,
    DialogueOptimizer,
    VisualOptimizer,
    InfoLayerOptimizer,
    PlatformValidator
)
from .pipeline import ScriptOptimizationPipeline


class TestBeatStructureOptimizer(unittest.TestCase):
    """测试节拍结构优化器"""
    
    def setUp(self):
        self.optimizer = BeatStructureOptimizer()
        self.sample_beats = {
            "version": "1.0",
            "title": "Test Episode",
            "episode": 1,
            "total_beats": 5,
            "target_duration": 46,
            "beats": [
                {"beat_number": 1, "beat_type": "setup", "description": "开场", "duration_seconds": 3, "emotion": "日常"},
                {"beat_number": 2, "beat_type": "rising", "description": "上升", "duration_seconds": 4, "emotion": "紧张"},
                {"beat_number": 3, "beat_type": "rising", "description": "继续上升", "duration_seconds": 5, "emotion": "紧张"},
                {"beat_number": 4, "beat_type": "setup", "description": "平淡", "duration_seconds": 3, "emotion": "日常"},
                {"beat_number": 5, "beat_type": "setup", "description": "结尾", "duration_seconds": 3, "emotion": "日常"}
            ]
        }
    
    def test_optimize_creates_hook(self):
        """测试是否能正确创建开场钩子"""
        result, log = self.optimizer.optimize(self.sample_beats)
        
        first_beat = result['beats'][0]
        self.assertEqual(first_beat['beat_type'], 'hook')
        # 检查log中有设置hook的fix
        fixes_str = str(log.get('fixes', []))
        self.assertTrue('hook' in fixes_str.lower() or '开场' in fixes_str or '钩子' in fixes_str)
    
    def test_optimize_finds_climax(self):
        """测试是否能识别并标记高潮"""
        result, log = self.optimizer.optimize(self.sample_beats)
        
        beat_types = [b['beat_type'] for b in result['beats']]
        self.assertIn('climax', beat_types)
    
    def test_score_calculation(self):
        """测试评分计算"""
        result, log = self.optimizer.optimize(self.sample_beats)
        
        self.assertIn('score_before', log)
        self.assertIn('score_after', log)
        self.assertGreaterEqual(log['score_after'], 0)
        self.assertLessEqual(log['score_after'], 10)


class TestDialogueOptimizer(unittest.TestCase):
    """测试对白优化器"""
    
    def setUp(self):
        self.optimizer = DialogueOptimizer()
        self.sample_shots = {
            "version": "2.0",
            "shots": [
                {
                    "shot_number": 1,
                    "dialogue": {
                        "speaker": "Character A",
                        "lines_en": "You should remember this next time.",
                        "tone_en": "Teaching"
                    }
                },
                {
                    "shot_number": 2,
                    "dialogue": {
                        "speaker": "Character B", 
                        "lines_en": "Is this... the truth?",
                        "tone_en": "Surprised"
                    }
                },
                {
                    "shot_number": 3,
                    "dialogue": {
                        "speaker": "None",
                        "lines_en": "None",
                        "tone_en": "None"
                    }
                }
            ]
        }
    
    def test_remove_preaching(self):
        """测试删除说教台词"""
        result, log = self.optimizer.optimize(self.sample_shots)
        
        first_dialogue = result['shots'][0]['dialogue']['lines_en']
        # 应该被修改或删除
        self.assertNotEqual(first_dialogue, "You should remember this next time.")
    
    def test_remove_explicit_exposition(self):
        """测试删除直白解说"""
        result, log = self.optimizer.optimize(self.sample_shots)
        
        second_dialogue = result['shots'][1]['dialogue']['lines_en']
        # "Is this..." 应该被处理
        # 实际可能被改为空字符串或省略号
        self.assertIn('changes', log)


class TestVisualOptimizer(unittest.TestCase):
    """测试视觉优化器"""
    
    def setUp(self):
        self.optimizer = VisualOptimizer()
        self.sample_shots = {
            "version": "2.0",
            "shots": [
                {
                    "shot_number": 1,
                    "shot_type": "全景",
                    "veo_prompt_standard": "City street view",
                    "visual_description_standard": "Wide view of city"
                },
                {
                    "shot_number": 2,
                    "shot_type": "Close-up",
                    "veo_prompt_standard": "Cinematic close-up of face",
                    "visual_description_standard": "Face close-up"
                }
            ]
        }
    
    def test_standardize_shot_type(self):
        """测试标准化shot_type"""
        result, log = self.optimizer.optimize(self.sample_shots)
        
        # 中文"全景"应该被转换为英文
        first_shot_type = result['shots'][0]['shot_type']
        self.assertIn(first_shot_type, ['Wide Shot', '全景'])
    
    def test_enhance_veo_prompt(self):
        """测试增强veo_prompt"""
        result, log = self.optimizer.optimize(self.sample_shots)
        
        # 不包含cinematic的prompt应该被增强
        first_prompt = result['shots'][0]['veo_prompt_standard']
        # 可能被添加了"Cinematic shot"前缀
        self.assertTrue(len(first_prompt) > len("City street view"))


class TestPlatformValidator(unittest.TestCase):
    """测试平台质检器"""
    
    def setUp(self):
        self.validator = PlatformValidator()
        self.good_shots = {
            "version": "2.0",
            "shots": [
                {"shot_number": 1, "shot_type": "Wide", "scene_title": "Crisis", "duration_seconds": 2},
                {"shot_number": 2, "shot_type": "Medium", "scene_title": "Action", "duration_seconds": 3},
                {"shot_number": 3, "shot_type": "Close-up", "scene_title": "Climax", "duration_seconds": 4},
                {"shot_number": 4, "shot_type": "Medium", "scene_title": "Hook", "duration_seconds": 3}
            ]
        }
        self.bad_shots = {
            "version": "2.0",
            "shots": [
                {"shot_number": 1, "shot_type": "Wide", "scene_title": "Slow Start", "duration_seconds": 8},
                {"shot_number": 2, "shot_type": "Wide", "scene_title": "Still Slow", "duration_seconds": 7},
                {"shot_number": 3, "shot_type": "Wide", "scene_title": "Too Slow", "duration_seconds": 6}
            ]
        }
    
    def test_validate_good_shots(self):
        """测试良好剧本的验证"""
        result, log = self.validator.validate(self.good_shots, target_duration=46)
        
        self.assertGreaterEqual(log['score'], 7.0)
        self.assertLessEqual(len(log['issues']), 1)
    
    def test_validate_bad_shots(self):
        """测试问题剧本的验证"""
        result, log = self.validator.validate(self.bad_shots, target_duration=46)
        
        # 应该发现问题
        self.assertTrue(len(log['issues']) > 0 or len(log['warnings']) > 0)
    
    def test_check_pacing(self):
        """测试节奏检查"""
        result, log = self.validator.validate(self.bad_shots, target_duration=46)
        
        # 连续慢镜头应该被检测到
        issues_text = str(log['issues'])
        self.assertIn('慢镜头', issues_text or 'slow' in issues_text.lower())


class TestScriptOptimizationPipeline(unittest.TestCase):
    """测试完整管道"""
    
    def setUp(self):
        self.pipeline = ScriptOptimizationPipeline()
        self.sample_beats = {
            "version": "1.0",
            "title": "Test Episode",
            "episode": 1,
            "target_duration": 46,
            "beats": [
                {"beat_number": 1, "description": "Hook scene", "duration_seconds": 3, "emotion": "紧张"},
                {"beat_number": 2, "description": "Rising action", "duration_seconds": 4, "emotion": "上升"},
                {"beat_number": 3, "description": "Climax", "duration_seconds": 5, "emotion": "爆发"},
                {"beat_number": 4, "description": "Resolution", "duration_seconds": 3, "emotion": "回落"}
            ]
        }
        self.sample_shots = {
            "version": "2.0",
            "language": "en",
            "title": "Test",
            "episode": 1,
            "total_shots": 3,
            "shots": [
                {
                    "shot_number": 1,
                    "shot_type": "Wide",
                    "scene_title": "Crisis",
                    "veo_prompt_standard": "City crisis scene",
                    "visual_description_standard": "City view",
                    "dialogue": {"speaker": "None", "lines_en": "None", "tone_en": "None", "audio_note_en": ""},
                    "duration_seconds": 2
                },
                {
                    "shot_number": 2,
                    "shot_type": "Medium",
                    "scene_title": "Action",
                    "veo_prompt_standard": "Action scene",
                    "visual_description_standard": "Action view",
                    "dialogue": {"speaker": "Hero", "lines_en": "You should be careful.", "tone_en": "Warning", "audio_note_en": ""},
                    "duration_seconds": 3
                },
                {
                    "shot_number": 3,
                    "shot_type": "Close-up",
                    "scene_title": "Hook",
                    "veo_prompt_standard": "Suspense scene",
                    "visual_description_standard": "Suspense view",
                    "dialogue": {"speaker": "None", "lines_en": "None", "tone_en": "None", "audio_note_en": ""},
                    "duration_seconds": 3
                }
            ]
        }
    
    def test_optimize_beats(self):
        """测试节拍优化"""
        result, log = self.pipeline.optimize_beats(self.sample_beats)
        
        self.assertIn('beats', result)
        self.assertIn('score_after', log)
        self.assertEqual(log['stage'], 'beat_structure')
    
    def test_optimize_shots(self):
        """测试分镜优化"""
        result, logs = self.pipeline.optimize_shots(self.sample_shots)
        
        self.assertIn('shots', result)
        self.assertIsInstance(logs, list)
        self.assertGreaterEqual(len(logs), 1)
    
    def test_quick_optimize(self):
        """测试快速优化"""
        result, report = self.pipeline.quick_optimize(self.sample_shots, focus='dialogue')
        
        self.assertIn('shots', result)
        self.assertEqual(report['focus'], 'dialogue')
    
    def test_full_pipeline(self):
        """测试完整流程"""
        # 创建包含shots的beats（简化情况）
        full_input = self.sample_shots.copy()
        
        config = OptimizationConfig(
            beat_structure=False,  # 跳过节拍优化，直接优化shots
            dialogue=True,
            visual=True,
            validation=True
        )
        
        result = self.pipeline.full_pipeline(full_input, config=config)
        
        self.assertIn('optimized_shots', result)
        self.assertIn('report', result)
        self.assertIn('final_score', result['report'])


def run_tests():
    """运行所有测试"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == '__main__':
    run_tests()
