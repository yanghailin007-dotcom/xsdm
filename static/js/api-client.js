/**
 * API 客户端 - 自动处理 Token、错误重试
 */
class ApiClient {
    constructor(options = {}) {
        this.baseURL = options.baseURL || '';
        this.timeout = options.timeout || 30000;
        this.retryCount = options.retryCount || 1;
        
        // 请求拦截器队列
        this.requestInterceptors = [];
        // 响应拦截器队列
        this.responseInterceptors = [];
        
        // 默认添加 Token 拦截器
        this.addRequestInterceptor(this.tokenInterceptor.bind(this));
        
        console.log('[ApiClient] 初始化完成');
    }

    // ==================== 拦截器 ====================

    addRequestInterceptor(fn) {
        this.requestInterceptors.push(fn);
    }

    addResponseInterceptor(fn) {
        this.responseInterceptors.push(fn);
    }

    /**
     * Token 拦截器 - 自动附加 Authorization Header
     */
    async tokenInterceptor(config) {
        // 如果已经设置了 Authorization，不覆盖
        if (config.headers && config.headers['Authorization']) {
            return config;
        }

        // 尝试从 AccountManager 获取 Token
        if (window.accountManager) {
            try {
                const token = await window.accountManager.getValidToken();
                config.headers = config.headers || {};
                config.headers['Authorization'] = `Bearer ${token}`;
            } catch (e) {
                // Token 获取失败，可能是未登录
                console.warn('[ApiClient] 无法获取 Token:', e.message);
            }
        }

        return config;
    }

    // ==================== 核心请求方法 ====================

    async request(endpoint, options = {}) {
        const url = endpoint.startsWith('http') ? endpoint : `${this.baseURL}${endpoint}`;
        
        // 构建配置
        let config = {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            ...options
        };

        // 应用请求拦截器
        for (const interceptor of this.requestInterceptors) {
            config = await interceptor(config);
        }

        // 处理请求体
        if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
            config.body = JSON.stringify(config.body);
        }

        // 发送请求（带超时控制）
        let lastError;
        for (let attempt = 0; attempt <= this.retryCount; attempt++) {
            try {
                const response = await this.fetchWithTimeout(url, config);
                
                // 处理响应
                const result = await this.handleResponse(response);
                
                // 应用响应拦截器
                for (const interceptor of this.responseInterceptors) {
                    await interceptor(result, response);
                }
                
                return result;
                
            } catch (error) {
                lastError = error;
                
                // 如果是 401，尝试刷新 Token 后重试
                if (error.code === 'AUTH_REQUIRED' || error.code === 'TOKEN_EXPIRED') {
                    const refreshed = await this.handleAuthError();
                    if (refreshed) {
                        // 重新获取 Token 并继续循环
                        continue;
                    }
                }
                
                // 其他错误或不需要重试
                if (attempt < this.retryCount && this.shouldRetry(error)) {
                    await this.delay(1000 * (attempt + 1)); // 指数退避
                    continue;
                }
                
                throw error;
            }
        }
        
        throw lastError;
    }

    async fetchWithTimeout(url, config) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);
        
        try {
            const response = await fetch(url, {
                ...config,
                signal: controller.signal
            });
            return response;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    async handleResponse(response) {
        // 解析 JSON
        let data;
        const contentType = response.headers.get('content-type') || '';
        
        if (contentType.includes('application/json')) {
            data = await response.json();
        } else {
            const text = await response.text();
            data = { success: response.ok, data: text };
        }

        // 处理 HTTP 错误
        if (!response.ok) {
            const error = new Error(data.error || data.message || `HTTP ${response.status}`);
            error.code = data.code || `HTTP_${response.status}`;
            error.status = response.status;
            error.data = data;
            
            // 特殊处理 401
            if (response.status === 401) {
                error.code = data.code || 'AUTH_REQUIRED';
            }
            
            throw error;
        }

        return data;
    }

    /**
     * 处理认证错误 - 尝试刷新 Token
     */
    async handleAuthError() {
        if (!window.accountManager) return false;
        
        const account = window.accountManager.getCurrentAccount();
        if (!account || account.needsRelogin) return false;

        try {
            console.log('[ApiClient] 尝试刷新 Token...');
            await window.accountManager.refreshToken(account);
            return true;
        } catch (e) {
            console.error('[ApiClient] Token 刷新失败:', e);
            return false;
        }
    }

    shouldRetry(error) {
        // 网络错误、超时、5xx 服务器错误可以重试
        return !error.status || error.status >= 500 || error.name === 'AbortError';
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // ==================== 快捷方法 ====================

    get(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'GET' });
    }

    post(endpoint, body, options = {}) {
        return this.request(endpoint, { ...options, method: 'POST', body });
    }

    put(endpoint, body, options = {}) {
        return this.request(endpoint, { ...options, method: 'PUT', body });
    }

    delete(endpoint, options = {}) {
        return this.request(endpoint, { ...options, method: 'DELETE' });
    }

    upload(endpoint, formData, options = {}) {
        return this.request(endpoint, {
            ...options,
            method: 'POST',
            body: formData,
            headers: {} // 让浏览器自动设置 Content-Type (multipart/form-data)
        });
    }
}

// 创建全局实例
window.apiClient = new ApiClient();

// 兼容性导出
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ApiClient;
}
