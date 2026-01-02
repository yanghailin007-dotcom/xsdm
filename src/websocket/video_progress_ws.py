"""
WebSocket实时进度推送服务

功能：
- 实时推送任务进度更新
- 支持多客户端连接
- 广播任务状态变化
"""

import asyncio
import json
from typing import Dict, Set, Any
from datetime import datetime
import logging

try:
    from flask_socketio import SocketIO, emit
    from flask import request
    HAS_SOCKETIO = True
except ImportError:
    HAS_SOCKETIO = False
    logging.warning("Flask-SocketIO未安装，WebSocket功能将不可用")

from src.utils.logger import get_logger


class VideoProgressWS:
    """视频进度WebSocket服务"""
    
    def __init__(self, app=None):
        """
        初始化WebSocket服务
        
        Args:
            app: Flask应用实例
        """
        self.logger = get_logger("VideoProgressWS")
        self.connected_clients: Set[str] = set()
        
        if HAS_SOCKETIO:
            self.socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
            self._register_handlers()
            self.logger.info("✅ WebSocket服务初始化完成")
        else:
            self.socketio = None
            self.logger.warning("⚠️  Flask-SocketIO未安装，WebSocket功能不可用")
    
    def _register_handlers(self):
        """注册WebSocket事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            self.connected_clients.add(client_id)
            self.logger.info(f"✅ 客户端连接: {client_id}")
            emit('connected', {'message': 'WebSocket连接成功'})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            self.connected_clients.discard(client_id)
            self.logger.info(f"❌ 客户端断开: {client_id}")
        
        @self.socketio.on('subscribe_task')
        def handle_subscribe_task(data):
            """订阅任务进度"""
            client_id = request.sid
            task_id = data.get('task_id')
            
            if task_id:
                # 加入任务房间
                from flask import join_room
                join_room(f'task_{task_id}')
                self.logger.info(f"📋 客户端 {client_id} 订阅任务: {task_id}")
                emit('subscribed', {'task_id': task_id})
        
        @self.socketio.on('unsubscribe_task')
        def handle_unsubscribe_task(data):
            """取消订阅任务进度"""
            client_id = request.sid
            task_id = data.get('task_id')
            
            if task_id:
                from flask import leave_room
                leave_room(f'task_{task_id}')
                self.logger.info(f"📋 客户端 {client_id} 取消订阅任务: {task_id}")
                emit('unsubscribed', {'task_id': task_id})
    
    async def broadcast_progress(self, task_id: str, event: str, data: Dict[str, Any]):
        """
        广播进度更新到所有订阅该任务的客户端
        
        Args:
            task_id: 任务ID
            event: 事件类型
            data: 事件数据
        """
        if not self.socketio:
            return
        
        message = {
            'task_id': task_id,
            'event': event,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        # 发送到任务房间
        self.socketio.emit('progress_update', message, room=f'task_{task_id}')
        
        self.logger.debug(f"📡 广播进度: {task_id} - {event}")
    
    async def broadcast_task_completed(self, task_id: str, result: Dict):
        """广播任务完成"""
        await self.broadcast_progress(task_id, 'task_completed', result)
    
    async def broadcast_task_failed(self, task_id: str, error: str):
        """广播任务失败"""
        await self.broadcast_progress(task_id, 'task_failed', {'error': error})
    
    async def broadcast_shot_started(self, task_id: str, shot_index: int):
        """广播镜头开始"""
        await self.broadcast_progress(task_id, 'shot_started', {'shot_index': shot_index})
    
    async def broadcast_shot_progress(self, task_id: str, shot_index: int, progress: float):
        """广播镜头进度"""
        await self.broadcast_progress(task_id, 'shot_progress', {
            'shot_index': shot_index,
            'progress': progress
        })
    
    async def broadcast_shot_completed(self, task_id: str, shot_index: int, result: Dict):
        """广播镜头完成"""
        await self.broadcast_progress(task_id, 'shot_completed', {
            'shot_index': shot_index,
            'result': result
        })
    
    async def broadcast_shot_failed(self, task_id: str, shot_index: int, error: str):
        """广播镜头失败"""
        await self.broadcast_progress(task_id, 'shot_failed', {
            'shot_index': shot_index,
            'error': error
        })
    
    def emit_sync(self, task_id: str, event: str, data: Dict):
        """同步发送进度更新（用于非异步上下文）"""
        if not self.socketio:
            return
        
        message = {
            'task_id': task_id,
            'event': event,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        
        self.socketio.emit('progress_update', message, room=f'task_{task_id}')


# 创建全局WebSocket服务实例
_ws_service = None


def get_video_progress_ws(app=None):
    """
    获取WebSocket服务实例
    
    Args:
        app: Flask应用实例
    
    Returns:
        WebSocket服务实例
    """
    global _ws_service
    if _ws_service is None and app:
        _ws_service = VideoProgressWS(app)
    return _ws_service