/**
 * 视频任务管理系统 - 前端逻辑
 */

class VideoTaskManager {
    constructor() {
        this.shots = [];
        this.currentTaskId = null;
        this.taskStatus = null;
        this.selectedShots = new Set();
        this.currentTaskType = 'single'; // single, batch, project
        
        // 进度轮询
        this.progressInterval = null;
        
        this.init();
    }
    
    async init() {
        console.log('🎬 视频任务管理系统初始化...');
        
        // 绑定事件
        this.bindEvents();
        
        // 加载任务历史
        await this.loadTaskHistory();
        
        // 开始进度轮询（如果有活动任务）
        this.startProgressPolling();
        
        console.log('✅ 初始化完成');
    }
    
    bindEvents() {
        // 任务类型切换
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchTaskType(btn.dataset.type);
            });
        });
        
        // 模板按钮
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyTemplate(btn.dataset.template);
            });
        });
        
        // 添加镜头
        document.getElementById('addShotBtn').addEventListener('click', () => {
            this.addShot();
        });
        
        // 创建任务
        document.getElementById('createTaskBtn').addEventListener('click', () => {
            this.createTask();
        });
        
        // 任务控制
        document.getElementById('startTaskBtn').addEventListener('click', () => {
            this.startTask();
        });
        
        document.getElementById('pauseTaskBtn').addEventListener('click', () => {
            this.pauseTask();
        });
        
        document.getElementById('resumeTaskBtn').addEventListener('click', () => {
            this.resumeTask();
        });
        
        document.getElementById('cancelTaskBtn').addEventListener('click', () => {
            this.cancelTask();
        });
        
        // 镜头操作
        document.getElementById('selectAllShotsBtn').addEventListener('click', () => {
            this.selectAllShots();
        });
        
        document.getElementById('clearShotsBtn').addEventListener('click', () => {
            this.clearShots();
        });
        
        // 文件上传
        document.getElementById('firstFrameInput').addEventListener('change', (e) => {
            this.handleFileUpload(e, 'firstFramePreview');
        });
        
        document.getElementById('lastFrameInput').addEventListener('change', (e) => {
            this.handleFileUpload(e, 'lastFramePreview');
        });
        
        // 任务历史刷新
        document.getElementById('refreshHistoryBtn').addEventListener('click', () => {
            this.loadTaskHistory();
        });
        
        // 模态框
        document.getElementById('closeShotModalBtn').addEventListener('click', () => {
            this.closeShotModal();
        });
    }
    
    switchTaskType(type) {
        this.currentTaskType = type;
        
        // 更新UI状态
        document.querySelectorAll('.type-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.type === type) {
                btn.classList.add('active');
            }
        });
        
        console.log('🔄 切换任务类型:', type);
    }
    
    applyTemplate(template) {
        const templates = {
            scifi: '一个科幻未来风格的视频场景，充满科技感的建筑和全息投影，蓝紫色调，赛博朋克风格',
            nature: '一个自然风光的视频场景，阳光透过树叶洒下斑驳光影，宁静祥和的氛围',
            urban: '一个都市夜景的视频场景，霓虹灯闪烁，繁华的街道，充满活力的城市生活',
            fantasy: '一个奇幻魔法风格的视频场景，发光的魔法阵，飘浮的魔法粒子，神秘而美丽'
        };
        
        const prompt = templates[template];
        if (prompt) {
            document.getElementById('promptInput').value = prompt;
            this.showToast(`已应用${template}模板`, 'success');
        }
    }
    
    addShot() {
        const prompt = document.getElementById('promptInput').value.trim();
        if (!prompt) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        
        const shot = {
            shot_index: this.shots.length,
            shot_type: document.getElementById('shotType').value,
            camera_movement: document.getElementById('cameraMovement').value,
            duration_seconds: parseFloat(document.getElementById('duration').value) || 10,
            description: prompt.substring(0, 100),
            generation_prompt: prompt,
            audio_prompt: '',
            status: 'pending'
        };
        
        this.shots.push(shot);
        this.renderShotsList();
        this.updateCreateButton();
        
        // 清空输入
        document.getElementById('promptInput').value = '';
        
        this.showToast('镜头已添加', 'success');
    }
    
    renderShotsList() {
        const container = document.getElementById('shotsList');
        
        if (this.shots.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>🎬 还没有添加镜头</p>
                    <p class="hint">在左侧配置并添加镜头</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = this.shots.map((shot, index) => `
            <div class="shot-card ${this.selectedShots.has(index) ? 'selected' : ''}" data-index="${index}">
                <div class="shot-card-header">
                    <span class="shot-number">镜头 #${index + 1}</span>
                    <span class="shot-status ${shot.status}">${this.getStatusText(shot.status)}</span>
                </div>
                <div class="shot-card-body">
                    <p class="shot-description">${shot.description || shot.generation_prompt}</p>
                    <div class="shot-meta">
                        <span class="shot-meta-item">${shot.shot_type}</span>
                        <span class="shot-meta-item">${shot.camera_movement}</span>
                        <span class="shot-meta-item">${shot.duration_seconds}s</span>
                    </div>
                </div>
            </div>
        `).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.shot-card').forEach(card => {
            card.addEventListener('click', () => {
                const index = parseInt(card.dataset.index);
                this.toggleShotSelection(index);
            });
        });
    }
    
    toggleShotSelection(index) {
        if (this.selectedShots.has(index)) {
            this.selectedShots.delete(index);
        } else {
            this.selectedShots.add(index);
        }
        this.renderShotsList();
    }
    
    selectAllShots() {
        this.shots.forEach((_, index) => this.selectedShots.add(index));
        this.renderShotsList();
    }
    
    clearShots() {
        if (this.shots.length > 0 && !confirm('确定要清空所有镜头吗？')) {
            return;
        }
        this.shots = [];
        this.selectedShots.clear();
        this.renderShotsList();
        this.updateCreateButton();
    }
    
    updateCreateButton() {
        const btn = document.getElementById('createTaskBtn');
        if (this.shots.length > 0) {
            btn.style.display = 'inline-block';
            btn.textContent = `🚀 创建任务 (${this.shots.length} 个镜头)`;
        } else {
            btn.style.display = 'none';
        }
    }
    
    async createTask() {
        if (this.shots.length === 0) {
            this.showToast('请先添加镜头', 'error');
            return;
        }
        
        const projectId = `project_${Date.now()}`;
        const maxConcurrent = parseInt(document.getElementById('maxConcurrent').value) || 3;
        
        const config = {
            max_concurrent: maxConcurrent,
            auto_start: false
        };
        
        try {
            this.showToast('正在创建任务...', 'success');
            
            const response = await fetch('/api/video/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    project_id: projectId,
                    shots: this.shots,
                    config: config
                })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.currentTaskId = data.task_id;
                this.updateTaskInfo();
                this.showToast('任务创建成功！', 'success');
                
                // 刷新任务历史
                await this.loadTaskHistory();
            } else {
                throw new Error(data.error || '创建任务失败');
            }
        } catch (error) {
            console.error('创建任务失败:', error);
            this.showToast('创建任务失败: ' + error.message, 'error');
        }
    }
    
    async startTask() {
        if (!this.currentTaskId) {
            this.showToast('没有可启动的任务', 'error');
            return;
        }
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/start`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('任务已启动', 'success');
                await this.updateTaskStatus();
                this.startProgressPolling();
            } else {
                throw new Error(data.error || '启动失败');
            }
        } catch (error) {
            console.error('启动任务失败:', error);
            this.showToast('启动失败: ' + error.message, 'error');
        }
    }
    
    async pauseTask() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/pause`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('任务已暂停', 'success');
                await this.updateTaskStatus();
            } else {
                throw new Error(data.error || '暂停失败');
            }
        } catch (error) {
            this.showToast('暂停失败: ' + error.message, 'error');
        }
    }
    
    async resumeTask() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/resume`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('任务已恢复', 'success');
                await this.updateTaskStatus();
                this.startProgressPolling();
            } else {
                throw new Error(data.error || '恢复失败');
            }
        } catch (error) {
            this.showToast('恢复失败: ' + error.message, 'error');
        }
    }
    
    async cancelTask() {
        if (!this.currentTaskId) return;
        
        if (!confirm('确定要取消当前任务吗？')) {
            return;
        }
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/cancel`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('任务已取消', 'success');
                await this.updateTaskStatus();
                this.stopProgressPolling();
            } else {
                throw new Error(data.error || '取消失败');
            }
        } catch (error) {
            this.showToast('取消失败: ' + error.message, 'error');
        }
    }
    
    async updateTaskStatus() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/status`);
            const data = await response.json();
            
            if (data.success) {
                this.taskStatus = data.status;
                this.updateTaskUI(data.status);
            }
        } catch (error) {
            console.error('获取任务状态失败:', error);
        }
    }
    
    updateTaskUI(status) {
        // 更新任务ID
        document.getElementById('currentTaskId').textContent = this.currentTaskId || '无';
        
        // 更新状态
        document.getElementById('taskStatus').textContent = this.getStatusText(status.status);
        
        // 更新进度
        const progress = Math.round(status.progress * 100);
        document.getElementById('taskProgressBar').style.width = `${progress}%`;
        document.getElementById('taskProgressText').textContent = `${progress}%`;
        
        // 更新镜头数
        document.getElementById('shotCount').textContent = 
            `${status.completed_shots}/${status.total_shots}`;
        
        // 更新按钮状态
        const statusEnum = status.status;
        document.getElementById('startTaskBtn').disabled = statusEnum !== 'pending';
        document.getElementById('pauseTaskBtn').disabled = statusEnum !== 'running';
        document.getElementById('resumeTaskBtn').disabled = statusEnum !== 'paused';
        document.getElementById('cancelTaskBtn').disabled = 
            statusEnum === 'completed' || statusEnum === 'cancelled';
        
        // 如果任务完成，显示结果
        if (statusEnum === 'completed') {
            this.loadTaskResults();
            this.stopProgressPolling();
        }
    }
    
    startProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
        }
        
        this.progressInterval = setInterval(async () => {
            await this.updateTaskStatus();
            
            // 更新镜头状态
            await this.updateShotsStatus();
        }, 2000); // 每2秒更新一次
    }
    
    stopProgressPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    }
    
    async updateShotsStatus() {
        if (!this.currentTaskId) return;
        
        try {
            const response = await fetch(`/api/video/tasks/${this.currentTaskId}/status`);
            const data = await response.json();
            
            if (data.success && data.status) {
                // 更新本地镜头状态
                // 这里需要从后端获取完整的镜头状态
            }
        } catch (error) {
            console.error('更新镜头状态失败:', error);
        }
    }
    
    async loadTaskHistory() {
        try {
            const response = await fetch('/api/video/tasks');
            const data = await response.json();
            
            if (data.success) {
                this.renderTaskHistory(data.tasks);
            }
        } catch (error) {
            console.error('加载任务历史失败:', error);
        }
    }
    
    renderTaskHistory(tasks) {
        const container = document.getElementById('taskHistoryList');
        
        if (!tasks || tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <p>📋 还没有任务历史</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = tasks.map(task => `
            <div class="history-item" data-task-id="${task.task_id}">
                <div class="history-item-header">
                    <span class="history-task-id">#${task.task_id.substr(0, 8)}</span>
                    <span class="history-status ${task.status}">${this.getStatusText(task.status)}</span>
                </div>
                <div class="history-info">
                    ${task.completed_shots}/${task.total_shots} 镜头 | 
                    进度: ${Math.round(task.progress * 100)}%
                </div>
            </div>
        `).join('');
        
        // 绑定点击事件
        container.querySelectorAll('.history-item').forEach(item => {
            item.addEventListener('click', () => {
                this.loadTask(item.dataset.task_id);
            });
        });
    }
    
    async loadTask(taskId) {
        this.currentTaskId = taskId;
        await this.updateTaskStatus();
        this.showToast('已加载任务: ' + taskId.substr(0, 8), 'success');
    }
    
    async loadTaskResults() {
        // TODO: 从后端加载任务结果
        const container = document.getElementById('resultsGrid');
        container.innerHTML = `
            <div class="empty-state">
                <p>🎬 任务已完成，结果加载中...</p>
            </div>
        `;
    }
    
    handleFileUpload(event, previewId) {
        const file = event.target.files[0];
        if (!file) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            const preview = document.getElementById(previewId);
            preview.innerHTML = `<img src="${e.target.result}" alt="预览">`;
        };
        reader.readAsDataURL(file);
    }
    
    getStatusText(status) {
        const statusMap = {
            'pending': '⏸️ 待处理',
            'running': '▶️ 生成中',
            'paused': '⏸️ 已暂停',
            'completed': '✅ 已完成',
            'failed': '❌ 失败',
            'cancelled': '✖️ 已取消'
        };
        return statusMap[status] || status;
    }
    
    updateTaskInfo() {
        document.getElementById('currentTaskId').textContent = 
            this.currentTaskId ? `#${this.currentTaskId.substr(0, 8)}` : '无';
    }
    
    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        
        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
    const manager = new VideoTaskManager();
    window.videoTaskManager = manager;
});