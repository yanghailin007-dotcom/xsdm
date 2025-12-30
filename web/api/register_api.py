"""
用户注册API
集成手机验证码功能
"""
from flask import request, jsonify, session
from datetime import datetime
import re

from web.web_config import logger
from web.models.user_model import user_model, verification_model
from web.services.sms_service import sms_service, rate_limiter


def register_register_routes(app):
    """注册用户注册相关API路由"""
    
    @app.route('/api/register/send-code', methods=['POST'])
    def send_verification_code():
        """
        发送验证码
        
        请求体:
        {
            "phone": "13800138000"
        }
        
        响应:
        {
            "success": true,
            "message": "验证码已发送",
            "code": "123456"  // 仅开发模式返回
        }
        """
        try:
            data = request.json or {}
            phone = data.get('phone', '').strip()
            
            # 验证手机号格式
            if not sms_service.validate_phone(phone):
                return jsonify({
                    "success": False,
                    "error": "手机号格式不正确"
                }), 400
            
            # 检查频率限制
            allowed, wait_seconds = rate_limiter.check_limit(
                phone, 
                max_requests=3, 
                window_seconds=3600
            )
            
            if not allowed:
                return jsonify({
                    "success": False,
                    "error": f"发送过于频繁，请在{wait_seconds}秒后重试",
                    "wait_seconds": wait_seconds
                }), 429
            
            # 检查手机号是否已注册
            existing_user = user_model.get_user_by_username(phone)
            if existing_user:
                return jsonify({
                    "success": False,
                    "error": "该手机号已注册"
                }), 400
            
            # 生成验证码
            code = verification_model.create_code(
                phone=phone,
                code_type="register",
                expiry_minutes=5,
                ip_address=request.remote_addr or "unknown"
            )
            
            # 发送短信
            result = sms_service.send_verification_code(phone, code)
            
            if result.get("success"):
                response_data = {
                    "success": True,
                    "message": "验证码已发送",
                    "expires_in": 300  # 5分钟
                }
                
                # 开发模式返回验证码
                if result.get("provider") == "mock":
                    response_data["code"] = code
                    response_data["dev_mode"] = True
                
                logger.info(f"✅ 验证码发送成功: {phone}")
                return jsonify(response_data)
            else:
                return jsonify({
                    "success": False,
                    "error": result.get("error", "发送失败")
                }), 500
                
        except Exception as e:
            logger.error(f"❌ 发送验证码失败: {e}")
            return jsonify({
                "success": False,
                "error": "发送失败，请稍后重试"
            }), 500
    
    @app.route('/api/register/verify-code', methods=['POST'])
    def verify_code():
        """
        验证验证码
        
        请求体:
        {
            "phone": "13800138000",
            "code": "123456"
        }
        
        响应:
        {
            "success": true,
            "message": "验证成功"
        }
        """
        try:
            data = request.json or {}
            phone = data.get('phone', '').strip()
            code = data.get('code', '').strip()
            
            # 验证手机号格式
            if not sms_service.validate_phone(phone):
                return jsonify({
                    "success": False,
                    "error": "手机号格式不正确"
                }), 400
            
            # 验证验证码
            if not verification_model.verify_code(phone, code, "register"):
                return jsonify({
                    "success": False,
                    "error": "验证码错误或已过期"
                }), 400
            
            # 验证成功，在session中标记
            session['verified_phone'] = phone
            session['verified_time'] = datetime.now().isoformat()
            
            return jsonify({
                "success": True,
                "message": "验证成功"
            })
            
        except Exception as e:
            logger.error(f"❌ 验证码验证失败: {e}")
            return jsonify({
                "success": False,
                "error": "验证失败"
            }), 500
    
    @app.route('/api/register', methods=['POST'])
    def register_user():
        """
        用户注册
        
        请求体:
        {
            "username": "testuser",
            "password": "password123",
            "phone": "13800138000",
            "code": "123456",
            "email": "optional@email.com"
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
            username = data.get('username', '').strip()
            password = data.get('password', '')
            phone = data.get('phone', '').strip()
            code = data.get('code', '').strip()
            email = data.get('email', '').strip() or None
            
            # 验证必填字段
            if not all([username, password, phone, code]):
                return jsonify({
                    "success": False,
                    "error": "请填写完整信息"
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
            
            # 验证手机号格式
            if not sms_service.validate_phone(phone):
                return jsonify({
                    "success": False,
                    "error": "手机号格式不正确"
                }), 400
            
            # 验证手机号是否与验证码一致
            verified_phone = session.get('verified_phone')
            if not verified_phone or verified_phone != phone:
                return jsonify({
                    "success": False,
                    "error": "请先验证手机号"
                }), 400
            
            # 再次验证验证码（确保未过期且正确）
            if not verification_model.verify_code(phone, code, "register"):
                return jsonify({
                    "success": False,
                    "error": "验证码错误或已过期"
                }), 400
            
            # 创建用户
            result = user_model.create_user(
                username=username,
                password=password,
                phone=phone,
                email=email or None
            )
            
            if result.get("success"):
                # 清除session中的验证信息
                session.pop('verified_phone', None)
                session.pop('verified_time', None)
                
                logger.info(f"✅ 用户注册成功: {username} ({phone})")
                
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
            username = data.get('username', '').strip()
            
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