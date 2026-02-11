/**
 * 图片生成模块
 * Image Generation Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.ImageGenerationMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
    openImageGenConfigModal() {
        const modal = document.getElementById('imageGenConfigModal');
        if (!modal) return;
        
        // 加载已保存的配置
        const config = this.getImageGenConfig();
        document.getElementById('imgGenProvider').value = config.provider || '';
        document.getElementById('imgGenApiUrl').value = config.apiUrl || '';
        document.getElementById('imgGenApiKey').value = config.apiKey || '';
        document.getElementById('imgGenModel').value = config.model || '';
        document.getElementById('imgGenSize').value = config.size || '1024x1024';
        document.getElementById('imgGenSaveToProject').checked = config.saveToProject || false;
        
        modal.style.display = 'flex';
    },

    closeImageGenConfigModal() {
        const modal = document.getElementById('imageGenConfigModal');
        if (modal) modal.style.display = 'none';
    },

    async saveImageGenConfig() {
        const config = {
            provider: document.getElementById('imgGenProvider').value,
            apiUrl: document.getElementById('imgGenApiUrl').value.trim(),
            apiKey: document.getElementById('imgGenApiKey').value.trim(),
            model: document.getElementById('imgGenModel').value,
            size: document.getElementById('imgGenSize').value,
            saveToProject: document.getElementById('imgGenSaveToProject').checked
        };
        
        // 验证必填字段
        if (!config.provider) {
            this.showToast('请选择服务提供商', 'warning');
            return;
        }
        if (!config.apiUrl) {
            this.showToast('请输入 API URL', 'warning');
            return;
        }
        
        // 保存到本地存储
        localStorage.setItem('shortDrama_imageGenConfig', JSON.stringify({
            provider: config.provider,
            apiUrl: config.apiUrl,
            model: config.model,
            size: config.size,
            // 注意：API Key 单独存储以提高安全性
        }));
        
        if (config.apiKey) {
            localStorage.setItem('shortDrama_imageGenApiKey', config.apiKey);
        }
        
        // 如果选择保存到项目，则同步到项目配置
        if (config.saveToProject && this.currentProject?.id) {
            try {
                const projectConfig = {
                    imageGen: {
                        provider: config.provider,
                        apiUrl: config.apiUrl,
                        model: config.model,
                        size: config.size
                        // API Key 不保存到项目
                    }
                };
                
                const response = await fetch(`/api/projects/${this.currentProject.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ settings: projectConfig })
                });
                
                if (response.ok) {
                    this.showToast('配置已保存到项目', 'success');
                }
            } catch (error) {
                console.error('保存项目配置失败:', error);
            }
        }
        
        this.closeImageGenConfigModal();
        this.showToast('💾 图片生成配置已保存', 'success');
    },

    getImageGenConfig() {
        let config = {};
        if (this.currentProject?.settings?.imageGen) {
            config = { ...this.currentProject.settings.imageGen };
        }
        
        const localConfig = localStorage.getItem('shortDrama_imageGenConfig');
        if (localConfig) {
            try {
                const parsed = JSON.parse(localConfig);
                config = { ...config, ...parsed };
            } catch (e) {
                console.error('Parse local config failed:', e);
            }
        }
        
        const apiKey = localStorage.getItem('shortDrama_imageGenApiKey');
        if (apiKey) {
            config.apiKey = apiKey;
        }
        
        return config;
    },

    getSystemImageGenConfig() {
        // 这些是与config/config.py中nanobanana配置对应的默认值
        return {
            provider: 'nano-banana',
            apiUrl: 'https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent',
            model: 'gemini-3-pro-image-preview',
            size: '2K'  // 默认2K竖屏 (1440x2560)，可选 1K/2K/4K
        };
    },

    async showImageGenConfig() {
        const modal = document.createElement('div');
        modal.className = 'modal-overlay';
        modal.style.cssText = `
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.8); display: flex;
            justify-content: center; align-items: center; z-index: 10000;
        `;

        // 获取系统默认配置
        const systemConfig = this.getSystemImageGenConfig();
        
        // 从后端获取当前配置
        let config = this.getImageGenConfig();
        try {
            const response = await fetch('/api/image-gen/config');
            const result = await response.json();
            if (result.success && result.configured) {
                config = {
                    provider: result.provider || config.provider,
                    apiUrl: result.api_url || config.apiUrl,
                    apiKey: result.api_key || config.apiKey,
                    model: result.model || config.model,
                    size: result.size || config.size
                };
            }
        } catch (e) {
            console.log('获取后端配置失败，使用本地缓存:', e);
        }
        
        // 优先级：已保存配置 > 系统默认配置
        const finalConfig = {
            provider: config.provider || systemConfig.provider,
            apiUrl: config.apiUrl || systemConfig.apiUrl,
            apiKey: config.apiKey || '',
            model: config.model || systemConfig.model,
            size: config.size || systemConfig.size
        };
        
        // 获取项目方向设置
        const settings = this.currentProject?.settings || {};
        const aspectRatio = settings.aspect_ratio || '9:16';
        const isLandscape = aspectRatio === '16:9';
        const isSquare = aspectRatio === '1:1';
        const orientationText = isLandscape ? '横屏' : (isSquare ? '方形' : '竖屏');

        modal.innerHTML = `
            <div class="modal-content" style="
                background: var(--bg-secondary); border-radius: 16px;
                max-width: 500px; width: 90%; padding: 2rem;
                box-shadow: 0 25px 80px rgba(0,0,0,0.4);
            ">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                    <h2 style="margin: 0;">🖼️ 图片生成配置</h2>
                    <button class="btn-close" onclick="this.closest('.modal-overlay').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer;">✕</button>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">服务提供商</label>
                    <select id="imgGenProviderModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="" style="background: var(--bg-dark); color: var(--text-primary);">-- 请选择 --</option>
                        <option value="nano-banana" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'nano-banana' ? 'selected' : ''}>Nano Banana (推荐)</option>
                        <option value="openai" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'openai' ? 'selected' : ''}>OpenAI (DALL-E)</option>
                        <option value="stability" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'stability' ? 'selected' : ''}>Stability AI</option>
                        <option value="midjourney" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'midjourney' ? 'selected' : ''}>Midjourney API</option>
                        <option value="custom" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.provider === 'custom' ? 'selected' : ''}>自定义</option>
                    </select>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API URL</label>
                    <input type="text" id="imgGenApiUrlModal" value="${finalConfig.apiUrl || ''}" placeholder="https://api.nanobanana.com/v1/images" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">API Key</label>
                    <input type="password" id="imgGenApiKeyModal" value="${finalConfig.apiKey || ''}" placeholder="请输入API Key" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                        🔒 配置将保存到服务器
                    </div>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认模型</label>
                    <select id="imgGenModelModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="" style="background: var(--bg-dark); color: var(--text-primary);">-- 请选择 --</option>
                        <optgroup label="Nano Banana" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="flux-1.1-pro" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-1.1-pro' ? 'selected' : ''}>FLUX 1.1 Pro (推荐)</option>
                            <option value="flux-pro" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-pro' ? 'selected' : ''}>FLUX Pro</option>
                            <option value="flux-dev" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-dev' ? 'selected' : ''}>FLUX Dev</option>
                            <option value="flux-schnell" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'flux-schnell' ? 'selected' : ''}>FLUX Schnell (快速)</option>
                        </optgroup>
                        <optgroup label="OpenAI" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="dall-e-3" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'dall-e-3' ? 'selected' : ''}>DALL-E 3</option>
                            <option value="dall-e-2" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'dall-e-2' ? 'selected' : ''}>DALL-E 2</option>
                        </optgroup>
                        <optgroup label="Stability AI" style="background: var(--bg-dark); color: var(--text-primary);">
                            <option value="sd-xl" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'sd-xl' ? 'selected' : ''}>Stable Diffusion XL</option>
                            <option value="sd-3" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.model === 'sd-3' ? 'selected' : ''}>Stable Diffusion 3</option>
                        </optgroup>
                    </select>
                </div>

                <div style="margin-bottom: 1rem;">
                    <label style="font-weight: 600; display: block; margin-bottom: 0.5rem;">默认尺寸 (${orientationText})</label>
                    <select id="imgGenSizeModal" class="form-select" style="
                        width: 100%; padding: 10px; background: var(--bg-dark);
                        border: 1px solid var(--border); border-radius: 8px;
                        color: var(--text-primary); font-size: 1rem;
                    ">
                        <option value="4K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '4K' ? 'selected' : ''}>4K (${isLandscape ? '3840x2160' : (isSquare ? '2160x2160' : '2160x3840')} ${orientationText} 推荐)</option>
                        <option value="2K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '2K' ? 'selected' : ''}>2K (${isLandscape ? '2560x1440' : (isSquare ? '1440x1440' : '1440x2560')} ${orientationText})</option>
                        <option value="1K" style="background: var(--bg-dark); color: var(--text-primary);" ${finalConfig.size === '1K' ? 'selected' : ''}>1K (${isLandscape ? '1920x1080' : (isSquare ? '1080x1080' : '1080x1920')} ${orientationText})</option>
                    </select>
                    <div style="font-size: 0.75rem; color: var(--text-tertiary); margin-top: 4px;">
                        💡 当前项目设置为${orientationText} (${aspectRatio})，尺寸对应 NanoBanana 服务的 1K/2K/4K 规格
                    </div>
                </div>

                <div style="display: flex; gap: 1rem; margin-top: 1.5rem;">
                    <button id="saveImgGenConfigBtn" class="btn btn-primary" style="flex: 1;">保存配置</button>
                    <button class="btn btn-secondary" onclick="this.closest('.modal-overlay').remove()" style="flex: 1;">取消</button>
                </div>

                <div style="margin-top: 1rem; padding: 1rem; background: var(--bg-tertiary); border-radius: 8px; font-size: 0.85rem; color: var(--text-secondary);">
                    <p style="margin: 0 0 0.5rem 0;">📌 获取Nano Banana API密钥：</p>
                    <ol style="margin: 0; padding-left: 1.5rem;">
                        <li>访问 <a href="https://nanobanana.com" target="_blank" style="color: var(--primary);">Nano Banana官网</a></li>
                        <li>注册并登录账号</li>
                        <li>在控制台创建API Key</li>
                    </ol>
                </div>
            </div>
        `;

        document.body.appendChild(modal);

        // 点击背景关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });

        // 保存配置
        const saveBtn = modal.querySelector('#saveImgGenConfigBtn');
        saveBtn.addEventListener('click', async () => {
            const provider = modal.querySelector('#imgGenProviderModal').value;
            const apiUrl = modal.querySelector('#imgGenApiUrlModal').value.trim();
            const apiKey = modal.querySelector('#imgGenApiKeyModal').value.trim();
            const model = modal.querySelector('#imgGenModelModal').value;
            const size = modal.querySelector('#imgGenSizeModal').value;

            if (!provider) {
                this.showToast('请选择服务提供商', 'warning');
                return;
            }
            if (!apiUrl) {
                this.showToast('请输入 API URL', 'warning');
                return;
            }
            if (!apiKey) {
                this.showToast('请输入 API Key', 'warning');
                return;
            }

            // 保存到localStorage
            localStorage.setItem('shortDrama_imageGenConfig', JSON.stringify({
                provider: provider,
                apiUrl: apiUrl,
                model: model,
                size: size
            }));
            localStorage.setItem('shortDrama_imageGenApiKey', apiKey);

            // 同步到后端
            try {
                const response = await fetch('/api/image-gen/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        provider: provider,
                        api_url: apiUrl,
                        api_key: apiKey,
                        model: model,
                        size: size
                    })
                });

                const result = await response.json();
                if (result.success) {
                    this.showToast('💾 图片生成配置已保存并生效', 'success');
                    modal.remove();
                } else {
                    this.showToast(`保存失败: ${result.error}`, 'error');
                }
            } catch (error) {
                console.error('保存图片配置失败:', error);
                this.showToast('保存失败，请检查网络', 'error');
            }
        });
    },

    async generateImage(prompt, options = {}) {
        const config = this.getImageGenConfig();
        
        if (!config.apiUrl || !config.apiKey) {
            this.showToast('请先配置图片生成服务', 'warning');
            this.showImageGenConfig();
            return null;
        }
        
        try {
            this.showToast('🎨 正在生成图片...', 'info');
            
            const requestBody = {
                prompt: prompt,
                model: options.model || config.model || 'dall-e-3',
                size: options.size || config.size || '1024x1024',
                n: 1,
                ...options
            };
            
            const response = await fetch(config.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${config.apiKey}`
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error?.message || `生成失败: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 解析不同 API 格式
            let imageUrl = null;
            if (data.data?.[0]?.url) {
                imageUrl = data.data[0].url; // OpenAI 格式
            } else if (data.artifacts?.[0]?.base64) {
                imageUrl = `data:image/png;base64,${data.artifacts[0].base64}`; // Stability 格式
            } else if (data.image_url) {
                imageUrl = data.image_url; // 通用格式
            }
            
            if (imageUrl) {
                this.showToast('✅ 图片生成成功', 'success');
                return imageUrl;
            } else {
                throw new Error('未能获取图片 URL');
            }
            
        } catch (error) {
            console.error('图片生成失败:', error);
            this.showToast(`❌ 生成失败: ${error.message}`, 'error');
            return null;
        }
    },

    initImageTaskManager() {
        // 开始轮询任务状态
        this.startImageTaskPolling();
    },

    startImageTaskPolling() {
        if (this.imageTaskPolling) return;
        
        this.imageTaskPolling = setInterval(() => {
            this.pollImageTasks();
        }, 2000); // 每2秒轮询一次
    },

    stopImageTaskPolling() {
        if (this.imageTaskPolling) {
            clearInterval(this.imageTaskPolling);
            this.imageTaskPolling = null;
        }
    },

    async pollImageTasks() {
        const pendingTasks = Array.from(this.imageTasks.values())
            .filter(t => t.status === 'pending' || t.status === 'running');
        
        if (pendingTasks.length === 0) return;
        
        for (const task of pendingTasks) {
            try {
                const response = await fetch(
                    `/api/short-drama/projects/${this.currentProject.id}/visual-assets/tasks/${task.task_id}`
                );
                const result = await response.json();
                
                if (result.success) {
                    const serverTask = result.task;
                    const oldStatus = task.status;
                    
                    // 更新本地状态
                    task.status = serverTask.status;
                    task.progress = serverTask.progress || 0;
                    task.result = serverTask.result;
                    task.error = serverTask.error;
                    
                    // 状态变化通知
                    if (serverTask.status !== oldStatus) {
                        if (serverTask.status === 'completed') {
                            this.handleImageTaskCompleted(task);
                        } else if (serverTask.status === 'failed') {
                            this.handleImageTaskFailed(task);
                        }
                    }
                    
                    // 刷新任务列表显示（进度更新也触发刷新）
                    this.updateImageTaskList();
                }
            } catch (error) {
                console.error(`轮询任务 ${task.task_id} 失败:`, error);
            }
        }
    },

    handleImageTaskCompleted(task) {
        const result = task.result;
        if (!result?.success) return;
        
        const { category, name, data } = task;
        const asset = this.currentProject?.visualAssets?.[category]?.[name];
        if (!asset) return;
        
        // 更新资产数据
        const imageUrl = result.data?.referenceUrl;
        const localPath = result.data?.localPath;
        if (imageUrl) {
            asset.referenceUrl = imageUrl;
            asset.localPath = localPath;
            asset.updatedAt = new Date().toISOString();
            
            // 更新 characterPortraits
            if (category === 'characters') {
                if (!this.characterPortraits.has(name)) {
                    this.characterPortraits.set(name, {});
                }
                this.characterPortraits.get(name).mainPortrait = {
                    url: imageUrl,
                    path: localPath,
                    generatedAt: new Date().toISOString()
                };
                this.refreshPortraitCanvas();
            }
            
            // 刷新显示
            this.selectVisualAsset(category.slice(0, -1), asset, imageUrl);
            this.loadVisualAssetsGrid(category);
            
            this.showToast(`✅ ${name} 图片生成完成`, 'success');
        }
    },

    handleImageTaskFailed(task) {
        this.showToast(`❌ ${task.name} 生成失败: ${task.error || '未知错误'}`, 'error');
    },

    async generateAssetImage(name, type) {
        const typeMap = {
            'character': 'characters',
            'scene': 'scenes', 
            'prop': 'props'
        };
        const category = typeMap[type];
        const asset = this.currentProject?.visualAssets?.[category]?.[name];
        
        if (!asset) {
            this.showToast('资产不存在', 'error');
            return;
        }
        
        // 检查是否已有进行中的任务
        const existingTask = Array.from(this.imageTasks.values())
            .find(t => t.name === name && t.category === category && 
                 (t.status === 'pending' || t.status === 'running'));
        if (existingTask) {
            this.showToast(`⚠️ ${name} 正在生成中，请耐心等待`, 'warning');
            return;
        }
        
        // 构建生成提示词
        let prompt = '';
        const description = asset.description || '';
        
        if (type === 'character') {
            prompt = JSON.stringify({
                type: 'character',
                id: name,
                name: name,
                raw_description: description || '',
                raw_clothing: asset.clothing || '',
                raw_expression: asset.expression || ''
            });
        } else if (type === 'scene') {
            const lighting = asset.lighting || '';
            const colorTone = asset.colorTone || '';
            let sceneDesc = description;
            if (sceneDesc && /[\u4e00-\u9fa5]/.test(sceneDesc)) {
                sceneDesc = 'detailed environment';
            }
            prompt = `Cinematic scene "${name}"`;
            prompt += `, SCENE_TAG: LOCATION_${name.replace(/\s+/g, '_').toUpperCase()}`;
            if (sceneDesc) prompt += `, ${sceneDesc}`;
            if (lighting) prompt += `, ${lighting} lighting`;
            if (colorTone) prompt += `, ${colorTone} color tone`;
            prompt += `, high quality, detailed environment, cinematic composition, photorealistic, 8k, sharp focus`;
        } else if (type === 'prop') {
            const propCategory = asset.category || '';
            let propDesc = description;
            if (propDesc && /[\u4e00-\u9fa5]/.test(propDesc)) {
                propDesc = 'detailed object';
            }
            prompt = `Detailed product shot of "${name}"`;
            prompt += `, PROP_TAG: ITEM_${name.replace(/\s+/g, '_').toUpperCase()}`;
            if (propDesc) prompt += `, ${propDesc}`;
            if (propCategory) prompt += `, ${propCategory}`;
            prompt += `, high quality, detailed, product photography style, clean background, photorealistic, 8k`;
        }
        
        // 获取视频设置
        const settings = this.currentProject?.settings || {};
        let aspectRatio, imageSize;
        if (type === 'character') {
            aspectRatio = '16:9';
            imageSize = '4K';
        } else {
            aspectRatio = settings.aspect_ratio || '9:16';
            const quality = settings.quality || '2K';
            imageSize = quality === '4K' ? '4K' : (quality === '2K' ? '2K' : '1K');
        }
        
        // 构建请求体
        const requestBody = {
            category: category,
            name: name,
            prompt: prompt,
            aspect_ratio: aspectRatio,
            image_size: imageSize
        };
        if (type === 'character') {
            requestBody.description = asset.description || '';
            requestBody.clothing = asset.clothing || '';
            requestBody.expression = asset.expression || '';
        }
        
        try {
            const response = await fetch(`/api/short-drama/projects/${this.currentProject.id}/visual-assets/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody)
            });
            
            const result = await response.json();
            
            if (result.success) {
                // 添加到本地任务列表
                const task = {
                    task_id: result.task_id,
                    project_id: this.currentProject.id,
                    category: category,
                    name: name,
                    type: type,
                    status: result.status,
                    created_at: new Date().toISOString(),
                    result: null,
                    error: null
                };
                this.imageTasks.set(result.task_id, task);
                
                this.showToast(`🚀 ${name} 生成任务已提交（队列）`, 'success');
                
                // 显示任务列表
                this.showImageTaskList();
                
                // 立即轮询一次
                this.pollImageTasks();
            } else {
                this.showToast(`❌ ${result.error || '提交失败'}`, 'error');
            }
        } catch (error) {
            console.error('提交生成任务失败:', error);
            this.showToast(`❌ 提交失败: ${error.message}`, 'error');
        }
    },

    showImageTaskList() {
        // 检查是否已有面板
        let panel = document.getElementById('image-task-panel');
        if (panel) {
            this.updateImageTaskList();
            return;
        }
        
        // 创建面板
        panel = document.createElement('div');
        panel.id = 'image-task-panel';
        panel.className = 'image-task-panel';
        panel.innerHTML = `
            <div class="task-panel-header">
                <h4>🎨 图片生成队列</h4>
                <button class="btn-close" onclick="shortDramaStudio.hideImageTaskList()">✕</button>
            </div>
            <div class="task-panel-body" id="task-panel-body">
                <div class="task-empty">暂无生成任务</div>
            </div>
        `;
        
        document.body.appendChild(panel);
        this.updateImageTaskList();
        
        // 添加样式
        if (!document.getElementById('image-task-panel-styles')) {
            const styles = document.createElement('style');
            styles.id = 'image-task-panel-styles';
            styles.textContent = `
                .image-task-panel {
                    position: fixed;
                    right: 20px;
                    top: 80px;
                    width: 320px;
                    background: rgba(15, 23, 42, 0.95);
                    border: 1px solid rgba(99, 102, 241, 0.3);
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
                    z-index: 9999;
                    backdrop-filter: blur(10px);
                }
                .task-panel-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 16px;
                    border-bottom: 1px solid rgba(99, 102, 241, 0.2);
                }
                .task-panel-header h4 {
                    margin: 0;
                    color: #fff;
                    font-size: 14px;
                }
                .task-panel-body {
                    max-height: 400px;
                    overflow-y: auto;
                    padding: 8px;
                }
                .task-item {
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    padding: 10px 12px;
                    margin-bottom: 6px;
                    background: rgba(30, 41, 59, 0.8);
                    border-radius: 8px;
                    border-left: 3px solid #6366f1;
                    transition: all 0.3s;
                }
                .task-item.pending { border-left-color: #f59e0b; }
                .task-item.running { border-left-color: #3b82f6; }
                .task-item.completed { border-left-color: #10b981; }
                .task-item.failed { border-left-color: #ef4444; }
                .task-item-icon {
                    font-size: 20px;
                }
                .task-item-info {
                    flex: 1;
                    min-width: 0;
                }
                .task-item-name {
                    font-size: 13px;
                    color: #fff;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .task-item-status {
                    font-size: 11px;
                    color: rgba(255,255,255,0.6);
                    margin-top: 2px;
                }
                .task-item-progress {
                    width: 60px;
                    height: 4px;
                    background: rgba(255,255,255,0.1);
                    border-radius: 2px;
                    overflow: hidden;
                }
                .task-item-progress-bar {
                    height: 100%;
                    background: linear-gradient(90deg, #6366f1, #8b5cf6);
                    border-radius: 2px;
                    transition: width 0.3s ease;
                }
                .task-item-running .task-item-progress-bar {
                    animation: progress-pulse 1.5s ease-in-out infinite;
                }
                @keyframes progress-pulse {
                    0%, 100% { opacity: 0.6; }
                    50% { opacity: 1; }
                }
                .task-empty {
                    text-align: center;
                    padding: 30px;
                    color: rgba(255,255,255,0.5);
                    font-size: 13px;
                }
            `;
            document.head.appendChild(styles);
        }
    },

    hideImageTaskList() {
        const panel = document.getElementById('image-task-panel');
        if (panel) {
            panel.remove();
        }
    },

    updateImageTaskList() {
        const body = document.getElementById('task-panel-body');
        if (!body) return;
        
        const tasks = Array.from(this.imageTasks.values())
            .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
        
        if (tasks.length === 0) {
            body.innerHTML = '<div class="task-empty">暂无生成任务</div>';
            return;
        }
        
        const statusIcons = {
            'pending': '⏳',
            'running': '🎨',
            'completed': '✅',
            'failed': '❌'
        };
        const statusText = {
            'pending': '等待中',
            'running': '生成中...',
            'completed': '完成',
            'failed': '失败'
        };
        
        // 只显示最近的10个任务
        const recentTasks = tasks.slice(0, 10);
        
        body.innerHTML = recentTasks.map(task => {
            const progress = task.progress || 0;
            const showProgress = task.status === 'running' || task.status === 'pending';
            const runningClass = task.status === 'running' ? 'task-item-running' : '';
            return `
            <div class="task-item ${task.status} ${runningClass}">
                <div class="task-item-icon">${statusIcons[task.status]}</div>
                <div class="task-item-info">
                    <div class="task-item-name">${task.name}</div>
                    <div class="task-item-status">${statusText[task.status]}${showProgress && progress > 0 ? ` ${progress}%` : ''}</div>
                </div>
                ${showProgress ? `
                <div class="task-item-progress">
                    <div class="task-item-progress-bar" style="width: ${progress}%"></div>
                </div>
                ` : ''}
            </div>
        `}).join('');
    }
    };
}));
