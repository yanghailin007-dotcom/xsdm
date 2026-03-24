# -*- coding: utf-8 -*-
"""
Phase One Optimize Then Assess Service
第一阶段优化+质量评估组合服务

流程:
1. 加载第一阶段所有产品
2. 执行三轮智能优化
3. 保存优化结果
4. 执行质量评估
5. 返回组合结果
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class PhaseOneOptimizeThenAssess:
    """
    第一阶段优化+质量评估组合服务
    将三轮优化嵌套到质量评估之前
    """
    
    def __init__(self, api_client=None, user_novel_dir: Path = None):
        """
        初始化服务
        
        Args:
            api_client: AI API客户端
            user_novel_dir: 用户小说目录路径
        """
        self.api_client = api_client
        self.user_novel_dir = user_novel_dir
        self.progress_callback = None
        
    def set_progress_callback(self, callback):
        """设置进度回调函数"""
        self.progress_callback = callback
        
    def _notify_progress(self, step: str, progress: int, message: str):
        """通知进度更新"""
        if self.progress_callback:
            self.progress_callback(step, progress, message)
        logger.info(f"[OptimizeThenAssess] {step}: {progress}% - {message}")
    
    def optimize_then_assess(self, novel_title: str, platform: str = "fanqie") -> Dict[str, Any]:
        """
        执行优化+评估组合流程
        
        Args:
            novel_title: 小说标题
            platform: 目标平台
            
        Returns:
            组合结果，包含优化结果和质量评估报告
        """
        logger.info(f"[OptimizeThenAssess] 开始优化+评估流程: {novel_title}, 平台: {platform}")
        
        # ========== 阶段1: 加载产品数据 (0-10%) ==========
        self._notify_progress("loading", 0, "正在加载第一阶段产品...")
        products = self._load_phase_one_products(novel_title)
        if not products:
            raise ValueError(f"未找到小说 '{novel_title}' 的第一阶段产品数据")
        self._notify_progress("loading", 10, f"已加载 {len(products)} 个产品")
        
        # ========== 阶段2: 三轮智能优化 (10-70%) ==========
        # 第一轮: 平台风格适配
        self._notify_progress("optimization", 10, "开始第一轮: 平台风格适配...")
        from web.services.phase_one_optimizer import PhaseOneOptimizer
        optimizer = PhaseOneOptimizer(api_client=self.api_client)
        
        # 使用自定义进度回调
        original_callback = optimizer.progress_callback if hasattr(optimizer, 'progress_callback') else None
        optimizer.progress_callback = lambda r, p, m: self._notify_progress(
            "optimization", 
            10 + int(p * 0.2),  # 10-30%
            f"[{r}] {m}"
        )
        
        optimization_result = optimizer.optimize(products, platform)
        self._notify_progress("optimization", 30, "第一轮完成")
        
        # 第二轮已经在optimizer.optimize()中完成，这里模拟进度
        self._notify_progress("optimization", 50, "第二轮: 数据匹配完成")
        self._notify_progress("optimization", 70, "第三轮: 内容连贯性检查完成")
        
        # 保存优化结果
        self._save_optimization_result(novel_title, optimization_result)
        
        # ========== 阶段3: 质量评估 (70-100%) ==========
        self._notify_progress("assessment", 70, "开始质量评估...")
        
        # 构建写作计划路径
        safe_title = self._safe_filename(novel_title)
        plan_path = self.user_novel_dir / safe_title / "plans" / f"{safe_title}_opening_stage_writing_plan.json"
        
        if not plan_path.exists():
            logger.warning(f"[OptimizeThenAssess] 写作计划不存在: {plan_path}")
            # 如果没有写作计划，仍然返回优化结果
            return {
                "success": True,
                "has_assessment": False,
                "optimization": optimization_result,
                "assessment": None,
                "message": "优化完成，但未找到写作计划进行质量评估"
            }
        
        # 执行质量评估
        try:
            from src.core.PlanQualityAssessor import PlanQualityAssessor
            
            assessor = PlanQualityAssessor(api_client=self.api_client)
            
            self._notify_progress("assessment", 80, "正在分析写作计划...")
            result = assessor.assess(plan_path, use_deep_analysis=True, skip_compression=True)
            
            self._notify_progress("assessment", 90, "正在生成评估报告...")
            
            # 转换为字典格式
            assessment_report = {
                "overall_score": result.overall_score,
                "readiness": result.readiness,
                "strengths": result.strengths,
                "issues": [
                    {
                        "category": i.category,
                        "severity": i.severity.value,
                        "location": i.location,
                        "description": i.description,
                        "suggestion": i.suggestion,
                        "auto_fixable": i.auto_fixable
                    }
                    for i in result.issues
                ],
                "summary": result.summary,
                "token_saved": result.token_saved,
                "assessment_time": datetime.now().isoformat()
            }
            
            # 保存质量评估报告
            self._save_assessment_report(novel_title, assessment_report)
            
            self._notify_progress("assessment", 100, "质量评估完成")
            
            return {
                "success": True,
                "has_assessment": True,
                "optimization": optimization_result,
                "assessment": assessment_report,
                "combined_score": self._calculate_combined_score(
                    optimization_result['overall_score'],
                    assessment_report['overall_score']
                ),
                "message": "优化和质量评估全部完成"
            }
            
        except Exception as e:
            logger.error(f"[OptimizeThenAssess] 质量评估失败: {e}")
            # 即使评估失败，也返回优化结果
            return {
                "success": True,
                "has_assessment": False,
                "optimization": optimization_result,
                "assessment": None,
                "error": str(e),
                "message": "优化完成，但质量评估失败"
            }
    
    def _load_phase_one_products(self, novel_title: str) -> Dict[str, Any]:
        """加载第一阶段产品数据"""
        safe_title = self._safe_filename(novel_title)
        project_path = self.user_novel_dir / safe_title
        
        products = {}
        product_files = {
            'worldview': '世界观设定.json',
            'characters': '核心角色.json',
            'factions': '势力设定.json',
            'growth': '升级路线.json',
            'writing': '写作风格.json',
            'storyline': '故事线.json',
            'market_analysis': '市场分析.json'
        }
        
        for key, filename in product_files.items():
            file_path = project_path / filename
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        products[key] = json.load(f)
                except Exception as e:
                    logger.warning(f"加载 {filename} 失败: {e}")
                    products[key] = None
            else:
                products[key] = None
        
        # 过滤掉None值
        return {k: v for k, v in products.items() if v is not None}
    
    def _save_optimization_result(self, novel_title: str, result: Dict):
        """保存优化结果"""
        try:
            safe_title = self._safe_filename(novel_title)
            report_path = self.user_novel_dir / safe_title / "phase_one_optimization.json"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[OptimizeThenAssess] 优化结果已保存: {report_path}")
        except Exception as e:
            logger.warning(f"[OptimizeThenAssess] 保存优化结果失败: {e}")
    
    def _save_assessment_report(self, novel_title: str, report: Dict):
        """保存质量评估报告"""
        try:
            safe_title = self._safe_filename(novel_title)
            report_path = self.user_novel_dir / safe_title / "quality_assessment.json"
            
            # 添加优化信息到评估报告
            report['has_optimization'] = True
            report['optimization_time'] = datetime.now().isoformat()
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[OptimizeThenAssess] 评估报告已保存: {report_path}")
        except Exception as e:
            logger.warning(f"[OptimizeThenAssess] 保存评估报告失败: {e}")
    
    def _safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        import re
        return re.sub(r'[\\/*?:"<>|]', "_", title)
    
    def _calculate_combined_score(self, optimization_score: int, assessment_score: int) -> int:
        """计算综合评分"""
        # 优化评分占40%，质量评估占60%
        return round(optimization_score * 0.4 + assessment_score * 0.6)


# 任务管理器
class OptimizeThenAssessTaskManager:
    """优化+评估任务管理器"""
    
    def __init__(self):
        self.tasks = {}
        
    def create_task(self, novel_title: str, platform: str) -> str:
        """创建新任务"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self.tasks[task_id] = {
            "id": task_id,
            "novel_title": novel_title,
            "platform": platform,
            "status": "pending",
            "progress": 0,
            "current_phase": None,
            "message": "等待开始...",
            "result": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self.tasks.get(task_id)
    
    def update_task(self, task_id: str, **kwargs):
        """更新任务状态"""
        if task_id in self.tasks:
            self.tasks[task_id].update(kwargs)
            self.tasks[task_id]["updated_at"] = datetime.now().isoformat()
    
    def list_tasks(self, novel_title: str = None) -> list:
        """列出任务"""
        tasks = list(self.tasks.values())
        if novel_title:
            tasks = [t for t in tasks if t.get("novel_title") == novel_title]
        return sorted(tasks, key=lambda x: x["created_at"], reverse=True)


# 全局任务管理器实例
optimize_assess_task_manager = OptimizeThenAssessTaskManager()
