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

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger, Logger, LogLevel

# 🔥 配置日志系统：将所有可能的输出重定向到文件，避免控制台被base64数据填满
def _setup_global_logging():
    """在模块级别配置日志系统"""
    import logging as python_logging
    
    # 创建日志目录
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'nanobanana_detailed.log'
    
    # 创建Python标准日志的文件处理器
    file_handler = python_logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(python_logging.DEBUG)
    formatter = python_logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # 捕获所有可能打印base64数据的logger
    loggers_to_capture = [
        'requests', 'urllib3', 'requests.packages', 'requests.packages.urllib3',
        'urllib3.connectionpool', 'urllib3.util', 'urllib3.util.retry',
        'httpx', 'httpcore', 'http.client'
    ]
    
    for logger_name in loggers_to_capture:
        logger = python_logging.getLogger(logger_name)
        logger.setLevel(python_logging.DEBUG)
        # 清除所有现有的handlers
        logger.handlers.clear()
        # 只添加文件处理器
        logger.addHandler(file_handler)
        # 阻止传播到父logger（避免输出到控制台）
        logger.propagate = False
    
    # 同时启用我们的自定义日志系统的文件日志
    Logger.enable_file_logging(str(log_file))
    # 将控制台日志级别设置为INFO，只显示重要信息
    Logger.set_global_level(LogLevel.INFO)
    
    return log_file

# 在模块加载时配置日志
_log_file = _setup_global_logging()


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
        self.logger.info(f"📝 详细日志已启用，文件位置: {_log_file}")
        
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
        reference_image: Optional[str] = None,
        reference_images: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        生成图像
        
        Args:
            prompt: 提示词描述
            aspect_ratio: 图片比例 (16:9, 4:3, 1:1, 9:16)
            image_size: 图片尺寸 (1K, 2K, 4K)
            save_path: 保存路径，如果为None则自动生成
            retry_count: 当前重试次数
            reference_image: 参考图像路径（单张，兼容旧版本）
            reference_images: 参考图像路径列表（多张，最多5张，优先使用）
            
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
        
        # 🔥 新增：处理参考图像（支持多个参考图像，最多5张）
        # 🔥 集成图像压缩功能，避免请求体过大导致连接被服务器断开
        parts = []
        
        # 🔥 重要：先添加文本提示词，再添加参考图像（符合API规范）
        parts.append({
            "text": prompt
        })
        
        # 🔥 合并参考图像：优先使用 reference_images（数组），否则使用 reference_image（单张）
        all_reference_images = []
        if reference_images:
            # 新版本：使用多张参考图像
            all_reference_images = reference_images[:5]  # 最多5张
        elif reference_image:
            # 兼容旧版本：使用单张参考图像
            all_reference_images = [reference_image]
        
        # 添加所有参考图像到parts（先压缩）
        if all_reference_images:
            import mimetypes
            # 🔥 导入图像压缩工具
            try:
                from src.utils.image_compressor import compress_image, MAX_IMAGE_SIZE_BYTES
                # 限制单张参考图像最大1.5MB（比默认2MB更保守，避免多张图时超过限制）
                max_size_mb = 1.5
                self.logger.info(f"🗜️  参考图像压缩模式已启用，单张限制: {max_size_mb} MB")
            except ImportError:
                compress_image = None
                max_size_mb = None
                self.logger.warn("⚠️  图像压缩工具未找到，将使用原始图像")
            
            for idx, ref_path in enumerate(all_reference_images):
                try:
                    # 读取并编码参考图像
                    if not os.path.exists(ref_path):
                        self.logger.warn(f"⚠️ 参考图像{idx+1}不存在: {ref_path}")
                        continue
                    
                    with open(ref_path, 'rb') as f:
                        ref_image_data = f.read()
                    
                    original_size = len(ref_image_data)
                    self.logger.debug(f"📸 参考图{idx+1}原始大小: {original_size / (1024*1024):.2f} MB")
                    
                    # 🔥 如果压缩工具可用，先压缩图像
                    if compress_image and max_size_mb:
                        try:
                            # 将图像数据转换为base64 data URL格式
                            raw_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                            data_url = f"data:image/jpeg;base64,{raw_base64}"
                            
                            # 压缩图像
                            compressed_data_url = compress_image(
                                data_url,
                                max_size_mb=max_size_mb,
                                quality=85,
                                max_dimension=1280  # 限制最大尺寸为1280px
                            )
                            
                            # 提取压缩后的base64数据
                            if ',' in compressed_data_url:
                                compressed_base64 = compressed_data_url.split(',', 1)[1]
                            else:
                                compressed_base64 = compressed_data_url
                            
                            ref_image_base64 = compressed_base64
                            compressed_size = len(base64.b64decode(compressed_base64))
                            compression_ratio = (1 - compressed_size / original_size) * 100
                            self.logger.info(f"🗜️  参考图{idx+1}压缩: {original_size / (1024*1024):.2f} MB -> "
                                           f"{compressed_size / (1024*1024):.2f} MB (压缩率: {compression_ratio:.1f}%)")
                        except Exception as compress_error:
                            self.logger.warn(f"⚠️  参考图{idx+1}压缩失败，使用原始数据: {compress_error}")
                            ref_image_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                    else:
                        # 不压缩，直接使用原始数据
                        ref_image_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                    
                    # 获取MIME类型
                    mime_type = mimetypes.guess_type(ref_path)[0] or 'image/jpeg'
                    
                    parts.append({
                        "inline_data": {  # 使用下划线格式，符合API规范
                            "mime_type": mime_type,  # 使用下划线格式
                            "data": ref_image_base64
                        }
                    })
                    self.logger.debug(f"✅ 已添加参考图像{idx+1}: {ref_path}")
                except Exception as e:
                    self.logger.debug(f"⚠️ 添加参考图像{idx+1}失败: {e}")
            
            self.logger.info(f"🖼️ 共添加 {len([p for p in parts if 'inline_data' in p])} 张参考图像（已压缩）")
        
        # 构建请求体（移除role字段，使用简化的contents结构）
        request_body = {
            "contents": [
                {
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
            self.logger.info(f"📋 请求配置:")
            self.logger.info(f"  - API URL: {self.base_url}")
            self.logger.info(f"  - 比例: {aspect_ratio}")
            self.logger.info(f"  - 尺寸: {image_size}")
            self.logger.info(f"  - 超时: {self.timeout}秒")
            self.logger.info(f"  - 提示词长度: {len(prompt)} 字符")
            self.logger.info(f"  - 提示词内容: {prompt}")  # 显示完整提示词
            
            # 🔥 显示参考图像信息
            if all_reference_images:
                self.logger.info(f"  - 参考图像数量: {len(all_reference_images)} 张")
                for idx, ref_path in enumerate(all_reference_images):
                    self.logger.info(f"    参考图{idx+1}: {ref_path}")
            
            # 发送请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"  # 使用完整的 API key
            }
            
            self.logger.info(f"🚀 发送POST请求到API...")
            
            # 计算请求体大小（不打印完整内容以避免显示base64数据）
            request_body_size = len(json.dumps(request_body))
            self.logger.debug(f"请求体大小: {request_body_size} 字节")
            
            # 🔥 如果有参考图像，单独记录
            if all_reference_images:
                self.logger.debug(f"  - 包含 {len(all_reference_images)} 张参考图像")
            self.logger.debug(f"Authorization Header: Bearer {self.api_key[:20]}...{self.api_key[-4:]}")  # 日志中只显示部分
            
            response = requests.post(
                self.base_url,
                json=request_body,  # 使用 json 参数，requests 会自动序列化并设置 Content-Type
                headers=headers,
                timeout=self.timeout
            )
            
            self.logger.info(f"📥 收到API响应:")
            self.logger.info(f"  - 状态码: {response.status_code}")
            self.logger.info(f"  - 响应大小: {len(response.content)} 字节")
            
            # 打印响应内容的预览（非base64部分）
            try:
                response_preview = response.text[:500] if response.text else "空响应"
                self.logger.info(f"  - 响应预览: {response_preview}...")
            except:
                pass
            
            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败 (状态码: {response.status_code})"
                self.logger.error(f"{error_msg}\n响应: {response.text[:500]}")
                
                # 如果是可重试的错误，尝试重试
                if retry_count < self.max_retries and response.status_code >= 500:
                    self.logger.info(f"尝试重试 ({retry_count + 1}/{self.max_retries})...")
                    return self.generate_image(prompt, aspect_ratio, image_size, save_path, retry_count + 1, reference_image, reference_images)
                
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
            
            self.logger.info(f"📋 解析响应数据...")
            self.logger.info(f"  - 响应顶层键: {list(response_data.keys())}")
            
            if 'candidates' in response_data:
                self.logger.info(f"  - 候选数量: {len(response_data['candidates'])}")
                if response_data['candidates']:
                    first_candidate = response_data['candidates'][0]
                    self.logger.info(f"  - 首个候选键: {list(first_candidate.keys())}")
            elif 'base64Image' in response_data:
                self.logger.info(f"  - 包含 base64Image 字段，数据长度: {len(response_data['base64Image'])} 字符")
            elif 'image' in response_data:
                self.logger.info(f"  - 包含 image 字段，数据长度: {len(response_data['image'])} 字符")
            elif 'data' in response_data:
                self.logger.info(f"  - 包含 data 字段，数据长度: {len(response_data['data'])} 字符")
            
            # 🔥 支持多种响应格式
            image_data = None
            text_response = None
            
            # 格式1: 标准 Gemini API 格式
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                self.logger.debug(f"📋 候选响应结构")
                
                if 'content' in candidate and 'parts' in candidate['content']:
                    parts_count = len(candidate['content']['parts'])
                    self.logger.info(f"  - Parts数量: {parts_count}")
                    
                    for idx, part in enumerate(candidate['content']['parts']):
                        part_keys = list(part.keys())
                        self.logger.info(f"  - Part {idx} 键: {part_keys}")
                        
                        # 兼容 inlineData 和 inline_data 两种格式
                        if 'inlineData' in part:
                            image_data = part['inlineData'].get('data')
                            self.logger.info(f"✅ 从 inlineData 提取到图像数据 (长度: {len(image_data) if image_data else 0})")
                        elif 'inline_data' in part:
                            image_data = part['inline_data'].get('data')
                            self.logger.info(f"✅ 从 inline_data 提取到图像数据 (长度: {len(image_data) if image_data else 0})")
                        elif 'text' in part:
                            text_response = part['text']
                            self.logger.info(f"📝 提取到文本响应: {text_response[:100]}...")
            
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
            
            self.logger.info(f"✅ 图像生成成功!")
            self.logger.info(f"  - 保存路径: {save_path}")
            self.logger.info(f"  - 文件大小: {len(image_bytes)} 字节")
            if text_response:
                self.logger.info(f"  - 文本响应: {text_response[:100]}...")
            
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
                return self.generate_image(prompt, aspect_ratio, image_size, save_path, retry_count + 1, reference_image, reference_images)
            
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