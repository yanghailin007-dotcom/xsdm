// 在浏览器控制台中运行此脚本检查首次提示
console.clear();
console.log('=== 首次进入提示调试 ===');

// 1. 检查 localStorage
const storedProject = localStorage.getItem('selectedProjectTitle');
console.log('1. localStorage.selectedProjectTitle:', storedProject || '(空)');

// 2. 检查 URL 参数
const urlParams = new URLSearchParams(window.location.search);
const urlTitle = urlParams.get('title');
console.log('2. URL title 参数:', urlTitle || '(空)');

// 3. 检查提示元素
const hint = document.getElementById('first-time-hint');
console.log('3. first-time-hint 元素:', hint ? '存在' : '不存在');
if (hint) {
    console.log('   可见性:', hint.offsetParent !== null ? '可见' : '不可见');
    console.log('   尺寸:', hint.offsetWidth, 'x', hint.offsetHeight);
    console.log('   内容预览:', hint.innerText.substring(0, 50) + '...');
}

// 4. 检查 project-details
const details = document.getElementById('project-details');
console.log('4. project-details 元素:', details ? '存在' : '不存在');
if (details) {
    console.log('   HTML内容预览:', details.innerHTML.substring(0, 200));
}

// 5. 检查右侧面板
const rightPanel = document.getElementById('right-panel');
console.log('5. right-panel 元素:', rightPanel ? '存在' : '不存在');

// 6. 检查是否有项目被选中
const selectedCard = document.querySelector('.project-select-card.selected');
console.log('6. 是否有选中的项目卡片:', selectedCard ? '是' : '否');

// 7. 显示所有项目卡片
const cards = document.querySelectorAll('.project-select-card');
console.log('7. 项目卡片数量:', cards.length);

console.log('=== 调试结束 ===');
