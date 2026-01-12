/**
 * 视频工作室 - 专注于视频生成
 * 支持自定义提示词和多种视频配置
 */

class VideoStudio {
    constructor() {
        this.generatedVideoUrl = null;
        this.selectedRatio = '16:9';
        
        this.init();
    }
    
    init() {
        console.log('🎬 视频工作室初始化...');
        this.bindEvents();
        console.log('✅ 初始化完成');
    }
    
    bindEvents() {
        // 提示词操作
        document.getElementById('copyPromptBtn')?.addEventListener('click', () => {
            this.copyPrompt();
        });
        
        // 比例选择
        document.querySelectorAll('.ratio-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.ratio-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.selectedRatio = btn.dataset.ratio;
            });
        });
        
        // 生成按钮
        document.getElementById('generateBtn')?.addEventListener('click', () => {
            this.generateVideo();
        });
        
        // 结果操作
        document.getElementById('downloadResultBtn')?.addEventListener('click', () => {
            this.downloadResult();
        });
        
        document.getElementById('regenerateBtn')?.addEventListener('click', () => {
            this.generateVideo();
        });
        
        // 全屏播放按钮
        document.getElementById('fullscreenBtn')?.addEventListener('click', () => {
            this.openFullscreen();
        });
        
        // 关闭全屏按钮
        document.getElementById('closeFullscreenBtn')?.addEventListener('click', () => {
            this.closeFullscreen();
        });
        
        // 点击视频包装器也可以全屏
        document.querySelector('.video-wrapper')?.addEventListener('click', (e) => {
            if (e.target.closest('.fullscreen-btn')) return;
            this.openFullscreen();
        });
        
        // ESC键关闭全屏
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeFullscreen();
            }
        });
        
        // 模板按钮
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyTemplate(btn.dataset.template);
            });
        });
    }
    
    applyTemplate(templateType) {
        const templates = {
            xianxia: '一位仙风道骨的剑仙在云端修行的场景，使用水墨画风，背景是壮观的云海和山峦，仙气缭绕。镜头从远处缓缓推进，展现剑仙的修炼姿态，周围云雾缭绕，仙鹤飞翔，营造出超凡脱俗的仙境氛围。',
            modern: '繁华都市夜景，霓虹灯闪烁，年轻的主角走在街道上，充满活力和希望。使用现代电影风格，镜头跟随主角移动，展现城市的繁华和现代感，背景音乐轻快愉悦。',
            scifi: '未来科技城市，高科技建筑林立，飞行器穿梭。主角身穿高科技战甲，站在城市高处俯瞰。使用赛博朋克风格，霓虹灯光和全息投影交织，营造出强烈的科技感和未来感。',
            fantasy: '神秘的魔法森林，古老的巨树参天，魔法光芒闪烁。魔法师施展强大的魔法咒语，周围元素环绕。使用奇幻魔法风格，镜头缓缓旋转展现魔法效果，色彩丰富绚丽，充满神秘感。',
            nature: '壮丽的自然风光，高山流水，云雾缭绕。镜头从高空俯瞰山脉，展现大自然的壮美。使用写实风格，光影效果真实自然，色彩清新自然，营造出宁静祥和的氛围。'
        };
        
        const prompt = templates[templateType];
        if (prompt) {
            document.getElementById('promptEditor').value = prompt;
            this.showToast('已应用模板', 'success');
        }
    }
    
    copyPrompt() {
        const prompt = document.getElementById('promptEditor').value;
        if (!prompt) {
            this.showToast('提示词为空', 'error');
            return;
        }
        
        navigator.clipboard.writeText(prompt).then(() => {
            this.showToast('提示词已复制到剪贴板', 'success');
        }).catch(() => {
            this.showToast('复制失败', 'error');
        });
    }
    
    async generateVideo() {
        const prompt = document.getElementById('promptEditor').value.trim();
        
        if (!prompt) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        
        const duration = document.getElementById('durationSelect').value;
        const resolution = document.getElementById('resolutionSelect').value;
        const fps = document.getElementById('fpsSelect').value;
        const style = document.getElementById('styleSelect').value;
        
        // 显示进度
        document.getElementById('progressCard').style.display = 'block';
        document.getElementById('resultCard').style.display = 'none';
        document.getElementById('generateBtn').disabled = true;
        
        // 更新进度详情
        this.updateProgressDetail('正在初始化视频生成任务...');
        
        try {
            this.showToast('正在生成视频...', 'success');
            
            // 构建请求数据
            const requestData = {
                model: 'video-model',
                prompt: prompt,
                generation_config: {
                    duration_seconds: parseInt(duration),
                    resolution: resolution,
                    aspect_ratio: this.selectedRatio,
                    fps: parseInt(fps),
                    style: style
                }
            };
            
            this.updateProgressDetail('正在发送生成请求...');
            
            // 调用OpenAI标准视频生成API
            const response = await fetch('/v1/videos/generations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error.message || '生成失败');
            }
            
            // 获取生成任务ID
            const generationId = data.id;
            this.updateProgressDetail(`任务已创建 (ID: ${generationId})，正在生成中...`);
            
            // 轮询查询生成状态
            await this.pollGenerationStatus(generationId);
            
        } catch (error) {
            console.error('生成视频失败:', error);
            this.showToast('生成失败: ' + error.message, 'error');
            this.updateProgressDetail('生成失败: ' + error.message);
        } finally {
            document.getElementById('progressCard').style.display = 'none';
            document.getElementById('generateBtn').disabled = false;
        }
    }
    
    async pollGenerationStatus(generationId) {
        const maxAttempts = 60; // 最多轮询60次
        const pollInterval = 2000; // 每2秒轮询一次
        
        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            try {
                const response = await fetch(`/v1/videos/generations/${generationId}`);
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const data = await response.json();
                
                if (data.error) {
                    throw new Error(data.error.message || '查询失败');
                }
                
                const status = data.status;
                
                // 更新进度信息
                if (status === 'processing') {
                    const progress = data.progress || 0;
                    this.updateProgressDetail(`正在生成中... ${progress}%`);
                } else if (status === 'completed') {
                    // 生成完成
                    this.updateProgressDetail('生成完成！');
                    this.showResult(data.result);
                    this.showToast('视频生成成功！', 'success');
                    return;
                } else if (status === 'failed') {
                    throw new Error(data.error?.message || '生成失败');
                } else if (status === 'cancelled') {
                    throw new Error('生成已取消');
                }
                
                // 继续轮询
                await new Promise(resolve => setTimeout(resolve, pollInterval));
                
            } catch (error) {
                console.error('轮询状态失败:', error);
                throw error;
            }
        }
        
        throw new Error('生成超时，请稍后查看任务状态');
    }
    
    updateProgressDetail(text) {
        const detailElement = document.getElementById('progressDetail');
        if (detailElement) {
            detailElement.textContent = text;
        }
    }
    
    showResult(result) {
        console.log('🎬 显示视频结果:', result);
        
        // 显示结果卡片
        document.getElementById('resultCard').style.display = 'block';
        
        // 设置视频源
        const videoElement = document.getElementById('resultVideo');
        
        // API返回的数据结构是 result.videos[0].url
        if (result.videos && result.videos.length > 0) {
            const video = result.videos[0];
            this.generatedVideoUrl = video.url;
            videoElement.src = video.url;
            console.log('✅ 视频URL已设置:', video.url);
        } else if (result.video_url) {
            // 兼容旧格式
            videoElement.src = result.video_url;
            this.generatedVideoUrl = result.video_url;
            console.log('✅ 视频URL已设置(旧格式):', result.video_url);
        } else if (result.video_path) {
            // 如果是本地路径，需要转换为可访问的URL
            this.generatedVideoUrl = result.video_path;
            videoElement.src = result.video_path;
            console.log('✅ 视频路径已设置:', result.video_path);
        } else {
            console.error('❌ 无法找到视频URL，result结构:', result);
            this.showToast('无法获取视频URL', 'error');
            return;
        }
        
        // 自动播放视频
        videoElement.load();
        videoElement.play().catch(e => {
            console.log('⚠️ 自动播放失败:', e);
        });
    }
    
    downloadResult() {
        if (!this.generatedVideoUrl) {
            this.showToast('没有可下载的视频', 'error');
            return;
        }
        
        const link = document.createElement('a');
        link.href = this.generatedVideoUrl;
        link.download = `video_${Date.now()}.mp4`;
        link.target = '_blank';
        link.click();
        
        this.showToast('视频下载已开始', 'success');
    }
    
    openFullscreen() {
        if (!this.generatedVideoUrl) {
            this.showToast('没有可播放的视频', 'error');
            return;
        }
        
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const fullscreenVideo = document.getElementById('fullscreenVideo');
        
        // 设置全屏视频源
        fullscreenVideo.src = this.generatedVideoUrl;
        
        // 显示全屏播放器
        fullscreenPlayer.style.display = 'flex';
        
        // 播放视频
        fullscreenVideo.play().catch(e => {
            console.log('自动播放失败:', e);
        });
        
        // 阻止body滚动
        document.body.style.overflow = 'hidden';
    }
    
    closeFullscreen() {
        const fullscreenPlayer = document.getElementById('fullscreenPlayer');
        const fullscreenVideo = document.getElementById('fullscreenVideo');
        
        // 暂停视频
        fullscreenVideo.pause();
        
        // 隐藏全屏播放器
        fullscreenPlayer.style.display = 'none';
        
        // 恢复body滚动
        document.body.style.overflow = '';
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
    const studio = new VideoStudio();
    window.videoStudio = studio;
});