/**
 * 配音制作模块
 * Dubbing Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.DubbingMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
        async loadDubbingStep() {
            const container = document.getElementById('dubbingContent');
            if (!container) return;

            // 🔥 统一数据源：复用视频步骤已加载的数据
            if (!this.shots || this.shots.length === 0) {
                // 如果视频步骤没有加载过，调用统一的数据加载方法
                await this.loadShotsData();
            }
            
            if (!this.shots || this.shots.length === 0) {
                console.log('⚠️ [配音] 没有可用的镜头数据');
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">🎙️</p>
                        <p>还没有分镜头数据</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">
                            请先在"分镜生成"步骤生成分镜头
                        </p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.goToStep('storyboard')" style="margin-top: 1rem;">
                            前往分镜生成
                        </button>
                    </div>
                `;
                return;
            }

            // 🔥 确保镜头按 episode_order 和 shot_number 排序
            this.shots.sort((a, b) => {
                // 首先按事件选择顺序
                const orderA = a.episode_order ?? 9999;
                const orderB = b.episode_order ?? 9999;
                if (orderA !== orderB) {
                    return orderA - orderB;
                }
                // 同一事件内按镜头编号排序
                const numA = parseInt(a.shot_number || a.scene_number) || 0;
                const numB = parseInt(b.shot_number || b.scene_number) || 0;
                return numA - numB;
            });
            console.log('🎙️ [配音] 镜头已按 episode_order 排序');

            // 🔥 加载角色数据
            if (!this.characters || this.characters.length === 0) {
                console.log('🎙️ [配音] 角色数据为空，正在加载...');
                await this.loadEventsAndCharacters();
            }

            // 🔥 提取所有有台词的角色（从镜头中提取）
            const speakerSet = new Set();
            this.shots.forEach(shot => {
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                const { speaker } = this.parseDialogue(dialogue);
                if (speaker && speaker !== '无' && speaker !== '未知') {
                    speakerSet.add(speaker);
                }
            });

            // 合并项目角色和台词中的角色
            const allSpeakers = new Set([...speakerSet]);
            this.characters.forEach(char => {
                if (char.name) allSpeakers.add(char.name);
            });

            // 🔥 构建角色-音色映射
            this.characterVoiceMap = {};
            allSpeakers.forEach(speaker => {
                // 从配置中查找匹配的音色
                let matchedVoice = this.characterVoices[speaker];

                // 如果没有直接匹配，尝试模糊匹配
                if (!matchedVoice) {
                    for (const [charName, voiceId] of Object.entries(this.characterVoices)) {
                        if (speaker.includes(charName) || charName.includes(speaker)) {
                            matchedVoice = voiceId;
                            break;
                        }
                    }
                }

                // 如果还没找到，使用默认音色
                if (!matchedVoice) {
                    matchedVoice = this.characterVoices['默认'] || 'female-qn-dahu';
                }

                this.characterVoiceMap[speaker] = matchedVoice;
            });

            console.log('🎙️ [配音] 角色-音色映射:', this.characterVoiceMap);

            // 检查TTS配置
            const ttsConfigResponse = await fetch('/api/tts/config');
            const ttsConfig = await ttsConfigResponse.json();
            const ttsConfigured = ttsConfig.success && ttsConfig.configured;

            // 🔥 获取当前配置的模型
            if (ttsConfig.model) {
                this.ttsModel = ttsConfig.model;
                console.log('🎙️ [配音] 当前TTS模型:', this.ttsModel);
            }

            // 🔥 展开对话场景为独立的配音子镜头
            const expandedDialogueShots = [];
            for (let i = 0; i < this.shots.length; i++) {
                const shot = this.shots[i];
                
                // 优先检查 dialogues 数组（多个对话）
                if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
                    // 🔥 初始化子镜头音频状态数组（如果不存在）
                    if (!shot._sub_audios || !Array.isArray(shot._sub_audios)) {
                        shot._sub_audios = new Array(shot.dialogues.length).fill(null);
                    }

                    // 对话场景：展开为多个子镜头
                    shot.dialogues.forEach((dlg, dlgIdx) => {
                        expandedDialogueShots.push({
                            ...shot,
                            // 保存原始索引和子镜头索引
                            _original_shot_index: i,
                            _sub_dialogue_index: dlgIdx,
                            // 覆盖对话数据
                            _dialogue_data: dlg,
                            dialogue: dlg.lines || dlg.speaker || '',
                            // 子镜头特定信息
                            dialogue_index: dlgIdx + 1,
                            dialogue_count: shot.dialogues.length,
                            // 保留原始场景信息用于显示
                            original_scene_number: shot.shot_number,
                            is_dialogue_scene: true,
                            // 🔥 使用原始shot的状态引用（双向绑定）
                            get audioUrl() { return shot._sub_audios?.[dlgIdx]?.audioUrl; },
                            get audio_path() { return shot._sub_audios?.[dlgIdx]?.audio_path; },
                            get audioDuration() { return shot._sub_audios?.[dlgIdx]?.audioDuration; },
                            get dubbingGenerating() { return shot._sub_audios?.[dlgIdx]?.dubbingGenerating || false; },
                            get dubbingError() { return shot._sub_audios?.[dlgIdx]?.dubbingError || false; },
                            set audioUrl(v) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                shot._sub_audios[dlgIdx].audioUrl = v;
                            },
                            set audio_path(v) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                shot._sub_audios[dlgIdx].audio_path = v;
                            },
                            set audioDuration(v) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                shot._sub_audios[dlgIdx].audioDuration = v;
                            },
                            set dubbingGenerating(v) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                shot._sub_audios[dlgIdx].dubbingGenerating = v;
                            },
                            set dubbingError(v) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                shot._sub_audios[dlgIdx].dubbingError = v;
                            }
                        });
                    });
                } else {
                    // 检查单个 dialogue 对象
                    const dialogue = shot._dialogue_data || shot.dialogue || {};
                    const { speaker, lines } = this.parseDialogue(dialogue);
                    
                    // 如果有有效台词（说话人不是"无"或"未知"，且有台词内容）
                    if (speaker && speaker !== '无' && speaker !== '未知' && lines && lines !== '无') {
                        // 初始化子镜头音频状态
                        if (!shot._sub_audios || !Array.isArray(shot._sub_audios)) {
                            shot._sub_audios = [null];
                        }
                        
                        // 添加原始索引
                        shot._original_shot_index = i;
                        shot._sub_dialogue_index = 0;
                        shot._dialogue_data = dialogue;
                        shot.dialogue_index = 1;
                        shot.dialogue_count = 1;
                        shot.original_scene_number = shot.shot_number;
                        shot.is_dialogue_scene = true;
                        
                        expandedDialogueShots.push(shot);
                    }
                }
            }

            // 检查已存在的音频文件
            await this.checkExistingAudio();

            // 🔥 保存展开后的镜头列表供后续使用
            this.expandedDubbingShots = expandedDialogueShots;
            console.log('🎙️ [配音] 展开后的镜头数量:', expandedDialogueShots.length);
            console.log('🎙️ [配音] 原始镜头数量:', this.shots.length);
            // 检查对话场景
            const dialogueScenes = expandedDialogueShots.filter(s => s.is_dialogue_scene);
            console.log('🎙️ [配音] 对话场景子镜头数量:', dialogueScenes.length);

            // 🔥 调试：打印展开镜头的 episode_title 和 episode_order
            console.log('🎙️ [配音] 展开镜头的事件顺序:');
            expandedDialogueShots.forEach((shot, idx) => {
                console.log(`  [${idx}] episode_title="${shot.episode_title}", episode_order=${shot.episode_order}, shot_number=${shot.shot_number}, dialogue="${shot._dialogue_data?.lines?.substring(0, 20)}..."`);
            });

            // 按事件分组
            const eventGroups = this.groupShotsByEvent(expandedDialogueShots);

            console.log('🎙️ [配音] 事件分组结果:');
            eventGroups.forEach((group, idx) => {
                console.log(`  组${idx}: ${group.eventName}, ${group.shots.length}个镜头`);
            });

            let scenesHtml = '';
            eventGroups.forEach((group, groupIdx) => {
                // 添加事件分隔线（第一个事件之前不添加）
                if (groupIdx > 0) {
                    scenesHtml += `
                        <div class="event-separator">
                            <div class="event-separator-line"></div>
                            <div class="event-separator-label">${group.eventName}</div>
                            <div class="event-separator-line"></div>
                        </div>
                    `;
                } else if (group.eventName) {
                    // 第一个事件也显示标签，但没有上面的分隔线
                    scenesHtml += `
                        <div class="event-separator first">
                            <div class="event-separator-label">${group.eventName}</div>
                        </div>
                    `;
                }

                // 渲染该事件的所有镜头，使用展开后的索引
                group.shots.forEach((shot) => {
                    // 🔥 在展开的镜头列表中查找索引
                    const expandedIdx = expandedDialogueShots.indexOf(shot);
                    console.log(`🎙️ [配音] 渲染镜头: scene=#${shot.shot_number}, expandedIdx=${expandedIdx}, dialogue="${shot._dialogue_data?.lines?.substring(0, 15)}..."`);
                    scenesHtml += this.renderDubbingScene(shot, expandedIdx);
                });
            });

            container.innerHTML = `
                <div class="dubbing-workspace">
                    <!-- 工具栏 -->
                    <div class="dubbing-toolbar">
                        <div class="dubbing-stats">
                            <span class="stat-item">共 ${expandedDialogueShots.length} 个镜头</span>
                            <span class="stat-item completed">已完成 ${expandedDialogueShots.filter(s => s.audioUrl || s.audio_path).length}</span>
                            <span class="stat-item pending">待生成 ${expandedDialogueShots.filter(s => !(s.audioUrl || s.audio_path)).length}</span>
                        </div>
                        <div class="toolbar-actions">
                            ${ttsConfigured ?
                                '<button class="toolbar-btn primary" onclick="shortDramaStudio.batchGenerateDubbing()"><span class="btn-icon">🎙️</span><span class="btn-text">全部生成配音</span></button>' :
                                '<button class="toolbar-btn warning" onclick="shortDramaStudio.showTTSConfig()"><span class="btn-icon">⚙️</span><span class="btn-text">配置API</span></button>'
                            }
                            <button class="toolbar-btn" onclick="shortDramaStudio.exportSubtitle()"><span class="btn-icon">📝</span><span class="btn-text">导出字幕</span></button>
                            <button class="toolbar-btn" onclick="shortDramaStudio.downloadAllAudio()"><span class="btn-icon">📦</span><span class="btn-text">打包下载</span></button>
                        </div>
                    </div>

                    <!-- 镜头列表 -->
                    <div class="dubbing-scene-list">
                        ${scenesHtml}
                    </div>
                </div>
            `;

            // 更新项目状态
            this.updateProjectStatus();
        },

        /**
         * 渲染单个配音场景（支持更新和返回模板）
         */
        renderDubbingScene(shot, idx) {
            const dialogue = shot._dialogue_data || shot.dialogue || {};
            const { speaker, lines, tone } = this.parseDialogue(dialogue);

            const hasAudio = shot.audioUrl || shot.audio_path;
            const isGenerating = shot.dubbingGenerating;
            const hasError = shot.dubbingError;

            // 状态样式和文字（与视频卡片保持一致）
            const statusClass = hasAudio ? 'done' : isGenerating ? 'processing' : hasError ? 'error' : 'pending';
            const statusText = hasAudio ? '已完成' : isGenerating ? '生成中...' : hasError ? '失败' : '待生成';

            // 获取事件名（从 episode_title 或 event_name）
            const eventName = shot.episode_title || shot.event_name || '';

            // 对话场景的序号显示
            const dialogueIndex = shot.dialogue_index;
            const dialogueCount = shot.dialogue_count;
            const dialogueLabel = (dialogueIndex && dialogueCount && dialogueCount > 1)
                ? `<span class="dialogue-index" style="font-size: 0.75rem; color: var(--primary); background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px; margin-left: 4px;">对话${dialogueIndex}/${dialogueCount}</span>`
                : '';

            // 场景号和镜头号显示
            const sceneNum = shot._scene_number || shot.scene_number || 1;
            const shotNum = shot.shot_number || (idx + 1);
            const shotLabel = `S${sceneNum}-#${shotNum}`;

            const innerHTML = `
                <div class="scene-header">
                    <span class="scene-number">${shotLabel}${dialogueLabel}</span>
                    ${eventName ? `<span class="scene-event" title="事件：${eventName}" style="font-size: 0.75rem; color: var(--accent); background: var(--bg-tertiary); padding: 2px 8px; border-radius: 4px;">📋 ${eventName.length > 12 ? eventName.substring(0, 12) + '...' : eventName}</span>` : ''}
                    <span class="scene-type">${shot.shot_type || '镜头'}</span>
                    <span class="scene-duration">⏱️ ${shot.duration || 5}秒</span>
                    <span class="task-status ${statusClass}">${statusText}</span>
                </div>

                <div class="scene-content">
                    <div class="scene-visual">
                        <div class="visual-label">🎬 画面</div>
                        <div class="visual-desc">${(shot.veo_prompt || shot.screen_action || '').substring(0, 100)}...</div>
                    </div>

                    <div class="scene-dialogue">
                        <div class="dialogue-label">💬 台词</div>
                        <div class="dialogue-speaker">${speaker}</div>
                        <div class="dialogue-lines">"${lines}"</div>
                        ${tone ? `<div class="dialogue-tone" style="font-size: 0.75rem; color: var(--text-tertiary);">🎭 ${tone}</div>` : ''}
                    </div>
                </div>

                <div class="scene-actions">
                    ${hasAudio ? `
                        <div class="audio-player-wrapper" style="width: 100%;">
                            <audio id="audio_${idx}" src="${shot.audioUrl}" controls style="width: 100%; height: 32px;"></audio>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 8px;">
                            <button class="scene-btn edit-btn" onclick="shortDramaStudio.editDubbing(${idx})">
                                <span>✏️</span> 编辑台词
                            </button>
                            <button class="scene-btn download-btn" onclick="shortDramaStudio.downloadAudio('${shot.audioUrl}', '${speaker}_S${sceneNum}_${shotNum}')">
                                <span>⬇️</span> 下载
                            </button>
                            <button class="scene-btn restore-btn" onclick="shortDramaStudio.showAudioRestoreModal(${idx})" title="还原备份">
                                <span>♻️</span> 还原
                            </button>
                            <button class="scene-btn regenerate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                                <span>🔄</span> 重生成
                            </button>
                        </div>
                    ` : isGenerating ? `
                        <div class="generating-status">生成中...</div>
                        <button class="scene-btn" disabled>请稍候...</button>
                    ` : hasError ? `
                        <button class="scene-btn generate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                            <span>🔄</span> 重试
                        </button>
                    ` : `
                        <button class="scene-btn generate-btn" onclick="shortDramaStudio.generateDubbing(${idx})">
                            <span>🎙️</span> 生成配音
                        </button>
                    `}
                </div>
            `;

            // 如果元素存在，更新它；否则返回模板字符串
            const sceneEl = document.getElementById(`dubbingScene_${idx}`);
            if (sceneEl) {
                sceneEl.innerHTML = innerHTML;
                // 更新状态类
                sceneEl.classList.remove('generating', 'error', 'done', 'pending');
                if (isGenerating) {
                    sceneEl.classList.add('generating');
                } else if (hasError) {
                    sceneEl.classList.add('error');
                } else if (hasAudio) {
                    sceneEl.classList.add('done');
                } else {
                    sceneEl.classList.add('pending');
                }
                return;
            }

            // 返回带外层div的模板字符串（用于初始渲染）
            const initialClass = isGenerating ? 'generating' : hasError ? 'error' : hasAudio ? 'done' : 'pending';
            return `
                <div class="dubbing-scene ${initialClass}" id="dubbingScene_${idx}" data-idx="${idx}">
                    ${innerHTML}
                </div>
            `;
        }

        /**
         * 更新配音统计数字
         */
        updateDubbingStats() {

        updateDubbingStats() {
            const dialogueShots = this.shots.filter(shot => {
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                if (typeof dialogue === 'string') return dialogue.trim();
                if (typeof dialogue === 'object') {
                    const speaker = dialogue.speaker || '';
                    const lines = dialogue.lines || '';
                    return speaker && speaker !== '无' && lines;
                }
                return false;
            });

            const completedCount = dialogueShots.filter(s => s.audioUrl || s.audio_path).length;
            const pendingCount = dialogueShots.filter(s => !(s.audioUrl || s.audio_path)).length;
            const totalCount = dialogueShots.length;

            const statsContainer = document.querySelector('.dubbing-stats');
            if (statsContainer) {
                statsContainer.innerHTML = `
                    <span class="stat-item">共 ${totalCount} 个镜头</span>
                    <span class="stat-item completed">已完成 ${completedCount}</span>
                    <span class="stat-item pending">待生成 ${pendingCount}</span>
                `;
            }
        }

        /**
         * 清除步骤缓存（用于数据更新后强制刷新）
         */
        invalidateStepCache(step = null) {
            if (!this.loadedSteps) return;
    };
}));
