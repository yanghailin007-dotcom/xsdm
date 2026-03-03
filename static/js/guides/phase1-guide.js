/**
 * ============================================
 * 第一阶段引导配置 - 完整版
 * ============================================
 * 用户首次进入第一阶段设定生成页面时显示
 */

const Phase1GuideConfig = {
    id: 'phase1_guide_v2',
    steps: [
        {
            layout: 'center',
            visual: { type: 'emoji', content: '📋' },
            badge: '第一阶段',
            title: '欢迎来到设定生成',
            description: '这是<strong>两阶段创作法</strong>的核心第一步。在这个阶段，你需要为 AI 提供故事的<strong>基础蓝图</strong>，它会帮你扩展成完整的世界观设定。',
            features: [
                {
                    icon: '🌍',
                    title: '生成世界观',
                    description: '背景故事、势力分布、修炼体系、社会规则'
                },
                {
                    icon: '👥',
                    title: '设计角色',
                    description: '主角、配角、反派的详细人设和能力'
                },
                {
                    icon: '📚',
                    title: '规划大纲',
                    description: '每章的情节要点、伏笔、爽点分布'
                },
                {
                    icon: '✅',
                    title: '质量检查',
                    description: 'AI 自动评估设定完整性和合理性'
                }
            ],
            tip: {
                icon: '⚠️',
                title: '重要提示',
                content: '第一阶段的质量直接决定最终小说的质量。花 10 分钟写好设定，比花 1 小时修改生成结果更有效。宁可在设定阶段多花时间，也不要带着问题进入第二阶段。'
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
                    description: '修仙世界？现代都市？异世大陆？赛博朋克？'
                },
                {
                    icon: '⚔️',
                    title: '力量体系',
                    description: '修炼境界、魔法系统、科技水平、特殊能力'
                },
                {
                    icon: '🏛️',
                    title: '势力分布',
                    description: '宗门、家族、国家、组织等各方势力'
                },
                {
                    icon: '📜',
                    title: '核心规则',
                    description: '世界运行的基本法则、限制条件、禁忌'
                }
            ],
            example: {
                title: '优秀示例（节选）',
                content: '「这是一个以"文气"为核心的修炼世界。读书人通过诵读经典积累文气，诗词文章可具现为真实力量。文气分九品，从童生到圣人。主角是偏远书院的扫地杂役，无意中获得破损的《论语》竹简，发现里面记载着失传的"春秋笔法"...」'
            }
        },
        {
            layout: 'image-left',
            visual: { type: 'emoji', content: '✏️' },
            badge: '进阶工具',
            title: '创意编辑器：精细化设定工具',
            description: '点击表单上方的 <strong>「打开创意编辑器」</strong> 按钮，进入专业级设定编辑界面：',
            features: [
                {
                    icon: '📝',
                    title: '分段设定编辑',
                    description: '世界观、背景故事、核心规则分开编辑，更清晰'
                },
                {
                    icon: '📖',
                    title: '故事线时间轴',
                    description: '规划开篇、发展、高潮、结局四个阶段的具体内容'
                },
                {
                    icon: '💎',
                    title: '核心卖点管理',
                    description: '添加多个卖点标签，AI 会在生成时重点强化'
                },
                {
                    icon: '👤',
                    title: '角色编辑器',
                    description: '详细设定每个角色的外貌、性格、能力、关系'
                }
            ],
            tip: {
                icon: '💡',
                title: '使用建议',
                content: '如果你有详细的想法，建议用创意编辑器；如果只是初步构思，直接填写表单即可。创意编辑器的内容会自动同步回主表单。'
            }
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎯' },
            badge: '平台选择',
            title: '选择适合的目标平台',
            description: '不同平台的读者偏好不同，选择合适的平台会显著优化生成风格和质量：',
            features: [
                {
                    icon: '🍅',
                    title: '番茄小说',
                    description: '快节奏爽文，黄金三章抓眼球，悬念密集，日更压力大'
                },
                {
                    icon: '📚',
                    title: '起点中文网',
                    description: '付费阅读导向，注重世界观完整性和升级体系合理性'
                },
                {
                    icon: '💡',
                    title: '知乎盐选',
                    description: '精品短篇，强情节推进，反转多，开头即高潮'
                },
                {
                    icon: '🎬',
                    title: '短剧剧本',
                    description: '极致快节奏，强冲突，情绪直接，适合改编拍摄'
                }
            ],
            tip: {
                icon: '📊',
                title: '平台差异示例',
                content: '同样的"退婚流"题材：番茄版会在第1章就完成退婚+打脸；起点版可能用3章铺垫背景；知乎版会加入更多心理描写和反转。'
            }
        },
        {
            layout: 'image-right',
            visual: { type: 'emoji', content: '🚀' },
            badge: '生成流程',
            title: '开始生成设定',
            description: '填写完信息后，点击 <strong>「开始生成设定」</strong> 按钮。整个生成过程大约需要 <strong>3-5 分钟</strong>，你会看到实时进度：',
            features: [
                {
                    icon: '📊',
                    title: '实时进度追踪',
                    description: '规划 → 世界观 → 角色 → 大纲 → 验证，每一步都有进度显示'
                },
                {
                    icon: '⏸️',
                    title: '可随时暂停',
                    description: '有事可以暂停，保存进度，稍后回来继续'
                },
                {
                    icon: '👁️',
                    title: '分段预览',
                    description: '每完成一部分就可以预览，不满意可以中断重来'
                }
            ]
        },
        {
            layout: 'center',
            visual: { type: 'emoji', content: '🎉' },
            badge: '后续操作',
            title: '第一阶段完成后做什么？',
            description: '设定生成完成后，你可以查看、编辑所有生成内容，然后决定下一步：',
            features: [
                {
                    icon: '➡️',
                    title: '继续第二阶段',
                    description: '直接开始生成章节正文（推荐）'
                },
                {
                    icon: '💾',
                    title: '保存项目',
                    description: '保存当前进度，稍后继续或明天再写'
                },
                {
                    icon: '🔄',
                    title: '重新生成',
                    description: '调整参数后重新生成设定'
                },
                {
                    icon: '✏️',
                    title: '编辑设定',
                    description: '在页面上直接修改不满意的部分'
                }
            ],
            tip: {
                icon: '🎯',
                title: '最佳实践建议',
                content: '建议先花 5-10 分钟阅读生成的设定，检查是否有逻辑漏洞或与你的预期不符的地方。修改满意后再进入第二阶段，这样最终小说的质量会高很多。'
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
