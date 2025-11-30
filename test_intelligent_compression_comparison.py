"""智能权重压缩vs传统距离压缩对比测试"""
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.LayeredContextManager import LayeredContextManager
from src.utils.IntelligentWeightedCompression import IntelligentWeightedCompressionManager

def print_safe(text):
    """安全打印，避免编码错误"""
    try:
        print(text)
    except UnicodeEncodeError:
        clean_text = text.encode('ascii', errors='ignore').decode('ascii')
        print(clean_text)

def create_realistic_novel_context():
    """创建真实小说场景的上下文"""
    return {
        # 主角相关信息 - 最高权重
        "protagonist_info": {
            "name": "林云",
            "current_level": "筑基中期",
            "main_abilities": [
                "御剑术（精通）",
                "五行神通（天赋）",
                "空间跳跃（获得传承后）",
                "炼丹术（学习中）"
            ],
            "character_arc": "从普通散修一步步成长为修仙界的巅峰强者，历经磨难，始终不忘初心，最终守护了整个修仙界",
            "emotional_state": "正值突破的关键期，心境上有些波动，但对修炼的信念从未动摇",
            "key_memories": [
                "获得上古传承的那一天改变了命运",
                "与师父初遇的教诲时刻铭记在心",
                "第一次真正心动是因为苏雪儿",
                "面对强敌时的生死抉择塑造了坚韧性格"
            ]
        },

        # 主线剧情 - 很高权重
        "main_plot_progression": {
            "current_arc": "传承秘境探索篇",
            "arc_chapters": [45, 46, 47, 48, 49, 50],
            "plot_twist": "在秘境深处发现了自己的身世之谜，原来体内流淌着上古神族的血脉",
            "setup_elements": [
                "早期遇到的神秘老人实为传承守护者",
                "修炼时遇到的瓶颈与血脉觉醒有关",
                "古籍中反复出现的神子预言指的就是自己"
            ],
            "climax_building": "正在追寻血脉力量的真相，即将面对改变命运的最终抉择"
        },

        # 重要关系 - 较高权重
        "important_relationships": {
            "master_disciple": {
                "苏玄天": "师父，神秘的传承之主，真实身份是上古神族的守护者",
                "relationship_status": "亦师亦父，正在教习血脉力量的控制方法"
            },
            "love_interest": {
                "苏雪儿": "红颜知己，天剑宗圣女，两情相悦",
                "relationship_development": "感情稳定发展，已到谈婚论嫁阶段",
                "shared_secrets": "知道林云的身世之谜，正在共同面对即将到来的挑战"
            },
            "rival": {
                "李天霸": "宿敌，魔云派少主，多次与林云发生冲突",
                "conflict_source": "觊觎林云的传承和血脉力量",
                "final_confrontation": "将在秘境深处进行最终对决"
            }
        },

        # 重大事件 - 高权重
        "major_recent_events": [
            {
                "chapter": 42,
                "event": "突破筑基期成功",
                "impact": "修为大涨，掌握了更强的力量",
                "significance": "标志着正式踏入修仙界的更高层次"
            },
            {
                "chapter": 44,
                "event": "发现血脉秘密",
                "impact": "对自己的身世产生了疑问，开始了寻找真相的旅程",
                "significance": "这是改变命运的关键转折点"
            },
            {
                "chapter": 45,
                "event": "进入传承秘境",
                "impact": "开始了寻找身世真相的冒险",
                "significance": "将会揭开上古神族的历史和自己的使命"
            }
        ],

        # 角色成长 - 中高权重
        "character_development": {
            "emotional_growth": "从最初的懵懂无知到现在的心境通透，经历了很多情感的洗礼",
            "power_progression": "修为从炼气期一步步突破到现在的筑基中期，每一步都很扎实",
            "wisdom_gained": [
                "明白实力的重要性，但更明白人性的可贵",
                "学会了权衡利弊，不轻易冒险",
                "懂得了团队合作的力量",
                "对善恶有了更深刻的理解"
            ]
        },

        # 支线剧情 - 中等权重
        "subplots": [
            {
                "name": "修炼伙伴的成长",
                "status": "张狂也在秘境中获得了机缘，实力大增",
                "relevance": "重要盟友，会在最终决战中起到关键作用"
            },
            {
                "name": "宗门内部事务",
                "status": "天剑宗正在面临魔云派的威胁",
                "relevance": "需要尽快解决外部威胁，保护宗门"
            }
        ],

        # 配角相关 - 较低权重
        "supporting_characters": {
            "张狂": "万妖谷的妖修，性格豪爽，是林云的好朋友",
            "陈明": "丹鼎门弟子，擅长炼丹，多次帮助林云",
            "王老": "神秘的散修，偶尔给林云一些指导"
        },

        # 背景设定 - 低权重
        "background_info": {
            "world_setting": "这是一个修仙者与凡人共存的世界，修仙者掌握着强大的力量",
            "power_system": "修仙境界分为：炼气、筑基、金丹、元婴、化神等多个层次",
            "major_forces": [
                "天剑宗：正道第一大宗门",
                "魔云派：邪道霸主",
                "万妖谷：妖修聚集地",
                "丹鼎门：炼丹师圣地"
            ],
            "geography": "世界分为五大域，每个域都有独特的气候和修炼资源"
        },

        # 次要事件 - 最低权重
        "minor_events": [
            {"chapter": 41, "event": "参加宗门小比", "result": "获得奖励，修为略有提升"},
            {"chapter": 43, "event": "购买修炼资源", "detail": "花费了一些灵石购买了丹药"},
            {"chapter": 46, "event": "偶遇朋友", "description": "在路上遇到了陈明，聊了几句"}
        ]
    }

def run_intelligent_compression_comparison():
    """运行智能压缩与传统压缩的对比测试"""
    print("=" * 80)
    print("智能权重压缩 vs 传统距离压缩 - 对比测试")
    print("=" * 80)

    novel_context = create_realistic_novel_context()
    current_chapter = 47

    # 初始化两个压缩管理器
    traditional_manager = LayeredContextManager()
    intelligent_manager = IntelligentWeightedCompressionManager()

    print(f"\n[测试场景]")
    print(f"当前章节: {current_chapter}")
    print(f"上下文章节数据: 从第1章到第47章的完整信息")

    # 计算原始上下文大小
    original_tokens = intelligent_manager._estimate_tokens_fast(novel_context)
    print(f"原始上下文大小: {original_tokens:,} tokens")

    print(f"\n" + "=" * 50)
    print(f"传统距离压缩结果")
    print(f"=" * 50)

    # 测试不同章节距离的传统压缩
    test_scenarios = [
        (1, "46章前", "distant"),
        (20, "27章前", "distant"),
        (30, "17章前", "far"),
        (40, "7章前", "medium"),
        (45, "2章前", "close")
    ]

    print(f"{'章节距离':<15} {'层级':<12} {'压缩后tokens':<15} {'压缩率':<12} {'保留信息':<30}")
    print("-" * 85)

    for target_chapter, description, expected_layer in test_scenarios:
        layer = traditional_manager.get_context_layer(current_chapter, target_chapter)
        compressed = traditional_manager.compress_context(novel_context, current_chapter, target_chapter)
        compressed_tokens = intelligent_manager._estimate_tokens_fast(compressed)
        compression_ratio = (1 - compressed_tokens / original_tokens) * 100

        # 简单分析保留的信息类型
        保留信息 = []
        if "protagonist_info" in compressed:
            保留信息.append("主角信息")
        if "main_plot" in str(compressed):
            保留信息.append("主线剧情")
        if "relationship" in str(compressed):
            保留信息.append("人物关系")

        保留信息_str = ", ".join(保留信息) if 保留信息 else "基本信息"

        print(f"{description:<15} {layer:<12} {compressed_tokens:<15,} {compression_ratio:>6.1f}%     {保留信息_str:<30}")

    print(f"\n" + "=" * 50)
    print(f"智能权重压缩结果")
    print(f"=" * 50)

    # 测试不同的智能压缩策略
    max_tokens_scenarios = [
        (2000, "宽松限制"),
        (1000, "适中限制"),
        (500, "紧张限制"),
        (200, "严格限制"),
        (100, "极严格限制")
    ]

    print(f"{'目标tokens':<15} {'压缩策略':<20} {'实际tokens':<15} {'压缩率':<12} {'关键信息保留':<20}")
    print("-" * 85)

    for max_tokens, description in max_tokens_scenarios:
        compressed = intelligent_manager.compress_context_intelligently(
            novel_context, current_chapter, max_tokens=max_tokens, preserve_critical=True
        )

        actual_tokens = intelligent_manager._estimate_tokens_fast(compressed)
        compression_ratio = (1 - actual_tokens / original_tokens) * 100

        # 检查关键信息是否保留
        critical_preserved = []
        compressed_str = str(compressed).lower()

        if "林云" in compressed_str:
            critical_preserved.append("主角")
        if "突破" in compressed_str or "传承" in compressed_str:
            critical_preserved.append("主线")
        if "苏雪儿" in compressed_str or "感情" in compressed_str:
            critical_preserved.append("感情线")

        critical_str = f"{len(critical_preserved)}/3" if critical_preserved else "0/3"

        # 确定压缩策略
        if actual_tokens >= original_tokens * 0.8:
            strategy = "preserve_all"
        elif actual_tokens >= original_tokens * 0.4:
            strategy = "smart_reduce"
        elif actual_tokens >= original_tokens * 0.1:
            strategy = "essence_only"
        else:
            strategy = "minimal"

        print(f"{max_tokens:<15,} {strategy:<20} {actual_tokens:<15,} {compression_ratio:>6.1f}%     {critical_str:<20}")

    print(f"\n" + "=" * 50)
    print(f"详细对比分析")
    print(f"=" * 50)

    # 深度分析1000 tokens限制下的压缩效果
    print(f"\n[1000 tokens限制下的详细对比]")

    # 传统压缩结果
    traditional_compressed = traditional_manager.compress_context(novel_context, current_chapter, 30)
    traditional_tokens = intelligent_manager._estimate_tokens_fast(traditional_compressed)

    # 智能压缩结果
    intelligent_compressed = intelligent_manager.compress_context_intelligently(
        novel_context, current_chapter, max_tokens=1000, preserve_critical=True
    )
    intelligent_tokens = intelligent_manager._estimate_tokens_fast(intelligent_compressed)

    print(f"传统压缩: {traditional_tokens:,} tokens")
    print(f"智能压缩: {intelligent_tokens:,} tokens")

    # 分析保留的信息质量
    print(f"\n[信息保留质量对比]")

    def analyze_information_quality(compressed_data, method_name):
        """分析压缩后信息的质量"""
        compressed_str = str(compressed_data).lower()

        quality_score = {
            "protagonist": 0,
            "main_plot": 0,
            "relationships": 0,
            "character_development": 0,
            "critical_events": 0
        }

        # 主角信息
        if "林云" in compressed_str:
            quality_score["protagonist"] += 1
        if "突破" in compressed_str or "修为" in compressed_str:
            quality_score["protagonist"] += 1
        if "感情" in compressed_str or "心理" in compressed_str:
            quality_score["protagonist"] += 1

        # 主线剧情
        if "传承" in compressed_str:
            quality_score["main_plot"] += 2
        if "秘境" in compressed_str:
            quality_score["main_plot"] += 1

        # 重要关系
        if "苏雪儿" in compressed_str:
            quality_score["relationships"] += 1
        if "师父" in compressed_str or "朋友" in compressed_str:
            quality_score["relationships"] += 1

        # 角色成长
        if "成长" in compressed_str or "变化" in compressed_str:
            quality_score["character_development"] += 1
        if "心境" in compressed_str or "感悟" in compressed_str:
            quality_score["character_development"] += 1

        # 关键事件
        if "事件" in compressed_str:
            quality_score["critical_events"] += 1
        if "冲突" in compressed_str or "对决" in compressed_str:
            quality_score["critical_events"] += 1

        total_score = sum(quality_score.values())
        print(f"\n{method_name}信息质量评分:")
        for category, score in quality_score.items():
            print(f"  {category}: {score}")
        print(f"  总分: {total_score}/10")

        return total_score

    trad_score = analyze_information_quality(traditional_compressed, "传统压缩")
    intel_score = analyze_information_quality(intelligent_compressed, "智能压缩")

    print(f"\n[结论]")
    if trad_score > 0:
        print(f"智能压缩质量提升: {((intel_score - trad_score) / trad_score * 100):.1f}%")
    else:
        print(f"智能压缩质量提升: 显著（传统压缩丢失了所有关键信息）")
        print(f"智能压缩保留了{intel_score}个关键信息点，而传统压缩保留了0个")

    # 输出智能压缩的权重分析
    print(f"\n[智能权重分析示例]")
    analysis = intelligent_manager._analyze_context_weights(
        {
            "protagonist_info": novel_context["protagonist_info"],
            "minor_event": novel_context["minor_events"][0]
        }, current_chapter, 1
    )

    print(f"分析结果:")
    for element_key, element_analysis in analysis["weighted_elements"].items():
        print(f"  {element_key}:")
        print(f"    内容类型: {element_analysis['content_type']}")
        print(f"    基础权重: {element_analysis['base_weight']:.2f}")
        print(f"    时间因子: {element_analysis['time_factor']:.2f}")
        print(f"    有效权重: {element_analysis['effective_weight']:.3f}")
        print(f"    是否关键: {element_analysis['is_critical']}")
        if element_analysis['importance_reasons']:
            print(f"    重要性原因: {', '.join(element_analysis['importance_reasons'])}")

    print(f"\n" + "=" * 80)
    print_safe("✅ 智能权重压缩对比测试完成")
    print("=" * 80)

    # 推荐使用建议
    print(f"\n[使用建议]")
    print(f"1. 对于小说创作，建议使用智能权重压缩")
    print(f"2. 传统距离压缩适合一般文档处理")
    print(f"3. 智能压缩能更好地保留故事连贯性和一致性")
    print(f"4. 可根据创作需要动态调整权重配置")

if __name__ == "__main__":
    run_intelligent_compression_comparison()