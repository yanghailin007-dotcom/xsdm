"""
Nano Banana文生图API客户端
支持文本生成图像功能，用于角色生成
"""
import os
import sys
import requests
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

# 🔥 在模块级别禁用requests和urllib3的调试日志，避免打印请求体中的base64数据
import logging
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger


class NanoBananaImageGenerator:
    """Nano Banana文生图API客户端（用于角色生成）"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化Nano Banana文生图客户端
        
        Args:
            api_key: API密钥，如果为None则从配置获取
            base_url: API基础URL，如果为None则从配置获取
        """
        self.logger = get_logger("NanoBananaImageGenerator")
        
        # 从配置导入或使用传入的参数
        try:
            from config.config import CONFIG
            config = CONFIG.get('nanobanana', {})
            
            self.base_url = base_url or config.get('base_url', 'https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent')
            self.api_key = api_key or config.get('api_key', '')
            # 🔥 增加默认超时时间，特别是处理包含参考图像的请求
            default_timeout = config.get('timeout', 60)
            self.timeout_without_ref = default_timeout  # 无参考图像时的超时
            self.timeout_with_ref = max(default_timeout * 3, 300)  # 有参考图像时超时3倍或至少300秒
            self.timeout = default_timeout
            self.max_retries = config.get('max_retries', 3)
            self.enabled = config.get('enabled', True)
            
            self.default_config = config.get('default_config', {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": "16:9",
                    "imageSize": "4K"
                }
            })
            
        except ImportError:
            # 如果配置导入失败，使用默认值（不从环境变量读取）
            self.base_url = base_url or 'https://newapi.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent'
            self.api_key = api_key or ''  # 不再从环境变量读取
            self.timeout = 60
            self.max_retries = 3
            self.enabled = True
            self.default_config = {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": "16:9",
                    "imageSize": "4K"
                }
            }
        
        # 验证API密钥
        if not self.api_key:
            self.logger.warn("⚠️ 未配置Nano Banana API密钥，请在config/config.py中配置nanobanana.api_key")
        else:
            # API密钥已配置，无需打印详细信息
            pass
        
        # 确保输出目录存在
        self.output_dir = BASE_DIR / 'generated_images'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"✅ Nano Banana客户端初始化完成 (enabled={self.enabled})")
    
    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        image_size: str = "4K",
        save_path: Optional[str] = None,
        retry_count: int = 0,
        reference_image: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成图像
        
        Args:
            prompt: 提示词描述
            aspect_ratio: 图片比例 (16:9, 4:3, 1:1, 9:16)
            image_size: 图片尺寸 (1K, 2K, 4K)
            save_path: 保存路径，如果为None则自动生成
            retry_count: 当前重试次数
            reference_image: 参考图像路径（支持图像转图像生成）
            
        Returns:
            dict: 包含生成结果的字典
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Nano Banana服务未启用"
            }
        
        if not self.api_key:
            return {
                "success": False,
                "error": "未配置API密钥，请在config/config.py中配置nanobanana.api_key"
            }
        
        # 🔥 新增：处理参考图像
        parts = []
        
        # 如果有参考图像，先添加图像
        if reference_image:
            try:
                # 读取并编码参考图像
                if not os.path.exists(reference_image):
                    self.logger.warn(f"⚠️ 参考图像不存在: {reference_image}")
                else:
                    with open(reference_image, 'rb') as f:
                        ref_image_data = f.read()
                    
                    # 获取MIME类型
                    import mimetypes
                    mime_type = mimetypes.guess_type(reference_image)[0] or 'image/jpeg'
                    
                    # 编码为base64
                    ref_image_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                    
                    parts.append({
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": ref_image_base64
                        }
                    })
                    # 🔥 不打印参考图像的base64数据
                    self.logger.debug(f"✅ 已添加参考图像: {reference_image} ({len(ref_image_data)} bytes, base64编码后长度: {len(ref_image_base64)} 字符)")
            except Exception as e:
                self.logger.debug(f"⚠️ 添加参考图像失败: {e}，继续使用纯文本模式")
        
        # 添加文本提示词
        parts.append({
            "text": prompt
        })
        
        # 构建请求体
        request_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size
                }
            }
        }
        
        try:
            self.logger.info(f"🎨 开始生成图像")
            self.logger.debug(f"📋 请求配置:")
            self.logger.debug(f"  - API URL: {self.base_url}")
            self.logger.debug(f"  - 比例: {aspect_ratio}")
            self.logger.debug(f"  - 尺寸: {image_size}")
            self.logger.debug(f"  - 超时: {self.timeout}秒")
            self.logger.debug(f"  - 提示词长度: {len(prompt)} 字符")
            self.logger.debug(f"  - 提示词预览: {prompt[:100]}...")  # 只显示前100字符
            
            # 发送请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"  # 使用完整的 API key
            }
            
            self.logger.debug(f"🚀 发送POST请求到API...")
            
            # 计算请求体大小（不打印完整内容以避免显示base64数据）
            request_body_size = len(json.dumps(request_body))
            self.logger.debug(f"请求体大小: {request_body_size} 字节")
            
            # 如果有参考图像，单独记录
            if reference_image:
                self.logger.debug(f"  - 包含参考图像: {reference_image}")
            self.logger.debug(f"Authorization Header: Bearer {self.api_key[:20]}...{self.api_key[-4:]}")  # 日志中只显示部分
            
            response = requests.post(
                self.base_url,
                json=request_body,  # 使用 json 参数，requests 会自动序列化并设置 Content-Type
                headers=headers,
                timeout=self.timeout
            )
            
            self.logger.debug(f"📥 收到API响应:")
            self.logger.debug(f"  - 状态码: {response.status_code}")
            self.logger.debug(f"  - 响应大小: {len(response.content)} 字节")
            self.logger.debug(f"  - 响应头: {dict(response.headers)}")
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败 (状态码: {response.status_code})"
                self.logger.error(f"{error_msg}\n响应: {response.text[:500]}")
                
                # 如果是可重试的错误，尝试重试
                if retry_count < self.max_retries and response.status_code >= 500:
                    self.logger.info(f"尝试重试 ({retry_count + 1}/{self.max_retries})...")
                    return self.generate_image(prompt, aspect_ratio, image_size, save_path, retry_count + 1)
                
                return {
                    "success": False,
                    "error": error_msg,
                    "details": response.text
                }
            
            # 解析响应
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ JSON解析失败: {e}")
                self.logger.debug(f"响应内容前500字符: {response.text[:500]}")
                return {
                    "success": False,
                    "error": f"响应JSON解析失败: {str(e)}",
                    "response_text": response.text[:500]
                }
            
            # 🔥 不打印完整响应数据，避免打印超长Base64字符串
            self.logger.debug(f"📋 响应数据顶层键: {list(response_data.keys())}")
            if 'candidates' in response_data:
                self.logger.debug(f"📋 候选数量: {len(response_data['candidates'])}")
            elif 'base64Image' in response_data:
                self.logger.debug(f"📋 包含 base64Image 字段，数据长度: {len(response_data['base64Image'])} 字符")
            elif 'image' in response_data:
                self.logger.debug(f"📋 包含 image 字段，数据长度: {len(response_data['image'])} 字符")
            elif 'data' in response_data:
                self.logger.debug(f"📋 包含 data 字段，数据长度: {len(response_data['data'])} 字符")
            
            # 🔥 支持多种响应格式
            image_data = None
            text_response = None
            
            # 格式1: 标准 Gemini API 格式
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                self.logger.debug(f"📋 候选响应结构")
                
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'inlineData' in part:
                            image_data = part['inlineData'].get('data')
                            self.logger.debug(f"✅ 从 inlineData 提取到图像数据")
                        elif 'text' in part:
                            text_response = part['text']
                            self.logger.debug(f"📝 提取到文本响应")
            
            # 格式2: 直接包含 base64Image 字段
            elif 'base64Image' in response_data:
                image_data = response_data['base64Image']
                self.logger.debug(f"✅ 从 base64Image 字段提取到图像数据")
            
            # 格式3: 包含在 image 字段中
            elif 'image' in response_data:
                image_data = response_data['image']
                self.logger.debug(f"✅ 从 image 字段提取到图像数据")
            
            # 格式4: 包含在 data 字段中
            elif 'data' in response_data:
                image_data = response_data['data']
                self.logger.debug(f"✅ 从 data 字段提取到图像数据")
            
            # 如果仍然没有找到图像数据，尝试从任何可能的字段中提取
            if not image_data:
                self.logger.debug(f"响应顶层键: {list(response_data.keys())}")
                
                # 递归搜索包含base64数据的字段
                def find_base64_in_dict(obj, depth=0):
                    if depth > 10:  # 防止无限递归
                        return None
                    
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            # 检查键名可能包含图像数据的字段
                            if any(keyword in key.lower() for keyword in ['image', 'photo', 'picture', 'base64', 'data', 'binary']):
                                if isinstance(value, str) and len(value) > 100:  # base64数据通常较长
                                    # 尝试解码验证是否为有效的base64
                                    try:
                                        base64.b64decode(value)
                                        self.logger.debug(f"✅ 从字段 '{key}' 找到可能的base64图像数据")
                                        return value
                                    except:
                                        pass
                            # 递归搜索
                            result = find_base64_in_dict(value, depth + 1)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_base64_in_dict(item, depth + 1)
                            if result:
                                return result
                    return None
                
                image_data = find_base64_in_dict(response_data)
            
            if not image_data:
                return {
                    "success": False,
                    "error": "未能从响应中提取图像数据",
                    "response_structure": list(response_data.keys()),
                    "text_response": text_response
                }
            
            # 解码base64图像数据
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"图像数据解码失败: {str(e)}"
                }
            
            # 生成保存路径
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_name = "".join(x for x in prompt[:30] if x.isalnum() or x in (' ', '-', '_')).strip()
                clean_name = clean_name.replace(' ', '_')
                filename = f"nanobanana_{timestamp}_{clean_name}.png"
                save_path = str(self.output_dir / filename)
            
            # 保存图像
            with open(save_path, 'wb') as f:
                f.write(image_bytes)
            
            self.logger.info(f"✅ 图像生成成功")
            
            # 返回结果
            return {
                "success": True,
                "local_path": save_path,
                "url": f"/generated_images/{os.path.basename(save_path)}",
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "text_response": text_response,
                "file_size": len(image_bytes)
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"请求超时 (超过{self.timeout}秒)"
            self.logger.error(error_msg)
            
            if retry_count < self.max_retries:
                self.logger.info(f"尝试重试 ({retry_count + 1}/{self.max_retries})...")
                return self.generate_image(prompt, aspect_ratio, image_size, save_path, retry_count + 1)
            
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"生成图像时发生错误: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def batch_generate(
        self,
        prompts: List[str],
        aspect_ratio: str = "16:9",
        image_size: str = "4K",
        delay: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        批量生成图像
        
        Args:
            prompts: 提示词列表
            aspect_ratio: 图片比例
            image_size: 图片尺寸
            delay: 请求间隔(秒)
            
        Returns:
            list: 生成结果列表
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            self.logger.info(f"正在生成第 {i+1}/{len(prompts)} 张图像...")
            
            try:
                result = self.generate_image(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
                result['index'] = i + 1
                result['prompt'] = prompt
                results.append(result)
                
                # 避免频繁调用，添加延迟
                if delay > 0 and i < len(prompts) - 1:
                    import time
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"生成第 {i+1} 张图像时出错: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "index": i + 1,
                    "prompt": prompt
                })
        
        success_count = len([r for r in results if r.get('success')])
        self.logger.info(f"🎉 批量生成完成: {success_count}/{len(prompts)} 成功")
        
        return results
    
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        return self.enabled and bool(self.api_key)


def main():
    """测试函数"""
    try:
        # 初始化生成器
        generator = NanoBananaImageGenerator()
        
        if not generator.is_available():
            print("❌ Nano Banana服务不可用，请检查配置")
            return
        
        # 测试提示词
        test_prompt = "a cute cat sitting on a red cushion, cartoon style, vibrant colors"
        
        print("🎨 开始测试生成图像...")
        result = generator.generate_image(
            prompt=test_prompt,
            aspect_ratio="16:9",
            image_size="2K"
        )
        
        if result["success"]:
            print(f"✅ 测试成功!")
            print(f"   图像路径: {result['local_path']}")
            print(f"   访问URL: {result['url']}")
            if result.get('text_response'):
                print(f"   文本响应: {result['text_response']}")
        else:
            print(f"❌ 测试失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()