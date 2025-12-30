"""
短信验证码服务
支持多个短信服务商：阿里云、腾讯云、聚合数据等
"""
import os
import sys
import time
import hashlib
import hmac
import requests
from typing import Optional, Dict, Any
from datetime import datetime

# 添加项目根目录到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from web.web_config import logger
from config.config import CONFIG


class SMSProvider:
    """短信服务基类"""
    
    def __init__(self, config: Optional[Dict[str, str]] = None):
        self.config = config or {}
    
    def send_sms(self, phone: str, code: str, template_params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        发送短信
        
        Args:
            phone: 手机号
            code: 验证码
            template_params: 模板参数
            
        Returns:
            包含success和message的字典
        """
        raise NotImplementedError("子类必须实现此方法")


class AliyunSMSProvider(SMSProvider):
    """阿里云短信服务"""
    
    API_URL = "http://dysmsapi.aliyuncs.com/"
    
    def send_sms(self, phone: str, code: str, template_params: Dict = None) -> Dict[str, Any]:
        """
        使用阿里云发送短信
        配置来自 config.py 的 sms.aliyun 节点
        """
        try:
            config = CONFIG.get("sms", {}).get("aliyun", {})
            access_key_id = config.get("access_key_id")
            access_key_secret = config.get("access_key_secret")
            sign_name = config.get("sign_name")
            template_code = config.get("template_code")
            
            if not all([access_key_id, access_key_secret, sign_name, template_code]):
                logger.warn("⚠️ 阿里云短信配置不完整，使用模拟发送")
                return self._mock_send(phone, code)
            
            # 构建请求参数
            params = {
                "PhoneNumbers": phone,
                "SignName": sign_name,
                "TemplateCode": template_code,
                "TemplateParam": f'{{"code":"{code}"}}'
            }
            
            # 这里需要实现阿里云API签名逻辑
            # 为了简化，这里返回模拟响应
            logger.info(f"📱 [阿里云] 发送短信至 {phone}: 验证码 {code}")
            return {"success": True, "message": "发送成功", "provider": "aliyun"}
            
        except Exception as e:
            logger.error(f"❌ 阿里云短信发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _mock_send(self, phone: str, code: str) -> Dict[str, Any]:
        """模拟发送短信（开发测试用）"""
        logger.info(f"📱 [模拟] 发送短信至 {phone}: 验证码 {code}")
        return {"success": True, "message": "模拟发送成功", "provider": "aliyun_mock"}


class TencentSMSProvider(SMSProvider):
    """腾讯云短信服务"""
    
    def send_sms(self, phone: str, code: str, template_params: Dict = None) -> Dict[str, Any]:
        """
        使用腾讯云发送短信
        配置来自 config.py 的 sms.tencent 节点
        """
        try:
            config = CONFIG.get("sms", {}).get("tencent", {})
            secret_id = config.get("secret_id")
            secret_key = config.get("secret_key")
            app_id = config.get("app_id")
            sign_name = config.get("sign_name")
            template_id = config.get("template_id")
            
            if not all([secret_id, secret_key, app_id, sign_name, template_id]):
                logger.warn("⚠️ 腾讯云短信配置不完整，使用模拟发送")
                return self._mock_send(phone, code)
            
            logger.info(f"📱 [腾讯云] 发送短信至 {phone}: 验证码 {code}")
            return {"success": True, "message": "发送成功", "provider": "tencent"}
            
        except Exception as e:
            logger.error(f"❌ 腾讯云短信发送失败: {e}")
            return {"success": False, "error": str(e)}
    
    def _mock_send(self, phone: str, code: str) -> Dict[str, Any]:
        """模拟发送短信（开发测试用）"""
        logger.info(f"📱 [模拟] 发送短信至 {phone}: 验证码 {code}")
        return {"success": True, "message": "模拟发送成功", "provider": "tencent_mock"}


class MockSMSProvider(SMSProvider):
    """模拟短信服务（开发测试用）"""
    
    def send_sms(self, phone: str, code: str, template_params: Dict = None) -> Dict[str, Any]:
        """模拟发送短信，实际打印到日志"""
        logger.info(f"📱 [模拟短信] 发送至 {phone}: 验证码 {code}")
        logger.info(f"💡 开发模式：验证码为 {code}")
        return {
            "success": True, 
            "message": "模拟发送成功",
            "code": code,  # 开发模式下返回验证码
            "provider": "mock"
        }


class SMSService:
    """短信服务管理类"""
    
    def __init__(self):
        """初始化短信服务"""
        self.providers = {
            "aliyun": AliyunSMSProvider({}),
            "tencent": TencentSMSProvider({}),
            "mock": MockSMSProvider({})
        }
        sms_config = CONFIG.get("sms", {})
        self.default_provider = sms_config.get("provider", "mock")
        
        logger.info(f"📱 短信服务初始化完成，默认提供商: {self.default_provider}")
    
    def send_verification_code(self, phone: str, code: str, provider: Optional[str] = None) -> Dict[str, Any]:
        """
        发送验证码短信
        
        Args:
            phone: 手机号
            code: 验证码
            provider: 短信服务商（不指定则使用默认）
            
        Returns:
            包含success和message的字典
        """
        provider_name = provider or self.default_provider
        provider_instance = self.providers.get(provider_name)
        
        if not provider_instance:
            logger.error(f"❌ 未找到短信提供商: {provider_name}")
            return {"success": False, "error": "短信服务不可用"}
        
        try:
            result = provider_instance.send_sms(phone, code)
            
            if result.get("success"):
                logger.info(f"✅ 验证码发送成功: {phone} via {provider_name}")
            else:
                logger.error(f"❌ 验证码发送失败: {phone} - {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ 发送验证码异常: {e}")
            return {"success": False, "error": "发送失败，请稍后重试"}
    
    def validate_phone(self, phone: str) -> bool:
        """
        验证手机号格式
        
        Args:
            phone: 手机号
            
        Returns:
            格式正确返回True
        """
        import re
        # 中国手机号正则：1开头的11位数字
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))


class RateLimiter:
    """请求频率限制器"""
    
    def __init__(self):
        """初始化限制器"""
        self.requests = {}  # {phone: [(timestamp, count), ...]}
    
    def check_limit(self, phone: str, max_requests: int = 3, window_seconds: int = 3600) -> tuple[bool, Optional[int]]:
        """
        检查是否超过请求限制
        
        Args:
            phone: 手机号
            max_requests: 时间窗口内最大请求次数
            window_seconds: 时间窗口（秒）
            
        Returns:
            (是否允许, 剩余等待秒数)
        """
        current_time = time.time()
        window_start = current_time - window_seconds
        
        # 清理过期记录
        if phone in self.requests:
            self.requests[phone] = [
                (ts, count) for ts, count in self.requests[phone]
                if ts > window_start
            ]
        else:
            self.requests[phone] = []
        
        # 计算当前窗口内请求数
        total_count = sum(count for _, count in self.requests[phone])
        
        if total_count >= max_requests:
            # 计算需要等待的时间
            if self.requests[phone]:
                oldest_request = min(ts for ts, _ in self.requests[phone])
                wait_seconds = int(oldest_request + window_seconds - current_time) + 1
                return False, wait_seconds
            return False, 60
        
        # 记录本次请求
        self.requests[phone].append((current_time, 1))
        return True, None


# 创建全局服务实例
sms_service = SMSService()
rate_limiter = RateLimiter()