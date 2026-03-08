/**
 * 大文娱创作平台 - 国际化(i18n)系统
 * 支持中文(zh-CN)和英文(en)
 */

const I18N = {
    // 当前语言
    currentLang: 'zh-CN',
    
    // 翻译字典
    translations: {
        'zh-CN': {
            // 通用
            'app.name': '大文娱创作平台',
            'app.name.short': '大文娱',
            'app.tagline': 'AI驱动的创意写作助手',
            'loading': '加载中...',
            'save': '保存',
            'cancel': '取消',
            'confirm': '确认',
            'delete': '删除',
            'edit': '编辑',
            'create': '创建',
            'submit': '提交',
            'close': '关闭',
            'back': '返回',
            'next': '下一步',
            'prev': '上一步',
            'search': '搜索',
            'filter': '筛选',
            'sort': '排序',
            'all': '全部',
            'none': '无',
            'or': '或',
            'and': '和',
            'yes': '是',
            'no': '否',
            'ok': '确定',
            'success': '成功',
            'error': '错误',
            'warning': '警告',
            'info': '信息',
            
            // 导航
            'nav.home': '首页',
            'nav.novels': '我的小说',
            'nav.projects': '项目管理',
            'nav.tools': '工具箱',
            'nav.settings': '偏好设置',
            'nav.profile': '个人中心',
            'nav.logout': '退出登录',
            'nav.login': '登录',
            'nav.register': '注册',
            
            // 注册页面
            'register.title': '创建账号',
            'register.subtitle': '开启您的AI创作之旅',
            'register.username': '用户名',
            'register.username.placeholder': '请输入用户名（3-20个字符）',
            'register.username.hint': '用户名可用',
            'register.username.checking': '检查中...',
            'register.password': '密码',
            'register.password.placeholder': '请输入密码（至少6位）',
            'register.password.hint': '密码长度至少6位',
            'register.password.weak': '弱',
            'register.password.medium': '中',
            'register.password.strong': '强',
            'register.confirmPassword': '确认密码',
            'register.confirmPassword.placeholder': '请再次输入密码',
            'register.email': '邮箱（可选）',
            'register.email.placeholder': '请输入邮箱地址',
            'register.inviteCode': '邀请码（可选）',
            'register.inviteCode.placeholder': '有邀请码？输入可获得额外奖励',
            'register.agreement': '我同意',
            'register.terms': '用户协议',
            'register.and': '和',
            'register.privacy': '隐私政策',
            'register.submit': '创建账号',
            'register.haveAccount': '已有账号？',
            'register.login': '立即登录',
            'register.error.username.empty': '请输入用户名',
            'register.error.username.length': '用户名长度需在3-20个字符之间',
            'register.error.username.format': '用户名只能包含字母、数字和下划线',
            'register.error.username.taken': '该用户名已被注册',
            'register.error.password.empty': '请输入密码',
            'register.error.password.length': '密码长度至少为6位',
            'register.error.password.mismatch': '两次输入的密码不一致',
            'register.error.email.invalid': '邮箱格式不正确',
            'register.error.terms': '请同意用户协议和隐私政策',
            'register.success': '注册成功！正在跳转...',
            'register.error.generic': '注册失败，请稍后重试',
            
            // 登录页面
            'login.title': '欢迎回来',
            'login.subtitle': '登录以继续您的创作',
            'login.username': '用户名',
            'login.username.placeholder': '请输入用户名',
            'login.password': '密码',
            'login.password.placeholder': '请输入密码',
            'login.remember': '记住我',
            'login.forgot': '忘记密码？',
            'login.submit': '登录',
            'login.noAccount': '还没有账号？',
            'login.register': '立即注册',
            'login.demoAccount': '测试账户',
            'login.error.empty': '请填写用户名和密码',
            'login.error.invalid': '用户名或密码错误',
            'login.success': '登录成功！',
            
            // 设置页面
            'settings.title': '偏好设置',
            'settings.subtitle': '自定义您的使用体验',
            'settings.saved': '设置已保存',
            
            'settings.appearance.title': '🎨 界面设置',
            'settings.darkMode': '深色模式',
            'settings.darkMode.desc': '使用深色主题保护眼睛',
            'settings.language': '语言',
            'settings.language.desc': '选择界面显示语言',
            'settings.lang.zh-CN': '简体中文',
            'settings.lang.zh-TW': '繁体中文',
            'settings.lang.en': 'English',
            
            'settings.notification.title': '🔔 通知设置',
            'settings.emailNotify': '邮件通知',
            'settings.emailNotify.desc': '接收重要更新和提醒',
            'settings.generationNotify': '生成完成提醒',
            'settings.generationNotify.desc': 'AI生成任务完成时通知我',
            
            'settings.creation.title': '✍️ 创作设置',
            'settings.autoSave': '自动保存',
            'settings.autoSave.desc': '编辑时自动保存草稿',
            'settings.defaultMode': '默认生成模式',
            'settings.defaultMode.desc': '选择章节生成的默认模式',
            'settings.mode.batch': '批量模式',
            'settings.mode.refined': '精修模式',
            
            'settings.privacy.title': '🔒 隐私设置',
            'settings.publicWorks': '公开我的作品',
            'settings.publicWorks.desc': '允许其他用户查看您的作品',
            'settings.dataShare': '数据分享',
            'settings.dataShare.desc': '贡献匿名数据帮助改进AI',
            
            'settings.advanced.title': '⚙️ 高级功能',
            'settings.experimental': '实验性功能',
            'settings.experimental.desc': '提前体验新功能',
            'settings.devMode': '开发者模式',
            'settings.devMode.desc': '显示调试信息和API日志',
            'settings.comingSoon': '即将上线',
            
            // 导航
            'nav.home': '首页',
            'nav.features': '功能',
            'nav.create': '新建创作',
            'nav.workspace': '工作台',
            'nav.projects': '项目',
            'nav.works': '作品',
            'nav.login': '登录',
            'nav.getStarted': '开始使用',
            'nav.logout': '退出',
            'nav.settings': '设置',
            
            // 页脚
            'footer.help': '帮助中心',
            'footer.terms': '使用条款',
            'footer.privacy': '隐私政策',
            'footer.contact': '联系我们',
            'footer.copyright': '© 2024 大文娱系统 - AI 创作平台',
            
            // Help 页面
            'help.title': '帮助中心',
            'help.subtitle': '了解如何使用大文娱系统的各项功能',
            'help.card.quickStart.title': '快速开始',
            'help.card.quickStart.desc': '了解如何创建您的第一个AI小说项目，从创意到成品的完整流程。',
            'help.card.guide.title': '创作指南',
            'help.card.guide.desc': '学习如何编写有效的提示词，让AI生成更符合您期望的内容。',
            'help.card.project.title': '项目管理',
            'help.card.project.desc': '掌握项目创建、编辑、续写和导出的各种操作技巧。',
            'help.card.settings.title': '系统设置',
            'help.card.settings.desc': '配置您的账户信息、修改密码和管理个人偏好设置。',
            'help.faq.title': '常见问题',
            'help.moreHelp.title': '需要更多帮助？',
            'help.moreHelp.desc': '如果您在使用过程中遇到其他问题，欢迎联系我们',
            'help.moreHelp.contact': '联系客服',
            
            // Contact 页面
            'contact.title': '联系我们',
            'contact.subtitle': '有任何问题或建议？我们期待听到您的声音',
            'contact.card.email.title': '邮件联系',
            'contact.card.email.desc': '发送邮件至 support@example.com<br>我们会在24小时内回复',
            'contact.card.online.title': '在线客服',
            'contact.card.online.desc': '工作日 9:00-18:00<br>实时为您解答问题',
            'contact.card.wechat.title': '微信公众号',
            'contact.card.wechat.desc': '关注我们的公众号<br>获取最新动态和教程',
            'contact.form.title': '发送消息',
            'contact.form.desc': '填写以下表单，我们会尽快与您联系',
            'contact.form.name': '您的姓名',
            'contact.form.name.placeholder': '请输入您的姓名',
            'contact.form.email': '邮箱地址',
            'contact.form.email.placeholder': '请输入您的邮箱',
            'contact.form.subject': '主题',
            'contact.form.subject.placeholder': '请输入消息主题',
            'contact.form.message': '消息内容',
            'contact.form.message.placeholder': '请详细描述您的问题或建议...',
            'contact.form.submit': '发送消息',
            'contact.form.success': '感谢您的留言！我们会尽快与您联系。',
            'contact.social.title': '关注我们的社交媒体',
            
            // Privacy 页面
            'privacy.title': '隐私政策',
            'privacy.subtitle': '我们重视您的隐私，请了解我们如何收集、使用和保护您的信息',
            'privacy.lastUpdated': '最后更新日期：2026年3月5日',
            
            // Terms 页面
            'terms.title': '使用条款',
            'terms.subtitle': '请仔细阅读以下条款，使用本服务即表示您同意这些条款',
            'terms.lastUpdated': '最后更新日期：2026年3月5日',
            
            // Recharge 页面
            'recharge.title': '充值中心',
            'recharge.subtitle': '充值点数，解锁更多创作功能',
            'recharge.currentBalance': '当前余额',
            'recharge.points': '点',
            'recharge.totalEarned': '累计获得:',
            'recharge.totalSpent': '累计消费:',
            'recharge.instructions.title': '充值说明',
            'recharge.recentOrders': '最近充值',
            'recharge.selectAmount': '选择充值金额',
            'recharge.customAmount': '自定义金额',
            'recharge.customAmount.placeholder': '输入金额（0.01-5000）',
            'recharge.rechargeNow': '立即充值',
            'recharge.payMethod': '支付方式',
            'recharge.alipay': '支付宝',
            'recharge.recommended': '推荐',
            'recharge.orderId': '订单号:',
            'recharge.modal.title': '支付宝扫码支付',
            'recharge.modal.orderAmount': '订单金额:',
            'recharge.modal.completed': '已完成支付',
            
            // Payment Success 页面
            'paymentSuccess.title': '支付成功！',
            'paymentSuccess.message': '您的点数已到账，可以开始创作了',
            'paymentSuccess.orderId': '订单号',
            'paymentSuccess.amount': '支付金额',
            'paymentSuccess.points': '获得点数',
            'paymentSuccess.balance': '当前余额',
            'paymentSuccess.continue': '继续充值',
            'paymentSuccess.backHome': '返回首页',
            
            // Landing 页面
            'landing.title': '大文娱系统 - AI 创作平台',
            'landing.subtitle': '用 AI 将创意变成作品',
            'landing.description': '小说 · 视频 · 动漫 · 一站式创作体验',
            'landing.description.full': '大文娱系统提供全流程 AI 辅助创作工具，从创意构思到成品输出，让创作变得简单高效',
            'landing.cta.start': '🚀 开始创作',
            'landing.cta.learnMore': '📖 了解更多',
            'landing.stats.tools': '创作工具',
            'landing.stats.ai': '全流程辅助',
            'landing.stats.platform': '一站式平台',
            'landing.quickStart': '快速开始',
            'landing.chooseEntry': '选择创作入口',
            'landing.novel.title': '小说创作',
            'landing.novel.desc': 'AI 驱动的智能小说生成系统',
            'landing.novel.features': '两阶段生成 · 智能世界观',
            'landing.novel.enter': '进入 →',
            'landing.video.title': '视频制作',
            'landing.video.desc': '多模式视频生成系统',
            'landing.video.features': '多模式生成 · 自动剪辑',
            'landing.video.enter': '进入 →',
            'landing.features.title': '核心特性',
            'landing.features.why': '为什么选择大文娱',
            'landing.feature.efficient': '高效创作',
            'landing.feature.precise': '精准生成',
            'landing.feature.secure': '数据安全',
            'landing.feature.updated': '持续更新',
            
            // 首页
            'home.welcome': '欢迎回来',
            'home.createNew': '创建新作品',
            'home.continue': '继续创作',
            'home.recentWorks': '最近作品',
            'home.viewAll': '查看全部',
            
            // 小说创作
            'novel.create.title': '创建新小说',
            'novel.title': '小说标题',
            'novel.title.placeholder': '请输入小说标题',
            'novel.category': '分类',
            'novel.tags': '标签',
            'novel.synopsis': '简介',
            'novel.synopsis.placeholder': '简要描述您的小说内容...',
            
            // 生成相关
            'gen.start': '开始生成',
            'gen.stop': '停止生成',
            'gen.regenerate': '重新生成',
            'gen.download': '下载',
            'gen.preview': '预览',
            'gen.progress': '生成进度',
            'gen.status.waiting': '等待中',
            'gen.status.processing': '处理中',
            'gen.status.completed': '已完成',
            'gen.status.failed': '失败',
            
            // Phase 1 页面
            'phase1.badge': '第一阶段设定生成',
            'phase1.title': '两阶段小说生成',
            'phase1.subtitle': '生成完整的世界观设定、角色设计和故事大纲',
            'phase1.form.title': '创意输入与配置',
            'phase1.guide.title': '使用说明',
            'phase1.guide.goal.title': '🎯 第一阶段目标',
            'phase1.guide.goal.desc': '生成完整的世界观设定、角色设计和详细的故事大纲，为后续章节内容生成提供高质量的基础框架。',
            'phase1.guide.content.title': '⚙️ 生成内容',
            'phase1.guide.content.desc': '• 世界观设定和背景故事<br>• 主要角色设计和性格特征<br>• 故事发展阶段规划<br>• 详细章节大纲<br>• 情感线索和伏笔安排',
            'phase1.guide.bestPractice.title': '💡 最佳实践',
            'phase1.guide.bestPractice.desc': '• 核心设定描述尽量详细（建议300字以上）<br>• 明确故事的主要卖点和特色<br>• 合理规划章节数量（建议20-100章）<br>• 可以先仅生成设定，审核后再继续生成章节',
            'phase1.guide.nextSteps.title': '🔄 后续操作',
            'phase1.guide.nextSteps.desc': '第一阶段完成后，您可以：<br>• 立即继续第二阶段章节生成<br>• 保存项目，稍后继续<br>• 查看和编辑生成的设定<br>• 调整生成参数后重新生成',
            
            // Dashboard 页面
            'dashboard.title': '📊 创作仪表板',
            'dashboard.subtitle': '查看你的创作数据统计和分析',
            'dashboard.stat.chapters': '生成章节数',
            'dashboard.stat.thisSession': '↑ 本次生成',
            'dashboard.stat.words': '总字数',
            'dashboard.stat.avgScore': '平均质量分',
            'dashboard.stat.progress': '生成进度',
            'dashboard.detail.chapters': '章节详情',
            'dashboard.detail.scoreDist': '质量分数分布',
            'dashboard.table.chapter': '章节',
            'dashboard.table.title': '标题',
            'dashboard.table.words': '字数',
            'dashboard.table.score': '质量分',
            'dashboard.table.status': '状态',
            'dashboard.table.action': '操作',
            
            // 项目管理页面
            'projectMgmt.badge': '项目管理中心',
            'projectMgmt.title': '管理您的小说项目',
            'projectMgmt.subtitle': '统一管理两阶段生成的小说项目，查看进度和进行后续操作',
            'projectMgmt.stat.totalProjects': '总项目数',
            'projectMgmt.stat.completed': '已完成',
            'projectMgmt.stat.inProgress': '进行中',
            'projectMgmt.stat.totalChapters': '总章节数',
            'projectMgmt.searchPlaceholder': '搜索项目...',
            
            // 作品页面 (novels)
            'novels.title': '📚 我的创作作品',
            'novels.subtitle': '管理和浏览您所有的AI小说创作项目',
            'novels.stat.projects': '创作项目',
            'novels.stat.chapters': '总章节数',
            'novels.stat.words': '总字数',
            'novels.stat.completed': '已完成',
            'novels.filters.title': '筛选和搜索',
            'novels.view.grid': '网格',
            'novels.view.list': '列表',
            'novels.searchPlaceholder': '搜索小说标题、简介或设定...',
            'novels.filter.all': '全部',
            'novels.filter.completed': '已完成',
            'novels.filter.generating': '生成中',
            'novels.filter.paused': '已暂停',
            'novels.empty.title': '还没有创作作品',
            'novels.empty.desc': '开始您的第一个AI小说创作之旅吧！点击上方"新建创作"按钮开始。',
            'novels.empty.start': '开始创作',
            
            // 工作台 (index-v2)
            'workspace.welcome': '欢迎回来，{{username}}',
            'workspace.title': '开始你的创作之旅',
            'workspace.subtitle': '选择一个工具，让 AI 助你实现创意',
            'workspace.stat.projects': '创作项目',
            'workspace.stat.chapters': '生成章节',
            'workspace.stat.points': '创造点',
            'workspace.quickActions.label': 'Quick Actions',
            'workspace.quickActions.title': '快速开始',
            'workspace.card.twoPhase.title': '两阶段生成',
            'workspace.card.twoPhase.desc': '从设定到内容，AI 全流程辅助创作。先生成世界观设定，再批量生成章节。',
            'workspace.card.twoPhase.tag': '智能设定 · 批量生成',
            'workspace.card.projectMgmt.title': '项目管理',
            'workspace.card.projectMgmt.desc': '管理所有小说项目，查看进度、继续生成、导出作品。支持多项目并行管理。',
            'workspace.card.projectMgmt.tag': '查看进度 · 继续创作',
            'workspace.card.creativeLib.title': '创意库',
            'workspace.card.creativeLib.desc': '从预设创意中选择灵感，快速启动创作。多种题材模板任你选择。',
            'workspace.card.creativeLib.tag': '12 个创意模板',
            'workspace.card.viewWorks.title': '查看作品',
            'workspace.card.viewWorks.desc': '浏览和管理已创作的小说章节，支持在线阅读、编辑和导出。',
            'workspace.card.viewWorks.tag': '在线阅读 · 编辑导出',
            'workspace.card.start': '开始 →',
            'workspace.card.enter': '进入 →',
            'workspace.card.browse': '浏览 →',
            'workspace.card.view': '查看 →',
            
            // 账户页面
            'account.title': '账户设置',
            'account.subtitle': '管理你的账户信息和安全设置',
            'account.basicInfo.title': '基本信息',
            'account.basicInfo.username': '用户名',
            'account.basicInfo.userId': '用户ID',
            'account.basicInfo.status': '账户状态',
            'account.changePassword.title': '修改密码',
            'account.changePassword.current': '当前密码',
            'account.changePassword.currentPlaceholder': '请输入当前密码',
            'account.changePassword.new': '新密码',
            'account.changePassword.newPlaceholder': '请输入新密码（至少6个字符）',
            'account.changePassword.confirm': '确认新密码',
            'account.changePassword.confirmPlaceholder': '请再次输入新密码',
            'account.changePassword.btn': '修改密码',
            'account.dangerZone.title': '危险区域',
            'account.dangerZone.logout.title': '退出登录',
            'account.dangerZone.logout.desc': '退出当前账户并返回登录页',
            
            // 小说详情页
            'novel.settings': '设置',
            'novel.export': '导出',
            'novel.print': '打印',
            'novel.backToList': '返回列表',
            'novel.readingSettings.title': '阅读设置',
            'novel.readingSettings.fontSize': '字体大小：',
            'novel.readingSettings.theme': '背景主题：',
            'novel.readingSettings.lineHeight': '行间距：',
            'novel.theme.light': '白天',
            'novel.theme.sepia': '护眼',
            'novel.theme.dark': '夜间',
            'novel.lineHeight.compact': '紧密',
            'novel.lineHeight.loose': '宽松',
            'novel.sidebar.info': '小说信息',
            'novel.sidebar.title': '标题',
            'novel.sidebar.progress': '进度',
            'novel.sidebar.status': '状态',
            'novel.sidebar.coreSetting': '核心设定',
            'novel.sidebar.sellingPoints': '卖点',
            'novel.sidebar.chapterNav': '章节导航',
            'novel.selectChapter': '选择章节阅读',
            'novel.selectChapterHint': '点击左侧章节列表选择要查看的章节',
            'novel.selectChapterPrompt': '请从左侧选择章节开始阅读',
            
            // 通用
            'common.loading': '加载中...',
            'common.loadingProjects': '加载项目中...',
            'common.save': '保存',
            'common.cancel': '取消',
            'common.confirm': '确认',
            'common.delete': '删除',
            'common.edit': '编辑',
            'common.create': '创建',
            'common.refresh': '刷新',
            'common.newProject': '新建项目',
            
            // 步骤名称
            'step.creative_refinement': '创意精炼',
            'step.fanfiction_detection': '同人检测',
            'step.multiple_plans': '方案生成',
            'step.freshness_assessment': '新颖度评估',
            'step.plan_selection': '方案选择',
            'step.writing_style': '写作风格制定',
            'step.market_analysis': '市场分析',
            'step.worldview': '世界观构建',
            'step.faction_system': '势力系统设计',
            'step.character_design': '角色设计',
            'step.emotional_blueprint': '情绪蓝图规划',
            'step.growth_plan': '成长规划',
            'step.stage_plan': '阶段计划',
            'step.detailed_stage_plans': '详细阶段计划',
            'step.expectation_mapping': '期待感映射',
            'step.system_init': '系统初始化',
            'step.saving': '保存结果',
            'step.quality_assessment': '质量评估',
        },
        
        'zh-TW': {
            // 通用
            'app.name': '大文娛創作平台',
            'app.name.short': '大文娛',
            'app.tagline': 'AI驅動的創意寫作助手',
            'loading': '載入中...',
            'save': '儲存',
            'cancel': '取消',
            'confirm': '確認',
            'delete': '刪除',
            'edit': '編輯',
            'create': '建立',
            'submit': '送出',
            'close': '關閉',
            'back': '返回',
            'next': '下一步',
            'prev': '上一步',
            'search': '搜尋',
            'filter': '篩選',
            'sort': '排序',
            'all': '全部',
            'none': '無',
            'or': '或',
            'and': '和',
            'yes': '是',
            'no': '否',
            'ok': '確定',
            'success': '成功',
            'error': '錯誤',
            'warning': '警告',
            'info': '資訊',
            
            // 導航
            'nav.home': '首頁',
            'nav.novels': '我的小說',
            'nav.projects': '專案管理',
            'nav.tools': '工具箱',
            'nav.settings': '偏好設定',
            'nav.profile': '個人中心',
            'nav.logout': '登出',
            'nav.login': '登入',
            'nav.register': '註冊',
            
            // 註冊頁面
            'register.title': '建立帳號',
            'register.subtitle': '開啟您的AI創作之旅',
            'register.username': '使用者名稱',
            'register.username.placeholder': '請輸入使用者名稱（3-20個字元）',
            'register.username.hint': '使用者名稱可用',
            'register.username.checking': '檢查中...',
            'register.password': '密碼',
            'register.password.placeholder': '請輸入密碼（至少6位）',
            'register.password.hint': '密碼長度至少6位',
            'register.password.weak': '弱',
            'register.password.medium': '中',
            'register.password.strong': '強',
            'register.confirmPassword': '確認密碼',
            'register.confirmPassword.placeholder': '請再次輸入密碼',
            'register.email': '電子郵件（選填）',
            'register.email.placeholder': '請輸入電子郵件地址',
            'register.inviteCode': '邀請碼（選填）',
            'register.inviteCode.placeholder': '有邀請碼？輸入可獲得額外獎勵',
            'register.agreement': '我同意',
            'register.terms': '使用者協議',
            'register.and': '和',
            'register.privacy': '隱私政策',
            'register.submit': '建立帳號',
            'register.haveAccount': '已有帳號？',
            'register.login': '立即登入',
            'register.error.username.empty': '請輸入使用者名稱',
            'register.error.username.length': '使用者名稱長度需在3-20個字元之間',
            'register.error.username.format': '使用者名稱只能包含字母、數字和底線',
            'register.error.username.taken': '該使用者名稱已被註冊',
            'register.error.password.empty': '請輸入密碼',
            'register.error.password.length': '密碼長度至少為6位',
            'register.error.password.mismatch': '兩次輸入的密碼不一致',
            'register.error.email.invalid': '電子郵件格式不正確',
            'register.error.terms': '請同意使用者協議和隱私政策',
            'register.success': '註冊成功！正在跳轉...',
            'register.error.generic': '註冊失敗，請稍後重試',
            
            // 登入頁面
            'login.title': '歡迎回來',
            'login.subtitle': '登入以繼續您的創作',
            'login.username': '使用者名稱',
            'login.username.placeholder': '請輸入使用者名稱',
            'login.password': '密碼',
            'login.password.placeholder': '請輸入密碼',
            'login.remember': '記住我',
            'login.forgot': '忘記密碼？',
            'login.submit': '登入',
            'login.noAccount': '還沒有帳號？',
            'login.register': '立即註冊',
            'login.demoAccount': '測試帳號',
            'login.error.empty': '請填寫使用者名稱和密碼',
            'login.error.invalid': '使用者名稱或密碼錯誤',
            'login.success': '登入成功！',
            
            // 設定頁面
            'settings.title': '偏好設定',
            'settings.subtitle': '自訂您的使用體驗',
            'settings.saved': '設定已儲存',
            
            'settings.appearance.title': '🎨 介面設定',
            'settings.darkMode': '深色模式',
            'settings.darkMode.desc': '使用深色主題保護眼睛',
            'settings.language': '語言',
            'settings.language.desc': '選擇介面顯示語言',
            'settings.lang.zh-CN': '簡體中文',
            'settings.lang.zh-TW': '繁體中文',
            'settings.lang.en': 'English',
            
            'settings.notification.title': '🔔 通知設定',
            'settings.emailNotify': '電子郵件通知',
            'settings.emailNotify.desc': '接收重要更新和提醒',
            'settings.generationNotify': '生成完成提醒',
            'settings.generationNotify.desc': 'AI生成任務完成時通知我',
            
            'settings.creation.title': '✍️ 創作設定',
            'settings.autoSave': '自動儲存',
            'settings.autoSave.desc': '編輯時自動儲存草稿',
            'settings.defaultMode': '預設生成模式',
            'settings.defaultMode.desc': '選擇章節生成的預設模式',
            'settings.mode.batch': '批次模式',
            'settings.mode.refined': '精修模式',
            
            'settings.privacy.title': '🔒 隱私設定',
            'settings.publicWorks': '公開我的作品',
            'settings.publicWorks.desc': '允許其他使用者查看您的作品',
            'settings.dataShare': '資料分享',
            'settings.dataShare.desc': '貢獻匿名資料幫助改進AI',
            
            'settings.advanced.title': '⚙️ 進階功能',
            'settings.experimental': '實驗性功能',
            'settings.experimental.desc': '提前體驗新功能',
            'settings.devMode': '開發者模式',
            'settings.devMode.desc': '顯示除錯資訊和API日誌',
            'settings.comingSoon': '即將上線',
            
            // 導航
            'nav.home': '首頁',
            'nav.features': '功能',
            'nav.create': '建立創作',
            'nav.workspace': '工作台',
            'nav.projects': '專案',
            'nav.works': '作品',
            'nav.login': '登入',
            'nav.getStarted': '開始使用',
            'nav.logout': '登出',
            'nav.settings': '設定',
            
            // 頁腳
            'footer.help': '幫助中心',
            'footer.terms': '使用條款',
            'footer.privacy': '隱私政策',
            'footer.contact': '聯繫我們',
            'footer.copyright': '© 2024 大文娛系統 - AI 創作平台',
            
            // Help 頁面
            'help.title': '幫助中心',
            'help.subtitle': '了解如何使用大文娛系統的各項功能',
            'help.card.quickStart.title': '快速開始',
            'help.card.quickStart.desc': '了解如何創建您的第一個AI小說項目，從創意到成品的完整流程。',
            'help.card.guide.title': '創作指南',
            'help.card.guide.desc': '學習如何編寫有效的提示詞，讓AI生成更符合您期望的內容。',
            'help.card.project.title': '項目管理',
            'help.card.project.desc': '掌握項目創建、編輯、續寫和導出的各種操作技巧。',
            'help.card.settings.title': '系統設置',
            'help.card.settings.desc': '配置您的賬戶信息、修改密碼和管理個人偏好設置。',
            'help.faq.title': '常見問題',
            'help.moreHelp.title': '需要更多幫助？',
            'help.moreHelp.desc': '如果您在使用過程中遇到其他問題，歡迎聯繫我們',
            'help.moreHelp.contact': '聯繫客服',
            
            // Contact 頁面
            'contact.title': '聯繫我們',
            'contact.subtitle': '有任何問題或建議？我們期待聽到您的聲音',
            'contact.card.email.title': '郵件聯繫',
            'contact.card.email.desc': '發送郵件至 support@example.com<br>我們會在24小時內回復',
            'contact.card.online.title': '在線客服',
            'contact.card.online.desc': '工作日 9:00-18:00<br>實時為您解答問題',
            'contact.card.wechat.title': '微信公眾號',
            'contact.card.wechat.desc': '關注我們的公眾號<br>獲取最新動態和教程',
            'contact.form.title': '發送消息',
            'contact.form.desc': '填寫以下表單，我們會盡快與您聯繫',
            'contact.form.name': '您的姓名',
            'contact.form.name.placeholder': '請輸入您的姓名',
            'contact.form.email': '郵箱地址',
            'contact.form.email.placeholder': '請輸入您的郵箱',
            'contact.form.subject': '主題',
            'contact.form.subject.placeholder': '請輸入消息主題',
            'contact.form.message': '消息內容',
            'contact.form.message.placeholder': '請詳細描述您的問題或建議...',
            'contact.form.submit': '發送消息',
            'contact.form.success': '感謝您的留言！我們會盡快與您聯繫。',
            'contact.social.title': '關注我們的社交媒體',
            
            // Privacy 頁面
            'privacy.title': '隱私政策',
            'privacy.subtitle': '我們重視您的隱私，請了解我們如何收集、使用和保護您的信息',
            'privacy.lastUpdated': '最後更新日期：2026年3月5日',
            
            // Terms 頁面
            'terms.title': '使用條款',
            'terms.subtitle': '請仔細閱讀以下條款，使用本服務即表示您同意這些條款',
            'terms.lastUpdated': '最後更新日期：2026年3月5日',
            
            // Recharge 頁面
            'recharge.title': '充值中心',
            'recharge.subtitle': '充值點數，解鎖更多創作功能',
            'recharge.currentBalance': '當前餘額',
            'recharge.points': '點',
            'recharge.totalEarned': '累計獲得:',
            'recharge.totalSpent': '累計消費:',
            'recharge.instructions.title': '充值說明',
            'recharge.recentOrders': '最近充值',
            'recharge.selectAmount': '選擇充值金額',
            'recharge.customAmount': '自定義金額',
            'recharge.customAmount.placeholder': '輸入金額（0.01-5000）',
            'recharge.rechargeNow': '立即充值',
            'recharge.payMethod': '支付方式',
            'recharge.alipay': '支付寶',
            'recharge.recommended': '推薦',
            'recharge.orderId': '訂單號:',
            'recharge.modal.title': '支付寶掃碼支付',
            'recharge.modal.orderAmount': '訂單金額:',
            'recharge.modal.completed': '已完成支付',
            
            // Payment Success 頁面
            'paymentSuccess.title': '支付成功！',
            'paymentSuccess.message': '您的點數已到賬，可以開始創作了',
            'paymentSuccess.orderId': '訂單號',
            'paymentSuccess.amount': '支付金額',
            'paymentSuccess.points': '獲得點數',
            'paymentSuccess.balance': '當前餘額',
            'paymentSuccess.continue': '繼續充值',
            'paymentSuccess.backHome': '返回首頁',
            
            // Landing 頁面
            'landing.title': '大文娛系統 - AI 創作平台',
            'landing.subtitle': '用 AI 將創意變成作品',
            'landing.description': '小說 · 視頻 · 動漫 · 一站式創作體驗',
            'landing.description.full': '大文娛系統提供全流程 AI 輔助創作工具，從創意構思到成品輸出，讓創作變得簡單高效',
            'landing.cta.start': '🚀 開始創作',
            'landing.cta.learnMore': '📖 了解更多',
            'landing.stats.tools': '創作工具',
            'landing.stats.ai': '全流程輔助',
            'landing.stats.platform': '一站式平台',
            'landing.quickStart': '快速開始',
            'landing.chooseEntry': '選擇創作入口',
            'landing.novel.title': '小說創作',
            'landing.novel.desc': 'AI 驅動的智能小說生成系統',
            'landing.novel.features': '兩階段生成 · 智能世界觀',
            'landing.novel.enter': '進入 →',
            'landing.video.title': '視頻製作',
            'landing.video.desc': '多模式視頻生成系統',
            'landing.video.features': '多模式生成 · 自動剪輯',
            'landing.video.enter': '進入 →',
            'landing.features.title': '核心特性',
            'landing.features.why': '為什麼選擇大文娛',
            'landing.feature.efficient': '高效創作',
            'landing.feature.precise': '精准生成',
            'landing.feature.secure': '數據安全',
            'landing.feature.updated': '持續更新',
            
            // 首頁
            'home.welcome': '歡迎回來',
            'home.createNew': '建立新作品',
            'home.continue': '繼續創作',
            'home.recentWorks': '最近作品',
            'home.viewAll': '查看全部',
            
            // 小說創作
            'novel.create.title': '建立新小說',
            'novel.title': '小說標題',
            'novel.title.placeholder': '請輸入小說標題',
            'novel.category': '分類',
            'novel.tags': '標籤',
            'novel.synopsis': '簡介',
            'novel.synopsis.placeholder': '簡要描述您的小說內容...',
            
            // 生成相關
            'gen.start': '開始生成',
            'gen.stop': '停止生成',
            'gen.regenerate': '重新生成',
            'gen.download': '下載',
            'gen.preview': '預覽',
            'gen.progress': '生成進度',
            'gen.status.waiting': '等待中',
            'gen.status.processing': '處理中',
            'gen.status.completed': '已完成',
            'gen.status.failed': '失敗',
            
            // Phase 1 頁面
            'phase1.badge': '第一階段設定生成',
            'phase1.title': '兩階段小說生成',
            'phase1.subtitle': '生成完整的世界觀設定、角色設計和故事大綱',
            'phase1.form.title': '創意輸入與配置',
            'phase1.guide.title': '使用說明',
            'phase1.guide.goal.title': '🎯 第一階段目標',
            'phase1.guide.goal.desc': '生成完整的世界觀設定、角色設計和詳細的故事大綱，為後續章節內容生成提供高質量的基礎框架。',
            'phase1.guide.content.title': '⚙️ 生成內容',
            'phase1.guide.content.desc': '• 世界觀設定和背景故事<br>• 主要角色設計和性格特徵<br>• 故事發展階段規劃<br>• 詳細章節大綱<br>• 情感線索和伏筆安排',
            'phase1.guide.bestPractice.title': '💡 最佳實踐',
            'phase1.guide.bestPractice.desc': '• 核心設定描述儘量詳細（建議300字以上）<br>• 明確故事的主要賣點和特色<br>• 合理規劃章節數量（建議20-100章）<br>• 可以先僅生成設定，審核後再繼續生成章節',
            'phase1.guide.nextSteps.title': '🔄 後續操作',
            'phase1.guide.nextSteps.desc': '第一階段完成後，您可以：<br>• 立即繼續第二階段章節生成<br>• 保存專案，稍後繼續<br>• 查看和編輯生成的設定<br>• 調整生成參數後重新生成',
            
            // 步驟名稱
            'step.creative_refinement': '創意精煉',
            'step.fanfiction_detection': '同人檢測',
            'step.multiple_plans': '方案生成',
            'step.freshness_assessment': '新穎度評估',
            'step.plan_selection': '方案選擇',
            'step.writing_style': '寫作風格制定',
            'step.market_analysis': '市場分析',
            'step.worldview': '世界觀建構',
            'step.faction_system': '勢力系統設計',
            'step.character_design': '角色設計',
            'step.emotional_blueprint': '情緒藍圖規劃',
            'step.growth_plan': '成長規劃',
            'step.stage_plan': '階段計劃',
            'step.detailed_stage_plans': '詳細階段計劃',
            'step.expectation_mapping': '期待感映射',
            'step.system_init': '系統初始化',
            'step.saving': '儲存結果',
            'step.quality_assessment': '品質評估',
        },
        
        'en': {
            // General
            'app.name': 'Da Wenyu Creation Platform',
            'app.name.short': 'Da Wenyu',
            'app.tagline': 'AI-Powered Creative Writing Assistant',
            'loading': 'Loading...',
            'save': 'Save',
            'cancel': 'Cancel',
            'confirm': 'Confirm',
            'delete': 'Delete',
            'edit': 'Edit',
            'create': 'Create',
            'submit': 'Submit',
            'close': 'Close',
            'back': 'Back',
            'next': 'Next',
            'prev': 'Previous',
            'search': 'Search',
            'filter': 'Filter',
            'sort': 'Sort',
            'all': 'All',
            'none': 'None',
            'or': 'or',
            'and': 'and',
            'yes': 'Yes',
            'no': 'No',
            'ok': 'OK',
            'success': 'Success',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Info',
            
            // Navigation
            'nav.home': 'Home',
            'nav.novels': 'My Novels',
            'nav.projects': 'Projects',
            'nav.tools': 'Tools',
            'nav.settings': 'Settings',
            'nav.profile': 'Profile',
            'nav.logout': 'Logout',
            'nav.login': 'Login',
            'nav.register': 'Register',
            
            // Register page
            'register.title': 'Create Account',
            'register.subtitle': 'Start Your AI Creation Journey',
            'register.username': 'Username',
            'register.username.placeholder': 'Enter username (3-20 characters)',
            'register.username.hint': 'Username available',
            'register.username.checking': 'Checking...',
            'register.password': 'Password',
            'register.password.placeholder': 'Enter password (at least 6 characters)',
            'register.password.hint': 'Password must be at least 6 characters',
            'register.password.weak': 'Weak',
            'register.password.medium': 'Medium',
            'register.password.strong': 'Strong',
            'register.confirmPassword': 'Confirm Password',
            'register.confirmPassword.placeholder': 'Enter password again',
            'register.email': 'Email (Optional)',
            'register.email.placeholder': 'Enter email address',
            'register.inviteCode': 'Invite Code (Optional)',
            'register.inviteCode.placeholder': 'Have an invite code? Enter for extra rewards',
            'register.agreement': 'I agree to the',
            'register.terms': 'Terms of Service',
            'register.and': 'and',
            'register.privacy': 'Privacy Policy',
            'register.submit': 'Create Account',
            'register.haveAccount': 'Already have an account?',
            'register.reward': 'Get 88 Creation Points FREE',
            'register.login': 'Login Now',
            'register.error.username.empty': 'Please enter username',
            'register.error.username.length': 'Username must be 3-20 characters',
            'register.error.username.format': 'Username can only contain letters, numbers and underscores',
            'register.error.username.taken': 'This username is already taken',
            'register.error.password.empty': 'Please enter password',
            'register.error.password.length': 'Password must be at least 6 characters',
            'register.error.password.mismatch': 'Passwords do not match',
            'register.error.email.invalid': 'Invalid email format',
            'register.error.terms': 'Please agree to Terms of Service and Privacy Policy',
            'register.success': 'Registration successful! Redirecting...',
            'register.error.generic': 'Registration failed, please try again later',
            
            // Login page
            'login.title': 'Welcome Back',
            'login.subtitle': 'Login to continue your creation',
            'login.username': 'Username',
            'login.username.placeholder': 'Enter username',
            'login.password': 'Password',
            'login.password.placeholder': 'Enter password',
            'login.remember': 'Remember me',
            'login.forgot': 'Forgot password?',
            'login.submit': 'Login',
            'login.noAccount': "Don't have an account?",
            'login.register': 'Register Now',
            'login.demoAccount': 'Demo Account',
            'login.error.empty': 'Please enter username and password',
            'login.error.invalid': 'Invalid username or password',
            'login.success': 'Login successful!',
            
            // Settings page
            'settings.title': 'Settings',
            'settings.subtitle': 'Customize your experience',
            'settings.saved': 'Settings saved',
            
            'settings.appearance.title': '🎨 Appearance',
            'settings.darkMode': 'Dark Mode',
            'settings.darkMode.desc': 'Use dark theme to protect your eyes',
            'settings.language': 'Language',
            'settings.language.desc': 'Choose interface language',
            'settings.lang.zh-CN': 'Simplified Chinese',
            'settings.lang.zh-TW': 'Traditional Chinese',
            'settings.lang.en': 'English',
            
            'settings.notification.title': '🔔 Notifications',
            'settings.emailNotify': 'Email Notifications',
            'settings.emailNotify.desc': 'Receive important updates and reminders',
            'settings.generationNotify': 'Generation Complete',
            'settings.generationNotify.desc': 'Notify me when AI generation is complete',
            
            'settings.creation.title': '✍️ Creation Settings',
            'settings.autoSave': 'Auto Save',
            'settings.autoSave.desc': 'Automatically save drafts while editing',
            'settings.defaultMode': 'Default Generation Mode',
            'settings.defaultMode.desc': 'Choose default mode for chapter generation',
            'settings.mode.batch': 'Batch Mode',
            'settings.mode.refined': 'Refined Mode',
            
            'settings.privacy.title': '🔒 Privacy',
            'settings.publicWorks': 'Public Works',
            'settings.publicWorks.desc': 'Allow other users to view your works',
            'settings.dataShare': 'Data Sharing',
            'settings.dataShare.desc': 'Contribute anonymous data to improve AI',
            
            'settings.advanced.title': '⚙️ Advanced',
            'settings.experimental': 'Experimental Features',
            'settings.experimental.desc': 'Experience new features early',
            'settings.devMode': 'Developer Mode',
            'settings.devMode.desc': 'Show debug info and API logs',
            'settings.comingSoon': 'Coming Soon',
            
            // Navigation
            'nav.home': 'Home',
            'nav.features': 'Features',
            'nav.create': 'Create',
            'nav.workspace': 'Workspace',
            'nav.projects': 'Projects',
            'nav.works': 'Works',
            'nav.login': 'Login',
            'nav.getStarted': 'Get Started',
            'nav.logout': 'Logout',
            'nav.settings': 'Settings',
            
            // Footer
            'footer.help': 'Help Center',
            'footer.terms': 'Terms of Use',
            'footer.privacy': 'Privacy Policy',
            'footer.contact': 'Contact Us',
            'footer.copyright': '© 2024 Da Wenyu - AI Creation Platform',
            
            // Help page
            'help.title': 'Help Center',
            'help.subtitle': 'Learn how to use Da Wenyu features',
            'help.card.quickStart.title': 'Quick Start',
            'help.card.quickStart.desc': 'Learn how to create your first AI novel project, from idea to finished work.',
            'help.card.guide.title': 'Creation Guide',
            'help.card.guide.desc': 'Learn how to write effective prompts for AI-generated content.',
            'help.card.project.title': 'Project Management',
            'help.card.project.desc': 'Master project creation, editing, continuation, and export.',
            'help.card.settings.title': 'System Settings',
            'help.card.settings.desc': 'Configure account info, change password, and manage preferences.',
            'help.faq.title': 'FAQ',
            'help.moreHelp.title': 'Need More Help?',
            'help.moreHelp.desc': 'Contact us if you have other questions',
            'help.moreHelp.contact': 'Contact Support',
            
            // Contact page
            'contact.title': 'Contact Us',
            'contact.subtitle': 'Have questions or suggestions? We\'d love to hear from you',
            'contact.card.email.title': 'Email',
            'contact.card.email.desc': 'Send to support@example.com<br>We reply within 24 hours',
            'contact.card.online.title': 'Live Chat',
            'contact.card.online.desc': 'Weekdays 9:00-18:00<br>Real-time support',
            'contact.card.wechat.title': 'WeChat',
            'contact.card.wechat.desc': 'Follow our account<br>for updates and tutorials',
            'contact.form.title': 'Send Message',
            'contact.form.desc': 'Fill out the form and we\'ll get back to you soon',
            'contact.form.name': 'Your Name',
            'contact.form.name.placeholder': 'Enter your name',
            'contact.form.email': 'Email Address',
            'contact.form.email.placeholder': 'Enter your email',
            'contact.form.subject': 'Subject',
            'contact.form.subject.placeholder': 'Enter message subject',
            'contact.form.message': 'Message',
            'contact.form.message.placeholder': 'Describe your question or suggestion...',
            'contact.form.submit': 'Send Message',
            'contact.form.success': 'Thank you for your message! We\'ll get back to you soon.',
            'contact.social.title': 'Follow Us',
            
            // Privacy page
            'privacy.title': 'Privacy Policy',
            'privacy.subtitle': 'We value your privacy. Learn how we collect, use and protect your information',
            'privacy.lastUpdated': 'Last updated: March 5, 2026',
            
            // Terms page
            'terms.title': 'Terms of Use',
            'terms.subtitle': 'Please read these terms carefully. Using this service means you agree to them',
            'terms.lastUpdated': 'Last updated: March 5, 2026',
            
            // Recharge page
            'recharge.title': 'Recharge Center',
            'recharge.subtitle': 'Recharge points to unlock more features',
            'recharge.currentBalance': 'Current Balance',
            'recharge.points': 'Points',
            'recharge.totalEarned': 'Total Earned:',
            'recharge.totalSpent': 'Total Spent:',
            'recharge.instructions.title': 'Instructions',
            'recharge.recentOrders': 'Recent Orders',
            'recharge.selectAmount': 'Select Amount',
            'recharge.customAmount': 'Custom Amount',
            'recharge.customAmount.placeholder': 'Enter amount (0.01-5000)',
            'recharge.rechargeNow': 'Recharge Now',
            'recharge.payMethod': 'Payment Method',
            'recharge.alipay': 'Alipay',
            'recharge.recommended': 'Recommended',
            'recharge.orderId': 'Order ID:',
            'recharge.modal.title': 'Alipay QR Payment',
            'recharge.modal.orderAmount': 'Amount:',
            'recharge.modal.completed': 'Payment Completed',
            
            // Payment Success page
            'paymentSuccess.title': 'Payment Successful!',
            'paymentSuccess.message': 'Your points have been added. Start creating now!',
            'paymentSuccess.orderId': 'Order ID',
            'paymentSuccess.amount': 'Amount',
            'paymentSuccess.points': 'Points Received',
            'paymentSuccess.balance': 'Current Balance',
            'paymentSuccess.continue': 'Continue Recharging',
            'paymentSuccess.backHome': 'Back to Home',
            
            // Landing page
            'landing.title': 'Da Wenyu - AI Creation Platform',
            'landing.subtitle': 'Turn ideas into works with AI',
            'landing.description': 'Novels · Videos · Anime · One-stop creation experience',
            'landing.description.full': 'Da Wenyu provides full-process AI-assisted creation tools, from idea to finished product, making creation simple and efficient',
            'landing.cta.start': '🚀 Start Creating',
            'landing.cta.learnMore': '📖 Learn More',
            'landing.stats.tools': 'Creation Tools',
            'landing.stats.ai': 'AI Powered',
            'landing.stats.platform': 'Platform',
            'landing.quickStart': 'QUICK START',
            'landing.chooseEntry': 'Choose Creation Entry',
            'landing.novel.title': 'Novel Creation',
            'landing.novel.desc': 'AI-powered intelligent novel generation system',
            'landing.novel.features': 'Two-phase · Smart Worldview',
            'landing.novel.enter': 'Enter →',
            'landing.video.title': 'Video Production',
            'landing.video.desc': 'Multi-modal video generation system',
            'landing.video.features': 'Multi-mode · Auto Edit',
            'landing.video.enter': 'Enter →',
            'landing.features.title': 'FEATURES',
            'landing.features.why': 'Why Choose Da Wenyu',
            'landing.feature.efficient': 'Efficient',
            'landing.feature.precise': 'Precise',
            'landing.feature.secure': 'Secure',
            'landing.feature.updated': 'Updated',
            
            // Home
            'home.welcome': 'Welcome back',
            'home.createNew': 'Create New Work',
            'home.continue': 'Continue Creating',
            'home.recentWorks': 'Recent Works',
            'home.viewAll': 'View All',
            
            // Novel creation
            'novel.create.title': 'Create New Novel',
            'novel.title': 'Novel Title',
            'novel.title.placeholder': 'Enter novel title',
            'novel.category': 'Category',
            'novel.tags': 'Tags',
            'novel.synopsis': 'Synopsis',
            'novel.synopsis.placeholder': 'Briefly describe your novel...',
            
            // Generation related
            'gen.start': 'Start Generation',
            'gen.stop': 'Stop Generation',
            'gen.regenerate': 'Regenerate',
            'gen.download': 'Download',
            'gen.preview': 'Preview',
            'gen.progress': 'Generation Progress',
            'gen.status.waiting': 'Waiting',
            'gen.status.processing': 'Processing',
            'gen.status.completed': 'Completed',
            'gen.status.failed': 'Failed',
            
            // Phase 1 Page
            'phase1.badge': 'Phase 1: Setup Generation',
            'phase1.title': 'Two-Phase Novel Generation',
            'phase1.subtitle': 'Generate complete world-building, character design and story outline',
            'phase1.form.title': 'Creative Input & Configuration',
            'phase1.guide.title': 'Instructions',
            'phase1.guide.goal.title': '🎯 Phase 1 Goal',
            'phase1.guide.goal.desc': 'Generate complete world-building, character design and detailed story outline to provide a high-quality foundation for subsequent chapter generation.',
            'phase1.guide.content.title': '⚙️ Generated Content',
            'phase1.guide.content.desc': '• World-building and background story<br>• Main character design and personality traits<br>• Story development stage planning<br>• Detailed chapter outlines<br>• Emotional threads and foreshadowing',
            'phase1.guide.bestPractice.title': '💡 Best Practices',
            'phase1.guide.bestPractice.desc': '• Describe core settings in detail (300+ words recommended)<br>• Clarify main selling points and features<br>• Plan chapter count reasonably (20-100 chapters recommended)<br>• Generate settings first, review before continuing',
            'phase1.guide.nextSteps.title': '🔄 Next Steps',
            'phase1.guide.nextSteps.desc': 'After Phase 1 completes, you can:<br>• Continue to Phase 2 chapter generation<br>• Save project and continue later<br>• View and edit generated settings<br>• Adjust parameters and regenerate',
            
            // Dashboard Page
            'dashboard.title': '📊 Dashboard',
            'dashboard.subtitle': 'View your creation statistics and analysis',
            'dashboard.stat.chapters': 'Chapters Generated',
            'dashboard.stat.thisSession': '↑ This Session',
            'dashboard.stat.words': 'Total Words',
            'dashboard.stat.avgScore': 'Avg Quality Score',
            'dashboard.stat.progress': 'Progress',
            'dashboard.detail.chapters': 'Chapter Details',
            'dashboard.detail.scoreDist': 'Quality Score Distribution',
            'dashboard.table.chapter': 'Chapter',
            'dashboard.table.title': 'Title',
            'dashboard.table.words': 'Words',
            'dashboard.table.score': 'Score',
            'dashboard.table.status': 'Status',
            'dashboard.table.action': 'Action',
            
            // Project Management Page
            'projectMgmt.badge': 'Project Center',
            'projectMgmt.title': 'Manage Your Novel Projects',
            'projectMgmt.subtitle': 'Manage two-phase novel generation projects, view progress and continue creation',
            'projectMgmt.stat.totalProjects': 'Total Projects',
            'projectMgmt.stat.completed': 'Completed',
            'projectMgmt.stat.inProgress': 'In Progress',
            'projectMgmt.stat.totalChapters': 'Total Chapters',
            'projectMgmt.searchPlaceholder': 'Search projects...',
            
            // Novels Page
            'novels.title': '📚 My Works',
            'novels.subtitle': 'Manage and browse all your AI novel creation projects',
            'novels.stat.projects': 'Projects',
            'novels.stat.chapters': 'Total Chapters',
            'novels.stat.words': 'Total Words',
            'novels.stat.completed': 'Completed',
            'novels.filters.title': 'Filter & Search',
            'novels.view.grid': 'Grid',
            'novels.view.list': 'List',
            'novels.searchPlaceholder': 'Search novel titles, descriptions or settings...',
            'novels.filter.all': 'All',
            'novels.filter.completed': 'Completed',
            'novels.filter.generating': 'Generating',
            'novels.filter.paused': 'Paused',
            'novels.empty.title': 'No Works Yet',
            'novels.empty.desc': 'Start your first AI novel creation journey! Click the "New Creation" button above to begin.',
            'novels.empty.start': 'Start Creating',
            
            // Workspace (index-v2)
            'workspace.welcome': 'Welcome back, {{username}}',
            'workspace.title': 'Start Your Creation Journey',
            'workspace.subtitle': 'Choose a tool and let AI help you realize your ideas',
            'workspace.stat.projects': 'Projects',
            'workspace.stat.chapters': 'Chapters',
            'workspace.stat.points': 'Points',
            'workspace.quickActions.label': 'Quick Actions',
            'workspace.quickActions.title': 'Quick Start',
            'workspace.card.twoPhase.title': 'Two-Phase Generation',
            'workspace.card.twoPhase.desc': 'From concept to content, AI assists the entire process. Generate world-building first, then chapters in batch.',
            'workspace.card.twoPhase.tag': 'Smart Setup · Batch Generation',
            'workspace.card.projectMgmt.title': 'Project Management',
            'workspace.card.projectMgmt.desc': 'Manage all novel projects, view progress, continue generation, export works. Support multiple projects.',
            'workspace.card.projectMgmt.tag': 'View Progress · Continue Creation',
            'workspace.card.creativeLib.title': 'Creative Library',
            'workspace.card.creativeLib.desc': 'Choose from preset creative ideas to quickly start creation. Multiple genre templates available.',
            'workspace.card.creativeLib.tag': '12 Creative Templates',
            'workspace.card.viewWorks.title': 'View Works',
            'workspace.card.viewWorks.desc': 'Browse and manage created novel chapters, support online reading, editing and exporting.',
            'workspace.card.viewWorks.tag': 'Online Reading · Edit & Export',
            'workspace.card.start': 'Start →',
            'workspace.card.enter': 'Enter →',
            'workspace.card.browse': 'Browse →',
            'workspace.card.view': 'View →',
            
            // Account Page
            'account.title': 'Account Settings',
            'account.subtitle': 'Manage your account information and security settings',
            'account.basicInfo.title': 'Basic Information',
            'account.basicInfo.username': 'Username',
            'account.basicInfo.userId': 'User ID',
            'account.basicInfo.status': 'Account Status',
            'account.changePassword.title': 'Change Password',
            'account.changePassword.current': 'Current Password',
            'account.changePassword.currentPlaceholder': 'Enter current password',
            'account.changePassword.new': 'New Password',
            'account.changePassword.newPlaceholder': 'Enter new password (at least 6 characters)',
            'account.changePassword.confirm': 'Confirm New Password',
            'account.changePassword.confirmPlaceholder': 'Enter new password again',
            'account.changePassword.btn': 'Change Password',
            'account.dangerZone.title': 'Danger Zone',
            'account.dangerZone.logout.title': 'Logout',
            'account.dangerZone.logout.desc': 'Logout and return to login page',
            
            // Novel Detail Page
            'novel.settings': 'Settings',
            'novel.export': 'Export',
            'novel.print': 'Print',
            'novel.backToList': 'Back to List',
            'novel.readingSettings.title': 'Reading Settings',
            'novel.readingSettings.fontSize': 'Font Size:',
            'novel.readingSettings.theme': 'Theme:',
            'novel.readingSettings.lineHeight': 'Line Height:',
            'novel.theme.light': 'Light',
            'novel.theme.sepia': 'Sepia',
            'novel.theme.dark': 'Dark',
            'novel.lineHeight.compact': 'Compact',
            'novel.lineHeight.loose': 'Loose',
            'novel.sidebar.info': 'Novel Info',
            'novel.sidebar.title': 'Title',
            'novel.sidebar.progress': 'Progress',
            'novel.sidebar.status': 'Status',
            'novel.sidebar.coreSetting': 'Core Setting',
            'novel.sidebar.sellingPoints': 'Selling Points',
            'novel.sidebar.chapterNav': 'Chapters',
            'novel.selectChapter': 'Select Chapter to Read',
            'novel.selectChapterHint': 'Click on chapter list to select',
            'novel.selectChapterPrompt': 'Please select a chapter from the left to start reading',
            
            // Common
            'common.loading': 'Loading...',
            'common.loadingProjects': 'Loading projects...',
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.confirm': 'Confirm',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.create': 'Create',
            'common.refresh': 'Refresh',
            'common.newProject': 'New Project',
            
            // Step names
            'step.creative_refinement': 'Creative Refinement',
            'step.fanfiction_detection': 'Fanfiction Detection',
            'step.multiple_plans': 'Plan Generation',
            'step.freshness_assessment': 'Freshness Assessment',
            'step.plan_selection': 'Plan Selection',
            'step.writing_style': 'Writing Style',
            'step.market_analysis': 'Market Analysis',
            'step.worldview': 'World Building',
            'step.faction_system': 'Faction System',
            'step.character_design': 'Character Design',
            'step.emotional_blueprint': 'Emotional Blueprint',
            'step.growth_plan': 'Growth Plan',
            'step.stage_plan': 'Stage Plan',
            'step.detailed_stage_plans': 'Detailed Plans',
            'step.expectation_mapping': 'Expectation Mapping',
            'step.system_init': 'System Init',
            'step.saving': 'Saving Results',
            'step.quality_assessment': 'Quality Assessment',
        }
    },
    
    /**
     * 初始化i18n系统
     */
    init() {
        // 从localStorage读取语言设置
        const savedSettings = JSON.parse(localStorage.getItem('userSettings') || '{}');
        if (savedSettings.language) {
            this.currentLang = savedSettings.language;
        } else {
            // 检测浏览器语言
            const browserLang = navigator.language || navigator.userLanguage;
            if (browserLang.startsWith('zh-TW') || browserLang.startsWith('zh-HK')) {
                this.currentLang = 'zh-TW';
            } else if (browserLang.startsWith('zh')) {
                this.currentLang = 'zh-CN';
            } else {
                this.currentLang = 'en';
            }
        }
        
        // 保存检测到的语言
        this.saveLanguage();
        
        // 应用语言到页面
        this.applyToPage();
    },
    
    /**
     * 获取翻译文本
     * @param {string} key - 翻译键
     * @param {object} params - 替换参数
     * @returns {string} 翻译后的文本
     */
    t(key, params = {}) {
        const translation = this.translations[this.currentLang]?.[key] 
            || this.translations['zh-CN']?.[key] 
            || key;
        
        // 替换参数
        return translation.replace(/\{\{(\w+)\}\}/g, (match, paramKey) => {
            return params[paramKey] !== undefined ? params[paramKey] : match;
        });
    },
    
    /**
     * 切换语言
     * @param {string} lang - 语言代码
     */
    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLang = lang;
            this.saveLanguage();
            this.applyToPage();
            
            // 更新HTML lang属性
            document.documentElement.lang = lang;
            
            // 触发自定义事件
            window.dispatchEvent(new CustomEvent('languageChanged', { 
                detail: { language: lang } 
            }));
        }
    },
    
    /**
     * 保存语言设置到localStorage
     */
    saveLanguage() {
        const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
        settings.language = this.currentLang;
        localStorage.setItem('userSettings', JSON.stringify(settings));
    },
    
    /**
     * 获取当前语言
     */
    getLanguage() {
        return this.currentLang;
    },
    
    /**
     * 应用翻译到页面所有带有data-i18n属性的元素
     */
    applyToPage() {
        // 翻译带有data-i18n属性的元素
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const attr = el.getAttribute('data-i18n-attr');
            if (key) {
                const translation = this.t(key);
                if (attr) {
                    // 如果指定了属性，则翻译该属性
                    el.setAttribute(attr, translation);
                } else if (el.hasAttribute('placeholder')) {
                    el.placeholder = translation;
                } else if (el.tagName === 'OPTION') {
                    // 对于下拉选项，保持value不变，只更新显示文本
                    el.textContent = translation;
                } else if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') {
                    if (el.hasAttribute('value')) {
                        el.value = translation;
                    } else {
                        el.textContent = translation;
                    }
                } else {
                    el.textContent = translation;
                }
            }
        });
        
        // 翻译带有data-i18n-html属性的元素（保留HTML）
        document.querySelectorAll('[data-i18n-html]').forEach(el => {
            const key = el.getAttribute('data-i18n-html');
            if (key) {
                el.innerHTML = this.t(key);
            }
        });
        
        // 翻译带有data-i18n-title属性的元素的title
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            if (key) {
                el.title = this.t(key);
            }
        });
        
        // 翻译带有data-i18n-placeholder属性的元素的placeholder
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (key) {
                el.placeholder = this.t(key);
            }
        });
        
        // 更新页面标题
        const titleEl = document.querySelector('title[data-i18n]');
        if (titleEl) {
            document.title = this.t(titleEl.getAttribute('data-i18n'));
        }
    },
    
    /**
     * 动态翻译元素
     * @param {HTMLElement} element - 要翻译的元素
     */
    translateElement(element) {
        if (element.hasAttribute('data-i18n')) {
            const key = element.getAttribute('data-i18n');
            if (element.hasAttribute('placeholder')) {
                element.placeholder = this.t(key);
            } else {
                element.textContent = this.t(key);
            }
        }
    }
};

// 简写函数
function t(key, params) {
    return I18N.t(key, params);
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    I18N.init();
});

// 导出供其他脚本使用
if (typeof module !== 'undefined' && module.exports) {
    module.exports = I18N;
}
