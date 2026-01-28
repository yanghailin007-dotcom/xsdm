/**
 * 视频制作系统 - API 核心模块
 * 统一的 API 请求封装
 */

class VideoAPI {
    constructor() {
        this.baseURL = '/api/video';
    }

    /**
     * 通用请求方法
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            ...options
        };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '请求失败');
            }

            return data;
        } catch (error) {
            console.error('API 请求失败:', error);
            throw error;
        }
    }

    /**
     * GET 请求
     */
    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url);
    }

    /**
     * POST 请求
     */
    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: data
        });
    }

    /**
     * PUT 请求
     */
    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: data
        });
    }

    /**
     * DELETE 请求
     */
    async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }

    // ========== 项目管理 ==========

    /**
     * 获取所有项目
     */
    async getProjects() {
        return this.get('/projects');
    }

    /**
     * 获取项目详情
     */
    async getProject(projectId) {
        return this.get(`/projects/${projectId}`);
    }

    /**
     * 创建项目
     */
    async createProject(data) {
        return this.post('/projects', data);
    }

    /**
     * 更新项目
     */
    async updateProject(projectId, data) {
        return this.put(`/projects/${projectId}`, data);
    }

    /**
     * 删除项目
     */
    async deleteProject(projectId) {
        return this.delete(`/projects/${projectId}`);
    }

    // ========== 小说相关 ==========

    /**
     * 获取可用于视频生成的小说列表
     */
    async getNovels() {
        return this.get('/novels');
    }

    /**
     * 获取小说详情
     */
    async getNovelDetail(title) {
        return this.get('/novel-detail', { title });
    }

    /**
     * 获取小说内容（事件和角色）
     */
    async getNovelContent(title) {
        return this.get('/novel-content', { title });
    }

    // ========== 剧照相关 ==========

    /**
     * 获取角色剧照列表
     */
    async getPortraits(projectId) {
        return this.get(`/projects/${projectId}/portraits`);
    }

    /**
     * 生成角色剧照
     */
    async generatePortrait(data) {
        return this.post('/generate-portrait', data);
    }

    /**
     * 获取道具/场景剧照列表
     */
    async getProps(projectId) {
        return this.get(`/projects/${projectId}/props`);
    }

    /**
     * 获取首尾帧列表
     */
    async getBookends(projectId) {
        return this.get(`/projects/${projectId}/bookends`);
    }

    // ========== 视频相关 ==========

    /**
     * 生成视频 (Veo API)
     */
    async generateVideo(data) {
        return this.post('/veo/generate', data);
    }

    /**
     * 获取视频生成状态
     */
    async getVideoStatus(taskId) {
        return this.get(`/veo/status/${taskId}`);
    }

    /**
     * 获取已生成的视频列表
     */
    async getVideoLibrary() {
        return this.get('/veo/tasks');
    }

    // ========== 分镜相关 ==========

    /**
     * 生成分镜脚本
     */
    async generateStoryboard(data) {
        return this.post('/generate-storyboard', data);
    }

    /**
     * 获取分镜脚本
     */
    async getStoryboard(projectId) {
        return this.get(`/projects/${projectId}/storyboard`);
    }

    // ========== 任务/流程相关 ==========

    /**
     * 创建批量任务
     */
    async createTask(data) {
        return this.post('/tasks', data);
    }

    /**
     * 获取任务状态
     */
    async getTask(taskId) {
        return this.get(`/tasks/${taskId}`);
    }

    /**
     * 启动任务
     */
    async startTask(taskId) {
        return this.post(`/tasks/${taskId}/start`);
    }

    /**
     * 暂停任务
     */
    async pauseTask(taskId) {
        return this.post(`/tasks/${taskId}/pause`);
    }

    /**
     * 取消任务
     */
    async cancelTask(taskId) {
        return this.post(`/tasks/${taskId}/cancel`);
    }

    /**
     * 获取所有任务
     */
    async getTasks() {
        return this.get('/tasks');
    }

    // ========== 统计数据 ==========

    /**
     * 获取统计数据
     */
    async getStats() {
        return this.get('/stats');
    }
}

// 创建全局实例
const videoAPI = new VideoAPI();
