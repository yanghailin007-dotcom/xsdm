/**
 * 故事节拍模块
 * Story Beats Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.StoryBeatsMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
        /**
         * 生成故事节拍
         */
        async generateStoryBeats() {
            if (!this.currentProject || !this.currentProject.episodes) {
                this.showToast('请先选择集数', 'warning');
                return;
            }
            const button = document.querySelector('#story-beatsStep .btn-primary');
            if (button) {
                button.disabled = true;
                button.innerHTML = '生成中...';
            }
            try {
                // 🔥 先保存视觉资产到项目（确保AI生成时使用标准描述）
                await this.saveVisualAssetsToProject();

                const response = await fetch('/api/short-drama/story-beats/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        projectId: this.currentProject.id,
                        episodeId: this.currentProject.episodes[0]?.id
                    })
                });
                const data = await response.json();
                if (data.success) {
                    this.currentProject.storyBeats = data.storyBeats;
                    this.renderStoryBeatsEditor();
                    this.showToast('故事节拍生成成功', 'success');
                } else {
                    throw new Error(data.message || '生成失败');
                }
            } catch (error) {
                console.error('生成故事节拍失败:', error);
                this.showToast('生成失败', 'error');
            } finally {
                if (button) {
                    button.disabled = false;
                    button.innerHTML = '生成故事节拍';
                }
            }
        },

        /**
         * 渲染故事节拍编辑器
         */
        renderStoryBeatsEditor() {
            const container = document.getElementById('story-beatsContent');
            if (!container) return;
            
            const storyBeats = this.currentProject?.storyBeats;
            if (!storyBeats || !storyBeats.scenes || storyBeats.scenes.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <p>暂无故事节拍</p>
                        <p style="font-size: 0.85rem; color: var(--text-secondary);">点击上方按钮生成故事节拍</p>
                    </div>
                `;
                return;
            }
            
            const totalDuration = storyBeats.scenes.reduce((sum, scene) => sum + (scene.durationSeconds || 0), 0);
            
            let html = `
                <div class="story-beats-header" style="margin-bottom: 1.5rem; padding: 1rem; background: rgba(99, 102, 241, 0.1); border-radius: 0.75rem; border: 1px solid rgba(99, 102, 241, 0.2);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <h3 style="font-size: 1rem; color: var(--text-primary); margin: 0;">故事节拍概览</h3>
                        <span style="font-size: 0.875rem; color: var(--text-secondary);">${storyBeats.scenes.length} 场景 | ${totalDuration}秒</span>
                    </div>
                    <div style="display: flex; gap: 1rem; font-size: 0.875rem; color: var(--text-tertiary);">
                        <span>第一幕: 建立 (0-${Math.round(totalDuration * 0.3)}秒)</span>
                        <span>第二幕: 对抗 (${Math.round(totalDuration * 0.3)}-${Math.round(totalDuration * 0.7)}秒)</span>
                        <span>第三幕: 高潮 (${Math.round(totalDuration * 0.7)}-${totalDuration}秒)</span>
                    </div>
                </div>
                <div class="story-beats-list" style="display: flex; flex-direction: column; gap: 1rem;">
            `;
            
            storyBeats.scenes.forEach((scene, index) => {
                const startTime = storyBeats.scenes.slice(0, index).reduce((sum, s) => sum + (s.durationSeconds || 0), 0);
                const endTime = startTime + (scene.durationSeconds || 0);
                
                html += `
                    <div class="scene-card" style="background: var(--bg-secondary); border-radius: 0.75rem; padding: 1rem; border: 1px solid rgba(255, 255, 255, 0.1);">
                        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.75rem;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                                    <span style="background: rgba(99, 102, 241, 0.2); color: #818cf8; padding: 0.125rem 0.5rem; border-radius: 0.25rem; font-size: 0.75rem; font-weight: 600;">场景 ${index + 1}</span>
                                    <span style="font-size: 0.75rem; color: var(--text-tertiary);">${startTime}-${endTime}秒</span>
                                </div>
                                <h4 style="font-size: 1rem; color: var(--text-primary); margin: 0;">${scene.sceneTitleCn || '未命名场景'}</h4>
                                <p style="font-size: 0.75rem; color: var(--text-tertiary); margin: 0.25rem 0 0 0;">${scene.sceneTitleEn || ''}</p>
                            </div>
                            <span style="font-size: 0.875rem; color: var(--text-secondary); background: rgba(255, 255, 255, 0.05); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">${scene.durationSeconds || 0}秒</span>
                        </div>
                        
                        <div style="margin-bottom: 0.75rem;">
                            <p style="font-size: 0.875rem; color: var(--text-secondary); margin: 0; line-height: 1.5;">
                                <strong style="color: var(--text-primary);">叙事目的:</strong> ${scene.storyBeatCn || '-'}
                            </p>
                        </div>

                        <div style="margin-bottom: 0.75rem;">
                            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                                <span style="font-size: 0.75rem; color: var(--text-tertiary);">情绪曲线:</span>
                                <span style="font-size: 0.875rem; color: var(--text-primary);">${scene.emotionalArc || '-'}</span>
                            </div>
                            <div style="height: 4px; background: rgba(255, 255, 255, 0.1); border-radius: 2px; overflow: hidden;">
                                <div style="height: 100%; background: linear-gradient(90deg, #6366f1, #8b5cf6); width: 100%;"></div>
                            </div>
                        </div>

                        ${scene.dialogues && scene.dialogues.length > 0 ? `
                            <div style="background: rgba(0, 0, 0, 0.2); border-radius: 0.5rem; padding: 0.75rem;">
                                <p style="font-size: 0.75rem; color: var(--text-tertiary); margin: 0 0 0.5rem 0;">对白:</p>
                                ${scene.dialogues.map(d => `
                                    <div style="margin-bottom: 0.5rem;">
                                        <span style="font-size: 0.75rem; color: #818cf8; margin-right: 0.5rem;">${d.speaker}</span>
                                        <span style="font-size: 0.875rem; color: var(--text-primary);">${d.linesCn || d.lines || '-'}</span>
                                    </div>
                                `).join('')}
                            </div>
                        ` : ''}
                    </div>
                `;
            });
            
            html += `
                </div>
                <div style="margin-top: 1.5rem; display: flex; gap: 1rem; justify-content: center;">
                    <button class="btn btn-secondary" onclick="shortDramaStudio.generateStoryBeats()">重新生成</button>
                    <button class="btn btn-primary" onclick="shortDramaStudio.goToStep('storyboard')">确认并进入分镜生成</button>
                </div>
            `;
            
            container.innerHTML = html;
        },

        /**
         * 渲染故事节拍步骤
         */
        renderStoryBeatsStep() {
            const container = document.getElementById('story-beatsContent');
            if (!container) return;
            
            const storyBeats = this.currentProject?.storyBeats;
            if (storyBeats && storyBeats.scenes && storyBeats.scenes.length > 0) {
                this.renderStoryBeatsEditor();
            } else {
                container.innerHTML = `
                    <div class="empty-state">
                        <p style="font-size: 2rem;">📋</p>
                        <p>还没有故事节拍</p>
                        <button class="btn btn-primary" onclick="shortDramaStudio.generateStoryBeats()" style="margin-top: 1rem;">生成故事节拍</button>
                    </div>
                `;
            }
        },

        /**
         * 保存故事节拍
         */
        async saveStoryBeats() {
            this.showToast('故事节拍已自动保存', 'success');
        }

    };
}));
