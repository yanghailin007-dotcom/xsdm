from web.services.market_driven.chapter_prompt_optimizer import ChapterPromptOptimizer

# 使用同样的测试数据
test_data = {
    'title': '具现石油，龙国暴富',
    'plan': {
        'golden_finger': {
            'type': '诸天扮演系统（国运特供版）',
            'initial_reward': '初始扮演度1%，获得角色5%实力（相当于顶级特种兵战力）',
            'upgrade': '击杀禁地生物（F级=1点，E级=10点，D级=50点）',
            'limitation': '每日仅能维持扮演状态8小时，超时强制解除并虚弱12小时'
        },
        'outline_first_30': [
            {'chapter': 1, 'title': '国运选中', 'event': '绑定系统，首次扮演'},
            {'chapter': 3, 'title': '首次装逼', 'event': '秒杀E级BOSS'}
        ],
        'opening_design': {
            'chapter_1': {
                'scene': '魔都某8平米出租屋，凌晨2点。林默被裁员3个月，负债37.8万，48小时未进食，前女友上午刚跟宝马男离开，房东在门外砸门催租。',
                'action': '手机突然黑屏，弹出血红色文字【国运禁地开启，龙国选中者：林默，是否绑定？】'
            }
        }
    },
    'character_design': {
        'protagonist': {
            'basic_info': {'name': '林默', 'age': 26, 'former_identity': '龙牙特战队队长，代号孤狼', 'current_identity': '国运禁地龙国唯一代表'},
            'archetype': '隐忍型狂魔，前特种兵/顶级雇佣兵退休，因任务失败被诬陷而落魄，表面冷傲内心极度护短',
            'traits': [
                '极致护短：伤害他可以，侮辱龙国或他在乎的人必死',
                '绝对理性：战斗中像机器计算，但涉及民族尊严时瞬间分神',
                '反圣母：对敌人零容忍耐，杀伐果断'
            ],
            'signature_details': {
                'catchphrase': ['龙国，不可辱', '系统，具现', '晚了'],
                'actions': ['战斗前会下意识摸左手腕的废旧军牌', '杀完人必擦拭右手']
            },
            'psychology': {'motivation': '表层是还债和生存，深层是洗清冤屈并守护龙国'}
        },
        'core_allies': [
            {
                'name': '赵铁柱',
                'role': '捧哏型/搞笑担当',
                'function': '负责惊呼林哥牛X、解释主角操作多难',
                'typical_lines': ['林哥这操作，我看不懂但我大受震撼！']
            },
            {
                'name': '苏冰冰',
                'role': '传声筒型/官方解说',
                'function': '负责在直播间科普禁地危险度',
                'typical_lines': ['各位观众，根据数据分析...等等，林默一击打穿了？！']
            }
        ],
        'main_antagonists': {
            'early_stage': [
                {
                    'name': '山田一郎',
                    'identity': '樱花国武士道传人',
                    'hate_point': '极端侮辱龙国历史',
                    'fate': '第3章被林默一刀封喉'
                }
            ]
        }
    },
    'core_worldview': {
        'world_overview': '国运禁地直播流：全球100个国家各选1人进入禁地，选手表现直接关系国家资源奖励/惩罚，全球实时直播',
        'world_rules': [
            {'rule': '禁地内击杀生物可具现资源到现实'},
            {'rule': '选手死亡国家遭受惩罚'},
            {'rule': '全球实时直播，弹幕互动'}
        ],
        'power_system': {'summary': 'F-SSS级禁地生物，对应不同实力层次。F级=普通野兽，E级=特种兵战力...'}
    },
    'emotion_curve': {
        'phase_1_early_domination': {
            'curve': [
                {'ch': 1, 'emotion': '紧张', 'intensity': 9, 'beat_type': '压抑_setup', 'event': '绑定系统', 'purpose': '建立压力后觉醒', 'hook': '倒计时死亡'}
            ]
        },
        'rhythm_pattern': {
            'small_climax': '3章一爽点',
            'medium_climax': '10章一中爽',
            'large_climax': '30章阶段高潮'
        }
    }
}

optimizer = ChapterPromptOptimizer(test_data)

# 测试System Prompt
system_prompt = optimizer.build_system_prompt()
print('=== System Prompt 统计 ===')
print(f'总字符数: {len(system_prompt)}')
print(f'总字节数: {len(system_prompt.encode("utf-8"))}')
print()
print('=== System Prompt 内容 ===')
print(system_prompt)
