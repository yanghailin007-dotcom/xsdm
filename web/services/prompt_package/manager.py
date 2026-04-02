"""
提示词包管理器
"""

import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .models import PromptPackage


class PromptPackageManager:
    """提示词包管理器"""
    
    def __init__(self, base_path: str = "prompt_packages"):
        """
        初始化管理器
        
        Args:
            base_path: 提示词包基础目录
        """
        self.base_path = Path(base_path)
        self.default_packages_path = self.base_path / "default"
        self.user_packages_path = self.base_path / "user_custom"
        
        # 确保目录存在
        self.default_packages_path.mkdir(parents=True, exist_ok=True)
        self.user_packages_path.mkdir(parents=True, exist_ok=True)
        
        # 初始化默认提示词包
        self._init_default_packages()
    
    def _init_default_packages(self):
        """初始化默认提示词包（如果不存在则创建）"""
        try:
            # 检查 market_driven 默认包是否存在
            market_driven_path = self.default_packages_path / "market_driven"
            if market_driven_path.exists() and (market_driven_path / "package_info.json").exists():
                return  # 已存在，跳过
            
            logger.info("[PromptPackageManager] 初始化默认提示词包...")
            
            # 创建目录结构
            market_driven_path.mkdir(parents=True, exist_ok=True)
            
            # 复制 JSON 文件
            import shutil
            template_dir = Path(__file__).parent.parent.parent.parent / "prompt_packages" / "default" / "market_driven"
            
            if template_dir.exists():
                for json_file in template_dir.glob("*.json"):
                    shutil.copy2(json_file, market_driven_path / json_file.name)
                logger.info("[PromptPackageManager] 默认提示词包初始化完成")
            else:
                logger.warning(f"[PromptPackageManager] 模板目录不存在: {template_dir}")
                
        except Exception as e:
            logger.error(f"[PromptPackageManager] 初始化默认包失败: {e}")
    
    def list_packages(self, user_id: Optional[str] = None, mode: Optional[str] = None) -> List[Dict]:
        """
        列出所有可用的提示词包
        
        Args:
            user_id: 用户ID（如果提供，包括用户的自定义包）
            mode: 过滤特定模式
            
        Returns:
            提示词包信息列表
        """
        packages = []
        
        # 1. 加载默认包（系统预设，只读）
        if self.default_packages_path.exists():
            for package_dir in self.default_packages_path.iterdir():
                if package_dir.is_dir():
                    try:
                        pkg = PromptPackage(package_dir)
                        if mode is None or pkg.mode == mode:
                            packages.append({
                                "id": pkg.id,
                                "name": pkg.name,
                                "description": pkg.description,
                                "mode": pkg.mode,
                                "version": pkg.info.get("version", "1.0.0"),
                                "is_default": True,
                                "is_editable": False,
                                "type": "default",
                                "total_steps": len(pkg.steps),
                                "tags": pkg.info.get("tags", [])
                            })
                    except Exception as e:
                        print(f"加载默认包失败 {package_dir}: {e}")
        
        # 2. 加载用户自定义包
        if user_id:
            user_path = self.user_packages_path / str(user_id)
            if user_path.exists():
                for package_dir in user_path.iterdir():
                    if package_dir.is_dir():
                        try:
                            pkg = PromptPackage(package_dir)
                            if mode is None or pkg.mode == mode:
                                packages.append({
                                    "id": pkg.id,
                                    "name": pkg.name,
                                    "description": pkg.description,
                                    "mode": pkg.mode,
                                    "version": pkg.info.get("version", "1.0.0"),
                                    "is_default": False,
                                    "is_editable": True,
                                    "type": "user",
                                    "user_id": user_id,
                                    "total_steps": len(pkg.steps),
                                    "tags": pkg.info.get("tags", [])
                                })
                        except Exception as e:
                            print(f"加载用户包失败 {package_dir}: {e}")
        
        return packages
    
    def get_package(self, package_id: str, user_id: Optional[str] = None,
                    allow_shared: bool = False) -> Optional[PromptPackage]:
        """
        获取提示词包
        
        Args:
            package_id: 包ID
            user_id: 用户ID（如果是用户自定义包）
            allow_shared: 是否允许访问其他用户的共享包（默认False）
            
        Returns:
            提示词包对象，如果不存在则返回None
        """
        # 1. 先查找默认包（系统预设，所有用户可访问）
        default_path = self.default_packages_path / package_id
        if default_path.exists():
            return PromptPackage(default_path)
        
        # 2. 查找当前用户的包（严格用户隔离）
        if user_id:
            user_path = self.user_packages_path / str(user_id) / package_id
            if user_path.exists():
                return PromptPackage(user_path)
        
        # 3. 查找共享包（仅当显式允许时，且包必须标记为共享）
        if allow_shared and user_id:
            for user_dir in self.user_packages_path.iterdir():
                if not user_dir.is_dir():
                    continue
                # 跳过当前用户自己的目录（已检查过）
                if user_dir.name == str(user_id):
                    continue
                package_path = user_dir / package_id
                if package_path.exists():
                    try:
                        pkg = PromptPackage(package_path)
                        # 只返回显式标记为共享的包
                        if pkg.info.get('is_shared', False):
                            return pkg
                    except Exception:
                        continue
        
        return None
    
    def create_package(self, user_id: str, name: str, base_package_id: Optional[str] = None,
                       mode: str = "market_driven", description: str = "") -> PromptPackage:
        """
        创建新的提示词包
        
        Args:
            user_id: 用户ID
            name: 包名称
            base_package_id: 基于的默认包ID（如果提供则复制）
            mode: 生成模式
            description: 描述
            
        Returns:
            新创建的提示词包
        """
        # 生成包ID
        package_id = f"{mode}_{user_id}_{int(datetime.now().timestamp())}"
        
        # 创建目录
        user_path = self.user_packages_path / str(user_id)
        user_path.mkdir(parents=True, exist_ok=True)
        package_path = user_path / package_id
        package_path.mkdir(parents=True, exist_ok=True)
        
        if base_package_id:
            # 复制基础包
            base_package = self.get_package(base_package_id)
            if base_package:
                # 复制所有文件
                for file_path in base_package.package_path.iterdir():
                    if file_path.is_file():
                        shutil.copy2(file_path, package_path / file_path.name)
                
                # 加载并修改信息
                pkg = PromptPackage(package_path)
                pkg.info["id"] = package_id
                pkg.info["name"] = name
                pkg.info["description"] = description
                pkg.info["is_default"] = False
                pkg.info["is_editable"] = True
                pkg.info["created_at"] = datetime.now().isoformat()
                pkg.info["updated_at"] = datetime.now().isoformat()
                pkg.info["author"] = user_id
                pkg.save()
                return pkg
        
        # 创建空包
        info = {
            "id": package_id,
            "name": name,
            "description": description,
            "version": "1.0.0",
            "author": user_id,
            "mode": mode,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "tags": [],
            "is_default": False,
            "is_editable": True,
            "total_steps": 0,
            "supported_features": []
        }
        
        with open(package_path / "package_info.json", 'w', encoding='utf-8') as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        
        return PromptPackage(package_path)
    
    def delete_package(self, package_id: str, user_id: str) -> bool:
        """
        删除用户自定义提示词包
        
        Args:
            package_id: 包ID
            user_id: 用户ID
            
        Returns:
            是否成功删除
        """
        package = self.get_package(package_id, user_id)
        if not package:
            return False
        
        if package.is_default:
            return False  # 不能删除默认包
        
        # 删除目录
        shutil.rmtree(package.package_path)
        return True
    
    def duplicate_package(self, package_id: str, user_id: str, new_name: Optional[str] = None) -> Optional[PromptPackage]:
        """
        复制提示词包
        
        Args:
            package_id: 源包ID
            user_id: 目标用户ID
            new_name: 新名称（可选）
            
        Returns:
            新创建的提示词包
        """
        source_package = self.get_package(package_id)
        if not source_package:
            return None
        
        name = new_name or f"{source_package.name} - 副本"
        
        return self.create_package(
            user_id=user_id,
            name=name,
            base_package_id=package_id if source_package.is_default else None,
            mode=source_package.mode,
            description=source_package.description
        )
    
    def export_package(self, package_id: str, user_id: Optional[str] = None) -> bytes:
        """
        导出提示词包为ZIP
        
        Args:
            package_id: 包ID
            user_id: 用户ID
            
        Returns:
            ZIP文件字节
        """
        import io
        import zipfile
        
        package = self.get_package(package_id, user_id)
        if not package:
            raise ValueError(f"包不存在: {package_id}")
        
        # 创建内存中的ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in package.package_path.iterdir():
                if file_path.is_file():
                    zf.write(file_path, file_path.name)
        
        buffer.seek(0)
        return buffer.read()
    
    def import_package(self, user_id: str, zip_data: bytes, package_name: Optional[str] = None) -> PromptPackage:
        """
        导入提示词包
        
        Args:
            user_id: 用户ID
            zip_data: ZIP文件字节
            package_name: 包名称（可选，覆盖原名称）
            
        Returns:
            导入的提示词包
        """
        import io
        import zipfile
        
        # 创建临时目录解压
        buffer = io.BytesIO(zip_data)
        
        # 读取包信息
        with zipfile.ZipFile(buffer, 'r') as zf:
            # 读取 package_info.json
            info_data = zf.read("package_info.json")
            info = json.loads(info_data.decode('utf-8'))
            
            # 生成新ID
            original_id = info.get("id", "unknown")
            package_id = f"imported_{user_id}_{int(datetime.now().timestamp())}"
            
            # 创建目录
            user_path = self.user_packages_path / str(user_id)
            user_path.mkdir(parents=True, exist_ok=True)
            package_path = user_path / package_id
            package_path.mkdir(parents=True, exist_ok=True)
            
            # 解压所有文件
            zf.extractall(package_path)
            
            # 更新信息
            info["id"] = package_id
            info["name"] = package_name or info.get("name", "导入的包")
            info["is_default"] = False
            info["is_editable"] = True
            info["author"] = user_id
            info["imported_from"] = original_id
            info["imported_at"] = datetime.now().isoformat()
            
            with open(package_path / "package_info.json", 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        
        return PromptPackage(package_path)
    
    def get_package_for_generation(self, user_id: str, mode: str, 
                                   package_id: Optional[str] = None) -> PromptPackage:
        """
        获取用于生成的提示词包
        
        Args:
            user_id: 用户ID
            mode: 生成模式
            package_id: 指定的包ID（可选，默认使用系统默认包）
            
        Returns:
            提示词包对象
        """
        if package_id:
            package = self.get_package(package_id, user_id)
            if package:
                return package
        
        # 使用默认包
        default_packages = self.list_packages(mode=mode)
        for pkg_info in default_packages:
            if pkg_info.get("is_default"):
                return self.get_package(pkg_info["id"])
        
        # 如果没有默认包，返回第一个可用的
        if default_packages:
            return self.get_package(default_packages[0]["id"])
        
        raise ValueError(f"找不到可用的提示词包，模式: {mode}")
