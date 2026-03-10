# 子线程被Kill问题解决方案

## 问题分析

当前代码中所有后台线程都设置了 `daemon = True`：
```python
thread = threading.Thread(target=run_generation)
thread.daemon = True  # ❌ 问题所在
thread.start()
```

**Daemon线程的问题：**
1. 主程序退出时，daemon线程会被强制终止
2. 系统资源紧张时，daemon线程可能被回收
3. 线程异常退出时，没有恢复机制

## 解决方案

### 1. 立即修复：将daemon改为False

### 2. 添加线程保活机制
- 线程健康检查（每30秒检查一次）
- 自动恢复（检测到线程死亡时重新启动）
- 持久化任务状态（即使线程死了也能恢复）

### 3. 添加优雅退出机制
- 使用shutdown标志位
- 等待线程自然结束
- 避免强制kill

## 实施步骤

1. 修改novel_manager.py中的线程创建
2. 添加ThreadMonitor类监控线程健康
3. 添加任务自动恢复机制
4. 添加日志记录便于排查
