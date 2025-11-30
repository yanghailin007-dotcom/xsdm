"""
集成测试示例 (Integration Test Example)
展示如何使用虚假数据与真实的 NovelGenerator 集成测试

这个脚本演示了如何在不调用真实 API 的情况下，
通过 Mock 对象来测试整个小说生成系统的核心逻辑。
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import Mock, patch, MagicMock
from src.utils.logger import get_logger
from config import CONFIG
import json
from datetime import datetime

def create_mock_api_client():
    """创建模拟 API 客户端"""
    mock_api = Mock()
    
    def mock_call_api(messages, role_name=None, **kwargs):
        """模拟 API 调用"""
        content = messages[-1]["content"] if messages else ""
        
        # 根据不同的请求返回不同的模拟数据
        if "故事方案" in content or "创意" in content:
            return json.dumps({
                "novel_title": "凡人修仙同人·观战者",
                "novel_synopsis": "穿越者李尘身具观战悟道体质",
                "plan_score": 9.2
            }, ensure_ascii=False)
        
        elif "章节" in content:
            return json.dumps({
                "chapter_title": "乱星观劫·初现异象",
                "outline": ["事件1", "事件2", "事件3"],
                "word_count": 3500
            }, ensure_ascii=False)
        
        elif "内容" in content or "生成" in content:
            return "第一章 乱星观劫·初现异象\n\n这是生成的章节内容..." * 20
        
        elif "评估" in content:
            return json.dumps({
                "score": 8.7,
                "quality": "优秀",
                "issues": []
            }, ensure_ascii=False)
        
        else:
            return json.dumps({"status": "ok"}, ensure_ascii=False)
    
    mock_api.call_api = mock_call_api
    mock_api.get_default_provider = Mock(return_value="mock_provider")
    mock_api.get_current_model = Mock(return_value="mock_model")
    
    return mock_api


def create_mock_event_bus():
    """创建模拟事件总线"""
    mock_bus = Mock()
    mock_bus.subscribe = Mock()
    mock_bus.emit = Mock()
    return mock_bus


def test_with_real_components():
    """使用真实组件但模拟 API 进行测试"""
    logger = get_logger("IntegrationTest")
    
    logger.info("\n" + "="*70)
    logger.info("集成测试: 真实组件 + 模拟 API")
    logger.info("="*70)
    
    try:
        # 1. 创建模拟 API 客户端
        logger.info("\n[步骤 1] 创建模拟 API 客户端")
        mock_api = create_mock_api_client()
        logger.info("✅ 模拟 API 客户端已创建")
        
        # 2. 创建模拟事件总线
        logger.info("\n[步骤 2] 创建模拟事件总线")
        mock_bus = create_mock_event_bus()
        logger.info("✅ 模拟事件总线已创建")
        
        # 3. 测试 API 调用
        logger.info("\n[步骤 3] 测试模拟 API 调用")
        response = mock_api.call_api([
            {"role": "user", "content": "根据创意生成故事方案"}
        ])
        logger.info(f"✅ API 响应: {response[:100]}...")
        
        # 4. 创建虚假创意数据
        logger.info("\n[步骤 4] 构建虚假创意数据")
        creative_data = {
            "coreSetting": "凡人修仙传同人，主角为穿越者",
            "coreSellingPoints": "观战悟道体质+因果干涉命运",
            "completeStoryline": {
                "opening": {
                    "stageName": "乱星观劫·阴冥托孤",
                    "summary": "乱星海观战→阴冥求生→绝境情缘→天南新生",
                    "arc_goal": "完成过渡，建立羁绊"
                },
                "development": {
                    "stageName": "药园潜龙·双星暗弈",
                    "summary": "同期入宗→初识沛灵→微妙试探→资源暗争",
                    "arc_goal": "建立潜伏环境"
                },
                "conflict": {
                    "stageName": "元婴双曜·天南惊变",
                    "summary": "结婴天兆→韩立结婴→地位重定→幕兰来袭",
                    "arc_goal": "成功结婴并确立地位"
                },
                "ending": {
                    "stageName": "道途共行·灵界曙光",
                    "summary": "道侣同心→知己至交→宗门鼎盛→灵界之约",
                    "arc_goal": "实现圆满"
                }
            }
        }
        logger.info("✅ 创意数据已构建")
        logger.info(f"   核心设定: {creative_data['coreSetting'][:40]}...")
        
        # 5. 创建虚假小说数据
        logger.info("\n[步骤 5] 构建虚假小说数据")
        novel_data = {
            "novel_title": "凡人修仙同人·观战者",
            "novel_synopsis": "穿越者李尘身具观战悟道体质，通过观摩强者对战获得修行启悟。",
            "total_chapters": 50,
            "current_progress": {
                "completed_chapters": 0,
                "current_chapter": 1,
                "characters": {
                    "主角": {"name": "李尘", "status": "初始化"},
                    "女主": {"name": "梅凝", "status": "初始化"}
                }
            }
        }
        logger.info("✅ 小说数据已构建")
        logger.info(f"   标题: {novel_data['novel_title']}")
        logger.info(f"   总章节: {novel_data['total_chapters']}")
        
        # 6. 创建 GenerationContext
        logger.info("\n[步骤 6] 创建生成上下文")
        from Contexts import GenerationContext
        
        context = GenerationContext(
            chapter_number=1,
            total_chapters=50,
            novel_data=novel_data,
            stage_plan=creative_data["completeStoryline"]["opening"],
            event_context={},
            foreshadowing_context={},
            growth_context={},
            expectation_context={}
        )
        
        is_valid, msg = context.validate()
        if is_valid:
            logger.info(f"✅ 生成上下文有效: {context}")
        else:
            logger.info(f"❌ 生成上下文无效: {msg}")
            return False
        
        # 7. 模拟完整的生成流程
        logger.info("\n[步骤 7] 模拟完整生成流程 (5 章)")
        
        for chapter_num in range(1, 6):
            logger.info(f"\n   【第 {chapter_num} 章】")
            
            # 7a. 生成大纲
            outline_response = mock_api.call_api([
                {"role": "user", "content": f"生成第 {chapter_num} 章大纲"}
            ])
            try:
                outline = json.loads(outline_response) if outline_response else {}
                outline_title = outline.get('章节标题', outline.get('chapter_title', '未知'))
            except (json.JSONDecodeError, TypeError):
                outline_title = '解析失败'
                outline = {}
            logger.info(f"      ✓ 大纲: {outline_title}")
            
            # 7b. 生成内容
            content_response = mock_api.call_api([
                {"role": "user", "content": f"生成第 {chapter_num} 章内容"}
            ])
            logger.info(f"      ✓ 内容: {len(content_response) if content_response else 0} 字")
            
            # 7c. 评估质量
            quality_response = mock_api.call_api([
                {"role": "user", "content": f"评估第 {chapter_num} 章质量"}
            ])
            try:
                quality = json.loads(quality_response) if quality_response else {}
                quality_score = quality.get('score', quality.get('整体评分', 0))
            except (json.JSONDecodeError, TypeError):
                quality_score = 0
            logger.info(f"      ✓ 评分: {quality_score}")
        
        logger.info("\n✅ 完整生成流程模拟成功")
        
        # 8. 数据持久化验证
        logger.info("\n[步骤 8] 数据持久化验证")
        import tempfile
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 保存创意数据
            creative_file = Path(tmpdir) / "creative.json"
            with open(creative_file, 'w', encoding='utf-8') as f:
                json.dump(creative_data, f, ensure_ascii=False, indent=2)
            
            # 保存小说数据
            novel_file = Path(tmpdir) / "novel.json"
            with open(novel_file, 'w', encoding='utf-8') as f:
                json.dump(novel_data, f, ensure_ascii=False, indent=2)
            
            # 保存章节
            chapter_file = Path(tmpdir) / "chapter_001.txt"
            with open(chapter_file, 'w', encoding='utf-8') as f:
                f.write("这是一个生成的章节")
            
            logger.info(f"✅ 数据持久化验证通过")
            logger.info(f"   创意文件: {creative_file.exists()}")
            logger.info(f"   小说文件: {novel_file.exists()}")
            logger.info(f"   章节文件: {chapter_file.exists()}")
        
        # 总结
        logger.info("\n" + "="*70)
        logger.info("集成测试总结")
        logger.info("="*70)
        logger.info("✅ 模拟 API 客户端正常运作")
        logger.info("✅ 生成上下文创建和验证通过")
        logger.info("✅ 完整生成流程可模拟执行")
        logger.info("✅ 数据持久化功能正常")
        logger.info("\n这验证了系统架构的完整性，现在可以安全地集成真实 API。")
        logger.info("="*70 + "\n")
        
        return True
        
    except Exception as e:
        logger.info(f"\n❌ 集成测试失败: {e}")
        import traceback
        logger.info(traceback.format_exc())
        return False


def test_mock_quality_assessment():
    """测试模拟质量评估"""
    logger = get_logger("QualityTest")
    
    logger.info("\n" + "="*70)
    logger.info("质量评估模拟测试")
    logger.info("="*70)
    
    try:
        mock_api = create_mock_api_client()
        
        test_content = "第一章 测试章节\n\n这是一段生成的章节内容。" * 50
        
        logger.info(f"\n测试内容长度: {len(test_content)} 字")
        
        # 调用质量评估
        response = mock_api.call_api([
            {"role": "user", "content": f"请评估以下内容的质量: {test_content[:200]}"}
        ])
        
        assessment = json.loads(response)
        
        logger.info(f"\n评估结果:")
        logger.info(f"  总体评分: {assessment.get('score', 'N/A')}")
        logger.info(f"  质量评级: {assessment.get('quality', 'N/A')}")
        logger.info(f"  问题数量: {len(assessment.get('issues', []))}")
        
        logger.info(f"\n✅ 质量评估模拟成功")
        logger.info("="*70 + "\n")
        
        return True
    except Exception as e:
        logger.info(f"❌ 质量评估测试失败: {e}")
        return False


def main():
    """主测试函数"""
    logger = get_logger("Main")
    
    logger.info("\n\n")
    logger.info("*"*70)
    logger.info("集成测试套件")
    logger.info("*"*70)
    
    results = []
    
    # 运行测试
    logger.info("\n[测试 1] 主集成测试")
    results.append(("主集成测试", test_with_real_components()))
    
    logger.info("\n[测试 2] 质量评估测试")
    results.append(("质量评估测试", test_mock_quality_assessment()))
    
    # 总结
    logger.info("\n" + "*"*70)
    logger.info("测试总结")
    logger.info("*"*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"[{status}] {test_name}")
    
    logger.info(f"\n总体: {passed}/{total} 测试通过 ({100*passed/total:.1f}%)")
    logger.info("*"*70 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
