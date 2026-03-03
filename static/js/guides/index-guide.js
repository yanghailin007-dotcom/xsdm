/**
 * ============================================
 * 首页欢迎引导配置 - 完整版
 * ============================================
 * 用户首次进入系统首页时显示 - 展示完整功能体系
 */

const IndexGuideConfig = {
    id: 'index_welcome_v2',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎉' },
            title: '欢迎来到大文娱创作系统',
            description: '这是一套专为网文作者设计的 <strong>AI 全流程创作工具</strong>。从灵感构思到平台发布，我们帮你完成小说创作的每一个环节。',
            features: [
                {
                    icon: '🤖',
                    title: 'AI 智能生成',
                    description: 'GPT-4 驱动，一键生成世界观、角色、章节，日更万字不是梦'
                },
                {
                    icon: '⚡',
                    title: '两阶段创作法',
                    description: '先规划后写作，解决 AI 生成前后矛盾、人设崩塌的行业难题'
                },
                {
                    icon: '📚',
                    title: '一站式发布',
                    description: '自动生成封面、一键上传番茄小说、签约管理，从创作到变现全流程覆盖'
                }
            ]
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '📖' },
            badge: '核心工作流',
            title: '「两阶段创作法」是什么？',
            description: '传统 AI 写作的最大痛点是<strong>写到后面忘了前面</strong>。我们的两阶段法彻底解决这个难题：',
            flowchart: {
                steps: [
                    {
                        icon: '📋',
                        title: '第一阶段',
                        description: '生成完整设定：世界观+角色+详细大纲'
                    },
                    {
                        icon: '✍️',
                        title: '第二阶段',
                        description: '基于设定逐章生成，确保逻辑自洽'
                    }
                ]
            },
            tip: {
                icon: '💡',
                title: '为什么这样更靠谱？',
                content: '就像建筑必须先画图纸再施工，小说也需要先规划再写作。第一阶段生成的详细设定会成为第二阶段的"写作圣经"，确保人物不崩、设定不乱。'
            }
        },
        {
            layout: 'image-right',
            visual: { type: 'emoji', content: '📋' },
            badge: '第一阶段',
            title: '第一阶段：设定生成',
            description: '在这一步，AI 会为你生成一套完整的<strong>小说蓝图</strong>，包括：',
            features: [
                {
                    icon: '🌍',
                    title: '世界观设定',
                    description: '背景故事、势力分布、修炼体系、社会规则等完整框架'
                },
                {
                    icon: '👥',
                    title: '角色设计',
                    description: '主角、配角、反派的详细人设、能力、关系图谱'
                },
                {
                    icon: '📚',
                    title: '详细大纲',
                    description: '每章的情节要点、伏笔安排、情感曲线、爽点分布'
                },
                {
                    icon: '🎯',
                    title: '质量评估',
                    description: 'AI 自动评估设定完整性，给出优化建议'
                }
            ],
            example: {
                title: '第一阶段产出示例',
                content: '输入："穿越到修仙世界当图书管理员" → 输出：5000字世界观设定 + 8个主要角色人设 + 200章详细大纲 + 伏笔对照表。你可以先审核修改这些设定，满意后再进入第二阶段。'
            }
        },
        {
            layout: 'image-left',
            visual: { type: 'emoji', content: '✍️' },
            badge: '第二阶段',
            title: '第二阶段：章节生成',
            description: '基于第一阶段审定的设定，AI 开始<strong>逐章创作正文</strong>：',
            features: [
                {
                    icon: '📝',
                    title: '按大纲写作',
                    description: '严格遵循第一阶段的情节规划，确保不跑题'
                },
                {
                    icon: '🎭',
                    title: '人设一致性',
                    description: '角色言行始终符合设定，不会出现"性格突变"'
                },
                {
                    icon: '🔍',
                    title: '伏笔回收',
                    description: '自动埋设伏笔并在后续章节按计划回收'
                },
                {
                    icon: '⚡',
                    title: '批量生成',
                    description: '支持一次生成 5-50 章，日更万字轻松实现'
                }
            ],
            tip: {
                icon: '✨',
                title: '生成质量保障',
                content: '第二阶段会引用第一阶段的设定作为上下文，确保不会出现"第1章说主角是孤儿，第10章突然冒出父母"这类低级错误。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🚀' },
            badge: '进阶功能',
            title: '从创作到变现的完整链路',
            description: '除了核心创作功能，我们还提供一站式发布工具，<strong>让作品更快变现</strong>：',
            features: [
                {
                    icon: '🎨',
                    title: 'AI 封面生成',
                    description: '根据小说内容自动生成精美封面，支持多种风格'
                },
                {
                    icon: '🍅',
                    title: '番茄自动上传',
                    description: '一键将章节内容上传到番茄小说平台，自动分卷、定时发布'
                },
                {
                    icon: '📝',
                    title: '签约辅助',
                    description: '签约申请自动化、合同管理、收益追踪（高级会员功能）'
                },
                {
                    icon: '📊',
                    title: '数据分析',
                    description: '阅读量、收益、读者画像等数据统计（开发中）'
                }
            ],
            tip: {
                icon: '💎',
                title: '会员权益说明',
                content: '基础功能（两阶段生成）完全免费；番茄自动上传、签约辅助等高级功能需要开通会员。新用户赠送 7 天会员体验。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎯' },
            badge: '开始创作',
            title: '准备好开始了吗？',
            description: '点击首页的 <strong>「开始创作」</strong> 或 <strong>「两阶段生成」</strong> 按钮，开启你的第一部 AI 辅助小说：',
            features: [
                {
                    icon: '📝',
                    title: '只需提供创意',
                    description: '一句话描述你的想法，比如"穿越到修仙世界当图书管理员"'
                },
                {
                    icon: '⚙️',
                    title: 'AI 完成扩展',
                    description: '自动生成世界观、角色、大纲，你可以随时修改调整'
                },
                {
                    icon: '📚',
                    title: '一键生成正文',
                    description: '设定满意后，进入第二阶段批量生成章节'
                }
            ],
            example: {
                title: '创作示例',
                content: '输入：「凡人修仙传同人，主角穿越当藏书阁管理员，偷看功法书悟道」→ 第一阶段生成完整设定 → 审核修改 → 第二阶段生成 200 章正文 → 一键上传番茄小说。整个过程最快只需 1 小时！'
            }
        }
    ],
    onComplete: () => {
        console.log('首页引导完成');
    }
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = IndexGuideConfig;
}
