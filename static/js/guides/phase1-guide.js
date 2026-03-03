/**
 * ============================================
 * 第一阶段引导配置
 * ============================================
 * 用户首次进入第一阶段设定生成页面时显示
 */

const Phase1GuideConfig = {
    id: 'phase1_guide',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '📋' },
            badge: '第一阶段',
            title: '设定生成',
            description: '这是<strong>两阶段创作法</strong>的第一步。在这个阶段，你需要为 AI 提供故事的<strong>基础蓝图</strong>，它会帮你扩展成完整的世界观设定。',
            features: [
                {
                    icon: '🌍',
                    title: '世界观设定',
                    description: '背景故事、势力分布、规则体系'
                },
                {
                    icon: '👥',
                    title: '角色设计',
                    description: '主角、配角的性格、能力、关系'
                },
                {
                    icon: '📚',
                    title: '章节大纲',
                    description: '每章的情节要点、伏笔安排'
                }
            ],
            tip: {
                icon: '⚠️',
                title: '重要提示',
                content: '第一阶段的质量直接决定最终小说的质量。花 10 分钟写好设定，比花 1 小时修改生成结果更有效。'
            }
        },
        {
            layout: 'image-right',
            visual: { type: 'emoji', content: '⚙️' },
            badge: '核心设定',
            title: '如何写好「核心设定」？',
            description: '核心设定是整个故事的基础，建议包含以下内容：',
            features: [
                {
                    icon: '🗺️',
                    title: '世界观',
                    description: '修仙世界？现代都市？异世大陆？'
                },
                {
                    icon: '⚔️',
                    title: '力量体系',
                    description: '修炼境界、魔法系统、科技水平'
                },
                {
                    icon: '🏛️',
                    title: '势力分布',
                    description: '宗门、家族、国家等组织'
                }
            ],
            example: {
                title: '优秀示例（节选）',
                content: '「这是一个以"文气"为核心的修炼世界。读书人通过诵读经典积累文气，诗词文章可具现为真实力量。主角是偏远书院的扫地杂役，无意中获得破损的《论语》竹简...」'
            }
        },
        {
            layout: 'image-left',
            visual: { type: 'emoji', content: '✏️' },
            badge: '进阶工具',
            title: '创意编辑器',
            description: '点击表单上方的 <strong>「打开创意编辑器」</strong> 按钮，可以进入更详细的编辑界面：',
            features: [
                {
                    icon: '📝',
                    title: '详细设定编辑',
                    description: '分段编辑世界观、背景故事'
                },
                {
                    icon: '📖',
                    title: '故事线时间轴',
                    description: '规划开篇、发展、高潮、结局四个阶段'
                },
                {
                    icon: '💎',
                    title: '核心卖点管理',
                    description: '添加多个卖点标签'
                }
            ],
            tip: {
                icon: '💡',
                title: '使用建议',
                content: '如果你有详细的想法，建议用创意编辑器；如果只是初步构思，直接填写表单即可。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎯' },
            badge: '平台选择',
            title: '选择适合的目标平台',
            description: '不同平台的读者偏好不同，选择合适的平台可以优化生成风格：',
            features: [
                {
                    icon: '🍅',
                    title: '番茄小说',
                    description: '快节奏爽文，黄金三章，悬念密集'
                },
                {
                    icon: '📚',
                    title: '起点中文网',
                    description: '付费阅读导向，注重世界观和升级体系'
                },
                {
                    icon: '💡',
                    title: '知乎盐选',
                    description: '精品短篇，强情节，反转多'
                },
                {
                    icon: '🎬',
                    title: '短剧',
                    description: '极致快节奏，强冲突，情绪直接'
                }
            ]
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🚀' },
            badge: '生成设定',
            title: '开始生成',
            description: '填写完信息后，点击 <strong>「开始生成设定」</strong> 按钮。生成过程大约需要 <strong>3-5 分钟</strong>，你可以实时查看进度。',
            features: [
                {
                    icon: '📊',
                    title: '实时进度',
                    description: '查看当前正在生成哪个部分'
                },
                {
                    icon: '⏸️',
                    title: '可暂停',
                    description: '随时可以暂停，稍后继续'
                },
                {
                    icon: '✅',
                    title: '结果预览',
                    description: '生成完成后可查看、编辑所有内容'
                }
            ],
            tip: {
                icon: '🎉',
                title: '下一步',
                content: '第一阶段完成后，你可以选择「继续第二阶段」直接生成章节，或者「保存项目」稍后继续。'
            }
        }
    ],
    onComplete: () => {
        console.log('第一阶段引导完成');
    }
};

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Phase1GuideConfig;
}
