"""
NovelCraft 用户模型配置管理器
按用户隔离的自定义模型配置存储
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

# 存储路径
NOVELCRAFT_MODELS_FILE = Path("data/novelcraft_user_models.json")


class NovelCraftModelManager:
    """NovelCraft 用户模型管理器"""
    
    def __init__(self):
        self._ensure_data_dir()
        self._data = self._load_data()
    
    def _ensure_data_dir(self):
        """确保数据目录存在"""
        NOVELCRAFT_MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self) -> Dict[str, Any]:
        """加载数据"""
        if NOVELCRAFT_MODELS_FILE.exists():
            try:
                with open(NOVELCRAFT_MODELS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[NovelCraftModelManager] 加载失败: {e}")
                return {"users": {}}
        return {"users": {}}
    
    def _save_data(self):
        """保存数据"""
        try:
            with open(NOVELCRAFT_MODELS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"[NovelCraftModelManager] 保存失败: {e}")
            return False
    
    def _get_user_models(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的所有模型配置"""
        return self._data.get("users", {}).get(str(user_id), {}).get("models", [])
    
    def list_models(self, user_id: str) -> List[Dict[str, Any]]:
        """列出用户的自定义模型"""
        models = self._get_user_models(user_id)
        result = []
        for m in models:
            item = dict(m)
            api_key = item.get("api_key", "")
            if len(api_key) > 10:
                item["api_key"] = api_key[:6] + "***" + api_key[-4:]
            else:
                item["api_key"] = "***"
            result.append(item)
        return result
    
    def get_model(self, user_id: str, model_id: str) -> Optional[Dict[str, Any]]:
        """获取指定模型的完整配置（包含未脱敏的 api_key）"""
        for m in self._get_user_models(user_id):
            if m.get("id") == model_id:
                return dict(m)
        return None
    
    def add_model(self, user_id: str, model: Dict[str, Any]) -> tuple[bool, str]:
        """添加模型"""
        required = ["id", "name", "api_url", "api_key", "model"]
        for field in required:
            if not model.get(field):
                return False, f"缺少必填字段: {field}"
        
        user_id = str(user_id)
        if user_id not in self._data["users"]:
            self._data["users"][user_id] = {"models": []}
        
        existing = self._get_user_models(user_id)
        for m in existing:
            if m.get("id") == model["id"]:
                return False, f"模型 ID 已存在: {model['id']}"
        
        model.setdefault("base_url", model.get("api_url", "").replace("/chat/completions", ""))
        model.setdefault("created_at", datetime.now().isoformat())
        existing.append(model)
        
        if self._save_data():
            return True, "添加成功"
        return False, "保存失败"
    
    def update_model(self, user_id: str, model_id: str, updates: Dict[str, Any]) -> tuple[bool, str]:
        """更新模型"""
        user_id = str(user_id)
        models = self._get_user_models(user_id)
        for m in models:
            if m.get("id") == model_id:
                updates.pop("id", None)
                updates.pop("created_at", None)
                updates["updated_at"] = datetime.now().isoformat()
                m.update(updates)
                if self._save_data():
                    return True, "更新成功"
                return False, "保存失败"
        return False, f"模型不存在: {model_id}"
    
    def delete_model(self, user_id: str, model_id: str) -> tuple[bool, str]:
        """删除模型"""
        user_id = str(user_id)
        models = self._get_user_models(user_id)
        for m in models:
            if m.get("id") == model_id:
                models.remove(m)
                if self._save_data():
                    return True, "删除成功"
                return False, "保存失败"
        return False, f"模型不存在: {model_id}"


# 全局实例
novelcraft_model_manager = NovelCraftModelManager()
