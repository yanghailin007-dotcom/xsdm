/**
 * 人物剧照工作室 - 简化版
 * 专注于参考图上传和提示词编辑
 * 支持多张参考图上传
 */

class PortraitStudio {
    constructor() {
        this.referenceImages = [];  // 改为数组，存储多张参考图
        this.generatedImageUrl = null;
        this.maxRefImages = 5;  // 最多支持5张参考图
        
        this.init();
    }
    
    init() {
        console.log('🎨 人物剧照工作室初始化...');
        this.bindEvents();
        console.log('✅ 初始化完成');
    }
    
    bindEvents() {
        // 参考图上传
        this.setupReferenceUpload();
        
        // 提示词操作
        document.getElementById('copyPromptBtn')?.addEventListener('click', () => {
            this.copyPrompt();
        });
        
        // 比例选择
        document.querySelectorAll('.ratio-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.ratio-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
            });
        });
        
        // 生成按钮
        document.getElementById('generateBtn')?.addEventListener('click', () => {
            this.generatePortrait();
        });
        
        // 结果操作
        document.getElementById('downloadResultBtn')?.addEventListener('click', () => {
            this.downloadResult();
        });
        
        document.getElementById('useAsRefBtn')?.addEventListener('click', () => {
            this.useAsReference();
        });
        
        document.getElementById('regenerateBtn')?.addEventListener('click', () => {
            this.generatePortrait();
        });
        
        // 模板按钮
        document.querySelectorAll('.template-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                this.applyTemplate(btn.dataset.template);
            });
        });
    }
    
    setupReferenceUpload() {
        const uploadZone = document.getElementById('refUploadZone');
        const fileInput = document.getElementById('refFileInput');
        
        if (uploadZone && fileInput) {
            // 点击上传
            uploadZone.addEventListener('click', () => {
                fileInput.click();
            });
            
            // 文件选择
            fileInput.addEventListener('change', (e) => {
                const files = e.target.files;
                if (files && files.length > 0) {
                    this.handleImageUpload(files);
                }
            });
            
            // 拖拽上传
            uploadZone.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadZone.style.borderColor = '#8b5cf6';
            });
            
            uploadZone.addEventListener('dragleave', () => {
                uploadZone.style.borderColor = '';
            });
            
            uploadZone.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadZone.style.borderColor = '';
                
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    this.handleImageUpload(files);
                }
            });
        }
    }
    
    handleImageUpload(files) {
        // 处理多个文件
        const fileArray = Array.from(files);
        
        // 检查数量限制
        if (this.referenceImages.length + fileArray.length > this.maxRefImages) {
            this.showToast(`最多只能上传${this.maxRefImages}张参考图`, 'error');
            return;
        }
        
        let processedCount = 0;
        
        fileArray.forEach(file => {
            if (!file.type.startsWith('image/')) {
                this.showToast(`文件 ${file.name} 不是图片`, 'error');
                return;
            }
            
            const reader = new FileReader();
            reader.onload = (e) => {
                // 添加到参考图数组
                this.referenceImages.push({
                    id: Date.now() + Math.random(),
                    name: file.name,
                    data: e.target.result
                });
                
                processedCount++;
                
                // 所有文件处理完成后更新UI
                if (processedCount === fileArray.length) {
                    this.updateReferencePreview();
                    this.showToast(`成功上传${processedCount}张参考图`, 'success');
                }
            };
            reader.readAsDataURL(file);
        });
    }
    
    updateReferencePreview() {
        const uploadZone = document.getElementById('refUploadZone');
        const placeholder = uploadZone.querySelector('.upload-placeholder');
        const previewContainer = document.getElementById('refPreviewContainer');
        const countInfo = document.getElementById('refCountInfo');
        const countSpan = document.getElementById('refCount');
        
        // 清空预览容器
        previewContainer.innerHTML = '';
        
        if (this.referenceImages.length === 0) {
            // 没有参考图
            placeholder.style.display = 'block';
            previewContainer.style.display = 'none';
            countInfo.style.display = 'none';
        } else {
            // 有参考图
            placeholder.style.display = 'none';
            previewContainer.style.display = 'grid';
            countInfo.style.display = 'block';
            countSpan.textContent = this.referenceImages.length;
            
            // 为每张参考图创建预览
            this.referenceImages.forEach((ref, index) => {
                const item = document.createElement('div');
                item.className = 'upload-preview-item';
                
                const img = document.createElement('img');
                img.src = ref.data;
                img.alt = `参考图${index + 1}`;
                
                const removeBtn = document.createElement('button');
                removeBtn.className = 'remove-btn';
                removeBtn.innerHTML = '×';
                removeBtn.onclick = (e) => {
                    e.stopPropagation();
                    this.removeReferenceImage(ref.id);
                };
                
                item.appendChild(img);
                item.appendChild(removeBtn);
                previewContainer.appendChild(item);
            });
        }
    }
    
    removeReferenceImage(id) {
        const index = this.referenceImages.findIndex(ref => ref.id === id);
        if (index !== -1) {
            this.referenceImages.splice(index, 1);
            this.updateReferencePreview();
            this.showToast('参考图已移除', 'success');
        }
    }
    
    removeReference() {
        // 清空所有参考图
        this.referenceImages = [];
        const fileInput = document.getElementById('refFileInput');
        fileInput.value = '';
        
        this.updateReferencePreview();
        this.showToast('所有参考图已移除', 'success');
    }
    
    applyTemplate(templateType) {
        const templates = {
            xianxia: '一位仙风道骨的剑仙，白发如雪，身穿白色仙袍，手持发光的长剑，站在云端之上，仙气缭绕，超凡脱俗',
            modern: '一位现代都市青年，时尚简约的服装，自信的微笑，站在繁华的城市街道，阳光洒在身上，充满活力',
            fantasy: '一位魔法师，身穿华丽的长袍，手持法杖，周围环绕着魔法元素，神秘而强大，奇幻风格',
            sci: '一位未来战士，身穿高科技战甲，手持能量武器，站在充满科技感的城市中，霓虹灯光闪烁，赛博朋克风格',
            romance: '一位温柔美丽的少女，长发飘逸，身穿轻盈的连衣裙，站在花海中，阳光柔和，浪漫唯美'
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
    
    async generatePortrait() {
        const prompt = document.getElementById('promptEditor').value.trim();
        
        if (!prompt) {
            this.showToast('请输入提示词', 'error');
            return;
        }
        
        const aspectRatio = document.querySelector('.ratio-btn.active')?.dataset.ratio || '9:16';
        const quality = document.getElementById('qualitySelect').value;
        const style = document.getElementById('styleSelect').value;
        
        // 显示进度
        document.getElementById('progressCard').style.display = 'block';
        document.getElementById('resultCard').style.display = 'none';
        document.getElementById('generateBtn').disabled = true;
        
        try {
            this.showToast('正在生成剧照...', 'success');
            
            const requestData = {
                prompt: prompt,
                aspect_ratio: aspectRatio,
                image_size: quality,
                reference_images: this.referenceImages.map(ref => ref.data),  // 改为数组
                style: style
            };
            
            const response = await fetch('/api/video/generate-character-portrait', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.generatedImageUrl = data.image_url;
                
                // 显示结果
                document.getElementById('resultImage').src = data.image_url;
                document.getElementById('resultCard').style.display = 'block';
                
                this.showToast('剧照生成成功！', 'success');
            } else {
                throw new Error(data.error || '生成失败');
            }
        } catch (error) {
            console.error('生成剧照失败:', error);
            this.showToast('生成失败: ' + error.message, 'error');
        } finally {
            document.getElementById('progressCard').style.display = 'none';
            document.getElementById('generateBtn').disabled = false;
        }
    }
    
    downloadResult() {
        if (!this.generatedImageUrl) {
            this.showToast('没有可下载的剧照', 'error');
            return;
        }
        
        const link = document.createElement('a');
        link.href = this.generatedImageUrl;
        link.download = `portrait_${Date.now()}.png`;
        link.click();
        
        this.showToast('剧照下载已开始', 'success');
    }
    
    useAsReference() {
        if (!this.generatedImageUrl) {
            this.showToast('没有可用的剧照', 'error');
            return;
        }
        
        // 检查数量限制
        if (this.referenceImages.length >= this.maxRefImages) {
            this.showToast(`最多只能上传${this.maxRefImages}张参考图，请先删除一些`, 'error');
            return;
        }
        
        // 将生成的剧照添加为参考图
        this.referenceImages.push({
            id: Date.now(),
            name: `生成剧照_${Date.now()}.png`,
            data: this.generatedImageUrl
        });
        
        this.updateReferencePreview();
        this.showToast('已将当前剧照添加为参考图', 'success');
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
    const studio = new PortraitStudio();
    window.portraitStudio = studio;
});