/**
 * Phase One Optimizer JavaScript
 * 第一阶段产品优化 - 三轮优化系统前端交互
 */

class PhaseOneOptimizer {
    constructor(options = {}) {
        this.title = options.title;
        this.platform = options.platform || 'fanqie';
        this.apiBaseUrl = options.apiBaseUrl || '/api';
        this.onProgress = options.onProgress || (() => {});
        this.onComplete = options.onComplete || (() => {});
        this.onError = options.onError || (() => {});
        
        this.taskId = null;
        this.pollingInterval = null;
        this.isRunning = false;
    }

    /**
     * 启动优化流程
     */
    async start() {
        if (this.isRunning) {
            throw new Error('优化任务已在运行中');
        }

        this.isRunning = true;
        
        try {
            // 启动优化任务
            const response = await fetch(`${this.apiBaseUrl}/phase-one/optimize`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: this.title,
                    platform: this.platform
                })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || '启动优化任务失败');
            }

            const data = await response.json();
            this.taskId = data.task_id;

            // 开始轮询进度
            this._startPolling();

            return data;
        } catch (error) {
            this.isRunning = false;
            this.onError(error);
            throw error;
        }
    }

    /**
     * 开始轮询任务状态
     */
    _startPolling() {
        this.pollingInterval = setInterval(() => {
            this._checkStatus();
        }, 2000); // 每2秒检查一次
    }

    /**
     * 检查任务状态
     */
    async _checkStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/phase-one/optimize/${this.taskId}`);
            
            if (!response.ok) {
                throw new Error('获取任务状态失败');
            }

            const data = await response.json();
            
            // 通知进度更新
            this.onProgress({
                status: data.status,
                progress: data.progress || 0,
                current_round: data.current_round,
                message: data.message || '',
                rounds: data.rounds || {}
            });

            // 任务完成或失败
            if (data.status === 'completed' || data.status === 'failed') {
                this._stopPolling();
                this.isRunning = false;

                if (data.status === 'completed') {
                    this.onComplete(data.result);
                } else {
                    this.onError(new Error(data.error || '优化任务失败'));
                }
            }
        } catch (error) {
            this._stopPolling();
            this.isRunning = false;
            this.onError(error);
        }
    }

    /**
     * 停止轮询
     */
    _stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    /**
     * 取消优化任务
     */
    cancel() {
        this._stopPolling();
        this.isRunning = false;
        this.taskId = null;
    }
}

/**
 * 优化结果渲染器
 */
class OptimizationResultRenderer {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`容器 #${containerId} 不存在`);
        }
    }

    /**
     * 渲染优化结果
     */
    render(result) {
        const html = this._generateHTML(result);
        this.container.innerHTML = html;
    }

    /**
     * 生成HTML
     */
    _generateHTML(result) {
        const overallScore = result.overall_score || 0;
        const rounds = result.rounds || {};
        
        return `
            <div class="v2-optimization-result">
                <!-- 总体评分 -->
                <div class="v2-optimization-result__header">
                    <div class="v2-optimization-result__score">
                        <div class="v2-score-ring" style="--score: ${overallScore}">
                            <span class="v2-score-ring__value">${overallScore}</span>
                            <span class="v2-score-ring__label">总分</span>
                        </div>
                    </div>
                    <div class="v2-optimization-result__summary">
                        <h4>优化完成</h4>
                        <p>${result.summary || '优化分析已完成，请查看各轮次详情。'}</p>
                    </div>
                </div>

                <!-- 三轮详情 -->
                <div class="v2-optimization-result__rounds">
                    ${this._renderRound('platform_adaptation', rounds.platform_adaptation, '第一轮：平台风格适配')}
                    ${this._renderRound('data_matching', rounds.data_matching, '第二轮：数据匹配')}
                    ${this._renderRound('coherence_check', rounds.coherence_check, '第三轮：内容连贯性')}
                </div>

                <!-- 操作按钮 -->
                <div class="v2-optimization-result__actions">
                    <button class="v2-btn v2-btn--primary" onclick="applyOptimization()">
                        <span class="material-icons">check</span>
                        应用优化建议
                    </button>
                    <button class="v2-btn v2-btn--secondary" onclick="exportReport()">
                        <span class="material-icons">download</span>
                        导出报告
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * 渲染单轮结果
     */
    _renderRound(roundId, roundData, title) {
        if (!roundData) return '';

        const score = roundData.score || 0;
        const scoreClass = score >= 80 ? 'high' : score >= 60 ? 'medium' : 'low';
        const suggestions = roundData.suggestions || [];
        const issues = roundData.issues || [];

        return `
            <div class="v2-optimization-round" data-round="${roundId}">
                <div class="v2-optimization-round__header">
                    <h5>${title}</h5>
                    <span class="v2-optimization-round__score v2-optimization-round__score--${scoreClass}">
                        ${score}分
                    </span>
                </div>
                <div class="v2-optimization-round__content">
                    ${issues.length > 0 ? `
                        <div class="v2-optimization-section">
                            <h6>发现的问题</h6>
                            <ul class="v2-optimization-list v2-optimization-list--issues">
                                ${issues.map(issue => `
                                    <li>
                                        <span class="material-icons">error_outline</span>
                                        <span>${issue}</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${suggestions.length > 0 ? `
                        <div class="v2-optimization-section">
                            <h6>改进建议</h6>
                            <ul class="v2-optimization-list v2-optimization-list--suggestions">
                                ${suggestions.map(suggestion => `
                                    <li>
                                        <span class="material-icons">lightbulb</span>
                                        <span>${suggestion}</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    ` : ''}
                    ${roundData.summary ? `
                        <div class="v2-optimization-section">
                            <h6>总结</h6>
                            <p>${roundData.summary}</p>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }
}

/**
 * 进度条组件
 */
class OptimizationProgressBar {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            throw new Error(`容器 #${containerId} 不存在`);
        }
    }

    update(progress, currentRound, message) {
        const roundNames = {
            'platform_adaptation': '平台风格适配',
            'data_matching': '数据匹配',
            'coherence_check': '内容连贯性检查'
        };

        const roundName = roundNames[currentRound] || '优化中';

        this.container.innerHTML = `
            <div class="v2-optimization-progress">
                <div class="v2-optimization-progress__info">
                    <span class="v2-optimization-progress__round">${roundName}</span>
                    <span class="v2-optimization-progress__percent">${progress}%</span>
                </div>
                <div class="v2-optimization-progress__bar">
                    <div class="v2-optimization-progress__fill" style="width: ${progress}%"></div>
                </div>
                ${message ? `<p class="v2-optimization-progress__message">${message}</p>` : ''}
            </div>
        `;
    }

    hide() {
        this.container.innerHTML = '';
    }
}

// 导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PhaseOneOptimizer, OptimizationResultRenderer, OptimizationProgressBar };
}
