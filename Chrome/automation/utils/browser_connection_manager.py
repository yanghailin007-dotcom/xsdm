import os
import time
import subprocess
import socket
import psutil
from typing import Optional, Tuple, List
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class BrowserConnectionManager:
    """浏览器连接管理器 - 解决连接错误问题"""
    
    def __init__(self, debug_port: int = 9988, max_retries: int = 3):
        self.debug_port = debug_port
        self.max_retries = max_retries
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    def is_port_available(self, port: int) -> bool:
        """检查端口是否可用"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('127.0.0.1', port))
                return result != 0
        except:
            return False
    
    def find_available_port(self, start_port: int = 9988) -> int:
        """查找可用端口"""
        for port in range(start_port, start_port + 100):
            if self.is_port_available(port):
                return port
        raise Exception("无法找到可用端口")
    
    def kill_existing_chrome_processes(self) -> bool:
        """杀死现有的Chrome进程"""
        try:
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('chrome' in str(cmd).lower() for cmd in cmdline):
                        if f'--remote-debugging-port={self.debug_port}' in ' '.join(cmdline):
                            print(f"终止现有Chrome进程 (PID: {proc.info['pid']})")
                            proc.terminate()
                            killed_count += 1
                            time.sleep(1)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if killed_count > 0:
                print(f"✓ 已终止 {killed_count} 个Chrome进程")
                return True
            return False
        except Exception as e:
            print(f"终止Chrome进程时出错: {e}")
            return False
    
    def start_chrome_with_debug(self, chrome_path: str = None, user_data_dir: str = None) -> Optional[subprocess.Popen]:
        """启动带调试端口的Chrome"""
        try:
            # 查找Chrome路径
            if not chrome_path:
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    r"D:\work6.05\Chrome\Chrome\App\chrome.exe",  # 您的路径
                    os.path.expanduser("~/AppData/Local/Google/Chrome/Application/chrome.exe"),
                ]
                
                chrome_path = None
                for path in chrome_paths:
                    if os.path.exists(path):
                        chrome_path = path
                        break
                
                if not chrome_path:
                    raise Exception("未找到Chrome可执行文件")
            
            # 设置用户数据目录
            if not user_data_dir:
                user_data_dir = os.path.join(os.getcwd(), "chrome_user_data")
            
            # 确保目录存在
            os.makedirs(user_data_dir, exist_ok=True)
            
            # 构建启动命令
            cmd = [
                chrome_path,
                f"--remote-debugging-port={self.debug_port}",
                f"--user-data-dir={user_data_dir}",
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-images",  # 可选：禁用图片加载以提高速度
                "--disable-javascript",  # 可选：如果不需要JS可以禁用
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-background-networking",
                "--disable-default-apps",
                "--disable-sync",
                "--metrics-recording-only",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-hang-monitor",
                "--disable-client-side-phishing-detection",
                "--disable-component-extensions-with-background-pages",
                "--disable-component-update",
                "--disable-domain-reliability",
                "--start-maximized",
                "about:blank"
            ]
            
            print(f"启动Chrome: {chrome_path}")
            print(f"调试端口: {self.debug_port}")
            print(f"用户数据目录: {user_data_dir}")
            
            # 启动Chrome
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # 等待Chrome启动
            print("等待Chrome启动...")
            for i in range(30):  # 最多等待30秒
                if self.is_port_available(self.debug_port) == False:  # 端口被占用说明Chrome已启动
                    print(f"✓ Chrome已启动 (耗时 {i + 1} 秒)")
                    return process
                time.sleep(1)
            
            raise Exception("Chrome启动超时")
            
        except Exception as e:
            print(f"启动Chrome失败: {e}")
            return None
    
    def connect_to_browser(self, retry_count: int = 0) -> Tuple[Optional[sync_playwright], Optional[Browser], Optional[BrowserContext], Optional[Page]]:
        """连接到浏览器 - 带重试机制"""
        try:
            print(f"尝试连接到浏览器 (端口: {self.debug_port}, 重试: {retry_count + 1}/{self.max_retries})")
            
            # 启动Playwright
            if not self.playwright:
                self.playwright = sync_playwright().start()
            
            # 尝试连接
            self.browser = self.playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{self.debug_port}")
            
            # 获取上下文和页面
            contexts = self.browser.contexts
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                if pages:
                    self.page = pages[0]
                else:
                    self.page = self.context.new_page()
            else:
                self.context = self.browser.new_context()
                self.page = self.context.new_page()
            
            print("✓ 成功连接到浏览器")
            return self.playwright, self.browser, self.context, self.page
            
        except Exception as e:
            print(f"连接失败 (重试 {retry_count + 1}): {e}")
            
            if retry_count < self.max_retries - 1:
                print(f"等待 3 秒后重试...")
                time.sleep(3)
                return self.connect_to_browser(retry_count + 1)
            else:
                print("✗ 所有连接尝试都失败了")
                self.cleanup()
                return None, None, None, None
    
    def ensure_browser_running(self, chrome_path: str = None, force_restart: bool = False) -> bool:
        """确保浏览器正在运行"""
        try:
            # 检查端口是否可用
            port_in_use = not self.is_port_available(self.debug_port)
            
            if force_restart or not port_in_use:
                print("浏览器未运行或需要重启")
                
                if port_in_use:
                    print("终止现有Chrome进程...")
                    self.kill_existing_chrome_processes()
                    time.sleep(2)
                
                # 查找可用端口
                if not port_in_use:
                    self.debug_port = self.find_available_port(self.debug_port)
                    print(f"使用端口: {self.debug_port}")
                
                # 启动Chrome
                process = self.start_chrome_with_debug(chrome_path)
                if not process:
                    return False
                
                # 等待Chrome完全启动
                time.sleep(3)
            
            # 连接到浏览器
            playwright, browser, context, page = self.connect_to_browser()
            return browser is not None
            
        except Exception as e:
            print(f"确保浏览器运行时出错: {e}")
            return False
    
    def get_connection_status(self) -> dict:
        """获取连接状态信息"""
        status = {
            "port_available": self.is_port_available(self.debug_port),
            "debug_port": self.debug_port,
            "playwright_active": self.playwright is not None,
            "browser_connected": self.browser is not None,
            "context_active": self.context is not None,
            "page_active": self.page is not None,
            "chrome_processes": []
        }
        
        # 查找Chrome进程
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and any('chrome' in str(cmd).lower() for cmd in cmdline):
                        if f'--remote-debugging-port={self.debug_port}' in ' '.join(cmdline):
                            status["chrome_processes"].append({
                                "pid": proc.info['pid'],
                                "cmdline": ' '.join(cmdline)[:100] + "..."
                            })
                except:
                    continue
        except:
            pass
        
        return status
    
    def diagnose_connection_issues(self) -> List[str]:
        """诊断连接问题"""
        issues = []
        status = self.get_connection_status()
        
        if status["port_available"]:
            issues.append(f"端口 {self.debug_port} 可用，但没有Chrome进程在监听")
        
        if not status["chrome_processes"]:
            issues.append("未找到带调试端口的Chrome进程")
            issues.append("建议: 启动Chrome时添加 --remote-debugging-port参数")
        
        if status["chrome_processes"] and status["port_available"]:
            issues.append("Chrome进程存在但端口无法访问")
            issues.append("可能原因: Chrome启动失败或参数错误")
        
        # 检查常见问题
        try:
            import requests
            response = requests.get(f"http://127.0.0.1:{self.debug_port}/json/version", timeout=5)
            if response.status_code != 200:
                issues.append(f"调试接口响应异常: {response.status_code}")
        except requests.exceptions.ConnectionError:
            issues.append("无法连接到调试接口")
        except requests.exceptions.Timeout:
            issues.append("调试接口连接超时")
        except ImportError:
            pass
        
        return issues
    
    def cleanup(self):
        """清理资源"""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except:
            pass
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
    
    def __del__(self):
        """析构函数"""
        self.cleanup()


# 便捷函数
def create_browser_connection(debug_port: int = 9988, chrome_path: str = None, force_restart: bool = False) -> BrowserConnectionManager:
    """创建浏览器连接"""
    manager = BrowserConnectionManager(debug_port)
    
    if manager.ensure_browser_running(chrome_path, force_restart):
        return manager
    else:
        raise Exception("无法建立浏览器连接")


# 测试函数
def test_browser_connection():
    """测试浏览器连接"""
    print("=== 浏览器连接测试 ===")
    
    manager = BrowserConnectionManager()
    
    # 显示连接状态
    status = manager.get_connection_status()
    print("连接状态:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 诊断问题
    issues = manager.diagnose_connection_issues()
    if issues:
        print("\n发现的问题:")
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("\n✓ 未发现明显问题")
    
    # 尝试连接
    print("\n尝试建立连接...")
    try:
        # 使用您项目中的Chrome路径
        chrome_path = r"D:\work6.05\Chrome\Chrome\App\chrome.exe"
        if manager.ensure_browser_running(chrome_path, force_restart=True):
            print("✓ 连接成功!")
            
            # 测试页面导航
            if manager.page:
                manager.page.goto("https://www.baidu.com")
                title = manager.page.title()
                print(f"✓ 页面导航成功: {title}")
        else:
            print("✗ 连接失败")
    except Exception as e:
        print(f"✗ 测试失败: {e}")
    finally:
        manager.cleanup()


if __name__ == "__main__":
    test_browser_connection()