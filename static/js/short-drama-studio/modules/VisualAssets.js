/**
 * 视觉资产库模块
 * Visual Assets Module
 */

(function(root, factory) {
    if (typeof define === 'function' && define.amd) {
        define([], factory);
    } else if (typeof module === 'object' && module.exports) {
        module.exports = factory();
    } else {
        root.VisualAssetsMixin = factory();
    }
}(typeof self !== 'undefined' ? self : this, function() {
    'use strict';

    return {
        async loadVisualAssetsStep() {
            try {
                console.log('🎨 [视觉资产库] 开始初始化');

                // 如果角色还没加载，先加载角色数据
                if (!this.characters || this.characters.length === 0) {
                    console.log('🎭 [视觉资产库] 角色数据为空，正在加载...');
                    await this.loadEventsAndCharacters();
                }

                // 加载剧照信息
                await this.loadPortraits();

                // 从后端加载视觉资产
                await this.loadVisualAssetsFromAPI();

                // 初始化并渲染视觉资产库
                setTimeout(() => {
                    this.initVisualAssetsPanel();
                    this.initPortraitCanvas(this.characters);
                }, 100);

                // 更新项目状态
                this.updateProjectStatus();

                console.log('✅ [视觉资产库] 初始化完成');
            } catch (error) {
                console.error('❌ [视觉资产库] 加载失败:', error);
            }
        }

        initVisualAssetsPanel() {
            // 🔥 初始化图片生成任务管理器
            this.initImageTaskManager();
            
            // 绑定分类切换
            document.querySelectorAll('.va-category-tab').forEach(tab => {
                tab.addEventListener('click', () => {
                    document.querySelectorAll('.va-category-tab').forEach(t => {
                        t.classList.remove('active');
                        t.style.color = '#64748b';
                    });
                    tab.classList.add('active');
                    tab.style.color = '#6366f1';
                    
                    const category = tab.dataset.category;
                    this.loadVisualAssetsGrid(category);
                });
            });

            // 初始化加载角色类别
            this.loadVisualAssetsGrid('characters');

            // 绑定上传/生成按钮
            document.getElementById('vaUploadBtn')?.addEventListener('click', () => {
                this.uploadVisualAsset();
            });

            document.getElementById('vaGenerateBtn')?.addEventListener('click', () => {
                this.generateVisualAsset();
            });
        }

        loadVisualAssetsGrid(category) {
            const grid = document.getElementById('visualAssetsGrid');
            if (!grid) return;

            grid.innerHTML = '';

            if (category === 'characters') {
                // 加载角色 - 从 visualAssets 加载
                const characters = this.currentProject?.visualAssets?.characters || {};
                const charNames = Object.keys(characters);
                
                if (charNames.length === 0) {
                    grid.innerHTML = `
                        <div style="grid-column: span 2; text-align: center; padding: 40px 20px; color: #64748b;">
                            <p style="font-size: 32px; margin-bottom: 12px;">🎭</p>
                            <p style="font-size: 13px;">暂无角色</p>
                            <p style="font-size: 11px; margin-top: 8px; color: #475569;">点击下方"生成"创建</p>
                        </div>
                    `;
                } else {
                    charNames.forEach(charName => {
                        const char = characters[charName];
                        // 🔥 优先使用 visualAssets 中的新生成图片
                        const imageUrl = char.referenceUrl || this.characterPortraits.get(charName)?.mainPortrait?.url;

                        const card = document.createElement('div');
                        card.className = 'va-asset-card';
                        card.innerHTML = `
                            ${imageUrl 
                                ? `<img src="${imageUrl}" alt="${charName}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">`
                                : ''}
                            <div style="display: ${imageUrl ? 'none' : 'flex'}; align-items: center; justify-content: center; height: 100%; font-size: 24px;">🎭</div>
                            <div class="asset-label">${charName}</div>
                        `;
                        card.addEventListener('click', () => {
                            this.selectVisualAsset('character', char, imageUrl);
                        });
                        grid.appendChild(card);
                    });
                }
            } else if (category === 'scenes') {
                // 场景 - 从 visualAssets 加载
                const scenes = this.currentProject?.visualAssets?.scenes || {};
                const sceneNames = Object.keys(scenes);
                
                if (sceneNames.length === 0) {
                    grid.innerHTML = `
                        <div style="grid-column: span 2; text-align: center; padding: 40px 20px; color: #64748b;">
                            <p style="font-size: 32px; margin-bottom: 12px;">🏞️</p>
                            <p style="font-size: 13px;">暂无场景</p>
                            <p style="font-size: 11px; margin-top: 8px; color: #475569;">点击下方"生成"创建</p>
                        </div>
                    `;
                } else {
                    sceneNames.forEach(sceneName => {
                        const scene = scenes[sceneName];
                        const imageUrl = scene.referenceUrl;
                        
                        const card = document.createElement('div');
                        card.className = 'va-asset-card';
                        card.innerHTML = `
                            ${imageUrl 
                                ? `<img src="${imageUrl}" alt="${sceneName}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">`
                                : ''}
                            <div style="display: ${imageUrl ? 'none' : 'flex'}; align-items: center; justify-content: center; height: 100%; font-size: 24px;">🏞️</div>
                            <div class="asset-label">${sceneName}</div>
                        `;
                        card.addEventListener('click', () => {
                            this.selectVisualAsset('scene', scene, imageUrl);
                        });
                        grid.appendChild(card);
                    });
                }
            } else if (category === 'props') {
                // 道具 - 从 visualAssets 加载
                const props = this.currentProject?.visualAssets?.props || {};
                const propNames = Object.keys(props);
                
                if (propNames.length === 0) {
                    grid.innerHTML = `
                        <div style="grid-column: span 2; text-align: center; padding: 40px 20px; color: #64748b;">
                            <p style="font-size: 32px; margin-bottom: 12px;">🎒</p>
                            <p style="font-size: 13px;">暂无道具</p>
                            <p style="font-size: 11px; margin-top: 8px; color: #475569;">点击下方"生成"创建</p>
                        </div>
                    `;
                } else {
                    propNames.forEach(propName => {
                        const prop = props[propName];
                        const imageUrl = prop.referenceUrl;
                        
                        const card = document.createElement('div');
                        card.className = 'va-asset-card';
                        card.innerHTML = `
                            ${imageUrl 
                                ? `<img src="${imageUrl}" alt="${propName}" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';">`
                                : ''}
                            <div style="display: ${imageUrl ? 'none' : 'flex'}; align-items: center; justify-content: center; height: 100%; font-size: 24px;">🎒</div>
                            <div class="asset-label">${propName}</div>
                        `;
                        card.addEventListener('click', () => {
                            this.selectVisualAsset('prop', prop, imageUrl);
                        });
                        grid.appendChild(card);
                    });
                }
            }
        }

        selectVisualAsset(type, data, imageUrl) {
            const panel = document.getElementById('vaPropertiesContent');
            if (!panel) return;

            const typeMap = {
                'character': { icon: '🎭', label: '角色', color: '#ec4899' },
                'scene': { icon: '🏞️', label: '场景', color: '#22c55e' },
                'prop': { icon: '🎒', label: '道具', color: '#f59e0b' }
            };
            const typeInfo = typeMap[type] || typeMap['character'];

            // 提取标准描述
            let description = '';
            let clothing = '';
            let expression = '';
            let lighting = '';
            let colorTone = '';
            let category = '';
            
            if (type === 'character') {
                description = data.living_characteristics?.physical_presence 
                    || data.initial_state?.description 
                    || data.appearance 
                    || data.description 
                    || '';
                clothing = data.clothing || '';
                expression = data.expression || '';
            } else if (type === 'scene') {
                description = data.description || '';
                lighting = data.lighting || '';
                colorTone = data.colorTone || '';
            } else if (type === 'prop') {
                description = data.description || '';
                category = data.category || '';
            }

            panel.innerHTML = `
                <div class="va-asset-preview">
                    ${imageUrl 
                        ? `<img src="${imageUrl}" alt="${data.name || data}">`
                        : `<div style="display: flex; align-items: center; justify-content: center; height: 100%; font-size: 48px;">${typeInfo.icon}</div>`}
                </div>

                <div class="va-property-group">
                    <h5>📋 基本信息</h5>
                    <div class="va-form-row">
                        <span class="va-asset-type-badge ${type}">${typeInfo.icon} ${typeInfo.label}</span>
                    </div>
                    <div class="va-form-row">
                        <label>名称</label>
                        <input type="text" value="${data.name || data}" readonly>
                    </div>
                    ${data.role ? `
                    <div class="va-form-row">
                        <label>角色</label>
                        <input type="text" value="${data.role}" readonly>
                    </div>
                    ` : ''}
                </div>

                <div class="va-property-group">
                    <h5>📝 标准描述</h5>
                    <p class="va-hint">用于分镜生成的标准化描述</p>
                    <div class="va-form-row">
                        <textarea id="vaAssetDescription" placeholder="详细描述外观特征、颜色、风格...">${description}</textarea>
                    </div>
                    <div style="display: flex; gap: 8px;">
                        <button class="btn btn-sm btn-primary" onclick="shortDramaStudio.saveAssetDescription('${data.name || data}', '${type}')" style="flex: 1;">
                            💾 保存
                        </button>
                        <button class="btn btn-sm" onclick="shortDramaStudio.generateAssetImage('${data.name || data}', '${type}')" style="flex: 1; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; border: none;">
                            🎨 生成图片
                        </button>
                    </div>
                </div>

                ${type === 'character' ? `
                <div class="va-property-group">
                    <h5>🎨 角色特征</h5>
                    <div class="va-form-row">
                        <label>服装</label>
                        <input type="text" id="vaCharClothing" value="${clothing}" placeholder="例如：青色长袍、白色内衫">
                    </div>
                    <div class="va-form-row">
                        <label>标志性表情</label>
                        <input type="text" id="vaCharExpression" value="${expression}" placeholder="例如：沉稳、坚毅">
                    </div>
                </div>
                ` : ''}

                ${type === 'scene' ? `
                <div class="va-property-group">
                    <h5>🌟 场景特征</h5>
                    <div class="va-form-row">
                        <label>光线</label>
                        <input type="text" id="vaSceneLighting" value="${lighting}" placeholder="例如：晨光、柔和">
                    </div>
                    <div class="va-form-row">
                        <label>色调</label>
                        <input type="text" id="vaSceneColorTone" value="${colorTone}" placeholder="例如：青绿色调">
                    </div>
                </div>
                ` : ''}

                ${type === 'prop' ? `
                <div class="va-property-group">
                    <h5>🎒 道具特征</h5>
                    <div class="va-form-row">
                        <label>分类</label>
                        <input type="text" id="vaPropCategory" value="${category}" placeholder="例如：武器、饰品、工具">
                    </div>
                </div>
                ` : ''}
            `;
        }

        async saveVisualAssetsToProject() {
            if (!this.currentProject?.id || !this.currentProject?.visualAssets) {
                return;
            }
            
            try {
                // 同步字段名称兼容
                const projectData = {
                    visualAssets: this.currentProject.visualAssets
                };
                
                const response = await fetch(`/api/projects/${this.currentProject.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(projectData)
                });
                
                const data = await response.json();
                if (data.success) {
                    console.log('✅ [视觉资产] 已同步到项目，用于分镜生成');
                }
            } catch (error) {
                console.error('保存视觉资产失败:', error);
            }
        }

        uploadVisualAsset() {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = 'image/*';
            input.onchange = (e) => {
                const file = e.target.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        // TODO: 上传到服务器
                        this.showToast('图片已选择，正在上传...', 'info');
                    };
                    reader.readAsDataURL(file);
                }
            };
            input.click();
        }

        extractCharactersFromEpisodes() {
            const characters = [];
            const seen = new Set();

            for (const eventId of this.selectedEpisodes) {
                // 在重大事件的子事件中查找
                for (const majorEvent of this.events) {
                    const episode = majorEvent.children?.find(e =>
                        e.id === eventId || e.name === eventId
                    );
                    if (episode && episode.characters) {
                        episode.characters.forEach(char => {
                            if (!seen.has(char.name)) {
                                seen.add(char.name);
                                characters.push(char);
                            }
                        });
                    }
                }
            }

            return characters;
        }

        async generatePortrait(characterName) {
            const character = this.characters.find(c => c.name === characterName);
            if (!character) {
                this.showToast('找不到角色信息', 'error');
                return;
            }

            // 构建剧集目录名称
            const episodeDirectoryName = this.getEpisodeDirectoryName();

            // 生成角色剧照提示词（参考旧代码逻辑）
            const prompt = this.generateCharacterPortraitPrompt(character);

            // 保存数据到localStorage供剧照工作台使用
            const dataToSave = {
                id: character.id,
                name: character.name,
                role: character.role || '',
                description: character.description || '',
                appearance: character.appearance || '',
                generatedPrompt: prompt,
                episode_info: episodeDirectoryName,
                novel_title: this.selectedNovel,
                return_url: `/short-drama-studio`, // 保存返回地址
                return_step: 'check-portraits', // 保存返回步骤
                timestamp: Date.now() // 🔥 添加时间戳，用于过期检查
            };

            console.log('📸 保存角色数据到localStorage:', dataToSave);
            localStorage.setItem('portraitStudio_character', JSON.stringify(dataToSave));

            // 打开剧照工作台（新窗口）
            window.open('/portrait-studio?mode=episode', '_blank');
        }

        generateCharacterPortraitPrompt(character) {
            const name = character.name || '';
            const role = character.role || '';

            // 从角色设计文件结构中提取详细外观信息
            let physicalDescription = '';
            let personality = '';
            let age = '';
            let clothing = '';

            // 尝试从不同字段中提取信息
            if (character.living_characteristics) {
                physicalDescription = character.living_characteristics.physical_presence || '';
                personality = character.living_characteristics.distinctive_traits || character.living_characteristics.communication_style || '';
            }

            // 从initial_state中提取
            if (character.initial_state) {
                if (!physicalDescription) {
                    physicalDescription = character.initial_state.description || '';
                }
            }

            // 从top-level字段提取（兼容旧格式）
            if (!physicalDescription) {
                physicalDescription = character.appearance || character.description || '';
            }

            // 从soul_matrix中提取核心特质
            if (character.soul_matrix && character.soul_matrix.length > 0) {
                const firstTrait = character.soul_matrix[0];
                if (typeof firstTrait === 'object') {
                    personality = firstTrait.core_trait || personality;
                } else if (typeof firstTrait === 'string') {
                    personality = firstTrait;
                }
            }

            // 提取年龄
            age = character.age || character.initial_state?.age || '';

            // 构建详细的角色特征描述
            let characterFeatures = [];

            // 添加身体特征（最重要）
            if (physicalDescription) {
                characterFeatures.push(`外形：${physicalDescription}`);
            }

            // 添加性格特质
            if (personality) {
                characterFeatures.push(`性格：${personality}`);
            }

            // 添加年龄
            if (age) {
                characterFeatures.push(`年龄：${age}`);
            }

            // 添加服装/装备信息（从physical_description中提取关键词）
            const clothingKeywords = ['身穿', '身披', '着', '战甲', '锦袍', '长袍', '铠甲', '盔甲', '衣服', '套装'];
            for (const keyword of clothingKeywords) {
                if (physicalDescription.includes(keyword)) {
                    // 找到包含服装关键词的句子
                    const sentences = physicalDescription.split(/[，。；！]/);
                    for (const sentence of sentences) {
                        if (sentence.includes(keyword)) {
                            clothing = sentence.trim();
                            break;
                        }
                    }
                    if (clothing) break;
                }
            }
            if (clothing) {
                characterFeatures.push(`服装：${clothing}`);
            }

            // 根据角色的actual特征构建提示词，而不是用通用模板
            let prompt = `角色名称：${name}\n`;
            prompt += `角色定位：${role}\n`;
            prompt += `\n`;

            // 如果有详细的特征描述，优先使用
            if (characterFeatures.length > 0) {
                prompt += `【角色特征】\n`;
                prompt += characterFeatures.join('\n');
                prompt += `\n\n`;
            }

            // 根据角色定位添加画面要求（使用更精确的风格）
            prompt += `【画面要求】\n`;

            // 根据实际角色特征确定风格，而不是通用模板
            let style = '高质量人物立绘，细节丰富';
            let composition = '半身正面像，突出面部特征和表情';
            let expression = '自然生动';
            let background = '东方玄幻修仙世界风格背景';

            // 根据physical_description中的关键词调整风格
            if (physicalDescription) {
                if (physicalDescription.includes('横肉') || physicalDescription.includes('魁梧') || physicalDescription.includes('壮汉')) {
                    // 粗犷威猛型角色
                    style = '东方玄幻风格，粗犷威猛，力量感十足';
                    expression = '威严霸气，眼神锐利，气势逼人';
                    background = '压抑的氛围，强者威压的视觉效果';
                } else if (physicalDescription.includes('仙风') || physicalDescription.includes('鹤发') || physicalDescription.includes('童颜')) {
                    // 仙风道骨型角色
                    style = '东方玄幻风格，仙风道骨，高人风范';
                    expression = '慈祥深邃，眼神空灵，道法自然';
                    background = '仙气缭绕，云雾飘渺，道韵天成';
                } else if (physicalDescription.includes('绝美') || physicalDescription.includes('容') || physicalDescription.includes('少女') || physicalDescription.includes('美女')) {
                    // 美女型角色
                    style = '东方玄幻风格，精致唯美，仙气飘飘';
                    expression = '温柔恬静或清冷孤傲，眼神灵动';
                    background = '花海仙宫，梦幻氛围';
                } else if (physicalDescription.includes('阴鸷') || physicalDescription.includes('阴') || physicalDescription.includes('煞')) {
                    // 阴狠型角色
                    style = '东方玄幻风格，阴狠霸气，魔道气息';
                    expression = '阴鸷狠戾，眼神如蛇，压迫感强';
                    background = '黑暗气息，血煞之气，魔道氛围';
                } else {
                    // 默认风格
                    style = '东方玄幻修真风格，高质量人物立绘';
                    expression = '生动自然，眼神有神';
                    background = '东方玄幻修仙世界风格，灵气氤氲';
                }
            }

            prompt += `风格：${style}\n`;
            prompt += `构图：${composition}\n`;
            prompt += `表情：${expression}\n`;
            prompt += `背景：${background}\n`;

            // 添加技术要求
            prompt += `\n【技术要求】\n`;
            prompt += `- 高清画质，细节精致\n`;
            prompt += `- 专业插画质量\n`;
            prompt += `- 光影效果出色，立体感强\n`;
            prompt += `- 色彩和谐，符合东方玄幻美学\n`;
            prompt += `- 人物比例协调，五官端正\n`;
            prompt += `- 空气中弥漫灵气粒子效果\n`;

            return prompt;
        }

        viewPortrait(characterName) {
            // 🔥 宽松匹配：查找包含角色名的剧照
            let portrait = this.characterPortraits.get(characterName);
            if (!portrait) {
                // 精确匹配失败，尝试模糊匹配
                for (const [key, value] of this.characterPortraits.entries()) {
                    if (key.includes(characterName) || characterName.includes(key)) {
                        portrait = value;
                        console.log(`🎭 [剧照查看] 模糊匹配: "${characterName}" <- "${key}"`);
                        break;
                    }
                }
            }
            if (portrait) {
                // 打开模态框显示剧照
                this.showPortraitModal(characterName, portrait);
            }
        }

    };
}));
