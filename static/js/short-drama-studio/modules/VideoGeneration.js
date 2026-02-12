/**
 * 视频生成模块
 * Video Generation Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.VideoGenerationMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
    async loadVideoStep() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>加载分镜头数据...</p></div>';

        // 调用统一的数据加载方法
        const allShots = await this.loadShotsData();

        if (allShots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
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

        console.log('✅ [视频步骤] 最终加载的镜头数:', this.shots.length);

        container.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>检查视频文件...</p></div>';

        // 检查已存在的视频
        await this.checkExistingVideos();

        // 渲染视频卡片
        this.renderVideoCards();
    },

    async checkExistingVideos() {
        const episodeDirectoryName = this.getEpisodeDirectoryName();

        console.log('🎬 [视频检查] 开始检查视频...');
        console.log('🎬 [视频检查] Episode:', episodeDirectoryName);
        console.log('🎬 [视频检查] Shots数量:', this.shots.length);

        try {
            // 使用新的API列出视频文件
            const response = await fetch(`/api/short-drama/list-videos?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            console.log('🎬 [视频检查] API返回的视频:', data.videos);

            // 🔥 详细打印每个视频的信息
            if (data.videos && data.videos.length > 0) {
                console.log('🎬 [视频检查] 视频文件详情:');
                data.videos.forEach((video, idx) => {
                    console.log(`   [${idx}] ${video.filename}`);
                    console.log(`       scene_number=${video.scene_number}, episode_name="${video.episode_name}", shot_type="${video.shot_type}", is_dialogue=${video.is_dialogue_scene}`);
                });
            }

            if (data.videos && data.videos.length > 0) {
                // 🔥 先重置所有镜头的videoExists标志
                for (let i = 0; i < this.shots.length; i++) {
                    this.shots[i].videoExists = false;
                    this.shots[i].videoPath = null;
                    this.shots[i].videoUrl = null;
                }

                // 🔥 按episode_title分组统计
                const episodeStats = {};
                for (const shot of this.shots) {
                    const ep = shot.episode_title || 'unknown';
                    if (!episodeStats[ep]) episodeStats[ep] = 0;
                    episodeStats[ep]++;
                }
                console.log('📊 Shots按episode分组:', episodeStats);

                // 为每个镜头匹配视频
                let matchedCount = 0;
                for (let i = 0; i < this.shots.length; i++) {
                    const shot = this.shots[i];
                    const episodeTitle = shot.episode_title || '';
                    const shotNumber = shot.shot_number || (i + 1);
                    const sceneNumber = shot.scene_number || 1;
                    const shotType = shot.shot_type || '';

                    console.log(`🔍 镜头 #${i + 1}: episode="${episodeTitle}", scene_number=${sceneNumber}, shot_number=${shotNumber}, shot_type="${shotType}"`);

                    // 🔥 在所有视频中查找匹配的视频
                    let matchedVideo = null;
                    for (const video of data.videos) {
                        // 新格式视频有 episode_name 和 scene_number 字段
                        const videoEpisodeName = video.episode_name || video.storyboard_key || '';
                        const videoSceneNum = video.scene_number || 0;
                        const videoShotType = video.shot_type || '';
                        const videoIsDialogue = video.is_dialogue_scene;

                        console.log(`   🔍 检查视频: scene_number=${videoSceneNum}, event="${videoEpisodeName}", shot_type="${videoShotType}", is_dialogue=${videoIsDialogue}`);

                        // 🔥 优先使用 scene_number 匹配（最可靠）
                        if (videoSceneNum === sceneNumber) {
                            // 再检查事件名是否匹配（包含关系即可）
                            const eventMatches = videoEpisodeName.includes(episodeTitle) ||
                                                 episodeTitle.includes(videoEpisodeName) ||
                                                 videoEpisodeName === episodeTitle;
                            if (eventMatches) {
                                matchedVideo = video;
                                console.log(`   ✅ 匹配成功! scene_number=${sceneNumber}, event="${videoEpisodeName}"`);
                                break;
                            } else {
                                console.log(`   ⚠️ scene_number匹配但事件名不匹配: video event="${videoEpisodeName}", shot event="${episodeTitle}"`);
                            }
                        }
                    }

                    if (matchedVideo) {
                        shot.videoExists = true;
                        shot.videoPath = matchedVideo.path;
                        shot.videoUrl = matchedVideo.url;
                        matchedCount++;
                        console.log(`✅ 镜头 #${i + 1} 视频已存在: ${matchedVideo.filename}`);
                    } else {
                        console.log(`⭕ 镜头 #${i + 1} 无视频`);
                    }
                }
                console.log(`🎬 匹配完成: ${matchedCount}/${this.shots.length} 个镜头有视频`);
            } else {
                console.log('🎬 没有找到已存在的视频');
            }
        } catch (e) {
            console.error('检查视频失败:', e);
        }
    },

    async checkExistingAudio() {
        const episodeDirectoryName = this.getEpisodeDirectoryName();

        console.log('🎙️ [音频检查] 开始检查音频...');
        console.log('🎙️ [音频检查] Episode:', episodeDirectoryName);

        try {
            // 调用API列出音频文件
            const response = await fetch(`/api/tts/list-audio?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
            const data = await response.json();

            console.log('🎙️ [音频检查] API返回的音频:', data.audios);
            console.log('🎙️ [音频检查] 音频文件详情:');
            data.audios.forEach((audio, idx) => {
                console.log(`   [${idx}] ${audio.filename}`);
                console.log(`       scene_number=${audio.scene_number}, event_name="${audio.event_name}", speaker="${audio.speaker}"`);
            });

            // 打印所有镜头信息用于对比
            console.log('🎙️ [音频检查] 镜头信息:');
            for (let i = 0; i < this.shots.length; i++) {
                const shot = this.shots[i];
                const episodeTitle = shot.episode_title || '';
                const shotNumber = shot.shot_number || (i + 1);
                const dialogue = shot._dialogue_data || shot.dialogue || {};
                const { speaker } = this.parseDialogue(dialogue);
                const isDialogueScene = shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues);
                console.log(`   [${i}] shot_number=${shotNumber}, episode="${episodeTitle}", speaker="${speaker}", isDialogueScene=${isDialogueScene}`);
                if (isDialogueScene) {
                    shot.dialogues.forEach((dlg, dlgIdx) => {
                        const { speaker: dlgSpeaker } = this.parseDialogue(dlg);
                        console.log(`       对话${dlgIdx + 1}: speaker="${dlgSpeaker}"`);
                    });
                }
            }

            // 先重置所有镜头的音频状态
            for (let i = 0; i < this.shots.length; i++) {
                this.shots[i].audioUrl = null;
                this.shots[i].audio_path = null;
                // 重置子镜头音频状态
                if (this.shots[i]._sub_audios) {
                    this.shots[i]._sub_audios = new Array(this.shots[i]._sub_audios.length).fill(null);
                }
            }

            if (data.audios && data.audios.length > 0) {
                // 为每个镜头匹配音频（使用和视频一样的匹配逻辑）
                let matchedCount = 0;
                console.log('🎙️ [音频检查] 开始匹配镜头...');
                for (let i = 0; i < this.shots.length; i++) {
                    const shot = this.shots[i];
                    const episodeTitle = shot.episode_title || '';
                    const sceneNumber = shot.scene_number || 1;

                    console.log(`🎙️ [镜头 #${i + 1}] scene_number=${sceneNumber}, episode="${episodeTitle}"`);

                    // 检查是否是对话场景
                    if (shot.is_dialogue_scene && shot.dialogues && Array.isArray(shot.dialogues)) {
                        // 对话场景：遍历每个子对话
                        for (let dlgIdx = 0; dlgIdx < shot.dialogues.length; dlgIdx++) {
                            const dlg = shot.dialogues[dlgIdx];
                            const { speaker } = this.parseDialogue(dlg);
                            const dialogueIndex = dlgIdx + 1;

                            console.log(`   🔍 对话${dialogueIndex}: speaker="${speaker}"`);

                            // 🔥 优先使用 scene_number 匹配（最可靠）
                            let matchedAudio = null;
                            for (const audio of data.audios) {
                                const audioSceneNum = audio.scene_number || 0;
                                const audioEventName = audio.event_name || '';
                                const audioSpeaker = audio.speaker || '';
                                const audioDialogueIdx = audio.dialogue_idx || 1;

                                // 优先使用 scene_number 匹配
                                if (audioSceneNum === sceneNumber) {
                                    // 再检查事件名和说话人是否匹配（使用包含关系）
                                    const eventMatches = audioEventName.includes(episodeTitle) ||
                                                         episodeTitle.includes(audioEventName) ||
                                                         audioEventName === episodeTitle;
                                    const speakerMatches = audioSpeaker === speaker || audioSpeaker.includes(speaker) || speaker.includes(audioSpeaker);

                                    if (eventMatches && speakerMatches && audioDialogueIdx === dialogueIndex) {
                                        matchedAudio = audio;
                                        console.log(`      ✅ ${audio.filename} (scene_number=${audioSceneNum})`);
                                        break;
                                    }
                                }
                            }

                            if (matchedAudio) {
                                if (!shot._sub_audios) shot._sub_audios = [];
                                if (!shot._sub_audios[dlgIdx]) shot._sub_audios[dlgIdx] = {};
                                const timestamp = Date.now();
                                shot._sub_audios[dlgIdx].audioUrl = matchedAudio.url + (matchedAudio.url.includes('?') ? '&' : '?') + 't=' + timestamp;
                                shot._sub_audios[dlgIdx].audio_path = matchedAudio.path;
                                matchedCount++;
                            } else {
                                console.log(`      ❌ 无匹配`);
                            }
                        }
                    } else {
                        // 普通镜头：单个音频
                        const dialogue = shot._dialogue_data || shot.dialogue || {};
                        const { speaker } = this.parseDialogue(dialogue);

                        console.log(`   🔍 speaker="${speaker}"`);

                        // 🔥 优先使用 scene_number 匹配（最可靠）
                        let matchedAudio = null;
                        for (const audio of data.audios) {
                            const audioSceneNum = audio.scene_number || 0;
                            const audioEventName = audio.event_name || '';
                            const audioSpeaker = audio.speaker || '';

                            // 优先使用 scene_number 匹配
                            if (audioSceneNum === sceneNumber) {
                                // 再检查事件名和说话人是否匹配（使用包含关系）
                                const eventMatches = audioEventName.includes(episodeTitle) ||
                                                     episodeTitle.includes(audioEventName) ||
                                                     audioEventName === episodeTitle;
                                const speakerMatches = audioSpeaker === speaker || audioSpeaker.includes(speaker) || speaker.includes(audioSpeaker);

                                if (eventMatches && speakerMatches) {
                                    matchedAudio = audio;
                                    console.log(`   ✅ ${audio.filename} (scene_number=${audioSceneNum})`);
                                    break;
                                }
                            }
                        }

                        if (matchedAudio) {
                            const timestamp = Date.now();
                            shot.audioUrl = matchedAudio.url + (matchedAudio.url.includes('?') ? '&' : '?') + 't=' + timestamp;
                            shot.audio_path = matchedAudio.path;
                            matchedCount++;
                        } else {
                            console.log(`   ❌ 无匹配`);
                        }
                    }
                }
                console.log(`🎙️ [音频检查] 匹配完成: ${matchedCount} 个音频文件已匹配`);
            } else {
                console.log('🎙️ [音频检查] 没有找到已存在的音频');
            }
        } catch (e) {
            console.error('检查音频失败:', e);
        }
    },

    renderVideoCards() {
        const container = document.getElementById('videoContent');
        if (!container) return;

        console.log(`🎬 渲染视频卡片, shots数量: ${this.shots?.length || 0}`);
        console.log(`🎬 this.shots内容:`, this.shots);

        if (!this.shots || this.shots.length === 0) {
            console.error('❌ this.shots为空或未定义');
            container.innerHTML = `
                <div class="empty-state">
                    <p style="font-size: 2rem;">🎬</p>
                    <p>没有分镜头数据</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary);">
                        请先在"分镜头"步骤生成分镜头
                    </p>
                </div>
            `;
            return;
        }

        const completedCount = this.shots.filter(s => s.videoExists).length;
        const totalCount = this.shots.length;

        // 按事件分组
        const eventGroups = this.groupShotsByEvent(this.shots);

        console.log(`📊 分组数量: ${eventGroups.length}`);
        eventGroups.forEach((g, i) => console.log(`  组${i}: ${g.eventName}, ${g.shots.length}个镜头`));

        let rowsHtml = '';
        eventGroups.forEach((group, groupIdx) => {
            // 添加事件分隔线（第一个事件之前不添加）
            if (groupIdx > 0) {
                rowsHtml += `
                    <div class="event-separator">
                        <div class="event-separator-line"></div>
                        <div class="event-separator-label">${group.eventName}</div>
                        <div class="event-separator-line"></div>
                    </div>
                `;
            } else if (group.eventName) {
                // 第一个事件也显示标签，但没有上面的分隔线
                rowsHtml += `
                    <div class="event-separator first">
                        <div class="event-separator-label">${group.eventName}</div>
                    </div>
                `;
            }

            // 渲染该事件的所有镜头
            group.shots.forEach(shot => {
                const idx = this.shots.indexOf(shot);
                rowsHtml += this.renderVideoTaskRow(shot, idx);
            });
        });

        container.innerHTML = `
            <div class="video-workspace">
                <div class="video-toolbar">
                    <div class="video-stats">
                        <span class="stat-item">共 ${totalCount} 个镜头</span>
                        <span class="stat-item completed">已完成 ${completedCount}</span>
                        <span class="stat-item pending">待生成 ${totalCount - completedCount}</span>
                    </div>
                    <div class="toolbar-actions">
                        <button class="toolbar-btn" onclick="shortDramaStudio.refreshVideos()">
                            <span class="btn-icon">🔄</span>
                            <span class="btn-text">刷新</span>
                        </button>
                        <button class="toolbar-btn" onclick="shortDramaStudio.runQualityCheck()">
                            <span class="btn-icon">📋</span>
                            <span class="btn-text">剧本质量检查</span>
                        </button>
                        <button class="toolbar-btn primary" onclick="shortDramaStudio.batchGenerateFirstFive()">
                            <span class="btn-icon">🚀</span>
                            <span class="btn-text">批量生成（前5个）</span>
                        </button>
                    </div>
                </div>
                <div class="video-task-list">
                    ${rowsHtml}
                </div>
            </div>
        `;
    },

    renderVideoTaskRow(shot, idx) {
        const isCompleted = shot.videoExists;
        const isGenerating = shot.generating;
        const hasError = shot.hasError;

        const statusClass = isCompleted ? 'done' : isGenerating ? 'processing' : hasError ? 'error' : 'pending';
        const statusText = isCompleted ? '已完成' : isGenerating ? '生成中...' : hasError ? '失败' : '待生成';

        // 🔥 获取错误信息
        const errorMessage = shot.errorMessage || '';
        const hasErrorMessage = hasError && errorMessage;

        // 参考图缩略图
        const referenceImages = shot.reference_images || [];
        const hasRefs = referenceImages.length > 0;

        // 🔥 获取台词信息（支持dialogues数组和dialogue对象）
        let hasDialogue = false;
        let dialogueDisplayHtml = '';

        // 检查是否是对话场景（dialogues数组）
        if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
            hasDialogue = true;
            const firstLines = shot.dialogues.slice(0, 2).map(d =>
                `${d.speaker}: ${d.lines?.substring(0, 20) || ''}${d.lines?.length > 20 ? '...' : ''}`
            ).join('\n');
            const count = shot.dialogues.length;
            dialogueDisplayHtml = `
                <div class="task-dialogue">
                    <span class="prompt-label">💬 对话:</span>
                    <span class="dialogue-text">${firstLines}${count > 2 ? `\n... 等 ${count} 句` : ''}</span>
                </div>
            `;
        } else {
            // 普通单个对话
            const dialogueData = shot._dialogue_data || shot.dialogue;
            if (dialogueData && dialogueData.speaker && dialogueData.speaker !== '无') {
                hasDialogue = true;
                dialogueDisplayHtml = `
                    <div class="task-dialogue">
                        <span class="prompt-label">💬 台词:</span>
                        <span class="dialogue-text">${dialogueData.speaker}: ${dialogueData.lines?.substring(0, 50) || ''}${dialogueData.lines?.length > 50 ? '...' : ''}</span>
                        ${dialogueData.tone ? `<span class="dialogue-tone">(${dialogueData.tone})</span>` : ''}
                    </div>
                `;
            }
        }

        // 生成参考图缩略图HTML（仅在有参考图时）
        const refsThumbnailsHtml = hasRefs ? referenceImages.map(img => `
            <div class="ref-thumb" onclick="event.stopPropagation(); shortDramaStudio.showImagePreview('${img}')">
                <img src="${img}" alt="参考图">
            </div>
        `).join('') : '';

        // 视频预览（如果已完成）
        const videoPreviewHtml = isCompleted && shot.videoUrl
            ? `<div class="task-video-preview" onclick="shortDramaStudio.previewVideo(${idx})">
                <video src="${shot.videoUrl}" muted preload="metadata"></video>
                <span class="play-icon">▶</span>
               </div>`
            : `<div class="task-video-placeholder">${isGenerating ? '<span class="spinner"></span>' : '⏳'}</div>`;

        // 🔥 检查是否支持多模式（数据流A）
        const hasMultipleModes = shot.veo_prompt_standard && shot.veo_prompt_reference && shot.veo_prompt_frames;
        const currentMode = shot.preferred_mode || 'standard';

        // 🔥 根据当前模式获取提示词
        const currentPrompt = this.getCurrentVeoPrompt(shot);
        const currentVisualDesc = this.getCurrentVisualDescription(shot);

        // 🔥 模式选择器HTML（仅在支持多模式时显示）
        const modeSelectorHtml = hasMultipleModes ? `
            <div class="task-mode-selector" style="margin-bottom: 0.5rem;">
                <span class="prompt-label">🎨 模式:</span>
                <select id="mode-select-${idx}" onchange="shortDramaStudio.updateShotMode(${idx})"
                        style="font-size: 0.75rem; padding: 0.25rem 0.5rem; border-radius: 0.25rem; background: rgba(0,0,0,0.3); color: var(--text-primary); border: 1px solid rgba(255,255,255,0.1);">
                    <option value="standard" ${currentMode === 'standard' ? 'selected' : ''}>标准模式</option>
                    <option value="reference" ${currentMode === 'reference' ? 'selected' : ''}>参考图模式</option>
                    <option value="frames" ${currentMode === 'frames' ? 'selected' : ''}>首尾帧模式</option>
                </select>
            </div>
        ` : '';

        return `
            <div class="task-row ${statusClass}" id="taskRow_${idx}">
                <div class="task-index">S${shot.scene_number || 1}-#${shot.shot_number || 1}</div>
                <div class="task-content">
                    ${modeSelectorHtml}
                    <div class="task-prompt">
                        <span class="prompt-label">画面描述:</span>
                        <span class="prompt-text" id="prompt-text-${idx}">${(currentVisualDesc || shot.visual_description || shot.screen_action || '').substring(0, 150)}${(currentVisualDesc || shot.visual_description || shot.screen_action || '').length > 150 ? '...' : ''}</span>
                    </div>
                    ${shot.plot_content ? `
                    <div class="task-plot">
                        <span class="plot-label">📖 情节:</span>
                        <span class="plot-text">${shot.plot_content.substring(0, 150)}${shot.plot_content.length > 150 ? '...' : ''}</span>
                    </div>
                    ` : ''}
                    ${hasDialogue ? dialogueDisplayHtml : ''}
                    ${hasErrorMessage ? `
                    <div class="task-error" style="
                        background: var(--danger-bg, rgba(239, 68, 68, 0.1));
                        border-left: 3px solid var(--danger);
                        padding: 0.5rem 0.75rem;
                        border-radius: 4px;
                        margin-top: 0.5rem;
                    ">
                        <span class="error-label" style="color: var(--danger); font-weight: 500;">❌ 错误原因:</span>
                        <span class="error-text" style="color: var(--text-secondary); margin-left: 0.5rem;">${errorMessage}</span>
                    </div>
                    ` : ''}
                    <div class="task-meta">
                        <span class="meta-tag">${shot.shot_type || '镜头'}</span>
                        <span class="meta-tag">⏱️ ${shot.duration || 5}秒</span>
                        ${isCompleted ? '<span class="meta-tag success">📸 ' + referenceImages.length + '张参考</span>' : ''}
                    </div>
                    ${isCompleted && hasRefs ? `
                    <div class="task-refs">
                        <span class="refs-label">参考图:</span>
                        <div class="refs-thumbnails">${refsThumbnailsHtml}</div>
                    </div>
                    ` : ''}
                </div>
                <div class="task-visual">
                    ${hasRefs ? `<div class="refs-thumbnails">${refsThumbnailsHtml}</div>` : '<div class="task-visual-empty"></div>'}
                    ${hasRefs ? '<span class="visual-arrow">→</span>' : ''}
                    ${videoPreviewHtml}
                </div>
                <div class="task-actions">
                    <button class="task-btn" onclick="shortDramaStudio.showBilingualPromptModal(${idx})" title="编辑中英文提示词" style="font-size: 11px; font-weight: bold; color: #6366f1;">EN</button>
                    ${isCompleted ? `
                    <button class="task-btn view-btn" onclick="shortDramaStudio.previewVideo(${idx})" title="查看视频">
                        <span>👁️</span>
                    </button>
                    <button class="task-btn restore-btn" onclick="shortDramaStudio.showVideoRestoreModal(${idx})" title="还原备份">
                        <span>♻️</span>
                    </button>
                    <button class="task-btn retry-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="重新生成">
                        <span>🔄</span>
                    </button>
                    ` : `
                    <button class="task-btn generate-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="生成视频">
                        <span>🎬</span>
                    </button>
                    `}
                    ${hasError ? `<button class="task-btn retry-btn" onclick="shortDramaStudio.generateShotVideo(${idx})" title="重试"><span>🔄</span></button>` : ''}
                </div>
                <div class="task-status">
                    <span class="status-dot ${statusClass}"></span>
                    <span class="status-text">${statusText}</span>
                </div>
            </div>
        `;
    },

    getCurrentVisualDescription(shot) {
        const mode = shot.preferred_mode || 'standard';
        if (mode === 'reference' && shot.visual_description_reference) {
            return shot.visual_description_reference;
        }
        if (mode === 'frames' && shot.visual_description_frames) {
            return shot.visual_description_frames;
        }
        return shot.visual_description_standard || shot.visual_description || shot.screen_action || '';
    },

    getCurrentVeoPrompt(shot) {
        const mode = shot.preferred_mode || 'standard';
        if (mode === 'reference' && shot.veo_prompt_reference) {
            return shot.veo_prompt_reference;
        }
        if (mode === 'frames' && shot.veo_prompt_frames) {
            return shot.veo_prompt_frames;
        }
        return shot.veo_prompt_standard || shot.veo_prompt || '';
    },

    async refreshVideos() {
        this.invalidateStepCache('video');
        this.loadedSteps?.delete('video');
        await this.loadVideoStep();
        this.showToast('已刷新视频状态', 'success');
    },

    updateVideoCard(shotIndex) {
        const row = document.getElementById(`taskRow_${shotIndex}`);
        const shot = this.shots[shotIndex];

        console.log(`🎬 [更新卡片] shotIndex=${shotIndex}, row存在=${!!row}, shot.videoExists=${shot?.videoExists}, shot.generating=${shot?.generating}`);

        if (row && shot) {
            row.outerHTML = this.renderVideoTaskRow(shot, shotIndex);
        } else if (shot && shot.videoExists) {
            console.warn(`🎬 [更新卡片] 找不到行元素 taskRow_${shotIndex}, 但视频已生成`);
            // 尝试重新渲染整个视频列表
            this.renderVideoCards();
        } else {
            console.warn(`🎬 [更新卡片] row不存在, shot=${shot ? '存在但未完成' : '不存在'}`);
        }
    },

    previewVideo(idx) {
        const shot = this.shots[idx];
        if (!shot || !shot.videoUrl) {
            this.showToast('视频不存在', 'error');
            return;
        }

        // 创建预览弹窗
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-secondary);
                border-radius: 16px;
                width: 90%;
                max-width: 600px;
                padding: 24px;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                    <h3 style="margin: 0;">🎬 镜头 #${shot.shot_number || (idx + 1)}</h3>
                    <button onclick="this.closest('.video-preview-modal')?.remove()" style="
                        background: none;
                        border: none;
                        font-size: 1.5rem;
                        cursor: pointer;
                        color: var(--text-secondary);
                    ">×</button>
                </div>
                <div style="
                    background: var(--bg-dark);
                    border-radius: 12px;
                    overflow: hidden;
                    aspect-ratio: 9/16;
                    margin-bottom: 16px;
                ">
                    <video src="${shot.videoUrl}" controls autoplay loop style="width: 100%; height: 100%;"></video>
                </div>
                <div style="display: flex; gap: 12px; justify-content: center;">
                    <button onclick="shortDramaStudio.downloadVideo('${shot.videoUrl}')" style="
                        padding: 12px 24px;
                        background: var(--bg-tertiary);
                        border: 1px solid var(--border);
                        border-radius: 8px;
                        cursor: pointer;
                    ">📥 下载</button>
                    <button onclick="this.closest('.video-preview-modal')?.remove(); shortDramaStudio.regenerateVideo(${idx});" style="
                        padding: 12px 24px;
                        background: var(--warning);
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                    ">🔄 重新生成</button>
                    <button onclick="this.closest('.video-preview-modal')?.remove()" style="
                        padding: 12px 24px;
                        background: var(--primary);
                        border: none;
                        border-radius: 8px;
                        cursor: pointer;
                    ">关闭</button>
                </div>
            </div>
        `;

        modal.className = 'video-preview-modal';
        document.body.appendChild(modal);

        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    },

    async downloadVideo(videoUrl) {
        try {
            const response = await fetch(videoUrl);
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `video_${Date.now()}.mp4`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            this.showToast('下载开始', 'success');
        } catch (error) {
            console.error('下载失败:', error);
            this.showToast('下载失败', 'error');
        }
    },

    closeVideoProgressModal(shotIndex = null) {
        if (shotIndex !== null) {
            // 只关闭特定任务的弹窗
            const modal = document.getElementById(`videoProgressModal_${shotIndex}`);
            if (modal) modal.remove();
        } else {
            // 关闭所有进度弹窗
            document.querySelectorAll('[id^="videoProgressModal_"]').forEach(modal => modal.remove());
            // 兼容旧的 ID
            const oldModal = document.getElementById('videoProgressModal');
            if (oldModal) oldModal.remove();
        }
    },

    stopBatchGeneration() {
        this.stopBatchGeneration = true;
    },

    /**
     * 显示中英文提示词对照编辑弹窗
     */
    showBilingualPromptModal(idx) {
        console.log(`🖊️ [EN弹窗] 点击索引: ${idx}, shots数量: ${this.shots?.length || 0}`);
        const shot = this.shots[idx];
        if (!shot) {
            console.error(`❌ [EN弹窗] 找不到镜头: idx=${idx}, shots=${this.shots?.length}`);
            this.showToast('找不到镜头数据', 'error');
            return;
        }

        const mode = shot.preferred_mode || 'standard';
        const modeNames = {
            'standard': '标准模式',
            'reference': '参考图模式',
            'frames': '首尾帧模式'
        };

        // 获取当前模式的中英文提示词
        let veoPrompt, visualDesc;
        if (mode === 'reference') {
            veoPrompt = shot.veo_prompt_reference || shot.veo_prompt || '';
            visualDesc = shot.visual_description_reference || shot.visual_description || '';
        } else if (mode === 'frames') {
            veoPrompt = shot.veo_prompt_frames || shot.veo_prompt || '';
            visualDesc = shot.visual_description_frames || shot.visual_description || '';
        } else {
            veoPrompt = shot.veo_prompt_standard || shot.veo_prompt || '';
            visualDesc = shot.visual_description_standard || shot.visual_description || '';
        }

        // 创建弹窗
        const modal = document.createElement('div');
        modal.id = 'bilingualPromptModal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        `;

        modal.innerHTML = `
            <div style="
                background: var(--bg-secondary, #1e1e2e);
                border-radius: 12px;
                width: 90%;
                max-width: 900px;
                max-height: 85vh;
                overflow: hidden;
                display: flex;
                flex-direction: column;
            ">
                <!-- 头部 -->
                <div style="
                    padding: 16px 20px;
                    border-bottom: 1px solid var(--border, #333);
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                ">
                    <div>
                        <h3 style="margin: 0; color: #fff; font-size: 1.1rem;">编辑提示词 - S${shot.scene_number || 1}#${shot.shot_number || idx+1}</h3>
                        <span style="color: #6366f1; font-size: 0.85rem;">${modeNames[mode]}</span>
                    </div>
                    <button onclick="document.getElementById('bilingualPromptModal').remove()" style="
                        background: none;
                        border: none;
                        color: #888;
                        font-size: 1.5rem;
                        cursor: pointer;
                    ">×</button>
                </div>

                <!-- 内容区 -->
                <div style="padding: 20px; overflow-y: auto; flex: 1;">
                    <!-- 中文视觉描述 -->
                    <div style="margin-bottom: 20px;">
                        <label style="
                            display: block;
                            color: #10b981;
                            font-size: 0.85rem;
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">🇨🇳 中文视觉描述 (Visual Description)</label>
                        <textarea id="bilingual-visual-desc" style="
                            width: 100%;
                            min-height: 80px;
                            padding: 12px;
                            background: var(--bg-dark, #0f0f1a);
                            border: 1px solid var(--border, #333);
                            border-radius: 8px;
                            color: #fff;
                            font-size: 0.9rem;
                            line-height: 1.5;
                            resize: vertical;
                        " placeholder="中文画面描述...">${visualDesc}</textarea>
                        <div style="color: #888; font-size: 0.75rem; margin-top: 4px;">用于前端显示，帮助理解画面内容</div>
                    </div>

                    <!-- 英文VEO提示词 -->
                    <div style="margin-bottom: 20px;">
                        <label style="
                            display: block;
                            color: #6366f1;
                            font-size: 0.85rem;
                            font-weight: 600;
                            margin-bottom: 8px;
                        ">🇺🇸 英文VEO提示词 (Video Prompt)</label>
                        <textarea id="bilingual-veo-prompt" style="
                            width: 100%;
                            min-height: 120px;
                            padding: 12px;
                            background: var(--bg-dark, #0f0f1a);
                            border: 1px solid var(--border, #333);
                            border-radius: 8px;
                            color: #fff;
                            font-size: 0.9rem;
                            line-height: 1.5;
                            resize: vertical;
                            font-family: monospace;
                        " placeholder="英文视频生成提示词...">${veoPrompt}</textarea>
                        <div style="color: #888; font-size: 0.75rem; margin-top: 4px;">发送给VEO/AI视频生成模型的提示词</div>
                    </div>

                    <!-- 其他信息 -->
                    <div style="
                        background: rgba(99, 102, 241, 0.1);
                        padding: 12px;
                        border-radius: 8px;
                        font-size: 0.8rem;
                        color: #888;
                    ">
                        <div style="margin-bottom: 4px;"><strong>镜头类型:</strong> ${shot.shot_type || 'N/A'}</div>
                        <div style="margin-bottom: 4px;"><strong>时长:</strong> ${shot.duration || 5}秒</div>
                        ${shot.scene_title ? `<div><strong>场景:</strong> ${shot.scene_title}</div>` : ''}
                    </div>
                </div>

                <!-- 底部按钮 -->
                <div style="
                    padding: 16px 20px;
                    border-top: 1px solid var(--border, #333);
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                ">
                    <button onclick="document.getElementById('bilingualPromptModal').remove()" style="
                        padding: 10px 20px;
                        background: transparent;
                        border: 1px solid var(--border, #333);
                        border-radius: 8px;
                        color: #888;
                        cursor: pointer;
                        font-size: 0.9rem;
                    ">取消</button>
                    <button onclick="shortDramaStudio.saveBilingualPrompt(${idx})" style="
                        padding: 10px 24px;
                        background: linear-gradient(135deg, #6366f1, #8b5cf6);
                        border: none;
                        border-radius: 8px;
                        color: #fff;
                        cursor: pointer;
                        font-size: 0.9rem;
                        font-weight: 600;
                    ">保存</button>
                </div>
            </div>
        `;

        document.body.appendChild(modal);
    },

    /**
     * 保存中英文提示词
     */
    saveBilingualPrompt(idx) {
        const shot = this.shots[idx];
        if (!shot) return;

        const visualDesc = document.getElementById('bilingual-visual-desc').value.trim();
        const veoPrompt = document.getElementById('bilingual-veo-prompt').value.trim();

        if (!visualDesc && !veoPrompt) {
            this.showToast('提示词不能为空', 'warning');
            return;
        }

        const mode = shot.preferred_mode || 'standard';

        // 根据当前模式保存到对应的字段
        if (mode === 'reference') {
            shot.visual_description_reference = visualDesc;
            shot.veo_prompt_reference = veoPrompt;
        } else if (mode === 'frames') {
            shot.visual_description_frames = visualDesc;
            shot.veo_prompt_frames = veoPrompt;
        } else {
            shot.visual_description_standard = visualDesc;
            shot.veo_prompt_standard = veoPrompt;
        }

        // 同时更新兼容字段
        shot.visual_description = visualDesc;
        shot.veo_prompt = veoPrompt;

        // 关闭弹窗
        const modal = document.getElementById('bilingualPromptModal');
        if (modal) modal.remove();

        // 刷新显示
        this.renderVideoCards();
        this.showToast('提示词已更新', 'success');
    }
    };
}));
