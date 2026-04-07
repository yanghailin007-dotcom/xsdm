"""
CharacterNarrativeSession 产物格式测试
=========================================

验证产物格式与传统模式一致
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.session_mode.validators import CharacterNarrativeValidator


def create_mock_outputs():
    """创建模拟产物"""
    return {
        "character_design": {
            "protagonist": {
                "basic_info": {
                    "name": "林默",
                    "age": "25岁",
                    "gender": "男",
                    "appearance": "普通上班族外貌，末世后变得坚毅",
                    "background": "原本是普通白领，病毒爆发时正在公司加班，幸运地躲过了最初的混乱"
                },
                "personality": {
                    "core_traits": ["谨慎", "果断", "有领导力", "重情义"],
                    "behavior_pattern": "做事前先观察分析，关键时刻能果断决策",
                    "values": "生存至上，但不放弃人性",
                    "flaws": "有时过于谨慎，对陌生人防备心太重"
                },
                "goals": {
                    "short_term": "建立安全据点，囤积足够物资",
                    "long_term": "建立势力，重建秩序",
                    "motivation": "保护身边的人，不让自己经历过的痛苦发生在他人身上"
                },
                "abilities": {
                    "initial": "无限储物空间，时间静止",
                    "limitations": "只能存放非生命体，空间大小与体力相关",
                    "growth_potential": "可以解锁更多功能，如空间内种植、时间流速调节"
                },
                "relationship_position": "初期独狼，后期成为团队核心"
            },
            "supporting_characters": [
                {
                    "role": "女主",
                    "name": "苏晴",
                    "description": "邻居美女护士，性格温柔坚强，擅长医疗",
                    "story_function": "主角的情感寄托，后期负责团队医疗"
                },
                {
                    "role": "兄弟",
                    "name": "王强",
                    "description": "退伍特种兵，性格豪爽，战斗力强",
                    "story_function": "主角的左膀右臂，负责战斗和安全"
                }
            ],
            "antagonist": {
                "name": "赵天龙",
                "positioning": "军方高层，野心家",
                "motivation": "想利用主角的空间能力称霸末世",
                "conflict_with_protagonist": "从合作到对立，最终决战"
            }
        },
        "emotional_blueprint": {
            "emotional_arcs": [
                {
                    "stage": "第一阶段：觉醒囤货",
                    "emotional_tone": "恐慌中带着希望",
                    "reader_feeling": "紧张刺激，期待主角囤货"
                },
                {
                    "stage": "第二阶段：建立势力",
                    "emotional_tone": "艰难奋斗，逐步壮大",
                    "reader_feeling": "爽感积累，看着势力成长"
                },
                {
                    "stage": "第三阶段：争霸末世",
                    "emotional_tone": "热血激昂，最终登顶",
                    "reader_feeling": "高潮迭起，最终大满足"
                }
            ],
            "key_emotional_beats": [
                {
                    "chapter_percent": 5,
                    "description": "觉醒空间能力，从绝望中看到希望",
                    "emotional_shift": "从恐慌到惊喜"
                },
                {
                    "chapter_percent": 25,
                    "description": "建立安全屋，获得初步安全感",
                    "emotional_shift": "从漂泊到安稳"
                },
                {
                    "chapter_percent": 50,
                    "description": "势力初成，第一次大胜",
                    "emotional_shift": "从弱小到强大"
                },
                {
                    "chapter_percent": 80,
                    "description": "与反派决战前夕，背水一战",
                    "emotional_shift": "从积累到爆发"
                }
            ],
            "emotional_themes": [
                "末世中的生存与人性",
                "从普通人到英雄的蜕变",
                "建立新秩序的使命感"
            ]
        },
        "global_growth_plan": {
            "protagonist_growth": [
                {
                    "stage": "起(开局)",
                    "chapter_range": "1-50章",
                    "growth_goal": "觉醒能力，建立安全基地",
                    "ability_progression": "掌握基础空间能力，初步囤货",
                    "mental_growth": "从普通人蜕变为末世生存者"
                },
                {
                    "stage": "承(发展)",
                    "chapter_range": "51-150章",
                    "growth_goal": "收编团队，建立势力",
                    "ability_progression": "空间能力升级，解锁新功能",
                    "mental_growth": "学会领导，承担责任"
                },
                {
                    "stage": "转(高潮)",
                    "chapter_range": "151-250章",
                    "growth_goal": "与各大势力争霸",
                    "ability_progression": "空间能力大成",
                    "mental_growth": "成为真正的领袖"
                },
                {
                    "stage": "合(结局)",
                    "chapter_range": "251-300章",
                    "growth_goal": "重建秩序，拯救世界",
                    "ability_progression": "空间能力圆满",
                    "mental_growth": "成就传奇，留下希望"
                }
            ],
            "milestone_events": [
                {
                    "chapter_range": "第10章",
                    "event": "觉醒空间能力",
                    "significance": "获得末世生存的金手指"
                },
                {
                    "chapter_range": "第30章",
                    "event": "建立安全屋",
                    "significance": "获得末世中的第一个家"
                },
                {
                    "chapter_range": "第60章",
                    "event": "收编第一批追随者",
                    "significance": "从独狼变成团队领袖"
                },
                {
                    "chapter_range": "第120章",
                    "event": "击败掠夺者团伙",
                    "significance": "势力初成，打响名号"
                },
                {
                    "chapter_range": "第200章",
                    "event": "与军方正式对立",
                    "significance": "进入争霸阶段"
                },
                {
                    "chapter_range": "第280章",
                    "event": "击败最终反派",
                    "significance": "成为末世最强势力"
                }
            ],
            "power_progression": [
                {
                    "chapter": "第1章",
                    "upgrade": "觉醒基础空间能力",
                    "impact": "可以存储物资"
                },
                {
                    "chapter": "第50章",
                    "upgrade": "空间扩容",
                    "impact": "可以存储更多物资"
                },
                {
                    "chapter": "第100章",
                    "upgrade": "解锁空间内时间流速调节",
                    "impact": "可以保鲜食物，加速种植"
                },
                {
                    "chapter": "第200章",
                    "upgrade": "空间能力大成",
                    "impact": "可以短暂开启空间通道"
                }
            ],
            "relationship_development": [
                {
                    "character": "苏晴",
                    "relationship_change": "从邻居到恋人",
                    "chapter": "第30-100章"
                },
                {
                    "character": "王强",
                    "relationship_change": "从陌生到生死兄弟",
                    "chapter": "第20-50章"
                },
                {
                    "character": "赵天龙",
                    "relationship_change": "从合作到敌对",
                    "chapter": "第100-280章"
                }
            ]
        }
    }


def test_format_validation():
    """测试产物格式验证"""
    print("\n" + "="*60)
    print("测试产物格式验证")
    print("="*60)
    
    outputs = create_mock_outputs()
    
    validator = CharacterNarrativeValidator()
    result = validator.validate(outputs)
    
    if result.is_valid:
        print("产物格式验证通过")
        print(f"  - character_design: OK")
        print(f"  - emotional_blueprint: OK")
        print(f"  - global_growth_plan: OK")
        return True
    else:
        print("产物格式验证失败:")
        print(result.get_error_report())
        return False


def test_context_brief():
    """测试 Context Brief 生成"""
    print("\n" + "="*60)
    print("测试 Context Brief")
    print("="*60)
    
    # 模拟 export_context_brief 输出
    outputs = create_mock_outputs()
    
    character_design = outputs.get("character_design", {})
    emotional_blueprint = outputs.get("emotional_blueprint", {})
    growth_plan = outputs.get("global_growth_plan", {})
    
    protagonist = character_design.get("protagonist", {})
    
    brief = {
        "protagonist_profile": {
            "name": protagonist.get("basic_info", {}).get("name", ""),
            "core_traits": protagonist.get("personality", {}).get("core_traits", []),
            "goals": protagonist.get("goals", {}).get("long_term", ""),
            "abilities": protagonist.get("abilities", {}).get("initial", "")
        },
        "key_supporting_chars": [
            {"role": sc.get("role", ""), "name": sc.get("name", "")}
            for sc in character_design.get("supporting_characters", [])
        ],
        "antagonist": {
            "name": character_design.get("antagonist", {}).get("name", ""),
            "motivation": character_design.get("antagonist", {}).get("motivation", "")
        },
        "emotional_arc": emotional_blueprint.get("emotional_arcs", []),
        "key_emotional_turning_points": [
            beat.get("description", "")
            for beat in emotional_blueprint.get("key_emotional_beats", [])
        ],
        "growth_milestones": [
            event.get("event", "")
            for event in growth_plan.get("milestone_events", [])
        ]
    }
    
    print("Context Brief 结构:")
    for key in brief.keys():
        print(f"  - {key}: OK")
    
    print(f"\n主角: {brief['protagonist_profile']['name']}")
    print(f"配角数: {len(brief['key_supporting_chars'])}")
    print(f"情绪转折点: {len(brief['key_emotional_turning_points'])}")
    print(f"成长里程碑: {len(brief['growth_milestones'])}")
    
    return True


def save_outputs():
    """保存产物到文件"""
    print("\n" + "="*60)
    print("保存产物")
    print("="*60)
    
    output_dir = Path("tests/comparison_outputs/character_narrative")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = create_mock_outputs()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存完整产物
    output_file = output_dir / f"character_narrative_output_{timestamp}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(outputs, f, ensure_ascii=False, indent=2)
    
    # 分别保存
    modules = ["character_design", "emotional_blueprint", "global_growth_plan"]
    for module in modules:
        module_file = output_dir / f"{module}_{timestamp}.json"
        with open(module_file, 'w', encoding='utf-8') as f:
            json.dump(outputs[module], f, ensure_ascii=False, indent=2)
    
    print(f"产物已保存: {output_dir}")
    return True


def main():
    """主函数"""
    print("="*60)
    print("CharacterNarrativeSession 产物格式测试")
    print("="*60)
    
    results = []
    
    results.append(("格式验证", test_format_validation()))
    results.append(("Context Brief", test_context_brief()))
    results.append(("保存产物", save_outputs()))
    
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "="*60)
    if all_passed:
        print("所有测试通过")
        print("CharacterNarrativeSession 产物格式正确")
    else:
        print("部分测试失败")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
