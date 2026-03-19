/**
 * 大文娱系统 V2 - 国际化 (i18n) 模块
 * 支持多语言切换和动态翻译
 */

const I18N = (function() {
    'use strict';

    // 翻译数据
    const translations = {
        'zh-CN': {
            // Phase 2 页面翻译
            'phase2.title': '第二阶段：章节生成',
            'phase2.subtitle': '生成小说章节内容',
            'phase2.step.select': '选择项目',
            'phase2.step.config': '配置参数',
            'phase2.step.generate': '生成章节',
            'phase2.step.preview': '预览结果',
            'phase2.project.placeholder': '请选择要续写的小说项目',
            'phase2.field.startChapter': '起始章节',
            'phase2.field.chapterCount': '生成章节数',
            'phase2.field.batchSize': '每批生成数量',
            'phase2.field.model': 'AI模型',
            'phase2.btn.start': '开始生成',
            'phase2.progress.title': '正在生成章节...',
            'phase2.progress.steps': '详细步骤进度',
            'phase2.result.title': '章节生成完成',
            'phase2.result.continue': '继续生成',
            'phase2.guide.title': '使用说明',
            'phase2.guide.tips': '生成技巧',
            
            // 通用翻译
            'common.loading': '加载中...',
            'common.save': '保存',
            'common.cancel': '取消',
            'common.confirm': '确认',
            'common.delete': '删除',
            'common.edit': '编辑',
            'common.create': '创建',
            'common.search': '搜索',
            'common.submit': '提交',
            'common.close': '关闭',
            'common.back': '返回',
            'common.next': '下一步',
            'common.prev': '上一步',
            'common.success': '成功',
            'common.error': '错误',
            'common.warning': '警告',
            'common.info': '信息',
            
            // 小说列表页翻译
            'novels.title': '我的作品',
            'novels.subtitle': '管理和浏览您的AI小说创作',
            'novels.filter.all': '全部',
            'novels.filter.completed': '已完成',
            'novels.filter.generating': '生成中',
            'novels.card.chapters': '章',
            'novels.card.words': '字',
            'novels.btn.read': '阅读',
            'novels.btn.continue': '继续生成',
            'novels.btn.export': '导出',
            'novels.empty.title': '还没有创作作品',
            'novels.empty.desc': '开始您的第一个AI小说创作之旅吧！',
            'novels.empty.start': '开始创作',
            
            // 仪表板翻译
            'dashboard.title': '创作仪表板',
            'dashboard.stat.projects': '创作项目',
            'dashboard.stat.chapters': '生成章节',
            'dashboard.stat.words': '总字数',
            'dashboard.section.recent': '最近项目',
            'dashboard.section.quick': '快速入口',
            'dashboard.btn.newProject': '新建项目',
            'dashboard.btn.continue': '继续创作',
            
            // 项目管理翻译
            'projectMgmt.badge': '项目管理中心',
            'projectMgmt.title': '管理您的小说项目',
            'projectMgmt.subtitle': '统一管理两阶段生成的小说项目',
            'projectMgmt.stat.totalProjects': '总项目数',
            'projectMgmt.stat.completed': '已完成',
            'projectMgmt.stat.inProgress': '进行中',
            'projectMgmt.filter.allStatus': '所有状态',
            'projectMgmt.filter.phaseOneOnly': '仅第一阶段完成',
            'projectMgmt.filter.phaseTwoInProgress': '第二阶段进行中',
            'projectMgmt.card.progress': '生成进度',
            'projectMgmt.card.chapters': '章节',
            'projectMgmt.status.completed': '已完成',
            'projectMgmt.status.phaseOneCompleted': '一阶段已完成',
            'projectMgmt.action.continue': '继续生成',
            'projectMgmt.action.viewSettings': '查看设定',
            'projectMgmt.action.export': '导出',
            'projectMgmt.empty.title': '暂无项目',
            'projectMgmt.empty.createBtn': '创建第一个项目',
            
            // 故事线时间线
            'storyline.title': '故事线时间线',
            'storyline.subtitle': '查看和管理所有重大事件及其细分',
            'storyline.timeline.title': '时间线',
            'storyline.event.major': '重大事件',
            'storyline.event.minor': '细分事件',
            'storyline.action.add': '添加事件',
            'storyline.action.edit': '编辑',
            'storyline.action.delete': '删除',
            
            // 视频生成页翻译
            'videoGen.title': '视频生成系统',
            'videoGen.subtitle': '将小说内容转换为视频',
            'videoGen.section.source': '选择素材',
            'videoGen.section.config': '生成配置',
            'videoGen.section.preview': '预览效果',
            'videoGen.form.novel': '选择小说',
            'videoGen.form.chapters': '选择章节',
            'videoGen.btn.generate': '生成视频',
            'videoGen.btn.preview': '预览',
            'videoGen.section.novels': '我的小说',
            'videoGen.section.selectContent': '选择内容',
            'videoGen.tab.events': '事件',
            'videoGen.tab.characters': '角色',
            'videoGen.selected.events': '已选: 0个事件',
            'videoGen.selected.characters': '已选: 0个角色',
            'videoGen.btn.selectAllEvents': '全选事件',
            'videoGen.btn.selectAllCharacters': '全选角色',
            'videoGen.btn.clearSelection': '清空选择',
            'videoGen.mode.custom': '自定义模式',
            'videoGen.mode.custom.desc': '完全自由控制，使用自定义提示词生成视频',
            'videoGen.feature.custom.prompt': '直接输入提示词，灵活创作',
            'videoGen.feature.custom.style': '支持任意风格和主题',
            'videoGen.feature.custom.fast': '快速生成，无需依赖小说',
            'videoGen.feature.custom.control': '完全自定义控制',
            'videoGen.mode.novel': '我的小说',
            'videoGen.mode.novel.desc': '基于已生成的小说项目自动生成分镜头脚本',
            'videoGen.feature.novel.auto': '从小说项目自动生成',
            'videoGen.feature.novel.extract': '智能提取关键情节',
            'videoGen.feature.novel.script': '自动生成详细脚本',
            'videoGen.feature.novel.style': '保持小说风格一致',
            'videoGen.mode.portrait': '人物剧照生成',
            'videoGen.mode.portrait.desc': '生成高质量的角色剧照，支持参考图像和自定义提示词',
            'videoGen.feature.portrait.character': '支持小说角色和自定义',
            'videoGen.feature.portrait.reference': '可上传参考图像',
            'videoGen.feature.portrait.quality': '多种比例和质量',
            'videoGen.feature.portrait.prompt': '自动生成角色提示词',
            'videoGen.mode.workspace': '视频工作台',
            'videoGen.mode.workspace.desc': '专业的视频制作工作台，支持实时预览和播放控制',
            'videoGen.feature.workspace.preview': '大屏视频预览窗口',
            'videoGen.feature.workspace.playback': '完整的播放控制功能',
            'videoGen.feature.workspace.api': 'OpenAI API 集成',
            'videoGen.feature.workspace.quality': '高质量视频输出',
            'videoGen.mode.shortDrama': '短剧工作台',
            'videoGen.mode.shortDrama.desc': '选集 → 角色剧照 → 分镜头 → 视频生成，一站式短剧制作',
            'videoGen.feature.shortDrama.episodes': '选择要制作的集数',
            'videoGen.feature.shortDrama.portraits': '角色剧照管理',
            'videoGen.feature.shortDrama.storyboard': '分镜头脚本',
            'videoGen.feature.shortDrama.batch': '批量视频生成',
            'videoGen.convert.title': '将小说转换为视频',
            'videoGen.convert.desc': '支持三种视频模式，满足不同创作需求',
            'videoGen.btn.backToMode': '返回模式选择',
            'videoGen.section.generatedShots': '已生成的分镜头',
            'videoGen.empty.noShots': '还没有生成分镜头',
            'videoGen.empty.selectContent': '选择事件和角色后开始生成',
            'videoGen.btn.export': '导出',
            'videoGen.btn.clear': '清空',
            'videoGen.help.workflow': '使用流程',
            'videoGen.step.selectMode': '选择模式',
            'videoGen.step.selectNovel': '选择小说和视频类型',
            'videoGen.step.selectContent': '选择事件和角色',
            'videoGen.step.viewPrompt': '查看提示词',
            'videoGen.step.generateStoryboard': '生成分镜头脚本',
            'videoGen.step.generateVideo': '逐个或批量生成视频',
            'videoGen.help.status': '当前状态',
            'videoGen.status.selectMode': '请选择生成模式',
            'videoGen.help.typeDesc': '视频类型说明',
            'videoGen.hint.selectMode': '选择模式后查看详细说明',
            'videoGen.modal.editPrompt': '编辑生成提示词',
            'videoGen.portrait.preview': '剧照预览',
            'videoGen.portrait.name': '角色名',
            'videoGen.portrait.role': '角色',
            
            // 通用翻译补充
            'common.recommended': '推荐',
            'common.newFeature': '新功能',
            'common.refresh': '刷新列表',
            'common.platformName': '大文娱创作平台',
            
            // 人物剧照生成页翻译
            'characterPortrait.title': '人物剧照生成',
            'characterPortrait.subtitle': '支持参考图像 + 自定义提示词，生成高质量角色剧照',
            'characterPortrait.step.select': '选择小说',
            'characterPortrait.step.config': '配置角色',
            'characterPortrait.step.generate': '生成剧照',
            'characterPortrait.form.character': '选择角色',
            'characterPortrait.form.prompt': '提示词',
            'characterPortrait.form.reference': '参考图像',
            'characterPortrait.btn.generate': '开始生成',
            
            // 项目可视化页面
            'projectViewer.title': '项目可视化',
            'projectViewer.subtitle': '可视化展示项目结构',
            'projectViewer.view.overview': '概览',
            'projectViewer.view.characters': '角色',
            'projectViewer.view.timeline': '时间线',
            'projectViewer.view.worldview': '世界观',
            'projectViewer.action.editMode': '编辑模式',
            'projectViewer.action.save': '保存',
            
            // 世界观查看器
            'worldviewViewer.title': '世界观查看器',
            'worldviewViewer.subtitle': '查看和管理小说世界观',
            'worldviewViewer.section.overview': '概览',
            'worldviewViewer.section.settings': '详细设定',
            'worldviewViewer.section.characters': '角色关系',
            'worldviewViewer.section.factions': '势力信息',
            'worldviewViewer.section.locations': '重要地点',
            'worldviewViewer.section.powerSystem': '修炼体系',
            'worldviewViewer.section.magicSystem': '法术系统',
            'worldviewViewer.section.socialSystem': '社会制度',
            'worldviewViewer.action.edit': '编辑',
            'worldviewViewer.action.save': '保存',
            'worldviewViewer.action.export': '导出',
            
            // 人物剧照工作室
            'portraitStudio.title': '人物剧照工作室',
            'portraitStudio.subtitle': '生成和管理角色剧照',
            'portraitStudio.section.characters': '角色列表',
            'portraitStudio.section.gallery': '剧照画廊',
            'portraitStudio.btn.generate': '生成剧照',
            'portraitStudio.btn.upload': '上传参考图',
            'portraitStudio.btn.batch': '批量生成',
            'portraitStudio.empty.noCharacters': '暂无角色',
            'portraitStudio.empty.addCharacter': '添加角色',
            
            // 图像素材库
            'imageLibrary.title': '图像素材库',
            'imageLibrary.subtitle': '管理和使用您的图像素材',
            'imageLibrary.section.all': '全部素材',
            'imageLibrary.section.characters': '角色',
            'imageLibrary.section.scenes': '场景',
            'imageLibrary.section.items': '道具',
            'imageLibrary.action.upload': '上传',
            'imageLibrary.action.search': '搜索',
            'imageLibrary.action.filter': '筛选',
            
            // 视频任务管理
            'videoTaskMgr.title': '视频任务管理',
            'videoTaskMgr.subtitle': '管理所有视频生成任务',
            'videoTaskMgr.status.pending': '待处理',
            'videoTaskMgr.status.processing': '处理中',
            'videoTaskMgr.status.completed': '已完成',
            'videoTaskMgr.status.failed': '失败',
            'videoTaskMgr.action.newTask': '新建任务',
            'videoTaskMgr.action.batchDelete': '批量删除',
            'videoTaskMgr.action.retry': '重试',
        },
        'zh-TW': {
            // Phase 2 頁面翻譯
            'phase2.title': '第二階段：章節生成',
            'phase2.subtitle': '生成小說章節內容',
            'phase2.step.select': '選擇項目',
            'phase2.step.config': '配置參數',
            'phase2.step.generate': '生成章節',
            'phase2.step.preview': '預覽結果',
            'phase2.project.placeholder': '請選擇要續寫的小說項目',
            'phase2.field.startChapter': '起始章節',
            'phase2.field.chapterCount': '生成章節數',
            'phase2.field.batchSize': '每批生成數量',
            'phase2.field.model': 'AI模型',
            'phase2.btn.start': '開始生成',
            'phase2.progress.title': '正在生成章節...',
            'phase2.progress.steps': '詳細步驟進度',
            'phase2.result.title': '章節生成完成',
            'phase2.result.continue': '繼續生成',
            'phase2.guide.title': '使用說明',
            'phase2.guide.tips': '生成技巧',
            
            // 通用翻譯
            'common.loading': '載入中...',
            'common.save': '儲存',
            'common.cancel': '取消',
            'common.confirm': '確認',
            'common.delete': '刪除',
            'common.edit': '編輯',
            'common.create': '建立',
            'common.search': '搜尋',
            'common.submit': '提交',
            'common.close': '關閉',
            'common.back': '返回',
            'common.next': '下一步',
            'common.prev': '上一步',
            'common.success': '成功',
            'common.error': '錯誤',
            'common.warning': '警告',
            'common.info': '資訊',
            
            // 小說列表頁翻譯
            'novels.title': '我的作品',
            'novels.subtitle': '管理和瀏覽您的AI小說創作',
            'novels.filter.all': '全部',
            'novels.filter.completed': '已完成',
            'novels.filter.generating': '生成中',
            'novels.card.chapters': '章',
            'novels.card.words': '字',
            'novels.btn.read': '閱讀',
            'novels.btn.continue': '繼續生成',
            'novels.btn.export': '匯出',
            'novels.empty.title': '還沒有創作作品',
            'novels.empty.desc': '開始您的第一個AI小說創作之旅吧！',
            'novels.empty.start': '開始創作',
            
            // 儀表板翻譯
            'dashboard.title': '創作儀表板',
            'dashboard.stat.projects': '創作項目',
            'dashboard.stat.chapters': '生成章節',
            'dashboard.stat.words': '總字數',
            'dashboard.section.recent': '最近項目',
            'dashboard.section.quick': '快速入口',
            'dashboard.btn.newProject': '新建項目',
            'dashboard.btn.continue': '繼續創作',
            
            // 項目管理翻譯
            'projectMgmt.badge': '項目管理中心',
            'projectMgmt.title': '管理您的小說項目',
            'projectMgmt.subtitle': '統一管理兩階段生成的小說項目',
            'projectMgmt.stat.totalProjects': '總項目數',
            'projectMgmt.stat.completed': '已完成',
            'projectMgmt.stat.inProgress': '進行中',
            'projectMgmt.filter.allStatus': '所有狀態',
            'projectMgmt.filter.phaseOneOnly': '僅第一階段完成',
            'projectMgmt.filter.phaseTwoInProgress': '第二階段進行中',
            'projectMgmt.card.progress': '生成進度',
            'projectMgmt.card.chapters': '章節',
            'projectMgmt.status.completed': '已完成',
            'projectMgmt.status.phaseOneCompleted': '一階段已完成',
            'projectMgmt.action.continue': '繼續生成',
            'projectMgmt.action.viewSettings': '查看設定',
            'projectMgmt.action.export': '匯出',
            'projectMgmt.empty.title': '暫無項目',
            'projectMgmt.empty.createBtn': '創建第一個項目',
            
            // 故事線時間線
            'storyline.title': '故事線時間線',
            'storyline.subtitle': '查看和管理所有重大事件及其細分',
            'storyline.timeline.title': '時間線',
            'storyline.event.major': '重大事件',
            'storyline.event.minor': '細分事件',
            'storyline.action.add': '添加事件',
            'storyline.action.edit': '編輯',
            'storyline.action.delete': '刪除',
            
            // 影片生成頁翻譯
            'videoGen.title': '影片生成系統',
            'videoGen.subtitle': '將小說內容轉換為影片',
            'videoGen.section.source': '選擇素材',
            'videoGen.section.config': '生成配置',
            'videoGen.section.preview': '預覽效果',
            'videoGen.form.novel': '選擇小說',
            'videoGen.form.chapters': '選擇章節',
            'videoGen.btn.generate': '生成影片',
            'videoGen.btn.preview': '預覽',
            'videoGen.section.novels': '我的小說',
            'videoGen.section.selectContent': '選擇內容',
            'videoGen.tab.events': '事件',
            'videoGen.tab.characters': '角色',
            'videoGen.selected.events': '已選: 0個事件',
            'videoGen.selected.characters': '已選: 0個角色',
            'videoGen.btn.selectAllEvents': '全選事件',
            'videoGen.btn.selectAllCharacters': '全選角色',
            'videoGen.btn.clearSelection': '清空選擇',
            'videoGen.mode.custom': '自訂模式',
            'videoGen.mode.custom.desc': '完全自由控制，使用自訂提示詞生成影片',
            'videoGen.feature.custom.prompt': '直接輸入提示詞，靈活創作',
            'videoGen.feature.custom.style': '支援任意風格和主題',
            'videoGen.feature.custom.fast': '快速生成，無需依賴小說',
            'videoGen.feature.custom.control': '完全自訂控制',
            'videoGen.mode.novel': '我的小說',
            'videoGen.mode.novel.desc': '基於已生成的小說項目自動生成分鏡頭腳本',
            'videoGen.feature.novel.auto': '從小說項目自動生成',
            'videoGen.feature.novel.extract': '智能提取關鍵情節',
            'videoGen.feature.novel.script': '自動生成詳細腳本',
            'videoGen.feature.novel.style': '保持小說風格一致',
            'videoGen.mode.portrait': '人物劇照生成',
            'videoGen.mode.portrait.desc': '生成高質量的角色劇照，支援參考圖像和自訂提示詞',
            'videoGen.feature.portrait.character': '支援小說角色和自訂',
            'videoGen.feature.portrait.reference': '可上傳參考圖像',
            'videoGen.feature.portrait.quality': '多種比例和質量',
            'videoGen.feature.portrait.prompt': '自動生成角色提示詞',
            'videoGen.mode.workspace': '影片工作台',
            'videoGen.mode.workspace.desc': '專業的影片製作工作台，支援實時預覽和播放控制',
            'videoGen.feature.workspace.preview': '大屏影片預覽窗口',
            'videoGen.feature.workspace.playback': '完整的播放控制功能',
            'videoGen.feature.workspace.api': 'OpenAI API 集成',
            'videoGen.feature.workspace.quality': '高質量影片輸出',
            'videoGen.mode.shortDrama': '短劇工作台',
            'videoGen.mode.shortDrama.desc': '選集 → 角色劇照 → 分鏡頭 → 影片生成，一站式短劇製作',
            'videoGen.feature.shortDrama.episodes': '選擇要製作的集數',
            'videoGen.feature.shortDrama.portraits': '角色劇照管理',
            'videoGen.feature.shortDrama.storyboard': '分鏡頭腳本',
            'videoGen.feature.shortDrama.batch': '批量影片生成',
            'videoGen.convert.title': '將小說轉換為影片',
            'videoGen.convert.desc': '支援三種影片模式，滿足不同創作需求',
            'videoGen.btn.backToMode': '返回模式選擇',
            'videoGen.section.generatedShots': '已生成的分鏡頭',
            'videoGen.empty.noShots': '還沒有生成分鏡頭',
            'videoGen.empty.selectContent': '選擇事件和角色後開始生成',
            'videoGen.btn.export': '匯出',
            'videoGen.btn.clear': '清空',
            'videoGen.help.workflow': '使用流程',
            'videoGen.step.selectMode': '選擇模式',
            'videoGen.step.selectNovel': '選擇小說和影片類型',
            'videoGen.step.selectContent': '選擇事件和角色',
            'videoGen.step.viewPrompt': '查看提示詞',
            'videoGen.step.generateStoryboard': '生成分鏡頭腳本',
            'videoGen.step.generateVideo': '逐個或批量生成影片',
            'videoGen.help.status': '當前狀態',
            'videoGen.status.selectMode': '請選擇生成模式',
            'videoGen.help.typeDesc': '影片類型說明',
            'videoGen.hint.selectMode': '選擇模式後查看詳細說明',
            'videoGen.modal.editPrompt': '編輯生成提示詞',
            'videoGen.portrait.preview': '劇照預覽',
            'videoGen.portrait.name': '角色名',
            'videoGen.portrait.role': '角色',
            
            // 通用翻譯補充
            'common.recommended': '推薦',
            'common.newFeature': '新功能',
            'common.refresh': '重新整理列表',
            'common.platformName': '大文娛創作平台',
            
            // 人物劇照生成頁翻譯
            'characterPortrait.title': '人物劇照生成',
            'characterPortrait.subtitle': '支援參考圖像 + 自訂提示詞，生成高質量角色劇照',
            'characterPortrait.step.select': '選擇小說',
            'characterPortrait.step.config': '配置角色',
            'characterPortrait.step.generate': '生成劇照',
            'characterPortrait.form.character': '選擇角色',
            'characterPortrait.form.prompt': '提示詞',
            'characterPortrait.form.reference': '參考圖像',
            'characterPortrait.btn.generate': '開始生成',
            
            // 世界觀查看器
            'worldviewViewer.title': '世界觀查看器',
            'worldviewViewer.subtitle': '查看和管理小說世界觀',
            'worldviewViewer.section.overview': '概覽',
            'worldviewViewer.section.settings': '詳細設定',
            'worldviewViewer.section.characters': '角色關係',
            'worldviewViewer.section.factions': '勢力信息',
            'worldviewViewer.section.locations': '重要地點',
            'worldviewViewer.section.powerSystem': '修煉體系',
            'worldviewViewer.section.magicSystem': '法術系統',
            'worldviewViewer.section.socialSystem': '社會制度',
            'worldviewViewer.action.edit': '編輯',
            'worldviewViewer.action.save': '儲存',
            'worldviewViewer.action.export': '匯出',
            
            // 人物劇照工作室
            'portraitStudio.title': '人物劇照工作室',
            'portraitStudio.subtitle': '生成和管理角色劇照',
            'portraitStudio.section.characters': '角色列表',
            'portraitStudio.section.gallery': '劇照畫廊',
            'portraitStudio.btn.generate': '生成劇照',
            'portraitStudio.btn.upload': '上傳參考圖',
            'portraitStudio.btn.batch': '批量生成',
            'portraitStudio.empty.noCharacters': '暫無角色',
            'portraitStudio.empty.addCharacter': '添加角色',
            
            // 圖像素材庫
            'imageLibrary.title': '圖像素材庫',
            'imageLibrary.subtitle': '管理和使用您的圖像素材',
            'imageLibrary.section.all': '全部素材',
            'imageLibrary.section.characters': '角色',
            'imageLibrary.section.scenes': '場景',
            'imageLibrary.section.items': '道具',
            'imageLibrary.action.upload': '上傳',
            'imageLibrary.action.search': '搜尋',
            'imageLibrary.action.filter': '篩選',
            
            // 视频任务管理
            'videoTaskMgr.title': '影片任務管理',
            'videoTaskMgr.subtitle': '管理所有影片生成任務',
            'videoTaskMgr.status.pending': '待處理',
            'videoTaskMgr.status.processing': '處理中',
            'videoTaskMgr.status.completed': '已完成',
            'videoTaskMgr.status.failed': '失敗',
            'videoTaskMgr.action.newTask': '新任務',
            'videoTaskMgr.action.batchDelete': '批量刪除',
            'videoTaskMgr.action.retry': '重試',
        },
        'en': {
            // Phase 2 Page Translations
            'phase2.title': 'Phase 2: Chapter Generation',
            'phase2.subtitle': 'Generate Novel Chapters',
            'phase2.step.select': 'Select Project',
            'phase2.step.config': 'Configure Parameters',
            'phase2.step.generate': 'Generate Chapters',
            'phase2.step.preview': 'Preview Results',
            'phase2.project.placeholder': 'Please select a novel project to continue',
            'phase2.field.startChapter': 'Start Chapter',
            'phase2.field.chapterCount': 'Number of Chapters',
            'phase2.field.batchSize': 'Batch Size',
            'phase2.field.model': 'AI Model',
            'phase2.btn.start': 'Start Generation',
            'phase2.progress.title': 'Generating Chapters...',
            'phase2.progress.steps': 'Detailed Progress',
            'phase2.result.title': 'Chapter Generation Complete',
            'phase2.result.continue': 'Continue Generation',
            'phase2.guide.title': 'Instructions',
            'phase2.guide.tips': 'Generation Tips',
            
            // Common Translations
            'common.loading': 'Loading...',
            'common.save': 'Save',
            'common.cancel': 'Cancel',
            'common.confirm': 'Confirm',
            'common.delete': 'Delete',
            'common.edit': 'Edit',
            'common.create': 'Create',
            'common.search': 'Search',
            'common.submit': 'Submit',
            'common.close': 'Close',
            'common.back': 'Back',
            'common.next': 'Next',
            'common.prev': 'Previous',
            'common.success': 'Success',
            'common.error': 'Error',
            'common.warning': 'Warning',
            'common.info': 'Info',
            
            // Novels List Page Translations
            'novels.title': 'My Works',
            'novels.subtitle': 'Manage and browse your AI novel creations',
            'novels.filter.all': 'All',
            'novels.filter.completed': 'Completed',
            'novels.filter.generating': 'Generating',
            'novels.card.chapters': 'chapters',
            'novels.card.words': 'words',
            'novels.btn.read': 'Read',
            'novels.btn.continue': 'Continue',
            'novels.btn.export': 'Export',
            'novels.empty.title': 'No works yet',
            'novels.empty.desc': 'Start your first AI novel creation journey!',
            'novels.empty.start': 'Start Creating',
            
            // Project Management Translations
            'projectMgmt.badge': 'Project Management',
            'projectMgmt.title': 'Manage Your Novel Projects',
            'projectMgmt.subtitle': 'Manage your two-phase novel generation projects',
            'projectMgmt.stat.totalProjects': 'Total Projects',
            'projectMgmt.stat.completed': 'Completed',
            'projectMgmt.stat.inProgress': 'In Progress',
            'projectMgmt.filter.allStatus': 'All Status',
            'projectMgmt.filter.phaseOneOnly': 'Phase One Only',
            'projectMgmt.filter.phaseTwoInProgress': 'Phase Two In Progress',
            'projectMgmt.card.progress': 'Progress',
            'projectMgmt.card.chapters': 'Chapters',
            'projectMgmt.status.completed': 'Completed',
            'projectMgmt.status.phaseOneCompleted': 'Phase One Completed',
            'projectMgmt.action.continue': 'Continue',
            'projectMgmt.action.viewSettings': 'View Settings',
            'projectMgmt.action.export': 'Export',
            'projectMgmt.empty.title': 'No Projects',
            'projectMgmt.empty.createBtn': 'Create First Project',
            
            // Storyline Timeline
            'storyline.title': 'Storyline Timeline',
            'storyline.subtitle': 'View and manage all major events and their subdivisions',
            'storyline.timeline.title': 'Timeline',
            'storyline.event.major': 'Major Events',
            'storyline.event.minor': 'Sub Events',
            'storyline.action.add': 'Add Event',
            'storyline.action.edit': 'Edit',
            'storyline.action.delete': 'Delete',
            
            // Video Generation Page Translations
            'videoGen.title': 'Video Generation',
            'videoGen.subtitle': 'Convert novel content to video',
            'videoGen.section.source': 'Select Source',
            'videoGen.section.config': 'Generation Config',
            'videoGen.section.preview': 'Preview',
            'videoGen.form.novel': 'Select Novel',
            'videoGen.form.chapters': 'Select Chapters',
            'videoGen.btn.generate': 'Generate Video',
            'videoGen.btn.preview': 'Preview',
            'videoGen.section.novels': 'My Novels',
            'videoGen.section.selectContent': 'Select Content',
            'videoGen.tab.events': 'Events',
            'videoGen.tab.characters': 'Characters',
            'videoGen.selected.events': 'Selected: 0 events',
            'videoGen.selected.characters': 'Selected: 0 characters',
            'videoGen.btn.selectAllEvents': 'Select All Events',
            'videoGen.btn.selectAllCharacters': 'Select All Characters',
            'videoGen.btn.clearSelection': 'Clear Selection',
            'videoGen.mode.custom': 'Custom Mode',
            'videoGen.mode.custom.desc': 'Full control with custom prompts for video generation',
            'videoGen.feature.custom.prompt': 'Direct prompt input for flexible creation',
            'videoGen.feature.custom.style': 'Support any style and theme',
            'videoGen.feature.custom.fast': 'Fast generation, no novel required',
            'videoGen.feature.custom.control': 'Full custom control',
            'videoGen.mode.novel': 'My Novels',
            'videoGen.mode.novel.desc': 'Auto-generate storyboard scripts from existing novel projects',
            'videoGen.feature.novel.auto': 'Auto-generate from novel projects',
            'videoGen.feature.novel.extract': 'Intelligent key plot extraction',
            'videoGen.feature.novel.script': 'Auto-generate detailed scripts',
            'videoGen.feature.novel.style': 'Maintain novel style consistency',
            'videoGen.mode.portrait': 'Character Portrait',
            'videoGen.mode.portrait.desc': 'Generate high-quality character portraits with reference images',
            'videoGen.feature.portrait.character': 'Support novel and custom characters',
            'videoGen.feature.portrait.reference': 'Upload reference images',
            'videoGen.feature.portrait.quality': 'Multiple ratios and quality options',
            'videoGen.feature.portrait.prompt': 'Auto-generate character prompts',
            'videoGen.mode.workspace': 'Video Workspace',
            'videoGen.mode.workspace.desc': 'Professional video production workspace with real-time preview',
            'videoGen.feature.workspace.preview': 'Large video preview window',
            'videoGen.feature.workspace.playback': 'Full playback controls',
            'videoGen.feature.workspace.api': 'OpenAI API integration',
            'videoGen.feature.workspace.quality': 'High-quality video output',
            'videoGen.mode.shortDrama': 'Short Drama Studio',
            'videoGen.mode.shortDrama.desc': 'Episodes → Portraits → Storyboard → Video, all-in-one short drama production',
            'videoGen.feature.shortDrama.episodes': 'Select episodes to produce',
            'videoGen.feature.shortDrama.portraits': 'Character portrait management',
            'videoGen.feature.shortDrama.storyboard': 'Storyboard scripts',
            'videoGen.feature.shortDrama.batch': 'Batch video generation',
            'videoGen.convert.title': 'Convert Novel to Video',
            'videoGen.convert.desc': 'Support three video modes for different creative needs',
            'videoGen.btn.backToMode': 'Back to Mode Selection',
            'videoGen.section.generatedShots': 'Generated Shots',
            'videoGen.empty.noShots': 'No shots generated yet',
            'videoGen.empty.selectContent': 'Select events and characters to start',
            'videoGen.btn.export': 'Export',
            'videoGen.btn.clear': 'Clear',
            'videoGen.help.workflow': 'Workflow',
            'videoGen.step.selectMode': 'Select Mode',
            'videoGen.step.selectNovel': 'Select novel and video type',
            'videoGen.step.selectContent': 'Select events and characters',
            'videoGen.step.viewPrompt': 'View prompts',
            'videoGen.step.generateStoryboard': 'Generate storyboard',
            'videoGen.step.generateVideo': 'Generate videos individually or in batch',
            'videoGen.help.status': 'Current Status',
            'videoGen.status.selectMode': 'Please select a generation mode',
            'videoGen.help.typeDesc': 'Video Type Description',
            'videoGen.hint.selectMode': 'View detailed description after selecting mode',
            'videoGen.modal.editPrompt': 'Edit Generation Prompt',
            'videoGen.portrait.preview': 'Portrait Preview',
            'videoGen.portrait.name': 'Character Name',
            'videoGen.portrait.role': 'Role',
            
            // Common translations supplement
            'common.recommended': 'Recommended',
            'common.newFeature': 'New',
            'common.refresh': 'Refresh List',
            'common.platformName': 'Entertainment Creation Platform',
            
            // Character Portrait Page Translations
            'characterPortrait.title': 'Character Portrait',
            'characterPortrait.subtitle': 'Generate high-quality character portraits with reference images and custom prompts',
            'characterPortrait.step.select': 'Select Novel',
            'characterPortrait.step.config': 'Configure Character',
            'characterPortrait.step.generate': 'Generate Portrait',
            'characterPortrait.form.character': 'Select Character',
            'characterPortrait.form.prompt': 'Prompt',
            'characterPortrait.form.reference': 'Reference Image',
            'characterPortrait.btn.generate': 'Start Generation',
            
            // Project Viewer Page
            'projectViewer.title': 'Project Viewer',
            'projectViewer.subtitle': 'Visualize project structure',
            'projectViewer.view.overview': 'Overview',
            'projectViewer.view.characters': 'Characters',
            'projectViewer.view.timeline': 'Timeline',
            'projectViewer.view.worldview': 'Worldview',
            'projectViewer.action.editMode': 'Edit Mode',
            'projectViewer.action.save': 'Save',
            
            // Worldview Viewer
            'worldviewViewer.title': 'Worldview Viewer',
            'worldviewViewer.subtitle': 'View and manage novel worldview',
            'worldviewViewer.section.overview': 'Overview',
            'worldviewViewer.section.settings': 'Detailed Settings',
            'worldviewViewer.section.characters': 'Character Relations',
            'worldviewViewer.section.factions': 'Factions',
            'worldviewViewer.section.locations': 'Key Locations',
            'worldviewViewer.section.powerSystem': 'Power System',
            'worldviewViewer.section.magicSystem': 'Magic System',
            'worldviewViewer.section.socialSystem': 'Social System',
            'worldviewViewer.action.edit': 'Edit',
            'worldviewViewer.action.save': 'Save',
            'worldviewViewer.action.export': 'Export',
            
            // Portrait Studio
            'portraitStudio.title': 'Character Portrait Studio',
            'portraitStudio.subtitle': 'Generate and manage character portraits',
            'portraitStudio.section.characters': 'Character List',
            'portraitStudio.section.gallery': 'Portrait Gallery',
            'portraitStudio.btn.generate': 'Generate Portrait',
            'portraitStudio.btn.upload': 'Upload Reference',
            'portraitStudio.btn.batch': 'Batch Generate',
            'portraitStudio.empty.noCharacters': 'No characters yet',
            'portraitStudio.empty.addCharacter': 'Add Character',
            
            // Image Library
            'imageLibrary.title': 'Image Library',
            'imageLibrary.subtitle': 'Manage and use your image assets',
            'imageLibrary.section.all': 'All Assets',
            'imageLibrary.section.characters': 'Characters',
            'imageLibrary.section.scenes': 'Scenes',
            'imageLibrary.section.items': 'Items',
            'imageLibrary.action.upload': 'Upload',
            'imageLibrary.action.search': 'Search',
            'imageLibrary.action.filter': 'Filter',
            
            // Video Task Manager
            'videoTaskMgr.title': 'Video Task Manager',
            'videoTaskMgr.subtitle': 'Manage all video generation tasks',
            'videoTaskMgr.status.pending': 'Pending',
            'videoTaskMgr.status.processing': 'Processing',
            'videoTaskMgr.status.completed': 'Completed',
            'videoTaskMgr.status.failed': 'Failed',
            'videoTaskMgr.action.newTask': 'New Task',
            'videoTaskMgr.action.batchDelete': 'Batch Delete',
            'videoTaskMgr.action.retry': 'Retry',
        }
    };

    // 当前语言
    let currentLanguage = 'zh-CN';

    // 从 localStorage 加载语言设置
    function loadLanguageSetting() {
        try {
            const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
            if (settings.language && translations[settings.language]) {
                currentLanguage = settings.language;
            }
        } catch (e) {
            console.warn('Failed to load language setting:', e);
        }
    }

    // 获取翻译
    function getTranslation(key, lang) {
        const language = lang || currentLanguage;
        const trans = translations[language];
        if (trans && trans[key]) {
            return trans[key];
        }
        // 回退到简体中文
        if (language !== 'zh-CN' && translations['zh-CN'][key]) {
            return translations['zh-CN'][key];
        }
        // 返回键名
        return key;
    }

    // 设置语言
    function setLanguage(lang) {
        if (translations[lang]) {
            currentLanguage = lang;
            applyTranslations();
            
            // 保存设置
            try {
                const settings = JSON.parse(localStorage.getItem('userSettings') || '{}');
                settings.language = lang;
                localStorage.setItem('userSettings', JSON.stringify(settings));
            } catch (e) {
                console.warn('Failed to save language setting:', e);
            }
            
            // 触发语言切换事件
            document.dispatchEvent(new CustomEvent('languageChanged', { detail: { language: lang } }));
            
            return true;
        }
        return false;
    }

    // 应用翻译到页面
    function applyTranslations() {
        // 翻译带有 data-i18n 属性的元素
        document.querySelectorAll('[data-i18n]').forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = getTranslation(key);
            
            // 根据元素类型设置翻译
            if (element.hasAttribute('data-i18n-attr')) {
                // 设置指定属性
                const attr = element.getAttribute('data-i18n-attr');
                element.setAttribute(attr, translation);
            } else if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
                // 输入框的 placeholder
                if (element.hasAttribute('placeholder')) {
                    element.placeholder = translation;
                } else {
                    element.value = translation;
                }
            } else {
                // 普通文本内容
                element.textContent = translation;
            }
        });

        // 翻译带有 data-i18n-placeholder 属性的元素（用于 placeholder）
        document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
            const key = element.getAttribute('data-i18n-placeholder');
            element.placeholder = getTranslation(key);
        });

        // 翻译带有 data-i18n-title 属性的元素（用于 title）
        document.querySelectorAll('[data-i18n-title]').forEach(element => {
            const key = element.getAttribute('data-i18n-title');
            element.title = getTranslation(key);
        });
    }

    // 初始化
    function init() {
        loadLanguageSetting();
        applyTranslations();
    }

    // 公共 API
    return {
        init,
        setLanguage,
        getTranslation,
        applyTranslations,
        getCurrentLanguage: () => currentLanguage,
        getSupportedLanguages: () => Object.keys(translations)
    };
})();

// DOM 加载完成后自动初始化
document.addEventListener('DOMContentLoaded', function() {
    I18N.init();
});
