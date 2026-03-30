"""
提示词包数据模型
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class StepConfig:
    """步骤配置"""
    step_id: str
    step_name: str
    step_order: int
    enabled: bool = True
    description: str = ""
    prompt_template: Dict = field(default_factory=dict)
    parameters: Dict = field(default_factory=dict)
    output_schema: Dict = field(default_factory=dict)
    
    def render_prompt(self, variables: Dict[str, Any]) -> str:
        """
        渲染提示词模板
        
        Args:
            variables: 变量字典
            
        Returns:
            渲染后的提示词字符串
        """
        sections = self.prompt_template.get("context_sections", [])
        rendered_parts = []
        
        for section in sections:
            section_type = section.get("type", "static")
            
            if section_type == "static":
                # 静态内容直接添加
                content = section.get("content", "")
                rendered_parts.append(content)
                
            elif section_type == "dynamic":
                # 动态内容需要渲染变量
                template = section.get("template", "")
                rendered = self._render_template(template, variables)
                rendered_parts.append(rendered)
        
        return "\n\n".join(rendered_parts)
    
    def _render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        渲染单个模板字符串
        
        支持 {var_name} 格式的变量替换
        """
        result = template
        
        # 查找所有变量占位符
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        for placeholder in placeholders:
            if placeholder in variables:
                value = variables[placeholder]
                # 处理不同类型的值
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, indent=2)
                elif value is None:
                    value = ""
                else:
                    value = str(value)
                
                result = result.replace(f"{{{placeholder}}}", value)
            else:
                # 变量未提供，使用默认值或保持原样
                var_config = self._get_variable_config(placeholder)
                if var_config and "default" in var_config:
                    default_value = var_config["default"]
                    result = result.replace(f"{{{placeholder}}}", str(default_value))
        
        return result
    
    def _get_variable_config(self, var_name: str) -> Optional[Dict]:
        """获取变量配置"""
        variables = self.prompt_template.get("variables", [])
        for var in variables:
            if var.get("name") == var_name:
                return var
        return None
    
    def get_variable_names(self) -> List[str]:
        """获取所有变量名"""
        variables = self.prompt_template.get("variables", [])
        return [v.get("name") for v in variables if v.get("name")]
    
    def validate_output(self, output: Any) -> tuple[bool, List[str]]:
        """
        验证输出是否符合schema
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        schema = self.output_schema
        
        if not schema:
            return True, []
        
        required_fields = schema.get("required_fields", [])
        
        if isinstance(output, dict):
            for field in required_fields:
                if field not in output:
                    errors.append(f"缺少必填字段: {field}")
        
        return len(errors) == 0, errors


class PromptPackage:
    """提示词包"""
    
    def __init__(self, package_path: Path):
        """
        初始化提示词包
        
        Args:
            package_path: 提示词包目录路径
        """
        self.package_path = Path(package_path)
        self.info = {}
        self.steps: Dict[str, StepConfig] = {}
        
        self._load_package()
    
    def _load_package(self):
        """加载提示词包信息"""
        # 加载 package_info.json
        info_path = self.package_path / "package_info.json"
        if info_path.exists():
            with open(info_path, 'r', encoding='utf-8') as f:
                self.info = json.load(f)
        
        # 加载所有步骤配置
        for step_file in self.package_path.glob("step_*.json"):
            with open(step_file, 'r', encoding='utf-8') as f:
                step_data = json.load(f)
                step_config = StepConfig(
                    step_id=step_data.get("step_id", ""),
                    step_name=step_data.get("step_name", ""),
                    step_order=step_data.get("step_order", 0),
                    enabled=step_data.get("enabled", True),
                    description=step_data.get("description", ""),
                    prompt_template=step_data.get("prompt_template", {}),
                    parameters=step_data.get("parameters", {}),
                    output_schema=step_data.get("output_schema", {})
                )
                self.steps[step_config.step_id] = step_config
    
    @property
    def id(self) -> str:
        return self.info.get("id", "")
    
    @property
    def name(self) -> str:
        return self.info.get("name", "")
    
    @property
    def description(self) -> str:
        return self.info.get("description", "")
    
    @property
    def mode(self) -> str:
        return self.info.get("mode", "")
    
    @property
    def is_default(self) -> bool:
        return self.info.get("is_default", False)
    
    @property
    def is_editable(self) -> bool:
        return self.info.get("is_editable", True)
    
    def get_step(self, step_id: str) -> Optional[StepConfig]:
        """获取步骤配置"""
        return self.steps.get(step_id)
    
    def get_step_by_order(self, order: int) -> Optional[StepConfig]:
        """按顺序获取步骤"""
        for step in self.steps.values():
            if step.step_order == order:
                return step
        return None
    
    def get_all_steps(self) -> List[StepConfig]:
        """获取所有步骤（按顺序排序）"""
        return sorted(self.steps.values(), key=lambda s: s.step_order)
    
    def get_enabled_steps(self) -> List[StepConfig]:
        """获取启用的步骤"""
        return [s for s in self.get_all_steps() if s.enabled]
    
    def save(self):
        """保存提示词包信息"""
        info_path = self.package_path / "package_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(self.info, f, ensure_ascii=False, indent=2)
        
        # 保存步骤配置
        for step_id, step in self.steps.items():
            step_path = self.package_path / f"{step_id}.json"
            step_data = {
                "step_id": step.step_id,
                "step_name": step.step_name,
                "step_order": step.step_order,
                "enabled": step.enabled,
                "description": step.description,
                "prompt_template": step.prompt_template,
                "parameters": step.parameters,
                "output_schema": step.output_schema
            }
            with open(step_path, 'w', encoding='utf-8') as f:
                json.dump(step_data, f, ensure_ascii=False, indent=2)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "info": self.info,
            "steps": [
                {
                    "step_id": s.step_id,
                    "step_name": s.step_name,
                    "step_order": s.step_order,
                    "enabled": s.enabled,
                    "description": s.description
                }
                for s in self.get_all_steps()
            ]
        }
