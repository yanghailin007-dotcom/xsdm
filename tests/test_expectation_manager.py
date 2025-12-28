"""
期待感管理系统测试
测试期待感的种植、释放和验证流程
"""

import unittest
from src.managers.ExpectationManager import (
    ExpectationManager,
    ExpectationType,
    ExpectationStatus,
    ExpectationIntegrator
)


class TestExpectationManager(unittest.TestCase):
    """测试期待管理器"""
    
    def setUp(self):
        """每个测试前初始化"""
        self.manager = ExpectationManager()
    
    def test_tag_event_with_expectation(self):
        """测试为事件添加期待标签"""
        exp_id = self.manager.tag_event_with_expectation(
            event_id="event_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=10,
            description="展示温天仁的六极真魔体威力",
            target_chapter=15
        )
        
        # 验证期待被正确创建
        self.assertIn(exp_id, self.manager.expectations)
        exp_record = self.manager.expectations[exp_id]
        
        self.assertEqual(exp_record.expectation_type, ExpectationType.SHOWCASE)
        self.assertEqual(exp_record.planted_chapter, 10)
        self.assertEqual(exp_record.target_chapter, 15)
        self.assertEqual(exp_record.status, ExpectationStatus.PLANTED)
        self.assertEqual(self.manager.planted_count, 1)
    
    def test_nested_doll_expectation(self):
        """测试套娃式期待"""
        # 大期待
        main_exp_id = self.manager.tag_event_with_expectation(
            event_id="main_arc_001",
            expectation_type=ExpectationType.SUPPRESSION_RELEASE,
            planting_chapter=10,
            description="击败温天仁,为师门报仇",
            target_chapter=25
        )
        
        # 小期待1
        sub_exp1_id = self.manager.tag_event_with_expectation(
            event_id="sub_arc_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=12,
            description="获得六极真魔体",
            target_chapter=18,
            related_expectations=[main_exp_id]
        )
        
        # 小期待2
        sub_exp2_id = self.manager.tag_event_with_expectation(
            event_id="sub_arc_002",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=15,
            description="掌握万剑归宗",
            target_chapter=20,
            related_expectations=[main_exp_id, sub_exp1_id]
        )
        
        # 验证关联关系
        sub_exp1 = self.manager.expectations[sub_exp1_id]
        sub_exp2 = self.manager.expectations[sub_exp2_id]
        
        self.assertIn(main_exp_id, sub_exp1.related_expectations)
        self.assertIn(main_exp_id, sub_exp2.related_expectations)
        self.assertIn(sub_exp1_id, sub_exp2.related_expectations)
    
    def test_pre_generation_check(self):
        """测试生成前检查"""
        # 种植一个期待,目标章节是15
        exp_id = self.manager.tag_event_with_expectation(
            event_id="event_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=10,
            description="展示六极真魔体",
            target_chapter=15
        )
        
        # 在第15章生成前检查
        constraints = self.manager.pre_generation_check(chapter_num=15)
        
        # 应该有must_release约束
        self.assertTrue(len(constraints) > 0)
        release_constraints = [c for c in constraints if c.type == "must_release"]
        self.assertTrue(len(release_constraints) > 0)
        
        # 检查约束内容
        constraint = release_constraints[0]
        self.assertEqual(constraint.urgency, "critical")
        self.assertIn("展示六极真魔体", constraint.message)
        self.assertEqual(constraint.expectation_id, exp_id)
    
    def test_post_generation_validate_success(self):
        """测试生成后验证 - 成功案例"""
        # 种植期待
        exp_id = self.manager.tag_event_with_expectation(
            event_id="event_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=10,
            description="获得六极真魔体",
            target_chapter=15
        )
        
        # 模拟内容分析 - 包含满足指标
        content_analysis = {
            "content": """
            主角经过千辛万苦,终于获得了六极真魔体。
            体内真气涌动,实力大增,感受到前所未有的强大。
            周围的修士都被这股威势震惊了。
            """
        }
        
        # 验证
        result = self.manager.post_generation_validate(
            chapter_num=15,
            content_analysis=content_analysis,
            released_expectation_ids=[exp_id]
        )
        
        # 验证结果
        self.assertTrue(len(result["satisfied_expectations"]) > 0)
        satisfied_exp = result["satisfied_expectations"][0]
        self.assertEqual(satisfied_exp["id"], exp_id)
        self.assertGreaterEqual(satisfied_exp["score"], 7.0)
        
        # 验证期待状态
        exp_record = self.manager.expectations[exp_id]
        self.assertEqual(exp_record.status, ExpectationStatus.RELEASED)
        self.assertEqual(exp_record.released_chapter, 15)
        # satisfaction_score 可能为 None，需要先检查
        if exp_record.satisfaction_score is not None:
            self.assertGreaterEqual(exp_record.satisfaction_score, 7.0)
        else:
            self.fail("satisfaction_score should not be None after validation")
    
    def test_post_generation_validate_failure(self):
        """测试生成后验证 - 失败案例"""
        # 种植期待
        exp_id = self.manager.tag_event_with_expectation(
            event_id="event_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=10,
            description="获得六极真魔体",
            target_chapter=15
        )
        
        # 模拟内容分析 - 不包含满足指标
        content_analysis = {
            "content": """
            主角继续修炼,感受着体内真气的流动。
            """
        }
        
        # 验证
        result = self.manager.post_generation_validate(
            chapter_num=15,
            content_analysis=content_analysis,
            released_expectation_ids=[exp_id]
        )
        
        # 验证结果 - 应该有违规
        self.assertTrue(len(result["violations"]) > 0)
        violation = result["violations"][0]
        self.assertEqual(violation["severity"], "high")
        self.assertIn("满足度不足", violation["message"])
    
    def test_generate_expectation_report(self):
        """测试生成期待感报告"""
        # 种植多个期待
        self.manager.tag_event_with_expectation(
            event_id="event_001",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=10,
            description="展示六极真魔体",
            target_chapter=15
        )
        
        self.manager.tag_event_with_expectation(
            event_id="event_002",
            expectation_type=ExpectationType.EMOTIONAL_HOOK,
            planting_chapter=12,
            description="宗门长老轻视主角",
            target_chapter=18
        )
        
        # 生成报告
        report = self.manager.generate_expectation_report(
            start_chapter=1,
            end_chapter=20
        )
        
        # 验证报告内容
        self.assertEqual(report["total_expectations"], 2)
        self.assertGreaterEqual(report["released_expectations"], 0)
        self.assertIn("expectation_type_stats", report)


class TestExpectationIntegrator(unittest.TestCase):
    """测试期待集成器"""
    
    def setUp(self):
        """每个测试前初始化"""
        self.manager = ExpectationManager()
        self.integrator = ExpectationIntegrator(self.manager)
    
    def test_analyze_and_tag_major_event(self):
        """测试分析和标记重大事件"""
        major_events = [
            {
                "name": "击败温天仁",
                "chapter_range": "10-25",
                "main_goal": "击败温天仁,为师门报仇",
                "composition": {}
            }
        ]
        
        result = self.integrator.analyze_and_tag_events(
            major_events=major_events,
            stage_name="opening_stage"
        )
        
        # 验证结果
        self.assertGreater(result["tagged_count"], 0)
        self.assertIn("expectation_summary", result)
        
        # 验证期待被创建
        self.assertEqual(self.manager.planted_count, 1)
    
    def test_analyze_and_tag_medium_event(self):
        """测试分析和标记中型事件"""
        major_events = [
            {
                "name": "击败温天仁",
                "chapter_range": "10-25",
                "main_goal": "击败温天仁",
                "composition": {
                    "起": [
                        {
                            "name": "宗门长老轻视主角",
                            "chapter_range": "8-10",
                            "main_goal": "宗门长老认为主角资质平庸",
                            "emotional_focus": "误解和轻视"
                        }
                    ]
                }
            }
        ]
        
        result = self.integrator.analyze_and_tag_events(
            major_events=major_events,
            stage_name="opening_stage"
        )
        
        # 验证结果 - 应该标记了重大事件和中型事件
        self.assertGreaterEqual(result["tagged_count"], 2)


class TestExpectationWorkflow(unittest.TestCase):
    """测试完整的期待感工作流程"""
    
    def test_complete_workflow(self):
        """测试完整的工作流程"""
        manager = ExpectationManager()
        
        # 第1步: 规划阶段 - 种植期待
        exp_id_1 = manager.tag_event_with_expectation(
            event_id="showcase_power",
            expectation_type=ExpectationType.SHOWCASE,
            planting_chapter=5,
            description="温天仁展示六极真魔体威力",
            target_chapter=15
        )
        
        exp_id_2 = manager.tag_event_with_expectation(
            event_id="emotional_hook",
            expectation_type=ExpectationType.EMOTIONAL_HOOK,
            planting_chapter=8,
            description="宗门长老轻视主角",
            target_chapter=12
        )
        
        # 第2步: 生成前检查 (第12章)
        constraints_ch12 = manager.pre_generation_check(chapter_num=12)
        self.assertTrue(any(c.expectation_id == exp_id_2 for c in constraints_ch12))
        
        # 模拟第12章生成并验证
        manager.post_generation_validate(
            chapter_num=12,
            content_analysis={"content": "主角展示实力,长老震惊后悔"},
            released_expectation_ids=[exp_id_2]
        )
        
        # 第3步: 生成前检查 (第15章)
        constraints_ch15 = manager.pre_generation_check(chapter_num=15)
        self.assertTrue(any(c.expectation_id == exp_id_1 for c in constraints_ch15))
        
        # 模拟第15章生成并验证
        manager.post_generation_validate(
            chapter_num=15,
            content_analysis={"content": "主角获得六极真魔体,实力大增"},
            released_expectation_ids=[exp_id_1]
        )
        
        # 第4步: 生成报告
        report = manager.generate_expectation_report(1, 20)
        
        # 验证整体结果
        self.assertEqual(report["total_expectations"], 2)
        self.assertEqual(report["released_expectations"], 2)
        self.assertEqual(report["satisfaction_rate"], 100.0)


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行期待感管理系统测试")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestExpectationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestExpectationIntegrator))
    suite.addTests(loader.loadTestsFromTestCase(TestExpectationWorkflow))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    print(f"运行测试: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    run_all_tests()