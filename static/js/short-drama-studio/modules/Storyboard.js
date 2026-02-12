/**
 * 分镜生成模块
 * Storyboard Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.StoryboardMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
        normalizeShotData(shot, title, episodeNumber, episodeOrder) {
            // 🔥 episodeOrder 是后端提供的事件顺序（_order字段），直接使用
            const order = episodeOrder !== undefined && episodeOrder !== null ? episodeOrder : 9999;

            // 🔥 获取场景号（从 _scene_number 或 scene_number）
            const sceneNumber = shot._scene_number || shot.scene_number || 1;
            // 🔥 shot_number 是场景内的镜头号，不是场景号！
            const shotNumber = shot.shot_number || 1;

            // 检查是否是新格式 (有 visual 字段)
            if (shot.visual) {
                // 新格式转旧格式
                const visual = shot.visual || {};

                // 检查是否有多个对话 (对话场景)
                if (shot.dialogues && Array.isArray(shot.dialogues) && shot.dialogues.length > 0) {
                    // 对话场景：保留原始结构，不展开
                    return {
                        scene_number: sceneNumber,  // 🔥 场景号
                        shot_number: shotNumber,     // 🔥 镜头号
                        shot_type: visual.shot_type || shot.shot_type || '镜头',
                        screen_action: visual.description || shot.screen_action || '',
                        // 保留dialogues数组用于配音展开
                        dialogues: shot.dialogues,
                        // 使用第一个对话作为默认显示（用于视频步骤）
                        dialogue: shot.dialogues[0].lines || shot.dialogues[0].speaker || '',
                        _dialogue_data: shot.dialogues[0],
                        veo_prompt: visual.veo_prompt || shot.veo_prompt || '',
                        duration: shot.duration || 5,
                        plot_content: shot.plot_content || '',
                        episode_title: title,
                        event_name: title,
                        episode_index: episodeNumber,
                        episode_order: order,
                        audio: shot.dialogues[0].audio_note || shot.audio || '',
                        is_dialogue_scene: true,
                        dialogue_count: shot.dialogues.length
                    };
                }

                const dialogue = shot.dialogue || {};
                return {
                    scene_number: sceneNumber,  // 🔥 场景号
                    shot_number: shotNumber,     // 🔥 镜头号
                    shot_type: visual.shot_type || shot.shot_type || '镜头',
                    screen_action: visual.description || shot.screen_action || '',
                    dialogue: dialogue.lines || dialogue.speaker || '',
                    _dialogue_data: dialogue,
                    veo_prompt: visual.veo_prompt || shot.veo_prompt || '',
                    duration: shot.duration || 5,
                    plot_content: shot.plot_content || '',
                    episode_title: title,
                    event_name: title,
                    episode_index: episodeNumber,
                    episode_order: order,
                    audio: dialogue.audio_note || shot.audio || ''
                };
            } else {
                // 旧格式，直接使用并添加场景号
                return {
                    ...shot,
                    scene_number: sceneNumber,  // 🔥 确保有场景号
                    shot_number: shotNumber,     // 🔥 确保有镜头号
                    episode_title: title,
                    event_name: shot.event_name || title,
                    episode_index: episodeNumber,
                    episode_order: order
                };
            }
        },

        async saveShotsV2(shots) {
            try {
                const episodeDirectoryName = this.getEpisodeDirectoryName();
                console.log('💾 [保存] 开始保存 shots_v2.json, 剧集:', episodeDirectoryName);

                const response = await fetch('/api/short-drama/shots-v2', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        novel: this.selectedNovel,
                        episode: episodeDirectoryName,
                        shots: shots
                    })
                });

                const data = await response.json();

                if (data.success) {
                    console.log('✅ [保存] shots_v2.json 保存成功');
                } else {
                    console.error('❌ [保存] shots_v2.json 保存失败:', data.error);
                }
            } catch (error) {
                console.error('❌ [保存] shots_v2.json 保存异常:', error);
            }
        },

        async loadShotsV2() {
            try {
                const episodeDirectoryName = this.getEpisodeDirectoryName();
                console.log('📂 [加载] 尝试加载 shots_v2.json, 剧集:', episodeDirectoryName);

                const response = await fetch(`/api/short-drama/shots-v2?novel=${encodeURIComponent(this.selectedNovel)}&episode=${encodeURIComponent(episodeDirectoryName)}`);
                const data = await response.json();

                if (data.success && data.shots && data.shots.length > 0) {
                    console.log('✅ [加载] shots_v2.json 加载成功, 镜头数:', data.shots.length);
                    return { shots: data.shots };
                } else {
                    console.log('⚠️ [加载] shots_v2.json 不存在或为空');
                    return null;
                }
            } catch (error) {
                console.error('❌ [加载] shots_v2.json 加载异常:', error);
                return null;
            }
        },

        normalizeShots(shots) {
            console.log('🔄 [格式化] 开始格式化镜头数据, 原始数量:', shots.length);

            return shots.map((shot, idx) => {
                // 确保必需字段存在
                const normalized = {
                    id: shot.id || `shot_${idx}`,
                    shot_number: shot.shot_number || idx + 1,
                    scene_number: shot.scene_number || 1,
                    scene_title: shot.scene_title || `场景${shot.scene_number || 1}`,
                    duration: shot.duration || shot.duration_seconds || 8,

                    // 🔥 保留优化格式的所有字段
                    visual_description: shot.visual_description,
                    visual_description_standard: shot.visual_description_standard,
                    visual_description_reference: shot.visual_description_reference,
                    visual_description_frames: shot.visual_description_frames,

                    veo_prompt: shot.veo_prompt,
                    veo_prompt_standard: shot.veo_prompt_standard,
                    veo_prompt_reference: shot.veo_prompt_reference,
                    veo_prompt_frames: shot.veo_prompt_frames,

                    preferred_mode: shot.preferred_mode || 'standard',

                    visual_elements: shot.visual_elements || {},
                    dialogue: shot.dialogue || shot._dialogue_data,
                    dialogues: shot.dialogues || [],
                    image_prompts: shot.image_prompts || {},
                    reference_images: shot.reference_images || [],

                    // 兼容旧格式字段
                    shot_type: shot.shot_type || '中景',
                    screen_action: shot.screen_action || shot.visual_description_standard || shot.visual_description,

                    // 视频生成状态
                    status: shot.status || 'pending',
                    videoExists: false,
                    videoPath: null,
                    videoUrl: null,

                    // 保留原始数据
                    _originalData: shot
                };

                return normalized;
            });
        },

        async loadShotsData() {
            // 如果已经有缓存数据，直接返回
            if (this.shots && this.shots.length > 0) {
                console.log('🔄 [数据加载] 使用缓存的镜头数据:', this.shots.length);
                return this.shots;
            }

            const episodeDirectoryName = this.getEpisodeDirectoryName();
            console.log('📚 [数据加载] 开始加载镜头数据, 剧集:', episodeDirectoryName);

            try {
                // 统一数据源：只使用 shots_v2.json
                const v2Data = await this.loadShotsV2();
                if (v2Data?.shots?.length > 0) {
                    console.log('✅ [数据加载] 从 shots_v2.json 加载成功, 镜头数:', v2Data.shots.length);
                    this.shots = this.normalizeShots(v2Data.shots);

                    // 缓存到项目中
                    if (!this.currentProject) {
                        this.currentProject = {};
                    }
                    this.currentProject.shots = this.shots;
                    
                    return this.shots;
                } else {
                    console.log('⚠️ [数据加载] shots_v2.json 不存在或为空');
                }
            } catch (error) {
                console.error('❌ [数据加载] 加载镜头数据失败:', error);
            }

            return [];
        },

        groupShotsByEvent(shots) {
            const groups = [];
            let currentEvent = null;
            let currentGroup = null;

            shots.forEach(shot => {
                const eventName = shot.episode_title || shot.event_name || '未分组';

                if (eventName !== currentEvent) {
                    // 新的事件组
                    currentGroup = {
                        eventName: eventName,
                        shots: []
                    };
                    groups.push(currentGroup);
                    currentEvent = eventName;
                }

                currentGroup.shots.push(shot);
            });

            return groups;
        },

        updateShotMode(shotIndex) {
            const selectElement = document.getElementById(`mode-select-${shotIndex}`);
            if (!selectElement) return;

            const newMode = selectElement.value;
            const shot = this.shots[shotIndex];

            if (!shot) return;

            // 更新镜头的首选模式
            shot.preferred_mode = newMode;

            // 更新显示的提示词
            const promptTextElement = document.getElementById(`prompt-text-${shotIndex}`);
            if (promptTextElement) {
                const newPrompt = this.getCurrentVisualDescription(shot);
                promptTextElement.textContent = `${newPrompt.substring(0, 150)}${newPrompt.length > 150 ? '...' : ''}`;
            }

            console.log(`🎨 [模式切换] 镜头${shotIndex} 切换到 ${newMode} 模式`);
        },

        normalizeShotsForImport(shots) {
            if (!Array.isArray(shots) || shots.length === 0) return [];
            
            return shots.map((shot, index) => {
                if (typeof shot === 'string') {
                    return {
                        shot_number: index + 1,
                        content: shot,
                        duration: 5
                    };
                }
                
                return {
                    shot_number: shot.shot_number || shot.number || shot.id || shot.index || (index + 1),
                    scene_title: shot.scene_title || shot.scene || shot.title || shot.name || '',
                    content: shot.content || shot.description || shot.desc || shot.prompt || shot.text || '',
                    duration: parseInt(shot.duration) || parseInt(shot.length) || parseInt(shot.time) || 5,
                    camera_angle: shot.camera_angle || shot.angle || shot.view || '',
                    camera_movement: shot.camera_movement || shot.movement || shot.motion || '',
                    scene_type: shot.scene_type || shot.type || 'standard',
                    dialogues: this.normalizeDialogues(shot.dialogues || shot.dialogue || shot.lines || shot.conversation || [])
                };
            });
        },

        async loadStoryboardStep() {
            const container = document.getElementById('storyboardContent');
            if (!container) return;

            // 🔥 优先检查 episodes 中是否有 shots 数据（创意导入优先级最高）
            if (this.currentProject?.episodes && this.currentProject.episodes.length > 0) {
                const firstEpisode = this.currentProject.episodes[0];
                if (firstEpisode.shots && firstEpisode.shots.length > 0) {
                    console.log('✅ [分镜头] 从 episodes 加载 shots 数据（创意导入）');
                    // 调用 normalizeShots 确保数据格式统一
                    this.currentProject.shots = this.normalizeShots(firstEpisode.shots);
                    this.shots = this.currentProject.shots;
                    this.renderShotsList();
                    return;
                }
            }

            // 🔥 其次检查根级别的 shots 数据（手动生成）
            if (this.currentProject?.shots && this.currentProject.shots.length > 0) {
                console.log('✅ [分镜头] 已有根级别 shots 数据，直接显示');
                this.renderShotsList();
                return;
            }

            if (!this.currentProject?.storyBeats?.scenes) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>🎬</p>
                        <p>请先生成故事节拍</p>
                    </div>
                `;
                return;
            }

            // 🔥 显示生成按钮，让用户手动触发生成
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬</p>
                    <p>暂无分镜头数据</p>
                    <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryboard()">
                        生成分镜头
                    </button>
                </div>
            `;
        },

        async generateStoryboard() {
            const container = document.getElementById('storyboardContent');
            if (!container) return;

            const settings = this.getVideoSettings();
            let modeText = '标准模式';
            if (settings.useFirstLastFrame) {
                modeText = '首尾帧模式（保持人物一致性）';
            } else if (settings.hasReferenceImages) {
                modeText = '参考图模式（使用角色剧照）';
            }

            container.innerHTML = `
                <div class="empty-state">
                    <p>⏳</p>
                    <p>正在生成分镜头...</p>
                    <p style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 0.5rem;">
                        使用：${modeText}
                    </p>
                </div>
            `;

            try {
                // 🔥 先保存视觉资产到项目（确保AI生成时使用标准描述）
                await this.saveVisualAssetsToProject();

                const response = await fetch('/api/short-drama/storyboard/generate-from-beats', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        projectId: this.currentProject.id,
                        storyBeats: this.currentProject.storyBeats,
                        hasReferenceImage: settings.hasReferenceImages,
                        hasFirstLastFrame: settings.useFirstLastFrame
                    })
                });

                const data = await response.json();

                if (data.success) {
                    this.currentProject.shots = data.shots;
                    // 🔥 保存到文件系统（数据流A持久化）
                    await this.saveShotsV2(data.shots);
                    this.showToast('分镜头生成成功', 'success');
                    this.renderShotsList();
                } else {
                    throw new Error(data.message || '生成失败');
                }
            } catch (error) {
                console.error('生成分镜头失败:', error);
                container.innerHTML = `
                    <div class="empty-state">
                        <p>❌</p>
                        <p>生成分镜头失败</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">${error.message}</p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryboard()">
                            重试
                        </button>
                    </div>
                `;
            }
        },

        renderShotsList() {
            const container = document.getElementById('storyboardContent');
            if (!container) return;
            
            const shots = this.currentProject?.shots || [];
            
            if (shots.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>🎬</p>
                        <p>暂无分镜头</p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.loadStoryboardStep()">
                            生成分镜头
                        </button>
                    </div>
                `;
                return;
            }
            
            const scenesMap = {};
            shots.forEach(shot => {
                const sceneNum = shot.scene_number || 1;
                if (!scenesMap[sceneNum]) {
                    scenesMap[sceneNum] = {
                        title: shot.scene_title || `场景${sceneNum}`,
                        shots: []
                    };
                }
                scenesMap[sceneNum].shots.push(shot);
            });
            
            let html = `
                <div class="storyboard-header">
                    <h3>🎬 分镜头脚本</h3>
                    <span>共 ${shots.length} 个镜头</span>
                </div>
                <div class="scenes-list">
            `;
            
            Object.keys(scenesMap).sort((a, b) => parseInt(a) - parseInt(b)).forEach(sceneNum => {
                const scene = scenesMap[sceneNum];
                html += `
                    <div class="scene-card">
                        <div class="scene-header">
                            <h4 class="scene-title">${scene.title}</h4>
                            <span class="scene-count">${scene.shots.length} 镜头</span>
                        </div>
                        <div class="shots-list">
                `;
                
                scene.shots.forEach((shot, idx) => {
                    const visualDescStandard = shot.visual_description_standard || shot.visual_description || '暂无画面描述';
                    const visualDescReference = shot.visual_description_reference || shot.visual_description || '暂无画面描述';
                    const visualDescFrames = shot.visual_description_frames || shot.visual_description || '暂无画面描述';
                    
                    const veoPromptStandard = shot.veo_prompt_standard || shot.veo_prompt || 'N/A';
                    const veoPromptReference = shot.veo_prompt_reference || shot.veo_prompt || 'N/A';
                    const veoPromptFrames = shot.veo_prompt_frames || shot.veo_prompt || 'N/A';
                    
                    const visualElements = shot.visual_elements || {};
                    const shotId = shot.id || `shot_${sceneNum}_${idx}`;
                    
                    html += `
                        <div class="shot-item">
                            <div class="shot-number">${shot.shot_number}</div>
                            <div class="shot-info">
                                <div class="shot-header">
                                    <span class="shot-type">${shot.shot_type || '镜头'}</span>
                                    <span class="shot-duration">⏱️ ${shot.duration || 8}秒</span>
                                </div>
                                
                                <div class="shot-mode-selector">
                                    <label>提示词模式：</label>
                                    <select id="mode-select-${shotId}" onchange="shortDramaStudio.switchPromptMode('${shotId}')" class="mode-select">
                                        <option value="standard" ${shot.preferred_mode === 'standard' ? 'selected' : ''}>标准模式</option>
                                        <option value="reference" ${shot.preferred_mode === 'reference' ? 'selected' : ''}>参考图模式</option>
                                        <option value="frames" ${shot.preferred_mode === 'frames' ? 'selected' : ''}>首尾帧模式</option>
                                    </select>
                                </div>
                                
                                <div id="visual-desc-${shotId}" class="shot-description">
                                    <p id="visual-desc-text-${shotId}">
                                        ${shot.preferred_mode === 'reference' ? visualDescReference : (shot.preferred_mode === 'frames' ? visualDescFrames : visualDescStandard)}
                                    </p>
                                </div>
                                
                                <div id="shot-data-${shotId}" style="display: none;"
                                     data-standard="${this.escapeHtml(visualDescStandard)}"
                                     data-reference="${this.escapeHtml(visualDescReference)}"
                                     data-frames="${this.escapeHtml(visualDescFrames)}"
                                     data-prompt-standard="${this.escapeHtml(veoPromptStandard)}"
                                     data-prompt-reference="${this.escapeHtml(veoPromptReference)}"
                                     data-prompt-frames="${this.escapeHtml(veoPromptFrames)}">
                                </div>
                                
                                ${visualElements.人物 || visualElements.光线 || visualElements.镜头 ? `
                                    <div class="shot-tags">
                                        ${visualElements.人物 ? `<span class="shot-tag character">👤 ${visualElements.人物.clothing || '传统服饰'}</span>` : ''}
                                        ${visualElements.光线 ? `<span class="shot-tag lighting">💡 ${visualElements.光线}</span>` : ''}
                                        ${visualElements.镜头 ? `<span class="shot-tag camera">🎥 ${visualElements.镜头}</span>` : ''}
                                    </div>
                                ` : ''}
                                
                                ${shot.dialogue?.lines ? `
                                    <div class="shot-dialogue">
                                        <p class="dialogue-speaker">${shot.dialogue.speaker}</p>
                                        <p class="dialogue-text">"${shot.dialogue.lines}"</p>
                                    </div>
                                ` : ''}
                                
                                <details class="shot-details">
                                    <summary>查看AI提示词（英文）</summary>
                                    <p id="veo-prompt-${shotId}" class="veo-prompt">${shot.preferred_mode === 'reference' ? veoPromptReference : (shot.preferred_mode === 'frames' ? veoPromptFrames : veoPromptStandard)}</p>
                                </details>
                                
                                ${shot.image_prompts ? `
                                    <details class="shot-details image-prompts">
                                        <summary>🎨 图片生成提示词</summary>
                                        <div class="image-prompts-list">
                                            ${shot.image_prompts.scene ? `
                                                <div class="image-prompt-item">
                                                    <div class="prompt-header">
                                                        <span>🏞️ 场景图（空场景背景）</span>
                                                        <button class="btn btn-sm" onclick="shortDramaStudio.copyToClipboard('${this.escapeHtml(shot.image_prompts.scene)}')">复制英文</button>
                                                    </div>
                                                    <p class="prompt-text">${shot.image_prompts_cn?.scene || shot.image_prompts.scene}</p>
                                                </div>
                                            ` : ''}
                                            ${shot.image_prompts.character ? `
                                                <div class="image-prompt-item">
                                                    <div class="prompt-header">
                                                        <span>👤 角色图（角色参考）</span>
                                                        <button class="btn btn-sm" onclick="shortDramaStudio.copyToClipboard('${this.escapeHtml(shot.image_prompts.character)}')">复制英文</button>
                                                    </div>
                                                    <p class="prompt-text">${shot.image_prompts_cn?.character || shot.image_prompts.character}</p>
                                                </div>
                                            ` : ''}
                                            ${shot.image_prompts.first_frame ? `
                                                <div class="image-prompt-item">
                                                    <div class="prompt-header">
                                                        <span>🎬 首帧（起始画面）</span>
                                                        <button class="btn btn-sm" onclick="shortDramaStudio.copyToClipboard('${this.escapeHtml(shot.image_prompts.first_frame)}')">复制英文</button>
                                                    </div>
                                                    <p class="prompt-text">${shot.image_prompts_cn?.first_frame || shot.image_prompts.first_frame}</p>
                                                </div>
                                            ` : ''}
                                            ${shot.image_prompts.last_frame ? `
                                                <div class="image-prompt-item">
                                                    <div class="prompt-header">
                                                        <span>🎬 尾帧（结束画面）</span>
                                                        <button class="btn btn-sm" onclick="shortDramaStudio.copyToClipboard('${this.escapeHtml(shot.image_prompts.last_frame)}')">复制英文</button>
                                                    </div>
                                                    <p class="prompt-text">${shot.image_prompts_cn?.last_frame || shot.image_prompts.last_frame}</p>
                                                </div>
                                            ` : ''}
                                        </div>
                                    </details>
                                ` : ''}
                            </div>
                            
                            <!-- 右侧：操作按钮 -->
                            <div class="shot-actions" style="display: flex; flex-direction: column; gap: 0.5rem; align-items: flex-end; margin-left: 1rem; min-width: 100px;">
                                <button class="btn btn-sm" onclick="shortDramaStudio.openMultiImageModalByShotId('${shotId}')" style="white-space: nowrap; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; border: none; padding: 0.5rem 0.75rem; border-radius: 0.375rem; cursor: pointer; font-size: 0.8rem;">
                                    🎨 多图生成
                                </button>
                                ${shot.generatedImages?.length > 0 ? `<span style="font-size: 0.7rem; color: #10b981;">✓ 已生成${shot.generatedImages.length}张</span>` : ''}
                            </div>
                        </div>
                    `;
                });
                
                html += `
                        </div>
                    </div>
                `;
            });
            
            html += `
                </div>
                <div class="storyboard-actions">
                    <button class="btn btn-secondary" onclick="shortDramaStudio.loadStoryboardStep()">🔄 重新生成</button>
                    <button class="btn btn-primary" onclick="shortDramaStudio.saveShotModes(); shortDramaStudio.goToStep('video')">✓ 确认并进入视频生成</button>
                </div>
            `;
            
            container.innerHTML = html;
        },

        saveShotModes() {
            if (!this.currentProject?.shots) return;
            
            this.currentProject.shots.forEach(shot => {
                const shotId = shot.id || `shot_${shot.scene_number}_${shot.shot_number}`;
                const select = document.getElementById(`mode-select-${shotId}`);
                if (select) {
                    shot.preferred_mode = select.value;
                }
            });
            
            console.log('Shot模式选择已保存');
        }

    };
}));
