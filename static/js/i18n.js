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
