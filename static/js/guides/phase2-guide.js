/**
 * ============================================
 * 第二阶段引导配置
 * ============================================
 * 用户首次进入第二阶段章节生成页面时显示
 */

const Phase2GuideConfig = {
    id: 'phase2_guide',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '✍️' },
            badge: '第二阶段',
            title: '章节生成',
            description: '欢迎来到第二阶段！现在，AI 将根据<strong>第一阶段生成的设定</strong>，开始创作具体的章节内容。',
            features: [
                {
                    icon: '📖',
                    title: '基于设定创作',
                    description: '严格遵循第一阶段的世界观、角色设定'
                },
                {
                    icon: '🎭',
                    title: '人设一致性',
                    description: '确保角色言行符合设定，避免人设崩塌'
                },
                {
                    icon: '🔍',
                    title: '伏笔回收',
                    description: '自动埋设伏笔并在后续章节回收'
                }
            ],
            tip: {
                icon: '💡',
                title: '为什么第二阶段如此顺畅？',
                content: '因为所有设定已经在第一阶段确定好了，AI 不需要"临时发挥"，只需要按照蓝图执行即可。'
            }
        },
        {
            layout: 'image-right',
            visual: { type: 'emoji', content: '🎛️' },
            badge: '生成模式',
            title: '选择生成模式',
            description: '我们提供两种章节生成方式，适应不同需求：',
            features: [
                {
                    icon: '⚡',
                    title: '批量生成模式',
                    description: '快速生成大量章节，适合网文连载。每章约 2000-3000 字，节奏快，爽点密集。'
                },
                {
                    icon: '✨',
                    title: '精修模式',
                    description: '逐章生成，每章更详细（3000-5000 字），可人工干预调整后再继续。'
                }
            ],
            example: {
                title: '如何选择？',
                content: '如果你是网文作者追求日更多章，选批量模式；如果你想要精品质量、每章精雕细琢，选精修模式。'
            }
        },
        {
            layout: 'image-left',
            visual: { type: 'emoji', content: '📊' },
            badge: '进度管理',
            title: '实时查看生成进度',
            description: '章节生成过程中，你可以：',
            features: [
                {
                    icon: '👁️',
                    title: '实时预览',
                    description: '刚生成的章节立即可以阅读'
                },
                {
                    icon: '🔄',
                    title: '重新生成',
                    description: '对不满意的章节可以要求重写'
                },
                {
                    icon: '✏️',
                    title: '人工编辑',
                    description: '在线修改后保存继续生成'
                },
                {
                    icon: '⏸️',
                    title: '暂停/继续',
                    description: '随时中断，保留进度下次继续'
                }
            ]
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎉' },
            badge: '完成创作',
            title: '导出与发布',
            description: '所有章节生成完成后，你可以：',
            features: [
                {
                    icon: '💾',
                    title: '导出文档',
                    description: '导出为 Word、TXT 等格式'
                },
                {
                    icon: '📤',
                    title: '一键上传',
                    description: '直接上传到番茄小说等平台'
                },
                {
                    icon: '📚',
                    title: '保存项目',
                    description: '保留完整项目，方便续写第二部'
                }
            ],
            tip: {
                icon: '🚀',
                title: '开始创作吧！',
                content: '现在你已经了解了整个流程，点击下方按钮开始生成你的第一章！'
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
