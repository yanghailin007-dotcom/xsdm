"""
NanoBanana Pro 图像生成器
基于 Gemini 的图像生成服务
"""
import os
import json
import base64
import requests
from datetime import datetime
from typing import Dict, Any, Optional

from web.web_config import logger


class NanoBananaProGenerator:
    """NanoBanana Pro 图像生成器"""
    
    def __init__(self):
        self.base_url = "https://aiapi.world"
        self.api_key = os.environ.get('NANOBANANA_API_KEY', '')
        self.model = "gemini-3.1-flash-image-preview"  # 用户指定的模型
        
    def generate_image(self, prompt: str, size: str = "1K", watermark: bool = False, 
                      save_path: str = None, aspect_ratio: str = "3:4") -> Dict[str, Any]:
        """
        使用 NanoBanana Pro 生成图片
        
        Args:
            prompt: 图像生成提示词
            size: 分辨率 (1K, 2K, 4K)
            watermark: 是否添加水印
            save_path: 保存路径
            aspect_ratio: 宽高比 (1:1, 16:9, 9:16, 3:4, 4:3 等)
            
        Returns:
            包含生成结果的字典
        """
        try:
            if not self.api_key:
                return {
                    "success": False,
                    "error": "未配置 NanoBanana API Key，请在环境变量中设置 NANOBANANA_API_KEY"
                }
            
            # 构建请求体 (cURL 格式使用驼峰命名)
            url = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 构建请求体
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "responseModalities": ["IMAGE"],
                    "temperature": 1.0,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                    "imageConfig": {
                        "aspectRatio": aspect_ratio,
                        "imageSize": size
                    }
                }
            }
            
            logger.info(f"🎨 调用 NanoBanana Pro 生成图片: size={size}, ratio={aspect_ratio}")
            
            response = requests.post(url, headers=headers, json=payload, timeout=300)
            response.raise_for_status()
            
            result = response.json()
            
            # 解析响应获取图片
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    
                    for part in parts:
                        if "inlineData" in part:
                            inline_data = part["inlineData"]
                            mime_type = inline_data.get("mimeType", "image/png")
                            image_data = inline_data.get("data", "")
                            
                            # Base64 解码图片数据
                            if image_data:
                                image_bytes = base64.b64decode(image_data)
                                
                                # 保存图片
                                if save_path:
                                    os.makedirs(os.path.dirname(save_path), exist_ok=True)
                                    with open(save_path, "wb") as f:
                                        f.write(image_bytes)
                                    
                                    logger.info(f"✅ 图片已保存: {save_path}")
                                    
                                    return {
                                        "success": True,
                                        "local_path": save_path,
                                        "mime_type": mime_type,
                                        "size": len(image_bytes)
                                    }
            
            # 检查是否有文本响应（错误或说明）
            text_response = ""
            if "candidates" in result and len(result["candidates"]) > 0:
                candidate = result["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    for part in candidate["content"]["parts"]:
                        if "text" in part:
                            text_response += part["text"]
            
            if text_response:
                logger.warning(f"⚠️ NanoBanana Pro 返回文本而非图片: {text_response[:200]}")
                return {
                    "success": False,
                    "error": f"API 返回文本而非图片: {text_response[:200]}"
                }
            
            logger.error(f"❌ NanoBanana Pro 响应中没有图片数据: {json.dumps(result, indent=2)[:500]}")
            return {
                "success": False,
                "error": "API 响应中没有图片数据"
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ NanoBanana Pro 请求失败: {e}")
            return {
                "success": False,
                "error": f"请求失败: {str(e)}"
            }
        except Exception as e:
            logger.error(f"❌ NanoBanana Pro 生成图片失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_config(self) -> bool:
        """验证配置是否完整"""
        return bool(self.api_key)


def test_generator():
    """测试生成器"""
    generator = NanoBananaProGenerator()
    
    if not generator.validate_config():
        print("❌ 未配置 API Key")
        return
    
    result = generator.generate_image(
        prompt="A cute sea otter floating on water, high quality, detailed",
        size="1K",
        save_path="test_nano.png",
        aspect_ratio="1:1"
    )
    
    print(f"结果: {json.dumps(result, indent=2, ensure_ascii=False)}")


if __name__ == "__main__":
    test_generator()
