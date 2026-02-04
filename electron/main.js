const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');

let mainWindow;
let flaskProcess;
const FLASK_PORT = 5000;

// 判断是否为开发模式
const isDev = process.env.NODE_ENV === 'development';

// Flask服务器路径
const getFlaskPath = () => {
    if (isDev) {
        // 开发模式：使用Python直接运行
        return {
            command: 'python',
            args: [path.join(__dirname, '..', 'web', 'app.py')]
        };
    } else {
        // 生产模式：使用打包的可执行文件
        const exePath = path.join(process.resourcesPath, 'backend', 'app.exe');
        return {
            command: exePath,
            args: []
        };
    }
};

// 启动Flask服务器
function startFlaskServer() {
    return new Promise((resolve, reject) => {
        const { command, args } = getFlaskPath();

        console.log('启动Flask服务器:', command, args);

        flaskProcess = spawn(command, args, {
            env: {
                ...process.env,
                FLASK_ENV: 'production',
                PYTHONUNBUFFERED: '1'
            }
        });

        flaskProcess.stdout.on('data', (data) => {
            const output = data.toString();
            console.log('[Flask]', output);

            // 检测服务器是否启动成功
            if (output.includes('Running on') || output.includes('WARNING')) {
                setTimeout(() => resolve(), 2000); // 等待2秒确保服务器完全启动
            }
        });

        flaskProcess.stderr.on('data', (data) => {
            console.error('[Flask Error]', data.toString());
        });

        flaskProcess.on('error', (error) => {
            console.error('Flask启动失败:', error);
            reject(error);
        });

        flaskProcess.on('close', (code) => {
            console.log(`Flask进程退出，代码: ${code}`);
        });

        // 超时保护
        setTimeout(() => {
            if (!flaskProcess.killed) {
                resolve(); // 即使没有检测到启动消息，也尝试继续
            }
        }, 10000);
    });
}

// 创建主窗口
function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        icon: path.join(__dirname, 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        },
        title: '短剧工作室',
        backgroundColor: '#1a1a1a',
        show: false // 先不显示，等加载完成后再显示
    });

    // 加载Flask应用
    mainWindow.loadURL(`http://localhost:${FLASK_PORT}`);

    // 窗口加载完成后显示
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    // 开发模式下打开开发者工具
    if (isDev) {
        mainWindow.webContents.openDevTools();
    }

    // 窗口关闭时的处理
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // 处理外部链接
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        require('electron').shell.openExternal(url);
        return { action: 'deny' };
    });
}

// 应用启动
app.whenReady().then(async () => {
    try {
        console.log('正在启动Flask服务器...');
        await startFlaskServer();
        console.log('Flask服务器启动成功');

        createWindow();
    } catch (error) {
        console.error('启动失败:', error);
        dialog.showErrorBox('启动失败', '无法启动后端服务器，请检查日志。');
        app.quit();
    }

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// 所有窗口关闭时退出应用（macOS除外）
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// 应用退出前清理
app.on('before-quit', () => {
    if (flaskProcess) {
        console.log('正在关闭Flask服务器...');
        flaskProcess.kill();
    }
});

// IPC通信：选择文件夹
ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    return result.filePaths[0];
});

// IPC通信：选择文件
ipcMain.handle('select-file', async (event, options) => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile'],
        filters: options?.filters || []
    });
    return result.filePaths[0];
});

// IPC通信：显示消息框
ipcMain.handle('show-message', async (event, options) => {
    return await dialog.showMessageBox(mainWindow, options);
});

// 错误处理
process.on('uncaughtException', (error) => {
    console.error('未捕获的异常:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('未处理的Promise拒绝:', reason);
});
