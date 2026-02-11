/**
 * 选集功能模块
 * Episode Selector Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.EpisodeSelectorMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
        /**
         * 显示集数列表
         */
        showEpisodeList(majorEvent) {
            const panel = document.getElementById('episodeSelectorPanel');
            const container = document.getElementById('episodeList');
            const nameSpan = document.getElementById('selectedMajorEventNameTitle');

            if (nameSpan) nameSpan.textContent = majorEvent.title;
            if (panel) panel.style.display = 'block';

            const episodes = majorEvent.children || [];

            if (episodes.length === 0) {
                if (container) {
                    container.innerHTML = `
                        <div class="empty-state" style="grid-column: 1 / -1;">
                            <p>该重大事件下没有中级事件</p>
                        </div>
                    `;
                }
                return;
            }

            if (container) {
                container.innerHTML = episodes.map((ep, idx) => {
                    // 🔥 使用后端生成的事件ID（后端已经计算好了正确的ID格式）
                    const epId = ep.id || `episode_${idx}`;
                    const isChecked = this.selectedEpisodes.includes(epId) ? 'checked' : '';
                    const selectedClass = this.selectedEpisodes.includes(epId) ? 'selected' : '';

                    return `
                        <div class="episode-item ${selectedClass}" data-episode-id="${epId}">
                            <input type="checkbox" class="episode-checkbox" id="ep_${idx}" ${isChecked}>
                            <span class="episode-number">第${idx + 1}集</span>
                            <div class="episode-info">
                                <span class="episode-title">${ep.title || ep.name || `集数 ${idx + 1}`}</span>
                                <span class="episode-stage">${ep.stage || ''}</span>
                            </div>
                        </div>
                    `;
                }).join('');

                // 默认全选（如果还没有选中任何集数）
                if (this.selectedEpisodes.length === 0) {
                    this.selectAllEpisodes(true);
                }
            }
        },

        /**
         * 切换集数选择状态
         */
        toggleEpisodeSelection(episodeId, selected) {
            if (selected) {
                if (!this.selectedEpisodes.includes(episodeId)) {
                    this.selectedEpisodes.push(episodeId);
                }
            } else {
                const index = this.selectedEpisodes.indexOf(episodeId);
                if (index > -1) {
                    this.selectedEpisodes.splice(index, 1);
                }
            }

            // 更新选中项样式和复选框状态
            const item = document.querySelector(`.episode-item[data-episode-id="${episodeId}"]`);
            if (item) {
                item.classList.toggle('selected', selected);
                const checkbox = item.querySelector('.episode-checkbox');
                if (checkbox) {
                    checkbox.checked = selected;
                }
            }

            // 更新计数
            const countSpan = document.getElementById('selectedEpisodesCount');
            if (countSpan) {
                countSpan.textContent = this.selectedEpisodes.length;
            }

            // 更新项目状态
            this.updateProjectStatus();
        },

        /**
         * 全选/清空集数
         */
        selectAllEpisodes(selectAll) {
            document.querySelectorAll('.episode-item').forEach(item => {
                const episodeId = item.dataset.episodeId;
                const checkbox = item.querySelector('.episode-checkbox');

                // 更新数据
                if (selectAll) {
                    if (!this.selectedEpisodes.includes(episodeId)) {
                        this.selectedEpisodes.push(episodeId);
                    }
                } else {
                    const index = this.selectedEpisodes.indexOf(episodeId);
                    if (index > -1) {
                        this.selectedEpisodes.splice(index, 1);
                    }
                }

                // 更新UI
                item.classList.toggle('selected', selectAll);
                if (checkbox) {
                    checkbox.checked = selectAll;
                }
            });

            // 更新计数
            const countSpan = document.getElementById('selectedEpisodesCount');
            if (countSpan) {
                countSpan.textContent = this.selectedEpisodes.length;
            }

            // 更新项目状态
            this.updateProjectStatus();
        }
    };
}));
