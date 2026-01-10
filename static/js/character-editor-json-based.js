// ==================== 基于JSON结构的角色编辑器 ====================

/**
 * 字段配置定义
 * 定义每个字段的显示名称、UI组件类型、验证规则等
 */
const FIELD_DEFINITIONS = {
    // 基本信息
    name: {
        label: '角色名称',
        type: 'text',
        required: true,
        category: 'basic',
        priority: 1
    },
    role: {
        label: '角色类型',
        type: 'select',
        options: ['主角', '核心配角', '配角', '反派', '路人'],
        required: true,
        category: 'basic',
        priority: 2
    },
    icon: {
        label: '角色图标',
        type: 'icon-selector',
        category: 'basic',
        priority: 3
    },
    color: {
        label: '代表颜色',
        type: 'color-selector',
        category: 'basic',
        priority: 4
    },
    
    // 核心特征
    core_personality: {
        label: '核心性格',
        type: 'textarea',
        placeholder: '用2-3个核心标签概括性格特质 (例如：谨慎、腹黑、重情义)',
        category: 'personality',
        priority: 1
    },
    dialogue_style_example: {
        label: '对话风格示例',
        type: 'textarea',
        placeholder: '写一句最能代表他说话风格和性格的标志性台词',
        category: 'personality',
        priority: 2
    },
    character_tag_for_reader: {
        label: '角色标签',
        type: 'text',
        placeholder: '一句话概括角色给读者的印象 (例如：扮猪吃虎的病秧子神医)',
        category: 'personality',
        priority: 3
    },
    
    // 生活特征（嵌套对象）
    'living_characteristics.physical_presence': {
        label: '外貌特征',
        type: 'textarea',
        placeholder: '角色的外貌、体态、穿着风格，以及他/她给人的【第一眼】的整体感觉或气场',
        category: 'appearance',
        priority: 1
    },
    'living_characteristics.daily_habits': {
        label: '日常习惯',
        type: 'textarea',
        placeholder: '角色的日常习惯 (数组)',
        category: 'appearance',
        priority: 2
    },
    'living_characteristics.speech_patterns': {
        label: '言语模式',
        type: 'textarea',
        placeholder: '说话风格和口头禅',
        category: 'appearance',
        priority: 3
    },
    'living_characteristics.personal_quirks': {
        label: '个人怪癖',
        type: 'textarea',
        placeholder: '独特的小动作或癖好',
        category: 'appearance',
        priority: 4
    },
    'living_characteristics.emotional_triggers': {
        label: '情感触发点',
        type: 'textarea',
        placeholder: '容易引发其强烈情绪波动的事物',
        category: 'appearance',
        priority: 5
    },
    'living_characteristics.distinctive_traits': {
        label: '鲜明特点',
        type: 'textarea',
        placeholder: '最鲜明的性格特点',
        category: 'appearance',
        priority: 6
    },
    'living_characteristics.communication_style': {
        label: '交流方式',
        type: 'textarea',
        placeholder: '与他人交流的方式 (例如：毒舌、沉默寡言)',
        category: 'appearance',
        priority: 7
    },
    
    // 内心世界
    'inner_world_and_flaws.inner_conflicts': {
        label: '内心矛盾',
        type: 'textarea',
        placeholder: '内心深处最主要的矛盾和挣扎',
        category: 'inner_world',
        priority: 1
    },
    'inner_world_and_flaws.contradictory_traits': {
        label: '矛盾特质',
        type: 'textarea',
        placeholder: '外在表现与内在真实的反差',
        category: 'inner_world',
        priority: 2
    },
    'inner_world_and_flaws.vulnerabilities': {
        label: '情感软肋',
        type: 'textarea',
        placeholder: '情感上的软肋和害怕失去的东西',
        category: 'inner_world',
        priority: 3
    },
    'inner_world_and_flaws.fatal_flaw': {
        label: '致命缺陷',
        type: 'textarea',
        placeholder: '导致其反复陷入困境的性格或认知缺陷',
        category: 'inner_world',
        priority: 4
    },
    
    // 背景和成长
    background: {
        label: '背景故事',
        type: 'textarea',
        placeholder: '只描述直接导致其当前动机和核心缺陷的关键背景事件',
        category: 'background',
        priority: 1
    },
    'motivation.inner_drive': {
        label: '内在驱动力',
        type: 'textarea',
        placeholder: '心理需求、价值观等内在驱动力',
        category: 'background',
        priority: 2
    },
    'motivation.external_goals': {
        label: '外在目标',
        type: 'textarea',
        placeholder: '具体行动、要达成的事件等外在目标',
        category: 'background',
        priority: 3
    },
    'motivation.secret_desires': {
        label: '秘密欲望',
        type: 'textarea',
        placeholder: '深藏心底、甚至自己都不愿承认的渴望',
        category: 'background',
        priority: 4
    },
    growth_arc: {
        label: '成长弧线',
        type: 'textarea',
        placeholder: '描述角色从故事起点到终点在认知、能力或性格上的核心转变路径',
        category: 'background',
        priority: 5
    },
    'cool_point_upgrade_path': {
        label: '爽点升级路线',
        type: 'textarea',
        placeholder: '爽点升级路线图 (例如：都市打脸 -> 武道界称雄 -> 揭秘身世)',
        category: 'background',
        priority: 6
    },
    
    // 势力关系（嵌套对象）
    'faction_affiliation.current_faction': {
        label: '当前势力',
        type: 'text',
        placeholder: '当前所属势力名称',
        category: 'faction',
        priority: 1
    },
    'faction_affiliation.position': {
        label: '势力地位',
        type: 'text',
        placeholder: '在势力中的地位/身份 (例如：外门弟子、内门弟子、长老)',
        category: 'faction',
        priority: 2
    },
    'faction_affiliation.loyalty_level': {
        label: '忠诚度',
        type: 'select',
        options: ['高', '中', '低', '绝对'],
        category: 'faction',
        priority: 3
    },
    'faction_affiliation.status_in_faction': {
        label: '势力声望',
        type: 'textarea',
        placeholder: '在势力中的声望和影响力描述',
        category: 'faction',
        priority: 4
    },
    'faction_affiliation.faction_benefits': {
        label: '势力资源',
        type: 'textarea',
        placeholder: '从势力获得的好处或资源',
        category: 'faction',
        priority: 5
    },
    'faction_affiliation.secret_factions': {
        label: '秘密势力',
        type: 'textarea',
        placeholder: '秘密归属的其他势力',
        category: 'faction',
        priority: 6
    },
    'faction_affiliation.faction_background': {
        label: '势力影响',
        type: 'textarea',
        placeholder: '势力背景和理念对角色的影响',
        category: 'faction',
        priority: 7
    },
    
    // 势力关系网络
    'faction_relationships.allies_in_faction': {
        label: '己方盟友',
        type: 'textarea',
        placeholder: '在己方势力中的盟友列表',
        category: 'faction_network',
        priority: 1
    },
    'faction_relationships.rivals_in_faction': {
        label: '己方竞争对手',
        type: 'textarea',
        placeholder: '在己方势力中的竞争对手列表',
        category: 'faction_network',
        priority: 2
    },
    'faction_relationships.external_allies': {
        label: '外部盟友',
        type: 'textarea',
        placeholder: '跨势力的盟友关系',
        category: 'faction_network',
        priority: 3
    },
    'faction_relationships.external_enemies': {
        label: '外部敌人',
        type: 'textarea',
        placeholder: '跨势力的敌对关系',
        category: 'faction_network',
        priority: 4
    },
    'faction_relationships.complex_ties': {
        label: '复杂关系',
        type: 'textarea',
        placeholder: '亦敌亦友、利用关系、潜在威胁等复杂关系',
        category: 'faction_network',
        priority: 5
    },
    
    // 能力和状态
    cultivation_level: {
        label: '修炼等级',
        type: 'text',
        category: 'abilities',
        priority: 1
    },
    abilities: {
        label: '特殊能力',
        type: 'textarea',
        category: 'abilities',
        priority: 2
    },
    skills: {
        label: '主要技能',
        type: 'textarea',
        category: 'abilities',
        priority: 3
    },
    
    // 初始状态
    'initial_state.description': {
        label: '初始状态描述',
        type: 'textarea',
        placeholder: '对该角色登场时状态的简要描述',
        category: 'initial_state',
        priority: 1
    },
    'initial_state.location': {
        label: '登场地点',
        type: 'text',
        placeholder: '登场时的地点',
        category: 'initial_state',
        priority: 2
    },
    'initial_state.identity': {
        label: '登场身份',
        type: 'text',
        placeholder: '登场时的主要身份或地位',
        category: 'initial_state',
        priority: 3
    },
    
    // 角色状态数组（简化显示）
    character_states: {
        label: '角色状态阶段',
        type: 'textarea',
        placeholder: '各个阶段的状态规划 (JSON数组)',
        category: 'state_progression',
        priority: 1
    },
    
    // 叙事相关
    'relationship_with_protagonist.initial_friction_or_hook': {
        label: '与主角的初始关系',
        type: 'textarea',
        placeholder: '两人初次相遇时的【冲突点】或【连接点】',
        category: 'narrative',
        priority: 1
    },
    'relationship_with_protagonist.development_dynamics': {
        label: '关系发展动态',
        type: 'textarea',
        placeholder: '这段关系将如何演变',
        category: 'narrative',
        priority: 2
    },
    'relationship_with_protagonist.memorable_interactions': {
        label: '标志性互动',
        type: 'textarea',
        placeholder: '能定义他们关系的标志性互动场景或事件',
        category: 'narrative',
        priority: 3
    },
    narrative_purpose: {
        label: '叙事作用',
        type: 'textarea',
        placeholder: '解释该角色在剧情中的【不可替代】的作用',
        category: 'narrative',
        priority: 4
    },
    'final_destiny_in_stage': {
        label: '阶段结局',
        type: 'textarea',
        placeholder: '这个角色在本阶段结束后的结局',
        category: 'narrative',
        priority: 5
    },
    reader_impression: {
        label: '读者印象',
        type: 'textarea',
        placeholder: '希望读者对这个角色的第一印象',
        category: 'narrative',
        priority: 6
    },
    
    // 兼容旧字段
    description: {
        label: '角色描述',
        type: 'textarea',
        category: 'other',
        priority: 1
    },
    personality: {
        label: '性格特点',
        type: 'textarea',
        category: 'other',
        priority: 2
    },
    appearance: {
        label: '外貌',
        type: 'textarea',
        category: 'other',
        priority: 3
    }
};

/**
 * 分类配置
 * 定义表单的分类和显示顺序
 */
const CATEGORY_CONFIG = {
    basic: {
        label: '基本信息',
        icon: '📋',
        layout: 'grid',
        priority: 1
    },
    personality: {
        label: '核心性格',
        icon: '🧠',
        layout: 'vertical',
        priority: 2
    },
    appearance: {
        label: '生活特征',
        icon: '✨',
        layout: 'vertical',
        priority: 3
    },
    inner_world: {
        label: '内心世界',
        icon: '💭',
        layout: 'vertical',
        priority: 4
    },
    background: {
        label: '背景成长',
        icon: '📖',
        layout: 'vertical',
        priority: 5
    },
    faction: {
        label: '势力归属',
        icon: '🏰',
        layout: 'vertical',
        priority: 6
    },
    faction_network: {
        label: '势力关系网络',
        icon: '🕸️',
        layout: 'vertical',
        priority: 7
    },
    abilities: {
        label: '能力状态',
        icon: '💪',
        layout: 'vertical',
        priority: 8
    },
    initial_state: {
        label: '初始状态',
        icon: '🎬',
        layout: 'grid',
        priority: 9
    },
    state_progression: {
        label: '状态规划',
        icon: '📈',
        layout: 'vertical',
        priority: 10
    },
    narrative: {
        label: '叙事作用',
        icon: '📝',
        layout: 'vertical',
        priority: 11
    },
    other: {
        label: '其他信息',
        icon: '📦',
        layout: 'vertical',
        priority: 12
    }
};

/**
 * 根据JSON数据动态生成表单
 * @param {Object} character - 角色数据对象
 * @returns {HTMLElement} - 生成的表单元素
 */
function generateFormFromJSON(character) {
    const container = document.createElement('div');
    container.className = 'dynamic-form-container';
    
    // 按分类组织字段
    const categorizedFields = categorizeFields(character);
    
    // 按优先级排序分类
    const sortedCategories = Object.values(categorizedFields)
        .sort((a, b) => a.priority - b.priority);
    
    // 为每个分类生成表单区块
    sortedCategories.forEach(category => {
        const section = createFormSection(category, character);
        container.appendChild(section);
    });
    
    return container;
}

/**
 * 将字段按分类组织
 * @param {Object} character - 角色数据
 * @returns {Object} - 分类后的字段
 */
function categorizeFields(character) {
    const categories = {};
    
    // 初始化分类
    Object.keys(CATEGORY_CONFIG).forEach(key => {
        categories[key] = {
            ...CATEGORY_CONFIG[key],
            fields: []
        };
    });
    
    // 遍历角色数据，为每个字段找到对应的分类
    Object.keys(character).forEach(key => {
        const value = character[key];
        
        // 跳过关系数组（单独处理）
        if (key === 'relationships') return;
        
        // 查找字段定义
        let fieldDef = FIELD_DEFINITIONS[key];
        
        // 如果没有直接定义，尝试处理嵌套对象
        if (!fieldDef && typeof value === 'object' && value !== null && !Array.isArray(value)) {
            // 处理嵌套对象的每个字段
            Object.keys(value).forEach(nestedKey => {
                const fullPath = `${key}.${nestedKey}`;
                const nestedDef = FIELD_DEFINITIONS[fullPath];
                if (nestedDef) {
                    const category = categories[nestedDef.category] || categories.other;
                    category.fields.push({
                        ...nestedDef,
                        fieldKey: fullPath,
                        value: value[nestedKey]
                    });
                }
            });
            return;
        }
        
        // 使用找到的定义或默认定义
        const def = fieldDef || {
            label: key,
            type: typeof value === 'string' && value.length > 50 ? 'textarea' : 'text',
            category: 'other',
            priority: 999
        };
        
        const category = categories[def.category] || categories.other;
        category.fields.push({
            ...def,
            fieldKey: key,
            value: value
        });
    });
    
    return categories;
}

/**
 * 创建表单区块
 * @param {Object} category - 分类对象
 * @param {Object} character - 角色数据
 * @returns {HTMLElement} - 表单区块元素
 */
function createFormSection(category, character) {
    const section = document.createElement('div');
    section.className = 'form-section';
    section.dataset.category = category.label;
    
    // 区块标题
    const header = document.createElement('div');
    header.className = 'section-header';
    header.innerHTML = `
        <h4>${category.icon} ${category.label}</h4>
        <button class="collapse-btn" onclick="toggleSection(this)">▼</button>
    `;
    section.appendChild(header);
    
    // 字段容器
    const fieldsContainer = document.createElement('div');
    fieldsContainer.className = category.layout === 'grid' ? 'form-grid' : 'form-vertical';
    
    // 按优先级排序字段
    const sortedFields = category.fields.sort((a, b) => a.priority - b.priority);
    
    // 为每个字段创建表单元素
    sortedFields.forEach(field => {
        const fieldElement = createFormFieldElement(field);
        fieldsContainer.appendChild(fieldElement);
    });
    
    section.appendChild(fieldsContainer);
    
    return section;
}

/**
 * 创建表单字段元素
 * @param {Object} field - 字段配置
 * @returns {HTMLElement} - 表单字段元素
 */
function createFormFieldElement(field) {
    const wrapper = document.createElement('div');
    wrapper.className = 'form-group';
    
    // 字段标签
    const label = document.createElement('label');
    label.textContent = field.label + (field.required ? ' *' : '');
    wrapper.appendChild(label);
    
    // 根据类型创建不同的输入组件
    let inputElement;
    
    switch (field.type) {
        case 'textarea':
            inputElement = document.createElement('textarea');
            inputElement.rows = 3;
            inputElement.value = field.value || '';
            break;
            
        case 'select':
            inputElement = document.createElement('select');
            (field.options || []).forEach(option => {
                const optElement = document.createElement('option');
                optElement.value = option;
                optElement.textContent = option;
                if (option === field.value) optElement.selected = true;
                inputElement.appendChild(optElement);
            });
            break;
            
        case 'icon-selector':
            inputElement = createIconSelector(field.value);
            break;
            
        case 'color-selector':
            inputElement = createColorSelector(field.value);
            break;
            
        default:
            inputElement = document.createElement('input');
            inputElement.type = 'text';
            inputElement.value = field.value || '';
    }
    
    // 设置通用属性
    inputElement.id = `field-${field.fieldKey.replace(/\./g, '-')}`;
    inputElement.dataset.fieldKey = field.fieldKey;
    inputElement.className = 'form-control';
    
    if (field.placeholder) {
        inputElement.placeholder = field.placeholder;
    }
    
    if (field.required) {
        inputElement.required = true;
    }
    
    wrapper.appendChild(inputElement);
    
    return wrapper;
}

/**
 * 创建图标选择器
 * @param {string} selectedIcon - 选中的图标
 * @returns {HTMLElement} - 图标选择器元素
 */
function createIconSelector(selectedIcon) {
    const container = document.createElement('div');
    container.className = 'icon-selector';
    
    const icons = ['👤', '🧑', '👨', '👩', '🧓', '👴', '👵', '🧙', '🧝', '🦸', '🦹', '👼'];
    
    icons.forEach(icon => {
        const iconOption = document.createElement('span');
        iconOption.className = 'icon-option';
        if (icon === selectedIcon) iconOption.classList.add('selected');
        iconOption.textContent = icon;
        iconOption.onclick = () => {
            container.querySelectorAll('.icon-option').forEach(el => el.classList.remove('selected'));
            iconOption.classList.add('selected');
        };
        container.appendChild(iconOption);
    });
    
    return container;
}

/**
 * 创建颜色选择器
 * @param {string} selectedColor - 选中的颜色
 * @returns {HTMLElement} - 颜色选择器元素
 */
function createColorSelector(selectedColor) {
    const container = document.createElement('div');
    container.className = 'color-selector';
    
    const colors = ['#667eea', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];
    
    colors.forEach(color => {
        const colorOption = document.createElement('span');
        colorOption.className = 'color-option';
        if (color === selectedColor) colorOption.classList.add('selected');
        colorOption.style.background = color;
        colorOption.onclick = () => {
            container.querySelectorAll('.color-option').forEach(el => el.classList.remove('selected'));
            colorOption.classList.add('selected');
        };
        container.appendChild(colorOption);
    });
    
    return container;
}

/**
 * 折叠/展开区块
 * @param {HTMLElement} button - 折叠按钮
 */
function toggleSection(button) {
    const section = button.closest('.form-section');
    const content = section.querySelector('.form-grid, .form-vertical');
    
    if (content.style.display === 'none') {
        content.style.display = '';
        button.textContent = '▼';
    } else {
        content.style.display = 'none';
        button.textContent = '▶';
    }
}

/**
 * 从动态表单收集数据
 * @returns {Object} - 收集的角色数据
 */
function collectDataFromForm() {
    const data = {};
    
    // 遍历所有表单字段
    document.querySelectorAll('[data-field-key]').forEach(element => {
        const fieldKey = element.dataset.fieldKey;
        let value;
        
        // 根据元素类型获取值
        if (element.tagName === 'SELECT') {
            value = element.value;
        } else if (element.tagName === 'TEXTAREA') {
            value = element.value;
        } else if (element.type === 'text') {
            value = element.value;
        } else if (element.classList.contains('icon-selector')) {
            const selected = element.querySelector('.icon-option.selected');
            value = selected ? selected.textContent : '👤';
        } else if (element.classList.contains('color-selector')) {
            const selected = element.querySelector('.color-option.selected');
            value = selected ? selected.style.background : '#667eea';
        }
        
        // 处理嵌套字段
        if (fieldKey.includes('.')) {
            const parts = fieldKey.split('.');
            let current = data;
            for (let i = 0; i < parts.length - 1; i++) {
                if (!current[parts[i]]) {
                    current[parts[i]] = {};
                }
                current = current[parts[i]];
            }
            current[parts[parts.length - 1]] = value;
        } else {
            data[fieldKey] = value;
        }
    });
    
    return data;
}

// ==================== 全局导出 ====================

window.generateFormFromJSON = generateFormFromJSON;
window.collectDataFromForm = collectDataFromForm;
window.toggleSection = toggleSection;