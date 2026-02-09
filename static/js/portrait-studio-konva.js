/**
 * 角色剧照工作室 - Konva 无限画布版本
 * 支持：角色/场景/道具分区、拖拽、缩放、画布管理
 */

// ==================== 全局状态 ====================
const StudioState = {
    stage: null,
    layer: null,
    transformer: null,
    scale: 1,
    isDragging: false,
    isPanning: false,
    lastPos: { x: 0, y: 0 },
    selectedNode: null,
    currentTool: 'select', // select, hand
    assets: {
        character: [],
        scene: [],
        prop: []
    },
    canvasItems: [] // 画布上的元素
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    initKonvaStage();
    initUI();
    loadAssets();
    initDragDrop();
});

// ==================== Konva 画布初始化 ====================
function initKonvaStage() {
    const container = document.getElementById('konva-container');
    const { width, height } = container.getBoundingClientRect();

    // 创建舞台
    StudioState.stage = new Konva.Stage({
        container: 'konva-container',
        width: width,
        height: height,
        draggable: false
    });

    // 创建主图层
    StudioState.layer = new Konva.Layer();
    StudioState.stage.add(StudioState.layer);

    // 创建变换器（用于选中框）
    StudioState.transformer = new Konva.Transformer({
        borderStroke: '#6366f1',
        borderStrokeWidth: 2,
        anchorStroke: '#6366f1',
        anchorFill: '#0f172a',
        anchorSize: 8,
        padding: 4,
        keepRatio: true,
        enabledAnchors: ['top-left', 'top-right', 'bottom-left', 'bottom-right']
    });
    StudioState.layer.add(StudioState.transformer);

    // 创建网格背景
    createGridBackground();

    // 绑定事件
    bindStageEvents();
    bindKeyboardEvents();

    // 窗口大小调整
    window.addEventListener('resize', () => {
        const { width, height } = container.getBoundingClientRect();
        StudioState.stage.width(width);
        StudioState.stage.height(height);
    });
}

// ==================== 创建网格背景 ====================
function createGridBackground() {
    const gridLayer = new Konva.Layer();
    const gridSize = 50;
    const stageWidth = 5000; // 大画布
    const stageHeight = 5000;

    // 垂直线
    for (let x = 0; x <= stageWidth; x += gridSize) {
        gridLayer.add(new Konva.Line({
            points: [x, 0, x, stageHeight],
            stroke: 'rgba(99, 102, 241, 0.1)',
            strokeWidth: 1
        }));
    }

    // 水平线
    for (let y = 0; y <= stageHeight; y += gridSize) {
        gridLayer.add(new Konva.Line({
            points: [0, y, stageWidth, y],
            stroke: 'rgba(99, 102, 241, 0.1)',
            strokeWidth: 1
        }));
    }

    // 中心点标记
    const centerX = stageWidth / 2;
    const centerY = stageHeight / 2;
    
    gridLayer.add(new Konva.Circle({
        x: centerX,
        y: centerY,
        radius: 5,
        fill: 'rgba(99, 102, 241, 0.3)'
    }));

    gridLayer.add(new Konva.Text({
        x: centerX + 10,
        y: centerY - 20,
        text: '中心',
        fontSize: 12,
        fill: 'rgba(99, 102, 241, 0.5)'
    }));

    // 区域标记
    const regions = [
        { x: 800, y: 500, name: '🎭 角色区', color: 'rgba(236, 72, 153, 0.3)' },
        { x: 2500, y: 500, name: '🏞️ 场景区', color: 'rgba(34, 197, 94, 0.3)' },
        { x: 4200, y: 500, name: '🎒 道具区', color: 'rgba(245, 158, 11, 0.3)' }
    ];

    regions.forEach(region => {
        // 区域背景
        gridLayer.add(new Konva.Rect({
            x: region.x - 600,
            y: region.y - 300,
            width: 1200,
            height: 2000,
            fill: region.color,
            stroke: region.color.replace('0.3', '0.5'),
            strokeWidth: 2,
            cornerRadius: 16
        }));

        // 区域标题
        gridLayer.add(new Konva.Text({
            x: region.x,
            y: region.y - 250,
            text: region.name,
            fontSize: 32,
            fontStyle: 'bold',
            fill: 'rgba(255, 255, 255, 0.8)',
            align: 'center'
        }));
    });

    StudioState.stage.add(gridLayer);
    gridLayer.moveToBottom();

    // 默认视图定位到中心
    const container = document.getElementById('konva-container');
    const viewWidth = container.offsetWidth;
    const viewHeight = container.offsetHeight;
    
    StudioState.stage.x((viewWidth - stageWidth) / 2);
    StudioState.stage.y((viewHeight - stageHeight) / 2);
}

// ==================== 绑定舞台事件 ====================
function bindStageEvents() {
    const stage = StudioState.stage;
    const container = document.getElementById('konva-container');

    // 滚轮缩放
    container.addEventListener('wheel', (e) => {
        e.preventDefault();
        
        const oldScale = stage.scaleX();
        const pointer = stage.getPointerPosition();
        
        const mousePointTo = {
            x: (pointer.x - stage.x()) / oldScale,
            y: (pointer.y - stage.y()) / oldScale
        };

        const zoomDirection = e.deltaY > 0 ? -1 : 1;
        const newScale = Math.max(0.1, Math.min(3, oldScale + zoomDirection * 0.1));

        stage.scale({ x: newScale, y: newScale });
        
        const newPos = {
            x: pointer.x - mousePointTo.x * newScale,
            y: pointer.y - mousePointTo.y * newScale
        };
        
        stage.position(newPos);
        StudioState.scale = newScale;
        updateZoomDisplay();
        
        stage.batchDraw();
    });

    // 鼠标按下
    stage.on('mousedown touchstart', (e) => {
        if (StudioState.currentTool === 'hand' || e.evt.button === 1) {
            // 抓手工具或中键 - 平移画布
            StudioState.isPanning = true;
            StudioState.lastPos = { x: e.evt.clientX, y: e.evt.clientY };
            container.classList.add('panning');
            return;
        }

        // 点击空白处取消选择
        if (e.target === stage) {
            StudioState.transformer.nodes([]);
            StudioState.selectedNode = null;
            updatePropertiesPanel();
        }
    });

    // 鼠标移动
    stage.on('mousemove touchmove', (e) => {
        if (StudioState.isPanning) {
            const dx = e.evt.clientX - StudioState.lastPos.x;
            const dy = e.evt.clientY - StudioState.lastPos.y;
            
            stage.x(stage.x() + dx);
            stage.y(stage.y() + dy);
            
            StudioState.lastPos = { x: e.evt.clientX, y: e.evt.clientY };
            stage.batchDraw();
        }
    });

    // 鼠标释放
    stage.on('mouseup touchend', () => {
        StudioState.isPanning = false;
        container.classList.remove('panning');
    });

    // 点击选中
    stage.on('click tap', (e) => {
        if (StudioState.isPanning) return;
        
        if (e.target.hasName('canvas-image')) {
            selectNode(e.target);
        } else if (e.target === stage) {
            // 点击空白处
            StudioState.transformer.nodes([]);
            StudioState.selectedNode = null;
            updatePropertiesPanel();
        }
    });
}

// ==================== 选中节点 ====================
function selectNode(node) {
    StudioState.selectedNode = node;
    StudioState.transformer.nodes([node]);
    updatePropertiesPanel();
}

// ==================== 添加图片到画布 ====================
function addImageToCanvas(imageSrc, x, y, type = 'character') {
    const imageObj = new Image();
    imageObj.onload = () => {
        // 计算缩放后尺寸，保持比例，最大宽度 300px
        const maxWidth = 300;
        const scale = Math.min(1, maxWidth / imageObj.width);
        const width = imageObj.width * scale;
        const height = imageObj.height * scale;

        const konvaImage = new Konva.Image({
            x: x,
            y: y,
            image: imageObj,
            width: width,
            height: height,
            draggable: true,
            name: 'canvas-image',
            type: type
        });

        // 添加阴影效果
        konvaImage.shadowColor('rgba(0, 0, 0, 0.3)');
        konvaImage.shadowBlur(10);
        konvaImage.shadowOffset({ x: 0, y: 4 });

        // 存储元数据
        konvaImage.setAttr('meta', {
            id: Date.now(),
            type: type,
            src: imageSrc,
            createdAt: new Date().toISOString()
        });

        // 拖拽事件
        konvaImage.on('dragstart', () => {
            konvaImage.shadowBlur(20);
        });

        konvaImage.on('dragend', () => {
            konvaImage.shadowBlur(10);
            updatePropertiesPanel();
        });

        konvaImage.on('transformend', () => {
            updatePropertiesPanel();
        });

        // 右键菜单
        konvaImage.on('contextmenu', (e) => {
            e.evt.preventDefault();
            showContextMenu(e.evt, konvaImage);
        });

        StudioState.layer.add(konvaImage);
        
        // 移到 transformer 之上
        konvaImage.moveToTop();
        StudioState.transformer.moveToTop();
        
        StudioState.layer.batchDraw();
        
        // 自动选中
        selectNode(konvaImage);

        // 添加到状态
        StudioState.canvasItems.push(konvaImage);
    };
    imageObj.src = imageSrc;
}

// ==================== 右键菜单 ====================
function showContextMenu(evt, node) {
    // 移除旧菜单
    const oldMenu = document.querySelector('.context-menu');
    if (oldMenu) oldMenu.remove();

    const menu = document.createElement('div');
    menu.className = 'context-menu';
    menu.style.cssText = `
        position: fixed;
        background: rgba(15, 23, 42, 0.98);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 4px;
        z-index: 1000;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    `;
    menu.innerHTML = `
        <div class="menu-item" data-action="front" style="padding: 8px 16px; cursor: pointer; border-radius: 4px; font-size: 13px; color: #e2e8f0;">
            ⬆️ 置于顶层
        </div>
        <div class="menu-item" data-action="back" style="padding: 8px 16px; cursor: pointer; border-radius: 4px; font-size: 13px; color: #e2e8f0;">
            ⬇️ 置于底层
        </div>
        <div class="menu-divider" style="height: 1px; background: rgba(255,255,255,0.1); margin: 4px 0;"></div>
        <div class="menu-item" data-action="delete" style="padding: 8px 16px; cursor: pointer; border-radius: 4px; font-size: 13px; color: #ef4444;">
            🗑️ 删除
        </div>
    `;

    menu.style.left = evt.clientX + 'px';
    menu.style.top = evt.clientY + 'px';

    menu.addEventListener('click', (e) => {
        const action = e.target.closest('.menu-item')?.dataset.action;
        if (action === 'front') {
            node.moveToTop();
            StudioState.transformer.moveToTop();
        } else if (action === 'back') {
            node.moveToBottom();
            // 保持在网格层之上
            const gridLayer = StudioState.stage.findOne('Layer');
            if (gridLayer) node.moveAbove(gridLayer);
        } else if (action === 'delete') {
            node.destroy();
            StudioState.transformer.nodes([]);
            StudioState.selectedNode = null;
            updatePropertiesPanel();
        }
        StudioState.layer.batchDraw();
        menu.remove();
    });

    document.body.appendChild(menu);

    // 点击其他地方关闭
    setTimeout(() => {
        document.addEventListener('click', function closeMenu() {
            menu.remove();
            document.removeEventListener('click', closeMenu);
        });
    }, 0);
}

// ==================== UI 初始化 ====================
function initUI() {
    // 分类切换
    document.querySelectorAll('.category-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.category-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            loadAssets(tab.dataset.category);
        });
    });

    // 工具栏
    document.getElementById('tool-select').addEventListener('click', () => setTool('select'));
    document.getElementById('tool-hand').addEventListener('click', () => setTool('hand'));
    document.getElementById('tool-fit').addEventListener('click', fitToCanvas);
    document.getElementById('tool-clear').addEventListener('click', clearCanvas);
    document.getElementById('tool-export').addEventListener('click', exportCanvas);

    // 缩放控制
    document.getElementById('zoomIn').addEventListener('click', () => zoomCanvas(0.2));
    document.getElementById('zoomOut').addEventListener('click', () => zoomCanvas(-0.2));

    // 生成按钮
    document.getElementById('generateAssetBtn').addEventListener('click', () => {
        document.getElementById('generateModal').classList.add('active');
    });

    document.getElementById('cancelGenerate').addEventListener('click', () => {
        document.getElementById('generateModal').classList.remove('active');
    });

    document.getElementById('confirmGenerate').addEventListener('click', generateImage);

    // 上传按钮
    document.getElementById('uploadAssetBtn').addEventListener('click', () => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'image/*';
        input.onchange = (e) => {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = (event) => {
                    const category = document.querySelector('.category-tab.active').dataset.category;
                    const region = getRegionCenter(category);
                    addImageToCanvas(event.target.result, region.x, region.y, category);
                };
                reader.readAsDataURL(file);
            }
        };
        input.click();
    });
}

// ==================== 获取区域中心 ====================
function getRegionCenter(type) {
    const centers = {
        character: { x: 800, y: 800 },
        scene: { x: 2500, y: 800 },
        prop: { x: 4200, y: 800 }
    };
    // 添加随机偏移，避免重叠
    const offset = () => (Math.random() - 0.5) * 200;
    const center = centers[type] || centers.character;
    return {
        x: center.x + offset(),
        y: center.y + offset()
    };
}

// ==================== 工具切换 ====================
function setTool(tool) {
    StudioState.currentTool = tool;
    document.querySelectorAll('.tool-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`tool-${tool}`).classList.add('active');
    
    if (tool === 'hand') {
        document.getElementById('konva-container').style.cursor = 'grab';
    } else {
        document.getElementById('konva-container').style.cursor = 'default';
    }
}

// ==================== 适应画布 ====================
function fitToCanvas() {
    const stage = StudioState.stage;
    const container = document.getElementById('konva-container');
    
    stage.scale({ x: 0.3, y: 0.3 });
    stage.position({
        x: (container.offsetWidth - 5000 * 0.3) / 2,
        y: (container.offsetHeight - 5000 * 0.3) / 2
    });
    
    StudioState.scale = 0.3;
    updateZoomDisplay();
    stage.batchDraw();
}

// ==================== 清空画布 ====================
function clearCanvas() {
    if (confirm('确定要清空画布吗？所有图片将被移除。')) {
        StudioState.layer.find('.canvas-image').forEach(node => node.destroy());
        StudioState.transformer.nodes([]);
        StudioState.selectedNode = null;
        StudioState.canvasItems = [];
        updatePropertiesPanel();
        StudioState.layer.batchDraw();
    }
}

// ==================== 导出画布 ====================
function exportCanvas() {
    // 临时隐藏 transformer
    StudioState.transformer.visible(false);
    StudioState.layer.batchDraw();
    
    const dataURL = StudioState.stage.toDataURL({
        pixelRatio: 2,
        x: 0,
        y: 0,
        width: 5000,
        height: 5000
    });
    
    // 恢复 transformer
    StudioState.transformer.visible(true);
    StudioState.layer.batchDraw();
    
    // 下载
    const link = document.createElement('a');
    link.download = `角色剧照画布_${new Date().toISOString().slice(0, 10)}.png`;
    link.href = dataURL;
    link.click();
}

// ==================== 缩放画布 ====================
function zoomCanvas(delta) {
    const stage = StudioState.stage;
    const oldScale = stage.scaleX();
    const newScale = Math.max(0.1, Math.min(3, oldScale + delta));
    
    const center = {
        x: stage.width() / 2,
        y: stage.height() / 2
    };
    
    const mousePointTo = {
        x: (center.x - stage.x()) / oldScale,
        y: (center.y - stage.y()) / oldScale
    };
    
    stage.scale({ x: newScale, y: newScale });
    stage.position({
        x: center.x - mousePointTo.x * newScale,
        y: center.y - mousePointTo.y * newScale
    });
    
    StudioState.scale = newScale;
    updateZoomDisplay();
    stage.batchDraw();
}

// ==================== 更新缩放显示 ====================
function updateZoomDisplay() {
    const percentage = Math.round(StudioState.scale * 100);
    document.getElementById('zoomValue').textContent = percentage + '%';
}

// ==================== 加载素材 ====================
function loadAssets(category = 'character') {
    const grid = document.getElementById('assetsGrid');
    grid.innerHTML = '';
    
    // 模拟数据 - 实际应从后端加载
    const mockAssets = {
        character: [
            { id: 1, name: '韩立', url: 'https://picsum.photos/200/280?random=1' },
            { id: 2, name: '南宫婉', url: 'https://picsum.photos/200/280?random=2' },
            { id: 3, name: '墨大夫', url: 'https://picsum.photos/200/280?random=3' },
            { id: 4, name: '陈师姐', url: 'https://picsum.photos/200/280?random=4' }
        ],
        scene: [
            { id: 5, name: '黄枫谷', url: 'https://picsum.photos/300/200?random=5' },
            { id: 6, name: '血色禁地', url: 'https://picsum.photos/300/200?random=6' },
            { id: 7, name: '灵石矿洞', url: 'https://picsum.photos/300/200?random=7' }
        ],
        prop: [
            { id: 8, name: '青竹蜂云剑', url: 'https://picsum.photos/150/150?random=8' },
            { id: 9, name: '储物袋', url: 'https://picsum.photos/150/150?random=9' },
            { id: 10, name: '筑基丹', url: 'https://picsum.photos/150/150?random=10' }
        ]
    };
    
    const assets = mockAssets[category] || [];
    
    assets.forEach(asset => {
        const item = document.createElement('div');
        item.className = 'asset-item';
        item.draggable = true;
        item.dataset.src = asset.url;
        item.dataset.type = category;
        item.innerHTML = `
            <img src="${asset.url}" alt="${asset.name}">
            <div class="asset-label">${asset.name}</div>
        `;
        
        // 点击添加到画布
        item.addEventListener('click', () => {
            const region = getRegionCenter(category);
            addImageToCanvas(asset.url, region.x, region.y, category);
        });
        
        // 拖拽开始
        item.addEventListener('dragstart', (e) => {
            e.dataTransfer.setData('src', asset.url);
            e.dataTransfer.setData('type', category);
            item.classList.add('dragging');
        });
        
        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
        });
        
        grid.appendChild(item);
    });
}

// ==================== 拖拽导入画布 ====================
function initDragDrop() {
    const container = document.getElementById('konva-container');
    
    container.addEventListener('dragover', (e) => {
        e.preventDefault();
        container.style.borderColor = '#6366f1';
    });
    
    container.addEventListener('dragleave', () => {
        container.style.borderColor = '';
    });
    
    container.addEventListener('drop', (e) => {
        e.preventDefault();
        container.style.borderColor = '';
        
        const src = e.dataTransfer.getData('src');
        const type = e.dataTransfer.getData('type');
        
        if (src) {
            // 转换为画布坐标
            const rect = container.getBoundingClientRect();
            const x = (e.clientX - rect.left - StudioState.stage.x()) / StudioState.scale;
            const y = (e.clientY - rect.top - StudioState.stage.y()) / StudioState.scale;
            
            addImageToCanvas(src, x, y, type);
        }
    });
}

// ==================== 更新属性面板 ====================
function updatePropertiesPanel() {
    const panel = document.getElementById('propertiesContent');
    const node = StudioState.selectedNode;
    
    if (!node) {
        panel.innerHTML = `
            <div class="empty-state" style="text-align: center; padding: 40px 20px; color: #64748b;">
                <div style="font-size: 48px; margin-bottom: 16px;">🖱️</div>
                <p>点击画布上的图片<br>查看和编辑属性</p>
            </div>
        `;
        return;
    }
    
    const meta = node.getAttr('meta') || {};
    const typeMap = { character: '🎭 角色', scene: '🏞️ 场景', prop: '🎒 道具' };
    
    panel.innerHTML = `
        <div class="property-group">
            <h4>📋 基本信息</h4>
            <div class="property-row">
                <span class="property-label">类型</span>
                <span class="property-value">${typeMap[meta.type] || '未知'}</span>
            </div>
            <div class="property-row">
                <span class="property-label">ID</span>
                <span class="property-value">#${meta.id || '-'}</span>
            </div>
        </div>
        
        <div class="property-group">
            <h4>📐 位置尺寸</h4>
            <div class="property-row">
                <span class="property-label">X 坐标</span>
                <span class="property-value">${Math.round(node.x())}px</span>
            </div>
            <div class="property-row">
                <span class="property-label">Y 坐标</span>
                <span class="property-value">${Math.round(node.y())}px</span>
            </div>
            <div class="property-row">
                <span class="property-label">宽度</span>
                <span class="property-value">${Math.round(node.width() * node.scaleX())}px</span>
            </div>
            <div class="property-row">
                <span class="property-label">高度</span>
                <span class="property-value">${Math.round(node.height() * node.scaleY())}px</span>
            </div>
            <div class="property-row">
                <span class="property-label">旋转</span>
                <span class="property-value">${Math.round(node.rotation())}°</span>
            </div>
        </div>
        
        <div class="property-group">
            <h4>🎨 外观</h4>
            <div class="property-row">
                <span class="property-label">不透明度</span>
                <span class="property-value">${Math.round(node.opacity() * 100)}%</span>
            </div>
        </div>
        
        <div class="property-group">
            <button class="btn btn-primary" style="width: 100%;" onclick="centerOnSelected()">📍 定位到该图片</button>
        </div>
    `;
}

// ==================== 定位到选中图片 ====================
function centerOnSelected() {
    if (!StudioState.selectedNode) return;
    
    const node = StudioState.selectedNode;
    const stage = StudioState.stage;
    const container = document.getElementById('konva-container');
    
    const scale = 0.8;
    const x = container.offsetWidth / 2 - node.x() * scale;
    const y = container.offsetHeight / 2 - node.y() * scale;
    
    stage.scale({ x: scale, y: scale });
    stage.position({ x, y });
    StudioState.scale = scale;
    updateZoomDisplay();
    stage.batchDraw();
}

// ==================== AI 生成图片 ====================
function generateImage() {
    const type = document.getElementById('generateType').value;
    const prompt = document.getElementById('generatePrompt').value;
    
    if (!prompt.trim()) {
        alert('请输入提示词');
        return;
    }
    
    document.getElementById('generateModal').classList.remove('active');
    document.getElementById('loadingOverlay').classList.add('active');
    
    // 模拟生成
    setTimeout(() => {
        document.getElementById('loadingOverlay').classList.remove('active');
        
        // 使用随机图片作为演示
        const randomId = Date.now();
        const url = `https://picsum.photos/400/560?random=${randomId}`;
        const region = getRegionCenter(type);
        
        addImageToCanvas(url, region.x, region.y, type);
        
        // 添加到素材库
        const grid = document.getElementById('assetsGrid');
        const item = document.createElement('div');
        item.className = 'asset-item';
        item.innerHTML = `
            <img src="${url}" alt="AI生成">
            <div class="asset-label">AI生成</div>
        `;
        item.addEventListener('click', () => {
            addImageToCanvas(url, region.x, region.y, type);
        });
        grid.insertBefore(item, grid.firstChild);
        
    }, 2000);
}

// ==================== 键盘事件 ====================
function bindKeyboardEvents() {
    document.addEventListener('keydown', (e) => {
        // Delete 删除选中
        if (e.key === 'Delete' || e.key === 'Backspace') {
            if (StudioState.selectedNode) {
                StudioState.selectedNode.destroy();
                StudioState.transformer.nodes([]);
                StudioState.selectedNode = null;
                updatePropertiesPanel();
                StudioState.layer.batchDraw();
            }
        }
        
        // V - 选择工具
        if (e.key === 'v' || e.key === 'V') {
            setTool('select');
        }
        
        // H - 抓手工具
        if (e.key === 'h' || e.key === 'H') {
            setTool('hand');
        }
        
        // 空格 - 临时抓手
        if (e.key === ' ') {
            e.preventDefault();
            setTool('hand');
        }
    });
    
    document.addEventListener('keyup', (e) => {
        if (e.key === ' ') {
            setTool('select');
        }
    });
}

// ==================== 退出登录 ====================
function logout() {
    if (confirm('确定要退出登录吗？')) {
        window.location.href = '/logout';
    }
}

// ==================== 返回按钮 ====================
document.getElementById('btnBack')?.addEventListener('click', () => {
    const returnUrl = localStorage.getItem('portraitStudio_returnUrl') || '/landing';
    window.location.href = returnUrl;
});

// 用户菜单切换
function toggleUserMenu(event) {
    event.stopPropagation();
    document.getElementById('userDropdown').classList.toggle('active');
}

// 点击外部关闭菜单
document.addEventListener('click', () => {
    document.getElementById('userDropdown')?.classList.remove('active');
});
