const { contextBridge, ipcRenderer } = require('electron');

// 向渲染进程暴露安全的API
contextBridge.exposeInMainWorld('electronAPI', {
    // 选择文件夹
    selectDirectory: () => ipcRenderer.invoke('select-directory'),

    // 选择文件
    selectFile: (options) => ipcRenderer.invoke('select-file', options),

    // 显示消息框
    showMessage: (options) => ipcRenderer.invoke('show-message', options),

    // 获取平台信息
    platform: process.platform,

    // 是否为桌面应用
    isDesktop: true
});
