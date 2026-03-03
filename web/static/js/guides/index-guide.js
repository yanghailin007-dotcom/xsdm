/**
 * ============================================
 * 首页欢迎引导配置
 * ============================================
 * 用户首次进入系统首页时显示
 */

const IndexGuideConfig = {
    id: 'index_welcome',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎉' },
            title: '欢迎来到大文娱系统',
            description: '这是一个专为小说创作者设计的 <strong>AI 辅助创作平台</strong>。无论你是想快速生成网文，还是寻找创作灵感，这里都能帮到你。',
            features: [
                {
                    icon: '🤖',
                    title: 'AI 智能生成',
                    description: '基于 GPT-4 等大模型，自动生成世界观、角色、章节内容'
                },
                {
                    icon: '⚡',
                    title: '两阶段创作法',
                    description: '先规划后写作，确保故事结构完整、逻辑自洽'
                },
                {
                    icon: '📚',
                    title: '多平台适配',
                    description: '针对番茄、起点、知乎等不同平台优化生成风格'
                }
            ]
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '📖' },
            badge: '核心概念',
            title: '什么是「两阶段创作法」？',
            description: '传统 AI 生成小说常常出现前后矛盾、人设崩塌的问题。我们的解决方案是：',
            flowchart: {
                steps: [
                    {
                        icon: '📋',
                        title: '第一阶段',
                        description: '生成完整设定：世界观、角色、大纲'
                    },
                    {
                        icon: '✍️',
                        title: '第二阶段',
                        description: '基于设定生成具体章节内容'
                    }
                ]
            },
            tip: {
                icon: '💡',
                title: '为什么这样更好？',
                content: '就像建筑需要先画图纸再施工，小说创作也需要先规划再写作。这样可以避免写到一半发现设定冲突的尴尬。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🚀' },
            badge: '开始创作',
            title: '准备好开始了吗？',
            description: '点击首页的 <strong>「开始创作」</strong> 按钮，进入第一阶段设定生成。你只需要提供：',
            features: [
                {
                    icon: '📝',
                    title: '小说标题和简介',
                    description: '一句话概括你想写的故事'
                },
                {
                    icon: '⚙️',
                    title: '核心设定',
                    description: '世界观、修炼体系、主要势力等背景设定'
                },
                {
                    icon: '💎',
                    title: '核心卖点',
                    description: '你的小说最吸引读者的点是什么？'
                }
            ],
            example: {
                title: '创作示例',
                content: '比如你想写一个「穿越到修仙世界当图书管理员」的故事，只需要描述：主角穿越到修真门派当藏书阁管理员，发现书籍中隐藏着上古秘法... 系统会自动帮你扩展成完整的世界观和剧情大纲。'
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
