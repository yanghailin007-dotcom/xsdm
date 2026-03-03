/**
 * ============================================
 * 第二阶段引导配置 - 完整版
 * ============================================
 * 用户首次进入第二阶段章节生成页面时显示
 */

const Phase2GuideConfig = {
    id: 'phase2_guide_v2',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '✍️' },
            badge: '第二阶段',
            title: '欢迎来到章节生成',
            description: '恭喜你完成了第一阶段的设定！现在，AI 将根据你审定的<strong>完整设定</strong>，开始创作具体的章节内容。',
            features: [
                {
                    icon: '📖',
                    title: '严格遵循设定',
                    description: '基于第一阶段的世界观、角色、大纲进行创作'
                },
                {
                    icon: '🎭',
                    title: '人设一致性保障',
                    description: '角色言行始终符合设定，避免"性格突变"'
                },
                {
                    icon: '🔍',
                    title: '伏笔自动回收',
                    description: '按计划埋设伏笔并在后续章节回收'
                },
                {
                    icon: '⚡',
                    title: '批量生产能力',
                    description: '一次生成 5-50 章，轻松实现日更万字'
                }
            ],
            tip: {
                icon: '💡',
                title: '为什么第二阶段如此顺畅？',
                content: '因为所有设定已经在第一阶段确定好了，AI 不需要"临时发挥"，只需要按照蓝图执行即可。这就像照着图纸施工，比边想边盖可靠得多。'
            }
        },
        {
            layout: 'image-right',
            visual: { type: 'emoji', content: '🎛️' },
            badge: '生成模式',
            title: '选择适合你的生成模式',
            description: '我们提供两种章节生成方式，适应不同的创作需求：',
            features: [
                {
                    icon: '⚡',
                    title: '批量生成模式',
                    description: '适合网文连载，一次生成 5-50 章。每章 2000-3000 字，节奏快，爽点密集，适合番茄等平台。'
                },
                {
                    icon: '✨',
                    title: '精修模式',
                    description: '适合精品创作，逐章生成。每章 3000-5000 字，可人工干预调整后再继续，质量更高。'
                }
            ],
            example: {
                title: '如何选择？',
                content: '如果你是网文作者追求日更多章选批量模式；如果你想要精品质量、每章精雕细琢选精修模式。也可以先用批量模式快速出稿，再用精修模式打磨关键章节。'
            }
        },
        {
            layout: 'image-left',
            visual: { type: 'emoji', content: '📊' },
            badge: '进度管理',
            title: '实时掌控生成进度',
            description: '章节生成过程中，你可以完全掌控整个过程：',
            features: [
                {
                    icon: '👁️',
                    title: '实时预览',
                    description: '每章生成后立即可以阅读，实时查看质量'
                },
                {
                    icon: '🔄',
                    title: '单章重生成',
                    description: '对不满意的章节可以单独要求重写'
                },
                {
                    icon: '✏️',
                    title: '人工编辑',
                    description: '在线修改后保存，AI 会以修改后的版本继续后续章节'
                },
                {
                    icon: '⏸️',
                    title: '暂停/继续',
                    description: '随时中断，保留所有进度，下次从断点继续'
                }
            ],
            tip: {
                icon: '⚠️',
                title: '重要提示',
                content: '如果发现生成的章节质量下降（常见于批量生成后期），建议暂停并检查第一阶段的设定是否足够详细。必要时可以回到第一阶段补充设定。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎨' },
            badge: '增值服务',
            title: '创作完成后的增值服务',
            description: '章节生成完成后，我们还提供一系列工具帮助你<strong>更快变现</strong>：',
            features: [
                {
                    icon: '🎨',
                    title: 'AI 封面生成',
                    description: '根据小说内容自动生成精美封面，支持玄幻、都市、言情等多种风格，可直接用于平台上传'
                },
                {
                    icon: '🍅',
                    title: '番茄自动上传',
                    description: '一键将章节上传到番茄小说平台，自动分卷、格式化、定时发布（会员功能）'
                },
                {
                    icon: '📝',
                    title: '签约辅助',
                    description: '签约申请自动化、合同管理、收益追踪，帮你更快拿到平台签约（高级会员功能）'
                },
                {
                    icon: '📊',
                    title: '数据统计',
                    description: '阅读量、收藏、收益等数据统计，了解作品表现（开发中）'
                }
            ],
            tip: {
                icon: '💎',
                title: '关于会员',
                content: '基础的两阶段创作功能完全免费。番茄自动上传、签约辅助等高级功能需要开通会员。新用户自动赠送 7 天会员体验期，足够你体验完整流程。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎉' },
            badge: '开始创作',
            title: '开始生成你的第一章',
            description: '现在你已经了解了整个流程，可以开始生成章节了：',
            features: [
                {
                    icon: '1️⃣',
                    title: '选择项目',
                    description: '从左侧选择你在第一阶段创建的项目'
                },
                {
                    icon: '2️⃣',
                    title: '配置参数',
                    description: '选择生成模式、章节数量、平台风格'
                },
                {
                    icon: '3️⃣',
                    title: '点击生成',
                    description: '点击「开始生成」按钮，等待 AI 创作'
                },
                {
                    icon: '4️⃣',
                    title: '审核发布',
                    description: '检查生成的内容，满意后导出或一键上传'
                }
            ],
            tip: {
                icon: '🚀',
                title: '祝你创作顺利！',
                content: '有了 AI 的协助，你可以把更多精力放在创意构思上，让机器处理繁琐的码字工作。期待你的作品大火！'
            }
        }
    ],
    onComplete: () => {
        console.log('第二阶段引导完成');
    }
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Phase2GuideConfig;
}
