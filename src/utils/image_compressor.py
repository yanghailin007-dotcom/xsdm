"""
图片压缩工具
用于压缩上传到 VeO API 的图片，避免 "message too large" 错误
"""
import base64
import io
from typing import Optional, Tuple
from PIL import Image
from src.utils.logger import get_logger

logger = get_logger(__name__)

# VeO API 图片大小策略
# 🔥 修改策略：≤6MB不压缩，>6MB才轻度压缩
MIN_IMAGE_SIZE_MB = 4  # 压缩后最小保持4MB
MAX_IMAGE_SIZE_MB = 6  # 只有超过6MB才压缩
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# 推荐的压缩质量
# 🔥 极高质量，几乎无损
DEFAULT_QUALITY = 98  # 极高质量（原95）
MIN_QUALITY = 95      # 最低也保持95（原80）

# 推荐的最大尺寸
# 🔥 不限制尺寸，保持原始分辨率
MAX_DIMENSION = 4096  # 4K分辨率（原2560）


def compress_image(
    image_data: str,
    max_size_mb: float = MAX_IMAGE_SIZE_MB,
    quality: int = DEFAULT_QUALITY,
    max_dimension: int = MAX_DIMENSION,
    output_format: str = 'JPEG'  # 🔥 修改：默认使用 JPEG 格式（兼容性更好）
) -> str:
    """
    压缩 base64 编码的图片
    
    Args:
        image_data: base64 编码的图片数据（可以是纯 base64 或 data URL 格式）
        max_size_mb: 最大允许大小（MB）
        quality: JPEG 压缩质量 (1-100)，仅在 output_format='JPEG' 时有效
        max_dimension: 最大边长（像素）
        output_format: 输出格式 ('PNG' 或 'JPEG')，默认 JPEG（兼容性更好）
    
    Returns:
        压缩后的 base64 编码图片数据（data URL 格式：data:image/xxx;base64,xxx）
    """
    try:
        # 解码 base64
        if ',' in image_data:
            # 移除 data URL 前缀（如果有）
            image_data = image_data.split(',', 1)[1]

        # 🔥 修复 Base64 填充问题
        # Base64 字符串长度必须是 4 的倍数，不足的用 = 填充
        missing_padding = len(image_data) % 4
        if missing_padding:
            image_data += '=' * (4 - missing_padding)

        image_bytes = base64.b64decode(image_data)
        
        # 检查原始大小
        original_size = len(image_bytes)
        original_size_mb = original_size / (1024 * 1024)

        logger.info(f"📸 原始图片大小: {original_size_mb:.2f} MB, 输出格式: {output_format}")

        # 🔥 新策略：≤6MB不压缩，>6MB才轻度压缩
        if original_size <= MAX_IMAGE_SIZE_MB * 1024 * 1024:
            logger.info(f"✅ 图片大小 {original_size_mb:.2f} MB <= {MAX_IMAGE_SIZE_MB} MB，无需压缩")
            # 🔥 返回带格式前缀的 data URL
            return f"data:image/{output_format.lower()};base64,{image_data}"
        
        # 打开图片
        img = Image.open(io.BytesIO(image_bytes))
        
        # 转换为 RGB（如果是 RGBA）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 调整尺寸（如果需要）
        width, height = img.size
        if max(width, height) > max_dimension:
            logger.info(f"🔄 调整图片尺寸: {width}x{height} -> ")
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"{new_width}x{new_height}")
        
        # 🔥 修改：默认使用 JPEG 格式（兼容性更好）
        if output_format.upper() == 'JPEG':
            # JPEG 格式：轻度压缩，保持高质量和大文件
            current_quality = quality
            output_buffer = io.BytesIO()

            # 🔥 新策略：目标是保持 >= 4MB，只做轻度压缩
            # 对于 >6MB 的图片，压缩到 4-6MB 范围
            target_min_size = MIN_IMAGE_SIZE_MB * 1024 * 1024  # 4MB
            target_max_size = MAX_IMAGE_SIZE_MB * 1024 * 1024  # 6MB

            while current_quality >= MIN_QUALITY:
                output_buffer.seek(0)
                output_buffer.truncate()

                # 保存为 JPEG
                img.save(output_buffer, format='JPEG', quality=current_quality, optimize=True)

                compressed_size = output_buffer.tell()
                compressed_size_mb = compressed_size / (1024 * 1024)

                logger.info(f"🔄 质量 {current_quality}: {compressed_size_mb:.2f} MB")

                # 🔥 新逻辑：如果压缩后在 4-6MB 范围内，就接受
                if target_min_size <= compressed_size <= target_max_size:
                    # 压缩成功，保持在理想范围
                    compressed_data = output_buffer.getvalue()
                    base64_data = base64.b64encode(compressed_data).decode('utf-8')

                    compression_ratio = (1 - compressed_size / original_size) * 100
                    logger.info(f"✅ 压缩成功 (JPEG): {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB "
                              f"({compression_ratio:.1f}% 减少)，保持高质量")

                    # 🔥 返回带格式前缀的 data URL
                    return f"data:image/jpeg;base64,{base64_data}"

                # 如果太小了，提高质量
                if compressed_size < target_min_size and current_quality < 100:
                    logger.info(f"⚠️  压缩后 {compressed_size_mb:.2f} MB < {MIN_IMAGE_SIZE_MB} MB，提高质量")
                    current_quality = min(100, current_quality + 1)
                    continue

                # 如果太大了，降低质量
                if compressed_size > target_max_size:
                    current_quality -= 1
                    continue

                # 其他情况，接受当前结果
                break

            # 使用当前质量的结果
            compressed_data = output_buffer.getvalue()
            base64_data = base64.b64encode(compressed_data).decode('utf-8')
            compressed_size_mb = len(compressed_data) / (1024 * 1024)
            logger.info(f"✅ 最终压缩 (JPEG质量{current_quality}): {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB")

            # 🔥 返回带格式前缀的 data URL
            return f"data:image/jpeg;base64,{base64_data}"
        else:
            # PNG 格式：直接保存（无法调整质量）
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='PNG', optimize=True)
            
            compressed_size = output_buffer.tell()
            compressed_size_mb = compressed_size / (1024 * 1024)
            
            # 检查是否满足大小要求
            if compressed_size <= max_size_mb * 1024 * 1024:
                compressed_data = output_buffer.getvalue()
                base64_data = base64.b64encode(compressed_data).decode('utf-8')
                
                compression_ratio = (1 - compressed_size / original_size) * 100
                logger.info(f"✅ 压缩成功 (PNG): {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB "
                          f"({compression_ratio:.1f}% 减少)")
                
                # 🔥 返回带格式前缀的 data URL
                return f"data:image/png;base64,{base64_data}"
            else:
                # PNG 太大，尝试降采样
                logger.warn(f"⚠️  PNG 格式仍然超过大小限制 ({compressed_size_mb:.2f} MB)，尝试降采样...")
                
                # 逐步降低分辨率
                scale_factors = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]
                for scale in scale_factors:
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    
                    output_buffer.seek(0)
                    output_buffer.truncate()
                    resized_img.save(output_buffer, format='PNG', optimize=True)
                    
                    compressed_size = output_buffer.tell()
                    compressed_size_mb = compressed_size / (1024 * 1024)
                    
                    logger.info(f"🔄 降采样 {scale*100:.0f}%: {new_width}x{new_height}, {compressed_size_mb:.2f} MB")
                    
                    if compressed_size <= max_size_mb * 1024 * 1024:
                        compressed_data = output_buffer.getvalue()
                        base64_data = base64.b64encode(compressed_data).decode('utf-8')
                        
                        compression_ratio = (1 - compressed_size / original_size) * 100
                        logger.info(f"✅ 压缩成功 (PNG降采样): {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB "
                                  f"({compression_ratio:.1f}% 减少)")
                        
                        # 🔥 返回带格式前缀的 data URL
                        return f"data:image/png;base64,{base64_data}"
                
                # 最后尝试：使用 JPEG 格式
                logger.warn(f"⚠️  PNG 降采样后仍然超过大小限制，改用 JPEG 格式")
                return compress_image(image_data, max_size_mb, quality, max_dimension, 'JPEG')
    
    except Exception as e:
        logger.error(f"❌ 图片压缩失败: {e}")
        # 返回原始数据（带格式前缀）
        if ',' not in image_data:
            # 如果原始数据没有格式前缀，添加默认的 JPEG 格式前缀
            return f"data:image/jpeg;base64,{image_data}"
        return image_data


def validate_and_compress_images(
    images: list,
    max_size_mb: float = MAX_IMAGE_SIZE_MB,
    quality: int = DEFAULT_QUALITY
) -> Tuple[list, dict]:
    """
    验证并压缩图片列表

    Args:
        images: base64 图片列表
        max_size_mb: 最大允许大小（MB）
        quality: JPEG 压缩质量

    Returns:
        (压缩后的图片列表, 压缩统计信息)
    """
    import re

    def is_valid_base64(s: str) -> bool:
        """检查字符串是否是有效的 base64 数据"""
        if not s or len(s) < 10:
            return False
        # Base64 只包含 A-Z, a-z, 0-9, +, /, = 字符
        # 移除可能的 data URL 前缀
        if ',' in s:
            s = s.split(',', 1)[1]
        pattern = r'^[A-Za-z0-9+/]*={0,2}$'
        return bool(re.match(pattern, s))

    compressed_images = []
    stats = {
        'total': len(images),
        'compressed': 0,
        'skipped': 0,
        'failed': 0,
        'total_original_size_mb': 0,
        'total_compressed_size_mb': 0
    }

    for i, img in enumerate(images):
        try:
            if not img or not isinstance(img, str):
                logger.warn(f"⚠️  图片 {i} 数据无效，跳过")
                stats['failed'] += 1
                continue

            # 🔥 检查是否是有效的 base64 数据
            if not is_valid_base64(img):
                logger.warn(f"⚠️  图片 {i} 不是有效的 base64 数据，跳过. 预览: {img[:100]}...")
                stats['failed'] += 1
                continue

            # 计算原始大小
            if ',' in img:
                img_data = img.split(',', 1)[1]
            else:
                img_data = img

            # 🔥 修复填充问题
            missing_padding = len(img_data) % 4
            if missing_padding:
                img_data += '=' * (4 - missing_padding)

            original_bytes = len(base64.b64decode(img_data))
            stats['total_original_size_mb'] = stats.get('total_original_size_mb', 0.0) + original_bytes / (1024 * 1024)

            # 压缩图片
            compressed = compress_image(img, max_size_mb, quality)
            compressed_images.append(compressed)

            # 计算压缩后大小
            if ',' in compressed:
                compressed_data = compressed.split(',', 1)[1]
            else:
                compressed_data = compressed
            missing_padding = len(compressed_data) % 4
            if missing_padding:
                compressed_data += '=' * (4 - missing_padding)
            compressed_bytes = len(base64.b64decode(compressed_data))
            stats['total_compressed_size_mb'] = stats.get('total_compressed_size_mb', 0.0) + compressed_bytes / (1024 * 1024)

            if compressed_bytes < original_bytes:
                stats['compressed'] += 1
            else:
                stats['skipped'] += 1
        
        except Exception as e:
            logger.error(f"❌ 处理图片 {i} 失败: {e}")
            stats['failed'] += 1
    
    # 计算总体压缩率
    if stats['total_original_size_mb'] > 0:
        stats['compression_ratio'] = (
            1 - stats['total_compressed_size_mb'] / stats['total_original_size_mb']
        ) * 100
    else:
        stats['compression_ratio'] = 0
    
    logger.info(f"📊 压缩统计:")
    logger.info(f"  总数: {stats['total']}")
    logger.info(f"  压缩: {stats['compressed']}")
    logger.info(f"  跳过: {stats['skipped']}")
    logger.info(f"  失败: {stats['failed']}")
    logger.info(f"  总大小: {stats['total_original_size_mb']:.2f} MB -> "
               f"{stats['total_compressed_size_mb']:.2f} MB")
    logger.info(f"  压缩率: {stats['compression_ratio']:.1f}%")
    
    return compressed_images, stats


if __name__ == "__main__":
    # 测试
    print("图片压缩工具测试")
    print(f"最大图片大小: {MAX_IMAGE_SIZE_MB} MB")
    print(f"默认质量: {DEFAULT_QUALITY}")
    print(f"最小质量: {MIN_QUALITY}")
    print(f"最大尺寸: {MAX_DIMENSION}x{MAX_DIMENSION}")