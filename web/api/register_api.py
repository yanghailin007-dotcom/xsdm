"""
用户注册API
简化版本 - 无需手机验证码
"""
from flask import request, jsonify, session
from datetime import datetime
import re

from web.web_config import logger
from web.models.user_model import user_model


def register_register_routes(app):
    """注册用户注册相关API路由"""
    
    @app.route('/api/register', methods=['POST'])
    def register_user():
        """
        用户注册（简化版 - 无需手机号验证码）
        
        请求体:
        {
            "username": "testuser",
            "password": "password123",
            "email": "optional@email.com"  // 可选
        }
        
        响应:
        {
            "success": true,
            "message": "注册成功",
            "user_id": 1
        }
        """
        try:
            data = request.json or {}
            username = (data.get('username') or '').strip()
            password = data.get('password') or ''
            email = (data.get('email') or '').strip() or None
            
            # 验证必填字段
            if not all([username, password]):
                return jsonify({
                    "success": False,
                    "error": "请填写用户名和密码"
                }), 400
            
            # 验证用户名格式（3-20个字符，字母数字下划线）
            if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
                return jsonify({
                    "success": False,
                    "error": "用户名只能包含字母、数字和下划线，长度3-20个字符"
                }), 400
            
            # 验证密码强度（至少6个字符）
            if len(password) < 6:
                return jsonify({
                    "success": False,
                    "error": "密码长度至少6个字符"
                }), 400
            
            # 创建用户（phone 设为 None，表示未绑定手机号）
            result = user_model.create_user(
                username=username,
                password=password,
                phone=None,
                email=email
            )
            
            if result.get("success"):
                logger.info(f"✅ 用户注册成功: {username}")
                
                return jsonify({
                    "success": True,
                    "message": "注册成功，请登录",
                    "user_id": result.get("user_id")
                })
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "注册失败")
                }), 400
                
        except Exception as e:
            logger.error(f"❌ 用户注册失败: {e}")
            return jsonify({
                "success": False,
                "error": "注册失败，请稍后重试"
            }), 500
    
    @app.route('/api/register/check-username', methods=['POST'])
    def check_username():
        """
        检查用户名是否可用
        
        请求体:
        {
            "username": "testuser"
        }
        
        响应:
        {
            "success": true,
            "available": true
        }
        """
        try:
            data = request.json or {}
            username = (data.get('username') or '').strip()
            
            if not username:
                return jsonify({
                    "success": False,
                    "error": "用户名不能为空"
                }), 400
            
            # 验证用户名格式
            if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
                return jsonify({
                    "success": False,
                    "error": "用户名格式不正确"
                }), 400
            
            # 检查用户名是否存在
            existing_user = user_model.get_user_by_username(username)
            
            return jsonify({
                "success": True,
                "available": existing_user is None
            })
            
        except Exception as e:
            logger.error(f"❌ 检查用户名失败: {e}")
            return jsonify({
                "success": False,
                "error": "检查失败"
            }), 500
