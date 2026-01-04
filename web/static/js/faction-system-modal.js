// ==================== 势力系统模态框功能 ====================

// 势力数据
const factionsData = [
    {
        name: "浩然剑宗",
        type: "正道/宗门",
        powerLevel: "一流",
        powerClass: "power-level-一流",
        icon: "⚔️",
        corePhilosophy: "顺我者昌，逆我者魔；以天地万物奉养己身。",
        background: "号称正道魁首，实则虚伪至极。宗门建立在一条巨大的灵脉之上，千年来以'斩妖除魔'为名，暗中掠夺凡人血气供奉老祖。宗内等级森严，外门弟子如猪狗，真传弟子享用一切。其禁地'弃剑渊'是埋葬无数废剑与失败弟子尸骨的极阴之地。",
        advantages: "拥有护宗大阵'浩然天罡'、垄断周边十国的修仙资源",
        disadvantages: "内部派系林立，互相倾轧、高层寿元将尽，急需续命邪法",
        allies: "天道盟",
        enemies: "血魂殿",
        storyRole: "新手村BOSS势力。主角在此苏醒，通过第一任宿主林寒大杀四方，揭露其虚伪面目，最终将其灭门吞噬，作为第一桶金。"
    },
    {
        name: "大乾皇朝",
        type: "朝廷/世俗",
        powerLevel: "二流（潜力极大）",
        powerClass: "power-level-二流（潜力极大）",
        icon: "👑",
        corePhilosophy: "普天之下，莫非王土（名义上）。",
        background: "统御亿万疆土的古老皇朝，但如今皇权旁落，奸臣当道，各地诸侯割据。皇室血脉凋零，当朝皇帝昏庸无道，沉迷炼丹长生。落魄公主（第二任宿主）正是在这种绝境中苟延残喘，等待复仇。",
        advantages: "庞大的人口基数（血气来源）、皇室秘库中的上古残卷",
        disadvantages: "凡人军队难以对抗高阶修士、权力中枢腐败",
        allies: "浩然剑宗（依附关系）",
        enemies: "各地起义军、觊觎皇权的世家",
        storyRole: "中期核心地图。主角扶持落魄公主姬无双，在此通过权谋与杀戮清洗朝堂，建立'魔剑帝国'，将整个国家转化为战争机器。"
    },
    {
        name: "血魂殿",
        type: "魔道/宗门",
        powerLevel: "一流",
        powerClass: "power-level-一流",
        icon: "💀",
        corePhilosophy: "万物皆虚，唯杀永恒。",
        background: "行事癫狂的魔道巨擘，信奉'杀戮证道'。成员多为被正道追杀的凶徒，手段残忍，喜好剥皮抽筋炼制法宝。他们虽然是魔道，但格局太小，只知杀人不知'养猪'，是主角眼中的低级竞争对手。",
        advantages: "单兵作战能力极强、拥有大量邪恶禁术",
        disadvantages: "全员疯子，毫无纪律、容易被正道集火",
        allies: "无",
        enemies: "浩然剑宗、天道盟",
        storyRole: "经验包势力。主角在建立魔道帝国时，会先收服或吞噬血魂殿，整合魔道资源，证明谁才是'真魔'。"
    },
    {
        name: "天道盟",
        type: "中立/执法者",
        powerLevel: "超一流（天花板）",
        powerClass: "power-level-超一流（天花板）",
        icon: "⚖️",
        corePhilosophy: "天道无亲，常与善人；器物不可成精。",
        background: "由上界仙人扶持的监察机构，自诩为世界秩序的维护者。他们极其神秘，平时不显山露水，一旦有超出界限的力量（如主角这种逆天魔剑）出现，便会降下雷霆一击。他们坚守'人御剑'的铁律，绝不允许器灵噬主。",
        advantages: "掌握通往上界的通道、拥有降维打击的神通",
        disadvantages: "人手稀少、傲慢自大，轻视下界生灵",
        allies: "各大正道宗门",
        enemies: "主角（魔剑）、所有试图逆天的魔头",
        storyRole: "最终BOSS势力。从中期开始不断阻挠主角，后期甚至会有上界仙人下凡追杀，是主角'斩断天路'的主要障碍。"
    },
    {
        name: "天机阁",
        type: "中立/商业",
        powerLevel: "一流（隐世）",
        powerClass: "power-level-一流（隐世）",
        icon: "📊",
        corePhilosophy: "利字当头，和气生财。",
        background: "遍布天下的情报与商业组织，号称'只要付得起代价，连仙人的内裤颜色都能查到'。保持绝对中立，向正魔两道同时出售情报和资源。",
        advantages: "情报网覆盖全界、拥有无数保命底牌",
        disadvantages: "战斗力相对较弱、容易被强者勒索",
        allies: "所有顾客",
        enemies: "试图赖账的人",
        storyRole: "工具人势力。为主角提供寻找特殊金属、特殊体质宿主的情报。主角偶尔会'物理打折'强买强卖。"
    }
];

// 初始化势力系统
document.addEventListener('DOMContentLoaded', function() {
    initializeFactionSystem();
});

function initializeFactionSystem() {
    // 检查是否已存在模态框
    let modal = document.getElementById('faction-system-modal');
    
    if (!modal) {
        // 创建模态框
        modal = createFactionModal();
        document.body.appendChild(modal);
    }
    
    // 为所有势力卡片添加点击事件
    attachFactionCardListeners();
}

// 创建模态框
function createFactionModal() {
    const modal = document.createElement('div');
    modal.id = 'faction-system-modal';
    modal.className = 'faction-modal';
    modal.innerHTML = `
        <div class="faction-modal-content" onclick="event.stopPropagation()">
            <div class="faction-modal-header" id="modal-header">
                <div class="header-icon">⚔️</div>
                <div class="header-text">
                    <h2>势力/阵营系统</h2>
                    <p>查看和管理世界中的各个势力及其关系</p>
                </div>
                <button class="close-btn" onclick="closeFactionModal()">×</button>
            </div>
            
            <div id="faction-list-view">
                <div class="faction-overview">
                    <div class="overview-card">
                        <div class="overview-icon">⚡</div>
                        <div class="overview-content">
                            <div class="overview-label">主要冲突</div>
                            <div class="overview-value">'剑御人'的逆天魔道法则 VS '人御剑'的传统修仙秩序。主角作为魔剑，要吞噬众生进化，必然与所有试图掌控、利用、毁灭它的势力产生死战。</div>
                        </div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-icon">⚖️</div>
                        <div class="overview-content">
                            <div class="overview-label">势力平衡</div>
                            <div class="overview-value">正道（浩然剑宗、天道盟）目前占据绝对统治地位，魔道（血魂殿）苟延残喘，世俗皇权（大乾）摇摇欲坠。主角的出现将打破这一平衡，形成'主角VS全世界'的局面。</div>
                        </div>
                    </div>
                    <div class="overview-card">
                        <div class="overview-icon">🎯</div>
                        <div class="overview-content">
                            <div class="overview-label">推荐势力</div>
                            <div class="overview-value">浩然剑宗（弃剑渊）。原因：1.符合'废剑'开局设定；2.第一任'废物宿主'在此，方便展开'莫欺少年穷'和'打脸'剧情；3.正道伪善的背景能最大化主角'噬主'和'屠宗'的爽感合理性。</div>
                        </div>
                    </div>
                </div>
                
                <div class="factions-grid" id="factions-grid"></div>
                
                <div class="faction-modal-footer">
                    <button class="btn btn-secondary" onclick="closeFactionModal()">关闭</button>
                </div>
            </div>
            
            <div id="faction-detail-view" class="faction-detail-view"></div>
        </div>
    `;
    
    return modal;
}

// 渲染势力卡片
function renderFactionCards() {
    const grid = document.getElementById('factions-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    factionsData.forEach((faction, index) => {
        const card = document.createElement('div');
        card.className = 'faction-card';
        card.style.animationDelay = `${index * 0.1}s`;
        card.dataset.factionIndex = index;
        
        card.innerHTML = `
            <div class="faction-header">
                <div class="faction-name">${faction.name}</div>
                <div class="faction-type-badge">${faction.type}</div>
            </div>
            <div class="faction-info faction-info-collapsed">
                <div class="info-row">
                    <span class="info-label">势力等级</span>
                    <span class="info-value ${faction.powerClass}">${faction.powerLevel}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">核心理念</span>
                    <span class="info-value philosophy-preview">${faction.corePhilosophy}</span>
                </div>
                <div class="info-row expand-hint">
                    <span class="info-value">点击查看详细信息 ↓</span>
                </div>
                <div class="faction-details-expanded" style="display: none;">
                    <div class="info-row">
                        <span class="info-label">势力背景</span>
                        <span class="info-value">${faction.background}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">优势</span>
                        <span class="info-value">${faction.advantages}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">劣势</span>
                        <span class="info-value">${faction.disadvantages}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">盟友势力</span>
                        <span class="info-value allies">${faction.allies}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">敌对势力</span>
                        <span class="info-value enemies">${faction.enemies}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">剧情作用</span>
                        <span class="info-value">${faction.storyRole}</span>
                    </div>
                    <div class="info-row collapse-hint">
                        <span class="info-value">点击收起 ↑</span>
                    </div>
                </div>
            </div>
        `;
        
        grid.appendChild(card);
    });
}

// 为势力卡片添加点击事件
function attachFactionCardListeners() {
    const existingCards = document.querySelectorAll('.faction-card');
    
    existingCards.forEach(card => {
        card.addEventListener('click', function(e) {
            e.stopPropagation();
            
            // 切换展开/收起状态
            const factionInfo = this.querySelector('.faction-info');
            const expandedDetails = this.querySelector('.faction-details-expanded');
            const expandHint = this.querySelector('.expand-hint');
            
            if (expandedDetails.style.display === 'none') {
                // 展开详情
                expandedDetails.style.display = 'block';
                factionInfo.classList.remove('faction-info-collapsed');
                factionInfo.classList.add('faction-info-expanded');
                if (expandHint) {
                    expandHint.style.display = 'none';
                }
            } else {
                // 收起详情
                expandedDetails.style.display = 'none';
                factionInfo.classList.remove('faction-info-expanded');
                factionInfo.classList.add('faction-info-collapsed');
                if (expandHint) {
                    expandHint.style.display = 'flex';
                }
            }
        });
    });
}

// 打开模态框
function openFactionModal() {
    const modal = document.getElementById('faction-system-modal');
    if (modal) {
        renderFactionCards();
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

// 关闭模态框
function closeFactionModal() {
    const modal = document.getElementById('faction-system-modal');
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// 点击背景关闭模态框
document.addEventListener('click', function(e) {
    const modal = document.getElementById('faction-system-modal');
    if (modal && e.target === modal) {
        closeFactionModal();
    }
});

// ESC键关闭模态框
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        closeFactionModal();
    }
});

// 显示势力详情（保留用于其他可能需要的地方）
function showFactionDetail(index) {
    const faction = factionsData[index];
    if (!faction) return;
    
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏列表视图
    if (listView) listView.style.display = 'none';
    
    // 更新头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = faction.name;
        modalHeader.querySelector('.header-text p').textContent = faction.type;
    }
    
    // 渲染详情视图
    if (detailView) {
        detailView.innerHTML = `
            <button class="detail-back-btn" onclick="hideFactionDetail()">
                <span>←</span>
                <span>返回列表</span>
            </button>
            
            <div class="detail-header">
                <div class="detail-header-content">
                    <h1 class="detail-name">${faction.name}</h1>
                    <div>
                        <span class="detail-type">${faction.type}</span>
                        <span class="detail-power-level">
                            <span>⚡</span>
                            <span>${faction.powerLevel}</span>
                        </span>
                    </div>
                </div>
            </div>
            
            <div class="detail-philosophy">
                "${faction.corePhilosophy}"
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">📖</span>
                    <span>势力背景</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.background}</p>
                </div>
            </div>
            
            <div class="detail-grid">
                <div class="detail-grid-item">
                    <div class="detail-grid-label">优势</div>
                    <div class="detail-grid-value">${faction.advantages}</div>
                </div>
                <div class="detail-grid-item">
                    <div class="detail-grid-label">劣势</div>
                    <div class="detail-grid-value">${faction.disadvantages}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🤝</span>
                    <span>势力关系</span>
                </h3>
                <div class="detail-grid">
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">盟友势力</div>
                        <div class="detail-grid-value allies">${faction.allies}</div>
                    </div>
                    <div class="detail-grid-item">
                        <div class="detail-grid-label">敌对势力</div>
                        <div class="detail-grid-value enemies">${faction.enemies}</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3 class="detail-section-title">
                    <span class="detail-section-icon">🎬</span>
                    <span>剧情作用</span>
                </h3>
                <div class="detail-section-content">
                    <p>${faction.storyRole}</p>
                </div>
            </div>
        `;
        
        detailView.classList.add('active');
    }
}

// 隐藏势力详情
function hideFactionDetail() {
    const listView = document.getElementById('faction-list-view');
    const detailView = document.getElementById('faction-detail-view');
    const modalHeader = document.getElementById('modal-header');
    
    // 隐藏详情视图
    if (detailView) {
        detailView.classList.remove('active');
    }
    
    // 恢复头部
    if (modalHeader) {
        modalHeader.querySelector('.header-text h2').textContent = '势力/阵营系统';
        modalHeader.querySelector('.header-text p').textContent = '查看和管理世界中的各个势力及其关系';
    }
    
    // 显示列表视图
    if (listView) listView.style.display = 'block';
}

// 导出函数供全局使用
window.openFactionModal = openFactionModal;
window.closeFactionModal = closeFactionModal;
window.showFactionDetail = showFactionDetail;
window.hideFactionDetail = hideFactionDetail;